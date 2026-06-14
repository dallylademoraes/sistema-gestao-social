from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

# Ajustamos para PostgreSQL (o Neon)
is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    # Se não for sqlite, adicionamos o pool de conexões resiliente
    pool_pre_ping=True,      # Verifica se a conexão está viva antes de usar
    pool_recycle=300,        # Recicla a conexão a cada 5 minutos
    pool_size=10,            # Mantém até 10 conexões abertas
    max_overflow=20          # Permite picos de até 20 conexões
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()