from scripts.setup_local_db import _find_schema_mismatches, _find_title_localization_violations


def test_find_schema_mismatches_accepts_current_v225_sentinels():
    column_snapshot = {
        "paper": {
            "id": {"type": "int", "null": "NO", "key": "PRI", "default": None, "extra": "auto_increment"},
            "arxiv_id": {"type": "varchar(50)", "null": "NO", "key": "UNI", "default": None, "extra": ""},
            "title_zh": {"type": "varchar(500)", "null": "NO", "key": "", "default": None, "extra": ""},
            "title_original": {"type": "varchar(500)", "null": "NO", "key": "", "default": None, "extra": ""},
            "authors": {"type": "json", "null": "NO", "key": "", "default": None, "extra": ""},
            "venue": {"type": "varchar(255)", "null": "YES", "key": "", "default": None, "extra": ""},
            "abstract": {"type": "text", "null": "NO", "key": "", "default": None, "extra": ""},
            "pdf_url": {"type": "varchar(255)", "null": "NO", "key": "", "default": None, "extra": ""},
            "upvotes": {"type": "int", "null": "NO", "key": "", "default": "0", "extra": ""},
            "arxiv_publish_date": {"type": "date", "null": "NO", "key": "MUL", "default": None, "extra": ""},
            "created_at": {"type": "datetime", "null": "NO", "key": "", "default": "current_timestamp", "extra": ""},
        },
        "paper_summary": {
            "id": {"type": "int", "null": "NO", "key": "PRI", "default": None, "extra": "auto_increment"},
            "paper_id": {"type": "int", "null": "NO", "key": "MUL", "default": None, "extra": ""},
            "issue_date": {"type": "date", "null": "NO", "key": "MUL", "default": None, "extra": ""},
            "score": {"type": "int", "null": "NO", "key": "", "default": "0", "extra": ""},
            "score_reasons": {"type": "json", "null": "YES", "key": "", "default": None, "extra": ""},
            "category": {
                "type": "enum('focus','watching','candidate')",
                "null": "NO",
                "key": "MUL",
                "default": None,
                "extra": "",
            },
            "candidate_reason": {
                "type": "enum('low_score','capacity_overflow','reviewer_rejected')",
                "null": "YES",
                "key": "",
                "default": None,
                "extra": "",
            },
            "direction": {
                "type": (
                    "enum('agent','reasoning','training_opt','rag','multimodal','code_intelligence',"
                    "'vision_image','video','safety_alignment','robotics','audio','interpretability',"
                    "'benchmarking','data_engineering','industry_trends')"
                ),
                "null": "NO",
                "key": "MUL",
                "default": None,
                "extra": "",
            },
            "one_line_summary": {"type": "text", "null": "YES", "key": "", "default": None, "extra": ""},
            "one_line_summary_en": {"type": "text", "null": "YES", "key": "", "default": None, "extra": ""},
            "core_highlights": {"type": "json", "null": "YES", "key": "", "default": None, "extra": ""},
            "core_highlights_en": {"type": "json", "null": "YES", "key": "", "default": None, "extra": ""},
            "application_scenarios": {"type": "text", "null": "YES", "key": "", "default": None, "extra": ""},
            "application_scenarios_en": {"type": "text", "null": "YES", "key": "", "default": None, "extra": ""},
            "created_at": {"type": "datetime", "null": "NO", "key": "", "default": "current_timestamp", "extra": ""},
        },
        "subscriber": {
            "id": {"type": "int", "null": "NO", "key": "PRI", "default": None, "extra": "auto_increment"},
            "email": {"type": "varchar(255)", "null": "NO", "key": "UNI", "default": None, "extra": ""},
            "status": {"type": "int", "null": "NO", "key": "MUL", "default": "0", "extra": ""},
            "verify_token": {"type": "varchar(64)", "null": "YES", "key": "UNI", "default": None, "extra": ""},
            "unsub_token": {"type": "varchar(64)", "null": "YES", "key": "UNI", "default": None, "extra": ""},
            "verify_expires_at": {"type": "datetime", "null": "YES", "key": "", "default": None, "extra": ""},
            "unsub_expires_at": {"type": "datetime", "null": "YES", "key": "", "default": None, "extra": ""},
            "created_at": {"type": "datetime", "null": "NO", "key": "", "default": "current_timestamp", "extra": ""},
            "updated_at": {
                "type": "datetime",
                "null": "NO",
                "key": "",
                "default": "current_timestamp",
                "extra": "on update current_timestamp",
            },
        },
        "paper_ai_trace": {
            "id": {"type": "int", "null": "NO", "key": "PRI", "default": None, "extra": "auto_increment"},
            "paper_summary_id": {"type": "int", "null": "NO", "key": "MUL", "default": None, "extra": ""},
            "stage": {
                "type": "enum('editor','writer','reviewer')",
                "null": "NO",
                "key": "MUL",
                "default": None,
                "extra": "",
            },
            "stage_status": {
                "type": "enum('generated','accepted','rejected','invalid')",
                "null": "NO",
                "key": "",
                "default": None,
                "extra": "",
            },
            "attempt_no": {"type": "int", "null": "NO", "key": "", "default": "1", "extra": ""},
            "content": {"type": "text", "null": "NO", "key": "", "default": None, "extra": ""},
            "created_at": {"type": "datetime", "null": "NO", "key": "", "default": "current_timestamp", "extra": ""},
        },
        "system_task_log": {
            "id": {"type": "int", "null": "NO", "key": "PRI", "default": None, "extra": "auto_increment"},
            "issue_date": {"type": "date", "null": "NO", "key": "UNI", "default": None, "extra": ""},
            "status": {"type": "varchar(20)", "null": "NO", "key": "", "default": None, "extra": ""},
            "fetched_count": {"type": "int", "null": "NO", "key": "", "default": "0", "extra": ""},
            "processed_count": {"type": "int", "null": "NO", "key": "", "default": "0", "extra": ""},
            "error_log": {"type": "text", "null": "YES", "key": "", "default": None, "extra": ""},
            "started_at": {"type": "datetime", "null": "NO", "key": "", "default": "current_timestamp", "extra": ""},
            "finished_at": {"type": "datetime", "null": "YES", "key": "", "default": None, "extra": ""},
        },
        "notification_delivery_log": {
            "id": {"type": "int", "null": "NO", "key": "PRI", "default": None, "extra": "auto_increment"},
            "notification_type": {
                "type": "enum('daily_digest','job_alert')",
                "null": "NO",
                "key": "MUL",
                "default": None,
                "extra": "",
            },
            "run_date": {"type": "date", "null": "NO", "key": "MUL", "default": None, "extra": ""},
            "issue_date": {"type": "date", "null": "YES", "key": "MUL", "default": None, "extra": ""},
            "recipient_email": {"type": "varchar(255)", "null": "NO", "key": "", "default": None, "extra": ""},
            "status": {
                "type": "enum('sent','failed','skipped')",
                "null": "NO",
                "key": "MUL",
                "default": None,
                "extra": "",
            },
            "subject": {"type": "varchar(255)", "null": "NO", "key": "", "default": None, "extra": ""},
            "error_log": {"type": "text", "null": "YES", "key": "", "default": None, "extra": ""},
            "sent_at": {"type": "datetime", "null": "NO", "key": "", "default": "current_timestamp", "extra": ""},
        },
    }
    index_snapshot = {
        "paper": {"PRIMARY", "uk_arxiv_id", "idx_publish_date"},
        "paper_summary": {"PRIMARY", "uk_paper_issue", "idx_issue_date", "idx_category", "idx_direction"},
        "paper_ai_trace": {"PRIMARY", "uk_trace_summary_stage_attempt", "idx_trace_summary_id", "idx_trace_stage"},
        "subscriber": {"PRIMARY", "uk_email", "uk_verify_token", "uk_unsub_token", "idx_status"},
        "system_task_log": {"PRIMARY", "uk_issue_date"},
        "notification_delivery_log": {
            "PRIMARY",
            "uk_notification_type_run_recipient",
            "idx_notification_type",
            "idx_notification_run_date",
            "idx_notification_issue_date",
            "idx_notification_status",
        },
    }
    foreign_key_snapshot = {
        "paper_summary": {"fk_paper_summary_paper_id"},
        "paper_ai_trace": {"fk_paper_ai_trace_summary_id"},
    }

    assert _find_schema_mismatches(column_snapshot, index_snapshot, foreign_key_snapshot) == []


