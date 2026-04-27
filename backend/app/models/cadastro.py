from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.db.session import Base


class Cadastro(Base):
    __tablename__ = "cadastros"

    id = Column(Integer, primary_key=True)

    # Identificação
    nome = Column(String, nullable=False)
    nome_social = Column(String)
    cpf = Column(String(14), unique=True, nullable=False, index=True)
    rg = Column(String)
    orgao_expedidor = Column(String)
    data_nascimento = Column(Date, nullable=False)

    # Contato
    email = Column(String)
    telefone = Column(String, nullable=False)

    # Endereço
    endereco = Column(String)
    cidade = Column(String)
    uf = Column(String(2))

    # Dados socioeconômicos
    estado_civil = Column(String)
    cor_raca = Column(String)
    identidade_genero = Column(String)
    pcd = Column(Boolean, default=False)
    renda_media = Column(String)

    # Encaminhamento
    com_encaminhamento = Column(Boolean, default=False)
    encaminhamento_realizado = Column(Boolean, default=False)

    # Documentos (caminhos no disco / URL do Drive)
    foto_url = Column(String)
    comprovante_residencia_url = Column(String)
    documento_pessoal_url = Column(String)
    termo_imagem_url = Column(String)
    termo_lgpd_url = Column(String)

    # Controle
    status = Column(String, default="pendente")  # pendente | ativo | inativo
    aprovado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    observacoes = Column(Text)

    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def lgpd_concluido(self) -> bool:
        return bool(self.termo_lgpd_url)
