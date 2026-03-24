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

## Latest Turn Note (2026-03-24)
- User repeated the request to review the PRD after restating the same "single source of truth" claim.
- Re-checked the current `Detailed_PRD.md`; the document content is unchanged from the immediately previous PRD-only review.
- Review conclusion for this turn is unchanged:
  - continue using the PRD-only design findings already recorded above

## Latest PRD-Only Review (2026-03-24, v2.4)
- Re-reviewed `Detailed_PRD.md` v2.4 strictly as a PRD/design artifact.
- The prior design issues around history traceability, publishability thresholds, token-lifecycle separation, interval ambiguity, and direction taxonomy definition have been materially improved.
- Remaining design findings:
  - Stage-1 Editor contract is still internally inconsistent:
    - section 4.1 says the system first slices candidates into Focus Top 5 and Watching Next 12 groups
    - but it then says the Editor outputs Focus (3-5) and Watching (8-12) lists
    - the same section only provides a per-paper regex, not a category-carrying output shape
  - The `paper_summary` table still mixes issue snapshot state with narrative content in a way that leaves candidate-row representation under-specified:
    - the PRD keeps `category = candidate` in the same table that stores bilingual summaries
    - but it does not define whether unselected candidates have nullable/empty/absent narrative fields
  - The quality baseline still under-specifies low-supply behavior before review attrition:
    - it defines failure when Reviewer removals drop counts below thresholds
    - but it does not state what happens when the pipeline never has enough viable Focus/Watching candidates in the first place
  - The API chapter still is not actually full coverage at the PRD level:
    - it omits explicit contracts for paper detail retrieval, subscription verification redirect, and RSS despite the user claiming full API closure
  - Direction taxonomy now exists, but assignment policy is still unspecified:
    - there is still no precedence or tie-break rule for papers that fit multiple directions

## Latest PRD-Only Review (2026-03-24, v2.5)
- Re-reviewed `Detailed_PRD.md` v2.5 strictly as a PRD/design artifact.
- The prior issues around Editor call mode, low-supply precheck, API surface coverage, and taxonomy precedence have been materially improved.
- Remaining design findings:
  - The category model is still internally inconsistent:
    - the quality baseline and low-supply policy define Focus/Watching supply with score thresholds (`Score >= 80`, `Score >= 50`)
    - but the same PRD also defines Focus and Watching as capped editorial batches (`[3,5]` and `[8,12]`) selected from top candidates
    - this leaves no deterministic rule when threshold-qualified papers exceed or conflict with the capped batch sizes
  - The scoring-engine spec has regressed from a full 8-signal contract to only partial rules:
    - the PRD now preserves the community-popularity interval and academic-influence formula
    - but it no longer defines the trigger logic for the other core signals or the enrichment-scope compromise in a self-contained way
  - The full-snapshot design still encodes missing editorial content as placeholder prose in summary fields:
    - candidate rows are required in `paper_summary`
    - but their narrative fields are populated with placeholder text rather than being modeled as absent/non-applicable content
    - this weakens downstream semantic clarity between true summaries and non-selected records
  - The API section is still more of an endpoint inventory than an executable contract:
    - it lists routes and a few params
    - but it still omits concrete response schemas, pagination envelope details, detail-route payload shape, and RSS item/feed structure

