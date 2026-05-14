from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional, Literal
from datetime import date, datetime


class CadastroDadosBase(BaseModel):
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


class CadastroCreate(CadastroDadosBase):
    aceite_termo_lgpd: bool = False
    aceite_termo_imagem: bool = False
    assinatura_base64: str = Field(..., min_length=24, description="PNG em base64 ou data URL")

    @model_validator(mode="after")
    def exigir_aceites(self):
        if not self.aceite_termo_lgpd or not self.aceite_termo_imagem:
            raise ValueError("É obrigatório aceitar o Termo LGPD e o Termo de uso de imagem")
        return self


class CadastroUpdate(BaseModel):
    nome: Optional[str] = None
    nome_social: Optional[str] = None
    cpf: Optional[str] = None
    rg: Optional[str] = None
    orgao_expedidor: Optional[str] = None
    data_nascimento: Optional[date] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    estado_civil: Optional[str] = None
    cor_raca: Optional[str] = None
    identidade_genero: Optional[str] = None
    pcd: Optional[bool] = None
    renda_media: Optional[str] = None
    com_encaminhamento: Optional[bool] = None
    encaminhamento_realizado: Optional[bool] = None
    observacoes: Optional[str] = None
    status: Optional[str] = None


class CadastroTermoPreviewRequest(CadastroDadosBase):
    tipo: Literal["lgpd", "imagem"]
    assinatura_base64: Optional[str] = None


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


class CadastroOut(CadastroDadosBase):
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
    status_lgpd: Optional[str] = None
    retencao_ate: Optional[datetime] = None
    excluido_em: Optional[datetime] = None
    motivo_exclusao: Optional[str] = None
    consentimentos: list[ConsentimentoLGPDOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}
