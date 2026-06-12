from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.core.config import settings
from app.api.routes import auth, cadastros
from app.models import usuario, cadastro, audit_log, cadastro_lgpd, consentimento_lgpd, login_throttle  # noqa: garante que os models são registrados
from app.services.sheets_cadastros import aquecer_cache_sheets

# Nota: Este projeto usa Google Planilhas como armazenamento principal.
# A criação automática de schemas de bancos relacionais foi removida.

app = FastAPI(
    title="ASAP — Sistema de Gestão",
    version="1.0.0",
    description="API para gestão de cadastros de usuários e doadores da ASAP",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origins=[
        "http://localhost:5173", 
        "https://sistema-gestao-social.vercel.app"
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(cadastros.router, prefix="/api")


@app.on_event("startup")
def startup() -> None:
    aquecer_cache_sheets()


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}