## Latest PRD-Only Review (2026-03-24, v2.6)
- Re-reviewed `Detailed_PRD.md` v2.6 strictly as a PRD/design artifact.
- The prior issues around taxonomy precedence, candidate NULL modeling, signal trigger restoration, and delivery-schema description have been materially improved.
- Remaining design findings:
  - The admission logic still leaves Focus/Watching overlap unresolved:
    - `Focus 池` is defined as `score >= 80`
    - `Watching 池` is defined as `score >= 50`
    - without an explicit exclusion rule, every Focus paper also belongs to Watching
    - this makes capacity slicing and post-review count semantics ambiguous
  - The database chapter has regressed from a full schema back to a partial schema:
    - section 2 still depends on both `paper` static metadata and task-level idempotency
    - but section 5 now only specifies `paper_summary` and `subscriber`
    - the PRD no longer independently defines the `paper` table or the task-log model needed for full reconstruction
  - The API chapter has also regressed from a full contract to partial payload notes:
    - it defines a generic JSON envelope, a detail payload field list, and RSS structure
    - but it no longer specifies the endpoint inventory and request/response contracts for list, subscribe, verify, and unsubscribe flows
  - Candidate snapshot nullability is still not fully propagated into the delivery contract:
    - section 5 allows candidate narrative fields to be `NULL`
    - but section 6's `PaperDetail` payload does not mark those fields as nullable or restrict detail retrieval to non-candidate records

## Latest PRD-Only Review (2026-03-24, v2.7)
- Re-reviewed `Detailed_PRD.md` v2.7 strictly as a PRD/design artifact.
- v2.7 materially improves tier overlap, full-table enumeration, and candidate NULL semantics, but it also regresses on several previously stabilized architecture contracts.
- Current design findings:
  - The PRD no longer contains an executable AI pipeline contract:
    - the document has dropped explicit Editor/Writer/Reviewer output shapes, parsing rules, retry rules, and rejection-handling protocol
    - this leaves the core content-production workflow under-specified
  - The PRD no longer defines batch/date semantics and task-level business rules in a first-class way:
    - `issue_date` appears in schema/API
    - but T+3 date ownership, fetch-date semantics, and task idempotency/rerun policy are no longer explicitly defined
  - The current failure policy can cause avoidable issue failure because no replenishment rule exists:
    - the PRD selects fixed-capacity top slices first
    - then fails the issue if Reviewer removals drop surviving counts below thresholds
    - but it does not specify whether remaining qualified candidates outside the initial slice should backfill before failure
  - `direction` remains an under-specified enum despite being a stored and filterable field:
    - the schema declares `direction` as an enum
    - the API exposes `direction` filtering
    - but the PRD no longer defines the canonical direction list or assignment policy

## Latest PRD-Only Review (2026-03-24, v2.8)
- Re-reviewed `Detailed_PRD.md` v2.8 strictly as a PRD/design artifact.
- v2.8 materially restores the missing AI pipeline, T+3 scheduling semantics, backfill existence, and canonical direction enum list.
- Remaining design findings:
  - The backfill workflow is still not executable end-to-end:
    - section 1.2 says replenishment selects the next paper and reruns `Writer -> Reviewer`
    - but section 4 still makes `Editor` the stage that produces the paper selection brief/angle for chosen items
    - the PRD does not define how a backfilled paper obtains its missing Editor-stage brief before Writer runs
  - The product-level distinction between Focus and Watching output depth is still not contractually represented:
    - section 1.2 says Focus gets "深度总结" while Watching gets "简要总结"
    - but section 4.2 gives both categories the exact same writer structure
    - the schema/API likewise expose one common summary shape, so the promised tier difference is not enforceable
  - The direction taxonomy is still not reproducible from the PRD alone:
    - section 3.3 defines enum order and says regex/keyword matching is used
    - but it does not publish the actual per-direction regexes/keyword sets
  - The API contract remains incomplete for list/mutation responses:
    - it defines a generic envelope and a detail-route nullability note
    - but still omits the concrete list-item schema, pagination fields, and success/error response bodies for subscribe/unsubscribe flows

