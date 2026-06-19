from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Configura o logging para exibir mensagens de nível INFO ou superior
logging.basicConfig(level=logging.INFO)


from app.core.config import settings
from app.api.routes import auth, cadastros
from app.models import usuario, cadastro, audit_log, cadastro_lgpd, consentimento_lgpd, login_throttle  # noqa: garante que os models são registrados
from app.db.session import Base, engine
from app.services.sheets_cadastros import aquecer_cache_sheets

app = FastAPI(
    title="ASAP — Sistema de Gestão",
    version="1.0.0",
    description="API para gestão de cadastros de usuários e doadores da ASAP",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(cadastros.router, prefix="/api")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    aquecer_cache_sheets()


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}
