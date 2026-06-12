from datetime import date, datetime, timezone
import base64
import csv
import io
import os
import re
import shutil
import uuid
import mimetypes
from typing import Optional, List
import xlsxwriter

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.session import get_db
from app.models.cadastro import Cadastro
from app.models.cadastro_lgpd import CadastroLGPD
from app.models.usuario import Usuario
from app.schemas.cadastro import (
    CadastroAssinaturaRequest,
    CadastroCreate,
    CadastroDadosBase,
    CadastroUpdate,
    CadastroOut,
    CadastroTermoPreviewRequest,
    ExcluirCadastroPayload,
)
from app.core.security import usuario_atual, requer_perfil
from app.services.pdf import gerar_pdf_cadastro
from app.services.pdf_termos import gerar_pdf_termo_acordo
from app.services.audit import registrar_auditoria
from app.services.arquivos import (
    validar_arquivo_upload,
    salvar_arquivo_externo,
    gerar_url_assinada_download,
    verificar_token_download,
    responder_download,
    header_content_disposition_attachment,
)
from app.services.sheets_cadastros import (
    atualizar_cadastro_sheets,
    buscar_cadastro_sheets,
    cpf_existe_sheets,
    criar_cadastro_sheets,
    excluir_cadastro_sheets,
    listar_cadastros_sheets,
    sheets_enabled,
)