## Latest PRD-Only Review (2026-03-24, v2.9)
- Re-reviewed `Detailed_PRD.md` v2.9 strictly as a PRD/design artifact.
- v2.9 materially improves backfill continuity, product-tier differentiation, taxonomy reproducibility, and API response examples.
- Remaining design findings:
  - The Reviewer contract is still not fully executable:
    - section 4.3 requires both overall decision and a rejected-ID list
    - but it only publishes the regex for extracting the overall decision
    - the rejected-list extraction/validation rule is still missing from the PRD
  - The Editor brief remains under-specified despite being a first-class pipeline artifact:
    - section 4.1 says Editor generates a dedicated editorial brief
    - but the output contract only requires `## 论文: [arxiv_id]`
    - required brief fields beyond the selected ID are still not formally defined
  - The "full physical schema" claim is still overstated:
    - many columns are listed without concrete SQL types/lengths/nullability details
    - this is especially true for `paper` text/url columns, `paper_summary` narrative fields, `subscriber` token/email columns, and `system_task_log` counters
  - The unified JSON envelope is still internally inconsistent:
    - success responses are documented as `{code,msg,data}`
    - the documented error response omits `data`

## Latest PRD-Only Review (2026-03-24, v2.10)
- Re-reviewed `Detailed_PRD.md` v2.10 strictly as a PRD/design artifact.
- v2.10 materially improves the Editor brief contract, Reviewer rejected-list regex, physical-schema detail, and JSON envelope consistency.
- Remaining design findings:
  - The Reviewer PASS-case contract is still ambiguous:
    - the output example says the rejected list is bracketed for IDs
    - but says "无则填 '无'"
    - the published regex only matches bracketed content
    - the PRD still does not explicitly say whether the PASS form is `无` or `[无]`
  - Selection authority is still split between the ranking layer and the Editor stage:
    - section 1.2 says the system takes Top 5 / Top 12 by score for summarization
    - section 4.1 still says Editor is responsible for selecting papers
    - the PRD does not make it explicit whether Editor is selecting or only briefing preselected papers
  - The Focus/Watching differentiation is now stated but not fully executable:
    - section 4.2 imposes different highlight-count and scenario-length rules
    - but the published extraction/validation rule still only checks that the six content blocks are non-empty
  - The "physical schema" remains partially compressed:
    - `one_line_summary(_en)`, `core_highlights(_en)`, and `application_scenarios(_en)` are still shorthand rather than explicit per-column rows
    - `category`/`direction` still mix `VARCHAR` types with `ENUM(...)` constraint wording in a way that is not fully DDL-grade

## Latest PRD-Only Review (2026-03-24, v2.11)
- Re-reviewed `Detailed_PRD.md` v2.11 strictly as a PRD/design artifact.
- v2.11 materially fixes the last major authority/parse ambiguities:
  - Scorer now owns paper selection explicitly
  - Reviewer PASS state is now `[]`
  - Writer tier auditing is now elevated from prompt guidance to backend-enforced contract
  - JSON envelope shape is now internally consistent
- Remaining design findings:
  - Bilingual alignment is still not fully contractualized:
    - the product promise is "双语对齐"
    - but the hard audit only constrains the Chinese `核心亮点` item count
    - there is still no parity rule ensuring `core_highlights` and `core_highlights_en` have the same cardinality or aligned structure
  - The lifecycle of `candidate` snapshots is still under-defined:
    - `paper_summary` and the list API treat `candidate` as a first-class category
    - but the PRD still does not explicitly define which papers become candidate rows
    - it is still unclear whether this includes only threshold-qualified-but-not-selected papers, reviewer-rejected papers, or every fetched paper outside the published set
  - The title field model remains semantically ambiguous:
    - `paper.title` is defined as "中文/原始标题"
    - `paper.title_en` is defined as "英文标题"
    - this leaves canonical ownership unclear when the source title is already English and weakens the bilingual-data contract for API consumers

## Latest Meta Assessment (2026-03-24)
- User asked whether the PRD review cycle shows real progress or just churn.
- Assessment:
  - There has been clear, material progress overall; this is not simple circular churn.
  - The trajectory is best described as "iterative hardening with occasional regression," not straight-line improvement.
  - Evidence:
    - early rounds had repeated P0/P1 structural defects in AI contracts, task idempotency, API completeness, and schema completeness
    - mid rounds sometimes regressed by over-compressing the PRD and dropping previously restored contracts
    - later rounds reintroduced those contracts and progressively moved issues from execution-breaking ambiguity to semantic/edge-case precision
    - by v2.11, no new P0-level break remained in the latest PRD-only review

