from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.usuario import Usuario

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash: str) -> bool:
    return pwd_context.verify(senha, hash)


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


def usuario_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Usuario:
    erro = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise erro
    except JWTError:
        raise erro
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
