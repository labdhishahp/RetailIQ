"""PDF rendering of a saved Decision Report.

Reads only the stored report (title, code, payload). Nothing is queried or
re-run: the charts are drawn from the chart data saved when the report was
generated, with reportlab's own chart primitives.
"""

import io
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer

from app.models import Report

_BLUE = colors.HexColor("#2563EB")
_SERIES = [_BLUE, colors.HexColor("#22C55E"), colors.HexColor("#F59E0B"),
           colors.HexColor("#EF4444"), colors.HexColor("#8B5CF6"), colors.HexColor("#64748B")]

_styles = getSampleStyleSheet()
_H1 = _styles["Title"]
_H2 = ParagraphStyle("h2", parent=_styles["Heading2"], spaceBefore=10, spaceAfter=4)
_BODY = ParagraphStyle("body", parent=_styles["BodyText"], fontSize=9.5, leading=13)
_SMALL = ParagraphStyle("small", parent=_BODY, fontSize=8, leading=10.5, textColor=colors.HexColor("#52627a"))
_BULLET = ParagraphStyle("bullet", parent=_BODY, leftIndent=12, bulletIndent=2)


def _t(value) -> str:
    """Escape for reportlab markup and keep to the built-in fonts' character set."""
    text = str(value if value is not None else "").replace("→", "->").replace("⇄", "<->")
    text = text.encode("cp1252", errors="replace").decode("cp1252")
    return escape(text)


def _date(iso) -> str:
    if not iso:
        return "-"
    try:
        value = datetime.fromisoformat(str(iso))
    except ValueError:
        return str(iso)
    if value.tzinfo is None:
        return value.strftime("%d %b %Y %H:%M")
    return value.astimezone(timezone.utc).strftime("%d %b %Y %H:%M UTC")


def _short(label, n=16) -> str:
    label = str(label)
    return label if len(label) <= n else label[: n - 1] + "…"


def _chart(chart: dict) -> Drawing | None:
    data = chart.get("data") or []
    if not data:
        return None
    drawing = Drawing(170 * mm, 62 * mm)
    if chart.get("type") == "pie":
        pie = Pie()
        pie.x, pie.y, pie.width, pie.height = 40 * mm, 6 * mm, 50 * mm, 50 * mm
        pie.data = [max(float(r.get("value") or 0), 0) for r in data]
        pie.labels = [_short(r.get("category")) for r in data]
        pie.sideLabels = True
        pie.slices.fontSize = 7
        for i in range(len(data)):
            pie.slices[i].fillColor = _SERIES[i % len(_SERIES)]
        drawing.add(pie)
        return drawing

    if chart.get("type") == "line":
        plot = HorizontalLineChart()
        keys = [line["key"] for line in chart.get("lines") or []]
        plot.data = [[float(r.get(k) or 0) for r in data] for k in keys]
        for i in range(len(keys)):
            plot.lines[i].strokeColor = _SERIES[i % len(_SERIES)]
            plot.lines[i].strokeWidth = 1.5
    elif chart.get("type") == "bar":
        plot = VerticalBarChart()
        plot.data = [[float(r.get(chart["dataKey"]) or 0) for r in data]]
        plot.bars[0].fillColor = _BLUE
        plot.barWidth = 6
    else:
        return None

    values = [v for series in plot.data for v in series]
    plot.x, plot.y, plot.width, plot.height = 14 * mm, 16 * mm, 150 * mm, 42 * mm
    plot.valueAxis.valueMin = min(0.0, min(values))
    plot.valueAxis.valueMax = max(values) if max(values) > plot.valueAxis.valueMin else plot.valueAxis.valueMin + 1
    plot.valueAxis.labels.fontSize = 7
    plot.categoryAxis.categoryNames = [_short(r.get(chart.get("xKey"))) for r in data]
    plot.categoryAxis.labels.fontSize = 7
    plot.categoryAxis.labels.angle = 30
    plot.categoryAxis.labels.boxAnchor = "ne"
    plot.categoryAxis.labelAxisMode = "low"   # labels below the plot, clear of negative bars
    drawing.add(plot)
    return drawing


def _footer(code: str):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(18 * mm, 10 * mm, f"RetailIQ Decision Report {code}")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()
    return draw


