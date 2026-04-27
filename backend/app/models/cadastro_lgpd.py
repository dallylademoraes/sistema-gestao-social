from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.db.session import Base


class CadastroLGPD(Base):
    __tablename__ = "cadastros_lgpd"

    id = Column(Integer, primary_key=True)
    cadastro_id = Column(Integer, ForeignKey("cadastros.id"), unique=True, nullable=False, index=True)
    base_legal = Column(String(100), nullable=False, default="consentimento")
    status_lgpd = Column(String(30), nullable=False, default="pendente")  # pendente | consentido | revogado
    retencao_ate = Column(DateTime(timezone=True), nullable=True)
    excluido_em = Column(DateTime(timezone=True), nullable=True)
    motivo_exclusao = Column(String(255), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())
