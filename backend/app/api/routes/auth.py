from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Response
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import and_
from datetime import datetime, timedelta, timezone
import io
import csv

from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.usuario import (
    Token,
    UsuarioCreate,
    UsuarioOut,
    UsuarioUpdate,
    AuditLogOut,
    AuditLogPage,
    PasswordForgotRequest,
    PasswordForgotResponse,
    PasswordResetConfirm,
)
from app.core.config import settings
from app.core.security import (
    hash_senha,
    verificar_senha,
    criar_token,
    usuario_atual,
    criar_token_redefinicao,
    validar_token_redefinicao,
)
from app.models.audit_log import AuditLog
from app.models.login_throttle import LoginThrottle
from app.services.audit import registrar_auditoria
from app.services.sheets_usuarios import (
    buscar_usuario_sheets,
    contar_coordenadoras_ativas_sheets,
    criar_usuario_sheets,
    listar_usuarios_sheets,
    atualizar_usuario_sheets,
    usuarios_sheets_enabled,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _garantir_coordenadora(usuario: Usuario) -> None:
    if usuario.perfil != "coordenadora":
        raise HTTPException(status_code=403, detail="Apenas coordenadora pode gerenciar usuários")


def _usuarios_em_planilha() -> bool:
    return usuarios_sheets_enabled()


def _usuario_valido_para_login(usuario) -> bool:
    return bool(usuario and getattr(usuario, "senha_hash", None) and getattr(usuario, "email", None))


def _contar_coordenadoras_ativas(db: Session) -> int:
    return db.query(Usuario).filter(and_(Usuario.perfil == "coordenadora", Usuario.ativo.is_(True))).count()


def _query_auditoria(
    db: Session,
    action: Optional[str] = None,
    usuario: Optional[str] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    if usuario:
        termo = f"%{usuario.strip()}%"
        q = q.filter(AuditLog.actor_nome.ilike(termo))
    if data_inicio:
        q = q.filter(AuditLog.created_em >= data_inicio)
    if data_fim:
        q = q.filter(AuditLog.created_em <= data_fim)
    return q


def _acao_legivel(action: str) -> str:
    mapa = {
        "user.create": "Usuario criado",
        "user.update": "Usuario atualizado",
        "cadastro.create": "Cadastro criado",
        "cadastro.update": "Cadastro atualizado",
        "cadastro.approve": "Cadastro aprovado",
        "cadastro.delete": "Cadastro excluido",
    }
    return mapa.get(action, action)


def _login_key(prefixo: str, valor: Optional[str]) -> str:
    return f"{prefixo}:{(valor or 'desconhecido').strip().lower()}"


def _utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """SQLite devolve DateTime sem tzinfo; unifica com agora em UTC para comparacoes."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _throttle_atual(db: Session, identifier: str) -> LoginThrottle:
    row = db.query(LoginThrottle).filter(LoginThrottle.identifier == identifier).first()
    if not row:
        row = LoginThrottle(identifier=identifier, attempts=0)
        db.add(row)
        db.flush()
    return row


def _limpar_throttle(db: Session, identifier: str) -> None:
    row = db.query(LoginThrottle).filter(LoginThrottle.identifier == identifier).first()
    if row:
        db.delete(row)


def _bloqueio_ativo(row: LoginThrottle, agora: datetime) -> Optional[int]:
    locked = _utc_aware(row.locked_until)
    if locked and locked > agora:
        return max(1, int((locked - agora).total_seconds()))
    return None


def _registrar_falha_login(db: Session, identifier: str, agora: datetime) -> None:
    janela_minutos = int(getattr(settings, "LOGIN_RATE_LIMIT_WINDOW_MINUTES", 10))
    max_tentativas = int(getattr(settings, "LOGIN_MAX_ATTEMPTS", 5))
    bloqueio_minutos = int(getattr(settings, "LOGIN_LOCK_MINUTES", 15))

    row = _throttle_atual(db, identifier)
    janela_inicio = _utc_aware(row.window_start)
    if janela_inicio is None or (agora - janela_inicio) > timedelta(minutes=janela_minutos):
        row.attempts = 0
        row.window_start = agora

    row.attempts += 1
    row.last_attempt_at = agora
    if row.attempts >= max_tentativas:
        row.locked_until = agora + timedelta(minutes=bloqueio_minutos)
    db.flush()


def _auth_cookie_options() -> dict:
    secure_cookie = settings.FRONTEND_URL.startswith("https://")
    return {
        "httponly": True,
        "secure": secure_cookie,
        "samesite": "none" if secure_cookie else "lax",
        "path": "/",
    }


@router.post("/token")
def login(request: Request, response: Response, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    agora = datetime.now(timezone.utc)
    email = form.username.strip().lower()
    ip = request.client.host if request.client else None
    chaves = [_login_key("email", email), _login_key("ip", ip)]

    for chave in chaves:
        row = db.query(LoginThrottle).filter(LoginThrottle.identifier == chave).first()
        if row:
            bloqueio = _bloqueio_ativo(row, agora)
            if bloqueio:
                raise HTTPException(
                    status_code=429,
                    detail=f"Muitas tentativas. Tente novamente em {max(1, (bloqueio + 59) // 60)} minuto(s)",
                    headers={"Retry-After": str(bloqueio), "X-RateLimit-Reset": str(bloqueio)},
                )

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not _usuario_valido_para_login(usuario) and _usuarios_em_planilha():
        usuario = buscar_usuario_sheets(email=email)
    if not _usuario_valido_para_login(usuario):
        usuario = None
    if not usuario or not verificar_senha(form.password, usuario.senha_hash):
        for chave in chaves:
            _registrar_falha_login(db, chave, agora)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Usuário inativo")
    for chave in chaves:
        _limpar_throttle(db, chave)
    db.commit()
    token = criar_token({"sub": usuario.email, "perfil": usuario.perfil})
    response.set_cookie(
        key="access_token",
        value=token,
        max_age=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60,
        **_auth_cookie_options(),
    )
    return {"message": "ok"}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token", **_auth_cookie_options())
    return {"message": "logged out"}


@router.post("/usuarios", response_model=UsuarioOut, status_code=201)
def criar_usuario(body: UsuarioCreate, request: Request, db: Session = Depends(get_db), atual: Usuario = Depends(usuario_atual)):
    _garantir_coordenadora(atual)
    
    # 1. Verifica no banco se já existe
    if db.query(Usuario).filter(Usuario.email == body.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado no banco")
        
    # 2. Verifica na planilha (se ativada)
    if _usuarios_em_planilha() and buscar_usuario_sheets(email=body.email):
        raise HTTPException(status_code=400, detail="E-mail já cadastrado na planilha")

    # 3. Sempre salva no banco de dados primeiro
    u = Usuario(
        nome=body.nome, 
        email=body.email,
        senha_hash=hash_senha(body.senha), 
        perfil=body.perfil
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    
    # 4. Salva na planilha como complemento
    if _usuarios_em_planilha():
        criar_usuario_sheets({
            "nome": body.nome,
            "email": body.email,
            "senha_hash": hash_senha(body.senha),
            "perfil": body.perfil,
            "ativo": True,
        })

    registrar_auditoria(
        db,
        action="user.create",
        entity_type="usuario",
        entity_id=u.id,
        details=f"perfil={u.perfil};email={u.email}",
        actor=atual,
        ip_address=request.client.host if request.client else None,
    )
    return u


@router.get("/usuarios", response_model=List[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db), atual: Usuario = Depends(usuario_atual)):
    _garantir_coordenadora(atual)
    if _usuarios_em_planilha():
        return listar_usuarios_sheets()
    return db.query(Usuario).order_by(Usuario.criado_em.desc()).all()


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioOut)
def atualizar_usuario(
    usuario_id: int,
    body: UsuarioUpdate,
    request: Request,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(usuario_atual),
):
    _garantir_coordenadora(atual)

    dados = body.model_dump(exclude_unset=True)
    if "nova_senha" in dados:
        senha_plana = dados.pop("nova_senha")
        dados["senha_hash"] = hash_senha(senha_plana)

    if not dados:
        alvo_db = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not alvo_db:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        return alvo_db

    # Busca obrigatoriamente no banco primeiro
    alvo = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not alvo:
        raise HTTPException(status_code=404, detail="Usuário não encontrado no banco de dados")

    # Verifica duplicidade de email
    if "email" in dados and dados["email"] != alvo.email:
        if db.query(Usuario).filter(and_(Usuario.email == dados["email"], Usuario.id != alvo.id)).first():
            raise HTTPException(status_code=400, detail="E-mail já cadastrado no banco")
        if _usuarios_em_planilha() and buscar_usuario_sheets(email=dados["email"]):
            raise HTTPException(status_code=400, detail="E-mail já cadastrado na planilha")

    perfil_novo = dados.get("perfil", alvo.perfil)
    ativo_novo = dados.get("ativo", alvo.ativo)
    era_coordenadora_ativa = alvo.perfil == "coordenadora" and alvo.ativo
    continuara_coordenadora_ativa = perfil_novo == "coordenadora" and ativo_novo

    # Regras de negócio usando os dados do banco
    if alvo.id == atual.id:
        if "ativo" in dados and dados["ativo"] is False:
            raise HTTPException(status_code=400, detail="Não é permitido desativar seu próprio usuário")
        if "perfil" in dados and dados["perfil"] != atual.perfil:
            raise HTTPException(status_code=400, detail="Não é permitido alterar seu próprio perfil")

    if era_coordenadora_ativa and not continuara_coordenadora_ativa and _contar_coordenadoras_ativas(db) <= 1:
        raise HTTPException(status_code=400, detail="Não é permitido remover a última coordenadora ativa")

    # Aplica as atualizações no banco (incluindo a nova senha)
    for campo, valor in dados.items():
        setattr(alvo, campo, valor)

    db.commit()
    db.refresh(alvo)

    # Aplica as mesmas atualizações na planilha
    if _usuarios_em_planilha():
        alvo_planilha = buscar_usuario_sheets(usuario_id=usuario_id)
        if alvo_planilha:
            atualizar_usuario_sheets(usuario_id, dados)

    registrar_auditoria(
        db,
        action="user.update",
        entity_type="usuario",
        entity_id=alvo.id,
        details=f"campos={','.join(sorted(dados.keys()))}",
        actor=atual,
        ip_address=request.client.host if request.client else None,
    )
    return alvo


@router.delete("/usuarios/{usuario_id}")
def excluir_usuario(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(usuario_atual),
):
    _garantir_coordenadora(atual)

    # Verifica no banco de dados primeiro
    alvo = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not alvo:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
    if alvo.id == atual.id:
        raise HTTPException(status_code=400, detail="Não é permitido excluir seu próprio usuário")
        
    if alvo.perfil == "coordenadora" and _contar_coordenadoras_ativas(db) <= 1:
        raise HTTPException(status_code=400, detail="Não é permitido remover a última coordenadora ativa")

    # Exclui no banco de dados
    db.delete(alvo)
    db.commit()

    # Exclui na planilha
    if _usuarios_em_planilha():
        alvo_planilha = buscar_usuario_sheets(usuario_id=usuario_id)
        if alvo_planilha:
            from app.services.sheets_usuarios import excluir_usuario_sheets
            excluir_usuario_sheets(usuario_id)

    registrar_auditoria(
        db,
        action="user.delete",
        entity_type="usuario",
        entity_id=usuario_id,
        details=f"email={alvo.email}",
        actor=atual,
        ip_address=request.client.host if request.client else None,
    )
    return {"message": "ok"}


@router.get("/auditoria", response_model=AuditLogPage)
def listar_auditoria(
    action: Optional[str] = Query(None),
    usuario: Optional[str] = Query(None),
    data_inicio: Optional[datetime] = Query(None),
    data_fim: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=300),
    db: Session = Depends(get_db),
    atual: Usuario = Depends(usuario_atual),
):
    _garantir_coordenadora(atual)

    q = _query_auditoria(db, action=action, usuario=usuario, data_inicio=data_inicio, data_fim=data_fim)
    total = q.count()
    items = q.order_by(AuditLog.created_em.desc()).offset(skip).limit(limit).all()
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/auditoria/export")
def exportar_auditoria_csv(
    action: Optional[str] = Query(None),
    usuario: Optional[str] = Query(None),
    data_inicio: Optional[datetime] = Query(None),
    data_fim: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    atual: Usuario = Depends(usuario_atual),
):
    _garantir_coordenadora(atual)

    logs = _query_auditoria(db, action=action, usuario=usuario, data_inicio=data_inicio, data_fim=data_fim)\
        .order_by(AuditLog.created_em.desc())\
        .all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "registro_id",
        "data_hora",
        "usuario_id",
        "usuario_nome",
        "acao_codigo",
        "acao_descricao",
        "entidade_tipo",
        "entidade_id",
        "detalhes",
        "ip_origem",
    ])
    for l in logs:
        writer.writerow([
            l.id,
            l.created_em.isoformat() if l.created_em else "",
            l.actor_user_id or "",
            l.actor_nome or "",
            l.action,
            _acao_legivel(l.action),
            l.entity_type,
            l.entity_id or "",
            l.details or "",
            l.ip_address or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=auditoria.csv"},
    )


@router.get("/me", response_model=UsuarioOut)
def me(usuario: Usuario = Depends(usuario_atual)):
    return usuario


@router.post("/password/forgot", response_model=PasswordForgotResponse)
def forgot_password(body: PasswordForgotRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == body.email).first()

    response = PasswordForgotResponse(
        message="Se o e-mail existir, enviaremos as instrucoes de redefinicao.",
    )

    if not usuario or not usuario.ativo:
        return response

    token = criar_token_redefinicao(usuario.email)
    reset_url = f"{settings.FRONTEND_URL}/redefinir-senha?token={token}"

    if settings.RETURN_PASSWORD_RESET_TOKEN_IN_RESPONSE:
        response.reset_token = token
        response.reset_url = reset_url

    return response


@router.post("/password/reset")
def reset_password(body: PasswordResetConfirm, db: Session = Depends(get_db)):
    if len(body.nova_senha) < 8:
        raise HTTPException(status_code=400, detail="A nova senha deve ter pelo menos 8 caracteres")

    try:
        email = validar_token_redefinicao(body.token)
    except ValueError:
        raise HTTPException(status_code=400, detail="Token invalido ou expirado")

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    usuario.senha_hash = hash_senha(body.nova_senha)
    db.commit()
    return {"message": "Senha redefinida com sucesso"}