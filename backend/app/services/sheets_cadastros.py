from datetime import date, datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import json
import threading
import time
from typing import Any, Iterable, Optional
from urllib import request, error

from fastapi import HTTPException

from app.core.config import settings
from app.models.cadastro import Cadastro


CADASTRO_FIELDS = [
    "id",
    "nome",
    "nome_social",
    "cpf",
    "rg",
    "orgao_expedidor",
    "data_nascimento",
    "email",
    "telefone",
    "endereco",
    "cidade",
    "uf",
    "estado_civil",
    "cor_raca",
    "identidade_genero",
    "pcd",
    "renda_media",
    "com_encaminhamento",
    "encaminhamento_realizado",
    "foto_url",
    "comprovante_residencia_url",
    "documento_pessoal_url",
    "termo_imagem_url",
    "termo_lgpd_url",
    "status",
    "aprovado_por_id",
    "observacoes",
    "criado_em",
    "atualizado_em",
]

DATE_FIELDS = {"data_nascimento"}
DATETIME_FIELDS = {"criado_em", "atualizado_em"}
BOOL_FIELDS = {"pcd", "com_encaminhamento", "encaminhamento_realizado"}
INT_FIELDS = {"id", "aprovado_por_id"}
LIST_CACHE_TTL_SECONDS = 60

_cache_lock = threading.Lock()
_cache_rows: list[dict[str, Any]] | None = None
_cache_at = 0.0
_refreshing = False
_executor = ThreadPoolExecutor(max_workers=1)


def sheets_enabled() -> bool:
    return settings.CADASTROS_STORAGE.lower() in {"sheets", "google_sheets", "apps_script"}


def _require_config() -> None:
    if not settings.GOOGLE_APPS_SCRIPT_URL:
        raise HTTPException(status_code=500, detail="GOOGLE_APPS_SCRIPT_URL não configurada")
    if not settings.GOOGLE_APPS_SCRIPT_TOKEN:
        raise HTTPException(status_code=500, detail="GOOGLE_APPS_SCRIPT_TOKEN não configurado")


def _serialize(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "sim", "yes", "y"}


def _parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value)[:10])


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.fromisoformat(text[:19])


def _row_to_cadastro(row: dict[str, Any]) -> Cadastro:
    data: dict[str, Any] = {}
    for field in CADASTRO_FIELDS:
        value = row.get(field)
        if field in BOOL_FIELDS:
            data[field] = _parse_bool(value)
        elif field in DATE_FIELDS:
            data[field] = _parse_date(value)
        elif field in DATETIME_FIELDS:
            data[field] = _parse_datetime(value)
        elif field in INT_FIELDS:
            data[field] = int(value) if value not in (None, "") else None
        else:
            data[field] = str(value) if value not in (None, "") else None

    cadastro = Cadastro(**{k: v for k, v in data.items() if k not in {"id", "criado_em", "atualizado_em"}})
    cadastro.id = data["id"]
    cadastro.criado_em = data.get("criado_em") or datetime.now(timezone.utc)
    cadastro.atualizado_em = data.get("atualizado_em")
    return cadastro


def _row_vazia(row: dict[str, Any]) -> bool:
    if not row:
        return True
    return not row.get("id") or all(value in (None, "") for value in row.values())


def _cadastro_to_row(cadastro: Cadastro) -> dict[str, Any]:
    return {field: _serialize(getattr(cadastro, field, None)) for field in CADASTRO_FIELDS}


def _call_apps_script(action: str, payload: Optional[dict[str, Any]] = None) -> Any:
    _require_config()
    body = json.dumps({
        "token": settings.GOOGLE_APPS_SCRIPT_TOKEN,
        "action": action,
        "payload": payload or {},
    }).encode("utf-8")
    req = request.Request(
        settings.GOOGLE_APPS_SCRIPT_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Erro ao acessar Google Apps Script: {exc}") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Resposta inválida do Google Apps Script") from exc

    if not parsed.get("ok"):
        raise HTTPException(status_code=502, detail=parsed.get("error") or "Erro no Google Apps Script")
    return parsed.get("data")


