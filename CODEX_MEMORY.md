# Codex Memory

## Purpose
This file is the persistent working memory for Codex in this project.
When continuing work in this repository, read this file first.

## Working Scope
- Primary role: review requirement documents, code, and implementation plans.
- Secondary role: perform the final Git commit/push after the user explicitly asks for it.
- Hard boundary: Codex only works on review and final commit/push in this project.
- File edit boundary: the only project file Codex may modify is `CODEX_MEMORY.md`; no other project file may be edited by Codex.
- Default review style: findings first, ordered by severity, then assumptions/questions, then a short summary.

## Current Repository State
- Checked on 2026-03-24.
- Project path: `/Users/zhangshijie/Desktop/Project/AI_paper_summary_website`
- Git repository initialized locally on branch `main`.
- Initial commit created: `1563259` (`chore: initialize project repository`)
- When the exact latest pushed commit matters, read it from `git log --oneline origin/main -1`.
- Global Git identity detected:
  - `user.name = Zhang Shijie`
  - `user.email = z1332556430@gmail.com`
- GitHub CLI is installed and authenticated.
- Active GitHub account: `Mr-silence`
- Git protocol: `https`

## Latest Review Target
- Files reviewed:
  - `backend/app/core/config.py`
  - `backend/app/db/session.py`
  - `backend/app/models/domain.py`
  - `backend/app/schemas/paper.py`
  - `backend/app/api/v1/papers.py`
  - `backend/app/api/v1/subscribe.py`
  - `backend/app/main.py`

## Latest PRD Status
- The PRD has now been rewritten into a v2.0 concept centered on T+3 cadence, 8-signal scoring, layered presentation, and bilingual output.
- The new PRD direction is strategically clear, but the document has become much less implementation-complete than the earlier frozen version.
- The current v2.0 review identified multiple new gaps between the rewritten PRD and the backend implementation.

## Latest Backend Review Status
- The previously reported backend initialization issues have been fixed:
  - the app now imports and starts successfully
  - `paper_summary` now includes the composite unique constraint on `(paper_id, issue_date)`
  - global exception handlers are now registered for JSON endpoints
  - the subscription verification redirect target now comes from `settings.FRONTEND_URL`
- Startup verification now passes with:
  - `cd backend && ./venv/bin/python -c "from app.main import app; print(app.title)"`
  - output: `AI Paper Summary API`
- The previously missing `GET /api/v1/rss` route is now implemented and registered.
- A backend-local `.gitignore` now excludes `venv/`, `.env`, and `__pycache__/`, which addresses the earlier repository hygiene concern for new commits.
- The current limiter risk has been explicitly accepted by the user for the demo stage:
  - `POST /api/v1/subscribe` uses an in-memory per-process IP limiter
  - this is acceptable for the current demo target
  - before production launch, the limiter should be upgraded to a shared-store design (for example Redis) to preserve the strict `5/hour/IP` contract across multi-worker or multi-instance deployments
- The latest pipeline review identified new implementation gaps in the AI batch workflow:
  - the prompt path issue has been fixed; `AIProcessor()` now initializes correctly from the `backend/` working directory
  - the crawl backfill date issue has been fixed; `Pipeline.run(target_date=...)` now computes `fetch_date = target_date - 1 day`
  - the crawler fallback-date `NameError` has been fixed by passing an explicit normalization fallback date
  - the previous strong-contract gaps around Editor retry, Writer retry, Reviewer reject-list validation, and strict final field parsing have now been addressed
  - the duplicate-ID enforcement gaps have now been addressed:
    - `run_editor()` now rejects duplicate selected IDs
    - `run_writer()` now rejects duplicate paper sections before doing set-equality validation
  - the latest review of those fixes did not identify new substantive pipeline findings
