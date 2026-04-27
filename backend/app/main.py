from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import engine, Base
from app.core.config import settings
from app.api.routes import auth, cadastros
from app.models import usuario, cadastro, audit_log, cadastro_lgpd, consentimento_lgpd, login_throttle  # noqa: garante que os models são registrados

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ASAP — Sistema de Cadastro",
    version="1.0.0",
    description="API para gestão de cadastros de usuários e doadores da ASAP",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(cadastros.router, prefix="/api")


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}
