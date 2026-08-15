# Test Layout

This repository uses a single root `tests/` directory.

## Directories

- `tests/backend/unit/`: pure logic tests with mocked dependencies only
- `tests/backend/integration/`: API and database integration tests with isolated test databases
- `tests/live/`: real external network tests for `backend/app/services/crawler.py` only
- `tests/smoke/`: repository-level smoke checks such as backend import, compile, and frontend build
- `tests/frontend/`: Vue page-level tests driven by mocked API responses
- `tests/fixtures/`: shared mock payloads and sample data

## Default Commands

- Backend default run:
  `cd backend && ./venv/bin/pytest ../tests/backend ../tests/live ../tests/smoke`
- Backend offline run:
  `cd backend && ./venv/bin/pytest -m "not live" ../tests/backend ../tests/live ../tests/smoke`
- Frontend test run:
  `cd frontend && npm run test:run`

## Live Test Policy

Live tests always hit real external services. They do not use recorded responses or on-disk caches.

- Hugging Face Daily Papers: strong failure on request failure, empty response, or malformed fields
- arXiv: strong failure on request failure, empty response, or malformed fields
- GitHub Trending: strong failure on request failure, empty response, or malformed fields
- Semantic Scholar: degradable, only requires the crawler path to return an integer `>= 0`
- `tests/live/` does not cover real LLM calls, `run_pipeline_once.py`, local MySQL bootstrap, API assertions, or frontend page integration. Those are validated separately via scripts and manual/browser checks.

## Notes

- Live tests intentionally make backend test runs dependent on network availability.
- Frontend tests stay mock-based and do not call the real backend.
