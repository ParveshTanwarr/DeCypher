import csv
import io
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)

from app.database.postgres import get_db
from app.models.sql_models import Actor, DarkWebHandle, Wallet
from app.routers.auth import require_role

# Bulk export of every actor's identity/correlation data is the single
# most sensitive action in this API, so it's restricted to "admin" rather
# than any authenticated user. This is a judgment call, not a spec
# requirement -- adjust the allowed role(s) if that doesn't match your
# actual policy (e.g. add "investigator" back if analysts need exports too).
router = APIRouter(prefix="/export", tags=["Export"], dependencies=[Depends(require_role("admin"))])

CSV_HEADERS = [
    "actor_id",
    "primary_handle",
    "risk_category",
    "confidence_score",
    "priority_score",
    "first_seen",
    "last_seen",
    "handles_count",
    "associated_handles",
    "wallets_count",
    "wallet_addresses",
]


def _get_live_actor_records(db: Session) -> List[Dict[str, Any]]:
    actors = db.query(Actor).all()
    if not actors:
        return []

    actor_ids = [a.actor_id for a in actors]

    # Pre-fetch handles and wallets in two batch queries (avoids 2N+1 query bottleneck)
    all_handles = db.query(DarkWebHandle).filter(DarkWebHandle.actor_id.in_(actor_ids)).all()
    all_wallets = db.query(Wallet).filter(Wallet.actor_id.in_(actor_ids)).all()

    handles_by_actor: Dict[str, list] = {}
    for h in all_handles:
        handles_by_actor.setdefault(h.actor_id, []).append(h)

    wallets_by_actor: Dict[str, list] = {}
    for w in all_wallets:
        wallets_by_actor.setdefault(w.actor_id, []).append(w)

    records = []
    for a in actors:
        actor_handles = handles_by_actor.get(a.actor_id, [])
        actor_wallets = wallets_by_actor.get(a.actor_id, [])

        handle_list = [h.handle for h in actor_handles]
        wallet_list = [w.address for w in actor_wallets]

        first_dates = [h.first_seen for h in actor_handles if h.first_seen]
        last_dates = [h.last_seen for h in actor_handles if h.last_seen]

        first_seen_str = min(first_dates).strftime("%Y-%m-%d") if first_dates else "N/A"
        last_seen_str = max(last_dates).strftime("%Y-%m-%d") if last_dates else "N/A"

        records.append({
            "actor_id": a.actor_id,
            "primary_handle": a.primary_handle,
            "risk_category": a.risk_category,
            "confidence_score": a.confidence_score,
            "priority_score": a.priority_score,
            "first_seen": first_seen_str,
            "last_seen": last_seen_str,
            "handles": handle_list,
            "handles_count": len(handle_list),
            "wallets": wallet_list,
            "wallets_count": len(wallet_list),
        })

    return records


@router.get("/json")
def export_json(db: Session = Depends(get_db)):
    records = _get_live_actor_records(db)
    return JSONResponse(content=records)


@router.get("/csv")
def export_csv(db: Session = Depends(get_db)):
    records = _get_live_actor_records(db)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_HEADERS)
    writer.writeheader()

    for r in records:
        writer.writerow({
            "actor_id": r["actor_id"],
            "primary_handle": r["primary_handle"],
            "risk_category": r["risk_category"],
            "confidence_score": r["confidence_score"],
            "priority_score": r["priority_score"],
            "first_seen": r["first_seen"],
            "last_seen": r["last_seen"],
            "handles_count": r["handles_count"],
            "associated_handles": "; ".join(r["handles"]),
            "wallets_count": r["wallets_count"],
            "wallet_addresses": "; ".join(r["wallets"]),
        })








    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=threat_actors.csv"},
    )


# ---------------------------------------------------------------------------
# Formatted report export (PDF) -- the third format NTRO's spec asks for
# alongside CSV/JSON. Built with reportlab (pure Python, no system binary
# dependency like wkhtmltopdf/WeasyPrint need), so it installs the same way
# on every teammate's machine with nothing beyond `pip install -r requirements.txt`.
# ---------------------------------------------------------------------------

RISK_COLORS = {
    "critical": colors.HexColor("#B91C1C"),
    "high": colors.HexColor("#C2410C"),
    "medium": colors.HexColor("#A16207"),
    "low": colors.HexColor("#15803D"),
}


