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

db = SessionLocal()

if not db.query(Usuario).filter(Usuario.email == "admin@asap.org").first():
    u = Usuario(
        nome="Coordenadora ASAP",
        email="admin@asap.org",
        senha_hash=hash_senha("troque-essa-senha"),
        perfil="coordenadora",
    )
    db.add(u)
    db.commit()
    print("Usuário criado: admin@asap.org / troque-essa-senha")
else:
    print("Usuário já existe.")

db.close()
