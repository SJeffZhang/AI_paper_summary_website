# Codex Memory

## Purpose
This file is the persistent working memory for Codex in this project.
When continuing work in this repository, read this file first.

## Working Scope
- Primary role: review requirement documents, code, and implementation plans.
- Secondary role: perform the final Git commit/push after the user explicitly asks for it.
- Default review style: findings first, ordered by severity, then assumptions/questions, then a short summary.

## Current Repository State
- Checked on 2026-03-23.
- Project path: `/Users/zhangshijie/Desktop/Project/AI_paper_summary_website`
- Git repository initialized locally on branch `main`.
- Global Git identity detected:
  - `user.name = Zhang Shijie`
  - `user.email = z1332556430@gmail.com`
- GitHub CLI is installed, but `gh auth status` showed no active login.

## Latest Review Target
- File reviewed: `Detailed_PRD.md`

## Latest Findings
1. [P1] Batch time window is not clearly defined.
   - The PRD mixes "past 24 hours", "run every day at 02:00", and date-based frontend queries.
   - It does not define a fixed timezone, batch ownership date, or the mapping between arXiv `published_date` and summary `publish_date`.

2. [P1] Idempotency is missing for reruns.
   - `paper` has unique `arxiv_id`, but `paper_summary` does not define a uniqueness rule such as `(paper_id, publish_date)`.
   - Task reruns or manual backfills can generate duplicate homepage items, RSS items, and emails.

3. [P1] Subscription and unsubscribe flow lacks security/compliance design.
   - The API only accepts `email + action`.
   - There is no email confirmation, signed unsubscribe token, or abuse/rate-limit design.

4. [P2] API contract and data model are inconsistent.
   - The PRD defines a unified response envelope, but examples only show the `data` fragment.
   - `core_highlights` is described ambiguously across endpoints.
   - `published_date` and `publish_date` are mixed.

5. [P2] Filter and AI processing rules are not executable enough yet.
   - The PRD does not define the institution source, scoring formula, thresholds, JSON parsing fallback, timeout/retry policy, quota limits, or cost controls.

## Review Notes
- The PRD direction is reasonable.
- It is not implementation-frozen yet.
- The most likely rework areas are:
  - batch/date model
  - rerun idempotency
  - subscription confirmation/unsubscribe flow
  - frontend/backend schema contract

## Collaboration Notes From User
- User requested a Codex-only Markdown file under this project for persistent work summary/context.
- User expects Codex to focus on review work in this project and do the final Git commit/upload at the end.
- User requested repository initialization and GitHub repository creation/push.
