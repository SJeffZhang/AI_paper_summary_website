import traceback
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.domain import Paper, PaperSummary, SystemTaskLog
from app.services.crawler import Crawler
from app.services.filter import Filter
from app.services.ai_processor import AIProcessor

class Pipeline:
    """
    Orchestrator for the entire paper processing pipeline.
    Ensures idempotency and error handling.
    """
    def __init__(self, db: Session):
        self.db = db
        self.crawler = Crawler()
        self.filter = Filter(top_n=15)
        self.ai_processor = AIProcessor()

    def run(self, target_date: str = None):
        """
        Execute the full pipeline for a given date (YYYY-MM-DD).
        """
        if target_date is None:
            # Default to today (UTC+8) as the issue_date
            # Note: The PRD says 02:00 run for today's issue.
            target_date = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")

        # 1. Idempotency Check & Logging
        task_log = self.db.query(SystemTaskLog).filter(SystemTaskLog.issue_date == target_date).first()
        if task_log and task_log.status == "SUCCESS":
            print(f"Pipeline for {target_date} already succeeded. Skipping.")
            return

        if task_log:
            # Reset existing log for retry
            task_log.status = "RUNNING"
            task_log.error_log = None
            task_log.started_at = datetime.now()
            task_log.finished_at = None
        else:
            # Create new log
            task_log = SystemTaskLog(issue_date=target_date, status="RUNNING")
            self.db.add(task_log)
        
        self.db.commit()

        try:
            # 2. Crawl
            # Calculate fetch_date: issue_date - 1 day
            dt_issue = datetime.strptime(target_date, "%Y-%m-%d")
            fetch_date = (dt_issue - timedelta(days=1)).strftime("%Y-%m-%d")

            print(f"[{target_date}] Crawling papers for fetch_date: {fetch_date}...")
            raw_papers = self.crawler.fetch_papers(fetch_date=fetch_date)
            task_log.fetched_count = len(raw_papers)
            self.db.commit()

            if not raw_papers:
                raise Exception(f"No papers found for date {fetch_date}")

            # 3. Filter
            print(f"[{target_date}] Filtering top papers...")
            candidate_papers = self.filter.process(raw_papers)

            # 4. AI Processing (Editor -> Writer -> Reviewer)
            max_retries = 2
            
            # 4.1 Editor Stage (Max 2 retries)
            editor_brief = None
            for attempt in range(max_retries + 1):
                try:
                    print(f"[{target_date}] AI Processing: Editor stage (Attempt {attempt + 1})...")
                    editor_brief = self.ai_processor.run_editor(candidate_papers)
                    break
                except ValueError as e:
                    if attempt < max_retries:
                        print(f"[{target_date}] Editor validation failed: {e}. Retrying...")
                        continue
                    raise e

            # 4.2 Writer -> Reviewer Loop (Max 2 retries)
            writer_history = []
            final_writer_output = None
            final_rejected_ids = []

            for attempt in range(max_retries + 1):
                try:
                    print(f"[{target_date}] AI Processing: Writer stage (Attempt {attempt + 1})...")
                    writer_output = self.ai_processor.run_writer(editor_brief, candidate_papers, history=writer_history)
                    
                    print(f"[{target_date}] AI Processing: Reviewer stage (Attempt {attempt + 1})...")
                    review_result = self.ai_processor.run_reviewer(writer_output)
                    
                    if review_result["status"] == "PASSED":
                        print(f"[{target_date}] Reviewer: PASSED")
                        final_writer_output = writer_output
                        final_rejected_ids = []
                        break
                    elif review_result["status"] == "REJECTED":
                        final_rejected_ids = review_result["rejected_ids"]
                        print(f"[{target_date}] Reviewer: REJECTED. IDs: {final_rejected_ids}")
                        
                        if attempt < max_retries:
                            # Append to history for retry
                            writer_history.append({"role": "assistant", "content": writer_output})
                            writer_history.append({"role": "user", "content": f"Reviewer Feedback:\n{review_result['raw_output']}\n\nPlease regenerate the FULL report (including passed and corrected ones)."})
                        else:
                            print(f"[{target_date}] Reached max retries. Using last output with rejection list.")
                            final_writer_output = writer_output
                    else:
                        raise ValueError(f"Reviewer output could not be parsed.")

                except (ValueError, Exception) as e:
                    if attempt < max_retries:
                        print(f"[{target_date}] Writer/Reviewer validation failed: {e}. Retrying...")
                        # Optional: Add error to history for better correction
                        writer_history.append({"role": "user", "content": f"Correction required due to error: {str(e)}. Please try again following the format exactly."})
                        continue
                    raise e

            # Final Parsing
            final_summaries = self.ai_processor.parse_final_summaries(
                final_writer_output, 
                final_rejected_ids
            )

            if len(final_summaries) < 3:
                raise Exception(f"Final summary count {len(final_summaries)} < 3 minimum requirement.")

            # 5. Persistence
            print(f"[{target_date}] Persisting results to database...")
            processed_count = 0
            for item in final_summaries:
                # Find matching raw paper metadata
                meta = next((p for p in raw_papers if p["arxiv_id"] == item["arxiv_id"]), None)
                if not meta: continue

                # Insert or update Paper
                db_paper = self.db.query(Paper).filter(Paper.arxiv_id == meta["arxiv_id"]).first()
                if not db_paper:
                    db_paper = Paper(
                        arxiv_id=meta["arxiv_id"],
                        title=meta["title"],
                        authors=meta["authors"],
                        abstract=meta["abstract"],
                        pdf_url=meta["pdf_url"],
                        upvotes=meta["upvotes"],
                        arxiv_publish_date=datetime.strptime(meta["arxiv_publish_date"], "%Y-%m-%d").date()
                    )
                    self.db.add(db_paper)
                    self.db.flush() # Get id

                # Insert or update Summary
                db_summary = self.db.query(PaperSummary).filter(
                    PaperSummary.paper_id == db_paper.id,
                    PaperSummary.issue_date == target_date
                ).first()
                
                if not db_summary:
                    db_summary = PaperSummary(
                        paper_id=db_paper.id,
                        one_line_summary=item["one_line_summary"],
                        core_highlights=item["core_highlights"],
                        application_scenarios=item["application_scenarios"],
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
