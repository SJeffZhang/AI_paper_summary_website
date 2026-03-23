import traceback
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.domain import Paper, PaperSummary, SystemTaskLog
from app.services.crawler import Crawler
from app.services.filter import Filter
from app.services.ai_processor import AIProcessor

from app.services.scorer import Scorer

class Pipeline:
    """
    Orchestrator for the entire paper processing pipeline v2.0.
    """
    def __init__(self, db: Session):
        self.db = db
        self.crawler = Crawler()
        self.scorer = Scorer()
        self.ai_processor = AIProcessor()

    def run(self, target_date: str = None):
        """
        Execute the full pipeline for a given date (YYYY-MM-DD).
        """
        if target_date is None:
            # issue_date is today
            target_date = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")

        task_log = self.db.query(SystemTaskLog).filter(SystemTaskLog.issue_date == target_date).first()
        if task_log and task_log.status == "SUCCESS":
            print(f"Pipeline for {target_date} already succeeded. Skipping.")
            return

        if task_log:
            task_log.status = "RUNNING"
            task_log.error_log = None
            task_log.started_at = datetime.now()
            task_log.finished_at = None
        else:
            task_log = SystemTaskLog(issue_date=target_date, status="RUNNING")
            self.db.add(task_log)
        
        self.db.commit()

        try:
            # 1. Fetch with T+3 logic
            dt_issue = datetime.strptime(target_date, "%Y-%m-%d")
            fetch_date = (dt_issue - timedelta(days=3)).strftime("%Y-%m-%d")

            print(f"[{target_date}] Crawling papers for fetch_date: {fetch_date}...")
            raw_papers = self.crawler.fetch_papers(fetch_date=fetch_date)
            task_log.fetched_count = len(raw_papers)
            self.db.commit()

            if not raw_papers:
                print(f"No papers found for date {fetch_date}. Ending task.")
                task_log.status = "SUCCESS"
                task_log.finished_at = datetime.now()
                self.db.commit()
                return

            # 2. Score and Filter
            print(f"[{target_date}] Scoring {len(raw_papers)} papers...")
            scored_papers = [self.scorer.score_paper(p) for p in raw_papers]
            
            # Sort all papers by score descending to avoid dropping high-score papers
            sorted_by_score = sorted(scored_papers, key=lambda x: x["score"], reverse=True)
            
            # Select focus (Top 3-5) and watching (Next 8-12)
            focus_papers = sorted_by_score[:5]
            watching_papers = sorted_by_score[5:17] # Take next 12
            candidate_papers = sorted_by_score[17:] # All others
            
            for p in focus_papers: p["category"] = "focus"
            for p in watching_papers: p["category"] = "watching"
            for p in candidate_papers: p["category"] = "candidate" # Explicitly reset others

            # 3. AI Processing
            all_summaries = []
            
            def process_batch(papers, cat_label, min_count, max_count):
                if not papers: return []
                print(f"[{target_date}] AI Processing: {len(papers)} {cat_label} papers (target {min_count}-{max_count})...")
                
                # 3.1 Editor Stage (Max 2 retries)
                max_retries = 2
                editor_brief = None
                for attempt in range(max_retries + 1):
                    try:
                        print(f"[{target_date}] Editor stage (Attempt {attempt + 1})...")
                        editor_brief = self.ai_processor.run_editor(papers, min_count=min_count, max_count=max_count)
                        break
                    except ValueError as e:
                        if attempt < max_retries:
                            print(f"[{target_date}] Editor validation failed: {e}. Retrying...")
                            continue
                        raise e

                # 3.2 Writer -> Reviewer Loop (Max 2 retries)
                writer_history = []
                final_writer_output = None
                final_rejected_ids = []

                for attempt in range(max_retries + 1):
                    try:
                        print(f"[{target_date}] Writer stage (Attempt {attempt + 1})...")
                        writer_output = self.ai_processor.run_writer(editor_brief, papers, history=writer_history)
                        
                        print(f"[{target_date}] Reviewer stage (Attempt {attempt + 1})...")
                        review_result = self.ai_processor.run_reviewer(writer_output)
                        
                        if review_result["status"] == "PASSED":
                            final_writer_output = writer_output
                            final_rejected_ids = []
                            break
                        elif review_result["status"] == "REJECTED":
                            final_rejected_ids = review_result["rejected_ids"]
                            if attempt < max_retries:
                                writer_history.append({"role": "assistant", "content": writer_output})
                                writer_history.append({"role": "user", "content": f"Feedback: {review_result['raw_output']}\nRegenerate FULL report."})
                            else:
                                final_writer_output = writer_output
                        else:
                            raise ValueError("Reviewer status unparseable")
                    except Exception as e:
                        if attempt < max_retries:
                            print(f"[{target_date}] Writer/Reviewer stage failed: {e}. Retrying...")
                            writer_history.append({"role": "user", "content": f"Error occurred: {str(e)}. Please try again."})
                            continue
                        raise e

                results = self.ai_processor.parse_final_summaries(final_writer_output, final_rejected_ids)
                
                # Final Post-AI Validation: Ensure minimum count is met after rejections
                if len(results) < min_count:
                    raise ValueError(f"Batch {cat_label} failed: only {len(results)} papers passed AI/Review, but {min_count} are required.")
                
                for r in results: r["category"] = cat_label
                return results

            # Process Focus Batch: 3-5 papers (or fewer if candidate pool is small)
            f_min = min(3, len(focus_papers))
            all_summaries.extend(process_batch(focus_papers, "focus", min_count=f_min, max_count=5))
            
            # Process Watching Batch: 8-12 papers (or fewer if candidate pool is small)
            w_min = min(8, len(watching_papers))
            all_summaries.extend(process_batch(watching_papers, "watching", min_count=w_min, max_count=12))

            # 5. Persistence
            processed_count = 0
            
            # Step 5.1: Persist ALL scored papers as candidates first (if they don't exist)
            print(f"[{target_date}] Persisting {len(scored_papers)} candidates...")
            for meta in scored_papers:
                db_paper = self.db.query(Paper).filter(Paper.arxiv_id == meta["arxiv_id"]).first()
                if not db_paper:
                    db_paper = Paper(
                        arxiv_id=meta["arxiv_id"],
                        title=meta["title"],
                        title_en=meta.get("title_en"),
                        authors=meta["authors"],
                        abstract=meta["abstract"],
                        pdf_url=meta["pdf_url"],
                        upvotes=meta["upvotes"],
                        arxiv_publish_date=datetime.strptime(meta["arxiv_publish_date"], "%Y-%m-%d").date(),
                        score=meta["score"],
                        score_reasons=meta["score_reasons"],
                        category=meta["category"],
                        direction=meta["direction"]
                    )
                    self.db.add(db_paper)
                    self.db.flush()
                else:
                    # Update existing paper metadata if it already exists (e.g. from a previous crawl)
                    db_paper.score = meta["score"]
                    db_paper.score_reasons = meta["score_reasons"]
                    db_paper.category = meta["category"]
                    db_paper.direction = meta["direction"]
                    self.db.flush()

            # Step 5.2: Persist summaries for Focus and Watching papers
            for item in all_summaries:
                db_paper = self.db.query(Paper).filter(Paper.arxiv_id == item["arxiv_id"]).first()
                if not db_paper: continue # Should have been created above

                db_summary = self.db.query(PaperSummary).filter(
                    PaperSummary.paper_id == db_paper.id,
                    PaperSummary.issue_date == target_date
                ).first()
                
                if not db_summary:
                    db_summary = PaperSummary(
                        paper_id=db_paper.id,
                        one_line_summary=item["one_line_summary"],
                        one_line_summary_en=item.get("one_line_summary_en"),
                        core_highlights=item["core_highlights"],
                        core_highlights_en=item.get("core_highlights_en"),
                        application_scenarios=item["application_scenarios"],
                        application_scenarios_en=item.get("application_scenarios_en"),
                        issue_date=target_date
                    )
                    self.db.add(db_summary)
                    processed_count += 1

            task_log.processed_count = processed_count
            task_log.status = "SUCCESS"
            task_log.finished_at = datetime.now()
            self.db.commit()
            print(f"[{target_date}] Pipeline completed successfully. {processed_count} papers processed.")

        except Exception as e:
            self.db.rollback()
            task_log.status = "FAILED"
            task_log.error_log = traceback.format_exc()
            task_log.finished_at = datetime.now()
            self.db.commit()
            print(f"[{target_date}] Pipeline failed: {e}")
            raise e

if __name__ == "__main__":
    db = SessionLocal()
    try:
        pipeline = Pipeline(db)
        pipeline.run()
    finally:
        db.close()
