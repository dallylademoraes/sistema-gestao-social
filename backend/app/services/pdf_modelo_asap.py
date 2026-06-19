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
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)

_FONTE_CORPO_MODELO = 12.0
_FONTE_MINIMA_CAMPO = 10.5
_FONTE_PADRAO = "helv"
_MARGEM_ESQ = 72.0
_MARGEM_DIR = 523.0


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


def _redact_rect(page: fitz.Page, rect: fitz.Rect) -> None:
    page.add_redact_annot(rect, fill=(1, 1, 1))
    page.apply_redactions()


def _inserir_bloco_texto(
    page: fitz.Page,
    rect: fitz.Rect,
    texto: str,
    *,
    fontsize: float = _FONTE_CORPO_MODELO,
    align: int = fitz.TEXT_ALIGN_LEFT,
) -> None:
    """
    Apaga a área do modelo e reescreve o texto como um bloco contínuo,
    permitindo que o PyMuPDF quebre as linhas naturalmente conforme a largura
    disponível — sem impor quebras artificiais no meio de frases.

    Se o texto não couber com o tamanho padrão, reduz progressivamente o
    fontsize até _FONTE_MINIMA_CAMPO antes de desistir.
    """
    t = str(texto or "").strip()
    if not t:
        return

    _redact_rect(page, rect)

    fs = fontsize
    while fs >= _FONTE_MINIMA_CAMPO:
        resultado = page.insert_textbox(
            rect,
            t,
            fontname=_FONTE_PADRAO,
            fontsize=fs,
            color=(0, 0, 0),
            align=align,
        )
        # insert_textbox devolve o espaço vertical restante (≥ 0) ou negativo se não coube
        if resultado >= 0:
            return
        fs -= 0.25

    # Último recurso: insere no tamanho mínimo mesmo que extravase levemente
    page.insert_textbox(
        rect,
        t,
        fontname=_FONTE_PADRAO,
        fontsize=_FONTE_MINIMA_CAMPO,
        color=(0, 0, 0),
        align=align,
    )


def _inserir_linha_simples(
    page: fitz.Page,
    y0: float,
    y1: float,
    texto: str,
    *,
    x0: float = _MARGEM_ESQ,
    x1: float = _MARGEM_DIR,
    fontsize: float = _FONTE_CORPO_MODELO,
) -> None:
    """Atalho para campos de linha única (data, CPF, nome isolado etc.)."""
    _inserir_bloco_texto(page, fitz.Rect(x0, y0, x1, y1), texto, fontsize=fontsize)


def _inserir_assinatura(page: fitz.Page, area: fitz.Rect, png: bytes) -> None:
    """Assinatura manuscrita ampliada."""
    _redact_rect(page, area)

    try:
        img_doc = fitz.open(stream=png, filetype="png")
        pix = img_doc[0].get_pixmap(alpha=True)
        img_doc.close()

        iw, ih = pix.width, pix.height
        if iw <= 0 or ih <= 0:
            return

        margem = 4.0
        inner = fitz.Rect(
            area.x0 + margem,
            area.y0 + margem,
            area.x1 - margem,
            area.y1 - margem,
        )

        escala = min(inner.width / iw, inner.height / ih)
        w, h = iw * escala, ih * escala

        dest = fitz.Rect(
            inner.x0 + (inner.width - w) / 2,
            inner.y0 + (inner.height - h) / 2,
            inner.x0 + (inner.width - w) / 2 + w,
            inner.y0 + (inner.height - h) / 2 + h,
        )

        page.insert_image(dest, pixmap=pix)

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

