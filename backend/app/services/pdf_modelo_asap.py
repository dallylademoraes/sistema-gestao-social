"""
Preenchimento dos PDFs oficiais ASAP (modelo plano, sem campos AcroForm),
usando coordenadas do layout «Termo de uso de imagem — ASAP» e «Termo LGPD — ASAP».
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

from app.models.cadastro import Cadastro

logger = logging.getLogger(__name__)

_MESES_PT = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


def _parse_agora_br(agora: str) -> tuple[str, str, str, str, str]:
    """Retorna (dia, mês_nome, ano_4, ano_2, mês_2d) a partir de 'DD/MM/YYYY HH:MM UTC' ou ISO."""
    s = (agora or "").strip()
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        d, mo, y = m.group(1).zfill(2), int(m.group(2)), m.group(3)
        mes_nome = _MESES_PT[mo - 1] if 1 <= mo <= 12 else str(mo)
        return d, mes_nome, y, y[-2:], f"{mo:02d}"
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        mes_nome = _MESES_PT[dt.month - 1]
        return f"{dt.day:02d}", mes_nome, f"{dt.year:04d}", f"{dt.year % 100:02d}", f"{dt.month:02d}"
    except ValueError:
        hoje = datetime.now()
        return (
            f"{hoje.day:02d}",
            _MESES_PT[hoje.month - 1],
            f"{hoje.year:04d}",
            f"{hoje.year % 100:02d}",
            f"{hoje.month:02d}",
        )


def _rua_e_numero(endereco: str | None) -> tuple[str, str]:
    if not (endereco or "").strip():
        return "", ""
    e = endereco.strip()
    if "," in e:
        partes = [p.strip() for p in e.split(",") if p.strip()]
        if len(partes) >= 2:
            return partes[0], partes[-1][:20]
    return e, "S/N"


def _cobrir_e_texto(
    page: fitz.Page,
    rect: fitz.Rect,
    texto: str,
    *,
    max_font: float = 10.0,
    min_font: float = 7.0,
    alinhamento: int = fitz.TEXT_ALIGN_LEFT,
) -> None:
    if texto is None:
        return
    t = str(texto).strip()
    if not t:
        return
    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
    inner = fitz.Rect(rect.x0 + 0.8, rect.y0 + 0.5, rect.x1 - 0.8, rect.y1 - 1.0)
    fs = max_font
    while fs >= min_font:
        excesso = page.insert_textbox(
            inner,
            t,
            fontname="helv",
            fontsize=fs,
            color=(0, 0, 0),
            align=alinhamento,
        )
        if excesso >= 0:
            return
        fs -= 0.5
    page.insert_textbox(inner, t, fontname="helv", fontsize=min_font, color=(0, 0, 0), align=alinhamento)


def _cobrir_e_imagem(page: fitz.Page, rect: fitz.Rect, png: bytes) -> None:
    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
    try:
        page.insert_image(rect, stream=png, keep_proportion=True)
    except Exception:
        logger.exception("Falha ao inserir assinatura no PDF modelo")


def _detect_layout_uso_imagem(doc: fitz.Document) -> bool:
    if doc.page_count < 1:
        return False
    p0 = doc[0]
    return bool(p0.search_for("Eu,")) and bool(p0.search_for("AUTORIZO"))


def _detect_layout_lgpd(doc: fitz.Document) -> bool:
    if doc.page_count < 1:
        return False
    for i in range(doc.page_count - 1, -1, -1):
        p = doc[i]
        if p.search_for("Assinatura") and (p.search_for("titular") or p.search_for("Nome")):
            return True
    return False


def _indice_pagina_assinatura_lgpd(doc: fitz.Document) -> int:
    for i in range(doc.page_count - 1, -1, -1):
        p = doc[i]
        if p.search_for("Assinatura") and p.search_for("CPF"):
            return i
    return doc.page_count - 1


def _preencher_uso_imagem_p0(page: fitz.Page, cadastro: Cadastro, agora: str, imagem_png: bytes | None) -> None:
    """Coordenadas extraídas do modelo «Termo de uso de imagem — ASAP.pdf» (A4)."""
    dia, mes_nome, _ano4, ano2, _mm = _parse_agora_br(agora)
    rua, numero = _rua_e_numero(cadastro.endereco)
    rg_txt = " ".join([p for p in [cadastro.rg or "", cadastro.orgao_expedidor or ""] if p]).strip() or "—"

    # Campos do formulário (y cresce para baixo)
    _cobrir_e_texto(page, fitz.Rect(95.59, 116.13, 439.20, 129.54), cadastro.nome or "")
    _cobrir_e_texto(page, fitz.Rect(233.82, 131.99, 350.58, 145.40), rg_txt)
    _cobrir_e_texto(page, fitz.Rect(72.0, 147.87, 182.09, 161.27), cadastro.cpf or "")
    _cobrir_e_texto(page, fitz.Rect(72.0, 163.74, 328.87, 177.14), rua)
    _cobrir_e_texto(page, fitz.Rect(369.16, 163.74, 419.20, 177.14), numero)
    _cobrir_e_texto(page, fitz.Rect(72.0, 179.60, 208.78, 193.01), cadastro.cidade or "")

    local = ", ".join([p for p in [cadastro.cidade or "", cadastro.uf or ""] if p]) or (cadastro.cidade or "—")
    _cobrir_e_texto(page, fitz.Rect(72.0, 469.67, 189.0, 482.96), local)
    _cobrir_e_texto(page, fitz.Rect(192.0, 469.67, 222.0, 482.96), dia, max_font=9)
    _cobrir_e_texto(page, fitz.Rect(239.33, 469.67, 323.33, 482.96), mes_nome, max_font=9)
    _cobrir_e_texto(page, fitz.Rect(340.65, 469.67, 373.65, 482.96), ano2, max_font=9)

    if imagem_png:
        _cobrir_e_imagem(page, fitz.Rect(167.50, 517.17, 427.71, 530.58), imagem_png)


def _preencher_lgpd_assinatura(page: fitz.Page, cadastro: Cadastro, agora: str, imagem_png: bytes | None) -> None:
    """Última página com «Nome do titular» / CPF / assinatura / data (modelo ASAP)."""
    dia, _mes_nome, ano4, _ano2, mm = _parse_agora_br(agora)

    _cobrir_e_texto(page, fitz.Rect(76.89, 627.80, 333.83, 641.20), cadastro.nome or "")
    _cobrir_e_texto(page, fitz.Rect(364.89, 627.80, 518.34, 641.20), cadastro.cpf or "")
    if imagem_png:
        _cobrir_e_imagem(page, fitz.Rect(167.50, 691.27, 427.71, 704.68), imagem_png)

    _cobrir_e_texto(page, fitz.Rect(257.59, 738.88, 284.28, 752.28), dia, max_font=9)
    _cobrir_e_texto(page, fitz.Rect(294.29, 738.88, 320.97, 752.28), mm, max_font=9)
    _cobrir_e_texto(page, fitz.Rect(330.98, 738.88, 371.02, 752.28), ano4, max_font=9)


def try_preencher_modelo_asap_pdf(
    modelo_path: Path,
    tipo: str,
    cadastro: Cadastro,
    agora: str,
    imagem_png: bytes | None,
) -> Optional[bytes]:
    """
    Devolve PDF em bytes com o modelo oficial preenchido, ou None para usar o fluxo antigo (anexo ReportLab).
    """
    try:
        doc = fitz.open(str(modelo_path))
    except Exception:
        logger.exception("Não foi possível abrir o modelo PDF: %s", modelo_path)
        return None
    try:
        if tipo == "imagem" and _detect_layout_uso_imagem(doc):
            _preencher_uso_imagem_p0(doc[0], cadastro, agora, imagem_png)
            return doc.tobytes(deflate=True, garbage=4)
        if tipo == "lgpd" and _detect_layout_lgpd(doc):
            idx = _indice_pagina_assinatura_lgpd(doc)
            _preencher_lgpd_assinatura(doc[idx], cadastro, agora, imagem_png)
            return doc.tobytes(deflate=True, garbage=4)
    except Exception:
        logger.exception("Falha ao preencher modelo ASAP (tipo=%s)", tipo)
        return None
    finally:
        doc.close()
    return None
