from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.db.session import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, nullable=True)
    actor_nome = Column(String, nullable=True)
    action = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    created_em = Column(DateTime(timezone=True), server_default=func.now(), index=True)