- The latest v2.0 backend/code review identified new issues in the upgraded architecture:
  - the previous gaps around crawler window size, score-overflow dropping, watching placeholders, and `title_en` schema/storage alignment have been addressed in code
  - the latest v2.1 review confirmed that several previously open v2 gaps are now fixed:
    - `process_batch()` has reintroduced the explicit Editor retry loop
    - `parse_final_summaries()` now treats both CN and EN sections as required, non-empty fields
    - `/api/v1/papers` list and detail responses now expose `title_en`
    - the frontend now includes a global CN/EN switch, layered home presentation, and new `sources` / `topic` routes
    - the pipeline now enforces a post-review minimum-count check before persisting a batch
    - the crawler now performs best-effort Semantic Scholar citation enrichment
    - the pipeline now persists the full scored candidate pool, not just summarized papers
    - `/api/v1/papers` now exposes server-side filters for `issue_date`, `direction`, `category`, and `include_candidates`
    - `Scorer` now includes implemented practitioner-relevance scoring
    - the `papers.py` import-time startup regression has been fixed by restoring `date` / `timedelta` imports
    - the pipeline now explicitly demotes non-selected scored papers back to `candidate`
    - `Sources.vue` and `Topic.vue` now implement server-side pagination instead of fixed top-100 local filtering
  - the current remaining v2.3 risks are:
    - the scoring engine is still not a fully realized 8-signal implementation:
      - the open-source-trending signal is now heuristic-only (`HF Daily` + `github.com` link), which still does not match the PRD's stated GitHub Trending signal
      - citation enrichment currently covers the top 150 by upvotes, so academic influence remains partial and biased rather than full-population
    - the new v2.0 PRD is strategically clear but has become much less implementation-complete than the earlier frozen PRD, especially around API and backend execution contracts

## Latest Frontend Review Status
- The frontend scaffold can build successfully with Vite.
- The earlier scaffold issues around global icon registration and leftover Vite template CSS have been corrected.
- After re-reading the updated PRD, the previous frontend findings about `issue_date` homepage queries and the dedicated archive page are no longer valid in their old form.
- The current frontend implementation is broadly aligned with the updated PRD's feed + pagination direction.
- There is still one document/code alignment caveat: PRD section 4.1 header wording still mentions archive/about/RSS navigation, while the actual current frontend header only exposes home + email subscription.
- The previous race-condition issue in homepage pagination has been fixed by adding stale-response protection.
- The frontend API integration now exists through a shared Axios request utility and `api/papers.js`.
- The previously reported runtime issues in the API-integrated frontend have been fixed:
  - the subscription dialog icon binding now uses the component object
  - the homepage now renders a visible empty state for empty/error results
  - the detail page now renders a visible empty/error state for failed loads
- The latest review of those fixes did not identify new substantive findings.
- Build verification still passes, but Vite continues to warn that the main production chunk is larger than 500 kB.

## Review Progress Summary
- Early review rounds identified major gaps in:
  - batch/date ownership
  - rerun idempotency
  - subscription security and compliance
  - API/data-model contract consistency
  - AI pipeline executability
- These were iteratively corrected in later PRD revisions.
- The latest accepted direction uses:
  - `issue_date` as the batch and frontend query key
  - MySQL uniqueness constraints for idempotency
  - double opt-in subscription and tokenized unsubscribe
  - strict API contract wording with explicit non-JSON exceptions
  - Hugging Face Daily Papers as the upstream source
  - a Markdown-based multi-agent AI pipeline

## Current AI Pipeline Snapshot
- Data source: Hugging Face Daily Papers.
- Crawler mapping is explicitly documented from HF fields to `arxiv_id`, `pdf_url`, `authors`, `upvotes`, and `arxiv_publish_date`.
- AI workflow uses three roles:
  - Editor
  - Writer
  - Reviewer
- Pipeline carrier format: structured Markdown, not JSON.
- Backend parsing strategy:
  - Markdown structure + regex extraction
  - strong validation at each stage
- Current validation rules captured in the PRD include:
  - Editor output IDs must be unique and must come from the Top 15 candidate set
  - Writer output ID set must exactly match the Editor-selected set before review
  - Reviewer output must include overall decision and a rejected-ID list
  - On Writer rewrites, the system requires a full-set output, not a partial patch output
  - If rejected items are discarded and the final kept count drops below 3, the batch fails and rolls back

## Prompt Assets
- Prompt files now exist under `backend/prompts/`:
  - `editor_prompt.md`
  - `writer_prompt.md`
  - `reviewer_prompt.md`
- Their structure is now aligned with the Markdown-carried AI pipeline in the PRD.

## Collaboration Notes From User
- User requested a Codex-only Markdown file under this project for persistent work summary/context.
- User expects Codex to focus on review work in this project and do the final Git commit/upload at the end.
- User added a hard constraint: Codex's work scope is limited to review and commit/push only.
- User added a hard constraint: Codex must not edit any project file other than `CODEX_MEMORY.md`.
- User requested repository initialization and GitHub repository creation/push.
- User explicitly wants this memory file to be kept up to date after each conversation turn in this project.
- On every future review request, re-read the current `Detailed_PRD.md` first and assess the whole system against the latest PRD, not just the files changed in the current round.
- User clarified the default review mode:
  - unless explicitly requested otherwise, review the PRD's own design quality, internal consistency, and planning risks
  - do not default to checking whether the current code matches the PRD

