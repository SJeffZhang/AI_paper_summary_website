import argparse
import json
import re
import sys
from pathlib import Path

import pymysql

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from scripts._common import parse_database_url


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "database" / "schema.sql"
MIGRATION_PATH = Path(__file__).resolve().parents[2] / "database" / "migrate_v225.sql"
POST_SCHEMA_FIXES = [
    "ALTER TABLE `paper_summary` MODIFY COLUMN `one_line_summary` TEXT NULL",
    "ALTER TABLE `paper_summary` MODIFY COLUMN `one_line_summary_en` TEXT NULL",
    "ALTER TABLE `paper_ai_trace` MODIFY COLUMN `stage_status` ENUM('generated','accepted','rejected','invalid') NOT NULL",
]
EXPECTED_COLUMN_RULES = {
    "paper": {
        "id": {"type": "int", "null": "NO", "extra_contains": "auto_increment"},
        "arxiv_id": {"type": "varchar(50)", "null": "NO"},
        "title_zh": {"type": "varchar(500)", "null": "NO"},
        "title_original": {"type": "varchar(500)", "null": "NO"},
        "authors": {"type": "json", "null": "NO"},
        "venue": {"type": "varchar(255)", "null": "YES"},
        "abstract": {"type": "text", "null": "NO"},
        "pdf_url": {"type": "varchar(255)", "null": "NO"},
        "upvotes": {"type": "int", "null": "NO", "default": "0"},
        "arxiv_publish_date": {"type": "date", "null": "NO"},
        "created_at": {"type": "datetime", "null": "NO"},
    },
    "paper_summary": {
        "id": {"type": "int", "null": "NO", "extra_contains": "auto_increment"},
        "paper_id": {"type": "int", "null": "NO"},
        "issue_date": {"type": "date", "null": "NO"},
        "score": {"type": "int", "null": "NO", "default": "0"},
        "score_reasons": {"type": "json", "null": "YES"},
        "category": {"type": "enum('focus','watching','candidate')", "null": "NO"},
        "candidate_reason": {"type": "enum('low_score','capacity_overflow','reviewer_rejected')", "null": "YES"},
        "direction": {
            "type": (
                "enum('agent','reasoning','training_opt','rag','multimodal','code_intelligence',"
                "'vision_image','video','safety_alignment','robotics','audio','interpretability',"
                "'benchmarking','data_engineering','industry_trends')"
            ),
            "null": "NO",
        },
        "one_line_summary": {"type": "text", "null": "YES"},
        "one_line_summary_en": {"type": "text", "null": "YES"},
        "core_highlights": {"type": "json", "null": "YES"},
        "core_highlights_en": {"type": "json", "null": "YES"},
        "application_scenarios": {"type": "text", "null": "YES"},
        "application_scenarios_en": {"type": "text", "null": "YES"},
        "created_at": {"type": "datetime", "null": "NO"},
    },
    "paper_ai_trace": {
        "id": {"type": "int", "null": "NO", "extra_contains": "auto_increment"},
        "paper_summary_id": {"type": "int", "null": "NO"},
        "stage": {"type": "enum('editor','writer','reviewer')", "null": "NO"},
        "stage_status": {"type": "enum('generated','accepted','rejected','invalid')", "null": "NO"},
        "attempt_no": {"type": "int", "null": "NO", "default": "1"},
        "content": {"type": "text", "null": "NO"},
        "created_at": {"type": "datetime", "null": "NO"},
    },
    "subscriber": {
        "id": {"type": "int", "null": "NO", "extra_contains": "auto_increment"},
        "email": {"type": "varchar(255)", "null": "NO"},
        "status": {"type": "int", "null": "NO", "default": "0"},
        "verify_token": {"type": "varchar(64)", "null": "YES"},
        "unsub_token": {"type": "varchar(64)", "null": "YES"},
        "verify_expires_at": {"type": "datetime", "null": "YES"},
        "unsub_expires_at": {"type": "datetime", "null": "YES"},
        "created_at": {"type": "datetime", "null": "NO"},
        "updated_at": {"type": "datetime", "null": "NO", "extra_contains": "on update current_timestamp"},
    },
    "system_task_log": {
        "id": {"type": "int", "null": "NO", "extra_contains": "auto_increment"},
        "issue_date": {"type": "date", "null": "NO"},
        "status": {"type": "varchar(20)", "null": "NO"},
        "fetched_count": {"type": "int", "null": "NO", "default": "0"},
        "processed_count": {"type": "int", "null": "NO", "default": "0"},
        "error_log": {"type": "text", "null": "YES"},
        "started_at": {"type": "datetime", "null": "NO"},
        "finished_at": {"type": "datetime", "null": "YES"},
    },
    "notification_delivery_log": {
        "id": {"type": "int", "null": "NO", "extra_contains": "auto_increment"},
        "notification_type": {"type": "enum('daily_digest','job_alert')", "null": "NO"},
        "run_date": {"type": "date", "null": "NO"},
        "issue_date": {"type": "date", "null": "YES"},
        "recipient_email": {"type": "varchar(255)", "null": "NO"},
        "status": {"type": "enum('sent','failed','skipped')", "null": "NO"},
        "subject": {"type": "varchar(255)", "null": "NO"},
        "error_log": {"type": "text", "null": "YES"},
        "sent_at": {"type": "datetime", "null": "NO"},
    },
}
EXPECTED_INDEXES = {
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
EXPECTED_FOREIGN_KEYS = {
    "paper_summary": {"fk_paper_summary_paper_id"},
    "paper_ai_trace": {"fk_paper_ai_trace_summary_id"},
}
CJK_PATTERN = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF]")


