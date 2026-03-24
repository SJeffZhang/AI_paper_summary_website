import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.db.session import SessionLocal
from app.models.domain import Paper
from app.services.ai_processor import AIProcessor


def main(batch_size: int = 20) -> None:
    db = SessionLocal()
    ai_processor = AIProcessor()

    try:
        papers = (
            db.query(Paper)
            .filter((Paper.title_zh.is_(None)) | (Paper.title_zh == "") | (Paper.title_zh == Paper.title_original))
            .order_by(Paper.id.asc())
            .all()
        )

        if not papers:
            print("No papers require title_zh backfill.")
            return

        print(f"Backfilling localized titles for {len(papers)} papers...")
        payload = [
            {
                "arxiv_id": paper.arxiv_id,
                "title_original": paper.title_original,
            }
            for paper in papers
        ]
        localized_titles = ai_processor.localize_titles(payload, batch_size=batch_size)

        updated = 0
        for paper in papers:
            localized_title = localized_titles.get(paper.arxiv_id, "").strip()
            if not localized_title:
                raise ValueError(f"Localized title missing for {paper.arxiv_id}.")
            paper.title_zh = localized_title
            updated += 1

        db.commit()
        print(f"Updated {updated} papers.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
