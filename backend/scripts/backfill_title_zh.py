import os
import sys
import argparse
from typing import Dict, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.db.session import SessionLocal
from app.models.domain import Paper
from app.services.ai_processor import AIProcessor


def _load_pending_papers(db) -> List[Paper]:
    return (
        db.query(Paper)
        .filter(
            (Paper.title_zh.is_(None))
            | (Paper.title_zh == "")
            | (Paper.title_zh == Paper.title_original)
            | (Paper.title_zh.like("待翻译：%"))
        )
        .order_by(Paper.id.asc())
        .all()
    )


def _localize_batch(
    ai_processor: AIProcessor,
    payload: List[Dict[str, str]],
    batch_size: int,
) -> Dict[str, str]:
    try:
        return ai_processor.localize_titles(payload, batch_size=batch_size)
    except Exception as exc:
        print(f"[backfill_title_zh] batch localization failed: {exc}; falling back to per-paper mode.")
        localized: Dict[str, str] = {}
        for item in payload:
            arxiv_id = item["arxiv_id"]
            try:
                localized[arxiv_id] = ai_processor.localize_title(item)
            except Exception as single_exc:
                print(f"[backfill_title_zh] single paper localization failed for {arxiv_id}: {single_exc}")
                localized[arxiv_id] = ai_processor.build_fallback_title(item["title_original"])
        return localized


def main(batch_size: int = 20) -> None:
    db = SessionLocal()
    ai_processor = AIProcessor()

    try:
        papers = _load_pending_papers(db)

        if not papers:
            print("No papers require title_zh backfill.")
            return

        total = len(papers)
        effective_batch_size = max(1, int(batch_size))
        print(f"Backfilling localized titles for {total} papers...")
        updated = 0
        fallback_count = 0

        for start in range(0, total, effective_batch_size):
            batch = papers[start:start + effective_batch_size]
            payload = [
                {
                    "arxiv_id": paper.arxiv_id,
                    "title_original": paper.title_original,
                    "title_zh": paper.title_zh,
                }
                for paper in batch
            ]
            localized_titles = _localize_batch(
                ai_processor=ai_processor,
                payload=payload,
                batch_size=effective_batch_size,
            )

            for paper in batch:
                localized_title = str(localized_titles.get(paper.arxiv_id, "")).strip()
                if not localized_title:
                    localized_title = ai_processor.build_fallback_title(paper.title_original)
                if localized_title.startswith("待翻译："):
                    fallback_count += 1
                paper.title_zh = localized_title
                updated += 1

            db.commit()
            print(
                f"[backfill_title_zh] progress: {min(start + len(batch), total)}/{total} "
                f"(updated={updated}, fallback={fallback_count})"
            )

        remaining = db.query(Paper).filter(Paper.title_zh.like("待翻译：%")).count()
        print(f"Updated {updated} papers. Remaining fallback titles: {remaining}.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill `paper.title_zh` using the configured LLM provider.")
    parser.add_argument("--batch-size", type=int, default=20, help="Title localization batch size. Default: 20")
    args = parser.parse_args()
    main(batch_size=args.batch_size)