def _connect(database: str | None = None):
    parsed = parse_database_url()
    socket_path = settings.MYSQL_UNIX_SOCKET.strip()

    kwargs = {
        "user": parsed.username or "root",
        "password": parsed.password or "",
        "charset": "utf8mb4",
        "autocommit": True,
    }
    if database is not None:
        kwargs["database"] = database

    if socket_path:
        kwargs["unix_socket"] = socket_path
    else:
        kwargs["host"] = parsed.host or "localhost"
        kwargs["port"] = int(parsed.port or 3306)

    return pymysql.connect(**kwargs)


def _iter_sql_statements(sql_text: str):
    buffer: list[str] = []
    for raw_line in sql_text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buffer.append(raw_line)
        if stripped.endswith(";"):
            yield "\n".join(buffer)
            buffer = []

    if buffer:
        yield "\n".join(buffer)


def _execute_sql_file(cursor, path: Path) -> None:
    sql_text = path.read_text(encoding="utf-8")
    for statement in _iter_sql_statements(sql_text):
        cursor.execute(statement)


def _normalize_default(value) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower()


def _collect_schema_snapshot(
    cursor,
) -> tuple[list[str], dict[str, dict[str, dict[str, str | None]]], dict[str, set[str]], dict[str, set[str]]]:
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    column_snapshot: dict[str, dict[str, dict[str, str | None]]] = {}
    index_snapshot: dict[str, set[str]] = {}
    foreign_key_snapshot: dict[str, set[str]] = {}

    for table in tables:
        cursor.execute(f"SHOW COLUMNS FROM `{table}`")
        column_snapshot[table] = {
            row[0]: {
                "type": str(row[1]).lower(),
                "null": str(row[2]).upper(),
                "key": str(row[3]).upper(),
                "default": _normalize_default(row[4]),
                "extra": str(row[5] or "").lower(),
            }
            for row in cursor.fetchall()
        }
        cursor.execute(f"SHOW INDEX FROM `{table}`")
        index_snapshot[table] = {str(row[2]) for row in cursor.fetchall()}
        cursor.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND REFERENCED_TABLE_NAME IS NOT NULL
            """,
            (table,),
        )
        foreign_key_snapshot[table] = {str(row[0]) for row in cursor.fetchall()}

    return tables, column_snapshot, index_snapshot, foreign_key_snapshot


def _find_schema_mismatches(
    column_snapshot: dict[str, dict[str, dict[str, str | None]]],
    index_snapshot: dict[str, set[str]],
    foreign_key_snapshot: dict[str, set[str]],
) -> list[str]:
    mismatches: list[str] = []

    for table, expected_columns in EXPECTED_COLUMN_RULES.items():
        if table not in column_snapshot:
            mismatches.append(f"missing table `{table}`")
            continue

        for column_name, rules in expected_columns.items():
            actual_column = column_snapshot[table].get(column_name)
            if actual_column is None:
                mismatches.append(f"missing column `{table}.{column_name}`")
                continue

            actual_type = str(actual_column["type"] or "")
            expected_type = str(rules["type"]).lower()
            if expected_type not in actual_type:
                mismatches.append(
                    f"column `{table}.{column_name}` expected type containing `{expected_type}` but got `{actual_type}`"
                )
            expected_null = str(rules["null"]).upper()
            if actual_column["null"] != expected_null:
                mismatches.append(
                    f"column `{table}.{column_name}` expected NULL={expected_null} but got `{actual_column['null']}`"
                )

            expected_default = rules.get("default")
            if expected_default is not None and actual_column["default"] != str(expected_default).lower():
                mismatches.append(
                    f"column `{table}.{column_name}` expected DEFAULT `{expected_default}` but got `{actual_column['default']}`"
                )

            extra_contains = rules.get("extra_contains")
            if extra_contains and str(extra_contains).lower() not in str(actual_column["extra"] or ""):
                mismatches.append(
                    f"column `{table}.{column_name}` expected EXTRA containing `{extra_contains}` but got `{actual_column['extra']}`"
                )

    for table, expected_index_names in EXPECTED_INDEXES.items():
        actual_index_names = index_snapshot.get(table, set())
        for index_name in expected_index_names:
            if index_name not in actual_index_names:
                mismatches.append(f"missing index `{table}.{index_name}`")

    for table, expected_foreign_keys in EXPECTED_FOREIGN_KEYS.items():
        actual_foreign_keys = foreign_key_snapshot.get(table, set())
        for foreign_key_name in expected_foreign_keys:
            if foreign_key_name not in actual_foreign_keys:
                mismatches.append(f"missing foreign key `{table}.{foreign_key_name}`")

    return mismatches


def _find_title_localization_violations(cursor) -> list[str]:
    cursor.execute("SELECT `arxiv_id`, `title_zh`, `title_original` FROM `paper`")
    violations: list[str] = []
    for arxiv_id, title_zh, title_original in cursor.fetchall():
        normalized_title_zh = str(title_zh or "").strip()
        normalized_title_original = str(title_original or "").strip()
        if not normalized_title_zh:
            violations.append(str(arxiv_id))
            continue
        if normalized_title_zh == normalized_title_original:
            violations.append(str(arxiv_id))
            continue
        if not CJK_PATTERN.search(normalized_title_zh):
            violations.append(str(arxiv_id))
    return violations


def _run_title_backfill() -> None:
    from scripts.backfill_title_zh import main as backfill_title_zh_main

    backfill_title_zh_main()


def ensure_database_ready(migrate_existing: bool = False, backfill_title_zh: bool = False) -> dict[str, object]:
    parsed = parse_database_url()
    database_name = parsed.database
    if not database_name:
        raise RuntimeError("DATABASE_URL must include a database name.")

    with _connect(database=None) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )

    migration_applied = False
    title_backfill_applied = False
    with _connect(database=database_name) as connection:
        with connection.cursor() as cursor:
            tables, column_snapshot, index_snapshot, foreign_key_snapshot = _collect_schema_snapshot(cursor)

            if not tables:
                _execute_sql_file(cursor, SCHEMA_PATH)
                for statement in POST_SCHEMA_FIXES:
                    cursor.execute(statement)
            else:
                mismatches = _find_schema_mismatches(column_snapshot, index_snapshot, foreign_key_snapshot)
                if mismatches and not migrate_existing:
                    mismatch_text = "; ".join(mismatches)
                    raise RuntimeError(
                        "Existing database schema does not match PRD v2.25: "
                        f"{mismatch_text}. Run `python scripts/setup_local_db.py --migrate-existing` "
                        "or apply `database/migrate_v225.sql` explicitly before treating the schema as ready."
                    )
                if mismatches and migrate_existing:
                    _execute_sql_file(cursor, MIGRATION_PATH)
                    migration_applied = True
                    _execute_sql_file(cursor, SCHEMA_PATH)
                    for statement in POST_SCHEMA_FIXES:
                        cursor.execute(statement)

            tables, column_snapshot, index_snapshot, foreign_key_snapshot = _collect_schema_snapshot(cursor)
            mismatches = _find_schema_mismatches(column_snapshot, index_snapshot, foreign_key_snapshot)
            if mismatches:
                mismatch_text = "; ".join(mismatches)
                raise RuntimeError(f"Database schema validation failed after setup: {mismatch_text}")

            title_localization_violations = _find_title_localization_violations(cursor)

    if title_localization_violations and not backfill_title_zh:
        sample_ids = ", ".join(title_localization_violations[:5])
        raise RuntimeError(
            "Localized title contract validation failed for existing paper data. "
            f"Found {len(title_localization_violations)} paper(s) with missing or non-Chinese `title_zh`, "
            f"for example: {sample_ids}. Run `python scripts/setup_local_db.py --backfill-title-zh` "
            "or `python scripts/backfill_title_zh.py` before treating the migrated database as fully ready."
        )

    if title_localization_violations and backfill_title_zh:
        _run_title_backfill()
        title_backfill_applied = True
        with _connect(database=database_name) as connection:
            with connection.cursor() as cursor:
                title_localization_violations = _find_title_localization_violations(cursor)
                if title_localization_violations:
                    sample_ids = ", ".join(title_localization_violations[:5])
                    raise RuntimeError(
                        "title_zh backfill finished, but localized title contract still fails for: "
                        f"{sample_ids}"
                    )

    return {
        "database_ready": True,
        "database": database_name,
        "tables": tables,
        "migration_applied": migration_applied,
        "schema_validated": True,
        "title_backfill_applied": title_backfill_applied,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ensure the local MySQL database schema matches PRD v2.25.")
    parser.add_argument(
        "--migrate-existing",
        action="store_true",
        help="Apply database/migrate_v225.sql before validating the schema.",
    )
    parser.add_argument(
        "--backfill-title-zh",
        action="store_true",
        help="Run scripts/backfill_title_zh.py if migrated legacy rows still violate the localized title contract.",
    )
    args = parser.parse_args()

    result = ensure_database_ready(
        migrate_existing=args.migrate_existing,
        backfill_title_zh=args.backfill_title_zh,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
