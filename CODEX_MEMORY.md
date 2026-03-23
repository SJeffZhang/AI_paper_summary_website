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
- Checked on 2026-03-23.
- Project path: `/Users/zhangshijie/Desktop/Project/AI_paper_summary_website`
- Git repository initialized locally on branch `main`.
- Initial commit created: `1563259` (`chore: initialize project repository`)
- Latest pushed commit: `0d831d5` (`前端：搭建基础框架并同步需求文档`)
- Global Git identity detected:
  - `user.name = Zhang Shijie`
  - `user.email = z1332556430@gmail.com`
- GitHub CLI is installed and authenticated.
- Active GitHub account: `Mr-silence`
- Git protocol: `https`

## Latest Review Target
- Files reviewed:
  - `frontend/src/main.js`
  - `frontend/src/router/index.js`
  - `frontend/src/App.vue`
  - `frontend/src/views/Home.vue`
  - `frontend/src/views/Detail.vue`
  - `frontend/src/views/Unsubscribe.vue`
  - `frontend/src/style.css`
  - `frontend/package.json`

## Latest PRD Status
- The PRD has gone through multiple review rounds and is now considered implementation-ready.
- The latest review did not produce new substantive findings.
- The current design direction is stable enough to start building.
- The frontend-facing PRD has been updated from date-switching homepage behavior to a feed-style homepage with `page`/`limit` pagination.

## Latest Frontend Review Status
- The frontend scaffold can build successfully with Vite.
- The earlier scaffold issues around global icon registration and leftover Vite template CSS have been corrected.
- After re-reading the updated PRD, the previous frontend findings about `issue_date` homepage queries and the dedicated archive page are no longer valid in their old form.
- The current frontend implementation is broadly aligned with the updated PRD's feed + pagination direction.
- There is still one document/code alignment caveat: PRD section 4.1 header wording still mentions archive/about/RSS navigation, while the actual current frontend header only exposes home + email subscription.
- The previous race-condition issue in homepage pagination has been fixed by adding stale-response protection.
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
- The current frontend scaffold, PRD updates, and project notes have been pushed to `origin/main`.
- Only `CODEX_MEMORY.md` has a new local sync update after that push.

## Latest Git Action Request
- On 2026-03-23, the user requested pushing the current PRD/frontend updates to GitHub.
- The requested commit message language is Chinese.
- The main push has been completed successfully.

## Memory Maintenance Rule
- At the end of each future conversation turn in this project, update `CODEX_MEMORY.md` if the project state, review conclusions, or collaboration rules have materially changed.