def _preencher_uso_imagem_p0(
    page: fitz.Page,
    cadastro: Cadastro,
    agora: str,
    imagem_png: bytes | None,
) -> None:

    dia, mes_nome, ano4, ano2, mm = _parse_agora_br(agora)

    rua, numero = _rua_e_numero(cadastro.endereco)

    rg_txt = " ".join(
        filter(None, [cadastro.rg or "", cadastro.orgao_expedidor or ""])
    ).strip() or "—"

    nome = (cadastro.nome or "").strip() or "—"
    cpf = (cadastro.cpf or "").strip() or "—"
    cidade = (cadastro.cidade or "").strip() or "—"

    local = ", ".join(
        filter(None, [cadastro.cidade or "", cadastro.uf or ""])
    ) or cidade

    ano_txt = ano4 if len(ano4) == 4 else f"20{ano2}"

    # Limpa a página inteira
    _redact_rect(
        page,
        fitz.Rect(
            40,
            40,
            560,
            820,
        )
    )

    # Título
    page.insert_text(
        fitz.Point(110, 80),
        "TERMO DE AUTORIZAÇÃO DE USO DE IMAGEM",
        fontsize=14,
        fontname="helv",
    )

    texto = (
        f"Eu, {nome}, portador(a) da Cédula de Identidade nº {rg_txt}, "
        f"inscrito(a) no CPF sob nº {cpf}, residente à Rua {rua}, "
        f"nº {numero}, na cidade de {cidade}, AUTORIZO o uso e divulgação "
        f"da minha imagem por meio de fotos, vídeos e/ou outros registros "
        f"audiovisuais realizados pela Ação Social Arquidiocesana de Palmas "
        f"(ASAP), para fins institucionais, sem finalidade comercial, "
        f"relacionados às atividades, projetos, ações e prestação de contas "
        f"da instituição.\n\n"

        f"A presente autorização é concedida a título gratuito, abrangendo "
        f"o uso da imagem acima mencionada em todo território nacional e no "
        f"exterior, em todas as suas modalidades e, em destaque, das "
        f"seguintes formas: (I) páginas institucionais na internet "
        f"(sites e redes sociais da ASAP); (II) relatórios institucionais "
        f"e de prestação de contas; (III) materiais informativos e de "
        f"divulgação; (IV) cartazes, apresentações e campanhas; e "
        f"(V) toda e qualquer forma de divulgação institucional.\n\n"

        f"Por esta ser a expressão da minha vontade, declaro que autorizo "
        f"o uso acima descrito sem que nada haja a ser reclamado a título "
        f"de direitos conexos à minha imagem ou a qualquer outro, não "
        f"recebendo para tanto qualquer tipo de remuneração, e assino "
        f"a presente autorização."
    )

    # Texto principal
    page.insert_textbox(
        fitz.Rect(
            60,
            120,
            540,
            450,
        ),
        texto,
        fontname="helv",
        fontsize=11,
        color=(0, 0, 0),
        align=fitz.TEXT_ALIGN_JUSTIFY,
    )

    # Assinatura mais próxima do texto
    if imagem_png:
        _inserir_assinatura(
            page,
            fitz.Rect(
                140,
                440,
                430,
                515,
            ),
            imagem_png,
        )

    page.insert_text(
        fitz.Point(245, 535),
        "Assinatura",
        fontsize=14,
        fontname="helv",
    )

    page.insert_text(
        fitz.Point(225, 560),
        f"{dia} de {mes_nome} de {ano_txt}",
        fontsize=12,
        fontname="helv",
    )

def _preencher_lgpd_assinatura(
    page: fitz.Page,
    cadastro: Cadastro,
    agora: str,
    imagem_png: bytes | None,
) -> None:

    dia, mes_nome, ano4, _ano2, _mm = _parse_agora_br(agora)

    nome = (cadastro.nome or "").strip() or "—"
    cpf = (cadastro.cpf or "").strip() or "—"

    # Limpa a área final da página
    _redact_rect(
        page,
        fitz.Rect(
            50,
            640,
            550,
            820,
        )
    )

    # Texto de consentimento
    texto_consentimento = (
        f"Declaro que fui informado(a) de forma clara sobre o tratamento "
        f"dos meus dados pessoais e concordo livremente com sua coleta e "
        f"utilização para os fins descritos neste documento. Eu, {nome}, "
        f"inscrito(a) no CPF sob o nº {cpf}, confirmo minha concordância "
        f"com os termos aqui apresentados e firmo o presente consentimento "
        f"na data de {dia} de {mes_nome} de {ano4}."
    )

    page.insert_textbox(
        fitz.Rect(
            60,
            610,
            540,
            710,
        ),
        texto_consentimento,
        fontname="helv",
        fontsize=11,
        color=(0, 0, 0),
        align=fitz.TEXT_ALIGN_JUSTIFY,
    )

    # Assinatura centralizada
    if imagem_png:
        _inserir_assinatura(
            page,
            fitz.Rect(
                150,
                720,
                420,
                770,
            ),
            imagem_png,
        )

    # Texto abaixo da assinatura
    page.insert_text(
        fitz.Point(245, 790),
        "Assinatura",
        fontsize=14,
        fontname="helv",
    )   

def try_preencher_modelo_asap_pdf(
    modelo_path: Path,
    tipo: str,
    cadastro: Cadastro,
    agora: str,
    imagem_png: bytes | None,
) -> Optional[bytes]:
    """
    Devolve PDF em bytes com o modelo oficial preenchido, ou None para usar
    o fluxo antigo (anexo ReportLab).
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
