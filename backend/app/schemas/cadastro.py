from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date, datetime


class CadastroCreate(BaseModel):
    nome: str
    nome_social: Optional[str] = None
    cpf: str
    rg: Optional[str] = None
    orgao_expedidor: Optional[str] = None
    data_nascimento: date
    email: Optional[EmailStr] = None
    telefone: str
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    estado_civil: Optional[str] = None
    cor_raca: Optional[str] = None
    identidade_genero: Optional[str] = None
    pcd: bool = False
    renda_media: Optional[str] = None
    com_encaminhamento: bool = False
    encaminhamento_realizado: bool = False
    observacoes: Optional[str] = None


class CadastroUpdate(CadastroCreate):
    nome: Optional[str] = None
    cpf: Optional[str] = None
    data_nascimento: Optional[date] = None
    telefone: Optional[str] = None
    status: Optional[str] = None


class CadastroLGPDUpdate(BaseModel):
    base_legal: Optional[str] = None
    status_lgpd: Optional[str] = None
    retencao_ate: Optional[datetime] = None


class ConsentimentoLGPDCreate(BaseModel):
    tipo: str  # concedido | revogado
    base_legal: str = "consentimento"
    observacao: Optional[str] = None


class ConsentimentoLGPDOut(BaseModel):
    id: int
    cadastro_id: int
    tipo: str
    base_legal: str
    observacao: Optional[str] = None
    registrado_por_id: Optional[int] = None
    criado_em: datetime

    model_config = {"from_attributes": True}


class ExcluirCadastroPayload(BaseModel):
    motivo: str


class CadastroOut(CadastroCreate):
    id: int
    status: str
    lgpd_concluido: bool = False
    criado_em: datetime
    foto_url: Optional[str] = None
    comprovante_residencia_url: Optional[str] = None
    documento_pessoal_url: Optional[str] = None
    termo_imagem_url: Optional[str] = None
    termo_lgpd_url: Optional[str] = None
    base_legal: Optional[str] = None
    status_lgpd: str = "pendente"
    retencao_ate: Optional[datetime] = None
    excluido_em: Optional[datetime] = None
    motivo_exclusao: Optional[str] = None
    consentimentos: list[ConsentimentoLGPDOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}
