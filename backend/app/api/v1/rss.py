from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET
from app.db.session import get_db
from app.models.domain import Paper, PaperSummary
from app.core.config import settings

router = APIRouter()

@router.get("/rss")
def get_rss(db: Session = Depends(get_db)):
    """
    Get RSS 2.0 feed of paper summaries for the last 7 days.
    """
    seven_days_ago = datetime.now(timezone.utc).date() - timedelta(days=7)
    
    # Query last 7 days of summaries
    summaries = db.query(PaperSummary, Paper).join(Paper).filter(
        PaperSummary.issue_date >= seven_days_ago
    ).order_by(PaperSummary.issue_date.desc()).all()
    
    # Create RSS root
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    
    ET.SubElement(channel, "title").text = "AI Paper Summary"
    ET.SubElement(channel, "link").text = settings.FRONTEND_URL
    ET.SubElement(channel, "description").text = "Daily AI paper summaries in Chinese."
    ET.SubElement(channel, "language").text = "zh-cn"
    
    for summary, paper in summaries:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = f"[{summary.issue_date}] {paper.title}"
        ET.SubElement(item, "link").text = f"{settings.FRONTEND_URL}/paper/{paper.id}"
        
        description = f"<h3>一句话总结</h3><p>{summary.one_line_summary}</p>"
        description += "<h3>核心亮点</h3><ul>"
        for highlight in summary.core_highlights:
            description += f"<li>{highlight}</li>"
        description += "</ul>"
        
        ET.SubElement(item, "description").text = description
        ET.SubElement(item, "pubDate").text = summary.created_at.strftime("%a, %d %b %Y %H:%M:%S +0800")
        ET.SubElement(item, "guid").text = str(paper.id)
        
    xml_str = ET.tostring(rss, encoding="utf-8", method="xml")
    return Response(content=b'<?xml version="1.0" encoding="UTF-8"?>' + xml_str, media_type="application/xml")