router = APIRouter(prefix="/cadastros", tags=["cadastros"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

STATUS_VALIDOS = {"pendente", "ativo", "inativo"}
MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _somente_digitos(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _cpf_valido(cpf: str) -> bool:
    digits = _somente_digitos(cpf)
    if len(digits) != 11:
        return False
    if digits == digits[0] * 11:
        return False

    soma_1 = sum(int(digits[i]) * (10 - i) for i in range(9))
    d1 = (soma_1 * 10) % 11
    d1 = 0 if d1 == 10 else d1

    soma_2 = sum(int(digits[i]) * (11 - i) for i in range(10))
    d2 = (soma_2 * 10) % 11
    d2 = 0 if d2 == 10 else d2

    return digits[-2:] == f"{d1}{d2}"


def _sanitizar_nome_titular_ficheiro(nome: str) -> str:
    """Segmento seguro para usar no nome do ficheiro (Windows / HTTP)."""
    s = (nome or "").strip()
    if not s:
        return "cadastro"
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", s)
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"^[.\s_-]+|[.\s_-]+$", "", s)
    return (s or "cadastro")[:80]


def _nome_pdf_previa_termo(nome_titular: str, tipo: str) -> str:
    base = _sanitizar_nome_titular_ficheiro(nome_titular)
    rotulo = "Termo_LGPD" if tipo == "lgpd" else "Termo_uso_imagem"
    return f"{base}_previa_{rotulo}.pdf"


def _nome_pdf_termo_armazenado(nome_titular: str, tipo_doc: str) -> str:
    base = _sanitizar_nome_titular_ficheiro(nome_titular)
    if tipo_doc == "termo_lgpd":
        return f"{base}_Termo_LGPD.pdf"
    if tipo_doc == "termo_imagem":
        return f"{base}_Termo_uso_imagem.pdf"
    raise ValueError("tipo_doc inválido para nome de termo")


def _nome_arquivo_export(prefixo: str, extensao: str = "csv") -> str:
    agora = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{prefixo}_{agora}.{extensao}"


def _valor_csv(valor):
    if isinstance(valor, bool):
        return "Sim" if valor else "Não"
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if valor is None:
        return ""
    texto = str(valor)
    if texto.startswith(("=", "+", "-", "@")):
        return f"'{texto}"
    return texto


def _response_csv(nome_arquivo: str, linhas: list[list[object]]) -> Response:
    buffer = io.StringIO()
    buffer.write("sep=;\n")
    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")
    for linha in linhas:
        writer.writerow([_valor_csv(valor) for valor in linha])
    return Response(
        content=buffer.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": header_content_disposition_attachment(nome_arquivo)},
    )


def _formatar_cpf(cpf: str) -> str:
    digits = _somente_digitos(cpf)
    return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"


def _idade_em_anos(data_nascimento: date) -> int:
    hoje = date.today()
    return hoje.year - data_nascimento.year - (
        (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day)
    )


def _validar_data_nascimento(data_nascimento: date) -> None:
    if data_nascimento is None:
        return
    if data_nascimento > date.today():
        raise HTTPException(status_code=400, detail="Data de nascimento não pode ser futura")
    if data_nascimento.year < 1900:
        raise HTTPException(status_code=400, detail="Data de nascimento inválida")
    if _idade_em_anos(data_nascimento) > 120:
        raise HTTPException(status_code=400, detail="Idade inválida")


def _validar_status(status: str) -> None:
    if status not in STATUS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Status inválido. Use: {sorted(STATUS_VALIDOS)}")


def _query_cadastros_filtrada(
    db: Session,
    busca: Optional[str] = None,
    status: Optional[str] = None,
    pcd: Optional[bool] = None,
    genero: Optional[str] = None,
    lgpd_concluido: Optional[bool] = None,
):
    q = db.query(Cadastro)
    if busca:
        q = q.filter(
            Cadastro.nome.ilike(f"%{busca}%") | Cadastro.cpf.contains(busca)
        )
    if status:
        q = q.filter(Cadastro.status == status)
    if pcd is not None:
        q = q.filter(Cadastro.pcd == pcd)
    if genero:
        q = q.filter(Cadastro.identidade_genero == genero)
    if lgpd_concluido is not None:
        tem_ambos = and_(
            Cadastro.termo_lgpd_url.isnot(None),
            Cadastro.termo_lgpd_url != "",
            Cadastro.termo_imagem_url.isnot(None),
            Cadastro.termo_imagem_url != "",
        )
        if lgpd_concluido:
            q = q.filter(tem_ambos)
        else:
            q = q.filter(
                or_(
                    Cadastro.termo_lgpd_url.is_(None),
                    Cadastro.termo_lgpd_url == "",
                    Cadastro.termo_imagem_url.is_(None),
                    Cadastro.termo_imagem_url == "",
                )
            )
    return q


def _cadastro_corresponde_filtros(
    cadastro: Cadastro,
    busca: Optional[str] = None,
    status: Optional[str] = None,
    pcd: Optional[bool] = None,
    genero: Optional[str] = None,
    lgpd_concluido: Optional[bool] = None,
) -> bool:
    if busca:
        termo = busca.lower()
        if termo not in (cadastro.nome or "").lower() and busca not in (cadastro.cpf or ""):
            return False
    if status and cadastro.status != status:
        return False
    if pcd is not None and cadastro.pcd != pcd:
        return False
    if genero and cadastro.identidade_genero != genero:
        return False
    if lgpd_concluido is not None and cadastro.lgpd_concluido != lgpd_concluido:
        return False
    return True


def _listar_cadastros_filtrados(
    db: Session,
    busca: Optional[str] = None,
    status: Optional[str] = None,
    pcd: Optional[bool] = None,
    genero: Optional[str] = None,
    lgpd_concluido: Optional[bool] = None,
) -> list[Cadastro]:
    if not sheets_enabled():
        return _query_cadastros_filtrada(db, busca, status, pcd, genero, lgpd_concluido).order_by(Cadastro.criado_em.desc()).all()

    cadastros = [
        cadastro
        for cadastro in listar_cadastros_sheets()
        if _cadastro_corresponde_filtros(cadastro, busca, status, pcd, genero, lgpd_concluido)
    ]
    return sorted(cadastros, key=lambda c: c.criado_em or datetime.min, reverse=True)


def _buscar_cadastro(db: Session, cadastro_id: int) -> Optional[Cadastro]:
    if sheets_enabled():
        return buscar_cadastro_sheets(cadastro_id)
    return db.query(Cadastro).filter(Cadastro.id == cadastro_id).first()


def _cpf_ja_cadastrado(db: Session, cpfs: list[str], ignorar_id: Optional[int] = None) -> bool:
    if sheets_enabled():
        return cpf_existe_sheets(cpfs, ignorar_id=ignorar_id)
    existente = db.query(Cadastro).filter(Cadastro.cpf.in_(cpfs)).first()
    return bool(existente and existente.id != ignorar_id)


def _obter_ou_criar_lgpd(db: Session, cadastro_id: int) -> CadastroLGPD:
    lgpd = db.query(CadastroLGPD).filter(CadastroLGPD.cadastro_id == cadastro_id).first()
    if not lgpd:
        lgpd = CadastroLGPD(cadastro_id=cadastro_id, base_legal="consentimento", status_lgpd="pendente")
        db.add(lgpd)
        db.flush()
    return lgpd


def _obter_lgpd(db: Session, cadastro_id: int) -> Optional[CadastroLGPD]:
    if sheets_enabled():
        return None
    return db.query(CadastroLGPD).filter(CadastroLGPD.cadastro_id == cadastro_id).first()


def _decode_assinatura_png(raw: str) -> bytes:
    s = (raw or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="Assinatura obrigatória")
    if s.startswith("data:"):
        parts = s.split(",", 1)
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Formato de assinatura inválido")
        s = parts[1]
    try:
        out = base64.b64decode(s, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Assinatura em base64 inválida") from exc
    if len(out) > 500_000:
        raise HTTPException(status_code=400, detail="Assinatura excede o tamanho máximo permitido")
    if not out.startswith(b"\x89PNG"):
        raise HTTPException(status_code=400, detail="A assinatura deve ser uma imagem PNG")
    return out


def _cadastro_para_preview(body: CadastroTermoPreviewRequest) -> Cadastro:
    d = body.model_dump(exclude={"tipo", "assinatura_base64"})
    c = Cadastro(**d)
    c.id = 0
    c.status = "pendente"
    return c


def _gerar_pdfs_termos_e_anexar(c: Cadastro, png: bytes) -> None:
    agora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    pdf_lgpd = gerar_pdf_termo_acordo(c, tipo="lgpd", imagem_png=png, quando_iso=agora)
    nome_lgpd = f"{uuid.uuid4().hex}.pdf"
    c.termo_lgpd_url = salvar_arquivo_externo(nome_lgpd, pdf_lgpd, "application/pdf")
    pdf_img = gerar_pdf_termo_acordo(c, tipo="imagem", imagem_png=png, quando_iso=agora)
    nome_img = f"{uuid.uuid4().hex}.pdf"
    c.termo_imagem_url = salvar_arquivo_externo(nome_img, pdf_img, "application/pdf")


def _alertas_aprovacao(cadastro: Cadastro) -> list[str]:
    docs_recomendados = {
        "foto": cadastro.foto_url,
        "comprovante de residência": cadastro.comprovante_residencia_url,
        "documento pessoal": cadastro.documento_pessoal_url,
    }
    return [nome for nome, valor in docs_recomendados.items() if not valor]


def _pendencias_aprovacao(cadastro: Cadastro) -> list[str]:
    pendencias: list[str] = []
    docs_bloqueantes = {
        "termo LGPD": cadastro.termo_lgpd_url,
        "termo de uso de imagem": cadastro.termo_imagem_url,
    }
    pendencias.extend(nome for nome, valor in docs_bloqueantes.items() if not valor)
    if not cadastro.telefone or not cadastro.nome:
        pendencias.append("dados básicos incompletos (nome e telefone)")
    if not _cpf_valido(cadastro.cpf):
        pendencias.append("CPF inválido")
    if cadastro.data_nascimento is None:
        pendencias.append("data de nascimento ausente")
    else:
        try:
            _validar_data_nascimento(cadastro.data_nascimento)
            if _idade_em_anos(cadastro.data_nascimento) < 16:
                pendencias.append("idade mínima de 16 anos")
        except HTTPException as exc:
            pendencias.append(str(exc.detail))
    return pendencias


def _validar_requisitos_aprovacao(cadastro: Cadastro) -> None:
    pendencias = _pendencias_aprovacao(cadastro)
    if not pendencias:
        return
    docs = {"termo LGPD", "termo de uso de imagem"}
    faltantes_docs = [p for p in pendencias if p in docs]
    if faltantes_docs:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível aprovar sem os termos assinados: {', '.join(faltantes_docs)}",
        )
    raise HTTPException(status_code=400, detail=pendencias[0].capitalize())


def _contar_por_label(valores: list[str]) -> list[tuple[str, int]]:
    contagem: dict[str, int] = {}
    for valor in valores:
        chave = (valor or "").strip() or "Não informado"
        contagem[chave] = contagem.get(chave, 0) + 1
    return sorted(contagem.items(), key=lambda item: item[1], reverse=True)


def _idade_cadastro(cadastro: Cadastro) -> Optional[int]:
    if not cadastro.data_nascimento:
        return None
    hoje = date.today()
    return hoje.year - cadastro.data_nascimento.year - (
        (hoje.month, hoje.day) < (cadastro.data_nascimento.month, cadastro.data_nascimento.day)
    )


def _faixa_etaria_label(cadastro: Cadastro) -> str:
    idade = _idade_cadastro(cadastro)
    if idade is None:
        return "Não informado"
    if idade <= 17:
        return "16 a 17"
    if idade <= 29:
        return "18 a 29"
    if idade <= 44:
        return "30 a 44"
    if idade <= 59:
        return "45 a 59"
    return "60+"


def _linhas_serie(titulo: str, dados: list[tuple[str, int]]) -> list[list[object]]:
    linhas: list[list[object]] = [[], [titulo, "Quantidade"]]
    linhas.extend([[label, valor] for label, valor in dados])
    return linhas


def _linhas_resumo_graficos(cadastros: list[Cadastro]) -> list[list[object]]:
    total = len(cadastros)
    ativos = sum(1 for c in cadastros if c.status == "ativo")
    pendentes = sum(1 for c in cadastros if c.status == "pendente")
    inativos = sum(1 for c in cadastros if c.status == "inativo")
    com_encaminhamento = sum(1 for c in cadastros if c.com_encaminhamento)
    termos_ok = sum(1 for c in cadastros if c.lgpd_concluido)
    pcd_sim = sum(1 for c in cadastros if c.pcd)

    linhas: list[list[object]] = [
        ["Relatório gerado em", datetime.now().strftime("%d/%m/%Y %H:%M")],
        [],
        ["Indicador", "Valor"],
        ["Total de cadastros", total],
        ["Ativos", ativos],
        ["Pendentes", pendentes],
        ["Inativos", inativos],
        ["Com encaminhamento", com_encaminhamento],
        ["Termos ok", termos_ok],
        ["Termos pendentes", total - termos_ok],
        ["PCD", pcd_sim],
        ["Não PCD", total - pcd_sim],
        [],
        ["Cadastros por status", "Quantidade"],
        ["Ativos", ativos],
        ["Pendentes", pendentes],
        ["Inativos", inativos],
        [],
        ["Termos LGPD", "Quantidade"],
        ["Termos ok", termos_ok],
        ["Termos pendentes", total - termos_ok],
        [],
        ["PCD", "Quantidade"],
        ["PCD", pcd_sim],
        ["Não PCD", total - pcd_sim],
    ]
    linhas.extend(_linhas_serie("Faixa etária", _contar_por_label([_faixa_etaria_label(c) for c in cadastros])))
    linhas.extend(_linhas_serie("Encaminhamentos", [
        ("Com encaminhamento", com_encaminhamento),
        ("Encaminhamento realizado", sum(1 for c in cadastros if c.encaminhamento_realizado)),
        ("Sem encaminhamento", max(total - com_encaminhamento, 0)),
    ]))
    linhas.extend(_linhas_serie("Renda média", _contar_por_label([c.renda_media for c in cadastros])))
    linhas.extend(_linhas_serie("Cor/raça", _contar_por_label([c.cor_raca for c in cadastros])))
    linhas.extend(_linhas_serie("Identidade de gênero", _contar_por_label([c.identidade_genero for c in cadastros])))
    linhas.extend(_linhas_serie("Principais cidades", [(label, valor) for label, valor in _contar_por_label([c.cidade for c in cadastros]) if label != "Não informado"][:20]))

    hoje = date.today()
    buckets: list[dict[str, object]] = []
    for i in range(11, -1, -1):
        mes = hoje.month - i
        ano = hoje.year
        while mes <= 0:
            mes += 12
            ano -= 1
        buckets.append({
            "ano": ano,
            "mes": mes,
            "label": f"{MESES_PT[mes - 1]}/{str(ano)[-2:]}",
            "value": 0,
        })
    indice = {(b["ano"], b["mes"]): idx for idx, b in enumerate(buckets)}
    for cadastro in cadastros:
        if not cadastro.criado_em:
            continue
        chave = (cadastro.criado_em.year, cadastro.criado_em.month)
        if chave in indice:
            buckets[indice[chave]]["value"] += 1

    linhas.extend(_linhas_serie("Novos cadastros por mês", [(b["label"], b["value"]) for b in buckets]))
    return linhas


def _montar_saida_cadastro(db: Session, cadastro: Cadastro) -> CadastroOut:
    lgpd = _obter_lgpd(db, cadastro.id)
    tem_termos = bool(cadastro.termo_lgpd_url) and bool(cadastro.termo_imagem_url)
    pendencias = _pendencias_aprovacao(cadastro)
    alertas = _alertas_aprovacao(cadastro)

    def url_documento(tipo: str, ref: Optional[str]) -> Optional[str]:
        return gerar_url_assinada_download(cadastro.id, tipo, ref) if ref else None

    return CadastroOut(
        id=cadastro.id,
        nome=cadastro.nome,
        nome_social=cadastro.nome_social,
        cpf=cadastro.cpf,
        rg=cadastro.rg,
        orgao_expedidor=cadastro.orgao_expedidor,
        data_nascimento=cadastro.data_nascimento,
        email=cadastro.email,
        telefone=cadastro.telefone,
        endereco=cadastro.endereco,
        cidade=cadastro.cidade,
        uf=cadastro.uf,
        estado_civil=cadastro.estado_civil,
        cor_raca=cadastro.cor_raca,
        identidade_genero=cadastro.identidade_genero,
        pcd=cadastro.pcd,
        renda_media=cadastro.renda_media,
        com_encaminhamento=cadastro.com_encaminhamento,
        encaminhamento_realizado=cadastro.encaminhamento_realizado,
        observacoes=cadastro.observacoes,
        status=cadastro.status,
        lgpd_concluido=tem_termos,
        pronto_aprovacao=not pendencias,
        pendencias_aprovacao=pendencias,
        alertas_aprovacao=alertas,
        criado_em=cadastro.criado_em,
        foto_url=url_documento("foto", cadastro.foto_url),
        comprovante_residencia_url=url_documento("comprovante", cadastro.comprovante_residencia_url),
        documento_pessoal_url=url_documento("documento", cadastro.documento_pessoal_url),
        termo_imagem_url=url_documento("termo_imagem", cadastro.termo_imagem_url),
        termo_lgpd_url=url_documento("termo_lgpd", cadastro.termo_lgpd_url),
        base_legal=None,
        status_lgpd=None,
        retencao_ate=lgpd.retencao_ate if lgpd else None,
        excluido_em=lgpd.excluido_em if lgpd else None,
        motivo_exclusao=lgpd.motivo_exclusao if lgpd else None,
        consentimentos=[],
    )


@router.get("/", response_model=List[CadastroOut])
def listar(
    busca: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    pcd: Optional[bool] = Query(None),
    genero: Optional[str] = Query(None),
    lgpd_concluido: Optional[bool] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
):
    itens = _listar_cadastros_filtrados(db, busca, status, pcd, genero, lgpd_concluido)[skip:skip + limit]
    return [_montar_saida_cadastro(db, c) for c in itens]


@router.get("/export/cadastros.csv")
def exportar_cadastros_csv(
    busca: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    pcd: Optional[bool] = Query(None),
    genero: Optional[str] = Query(None),
    lgpd_concluido: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
):
    cadastros = _listar_cadastros_filtrados(db, busca, status, pcd, genero, lgpd_concluido)
    linhas: list[list[object]] = [[
        "ID",
        "Nome completo",
        "Nome social",
        "CPF",
        "RG",
        "Órgão expedidor",
        "Data de nascimento",
        "E-mail",
        "Telefone",
        "Endereço",
        "Cidade",
        "UF",
        "Estado civil",
        "Cor/raça",
        "Identidade de gênero",
        "PCD",
        "Renda média",
        "Com encaminhamento",
        "Encaminhamento realizado",
        "Status",
        "Termos LGPD",
        "Foto anexada",
        "Comprovante anexado",
        "Documento pessoal anexado",
        "Pronto para aprovação",
        "Pendências de bloqueio",
        "Alertas",
        "Criado em",
        "Observações",
    ]]
    for cadastro in cadastros:
        pendencias = _pendencias_aprovacao(cadastro)
        alertas = _alertas_aprovacao(cadastro)
        linhas.append([
            cadastro.id,
            cadastro.nome,
            cadastro.nome_social,
            cadastro.cpf,
            cadastro.rg,
            cadastro.orgao_expedidor,
            cadastro.data_nascimento,
            cadastro.email,
            cadastro.telefone,
            cadastro.endereco,
            cadastro.cidade,
            cadastro.uf,
            cadastro.estado_civil,
            cadastro.cor_raca,
            cadastro.identidade_genero,
            cadastro.pcd,
            cadastro.renda_media,
            cadastro.com_encaminhamento,
            cadastro.encaminhamento_realizado,
            cadastro.status,
            "Concluído" if cadastro.lgpd_concluido else "Pendente",
            bool(cadastro.foto_url),
            bool(cadastro.comprovante_residencia_url),
            bool(cadastro.documento_pessoal_url),
            not pendencias,
            ", ".join(pendencias),
            ", ".join(alertas),
            cadastro.criado_em,
            cadastro.observacoes,
        ])
    return _response_csv(_nome_arquivo_export("cadastros_asap"), linhas)


@router.get("/export/graficos.csv")
def exportar_graficos_csv(
    busca: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    pcd: Optional[bool] = Query(None),
    genero: Optional[str] = Query(None),
    lgpd_concluido: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
):
    cadastros = _listar_cadastros_filtrados(db, busca, status, pcd, genero, lgpd_concluido)
    return _response_csv(_nome_arquivo_export("resumo_graficos_asap"), _linhas_resumo_graficos(cadastros))


@router.get("/export/cadastros.xlsx")
def exportar_cadastros_xlsx(
    busca: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    pcd: Optional[bool] = Query(None),
    genero: Optional[str] = Query(None),
    lgpd_concluido: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
):
    cadastros = _listar_cadastros_filtrados(db, busca, status, pcd, genero, lgpd_concluido)
    linhas = [[
        "ID",
        "Nome completo",
        "Nome social",
        "CPF",
        "RG",
        "Órgão expedidor",
        "Data de nascimento",
        "E-mail",
        "Telefone",
        "Endereço",
        "Cidade",
        "UF",
        "Estado civil",
        "Cor/raça",
        "Identidade de gênero",
        "PCD",
        "Renda média",
        "Com encaminhamento",
        "Encaminhamento realizado",
        "Status",
        "Termos LGPD",
        "Foto anexada",
        "Comprovante anexado",
        "Documento pessoal anexado",
        "Pronto para aprovação",
        "Pendências de bloqueio",
        "Alertas",
        "Criado em",
        "Observações",
    ]]
    for cadastro in cadastros:
        pendencias = _pendencias_aprovacao(cadastro)
        alertas = _alertas_aprovacao(cadastro)
        linhas.append([
            cadastro.id,
            cadastro.nome,
            cadastro.nome_social,
            cadastro.cpf,
            cadastro.rg,
            cadastro.orgao_expedidor,
            cadastro.data_nascimento,
            cadastro.email,
            cadastro.telefone,
            cadastro.endereco,
            cadastro.cidade,
            cadastro.uf,
            cadastro.estado_civil,
            cadastro.cor_raca,
            cadastro.identidade_genero,
            cadastro.pcd,
            cadastro.renda_media,
            cadastro.com_encaminhamento,
            cadastro.encaminhamento_realizado,
            cadastro.status,
            "Concluído" if cadastro.lgpd_concluido else "Pendente",
            bool(cadastro.foto_url),
            bool(cadastro.comprovante_residencia_url),
            bool(cadastro.documento_pessoal_url),
            not pendencias,
            ", ".join(pendencias),
            ", ".join(alertas),
            cadastro.criado_em,
            cadastro.observacoes,
        ])

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    ws = workbook.add_worksheet('Cadastros')
    for r, row in enumerate(linhas):
        for c, cell in enumerate(row):
            ws.write(r, c, cell)
    workbook.close()
    output.seek(0)
    return Response(content=output.read(), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={
        'Content-Disposition': header_content_disposition_attachment(_nome_arquivo_export('cadastros_asap', 'xlsx'))
    })


@router.get("/export/graficos.xlsx")
def exportar_graficos_xlsx(
    busca: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    pcd: Optional[bool] = Query(None),
    genero: Optional[str] = Query(None),
    lgpd_concluido: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
):
    cadastros = _listar_cadastros_filtrados(db, busca, status, pcd, genero, lgpd_concluido)
    linhas = _linhas_resumo_graficos(cadastros)

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    ws = workbook.add_worksheet('Resumo')
    for r, row in enumerate(linhas):
        for c, cell in enumerate(row):
            ws.write(r, c, cell)

    # parse blocks for charts
    status_block = []
    monthly_block = []
    i = 0
    while i < len(linhas):
        row = linhas[i]
        if len(row) >= 1 and row[0] == 'Cadastros por status':
            j = i + 2
            while j < len(linhas) and linhas[j] and len(linhas[j]) >= 2 and isinstance(linhas[j][1], int):
                status_block.append((linhas[j][0], linhas[j][1]))
                j += 1
            i = j
            continue
        if len(row) >= 1 and row[0] == 'Novos cadastros por mês':
            j = i + 2
            while j < len(linhas) and linhas[j] and len(linhas[j]) >= 2 and isinstance(linhas[j][1], int):
                monthly_block.append((linhas[j][0], linhas[j][1]))
                j += 1
            i = j
            continue
        i += 1

    chart_ws = workbook.add_worksheet('Charts')
    row = 0
    if status_block:
        chart_ws.write_row(row, 0, ['Status', 'Quantidade'])
        for k, (label, val) in enumerate(status_block, start=1):
            chart_ws.write(k, 0, label)
            chart_ws.write(k, 1, val)
        last = len(status_block)
        pie = workbook.add_chart({'type': 'pie'})
        pie.add_series({
            'name': 'Cadastros por status',
            'categories': f"=Charts!$A$2:$A${last+1}",
            'values': f"=Charts!$B$2:$B${last+1}",
        })
        chart_ws.insert_chart(0, 3, pie, {'x_scale': 1.2, 'y_scale': 1.2})
        row = last + 3

    if monthly_block:
        chart_ws.write_row(row, 0, ['Mês', 'Quantidade'])
        for k, (label, val) in enumerate(monthly_block, start=row+1):
            chart_ws.write(k, 0, label)
            chart_ws.write(k, 1, val)
        lastm = row + len(monthly_block)
        col_chart = workbook.add_chart({'type': 'column'})
        col_chart.add_series({
            'name': 'Novos cadastros por mês',
            'categories': f"=Charts!$A${row+2}:$A${lastm+1}",
            'values': f"=Charts!$B${row+2}:$B${lastm+1}",
        })
        chart_ws.insert_chart(row, 3, col_chart, {'x_scale': 1.6, 'y_scale': 1.6})

    workbook.close()
    output.seek(0)
    return Response(content=output.read(), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={
        'Content-Disposition': header_content_disposition_attachment(_nome_arquivo_export('resumo_graficos_asap', 'xlsx'))
    })


@router.post("/", response_model=CadastroOut, status_code=201)
def criar(body: CadastroCreate, request: Request, db: Session = Depends(get_db),
          atual: Usuario = Depends(requer_perfil("coordenadora", "assistente"))):
    if not _cpf_valido(body.cpf):
        raise HTTPException(status_code=400, detail="CPF inválido")
    _validar_data_nascimento(body.data_nascimento)
    cpf_formatado = _formatar_cpf(body.cpf)
    if _cpf_ja_cadastrado(db, [cpf_formatado, _somente_digitos(body.cpf), body.cpf]):
        raise HTTPException(status_code=400, detail="CPF já cadastrado")
    png = _decode_assinatura_png(body.assinatura_base64)
    dados = body.model_dump(exclude={"aceite_termo_lgpd", "aceite_termo_imagem", "assinatura_base64"})
    dados["cpf"] = cpf_formatado
    c = Cadastro(**dados)
    if sheets_enabled():
        c = criar_cadastro_sheets(c)
        try:
            _gerar_pdfs_termos_e_anexar(c, png)
        except Exception:
            excluir_cadastro_sheets(c.id)
            raise HTTPException(status_code=500, detail="Não foi possível gerar os termos em PDF. Tente novamente.")
        c = atualizar_cadastro_sheets(c)
    else:
        db.add(c)
        db.flush()
        try:
            _gerar_pdfs_termos_e_anexar(c, png)
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail="Não foi possível gerar os termos em PDF. Tente novamente.")
        db.commit()
        db.refresh(c)
    registrar_auditoria(
        db,
        action="cadastro.create",
        entity_type="cadastro",
        entity_id=c.id,
        details=f"cpf={c.cpf};status={c.status};termos_gerados=1",
        actor=atual,
        ip_address=request.client.host if request.client else None,
    )
    return _montar_saida_cadastro(db, c)


@router.post("/pendente-assinatura", response_model=CadastroOut, status_code=201)
def criar_pendente_assinatura(
    body: CadastroDadosBase,
    request: Request,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(requer_perfil("coordenadora", "assistente")),
):
    if not _cpf_valido(body.cpf):
        raise HTTPException(status_code=400, detail="CPF inválido")
    _validar_data_nascimento(body.data_nascimento)
    cpf_formatado = _formatar_cpf(body.cpf)
    if _cpf_ja_cadastrado(db, [cpf_formatado, _somente_digitos(body.cpf), body.cpf]):
        raise HTTPException(status_code=400, detail="CPF já cadastrado")
    dados = body.model_dump()
    dados["cpf"] = cpf_formatado
    c = Cadastro(**dados)
    if sheets_enabled():
        c = criar_cadastro_sheets(c)
    else:
        db.add(c)
        db.commit()
        db.refresh(c)
    registrar_auditoria(
        db,
        action="cadastro.create_pending_signature",
        entity_type="cadastro",
        entity_id=c.id,
        details=f"cpf={c.cpf};status={c.status};termos_gerados=0",
        actor=atual,
        ip_address=request.client.host if request.client else None,
    )
    return _montar_saida_cadastro(db, c)


@router.post("/preview-termo", response_class=Response)
def preview_termo(
    body: CadastroTermoPreviewRequest,
    _db: Session = Depends(get_db),
    _: Usuario = Depends(requer_perfil("coordenadora", "assistente")),
):
    if not _cpf_valido(body.cpf):
        raise HTTPException(status_code=400, detail="CPF inválido")
    _validar_data_nascimento(body.data_nascimento)
    png: Optional[bytes] = None
    if body.assinatura_base64 and body.assinatura_base64.strip():
        try:
            png = _decode_assinatura_png(body.assinatura_base64)
        except HTTPException:
            png = None
    c = _cadastro_para_preview(body)
    pdf = gerar_pdf_termo_acordo(c, tipo=body.tipo, imagem_png=png, quando_iso=None)
    nome = _nome_pdf_previa_termo(body.nome, body.tipo)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": header_content_disposition_attachment(nome)},
    )


