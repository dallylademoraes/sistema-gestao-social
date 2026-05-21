from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func

from app.db.session import Base


class ConsentimentoLGPD(Base):
    __tablename__ = "consentimentos_lgpd"

    id = Column(Integer, primary_key=True)
    cadastro_id = Column(Integer, nullable=False, index=True)
    tipo = Column(String(20), nullable=False)  # concedido | revogado
    base_legal = Column(String(100), nullable=False, default="consentimento")
    observacao = Column(Text, nullable=True)
    registrado_por_id = Column(Integer, nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
