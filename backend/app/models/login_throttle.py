from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.db.session import Base


class LoginThrottle(Base):
    __tablename__ = "login_throttles"

    id = Column(Integer, primary_key=True)
    identifier = Column(String, unique=True, nullable=False, index=True)
    attempts = Column(Integer, nullable=False, default=0)
    window_start = Column(DateTime(timezone=True), nullable=True)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())