## Remote Repository Plan
- Intended remote repository name: `AI_paper_summary_website`
- Intended owner: `Mr-silence`
- Intended visibility by default: `private`

## Remote Repository Status
- GitHub repository created successfully.
- Remote URL: `https://github.com/Mr-silence/AI_paper_summary_website`
- Git remote name: `origin`
- Local branch `main` is tracking `origin/main`

## Working Tree Notes
- Current project work now includes frontend scaffold/build-out in addition to PRD iteration.
- The current frontend scaffold, frontend API integration, backend implementation, RSS support, and AI pipeline modules have now been pushed to `origin/main`.
- The backend implementation, frontend API integration, and AI pipeline modules now define the active repository baseline for future reviews.
- The backend now also includes `backend/app/api/v1/rss.py` and `backend/.gitignore`.
- The backend now also includes pipeline-related service modules under `backend/app/services/`:
  - `crawler.py`
  - `filter.py`
  - `ai_processor.py`
  - `pipeline.py`

## Latest Git Action Request
- On 2026-03-23, the user requested pushing the current PRD/frontend updates to GitHub.
- The requested commit message language is Chinese.
- The main push has been completed successfully.
- On 2026-03-24, the user requested pushing the latest frontend/backend/API/pipeline work, and that push has also completed successfully.
- On 2026-03-24, the user requested pushing the latest v2.3 closure work.
- The current local code commit for that request is `59d9916` (`功能：完善 v2.3 架构闭环与分页能力`).

## Memory Maintenance Rule
- At the end of each future conversation turn in this project, update `CODEX_MEMORY.md` if the project state, review conclusions, or collaboration rules have materially changed.

## Latest Conversation Update (2026-03-24)
- User restated the standing task:
  - Codex's primary job in this repository is PRD review.
  - Reviews should strictly assess the overall project plan, not just isolated code diffs.
  - `CODEX_MEMORY.md` must be updated after every conversation turn.
  - Codex's task is review only; do not proactively produce remediation checklists or implementation plans unless the user explicitly asks.
- Latest PRD review target:
  - `Detailed_PRD.md` v2.3
- Latest high-severity PRD findings:
  - The AI pipeline contract in `Detailed_PRD.md` no longer matches the live prompt/parser contract:
    - PRD Editor output says `### Focus` / `### Watching`
    - actual prompt/parser expect repeated `## 论文: [arxiv_id]` sections
    - PRD Writer output says `#### [arxiv_id]` with `Summary/Highlights/Scenarios`
    - actual prompt/parser expect bilingual `## [arxiv_id]` blocks with Chinese and English field labels
    - PRD Reviewer output says `Rejected: [ID_LIST]`
    - actual parser expects `整体结论` and `拒绝名单`
  - The task-level idempotency contract in the PRD says task identity is keyed by `fetch_date` with `PENDING/RUNNING/SUCCESS/FAILED`, but the implemented schema/runtime are keyed by `issue_date` and only use `RUNNING/SUCCESS/FAILED`.
  - The PRD database section is no longer self-consistent with the bilingual product contract or the actual schema:
    - `paper_summary` omits `application_scenarios_en`
    - the schema section omits the task-log table required by the earlier idempotency section
  - The PRD is still missing an explicit API contract section for the already-existing frontend/backend integration surface (`/papers`, detail, sources filters, subscribe/unsubscribe, RSS), so it cannot yet serve as the sole executable planning document for cross-layer work.

## Latest Review Follow-up (2026-03-24, PRD v2.3 re-review)
- Re-reviewed the updated `Detailed_PRD.md` against the live prompts, pipeline, schemas, APIs, and frontend routes.
- The previous major truth-sync gaps around AI output shapes, task keying by `issue_date`, schema completeness, and the existence of an API section have been materially improved.
- Remaining review findings after the re-sync:
  - The Editor-stage business flow in the PRD still does not match runtime selection ownership:
    - PRD says Editor input is Top 30 candidates and describes Focus/Watching counts at that stage
    - actual pipeline first slices scored papers into `focus_papers[:5]` and `watching_papers[5:17]`, then calls the Editor separately for each batch
  - The Reviewer fallback semantics in the PRD are still broader than the code:
    - PRD implies that retry exhaustion leads to per-paper discard
    - actual code only does per-paper discard on a parsable final `REJECTED`
    - unparseable reviewer output or other writer/reviewer exceptions still fail the batch
  - The PRD still overstates unsubscribe token behavior:
    - PRD says activation and unsubscribe tokens are valid for 24 hours
    - actual `/api/v1/unsubscribe` does not check expiry and accepts any stored unsubscribe token
  - The API contract is still incomplete relative to the shipped surface:
    - PRD documents `/papers`, `/papers/{id}`, and `POST /subscribe`
    - current implementation also ships `GET /subscribe/verify`, `POST /unsubscribe`, and `GET /rss`
    - the response envelope fields `code` and `msg` are still omitted from the PRD API section

