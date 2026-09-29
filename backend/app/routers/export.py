import base64
import csv
import io
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Response, HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as ReportLabImage,
)

from app.database.postgres import get_db
from app.models.sql_models import Actor, DarkWebHandle, Wallet, Observation, ScanTarget
from app.routers.auth import require_role

# Bulk export is limited to authenticated investigative roles because it
# exposes the consolidated actor intelligence result set.
router = APIRouter(prefix="/export", tags=["Export"], dependencies=[Depends(require_role("admin", "investigator"))])

class ActorReportExportRequest(BaseModel):
    graph_image: str | None = None


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
    "pgp_keys",
    "infrastructure_indicators",
    "sources",
    "last_scan_date",
    "graph_priority_score",
    "graph_priority_level",
]


def _priority_level(score: Any) -> str:
    value = int(score or 0)
    if value >= 85:
        return "critical"
    if value >= 70:
        return "high"
    if value >= 50:
        return "medium"
    return "low"


def _get_live_actor_records(db: Session) -> List[Dict[str, Any]]:
    actors = db.query(Actor).all()
    if not actors:
        return []

    actor_ids = [a.actor_id for a in actors]

    # Pre-fetch handles and wallets in two batch queries (avoids 2N+1 query bottleneck)
    all_handles = db.query(DarkWebHandle).filter(DarkWebHandle.actor_id.in_(actor_ids)).all()
    all_wallets = db.query(Wallet).filter(Wallet.actor_id.in_(actor_ids)).all()
    all_observations = db.query(Observation).filter(Observation.detected.is_(True)).all()
    all_scan_targets = db.query(ScanTarget).filter(ScanTarget.actor_id.in_(actor_ids)).all()

    handles_by_actor: Dict[str, list] = {}
    for h in all_handles:
        handles_by_actor.setdefault(h.actor_id, []).append(h)

    wallets_by_actor: Dict[str, list] = {}
    for w in all_wallets:
        wallets_by_actor.setdefault(w.actor_id, []).append(w)

    observations_by_actor: Dict[str, list] = {}
    for obs in all_observations:
        observations_by_actor.setdefault(obs.target.lower(), []).append(obs)

    scan_targets_by_actor: Dict[str, list] = {}
    for target in all_scan_targets:
        if target.actor_id:
            scan_targets_by_actor.setdefault(target.actor_id, []).append(target)

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

        target_keys = {a.actor_id.lower(), a.primary_handle.lower(), *[h.handle.lower() for h in actor_handles]}
        actor_observations = [
            obs
            for key in target_keys
            for obs in observations_by_actor.get(key, [])
        ]
        # De-duplicate observations that matched more than one target key.
        actor_observations = list({obs.observation_id: obs for obs in actor_observations}.values())
        scan_dates = [obs.timestamp for obs in actor_observations if obs.timestamp]
        target_scan_dates = [target.last_scan_at for target in scan_targets_by_actor.get(a.actor_id, []) if target.last_scan_at]
        latest_scan = max(target_scan_dates or scan_dates, default=None)
        last_scan_str = latest_scan.strftime("%Y-%m-%d") if latest_scan else "N/A"
        pgp_list = sorted({
            key.fingerprint
            for handle in actor_handles
            for key in getattr(handle, "pgp_keys", [])
            if key.fingerprint
        })
        infrastructure = sorted({
            str(obs.value)
            for obs in actor_observations
            if obs.value and (
                "infra" in (obs.indicator_type or "").lower()
                or "certificate" in (obs.indicator_type or "").lower()
                or "tls" in (obs.indicator_type or "").lower()
                or "banner" in (obs.indicator_type or "").lower()
                or "descriptor" in (obs.indicator_type or "").lower()
            )
        })
        sources = sorted({str(obs.source) for obs in actor_observations if obs.source})

        records.append({
            "actor_id": a.actor_id,
            "primary_handle": a.primary_handle,
            "risk_category": a.risk_category,
            "confidence_score": a.confidence_score,
            "priority_score": a.priority_score,
            "first_seen": first_seen_str,
            "last_seen": last_seen_str,
            "last_scan_date": last_scan_str,
            "graph_priority_score": a.priority_score,
            "graph_priority_level": _priority_level(a.priority_score),
            "handles": handle_list,
            "handles_count": len(handle_list),
            "wallets": wallet_list,
            "wallets_count": len(wallet_list),
            "pgp_keys": pgp_list,
            "infrastructure_indicators": infrastructure,
            "sources": sources,
            "observations": [
                {
                    "observation_id": obs.observation_id,
                    "indicator_type": obs.indicator_type,
                    "value": obs.value,
                    "source": obs.source,
                    "confidence": obs.confidence,
                    "timestamp": obs.timestamp.isoformat() if obs.timestamp else None,
                    "description": obs.description,
                }
                for obs in actor_observations
            ],
        })

    return records


