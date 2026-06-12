"""Geração de PDFs dos termos LGPD e uso de imagem (ReportLab + texto ou modelo PDF em assets/termos)."""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.cadastro import Cadastro
from app.services.pdf_modelo_asap import try_preencher_modelo_asap_pdf

ASSETS_TERMOS = Path(__file__).resolve().parent.parent.parent / "assets" / "termos"

# Nomes aceites para modelos PDF em `backend/assets/termos/` (primeiro existente ganha).
# Inclui os nomes padrão ASAP (com travessão —) e variantes com hífen.
_NOMES_PDF_MODELO_LGPD = (
    "Termo LGPD — ASAP.pdf",
    "Termo LGPD - ASAP.pdf",
    "modelo_lgpd.pdf",
    "termo_lgpd.pdf",
    "termo-lgpd.pdf",
    "termo_lgpd_modelo.pdf",
)
_NOMES_PDF_MODELO_IMAGEM = (
    "Termo de uso de imagem — ASAP.pdf",
    "Termo de uso de imagem - ASAP.pdf",
    "modelo_imagem.pdf",
    "termo_imagem.pdf",
    "termo_uso_imagem.pdf",
    "termo-uso-imagem.pdf",
    "termo_uso_de_imagem.pdf",
)


def _normalizar_chave_nome_pdf(nome: str) -> str:
    """Compara nomes de PDF ignorando variações de travessão, espaços e NFC/NFD."""
    n = unicodedata.normalize("NFKC", (nome or "").strip()).lower()
    out: list[str] = []
    for ch in n:
        if unicodedata.category(ch) == "Pd" or ch in "-\u2010\u2011\u2012\u2013\u2014\u2015\u2212\ufe58\ufe63\uff0d":
            out.append("-")
        elif ch.isspace():
            out.append(" ")
        else:
            out.append(ch)
    s = "".join(out)
    s = re.sub(r"-+", "-", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _resolver_path_modelo_pdf(tipo: str) -> Path | None:
    """Localiza o PDF modelo em ASSETS_TERMOS (nomes ASAP, aliases e pontuação por conteúdo)."""
    if not ASSETS_TERMOS.is_dir():
        return None
    pdfs = [p for p in ASSETS_TERMOS.iterdir() if p.suffix.lower() == ".pdf" and p.is_file()]
    if not pdfs:
        return None

    canon_map: dict[str, Path] = {}
    for p in pdfs:
        canon_map[_normalizar_chave_nome_pdf(p.name)] = p

    prefer = _NOMES_PDF_MODELO_LGPD if tipo == "lgpd" else _NOMES_PDF_MODELO_IMAGEM
    for name in prefer:
        hit = canon_map.get(_normalizar_chave_nome_pdf(name))
        if hit:
            return hit

    def score_lgpd(p: Path) -> int:
        s = _normalizar_chave_nome_pdf(p.stem).replace(" ", "")
        sc = 0
        if "lgpd" in s:
            sc += 25
        if "asap" in s:
            sc += 5
        if "uso" in s and "imagem" in s:
            sc -= 80
        return sc

    def score_imagem(p: Path) -> int:
        s = _normalizar_chave_nome_pdf(p.stem).replace(" ", "")
        sc = 0
        if "uso" in s and "imagem" in s:
            sc += 35
        elif "imagem" in s and "lgpd" not in s:
            sc += 18
        if "asap" in s:
            sc += 5
        if "lgpd" in s and "imagem" not in s:
            sc -= 90
        return sc

    if tipo == "lgpd":
        best = max(pdfs, key=lambda p: (score_lgpd(p), -len(p.name)))
        if score_lgpd(best) >= 15:
            return best
    else:
        best = max(pdfs, key=lambda p: (score_imagem(p), -len(p.name)))
        if score_imagem(best) >= 15:
            return best

    logging.getLogger(__name__).warning(
        "PDFs em %s mas nenhum reconhecido como modelo %s. Ficheiros: %s",
        ASSETS_TERMOS,
        tipo,
        [p.name for p in pdfs],
    )
    return None


def _ler_texto_termo(arquivo: str) -> str:
    p = ASSETS_TERMOS / arquivo
    if not p.exists():
        return (
            f"Texto do termo ({arquivo}) ainda não foi configurado. "
            "Substitua o ficheiro em backend/assets/termos/ conforme README desse diretório."
        )
    return p.read_text(encoding="utf-8").strip()


def _linhas_paragrafos(texto: str, estilo) -> list:
    blocos = [b.strip() for b in texto.split("\n\n") if b.strip()]
    out = []
    for b in blocos:
        linhas = b.replace("\n", "<br/>")
        out.append(Paragraph(linhas, estilo))
        out.append(Spacer(1, 0.25 * cm))
    return out


def _tabela_identificacao(cadastro: Cadastro, corpo, subtitulo) -> list:
    def linha(label, valor):
        return [Paragraph(f"<b>{label}</b>", corpo), Paragraph(str(valor or "—"), corpo)]

    return [
        Paragraph("Identificação do titular", subtitulo),
        Table(
            [
                linha("Nome completo", cadastro.nome),
                linha("Nome social", cadastro.nome_social),
                linha("CPF", cadastro.cpf),
                linha("RG / Órgão", f"{cadastro.rg or ''} {cadastro.orgao_expedidor or ''}".strip()),
                linha("Data de nascimento", cadastro.data_nascimento),
                linha("E-mail", cadastro.email),
                linha("Telefone", cadastro.telefone),
                linha("Endereço", cadastro.endereco),
                linha("Cidade/UF", "/".join([p for p in [cadastro.cidade or "", cadastro.uf or ""] if p]) or "—"),
            ],
            colWidths=[4.2 * cm, 12.3 * cm],
            style=TableStyle(
                [
                    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F1FAF5")]),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            ),
        ),
        Spacer(1, 0.35 * cm),
    ]


def _estilos_termo():
    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("titulo", parent=styles["Heading1"], fontSize=15, spaceAfter=8, textColor=colors.HexColor("#1a1a1a"))
    subtitulo = ParagraphStyle("sub", parent=styles["Heading2"], fontSize=11, spaceAfter=6, textColor=colors.HexColor("#1D9E75"))
    corpo = ParagraphStyle("corpo", parent=styles["Normal"], fontSize=9, leading=13, alignment=TA_JUSTIFY)
    return styles, titulo, subtitulo, corpo


def _elementos_cabecalho(
    cadastro: Cadastro,
    *,
    titulo_doc: str,
    agora: str,
    styles,
    titulo,
) -> list:
    marca = ParagraphStyle("marca", parent=titulo, fontSize=18, textColor=colors.HexColor("#1D9E75"))
    return [
        Paragraph("ASAP", marca),
        Paragraph(titulo_doc, titulo),
        Paragraph(f"Cadastro nº {cadastro.id or '— (prévia)'} · Emitido em {agora}", styles["Normal"]),
        Spacer(1, 0.4 * cm),
    ]


def _elementos_assinatura_e_rodape(imagem_png: bytes | None, subtitulo, corpo) -> list:
    elems: list = [
        Spacer(1, 0.5 * cm),
        Paragraph("<b>Assinatura do titular (manuscrita digitalizada)</b>", subtitulo),
    ]
    if imagem_png:
        try:
            bio = BytesIO(imagem_png)
            pil = PILImage.open(bio)
            pil.load()
            w, h = pil.size
            max_w = 8 * cm
            scale = min(max_w / w, 3 * cm / h) if w and h else 1
            rw = w * scale
            rh = h * scale
            bio.seek(0)
            elems.append(RLImage(bio, width=rw, height=rh))
        except Exception:
            elems.append(Paragraph("(Não foi possível incluir a imagem da assinatura.)", corpo))
    else:
        elems.append(Paragraph("— Prévia sem assinatura —", corpo))

    elems.append(Spacer(1, 0.8 * cm))
    elems.append(
        Paragraph(
            "Declaro que li e compreendi o presente documento e que as informações acima estão corretas.",
            ParagraphStyle("rod", parent=corpo, fontSize=8, textColor=colors.grey),
        )
    )
    return elems


def _flowables_para_pdf_bytes(flowables: list) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.8 * cm, bottomMargin=1.8 * cm)
    doc.build(flowables)
    return buffer.getvalue()


def _merge_modelo_com_anexo(modelo_pdf: bytes, anexo_pdf: bytes) -> bytes:
    writer = PdfWriter()
    base = PdfReader(BytesIO(modelo_pdf))
    for page in base.pages:
        writer.add_page(page)
    anexo = PdfReader(BytesIO(anexo_pdf))
    for page in anexo.pages:
        writer.add_page(page)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def gerar_pdf_termo_acordo(
    cadastro: Cadastro,
    *,
    tipo: str,
    imagem_png: bytes | None,
    quando_iso: str | None = None,
) -> bytes:
    """
    tipo: 'lgpd' | 'imagem'
    imagem_png: PNG da assinatura manuscrita (opcional na prévia).

    Se existir um PDF modelo em `backend/assets/termos/` (ver nomes aceites no README),
    o PDF oficial é preservado e acrescenta-se um anexo com identificação e assinatura.
    Caso contrário, gera-se o documento completo a partir dos ficheiros .txt.
    """
    if tipo == "lgpd":
        titulo_doc = "Termo de consentimento — LGPD"
        arquivo_txt = "texto_lgpd.txt"
    elif tipo == "imagem":
        titulo_doc = "Termo de uso de imagem"
        arquivo_txt = "texto_imagem.txt"
    else:
        raise ValueError("tipo deve ser lgpd ou imagem")

    agora = quando_iso or datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    styles, titulo, subtitulo, corpo = _estilos_termo()

    modelo_path = _resolver_path_modelo_pdf(tipo)
    if modelo_path is not None:
        preenchido = try_preencher_modelo_asap_pdf(modelo_path, tipo, cadastro, agora, imagem_png)
        if preenchido is not None:
            return preenchido
        elems: list = _elementos_cabecalho(cadastro, titulo_doc=titulo_doc, agora=agora, styles=styles, titulo=titulo)
        elems.append(Paragraph("Dados do titular e aceite (anexo ao termo precedente)", subtitulo))
        elems.extend(_tabela_identificacao(cadastro, corpo, subtitulo))
        elems.extend(_elementos_assinatura_e_rodape(imagem_png, subtitulo, corpo))
        anexo = _flowables_para_pdf_bytes(elems)
        modelo_bytes = modelo_path.read_bytes()
        return _merge_modelo_com_anexo(modelo_bytes, anexo)

    texto_corpo = _ler_texto_termo(arquivo_txt)
    elems = _elementos_cabecalho(cadastro, titulo_doc=titulo_doc, agora=agora, styles=styles, titulo=titulo)
    elems.extend(_tabela_identificacao(cadastro, corpo, subtitulo))
    elems.append(Paragraph("Conteúdo do termo (ficheiro texto)", subtitulo))
    elems.extend(_linhas_paragrafos(texto_corpo, corpo))
    elems.extend(_elementos_assinatura_e_rodape(imagem_png, subtitulo, corpo))
    return _flowables_para_pdf_bytes(elems)