def test_find_schema_mismatches_flags_old_schema_shapes():
    column_snapshot = {
        "paper": {
            "id": {"type": "int", "null": "NO", "key": "PRI", "default": None, "extra": "auto_increment"},
            "title": {"type": "varchar(255)", "null": "YES", "key": "", "default": None, "extra": ""},
            "title_en": {"type": "varchar(255)", "null": "YES", "key": "", "default": None, "extra": ""},
        },
        "paper_summary": {
            "paper_id": {"type": "int", "null": "NO", "key": "", "default": None, "extra": ""},
            "one_line_summary": {"type": "varchar(255)", "null": "YES", "key": "", "default": None, "extra": ""},
            "one_line_summary_en": {"type": "varchar(255)", "null": "YES", "key": "", "default": None, "extra": ""},
        },
        "subscriber": {
            "verify_token": {"type": "varchar(64)", "null": "YES", "key": "", "default": None, "extra": ""},
        },
        "system_task_log": {
            "issue_date": {"type": "date", "null": "NO", "key": "", "default": None, "extra": ""},
            "status": {"type": "varchar(20)", "null": "NO", "key": "", "default": None, "extra": ""},
        },
    }
    index_snapshot = {
        "paper_summary": set(),
    }
    foreign_key_snapshot = {
        "paper_summary": set(),
    }

    mismatches = _find_schema_mismatches(column_snapshot, index_snapshot, foreign_key_snapshot)

    assert any("paper.title_zh" in mismatch for mismatch in mismatches)
    assert any("paper.title_original" in mismatch for mismatch in mismatches)
    assert any("paper_summary.candidate_reason" in mismatch for mismatch in mismatches)
    assert any("paper_summary.one_line_summary" in mismatch for mismatch in mismatches)
    assert any("missing table `paper_ai_trace`" in mismatch for mismatch in mismatches)
    assert any("missing table `notification_delivery_log`" in mismatch for mismatch in mismatches)
    assert any("subscriber.unsub_token" in mismatch for mismatch in mismatches)
    assert any("system_task_log.error_log" in mismatch for mismatch in mismatches)
    assert any("paper_summary.uk_paper_issue" in mismatch for mismatch in mismatches)
    assert any("paper_summary.fk_paper_summary_paper_id" in mismatch for mismatch in mismatches)


def test_find_title_localization_violations_flags_missing_english_and_non_cjk_titles():
    class FakeCursor:
        def execute(self, _query):
            return None

        def fetchall(self):
            return [
                ("ok-1", "中文标题", "English Title"),
                ("bad-1", "", "English Title"),
                ("bad-2", "English Title", "English Title"),
                ("bad-3", "Localized English Title", "English Title"),
            ]

    violations = _find_title_localization_violations(FakeCursor())

    assert violations == ["bad-1", "bad-2", "bad-3"]