def _fetch_rows() -> list[dict[str, Any]]:
    rows = _call_apps_script("list") or []
    if not isinstance(rows, list):
        return []
    return rows


def _set_cache(rows: list[dict[str, Any]]) -> None:
    global _cache_rows, _cache_at
    with _cache_lock:
        _cache_rows = rows
        _cache_at = time.monotonic()


def _refresh_cache_sync() -> list[dict[str, Any]]:
    rows = _fetch_rows()
    _set_cache(rows)
    return rows


def _refresh_cache_background() -> None:
    global _refreshing
    try:
        _refresh_cache_sync()
    finally:
        with _cache_lock:
            _refreshing = False


def _schedule_refresh() -> None:
    global _refreshing
    with _cache_lock:
        if _refreshing:
            return
        _refreshing = True
    _executor.submit(_refresh_cache_background)


def aquecer_cache_sheets() -> None:
    if sheets_enabled():
        _schedule_refresh()


def listar_cadastros_sheets(force_refresh: bool = False) -> list[Cadastro]:
    if force_refresh:
        rows = _refresh_cache_sync()
        return [_row_to_cadastro(row) for row in rows if not _row_vazia(row)]

    with _cache_lock:
        rows = list(_cache_rows) if _cache_rows is not None else None
        idade = time.monotonic() - _cache_at

    if rows is None:
        rows = _refresh_cache_sync()
    elif idade > LIST_CACHE_TTL_SECONDS:
        _schedule_refresh()

    return [_row_to_cadastro(row) for row in rows if not _row_vazia(row)]


def buscar_cadastro_sheets(cadastro_id: int) -> Optional[Cadastro]:
    for cadastro in listar_cadastros_sheets():
        if cadastro.id == cadastro_id:
            return cadastro
    row = _call_apps_script("get", {"id": cadastro_id})
    if row:
        _upsert_cache_row(row)
    return _row_to_cadastro(row) if row else None


def _upsert_cache_row(row: dict[str, Any]) -> None:
    row_id = int(row.get("id") or 0)
    if not row_id:
        return
    with _cache_lock:
        if _cache_rows is None:
            return
        next_rows = [existing for existing in _cache_rows if int(existing.get("id") or 0) != row_id]
        next_rows.append(row)
        next_rows.sort(key=lambda item: str(item.get("criado_em") or ""), reverse=True)
        _cache_rows[:] = next_rows


def _remove_cache_row(cadastro_id: int) -> None:
    with _cache_lock:
        if _cache_rows is None:
            return
        _cache_rows[:] = [row for row in _cache_rows if int(row.get("id") or 0) != cadastro_id]


def criar_cadastro_sheets(cadastro: Cadastro) -> Cadastro:
    if not cadastro.status:
        cadastro.status = "pendente"
    cadastro.criado_em = cadastro.criado_em or datetime.now(timezone.utc)
    row = _call_apps_script("create", {"row": _cadastro_to_row(cadastro)})
    _upsert_cache_row(row)
    return _row_to_cadastro(row)


def atualizar_cadastro_sheets(cadastro: Cadastro) -> Cadastro:
    cadastro.atualizado_em = datetime.now(timezone.utc)
    row = _call_apps_script("update", {"id": cadastro.id, "row": _cadastro_to_row(cadastro)})
    _upsert_cache_row(row)
    return _row_to_cadastro(row)


def excluir_cadastro_sheets(cadastro_id: int) -> None:
    _call_apps_script("delete", {"id": cadastro_id})
    _remove_cache_row(cadastro_id)


def cpf_existe_sheets(cpfs: Iterable[str], ignorar_id: Optional[int] = None) -> bool:
    candidatos = {cpf for cpf in cpfs if cpf}
    for cadastro in listar_cadastros_sheets():
        if ignorar_id and cadastro.id == ignorar_id:
            continue
        if cadastro.cpf in candidatos:
            return True
    return False
