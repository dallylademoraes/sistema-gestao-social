"""
Rode uma vez para criar o primeiro usuário coordenadora:
    python seed.py
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from app.db.session import SessionLocal, engine, Base
from app.models.usuario import Usuario
from app.core.security import hash_senha
from app.services.sheets_usuarios import criar_usuario_sheets, buscar_usuario_sheets, usuarios_sheets_enabled

# 1. Puxa as credenciais seguras do .env
ADMIN_EMAIL = os.getenv("FIRST_ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("FIRST_ADMIN_PASSWORD")

# 2. Trava de segurança: se esquecer de colocar no .env, o script avisa e para
if not ADMIN_EMAIL or not ADMIN_PASSWORD:
    print("ERRO: As variáveis FIRST_ADMIN_EMAIL e FIRST_ADMIN_PASSWORD não foram encontradas no .env!")
    sys.exit(1)

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# --- Lógica da Planilha ---
if usuarios_sheets_enabled():
    existente = buscar_usuario_sheets(email=ADMIN_EMAIL)
    dados_admin = {
        "nome": "Coordenadora ASAP",
        "email": ADMIN_EMAIL,
        "senha_hash": hash_senha(ADMIN_PASSWORD),
        "perfil": "coordenadora",
        "ativo": True,
    }
    if not existente:
        criar_usuario_sheets(dados_admin)
        print(f"Usuário criado na planilha: {ADMIN_EMAIL}")
    else:
        # Verifica se precisa atualizar dados essenciais
        if not getattr(existente, "senha_hash", None) or getattr(existente, "perfil", None) != "coordenadora" or not getattr(existente, "ativo", False):
            from app.services.sheets_usuarios import atualizar_usuario_sheets
            atualizar_usuario_sheets(int(existente.id), dados_admin)
            print(f"Usuário da planilha atualizado: {ADMIN_EMAIL}")
        else:
            print("Usuário já existe na planilha.")
else:
    print("Modo planilha desativado; mantendo fallback local.")

# --- Lógica do Banco de Dados (Neon) ---
if not db.query(Usuario).filter(Usuario.email == ADMIN_EMAIL).first():
    u = Usuario(
        nome="Coordenadora ASAP",
        email=ADMIN_EMAIL,
        senha_hash=hash_senha(ADMIN_PASSWORD),
        perfil="coordenadora",
    )
    db.add(u)
    db.commit()
    print(f"Usuário criado no banco de dados: {ADMIN_EMAIL}")
else:
    print("Usuário já existe no banco de dados.")

db.close()