@router.get("/{id}", response_model=CadastroOut)
def buscar(id: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    c = _buscar_cadastro(db, id)
    if not c:
        raise HTTPException(status_code=404, detail="Não encontrado")
    return _montar_saida_cadastro(db, c)


@router.patch("/{id}", response_model=CadastroOut)
def atualizar(id: int, body: CadastroUpdate, request: Request, db: Session = Depends(get_db),
              atual: Usuario = Depends(requer_perfil("coordenadora", "assistente"))):
    c = _buscar_cadastro(db, id)
    if not c:
        raise HTTPException(status_code=404, detail="Não encontrado")
    dados = body.model_dump(exclude_unset=True)
    if "cpf" in dados:
        if not _cpf_valido(dados["cpf"]):
            raise HTTPException(status_code=400, detail="CPF inválido")
        cpf_formatado = _formatar_cpf(dados["cpf"])
        if _cpf_ja_cadastrado(db, [cpf_formatado, _somente_digitos(dados["cpf"]), dados["cpf"]], ignorar_id=c.id):
            raise HTTPException(status_code=400, detail="CPF já cadastrado")
        dados["cpf"] = cpf_formatado
    if "data_nascimento" in dados:
        _validar_data_nascimento(dados["data_nascimento"])
    if "status" in dados:
        _validar_status(dados["status"])
        if dados["status"] == "ativo" and c.status != "ativo":
            raise HTTPException(status_code=400, detail="Use o endpoint de aprovação para ativar cadastro")
    for campo, valor in dados.items():
        setattr(c, campo, valor)
    if sheets_enabled():
        c = atualizar_cadastro_sheets(c)
    else:
        db.commit()
        db.refresh(c)
    registrar_auditoria(
        db,
        action="cadastro.update",
        entity_type="cadastro",
        entity_id=c.id,
        details=f"campos={','.join(sorted(dados.keys()))}",
        actor=atual,
        ip_address=request.client.host if request.client else None,
    )
    return _montar_saida_cadastro(db, c)


@router.post("/{id}/assinar", response_model=CadastroOut)
def assinar_cadastro(
    id: int,
    body: CadastroAssinaturaRequest,
    request: Request,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(requer_perfil("coordenadora", "assistente")),
):
    c = _buscar_cadastro(db, id)
    if not c:
        raise HTTPException(status_code=404, detail="Não encontrado")
    if c.termo_lgpd_url and c.termo_imagem_url:
        raise HTTPException(status_code=400, detail="Cadastro já possui termos assinados")
    png = _decode_assinatura_png(body.assinatura_base64)
    try:
        _gerar_pdfs_termos_e_anexar(c, png)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Não foi possível gerar os termos em PDF. Tente novamente.")
    if sheets_enabled():
        c = atualizar_cadastro_sheets(c)
    else:
        db.commit()
        db.refresh(c)
    registrar_auditoria(
        db,
        action="cadastro.sign_terms",
        entity_type="cadastro",
        entity_id=c.id,
        details="termos_gerados=1",
        actor=atual,
        ip_address=request.client.host if request.client else None,
    )
    return _montar_saida_cadastro(db, c)


@router.post("/{id}/aprovar", response_model=CadastroOut)
def aprovar(id: int, request: Request, db: Session = Depends(get_db),
            usuario: Usuario = Depends(requer_perfil("coordenadora"))):
    c = _buscar_cadastro(db, id)
    if not c:
        raise HTTPException(status_code=404, detail="Não encontrado")
    _validar_requisitos_aprovacao(c)
    c.status = "ativo"
    c.aprovado_por_id = usuario.id
    if sheets_enabled():
        c = atualizar_cadastro_sheets(c)
    else:
        db.commit()
        db.refresh(c)
    registrar_auditoria(
        db,
        action="cadastro.approve",
        entity_type="cadastro",
        entity_id=c.id,
        details="status=ativo",
        actor=usuario,
        ip_address=request.client.host if request.client else None,
    )
    return _montar_saida_cadastro(db, c)


@router.delete("/{id}", status_code=204)
def excluir(id: int, request: Request, db: Session = Depends(get_db),
            atual: Usuario = Depends(requer_perfil("coordenadora"))):
    c = _buscar_cadastro(db, id)
    if not c:
        raise HTTPException(status_code=404, detail="Nao encontrado")
    cadastro_id = c.id
    if sheets_enabled():
        excluir_cadastro_sheets(cadastro_id)
    else:
        db.delete(c)
        db.commit()
    registrar_auditoria(
        db,
        action="cadastro.delete",
        entity_type="cadastro",
        entity_id=cadastro_id,
        details="exclusao",
        actor=atual,
        ip_address=request.client.host if request.client else None,
    )
    return Response(status_code=204)


@router.get("/{id}/pdf")
def baixar_pdf(id: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    c = _buscar_cadastro(db, id)
    if not c:
        raise HTTPException(status_code=404, detail="Não encontrado")
    pdf = gerar_pdf_cadastro(c)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=cadastro_{id:04d}.pdf"},
    )


@router.post("/{id}/documentos/{tipo}")
async def upload_documento(id: int, tipo: str, arquivo: UploadFile = File(...),
                           db: Session = Depends(get_db),
                           _: Usuario = Depends(requer_perfil("coordenadora", "assistente"))):
    campos_validos = {
        "foto": "foto_url",
        "comprovante": "comprovante_residencia_url",
        "documento": "documento_pessoal_url",
    }
    if tipo not in campos_validos:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Use: {list(campos_validos)}")
    c = _buscar_cadastro(db, id)
    if not c:
        raise HTTPException(status_code=404, detail="Não encontrado")
    arquivo_seguro, conteúdo = await validar_arquivo_upload(tipo, arquivo)
    caminho = salvar_arquivo_externo(arquivo_seguro.storage_ref, conteúdo, arquivo_seguro.content_type)
    setattr(c, campos_validos[tipo], caminho)
    if sheets_enabled():
        c = atualizar_cadastro_sheets(c)
    else:
        db.commit()
    return {"url": gerar_url_assinada_download(c.id, tipo, caminho)}


@router.get("/{id}/documentos/{tipo}/baixar")
def baixar_documento(id: int, tipo: str, token: str, db: Session = Depends(get_db)):
    campos_validos = {
        "foto": "foto_url",
        "comprovante": "comprovante_residencia_url",
        "documento": "documento_pessoal_url",
        "termo_imagem": "termo_imagem_url",
        "termo_lgpd": "termo_lgpd_url",
    }
    if tipo not in campos_validos:
        raise HTTPException(status_code=400, detail="Tipo inválido")
    c = _buscar_cadastro(db, id)
    if not c:
        raise HTTPException(status_code=404, detail="Não encontrado")

    storage_ref = verificar_token_download(token, id, tipo)
    if getattr(c, campos_validos[tipo]) != storage_ref:
        raise HTTPException(status_code=401, detail="Token de download não confere com o arquivo atual")

    content_type = mimetypes.guess_type(storage_ref)[0] or "application/octet-stream"
    if tipo in ("termo_lgpd", "termo_imagem"):
        filename = _nome_pdf_termo_armazenado(c.nome or "", tipo)
    else:
        filename = os.path.basename(storage_ref)
    return responder_download(storage_ref, filename, content_type)


@router.post("/{id}/lgpd/excluir", response_model=CadastroOut)
def excluir_por_politica_lgpd(
    id: int,
    body: ExcluirCadastroPayload,
    request: Request,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(requer_perfil("coordenadora")),
):
    c = _buscar_cadastro(db, id)
    if not c:
        raise HTTPException(status_code=404, detail="Não encontrado")

    if sheets_enabled():
        agora = datetime.now(timezone.utc)
        c.nome = "DADO EXCLUIDO"
        c.nome_social = None
        c.rg = None
        c.orgao_expedidor = None
        c.email = None
        c.telefone = "DADO EXCLUIDO"
        c.endereco = None
        c.cidade = None
        c.uf = None
        c.foto_url = None
        c.comprovante_residencia_url = None
        c.documento_pessoal_url = None
        c.termo_imagem_url = None
        c.termo_lgpd_url = None
        c.status = "inativo"
        c.observacoes = (c.observacoes or "") + f"\n[LGPD] Exclusão lógica aplicada em {agora.isoformat()}; motivo={body.motivo}"
        c = atualizar_cadastro_sheets(c)
        registrar_auditoria(
            db,
            action="cadastro.lgpd.delete",
            entity_type="cadastro",
            entity_id=c.id,
            details=f"motivo={body.motivo}",
            actor=atual,
            ip_address=request.client.host if request.client else None,
        )
        return _montar_saida_cadastro(db, c)

    lgpd = _obter_ou_criar_lgpd(db, c.id)
    agora = datetime.now(timezone.utc)
    referencia = agora if lgpd.retencao_ate and lgpd.retencao_ate.tzinfo else agora.replace(tzinfo=None)
    if lgpd.retencao_ate and lgpd.retencao_ate > referencia:
        raise HTTPException(status_code=400, detail="Prazo de retenção ainda não expirou")

    c.nome = "DADO EXCLUIDO"
    c.nome_social = None
    c.rg = None
    c.orgao_expedidor = None
    c.email = None
    c.telefone = "DADO EXCLUIDO"
    c.endereco = None
    c.cidade = None
    c.uf = None
    c.foto_url = None
    c.comprovante_residencia_url = None
    c.documento_pessoal_url = None
    c.termo_imagem_url = None
    c.termo_lgpd_url = None
    c.status = "inativo"
    c.observacoes = (c.observacoes or "") + f"\n[LGPD] Exclusão lógica aplicada em {agora.isoformat()}"

    lgpd.excluido_em = agora
    lgpd.motivo_exclusao = body.motivo
    lgpd.status_lgpd = "revogado"

    db.commit()
    registrar_auditoria(
        db,
        action="cadastro.lgpd.delete",
        entity_type="cadastro",
        entity_id=c.id,
        details=f"motivo={body.motivo}",
        actor=atual,
        ip_address=request.client.host if request.client else None,
    )
    return _montar_saida_cadastro(db, c)