def _risk_color(risk_category: str) -> colors.Color:
    return RISK_COLORS.get((risk_category or "").strip().lower(), colors.HexColor("#374151"))


def _build_report_pdf(records: List[Dict[str, Any]]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.5 * inch, rightMargin=0.5 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], fontSize=20, spaceAfter=4)
    subtitle_style = ParagraphStyle("ReportSubtitle", parent=styles["Normal"], textColor=colors.grey, spaceAfter=18)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], spaceBefore=14, spaceAfter=8)
    body_style = styles["Normal"]

    story: List[Any] = []

    # --- Header ---
    story.append(Paragraph("DeCypher — Threat Actor Intelligence Report", title_style))
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(
        f"Generated {generated_at} &nbsp;|&nbsp; {len(records)} actor(s) &nbsp;|&nbsp; "
        f"Source: DeCypher Attribution Engine (SIH26151)",
        subtitle_style,
    ))

    # --- Summary section ---
    story.append(Paragraph("Summary", section_style))
    category_counts = Counter((r.get("risk_category") or "Unclassified") for r in records)
    avg_confidence = (
        sum(r.get("confidence_score") or 0 for r in records) / len(records) if records else 0
    )
    summary_data = [["Metric", "Value"]]
    summary_data.append(["Total actors in this export", str(len(records))])
    summary_data.append(["Average attribution confidence", f"{avg_confidence:.2f}"])
    for cat, count in sorted(category_counts.items(), key=lambda kv: -kv[1]):
        summary_data.append([f"  Risk category: {cat}", str(count)])

    summary_table = Table(summary_data, colWidths=[3.2 * inch, 2.0 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(summary_table)

    # --- Ethical / evidentiary disclaimer (matches the platform's own framing) ---
    story.append(Spacer(1, 14))
    disclaimer_style = ParagraphStyle(
        "Disclaimer", parent=styles["Normal"], fontSize=8, textColor=colors.grey,
        borderColor=colors.HexColor("#D1D5DB"), borderWidth=0.5, borderPadding=6,
    )
    story.append(Paragraph(
        "This report presents investigative leads generated by an automated attribution "
        "pipeline (stylometric persona linkage and infrastructure correlation). Confidence "
        "scores reflect statistical similarity, not confirmed identity, and are intended to "
        "support -- not replace -- human investigator review.",
        disclaimer_style,
    ))
    story.append(PageBreak())

    # --- Actor detail table ---
    story.append(Paragraph("Actor Records", section_style))
    table_header = ["Actor ID", "Primary Handle", "Risk", "Conf.", "Priority", "Last Seen", "Handles", "Wallets"]
    table_rows = [table_header]
    row_risk_colors = []
    for r in records:
        table_rows.append([
            r.get("actor_id", ""),
            r.get("primary_handle", ""),
            r.get("risk_category", ""),
            f"{r.get('confidence_score', 0):.2f}" if r.get("confidence_score") is not None else "N/A",
            str(r.get("priority_score", "N/A")),
            r.get("last_seen", "N/A"),
            str(r.get("handles_count", 0)),
            str(r.get("wallets_count", 0)),
        ])
        row_risk_colors.append(_risk_color(r.get("risk_category", "")))

    actor_table = Table(
        table_rows,
        colWidths=[0.75 * inch, 1.1 * inch, 0.7 * inch, 0.55 * inch, 0.6 * inch, 0.85 * inch, 0.6 * inch, 0.6 * inch],
        repeatRows=1,
    )
    table_style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    # Color each row's Risk cell by severity so a skim-read of the PDF still
    # surfaces the highest-priority actors, same intent as the dashboard's
    # Priority Score highlighting.
    for i, color in enumerate(row_risk_colors, start=1):
        table_style_cmds.append(("TEXTCOLOR", (2, i), (2, i), color))
        table_style_cmds.append(("FONTNAME", (2, i), (2, i), "Helvetica-Bold"))
    actor_table.setStyle(TableStyle(table_style_cmds))
    story.append(actor_table)

    if not records:
        story.append(Spacer(1, 12))
        story.append(Paragraph("No actor records matched the current export scope.", body_style))

    doc.build(story)
    return buffer.getvalue()


@router.get("/report")
def export_report(db: Session = Depends(get_db)):
    records = _get_live_actor_records(db)
    pdf_bytes = _build_report_pdf(records)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=decypher_threat_actor_report.pdf"},
    )