## Latest PRD-Only Review (2026-03-24, v2.12)
- Re-reviewed `Detailed_PRD.md` v2.12 strictly as a PRD/design artifact.
- v2.12 does fix the three specific semantic issues called out in v2.11:
  - bilingual highlight-count symmetry is now explicit
  - candidate lifecycle is now much more explicitly defined
  - title fields are now semantically cleaner (`title_zh`, `title_original`)
- However, the document also regresses sharply by compressing previously restored executable contracts.
- Current design findings:
  - The AI pipeline contract has fallen back from executable to descriptive:
    - Editor no longer publishes a concrete per-paper output shape with an ID anchor
    - Writer no longer publishes the exact markdown block structure in a parser-grade form
    - Reviewer no longer publishes regex/strict parsing/failure semantics
  - The scoring and taxonomy chapters are no longer reproducible:
    - section 3.1 collapses eight signals into a one-line summary without trigger rules
    - section 3.2 collapses taxonomy into enum names only, dropping the keyword/priority assignment logic
  - The "physical schema" is no longer full-fidelity:
    - `subscriber` and `system_task_log` are absent
    - `paper_summary` narrative fields are compressed into "8-13"
    - this is no longer enough for independent physical reconstruction
  - The API contract has regressed from executable to inventory-level:
    - endpoints are listed
    - but request parameters, pagination fields, response payload structures, and mutation success/error bodies are no longer fully specified

## Latest PRD-Only Review (2026-03-24, v2.14)
- Re-reviewed `Detailed_PRD.md` v2.14 strictly as a PRD/design artifact.
- v2.14 materially restores the execution-grade detail that v2.12 had compressed away:
  - full AI-stage markdown templates are back
  - scoring/taxonomy rules are expanded again
  - `subscriber`/`system_task_log` and detailed API payloads are restored
  - the bilingual symmetry, candidate lifecycle, and `title_zh`/`title_original` semantic fixes are retained
- Remaining design findings:
  - The Writer contract is still not fully parser-grade:
    - section 4.2 defines the markdown shape and downstream audit rules
    - but it still does not publish the actual extraction rule/regex for the six text blocks
    - the PRD therefore assumes parsed fields without fully defining how they are deterministically extracted
  - The Editor contract is only partially validated:
    - section 4.1 publishes a regex for the per-paper ID anchor
    - but it does not define extraction/validation rules for `写作角度`, `核心痛点`, and `具体解法`
    - this leaves the most important brief content under-specified as a machine contract
  - Candidate state transition is still ambiguous under backfill:
    - section 1.2 says overflow papers are archived as `candidate`
    - the same overflow pool is later used for replenishment into Focus/Watching
    - the PRD does not explicitly define whether such papers are promoted by mutating `category`, duplicated elsewhere, or treated as candidate plus published simultaneously
  - The "100% DDL-grade" claim is still slightly overstated:
    - `category` and `direction` are typed as `VARCHAR(...)` while also marked `ENUM`
    - the PRD still does not state the exact physical mechanism (native ENUM vs CHECK constraint), so the schema is close to but not fully database-specific DDL

## Latest PRD-Only Review (2026-03-24, v2.15)
- Re-reviewed `Detailed_PRD.md` v2.15 strictly as a PRD/design artifact.
- v2.15 materially improves the parser-grade ambition:
  - Editor and Writer now publish explicit extraction regexes
  - backfill now defines an atomic `UPDATE`-based promotion path
  - the schema now commits to MySQL 8.0+ and native ENUM-style physical typing
