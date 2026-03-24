from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.domain import Paper, PaperSummary

router = APIRouter()


@router.get("/rss")
def get_rss(db: Session = Depends(get_db)):
    seven_days_ago = datetime.now(timezone(timedelta(hours=8))).date() - timedelta(days=7)
    rows = (
        db.query(PaperSummary, Paper)
        .join(Paper)
        .filter(PaperSummary.issue_date >= seven_days_ago)
        .filter(PaperSummary.category.in_(("focus", "watching")))
        .order_by(PaperSummary.issue_date.desc(), PaperSummary.score.desc())
        .all()
    )

    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "AI Paper Summary"
    ET.SubElement(channel, "link").text = settings.FRONTEND_URL
    ET.SubElement(channel, "description").text = "Daily AI paper summaries in Chinese and English."
    ET.SubElement(channel, "language").text = "zh-cn"

    for summary, paper in rows:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = f"[{summary.issue_date}] {paper.title_zh}"
        ET.SubElement(item, "link").text = f"{settings.FRONTEND_URL}/paper/{paper.id}"
        ET.SubElement(item, "description").text = summary.one_line_summary or ""

        issue_dt = datetime.combine(summary.issue_date, datetime.min.time()).replace(tzinfo=timezone(timedelta(hours=8)))
        ET.SubElement(item, "pubDate").text = issue_dt.strftime("%a, %d %b %Y %H:%M:%S %z")
        ET.SubElement(item, "guid").text = f"{paper.id}-{summary.issue_date.isoformat()}"

    xml_content = ET.tostring(rss, encoding="utf-8", method="xml")
    return Response(
        content=b'<?xml version="1.0" encoding="UTF-8"?>' + xml_content,
        media_type="application/xml",
    )