def _get_actor_record(db: Session, actor_id: str) -> Dict[str, Any]:
    records = _get_live_actor_records(db)
    for record in records:
        if str(record.get("actor_id", "")).lower() == actor_id.lower():
            return record
    raise HTTPException(status_code=404, detail=f"Actor '{actor_id}' not found")


def _actor_csv_response(record: Dict[str, Any]) -> Response:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_HEADERS)
    writer.writeheader()
    writer.writerow({
        "actor_id": record["actor_id"],
        "primary_handle": record["primary_handle"],
        "risk_category": record["risk_category"],
        "confidence_score": record["confidence_score"],
        "priority_score": record["priority_score"],
        "first_seen": record["first_seen"],
        "last_seen": record["last_seen"],
        "handles_count": record["handles_count"],
        "associated_handles": "; ".join(record["handles"]),
        "wallets_count": record["wallets_count"],
        "wallet_addresses": "; ".join(record["wallets"]),
        "pgp_keys": "; ".join(record["pgp_keys"]),
        "infrastructure_indicators": "; ".join(record["infrastructure_indicators"]),
        "sources": "; ".join(record["sources"]),
        "last_scan_date": record["last_scan_date"],
        "graph_priority_score": record["graph_priority_score"],
        "graph_priority_level": record["graph_priority_level"],
    })
    safe_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in record["actor_id"])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=actor_{safe_id}.csv"},
    )


@router.get("/actor/{actor_id}/json")
def export_actor_json(actor_id: str, db: Session = Depends(get_db)):
    return JSONResponse(content=_get_actor_record(db, actor_id))


@router.get("/actor/{actor_id}/csv")
def export_actor_csv(actor_id: str, db: Session = Depends(get_db)):
    return _actor_csv_response(_get_actor_record(db, actor_id))


@router.get("/actor/{actor_id}/report")
def export_actor_report(actor_id: str, db: Session = Depends(get_db)):
    record = _get_actor_record(db, actor_id)
    pdf_bytes = _build_report_pdf([record])
    safe_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in actor_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=actor_{safe_id}_report.pdf"},
    )


@router.post("/actor/{actor_id}/report")
def export_actor_report_with_graph(
    actor_id: str,
    payload: ActorReportExportRequest,
    db: Session = Depends(get_db),
):
    record = _get_actor_record(db, actor_id)
    pdf_bytes = _build_report_pdf([record], graph_image=payload.graph_image)
    safe_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in actor_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=actor_{safe_id}_report.pdf"},
    )


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
            "pgp_keys": "; ".join(r["pgp_keys"]),
            "infrastructure_indicators": "; ".join(r["infrastructure_indicators"]),
            "sources": "; ".join(r["sources"]),
            "last_scan_date": r["last_scan_date"],
            "graph_priority_score": r["graph_priority_score"],
            "graph_priority_level": r["graph_priority_level"],
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