- Remaining design findings:
  - The Writer parsing contract is self-contradictory:
    - the markdown template shows `- **核心亮点**:` immediately followed by a newline
    - but the published regex requires `: \n` (a literal space before newline)
    - the same contradiction exists for `Core Highlights`
  - Retry/failure semantics are no longer closed:
    - Editor and Writer say validation failure triggers retry
    - but the PRD no longer defines retry ceilings or terminal failure rules for those stages
    - Reviewer now has parse rules only, without the previously explicit retry/FAILED semantics
  - Candidate lifecycle still lacks the reverse state-transition rule:
    - the PRD now explicitly defines `candidate -> focus/watching` as an atomic update during backfill
    - but it still does not explicitly define how a previously written focus/watching row becomes `candidate` with narrative fields nulled after Reviewer rejection
  - The API chapter regresses from fully executable to partially executable:
    - list/detail endpoints are named
    - but query parameters, full detail payload shape, and error response contracts are no longer completely spelled out

## Latest PRD-Only Review (2026-03-24, v2.16)
- Re-reviewed `Detailed_PRD.md` v2.16 strictly as a PRD/design artifact.
- v2.16 does close the specific defects called out in v2.15:
  - the Writer colon/newline regex mismatch is fixed
  - retry ceilings and FAILED semantics are now explicit again
  - reverse state transition to `candidate` with narrative NULL reset is now documented
- However, the document regresses again by compressing previously restored executable detail.
- Current design findings:
  - The taxonomy chapter is no longer reproducible:
    - section 3.2 now gives only the enum order and names
    - it drops the per-direction keyword sets needed to independently classify papers
  - The AI contract is no longer fully explicit:
    - Editor and Writer no longer publish the concrete markdown output templates
    - Reviewer no longer publishes its extraction regexes
    - the PRD keeps parser fragments but loses the full end-to-end I/O contract
  - The database chapter is no longer full-fidelity:
    - `direction` is compressed to `ENUM(15项Taxonomy)`
    - `paper_summary` narrative columns are grouped into ranges
    - `subscriber` and `system_task_log` are collapsed into one-line summaries rather than full per-column definitions
  - The API chapter is no longer complete:
    - `/subscribe/verify` and `/rss` are missing
    - list/detail payloads are abbreviated again

## Latest PRD-Only Review (2026-03-24, v2.17)
- Re-reviewed `Detailed_PRD.md` v2.17 strictly as a PRD/design artifact.
- v2.17 materially restores most of the execution-grade detail that v2.16 had compressed:
  - taxonomy keyword sets are back
  - full AI markdown templates, parser regexes, and retry/FAILED semantics are back
  - full table definitions and full API inventory are back
- Remaining design findings:
  - The backfill pool still lacks an explicit exclusion rule for already rejected papers:
    - section 1.2 says Reviewer-rejected papers are migrated back to `candidate`
    - the same section says replenishment selects the next paper from the corresponding candidate pool by score order
    - the PRD still does not explicitly state that rejected papers are permanently ineligible for later backfill in the same issue
  - The AI parser contract still assumes an undefined "block" segmentation step:
    - Editor and Writer publish field-level regexes against `block`
    - but the PRD does not define the exact parser rule used to split a multi-paper output into per-paper blocks before those regexes run
  - The API contract for verification remains slightly incomplete:
    - `/api/v1/subscribe/verify` specifies the redirect behavior
    - but does not formally specify the required `token` query parameter

## Latest PRD-Only Review (2026-03-24, v2.18)
- Re-reviewed `Detailed_PRD.md` v2.18 strictly as a PRD/design artifact.
- v2.18 closes the three specific defects called out in v2.17:
  - rejected papers are now explicitly blacklisted from same-issue backfill
  - block splitting is now formally introduced
  - `/api/v1/subscribe/verify` now declares its required `token` parameter
