from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    perfil: str = "assistente"


class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: str
    perfil: str
    ativo: bool
    criado_em: datetime
    precisa_trocar_senha: bool

    model_config = {"from_attributes": True}


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    perfil: Optional[str] = None
    ativo: Optional[bool] = None
    nova_senha: Optional[str] = None


class AuditLogOut(BaseModel):
    id: int
    actor_user_id: Optional[int] = None
    actor_nome: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_em: datetime

    model_config = {"from_attributes": True}


class AuditLogPage(BaseModel):
    items: list[AuditLogOut]
    total: int
    skip: int
    limit: int


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    precisa_trocar_senha: bool


class TokenData(BaseModel):
    email: Optional[str] = None


class PasswordForgotRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    nova_senha: str

class TrocaSenhaSchema(BaseModel):
    senha_atual: str
    nova_senha: str


class PasswordForgotResponse(BaseModel):
    message: str
    reset_url: Optional[str] = None
    reset_token: Optional[str] = None
