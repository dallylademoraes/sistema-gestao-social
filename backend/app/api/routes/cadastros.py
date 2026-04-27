from datetime import date, datetime, timezone
import os
import re
import shutil
import uuid
import mimetypes
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.session import get_db
from app.models.cadastro import Cadastro
from app.models.cadastro_lgpd import CadastroLGPD
from app.models.consentimento_lgpd import ConsentimentoLGPD
from app.models.usuario import Usuario
from app.schemas.cadastro import (
    CadastroCreate,
    CadastroUpdate,
    CadastroOut,
    CadastroLGPDUpdate,
    ConsentimentoLGPDCreate,
    ConsentimentoLGPDOut,
    ExcluirCadastroPayload,
)
from app.core.security import usuario_atual, requer_perfil
from app.services.pdf import gerar_pdf_cadastro
from app.services.audit import registrar_auditoria
from app.services.arquivos import (
    validar_arquivo_upload,
    salvar_arquivo_externo,
    gerar_url_assinada_download,
    verificar_token_download,
    responder_download,
)

router = APIRouter(prefix="/cadastros", tags=["cadastros"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

STATUS_VALIDOS = {"pendente", "ativo", "inativo"}
STATUS_LGPD_VALIDOS = {"pendente", "consentido", "revogado"}


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


def _formatar_cpf(cpf: str) -> str:
    digits = _somente_digitos(cpf)
    return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"


def _idade_em_anos(data_nascimento: date) -> int:
    hoje = date.today()
    return hoje.year - data_nascimento.year - (
        (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day)
    )


def _validar_data_nascimento(data_nascimento: date) -> None:
    if data_nascimento > date.today():
        raise HTTPException(status_code=400, detail="Data de nascimento não pode ser futura")
    if data_nascimento.year < 1900:
        raise HTTPException(status_code=400, detail="Data de nascimento inválida")
    if _idade_em_anos(data_nascimento) > 120:
        raise HTTPException(status_code=400, detail="Idade inválida")


def _validar_status(status: str) -> None:
    if status not in STATUS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Status inválido. Use: {sorted(STATUS_VALIDOS)}")


def _obter_ou_criar_lgpd(db: Session, cadastro_id: int) -> CadastroLGPD:
    lgpd = db.query(CadastroLGPD).filter(CadastroLGPD.cadastro_id == cadastro_id).first()
    if not lgpd:
        lgpd = CadastroLGPD(cadastro_id=cadastro_id, base_legal="consentimento", status_lgpd="pendente")
        db.add(lgpd)
        db.flush()
    return lgpd


def _obter_lgpd(db: Session, cadastro_id: int) -> Optional[CadastroLGPD]:
    return db.query(CadastroLGPD).filter(CadastroLGPD.cadastro_id == cadastro_id).first()


def _listar_consentimentos(db: Session, cadastro_id: int) -> list[ConsentimentoLGPD]:
    return (
        db.query(ConsentimentoLGPD)
        .filter(ConsentimentoLGPD.cadastro_id == cadastro_id)
        .order_by(ConsentimentoLGPD.criado_em.desc())
        .all()
    )


def _validar_requisitos_aprovacao(cadastro: Cadastro, lgpd: CadastroLGPD) -> None:
    docs_obrigatorios = {
        "foto": cadastro.foto_url,
        "comprovante de residência": cadastro.comprovante_residencia_url,
        "documento pessoal": cadastro.documento_pessoal_url,
        "termo LGPD": cadastro.termo_lgpd_url,
    }
    faltantes = [nome for nome, valor in docs_obrigatorios.items() if not valor]
    if faltantes:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível aprovar sem os documentos: {', '.join(faltantes)}",
        )
    if not cadastro.telefone or not cadastro.nome:
        raise HTTPException(status_code=400, detail="Dados básicos incompletos para aprovação")
    if not _cpf_valido(cadastro.cpf):
        raise HTTPException(status_code=400, detail="CPF inválido")
    _validar_data_nascimento(cadastro.data_nascimento)
    if _idade_em_anos(cadastro.data_nascimento) < 16:
        raise HTTPException(status_code=400, detail="Idade mínima para aprovação é 16 anos")
    if not lgpd.base_legal:
        raise HTTPException(status_code=400, detail="Base legal LGPD obrigatória para aprovação")
    if lgpd.status_lgpd != "consentido":
        raise HTTPException(status_code=400, detail="Não é possível aprovar sem consentimento LGPD ativo")


def _montar_saida_cadastro(db: Session, cadastro: Cadastro) -> CadastroOut:
    lgpd = _obter_lgpd(db, cadastro.id)
    consentimentos = _listar_consentimentos(db, cadastro.id)

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
        lgpd_concluido=bool(cadastro.termo_lgpd_url) and (lgpd.status_lgpd == "consentido" if lgpd else False),
        criado_em=cadastro.criado_em,
        foto_url=url_documento("foto", cadastro.foto_url),
        comprovante_residencia_url=url_documento("comprovante", cadastro.comprovante_residencia_url),
        documento_pessoal_url=url_documento("documento", cadastro.documento_pessoal_url),
        termo_imagem_url=url_documento("termo_imagem", cadastro.termo_imagem_url),
        termo_lgpd_url=url_documento("termo_lgpd", cadastro.termo_lgpd_url),
        base_legal=lgpd.base_legal if lgpd else None,
        status_lgpd=lgpd.status_lgpd if lgpd else "pendente",
        retencao_ate=lgpd.retencao_ate if lgpd else None,
        excluido_em=lgpd.excluido_em if lgpd else None,
        motivo_exclusao=lgpd.motivo_exclusao if lgpd else None,
        consentimentos=[ConsentimentoLGPDOut.model_validate(i) for i in consentimentos],
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
        if lgpd_concluido:
            q = q.filter(and_(Cadastro.termo_lgpd_url.is_not(None), Cadastro.termo_lgpd_url != ""))
        else:
            q = q.filter((Cadastro.termo_lgpd_url.is_(None)) | (Cadastro.termo_lgpd_url == ""))
    itens = q.order_by(Cadastro.criado_em.desc()).offset(skip).limit(limit).all()
    return [_montar_saida_cadastro(db, c) for c in itens]


@router.post("/", response_model=CadastroOut, status_code=201)
def criar(body: CadastroCreate, request: Request, db: Session = Depends(get_db),
          atual: Usuario = Depends(requer_perfil("coordenadora", "assistente"))):
    if not _cpf_valido(body.cpf):
        raise HTTPException(status_code=400, detail="CPF inválido")
    _validar_data_nascimento(body.data_nascimento)
    cpf_formatado = _formatar_cpf(body.cpf)
    if db.query(Cadastro).filter(Cadastro.cpf.in_([cpf_formatado, _somente_digitos(body.cpf), body.cpf])).first():
        raise HTTPException(status_code=400, detail="CPF já cadastrado")
    dados = body.model_dump()
    dados["cpf"] = cpf_formatado
    c = Cadastro(**dados)
    db.add(c)
    db.commit()
    db.refresh(c)
    _obter_ou_criar_lgpd(db, c.id)
    db.commit()
    registrar_auditoria(
        db,
        action="cadastro.create",
        entity_type="cadastro",
        entity_id=c.id,
        details=f"cpf={c.cpf};status={c.status}",
        actor=atual,
        ip_address=request.client.host if request.client else None,
    )
    return _montar_saida_cadastro(db, c)


@router.get("/{id}", response_model=CadastroOut)
def buscar(id: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    c = db.query(Cadastro).filter(Cadastro.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Não encontrado")
    return _montar_saida_cadastro(db, c)


@router.patch("/{id}", response_model=CadastroOut)
def atualizar(id: int, body: CadastroUpdate, request: Request, db: Session = Depends(get_db),
              atual: Usuario = Depends(requer_perfil("coordenadora", "assistente"))):
    c = db.query(Cadastro).filter(Cadastro.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Não encontrado")
    dados = body.model_dump(exclude_unset=True)
    if "cpf" in dados:
        if not _cpf_valido(dados["cpf"]):
            raise HTTPException(status_code=400, detail="CPF inválido")
        cpf_formatado = _formatar_cpf(dados["cpf"])
        existente = db.query(Cadastro).filter(Cadastro.cpf.in_([cpf_formatado, _somente_digitos(dados["cpf"]), dados["cpf"]])).first()
        if existente and existente.id != c.id:
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


@router.post("/{id}/aprovar", response_model=CadastroOut)
def aprovar(id: int, request: Request, db: Session = Depends(get_db),
            usuario: Usuario = Depends(requer_perfil("coordenadora", "ti"))):
    c = db.query(Cadastro).filter(Cadastro.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Não encontrado")
    lgpd = _obter_ou_criar_lgpd(db, c.id)
    _validar_requisitos_aprovacao(c, lgpd)
    c.status = "ativo"
    c.aprovado_por_id = usuario.id
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
    c = db.query(Cadastro).filter(Cadastro.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Nao encontrado")
    cadastro_id = c.id
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
    c = db.query(Cadastro).filter(Cadastro.id == id).first()
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
        "termo_imagem": "termo_imagem_url",
        "termo_lgpd": "termo_lgpd_url",
    }
    if tipo not in campos_validos:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Use: {list(campos_validos)}")
    c = db.query(Cadastro).filter(Cadastro.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Não encontrado")
    arquivo_seguro, conteúdo = await validar_arquivo_upload(tipo, arquivo)
    caminho = salvar_arquivo_externo(arquivo_seguro.storage_ref, conteúdo, arquivo_seguro.content_type)
    setattr(c, campos_validos[tipo], caminho)
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
    c = db.query(Cadastro).filter(Cadastro.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Não encontrado")

    storage_ref = verificar_token_download(token, id, tipo)
    if getattr(c, campos_validos[tipo]) != storage_ref:
        raise HTTPException(status_code=401, detail="Token de download não confere com o arquivo atual")

    content_type = mimetypes.guess_type(storage_ref)[0] or "application/octet-stream"
    filename = os.path.basename(storage_ref)
    return responder_download(storage_ref, filename, content_type)


@router.patch("/{id}/lgpd", response_model=CadastroOut)
def atualizar_lgpd(
    id: int,
    body: CadastroLGPDUpdate,
    request: Request,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(requer_perfil("coordenadora", "assistente")),
):
    c = db.query(Cadastro).filter(Cadastro.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Não encontrado")

    lgpd = _obter_ou_criar_lgpd(db, c.id)
    dados = body.model_dump(exclude_unset=True)
    if "status_lgpd" in dados and dados["status_lgpd"] not in STATUS_LGPD_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Status LGPD inválido. Use: {sorted(STATUS_LGPD_VALIDOS)}")

    for campo, valor in dados.items():
        setattr(lgpd, campo, valor)

    db.commit()
    registrar_auditoria(
        db,
        action="cadastro.lgpd.update",
        entity_type="cadastro",
        entity_id=c.id,
        details=f"campos={','.join(sorted(dados.keys()))}",
        actor=atual,
        ip_address=request.client.host if request.client else None,
    )
    return _montar_saida_cadastro(db, c)


@router.get("/{id}/lgpd/consentimentos", response_model=List[ConsentimentoLGPDOut])
def listar_consentimentos(
    id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
):
    c = db.query(Cadastro).filter(Cadastro.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Não encontrado")
    return _listar_consentimentos(db, c.id)


@router.post("/{id}/lgpd/consentimentos", response_model=CadastroOut)
def registrar_consentimento(
    id: int,
    body: ConsentimentoLGPDCreate,
    request: Request,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(requer_perfil("coordenadora", "assistente")),
):
    c = db.query(Cadastro).filter(Cadastro.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Não encontrado")
    if body.tipo not in {"concedido", "revogado"}:
        raise HTTPException(status_code=400, detail="Tipo inválido. Use: concedido ou revogado")

    lgpd = _obter_ou_criar_lgpd(db, c.id)
    evento = ConsentimentoLGPD(
        cadastro_id=c.id,
        tipo=body.tipo,
        base_legal=body.base_legal,
        observacao=body.observacao,
        registrado_por_id=atual.id,
    )
    db.add(evento)

    lgpd.base_legal = body.base_legal
    lgpd.status_lgpd = "consentido" if body.tipo == "concedido" else "revogado"

    db.commit()
    registrar_auditoria(
        db,
        action="cadastro.lgpd.consent",
        entity_type="cadastro",
        entity_id=c.id,
        details=f"tipo={body.tipo};base_legal={body.base_legal}",
        actor=atual,
        ip_address=request.client.host if request.client else None,
    )
    return _montar_saida_cadastro(db, c)


@router.post("/{id}/lgpd/excluir", response_model=CadastroOut)
def excluir_por_politica_lgpd(
    id: int,
    body: ExcluirCadastroPayload,
    request: Request,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(requer_perfil("coordenadora")),
):
    c = db.query(Cadastro).filter(Cadastro.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Não encontrado")

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