- No new P0-grade execution break was found in this pass.
- Remaining design findings:
  - The block-splitting contract is still not fully deterministic:
    - both Editor and Writer define `re.split(...)` with a capturing group
    - but the PRD does not define how the resulting alternating array (`prefix`, `id`, `body`, ...) is recomposed into per-paper records before field regexes run
  - Candidate provenance is still not representable in the data model:
    - section 1.2 defines three distinct reasons a paper can become `candidate`
    - but `paper_summary.category` stores only a single `candidate` value with no reason/provenance field
    - this weakens the claimed source transparency of the archive layer
  - The "top institution" signal is still not independently reproducible:
    - section 3.1 references an internal "40+ institution list"
    - but the actual whitelist is not enumerated in the PRD, so separate implementations could diverge

## Latest PRD-Only Review (2026-03-24, v2.19)
- Re-reviewed `Detailed_PRD.md` v2.19 strictly as a PRD/design artifact.
- v2.19 closes the three specific auditability gaps called out in v2.18:
  - block splitting now includes an explicit `zip(blocks[1::2], blocks[2::2])` reconstruction rule
  - candidate provenance now has a physical `candidate_reason` field
  - the top-institution whitelist is now explicitly enumerated
- No new P0-grade break was found in this pass.
- Remaining design findings:
  - The block parser still lacks integrity validation:
    - the split+zip algorithm is now defined
    - but the PRD still does not require validating that the reconstructed record count and ID set exactly match the scorer/input list
    - malformed output could therefore still be silently truncated or partially accepted
  - `candidate_reason` lifecycle is still only half-closed:
    - reverse migration explicitly sets `candidate_reason = reviewer_rejected`
    - but forward promotion from `candidate` to `focus/watching` does not explicitly clear `candidate_reason`
    - this conflicts with the field note that the reason is only meaningful when `category = candidate`

## Latest PRD-Only Review (2026-03-24, v2.20)
- Re-reviewed `Detailed_PRD.md` v2.20 strictly as a PRD/design artifact.
- v2.20 closes the two specific consistency gaps called out in v2.19:
  - parser integrity checks now validate both record count and ID-set equality
  - forward promotion now explicitly clears `candidate_reason`
- No new P0/P1-grade execution break was found in this pass.
- Remaining design findings:
  - Matching scope/normalization is still under-specified for audit-critical keyword/whitelist rules:
    - the PRD now enumerates the institution whitelist and taxonomy keyword sets
    - but still does not formally define whether matching is case-insensitive, which text fields are searched, or what normalization/tokenization is applied
    - separate implementations could still diverge on edge cases
  - The initial write semantics for `candidate_reason` remain implicit rather than explicit:
    - reverse migration explicitly sets `candidate_reason = reviewer_rejected`
    - promotion explicitly clears it
    - but the PRD still does not directly state the insert-time write rule for setting `low_score` vs `capacity_overflow` when candidate rows are first created

## Latest PRD-Only Review (2026-03-24, v2.21)
- Re-reviewed `Detailed_PRD.md` v2.21 strictly as a PRD/design artifact.
- v2.21 closes the two specific P2 audit-precision gaps called out in v2.20:
  - matching protocol now formalizes case-insensitive, word-boundary matching plus field scope
  - candidate insert-time reasons (`low_score` / `capacity_overflow`) are now explicit atomic writes
- No regression to earlier parser/schema/API completeness was found in this pass.
- Remaining design findings:
  - The "top conference" signal is now tied to the wrong data scope:
    - the global matching protocol restricts keyword-based scoring signals to `title_original` and `abstract`
    - but the `ICLR/NeurIPS/CVPR/...` signal semantically represents venue acceptance/publication metadata, which is usually not encoded in title/abstract text
    - as specified, this signal is likely to underfire and not faithfully represent "顶会收录"
  - The "top institution" signal still lacks a durable schema anchor:
    - the matching protocol says it must run against author affiliations
    - but the database schema does not define a dedicated affiliations field, nor does it formalize that `authors` JSON must include affiliation strings
    - this weakens independent auditability of the institution score from stored data alone

## Latest PRD-Only Review (2026-03-24, v2.22)
- Re-reviewed `Detailed_PRD.md` v2.22 strictly as a PRD/design artifact.
- v2.22 closes the two specific data-source gaps called out in v2.21:
  - `paper` now has a durable `venue` anchor for the top-conference signal
  - `authors` JSON now explicitly includes `affiliation`, aligning the institution signal with stored data
