from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.exc import UnknownHashError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.usuario import Usuario
from app.services.sheets_usuarios import buscar_usuario_sheets, usuarios_sheets_enabled

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def _get_token_from_header_or_cookie(request: Request) -> str:
    # Prefer Authorization header, fall back to cookie named 'access_token'
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1]
    token = request.cookies.get("access_token")
    if token:
        return token
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash: str) -> bool:
    try:
        return pwd_context.verify(senha, hash)
    except UnknownHashError:
        return False


def criar_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def criar_token_redefinicao(email: str) -> str:
    payload = {
        "sub": email,
        "typ": "password_reset",
        "exp": datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def validar_token_redefinicao(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("typ") != "password_reset":
            raise ValueError("Tipo de token invalido")
        email = payload.get("sub")
        if not email:
            raise ValueError("Token sem e-mail")
        return email
    except JWTError as exc:
        raise ValueError("Token invalido ou expirado") from exc


def usuario_atual(token: str = Depends(_get_token_from_header_or_cookie), db: Session = Depends(get_db)) -> Usuario:
    erro = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise erro
    except JWTError:
        raise erro
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if (not usuario or not getattr(usuario, "senha_hash", None) or not getattr(usuario, "perfil", None)) and usuarios_sheets_enabled():
        usuario = buscar_usuario_sheets(email=email)
    if not usuario or not getattr(usuario, "senha_hash", None) or not getattr(usuario, "perfil", None):
        usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise erro
    return usuario


def requer_perfil(*perfis: str):
    def verificar(usuario: Usuario = Depends(usuario_atual)):
        if usuario.perfil not in perfis:
            raise HTTPException(status_code=403, detail="Sem permissão")
        return usuario
    return verificar
