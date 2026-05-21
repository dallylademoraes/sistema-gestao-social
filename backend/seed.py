"""
Rode uma vez para criar o primeiro usuário coordenadora:
    python seed.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from app.db.session import SessionLocal
from app.models.usuario import Usuario
from app.core.security import hash_senha
from app.services.sheets_usuarios import criar_usuario_sheets, buscar_usuario_sheets, usuarios_sheets_enabled

db = SessionLocal()

if usuarios_sheets_enabled():
    existente = buscar_usuario_sheets(email="admin@asap.org")
    dados_admin = {
        "nome": "Coordenadora ASAP",
        "email": "admin@asap.org",
        "senha_hash": hash_senha("troque-essa-senha"),
        "perfil": "coordenadora",
        "ativo": True,
    }
    if not existente:
        criar_usuario_sheets(dados_admin)
        print("Usuário criado na planilha: admin@asap.org / troque-essa-senha")
    else:
        if not getattr(existente, "senha_hash", None) or getattr(existente, "perfil", None) != "coordenadora" or not getattr(existente, "ativo", False):
            from app.services.sheets_usuarios import atualizar_usuario_sheets

            atualizar_usuario_sheets(int(existente.id), dados_admin)
            print("Usuário da planilha atualizado: admin@asap.org / troque-essa-senha")
        else:
            print("Usuário já existe na planilha.")
else:
    print("Modo planilha desativado; mantendo fallback local.")

if not db.query(Usuario).filter(Usuario.email == "admin@asap.org").first():
    u = Usuario(
        nome="Coordenadora ASAP",
        email="admin@asap.org",
        senha_hash=hash_senha("troque-essa-senha"),
        perfil="coordenadora",
    )
    db.add(u)
    db.commit()
    print("Usuário criado no banco local: admin@asap.org / troque-essa-senha")
else:
    print("Usuário já existe no banco local.")

db.close()