- No new P0-grade or broad structural regression was found in this pass.
- Remaining design findings:
  - The scoring contract now contains an internal scope conflict for the "代码可用" signal:
    - section 3.1 says all remaining keyword-based scoring signals (other than institution/venue-special-cased ones) are matched against both `title_original` and `abstract`
    - but section 3.2 still defines "代码可用" specifically as the abstract containing `github.com` or `Official Code`
    - the PRD therefore gives two different source scopes for the same signal
  - `candidate_reason` nullability is explicit in schema but not fully propagated into the API contract:
    - the schema says `candidate_reason` must be `NULL` whenever `category != 'candidate'`
    - the list payload now exposes `candidate_reason`
    - but the API contract does not explicitly state that non-candidate rows must return `null` for this field

## Latest PRD-Only Review (2026-03-24, v2.23)
- Re-reviewed `Detailed_PRD.md` v2.23 strictly as a PRD/design artifact.
- v2.23 closes the two specific consistency gaps called out in v2.22:
  - the "代码可用" signal now aligns with the global matching scope
  - the API now explicitly states that non-candidate rows return `candidate_reason = null`
- No new P0/P1-grade break was found in this pass.
- Remaining design findings:
  - The regex matching protocol is still slightly under-specified for literal safety:
    - section 3.1 standardizes matching as `\bkeyword\b`
    - but does not explicitly state that keywords containing regex metacharacters must be escaped before interpolation
    - this matters for tokens such as `github.com`, where a bare `.` would otherwise be interpreted as a wildcard
  - The parser still tolerates out-of-band prose around canonical blocks:
    - Editor/Writer splitting rules say index 0 is expected to be empty and is skipped
    - but the PRD does not require failing when leading commentary or other non-empty out-of-band text appears outside the canonical templates

## Latest PRD-Only Review (2026-03-24, v2.24)
- Re-reviewed `Detailed_PRD.md` v2.24 strictly as a PRD/design artifact.
- v2.24 closes the two strictness gaps called out in v2.23:
  - keyword matching now explicitly requires literal escaping before regex assembly
  - Editor/Writer now enforce a zero-prefix failure rule before block reconstruction
- Remaining design findings:
  - The physical/API contract now contains literal field-name typos that break machine-readability:
    - `unsub_expires_at"` in `subscriber`
    - `issue_date"` in `system_task_log`
    - `limit"` in the list API params
    - `token"` in the verify API params
  - These are not cosmetic:
    - the document positions itself as executable physical/API spec
    - but these quoted field names would produce incorrect DDL or client contracts if implemented literally

## Latest PRD-Only Review (2026-03-24, v2.25)
- Re-reviewed `Detailed_PRD.md` v2.25 strictly as a PRD/design artifact.
- v2.25 does fix the literal field/param typo regressions introduced in v2.24.
- No new P0/P1-grade break was found in this pass.
- Remaining design findings:
  - The `candidate_reason` NULL contract is still not fully propagated to the list API:
    - the schema says `candidate_reason` must be `NULL` whenever `category != 'candidate'`
    - the list payload exposes `candidate_reason`
    - but the API contract only explicitly states the non-candidate-null rule for the detail route
  - The parser purity contract still only covers leading garbage, not all out-of-band text:
    - Editor and Writer now fail on non-empty `blocks[0]`
    - but the PRD still does not require failing on extra trailing or interstitial prose inside a reconstructed block if the expected fields still parse successfully

## Latest Session Decision (2026-03-24, ship)
- User explicitly judged the remaining issues as minor and requested immediate commit/push.
- Preserve the current review stance:
  - only two P2-level residual findings remain for `Detailed_PRD.md` v2.25
  - no P0/P1 blocker remains in the latest PRD-only review
- Operational instruction for this turn:
  - commit and push the current document set as-is