def decision_report_pdf(report: Report) -> bytes:
    p = report.payload or {}
    summary = p.get("summary") or {}
    rec = p.get("recommendation") or {}
    trace = p.get("trace") or {}
    story: list = []

    story.append(Paragraph(_t(report.title), _H1))
    story.append(Paragraph(
        f"{_t(report.code)} &middot; Generated {_date(p.get('generated_at'))} &middot; "
        f"Data as of {_date(p.get('data_as_of'))} &middot; "
        f"Investigated {_date((p.get('source') or {}).get('investigated_at'))}", _SMALL))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Business question", _H2))
    story.append(Paragraph(_t(p.get("question")), _BODY))

    story.append(Paragraph("Executive summary", _H2))
    story.append(Paragraph(_t(summary.get("rootCause")), _BODY))
    facts = [f"Risk: {_t(summary.get('riskLevel'))}", f"Confidence: {_t(summary.get('confidence'))}%",
             f"Revenue impact: {_t(summary.get('revenueImpact'))}", f"Synthesis: {_t(summary.get('synthesis'))}"]
    story.append(Paragraph(" &middot; ".join(facts), _SMALL))
    for key in ("businessImpact", "inventoryImpact"):
        if summary.get(key):
            story.append(Paragraph(_t(summary[key]), _SMALL))

    story.append(Paragraph("Recommendation", _H2))
    story.append(Paragraph(f"<b>{_t(rec.get('action'))}</b>", _BODY))
    for i, step in enumerate(rec.get("nextSteps") or [], 1):
        story.append(Paragraph(_t(step), _BULLET, bulletText=f"{i}."))

    story.append(Paragraph("Evidence", _H2))
    for item in p.get("evidence") or []:
        story.append(Paragraph(_t(item), _BULLET, bulletText="•"))

    charts = [(c, d) for c in p.get("charts") or [] if (d := _chart(c)) is not None]
    for i, (c, drawing) in enumerate(charts):
        block = [Paragraph("Charts", _H2)] if i == 0 else []   # heading stays with the first chart
        story.append(KeepTogether(block + [
            Paragraph(f"<b>{_t(c.get('title'))}</b> &middot; {_t(c.get('subtitle'))}", _BODY),
            drawing,
            Paragraph(f"Source: {_t(c.get('source'))}", _SMALL),
            Spacer(1, 6),
        ]))

    story.append(Paragraph("Agent investigation", _H2))
    story.append(Paragraph(
        f"Mode: {_t(trace.get('mode'))} &middot; Delegations: {_t(trace.get('delegations'))} &middot; "
        f"Tool calls: {_t(trace.get('toolCalls'))}"
        + (f" &middot; Fallback: {_t(trace.get('fallback'))}" if trace.get("fallback") else ""), _SMALL))
    for d in trace.get("decisions") or []:
        focus = f" ({_t(d.get('focus'))})" if d.get("focus") else ""
        story.append(Paragraph(f"R{_t(d.get('round'))} {_t(d.get('agent'))}{focus}: {_t(d.get('reason'))}",
                               _BULLET, bulletText="•"))
    for a in p.get("agents") or []:
        tools = " -> ".join(a.get("toolsCalled") or []) or "no tool calls"
        story.append(Paragraph(
            f"<b>{_t(a.get('name') or a.get('id'))}</b> (round {_t(a.get('round'))}, {_t(a.get('mode'))}): "
            f"{_t(tools)}", _BODY))
        for f in (a.get("findings") or [])[:4]:
            mark = {True: " [verified]", False: " [unverified]"}.get(f.get("verified"), "")
            story.append(Paragraph(f"{_t(f.get('statement'))}{mark}", _BULLET, bulletText="-"))
    if trace.get("unverifiedClaims"):
        story.append(Paragraph("Unverified claims in the conclusion: "
                               + "; ".join(_t(c) for c in trace["unverifiedClaims"]), _SMALL))

    citations = p.get("citations") or []
    if citations:
        story.append(Paragraph("Sources", _H2))
        for c in citations:
            story.append(Paragraph(f"{_t(c.get('title'))} ({_t(c.get('doc_type'))})", _BULLET, bulletText="•"))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=report.title, author="RetailIQ",
                            leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm)
    doc.build(story, onFirstPage=_footer(report.code), onLaterPages=_footer(report.code))
    return buf.getvalue()