def _build_report_pdf(records: List[Dict[str, Any]], graph_image: str | None = None) -> bytes:
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
    unique_sources = sorted({source for record in records for source in record.get("sources", [])})
    actors_with_pgp = sum(1 for record in records if record.get("pgp_keys"))
    actors_with_infrastructure = sum(1 for record in records if record.get("infrastructure_indicators"))
    summary_data.append(["Actors with PGP identifiers", str(actors_with_pgp)])
    summary_data.append(["Actors with infrastructure evidence", str(actors_with_infrastructure)])
    summary_data.append(["Evidence sources", ", ".join(unique_sources) if unique_sources else "N/A"])
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
    # --- Detailed actor intelligence ---
    if records:
        record = records[0]
        story.append(Paragraph("Actor Intelligence", section_style))
        identity_rows = [
            ["Actor ID", str(record.get("actor_id", "N/A"))],
            ["Primary handle", str(record.get("primary_handle", "N/A"))],
            ["Risk category", str(record.get("risk_category", "N/A"))],
            ["Attribution confidence", f"{float(record.get("confidence_score") or 0):.2f}"],
            ["Priority score", str(record.get("priority_score", "N/A"))],
            ["First seen", str(record.get("first_seen", "N/A"))],
            ["Last seen", str(record.get("last_seen", "N/A"))],
            ["Last scan", str(record.get("last_scan_date", "N/A"))],
        ]
        identity_table = Table(identity_rows, colWidths=[1.8 * inch, 4.6 * inch])
        identity_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E5E7EB")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(identity_table)
        story.append(Spacer(1, 10))

        def _joined(values: list) -> str:
            return ", ".join(str(v) for v in values if v) or "None recorded"

        intelligence_rows = [
            ["Associated handles", _joined(record.get("handles", []))],
            ["Wallet addresses", _joined(record.get("wallets", []))],
            ["PGP fingerprints", _joined(record.get("pgp_keys", []))],
            ["Infrastructure indicators", _joined(record.get("infrastructure_indicators", []))],
            ["Evidence sources", _joined(record.get("sources", []))],
        ]
        intelligence_table = Table(intelligence_rows, colWidths=[1.8 * inch, 4.6 * inch])
        intelligence_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F3F4F6")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(intelligence_table)

        # Trust relationships
        trust_links = record.get("trust_links", [])
        if trust_links:
            story.append(Spacer(1, 10))
            story.append(Paragraph("Persona / Trust Linkages", section_style))
            trust_rows = [["Source", "Target", "Relationship", "Confidence"]]
            for link in trust_links:
                trust_rows.append([
                    str(link.get("source", "")),
                    str(link.get("target", "")),
                    str(link.get("relationship_type", "")),
                    f"{float(link.get("confidence") or 0):.0%}",
                ])
            trust_table = Table(trust_rows, colWidths=[1.55*inch, 1.55*inch, 1.65*inch, 1.25*inch], repeatRows=1)
            trust_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(trust_table)

        # Evidence records
        observations = record.get("observations", [])
        if observations:
            story.append(PageBreak())
            story.append(Paragraph("Evidence Records", section_style))
            evidence_rows = [["Type", "Value / Target", "Source", "Confidence", "Timestamp"]]
            for obs in observations:
                evidence_rows.append([
                    str(obs.get("indicator_type", "unknown")),
                    str(obs.get("value") or obs.get("description") or obs.get("target") or "N/A")[:90],
                    str(obs.get("source") or "N/A"),
                    f"{float(obs.get("confidence") or 0):.0%}",
                    str(obs.get("timestamp") or "N/A")[:19],
                ])
            evidence_table = Table(
                evidence_rows,
                colWidths=[1.0*inch, 2.45*inch, 1.25*inch, 0.8*inch, 1.0*inch],
                repeatRows=1,
            )
            evidence_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(evidence_table)

        # Browser-generated investigation graph snapshot.
        if graph_image:
            try:
                encoded = graph_image.split(",", 1)[1] if "," in graph_image else graph_image
                graph_bytes = base64.b64decode(encoded, validate=True)
                story.append(PageBreak())
                story.append(Paragraph("Investigation Graph Snapshot", section_style))
                story.append(Paragraph(
                    "Relationship snapshot generated from the actor graph returned by the DeCypher API.",
                    body_style,
                ))
                image_buffer = io.BytesIO(graph_bytes)
                graph_flowable = ReportLabImage(image_buffer, width=7.1 * inch, height=4.35 * inch)
                graph_flowable.hAlign = "CENTER"
                story.append(Spacer(1, 8))
                story.append(graph_flowable)
            except Exception:
                # A malformed optional image must never break actor export.
                story.append(Paragraph(
                    "Graph snapshot could not be embedded in this export.",
                    body_style,
                ))

    story.append(PageBreak())

    # --- Actor detail table ---
    story.append(Paragraph("Actor Records", section_style))
    table_header = ["Actor ID", "Primary Handle", "Risk", "Conf.", "Graph Priority", "Last Scan", "PGP", "Infra", "Sources"]
    table_rows = [table_header]
    row_risk_colors = []
    for r in records:
        table_rows.append([
            r.get("actor_id", ""),
            r.get("primary_handle", ""),
            r.get("risk_category", ""),
            f"{r.get('confidence_score', 0):.2f}" if r.get("confidence_score") is not None else "N/A",
            str(r.get("graph_priority_score", r.get("priority_score", "N/A"))),
            r.get("last_scan_date", "N/A"),
            str(len(r.get("pgp_keys", []))),
            str(len(r.get("infrastructure_indicators", []))),
            str(len(r.get("sources", []))),
        ])
        row_risk_colors.append(_risk_color(r.get("risk_category", "")))

    actor_table = Table(
        table_rows,
        colWidths=[0.7 * inch, 1.05 * inch, 0.72 * inch, 0.5 * inch, 0.55 * inch, 0.72 * inch, 0.45 * inch, 0.48 * inch, 0.48 * inch],
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
