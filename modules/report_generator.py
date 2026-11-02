"""Generate a compact, printable PDF analytics report."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


NAVY = colors.HexColor("#142B4A")
BLUE = colors.HexColor("#2457A7")
GREEN = colors.HexColor("#10B981")
GRID = colors.HexColor("#E5EAF2")
PALE = colors.HexColor("#F5F7FB")


def _logo():
    """Small vector analytics mark for sharp rendering in the PDF header."""
    mark = Drawing(34, 34)
    mark.add(Rect(0, 0, 34, 34, 7, fillColor=BLUE, strokeColor=BLUE))
    mark.add(Rect(7, 12, 4, 12, fillColor=colors.white, strokeColor=None))
    mark.add(Rect(15, 8, 4, 16, fillColor=colors.white, strokeColor=None))
    mark.add(Rect(23, 5, 4, 19, fillColor=colors.white, strokeColor=None))
    mark.add(Line(7, 27, 14, 25, strokeColor=GREEN, strokeWidth=1.5))
    mark.add(Line(14, 25, 20, 28, strokeColor=GREEN, strokeWidth=1.5))
    mark.add(Line(20, 28, 28, 20, strokeColor=GREEN, strokeWidth=1.5))
    return mark


def _display_text(value):
    """Replace UI Unicode symbols with glyphs supported by standard PDF fonts."""
    text = str(value)
    for source, replacement in {
        "₹": "INR ", "→": "->", "−": "-", "—": "-", "–": "-", "•": "-", "·": "-",
    }.items():
        text = text.replace(source, replacement)
    return text


def _money(value):
    return "N/A" if value is None or value != value else f"INR {value:,.2f}"


def _percent(value, decimals=1):
    return "N/A" if value is None or value != value else f"{value:.{decimals}f}%"


def _ratio(value):
    return "N/A" if value is None or value != value else f"{value:.2f}x"


def _table_style(header_color=NAVY, font_size=7.5):
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, GRID),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size + 2),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(GRID)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, 0.42 * inch, letter[0] - doc.rightMargin, 0.42 * inch)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(doc.leftMargin, 0.25 * inch, "Campaign Intelligence | Revenue-based ROI")
    canvas.drawRightString(letter[0] - doc.rightMargin, 0.25 * inch, f"Page {doc.page}")
    canvas.restoreState()


def create_pdf_report(kpis, performance, funnel, highest_dropoff, recommendations, period):
    """Build report bytes from the currently filtered metrics and recommendations."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, rightMargin=0.52 * inch, leftMargin=0.52 * inch,
        topMargin=0.42 * inch, bottomMargin=0.62 * inch,
        title="Campaign Intelligence Marketing Analytics Report",
        author="Campaign Intelligence",
    )
    styles = getSampleStyleSheet()
    styles["Title"].fontSize = 18
    styles["Title"].leading = 22
    styles["Title"].textColor = NAVY
    styles["Title"].spaceAfter = 3
    styles["Normal"].fontSize = 8.5
    styles["Normal"].leading = 11
    styles["Heading2"].fontSize = 11
    styles["Heading2"].leading = 13
    styles["Heading2"].textColor = NAVY
    styles["Heading2"].spaceBefore = 7
    styles["Heading2"].spaceAfter = 4
    styles["BodyText"].fontSize = 8.5
    styles["BodyText"].leading = 10.5
    styles["BodyText"].spaceAfter = 0
    styles["Italic"].fontSize = 8
    styles["Italic"].leading = 10

    brand_title = Table([
        [_logo(), [Paragraph("Campaign Intelligence", styles["Title"]),
                  Paragraph("Turn Marketing Data Into Profitable Decisions.", styles["Normal"])]],
    ], colWidths=[0.52 * inch, 6.8 * inch])
    brand_title.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story = [
        brand_title,
        Paragraph("Marketing Campaign ROI &amp; Funnel Report", styles["Heading2"]),
        Paragraph(f"Analysis period: {_display_text(period)}", styles["Normal"]),
        Spacer(1, 5),
        Paragraph("Executive summary", styles["Heading2"]),
    ]
    kpi_rows = [
        ["Metric", "Result"],
        ["Impressions", f"{kpis['Impressions']:,.0f}"],
        ["Clicks", f"{kpis['Clicks']:,.0f}"],
        ["Leads", f"{kpis['Leads']:,.0f}"],
        ["Conversions", f"{kpis['Conversions']:,.0f}"],
        ["Ad spend", _money(kpis["Ad_Spend"])],
        ["Revenue", _money(kpis["Revenue"])],
        ["CTR", _percent(kpis["CTR"], 2)],
        ["CPC", _money(kpis["CPC"])],
        ["CPA", _money(kpis["CPA"])],
        ["ROI", _percent(kpis["ROI"], 2)],
        ["ROAS", _ratio(kpis["ROAS"])],
    ]
    story.append(Table(kpi_rows, colWidths=[2.25 * inch, 2.0 * inch], style=_table_style(font_size=8)))
    story += [Paragraph("Channel comparison", styles["Heading2"])]

    channel_rows = [["Channel", "Spend (INR)", "Revenue (INR)", "ROI", "ROAS", "CTR", "CPC (INR)", "CPA (INR)"]]
    for _, row in performance.iterrows():
        channel_rows.append([
            _display_text(row.Channel), _money(row.Ad_Spend), _money(row.Revenue),
            _percent(row["ROI (%)"], 1), _ratio(row.ROAS), _percent(row["CTR (%)"], 1),
            _money(row.CPC), _money(row.CPA),
        ])
    story.append(Table(
        channel_rows,
        colWidths=[1.15 * inch, 1.0 * inch, 1.0 * inch, 0.58 * inch, 0.55 * inch, 0.55 * inch, 0.9 * inch, 0.9 * inch],
        repeatRows=1,
        style=_table_style(font_size=7.2),
    ))

    story += [Paragraph("Funnel analysis", styles["Heading2"])]
    story.append(Paragraph(f"Largest observed drop-off: {_display_text(highest_dropoff)}.", styles["Normal"]))
    funnel_rows = [["Stage", "Volume", "Conversion from prior", "Drop-off from prior"]]
    for _, row in funnel.iterrows():
        funnel_rows.append([
            _display_text(row.Stage), f"{row.Volume:,.0f}",
            _percent(row["Conversion from prior (%)"]), _percent(row["Drop-off from prior (%)"]),
        ])
    story.append(Table(
        funnel_rows, colWidths=[1.5 * inch, 1.3 * inch, 1.7 * inch, 1.7 * inch],
        repeatRows=1, style=_table_style(header_color=colors.HexColor("#315B9C"), font_size=7.5),
    ))

    story += [Paragraph("Business recommendations", styles["Heading2"])]
    for recommendation in recommendations:
        story.append(Paragraph("- " + _display_text(recommendation), styles["BodyText"]))
        story.append(Spacer(1, 2))
    story += [
        Spacer(1, 3),
        Paragraph(
            "ROI in this report is revenue-based: (revenue - ad spend) / ad spend. "
            "It is not profit-based ROI because product costs and gross margin are not included. "
            "Metrics describe the selected historical records and do not predict future performance.",
            styles["Italic"],
        ),
    ]
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
