"""Recursos estáticos (logo ASAP, etc.) para geração de PDFs."""
from __future__ import annotations

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"

_NOMES_LOGO = (
    "logo_asap.png",
    "logo_asap.jpg",
    "logo_asap.jpeg",
    "logo.png",
    "logo.jpg",
    "asap.png",
    "asap.jpg",
    "logo.jpeg",
)


def resolver_logo_asap() -> Path | None:
    """Localiza o ficheiro da logo ASAP em `backend/assets/` ou `backend/assets/termos/`."""
    pastas = (ASSETS_DIR, ASSETS_DIR / "termos")
    for pasta in pastas:
        if not pasta.is_dir():
            continue
        for nome in _NOMES_LOGO:
            p = pasta / nome
            if p.is_file():
                return p
        for p in sorted(pasta.iterdir()):
            if not p.is_file():
                continue
            stem = p.stem.lower()
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and (
                "logo" in stem or stem.startswith("asap") or "whatsapp image" in stem
            ):
                return p
    return None
