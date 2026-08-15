import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import SessionLocal
from app.models.domain import Paper, PaperSummary
from app.services.affiliation_enricher import AffiliationEnricher


@dataclass
class PaperAffiliationBackfillResult:
    paper_id: int
    arxiv_id: str
    categories: list[str]
    status: str
    attempts: int
    affiliation_count: int
    affiliations: list[str]
    updated: bool
    reasons: list[str]


def _parse_date(value: Optional[str]):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _parse_csv_ints(value: Optional[str]) -> set[int]:
    if not value:
        return set()
    return {int(item.strip()) for item in value.split(",") if item.strip()}


def _parse_csv_strings(value: Optional[str]) -> set[str]:
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def _has_any_affiliation(affiliations) -> bool:
    for affiliation in affiliations or []:
        if str(affiliation or "").strip():
            return True
    return False


def _candidate_query(db, *, start_date=None, end_date=None, paper_ids=None, arxiv_ids=None):
    query = db.query(Paper, PaperSummary.category).join(PaperSummary)
    query = query.filter(PaperSummary.category.in_(("focus", "watching")))
    if start_date:
        query = query.filter(PaperSummary.issue_date >= start_date)
    if end_date:
        query = query.filter(PaperSummary.issue_date <= end_date)
    if paper_ids:
        query = query.filter(Paper.id.in_(paper_ids))
    if arxiv_ids:
        query = query.filter(Paper.arxiv_id.in_(arxiv_ids))
    return query.order_by(Paper.id.asc(), PaperSummary.issue_date.asc())


def _collect_candidate_rows(db, *, start_date=None, end_date=None, paper_ids=None, arxiv_ids=None):
    deduped: dict[int, dict[str, object]] = {}
    for paper, category in _candidate_query(
        db,
        start_date=start_date,
        end_date=end_date,
        paper_ids=paper_ids,
        arxiv_ids=arxiv_ids,
    ).all():
        entry = deduped.setdefault(int(paper.id), {"paper": paper, "categories": []})
        categories = entry["categories"]
        if category not in categories:
            categories.append(category)
    return list(deduped.values())


def backfill_affiliations(
    *,
    start_date=None,
    end_date=None,
    paper_ids: Optional[set[int]] = None,
    arxiv_ids: Optional[set[str]] = None,
    apply: bool = False,
    include_existing: bool = False,
    limit: Optional[int] = None,
) -> dict[str, object]:
    def log_progress(event: str, payload: dict[str, object]) -> None:
        reason_text = "; ".join(str(reason) for reason in payload.get("reasons", []) or [])
        suffix = ""
        if reason_text:
            suffix += f" reasons={reason_text}"
        if "affiliation_count" in payload:
            suffix += f" affiliation_count={payload.get('affiliation_count', 0)}"
        print(
            (
                f"[affiliation-backfill] attempt event={event} "
                f"arxiv_id={payload.get('arxiv_id', '')} "
                f"attempt={payload.get('attempt', '-')}/{payload.get('max_attempts', '-')}"
                f"{suffix}"
            ),
            flush=True,
        )

    enricher = AffiliationEnricher(progress_callback=log_progress)
    results: list[PaperAffiliationBackfillResult] = []
    scanned = 0
    candidates = 0
    updated = 0

    db = SessionLocal()
    try:
        rows = _collect_candidate_rows(
            db,
            start_date=start_date,
            end_date=end_date,
            paper_ids=paper_ids or set(),
            arxiv_ids=arxiv_ids or set(),
        )
        filtered_rows = []
        for row in rows:
            paper = row["paper"]
            scanned += 1
            if _has_any_affiliation(paper.affiliations) and not include_existing:
                continue
            filtered_rows.append(row)
            if limit is not None and len(filtered_rows) >= limit:
                break

        candidates = len(filtered_rows)
        print(
            (
                f"[affiliation-backfill] dry_run={not apply} scanned={scanned} "
                f"candidates={candidates} apply={apply}"
            ),
            flush=True,
        )

        for index, row in enumerate(filtered_rows, start=1):
            paper = row["paper"]
            categories = list(row["categories"])
            print(
                (
                    f"[affiliation-backfill] {index}/{candidates} start "
                    f"paper_id={paper.id} arxiv_id={paper.arxiv_id} categories={','.join(categories)}"
                ),
                flush=True,
            )
            payload = {
                "arxiv_id": paper.arxiv_id,
                "title_original": paper.title_original,
                "authors": paper.authors,
                "pdf_url": paper.pdf_url,
            }
            result = enricher.enrich_paper(payload)
            should_update = apply and result.status == "overwrite_applied"
            if should_update:
                paper.affiliations = result.affiliations
                updated += 1
            print(
                (
                    f"[affiliation-backfill] {index}/{candidates} done "
                    f"paper_id={paper.id} arxiv_id={paper.arxiv_id} "
                    f"status={result.status} attempts={int(result.attempts or 0)} "
                    f"affiliation_count={int(result.affiliation_count or 0)} "
                    f"affiliations={'; '.join(result.affiliations) if result.affiliations else '-'} "
                    f"updated={bool(should_update)} reasons={'; '.join(result.reasons) if result.reasons else '-'}"
                ),
                flush=True,
            )

            results.append(
                PaperAffiliationBackfillResult(
                    paper_id=int(paper.id),
                    arxiv_id=paper.arxiv_id,
                    categories=categories,
                    status=result.status,
                    attempts=int(result.attempts or 0),
                    affiliation_count=int(result.affiliation_count or 0),
                    affiliations=list(result.affiliations),
                    updated=bool(should_update),
                    reasons=list(result.reasons),
                )
            )

        if apply:
            db.commit()
        else:
            db.rollback()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {
        "dry_run": not apply,
        "scanned": scanned,
        "candidates": candidates,
        "updated": updated,
        "results": [asdict(result) for result in results],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill paper-level institutions from first-page PDF text.")
    parser.add_argument("--start-date", help="Inclusive issue_date lower bound, YYYY-MM-DD.")
    parser.add_argument("--end-date", help="Inclusive issue_date upper bound, YYYY-MM-DD.")
    parser.add_argument("--paper-id", help="Comma-separated paper IDs to process.")
    parser.add_argument("--arxiv-id", help="Comma-separated arXiv IDs to process.")
    parser.add_argument("--limit", type=int, help="Maximum number of candidate papers to process.")
    parser.add_argument(
        "--include-existing",
        action="store_true",
        help="Also re-extract papers that already have at least one paper-level affiliation.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist successful validated paper-level affiliation updates. Omit for dry-run mode.",
    )
    args = parser.parse_args()

    result = backfill_affiliations(
        start_date=_parse_date(args.start_date),
        end_date=_parse_date(args.end_date),
        paper_ids=_parse_csv_ints(args.paper_id),
        arxiv_ids=_parse_csv_strings(args.arxiv_id),
        apply=bool(args.apply),
        include_existing=bool(args.include_existing),
        limit=args.limit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
