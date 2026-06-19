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
    senha_hash_admin = hash_senha(ADMIN_PASSWORD)
    dados_admin = {
        "nome": "Coordenadora ASAP",
        "email": ADMIN_EMAIL,
        "senha_hash": senha_hash_admin,
        "perfil": "coordenadora",
        "ativo": True,
    }
    if not existente:
        criar_usuario_sheets(dados_admin)
        print("Usuário administrador criado na planilha.")
    else:
        # Verifica se precisa atualizar dados essenciais
        if not getattr(existente, "senha_hash", None) or getattr(existente, "perfil", None) != "coordenadora" or not getattr(existente, "ativo", False):
            from app.services.sheets_usuarios import atualizar_usuario_sheets
            atualizar_usuario_sheets(int(existente.id), dados_admin)
            print("Usuário administrador atualizado na planilha.")
        else:
            print("Usuário já existe na planilha.")
else:
    print("Modo planilha desativado; mantendo fallback local.")
    senha_hash_admin = hash_senha(ADMIN_PASSWORD)

# --- Lógica do Banco de Dados (Neon) ---
admin_db = db.query(Usuario).filter(Usuario.email == ADMIN_EMAIL).first()
if not admin_db:
    u = Usuario(
        nome="Coordenadora ASAP",
        email=ADMIN_EMAIL,
        senha_hash=senha_hash_admin,
        perfil="coordenadora",
    )
    db.add(u)
    db.commit()
    print("Usuário administrador criado no banco de dados.")
else:
    admin_db.nome = admin_db.nome or "Coordenadora ASAP"
    admin_db.senha_hash = senha_hash_admin
    admin_db.perfil = "coordenadora"
    admin_db.ativo = True
    admin_db.precisa_trocar_senha = False
    db.commit()
    print("Usuário atualizado no banco de dados.")

db.close()
