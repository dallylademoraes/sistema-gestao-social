from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import time
import threading
from typing import Any, Optional
from urllib import error, request

from fastapi import HTTPException

from app.core.config import settings


USER_FIELDS = [
    "id",
    "nome",
    "email",
    "senha_hash",
    "perfil",
    "ativo",
    "criado_em",
    "atualizado_em",
    "precisa_trocar_senha",
]

BOOL_FIELDS = {"ativo", "precisa_trocar_senha"}
DATETIME_FIELDS = {"criado_em", "atualizado_em"}
LIST_CACHE_TTL_SECONDS = 30

_cache_lock = threading.Lock()
_cache_rows: list[dict[str, Any]] | None = None
_cache_at = 0.0
_refreshing = False
_executor = ThreadPoolExecutor(max_workers=1)


@dataclass
class UsuarioSheets:
    id: int | None = None
    nome: str | None = None
    email: str | None = None
    senha_hash: str | None = None
    perfil: str | None = None
    ativo: bool = True
    criado_em: datetime | None = None
    atualizado_em: datetime | None = None
    precisa_trocar_senha: bool = False


def usuarios_sheets_enabled() -> bool:
    return settings.CADASTROS_STORAGE.lower() in {"sheets", "google_sheets", "apps_script"}


def _require_config() -> None:
    if not settings.GOOGLE_APPS_SCRIPT_URL:
        raise HTTPException(status_code=500, detail="GOOGLE_APPS_SCRIPT_URL não configurada")
    if not settings.GOOGLE_APPS_SCRIPT_TOKEN:
        raise HTTPException(status_code=500, detail="GOOGLE_APPS_SCRIPT_TOKEN não configurado")


def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "sim", "yes", "y"}


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


def _row_to_usuario(row: dict[str, Any]) -> UsuarioSheets:
    data: dict[str, Any] = {}
    for field in USER_FIELDS:
        value = row.get(field)
        if field in BOOL_FIELDS:
            data[field] = _parse_bool(value)
        elif field in DATETIME_FIELDS:
            data[field] = _parse_datetime(value)
        elif field == "id":
            data[field] = int(value) if value not in (None, "") else None
        else:
            data[field] = str(value) if value not in (None, "") else None
    if data.get("criado_em") is None:
        data["criado_em"] = datetime.now(timezone.utc)
    return UsuarioSheets(**data)


def _usuario_to_row(usuario: Any) -> dict[str, Any]:
    if isinstance(usuario, dict):
        return {field: _serialize(usuario.get(field)) for field in USER_FIELDS}
    return {field: _serialize(getattr(usuario, field, None)) for field in USER_FIELDS}


def _call_apps_script(action: str, payload: Optional[dict[str, Any]] = None) -> Any:
    _require_config()
    body = json.dumps(
        {
            "token": settings.GOOGLE_APPS_SCRIPT_TOKEN,
            "action": action,
            "payload": {"sheet": "usuarios", **(payload or {})},
        }
    ).encode("utf-8")
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


def listar_usuarios_sheets(force_refresh: bool = False) -> list[UsuarioSheets]:
    if force_refresh:
        return [_row_to_usuario(row) for row in _refresh_cache_sync()]

    with _cache_lock:
        rows = list(_cache_rows) if _cache_rows is not None else None
        idade = time.monotonic() - _cache_at

    if rows is None:
        rows = _refresh_cache_sync()
    elif idade > LIST_CACHE_TTL_SECONDS:
        _schedule_refresh()

    return [_row_to_usuario(row) for row in rows]


def buscar_usuario_sheets(usuario_id: int | None = None, email: str | None = None) -> Optional[UsuarioSheets]:
    if email:
        email_normalizado = email.strip().lower()
        for usuario in listar_usuarios_sheets():
            if (usuario.email or "").strip().lower() == email_normalizado:
                return usuario
    if usuario_id is not None:
        for usuario in listar_usuarios_sheets():
            if int(usuario.id or 0) == int(usuario_id):
                return usuario
        row = _call_apps_script("get", {"id": usuario_id})
        return _row_to_usuario(row) if row else None
    return None


def contar_coordenadoras_ativas_sheets() -> int:
    return sum(1 for usuario in listar_usuarios_sheets() if usuario.perfil == "coordenadora" and usuario.ativo)


def _upsert_cache_row(row: dict[str, Any]) -> None:
    row_id = int(row.get("id") or 0)
    if not row_id:
        return
    global _cache_rows
    with _cache_lock:
        if _cache_rows is None:
            return
        next_rows = [existing for existing in _cache_rows if int(existing.get("id") or 0) != row_id]
        next_rows.append(row)
        next_rows.sort(key=lambda item: str(item.get("criado_em") or ""), reverse=True)
        _cache_rows = next_rows


def _remove_cache_row(usuario_id: int) -> None:
    global _cache_rows
    with _cache_lock:
        if _cache_rows is None:
            return
        _cache_rows = [row for row in _cache_rows if int(row.get("id") or 0) != usuario_id]


def criar_usuario_sheets(usuario: Any) -> UsuarioSheets:
    row = _call_apps_script("create", {"row": _usuario_to_row(usuario)})
    _upsert_cache_row(row)
    return _row_to_usuario(row)


def atualizar_usuario_sheets(usuario_id: int, dados: dict[str, Any]) -> UsuarioSheets:
    row = _call_apps_script("update", {"id": usuario_id, "row": dados})
    _upsert_cache_row(row)
    return _row_to_usuario(row)


def excluir_usuario_sheets(usuario_id: int) -> bool:
    _call_apps_script("delete", {"id": usuario_id})
    _remove_cache_row(usuario_id)
    return True
