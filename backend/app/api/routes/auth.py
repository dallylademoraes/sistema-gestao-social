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
    TrocaSenhaSchema,
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


@router.put("/password/change")
def trocar_senha(
    body: TrocaSenhaSchema,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    if not verificar_senha(body.senha_atual, usuario.senha_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta.")

    if len(body.nova_senha) < 8:
        raise HTTPException(
            status_code=400, detail="A nova senha deve ter pelo menos 8 caracteres."
        )

    senha_hash = hash_senha(body.nova_senha)
    usuario_db = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if usuario_db:
        usuario_db.senha_hash = senha_hash
        usuario_db.precisa_trocar_senha = False
        db.commit()

    if _usuarios_em_planilha():
        usuario_planilha = buscar_usuario_sheets(email=usuario.email)
        if usuario_planilha and usuario_planilha.id:
            atualizar_usuario_sheets(
                int(usuario_planilha.id),
                {"senha_hash": senha_hash, "precisa_trocar_senha": False},
            )

    if not usuario_db:
        usuario.senha_hash = senha_hash
        usuario.precisa_trocar_senha = False
        db.commit()

    return {"detail": "Senha alterada com sucesso."}


def _garantir_coordenadora(usuario: Usuario) -> None:
    if usuario.perfil != "coordenadora":
        raise HTTPException(
            status_code=403, detail="Apenas coordenadora pode gerenciar usuários"
        )



def _usuarios_em_planilha() -> bool:
    return usuarios_sheets_enabled()


def _usuario_valido_para_login(usuario) -> bool:
    return bool(usuario and getattr(usuario, "senha_hash", None) and getattr(usuario, "email", None))


def _contar_coordenadoras_ativas(db: Session) -> int:
    if _usuarios_em_planilha():
        return contar_coordenadoras_ativas_sheets()
    return db.query(Usuario).filter(and_(Usuario.perfil == "coordenadora", Usuario.ativo.is_(True))).count()


def _buscar_usuario_por_id_ou_email(db: Session, usuario_id: int) -> tuple[Optional[Usuario], object | None]:
    usuario_db = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    usuario_planilha = None
    if _usuarios_em_planilha():
        usuario_planilha = buscar_usuario_sheets(usuario_id=usuario_id)
        if usuario_planilha and getattr(usuario_planilha, "email", None):
            usuario_db = (
                db.query(Usuario)
                .filter(Usuario.email == usuario_planilha.email)
                .first()
            ) or usuario_db
    return usuario_db, usuario_planilha


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


@router.post("/token", response_model=Token)
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

    usuario = None

    usuario_db = db.query(Usuario).filter(Usuario.email == email).first()
    if _usuario_valido_para_login(usuario_db) and verificar_senha(form.password, usuario_db.senha_hash):
        usuario = usuario_db
    elif _usuarios_em_planilha():
        usuario_planilha = buscar_usuario_sheets(email=email)
        if _usuario_valido_para_login(usuario_planilha) and verificar_senha(form.password, usuario_planilha.senha_hash):
            usuario = usuario_planilha

    if not usuario:
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
    return {
        "access_token": token,
        "token_type": "bearer",
        "precisa_trocar_senha": usuario.precisa_trocar_senha,
    }


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

    # 4. Envia e-mail de boas-vindas — falha aqui não derruba a criação do usuário,
    # mas registramos o resultado na auditoria para não perder o rastro do problema.
    from app.services.email_sender import enviar_email_conta_criada

    email_enviado = enviar_email_conta_criada(
        destinatario=u.email,
        nome_pessoa=u.nome,
        email_login=u.email,
        senha_temporaria=body.senha,
    )

    # 5. Salva na planilha como complemento
    if _usuarios_em_planilha():
        # FIXME: O hash da senha está sendo recalculado aqui, o que é desnecessário.
        # Idealmente, o hash gerado para o banco de dados deveria ser reutilizado.
        criar_usuario_sheets(
            {
                "id": u.id,
                "nome": u.nome,
                "email": u.email,
                "senha_hash": u.senha_hash,
                "perfil": u.perfil,
                "ativo": u.ativo,
                "criado_em": u.criado_em,
                "atualizado_em": u.atualizado_em,
                "precisa_trocar_senha": u.precisa_trocar_senha,
            }
        )

    registrar_auditoria(
        db,
        action="user.create",
        entity_type="usuario",
        entity_id=u.id,
        details=f"perfil={u.perfil};email={u.email};email_enviado={email_enviado}",
        actor=atual,
        ip_address=request.client.host if request.client else None,
    )

    if not email_enviado:
        # Usuário já foi criado com sucesso (201). Isso é só um aviso lateral —
        # o frontend pode usar esse header pra mostrar "copie a senha temporária".
        request.state.email_falhou = True

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

    alvo, alvo_planilha = _buscar_usuario_por_id_ou_email(db, usuario_id)
    if not dados:
        if not alvo and not alvo_planilha:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        return alvo or alvo_planilha

    if not alvo and not alvo_planilha:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    alvo_email = getattr(alvo_planilha, "email", None) or getattr(alvo, "email", None)
    alvo_id_db = getattr(alvo, "id", None)
    alvo_perfil = getattr(alvo, "perfil", None) or getattr(alvo_planilha, "perfil", None)
    alvo_ativo = getattr(alvo, "ativo", None)
    if alvo_ativo is None:
        alvo_ativo = getattr(alvo_planilha, "ativo", True)

    # Verifica duplicidade de email
    if "email" in dados and dados["email"] != alvo_email:
        q = db.query(Usuario).filter(Usuario.email == dados["email"])
        if alvo_id_db:
            q = q.filter(Usuario.id != alvo_id_db)
        if q.first():
            raise HTTPException(status_code=400, detail="E-mail já cadastrado no banco")
        existente_planilha = buscar_usuario_sheets(email=dados["email"]) if _usuarios_em_planilha() else None
        if existente_planilha and int(existente_planilha.id or 0) != int(usuario_id):
            raise HTTPException(status_code=400, detail="E-mail já cadastrado na planilha")

    perfil_novo = dados.get("perfil", alvo_perfil)
    ativo_novo = dados.get("ativo", alvo_ativo)
    era_coordenadora_ativa = alvo_perfil == "coordenadora" and alvo_ativo
    continuara_coordenadora_ativa = perfil_novo == "coordenadora" and ativo_novo

    # Regras de negócio usando os dados do banco
    if alvo_email and alvo_email == atual.email:
        if "ativo" in dados and dados["ativo"] is False:
            raise HTTPException(status_code=400, detail="Não é permitido desativar seu próprio usuário")
        if "perfil" in dados and dados["perfil"] != atual.perfil:
            raise HTTPException(status_code=400, detail="Não é permitido alterar seu próprio perfil")

    if era_coordenadora_ativa and not continuara_coordenadora_ativa and _contar_coordenadoras_ativas(db) <= 1:
        raise HTTPException(status_code=400, detail="Não é permitido remover a última coordenadora ativa")

    # Aplica as atualizações no banco (incluindo a nova senha)
    if alvo:
        for campo, valor in dados.items():
            setattr(alvo, campo, valor)
        db.commit()
        db.refresh(alvo)

    # Aplica as mesmas atualizações na planilha, incluindo o `atualizado_em`
    retorno = alvo
    if _usuarios_em_planilha() and alvo_planilha:
        dados_para_planilha = dados.copy()
        if alvo:
            dados_para_planilha["atualizado_em"] = alvo.atualizado_em
        atualizar_usuario_sheets(int(alvo_planilha.id), dados_para_planilha)
        alvo_planilha = buscar_usuario_sheets(usuario_id=int(alvo_planilha.id))
        if alvo_planilha:
            retorno = alvo_planilha

    registrar_auditoria(
        db,
        action="user.update",
        entity_type="usuario",
        entity_id=alvo_id_db or usuario_id,
        details=f"campos={','.join(sorted(dados.keys()))}",
        actor=atual,
        ip_address=request.client.host if request.client else None,
    )
    return retorno


@router.delete("/usuarios/{usuario_id}")
def excluir_usuario(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(usuario_atual),
):
    _garantir_coordenadora(atual)

    alvo, alvo_planilha = _buscar_usuario_por_id_ou_email(db, usuario_id)
    if not alvo and not alvo_planilha:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    alvo_email = getattr(alvo_planilha, "email", None) or getattr(alvo, "email", None)
    alvo_perfil = getattr(alvo, "perfil", None) or getattr(alvo_planilha, "perfil", None)
    alvo_id_db = getattr(alvo, "id", None)

    if alvo_email and alvo_email == atual.email:
        raise HTTPException(status_code=400, detail="Não é permitido excluir seu próprio usuário")
        
    if alvo_perfil == "coordenadora" and _contar_coordenadoras_ativas(db) <= 1:
        raise HTTPException(status_code=400, detail="Não é permitido remover a última coordenadora ativa")

    # Exclui no banco de dados
    if alvo:
        db.delete(alvo)
        db.commit()

    # Exclui na planilha
    if _usuarios_em_planilha() and alvo_planilha:
        from app.services.sheets_usuarios import excluir_usuario_sheets
        excluir_usuario_sheets(int(alvo_planilha.id))

    registrar_auditoria(
        db,
        action="user.delete",
        entity_type="usuario",
        entity_id=alvo_id_db or usuario_id,
        details=f"email={alvo_email}",
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