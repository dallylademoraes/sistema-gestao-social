from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader

from app.models.cadastro import Cadastro
from app.services.pdf_assets import resolver_logo_asap


def _elemento_logo_asap() -> list:
    logo_path = resolver_logo_asap()
    if not logo_path:
        return []
    reader = ImageReader(str(logo_path))
    iw, ih = reader.getSize()
    if iw <= 0 or ih <= 0:
        return []
    largura = 5.5 * cm
    altura = largura * (ih / float(iw))
    altura = min(altura, 2.8 * cm)
    largura = altura * (iw / float(ih))
    return [Image(str(logo_path), width=largura, height=altura), Spacer(1, 0.4 * cm)]


def gerar_pdf_cadastro(cadastro: Cadastro) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()

    titulo = ParagraphStyle("titulo", parent=styles["Heading1"], fontSize=16, spaceAfter=6)
    subtitulo = ParagraphStyle("sub", parent=styles["Heading2"], fontSize=12, spaceAfter=4, textColor=colors.HexColor("#1D9E75"))
    corpo = styles["Normal"]

    def linha(label, valor):
        return [Paragraph(f"<b>{label}</b>", corpo), Paragraph(str(valor or "—"), corpo)]

    elementos = [
        *_elemento_logo_asap(),
        Paragraph("ASAP — Ficha de Cadastro", titulo),
        Paragraph(f"#{cadastro.id:04d} · Status: {cadastro.status.upper()}", corpo),
        Spacer(1, 0.5*cm),

        Paragraph("Dados Pessoais", subtitulo),
        Table([
            linha("Nome completo", cadastro.nome),
            linha("Nome social", cadastro.nome_social),
            linha("CPF", cadastro.cpf),
            linha("RG / Órgão", f"{cadastro.rg} {cadastro.orgao_expedidor or ''}".strip()),
            linha("Data de nascimento", cadastro.data_nascimento),
            linha("Estado civil", cadastro.estado_civil),
            linha("Identidade de gênero", cadastro.identidade_genero),
            linha("Cor/raça", cadastro.cor_raca),
            linha("PCD", "Sim" if cadastro.pcd else "Não"),
            linha("Renda média", cadastro.renda_media),
        ], colWidths=[5*cm, 12*cm],
           style=TableStyle([
               ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F1FAF5")]),
               ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
               ("FONTSIZE", (0, 0), (-1, -1), 9),
               ("TOPPADDING", (0, 0), (-1, -1), 5),
               ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
           ])),
        Spacer(1, 0.4*cm),

        Paragraph("Contato e Endereço", subtitulo),
        Table([
            linha("E-mail", cadastro.email),
            linha("Telefone", cadastro.telefone),
            linha("Endereço", cadastro.endereco),
            linha("Cidade/UF", f"{cadastro.cidade or ''}/{cadastro.uf or ''}"),
        ], colWidths=[5*cm, 12*cm],
           style=TableStyle([
               ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F1FAF5")]),
               ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
               ("FONTSIZE", (0, 0), (-1, -1), 9),
               ("TOPPADDING", (0, 0), (-1, -1), 5),
               ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
           ])),
        Spacer(1, 0.4*cm),

        Paragraph("Encaminhamento", subtitulo),
        Table([
            linha("Com encaminhamento", "Sim" if cadastro.com_encaminhamento else "Não"),
            linha("Encaminhamento realizado", "Sim" if cadastro.encaminhamento_realizado else "Não"),
        ], colWidths=[5*cm, 12*cm],
           style=TableStyle([
               ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F1FAF5")]),
               ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
               ("FONTSIZE", (0, 0), (-1, -1), 9),
               ("TOPPADDING", (0, 0), (-1, -1), 5),
               ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
           ])),

        Spacer(1, 1*cm),
        Paragraph(f"Documento gerado pelo sistema ASAP · {cadastro.criado_em.strftime('%d/%m/%Y') if cadastro.criado_em else ''}", 
                  ParagraphStyle("rodape", parent=corpo, fontSize=8, textColor=colors.gray)),
    ]

    doc.build(elementos)
    return buffer.getvalue()


def gerar_pdf_relatorio_comparativo_mensal(relatorio: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("titulo_rel", parent=styles["Heading1"], fontSize=16, spaceAfter=6)
    subtitulo = ParagraphStyle("sub_rel", parent=styles["Heading2"], fontSize=11, spaceAfter=5, textColor=colors.HexColor("#1D9E75"))
    corpo = styles["Normal"]

    atual = relatorio.get("periodo_atual", {})
    anterior = relatorio.get("periodo_anterior", {})
    variacao = relatorio.get("variacao", {})

    def linha(label: str, chave: str):
        va = atual.get(chave, 0)
        vb = anterior.get(chave, 0)
        vv = variacao.get(chave, 0)
        sinal = "+" if isinstance(vv, (int, float)) and vv > 0 else ""
        return [
            Paragraph(f"<b>{label}</b>", corpo),
            Paragraph(str(va), corpo),
            Paragraph(str(vb), corpo),
            Paragraph(f"{sinal}{vv}%", corpo),
        ]

    elementos = [
        *_elemento_logo_asap(),
        Paragraph("ASAP — Relatório Comparativo Mensal", titulo),
        Paragraph(
            f"Período atual: {relatorio.get('periodo_atual_label', '—')} · "
            f"Período anterior: {relatorio.get('periodo_anterior_label', '—')}",
            corpo,
        ),
        Spacer(1, 0.4 * cm),
        Paragraph("Resumo de Indicadores", subtitulo),
        Table(
            [
                ["Indicador", "Mês atual", "Mês anterior", "Variação"],
                linha("Novos cadastros", "novos_cadastros"),
                linha("Cadastros ativos", "ativos"),
                linha("Pendentes", "pendentes"),
                linha("Com encaminhamento", "com_encaminhamento"),
            ],
            colWidths=[6.5 * cm, 3 * cm, 3.2 * cm, 3.3 * cm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF6F1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FCFA")]),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            ),
        ),
        Spacer(1, 0.5 * cm),
        Paragraph(
            "Este resumo compara o desempenho do mês atual com o mês imediatamente anterior, "
            "apoiando decisões operacionais da assistência social.",
            corpo,
        ),
    ]

    doc.build(elementos)
    return buffer.getvalue()