## Latest Review Follow-up (2026-03-24, PRD v2.3 single-source claim)
- Re-read the current `Detailed_PRD.md` after the user stated it is now the project's single source of truth.
- Current findings:
  - The API chapter still is not a fully truthful contract:
    - it omits the shipped `GET /api/v1/papers/{paper_id}` detail endpoint
    - it understates `GET /api/v1/papers` filters by omitting `category`, `limit`, and `include_candidates`
    - it documents `POST /unsubscribe?token=...`, while the implementation expects a JSON body `{token}`
  - The "统一响应格式" section is still overstated:
    - `GET /api/v1/subscribe/verify` returns an HTTP redirect
    - `GET /api/v1/rss` returns raw XML rather than the JSON `{code,msg,data}` envelope
  - The security/ops section still overstates runtime behavior:
    - unsubscribe tokens are documented as 24-hour tokens, but the live `/unsubscribe` path does not enforce expiry
    - rate limiting is documented for `/subscribe` related interfaces, but only `POST /subscribe` is actually rate-limited
    - external call timeouts are documented as `30s-60s`, while current implementation still includes `5s` and `15s` external timeouts
  - The database section still is not a complete schema source:
    - the `subscriber` table and its token/status fields are omitted from the PRD despite being required by the subscription flow

## Latest Review Follow-up (2026-03-24, PRD rewrite + geminicli sync)
- Re-reviewed the latest `Detailed_PRD.md` and `geminicli.md` against the current codebase after the user claimed full truth alignment.
- Current findings:
  - The documented 24h unsubscribe-token rule is still not true in runtime for verified subscribers:
    - `verify_subscription()` clears `token_expires_at`
    - `unsubscribe()` only rejects when `token_expires_at` exists and is expired
    - therefore a verified subscriber's unsubscribe token no longer has an enforceable expiry
    - `geminicli.md` currently records this as already implemented, which is also inaccurate
  - The Reviewer retry/failure semantics in the PRD are still stricter than the code:
    - the PRD says retry exhaustion makes the whole batch `FAILED`
    - the live pipeline still accepts a final parsable `REJECTED` result on the last attempt, drops rejected IDs, and only fails if the surviving count falls below the batch minimum
  - The PRD still cannot independently reconstruct the live database schema:
    - `paper` omits live fields such as `pdf_url`, `upvotes`, and `created_at`
    - `paper_summary` omits `created_at`
    - `subscriber` omits `created_at` and `updated_at`
    - `system_task_log` omits `started_at` and `finished_at`
    - `category` is described as `Enum`, while the live schema uses `VARCHAR(20)`
  - The timeout section is still incomplete relative to the running code:
    - it lists Semantic Scholar `5s`, arXiv `30s`, and Kimi `60s`
    - the live crawler also uses Hugging Face `30s` and GitHub Trending `15s`

## Latest Scope Clarification (2026-03-24)
- User explicitly corrected the review objective:
  - the task is to review the PRD itself
  - the default review target is PRD design quality, not implementation conformance

## Latest PRD-Only Review (2026-03-24)
- Re-reviewed the latest `Detailed_PRD.md` as a pure PRD/design artifact, without using current code conformance as the default evaluation standard.
- Current design findings:
  - The PRD still mixes immutable paper metadata with issue-scoped ranking state:
    - `paper` is globally unique by `arxiv_id`
    - but `score`, `score_reasons`, `category`, and `direction` are defined on that same global entity
    - this design weakens historical reproducibility for issue-based transparency and future rerun/versioned scoring needs
  - The subscription model still couples two token lifecycles into one expiry field:
    - `subscriber` carries both `verify_token` and `unsubscribe_token`
    - but only one shared `token_expires_at`
    - this is an unstable design for two distinct security flows
  - The PRD still lacks an explicit publishability threshold after Reviewer attrition:
    - it promises Top 15-20 and defines Focus/Watching slices
    - but it does not specify the minimum surviving counts required for a valid published issue after rejects or low-supply days
  - The scoring spec still contains boundary ambiguity:
    - community popularity buckets are written as `10-50`, `50-100`, `100+`
    - boundary inclusion at `50` and `100` is not explicitly defined
  - `direction` is modeled as a first-class field and API filter, but the PRD still does not define a canonical taxonomy or enum list for it
