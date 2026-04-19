# Codex CLI - 开发持久化记忆

## 1. 文件定位
- 本文件是 Codex 在本仓库中的长期开发记忆文件。
- 后续继续开发前，优先阅读本文件，再按需阅读 `geminicli.md` 与最新代码。
- 本文件于 2026-03-25 创建，首版内容基于 `geminicli.md` 继承整理。

## 2. 当前职责
- 当前角色：开发 AI（Codex）。
- 当前主任务：进行代码开发，覆盖前端 Vue 3、后端 FastAPI、数据库 MySQL 及相关工程配置。
- 可兼顾：实现、联调、修复、测试、文档同步、必要时做代码审查与提交准备。
- 以用户最新指令为准；若历史记忆与最新指令冲突，优先服从最新指令。

## 3. 继承来源与冲突处理
- 已继承来源：`geminicli.md`。
- 继承原则：保留 Gemini 已确认的项目事实、进展、架构约束、PRD 规则与下一步开发方向。
- 冲突处理：仓库内旧的 `CODEX_MEMORY.md` 含有“Codex 仅做 review”的历史约束；该约束与用户在 2026-03-25 明确下达的“Codex 进行代码开发”指令冲突，因此不作为当前开发职责依据，仅作历史参考。

## 4. 项目基础事实
- 项目路径：`/Users/zhangshijie/Desktop/Project/AI_paper_summary_website`
- 技术栈：
  - 前端：Vue 3
  - 后端：FastAPI
  - 数据库：MySQL
- 主要目录：
  - `frontend/`
  - `backend/`
  - `database/`
- 关键产品规格文档：`Detailed_PRD.md`

## 5. 核心开发戒律
- PRD 是当前产品与实现对齐的核心依据，变更时优先核对 `Detailed_PRD.md`。
- 对 `Detailed_PRD.md` 或其他核心文档做修改时，坚持无损修改原则：
  - 不得大幅删除、概括或压缩既有规格内容。
  - 应采用增量式补充或精准局部修订。
- 所有关键规则必须物理显式保留：
  - 正则表达式
  - 数据库定义
  - Taxonomy 关键词集
  - 关键 API / Pipeline 契约
- `paper_summary` 中 Candidate 的解读字段必须显式存储为 `NULL`。

## 6. 已继承的项目进展

### [2026-03-23] 第一阶段：需求分析与架构初始化
- 已完成初始 PRD 编写与项目目录结构创建。
- 已明确 FastAPI + Vue 3 + MySQL 技术栈。
- 已实现基础 API 路由：
  - `papers.py`
  - `subscribe.py`
- 已建立 SQLAlchemy 模型骨架。

### [2026-03-24] 第二阶段：v2.0+ 架构升级与评分引擎实装
- 已发布 `Detailed_PRD.md v2.0`，引入：
  - T+3 节奏
  - 8 类信号评分引擎
  - Focus / Watching 分层展示
- 已实现 `GET /api/v1/rss`。
- `Sources.vue` 与 `Topic.vue` 已支持服务端分页。
- 已接入 Semantic Scholar API，用于 Citations 信号。
- 已补齐 AI Pipeline 的 Markdown 契约、正则提取规则与三级幂等定义。
- 已找回并恢复以下规格内容：
  - 15 个分类方向关键词集
  - 全量 DDL 规格
  - API 详细 Payload
- 已加入：
  - 双语亮点项数强对齐审计
  - Candidate 物理 NULL 语义
- 已实现 GitHub Trending 专项爬虫，用真实开源热度数据驱动。
- 已修正部分物理 Schema 与 API 参数拼写问题。
- 已锁定正则安全规则：`re.escape`
- 已锁定 Parser 零前缀审计要求。

### [2026-03-25] 第三阶段：按 PRD v2.25 进行主干重构
- 已新增统一规格常量模块：`backend/app/core/specs.py`
  - 收敛评分阈值、容量、最低发布基线、15 类方向、候选原因与关键词白名单。
- 已完成数据库与 ORM 主模型重构：
  - `paper` 收敛为静态元数据表。
  - `paper_summary` 升级为以 `issue_date` 为核心的快照真相表。
  - `subscriber` 拆分为 `verify_token/verify_expires_at` 与 `unsub_token/unsub_expires_at`。
- 已重写 `database/schema.sql` 以对齐 PRD v2.25。
- 已补充一次性迁移脚本：`database/migrate_v225.sql`
  - 用于把旧版物理表结构迁移到 v2.25 结构。
- 已重写抓取与评分链路：
  - `crawler.py` 统一输出 `title_zh/title_original/authors/venue` 结构。
  - `scorer.py` 按 PRD 实装 `re.escape + 单词边界匹配`、8 类信号与 15 类方向分类。
- 已重写 AI 契约：
  - Editor 改为对锁定批次逐篇定调，不再负责选题。
  - Writer 强化双语字段完整性、亮点对称与 Focus/Watching 亮点数量校验。
  - Reviewer 收紧为严格两行输出格式。
- 已重写 `pipeline.py`：
  - 实装 `issue_date/fetch_date` 语义。
  - 实装 80/50 阈值切档。
  - 实装 Top 5 / Top 12 容量截断。
  - 实装 `low_score / capacity_overflow / reviewer_rejected` 候选原因。
  - 实装 Reviewer 拒稿后的 demotion、补位与黑名单规则。
  - 实装发布 3/8 基准线失败即任务失败。
- 已重写 API 查询面：
  - `/api/v1/papers` 与 `/api/v1/papers/{id}` 改为基于 `paper_summary` 快照查询。
  - RSS 仅输出 `focus/watching`。
  - 详情接口增加旧数据 `authors` 字符串数组的读时归一化兼容。
- 已同步前端字段：
  - 切换至 `title_zh/title_original`。
  - Candidate 明确显示 `candidate_reason`，不再伪造 narrative 占位文案。
  - `Sources.vue` 保留评分维度展示。
- 已完成本轮基础校验：
  - `python3 -m compileall backend/app` 通过。
  - `backend/venv/bin/python -c "from app.main import app; print(app.title)"` 通过。
  - `frontend npm run build` 通过。
  - 当前仍存在前端 chunk > 500 kB 的 Vite 体积警告，尚未处理。
- 已根据后续 review 再次修正 3 个关键问题：
  - 中文标题不再在抓取阶段直接回填英文原题；`pipeline.py` 现在会通过 `AIProcessor.localize_titles()` 先生成 `title_zh`，再入库。
  - 已新增历史数据修复脚本：`backend/scripts/backfill_title_zh.py`，用于批量回填既有英文 `title_zh`。
  - `unsubscribe` 已纳入与 `subscribe` 相同的写接口 IP 限流覆盖范围。
  - 运行时对 `verify_expires_at` / `unsub_expires_at` 改为“缺失即失效”，避免空过期时间绕过 24 小时约束。
  - `database/migrate_v225.sql` 已修正历史 `unsub_expires_at` 回填逻辑，不再把一部分旧 token 迁移成事实上的永久有效。
- 已根据新一轮 review 再次修正 2 个问题：
  - 活跃订阅用户重复调用 `/subscribe` 时，不再只返回“已订阅”；现在会刷新 `unsub_token` 与 `unsub_expires_at`，并发送新的管理/退订链接邮件，避免超过 24 小时后永久无法退订。
  - `AIProcessor.localize_titles()` 现在对 `title_zh` 执行更强校验：
    - 必须包含中文字符。
    - 不得与英文原题完全相同。
    - 重试时会把失败原因回灌给模型，减少“原样英文回传”通过校验的概率。

## 7. 当前待推进开发方向
- 执行真实数据库迁移并验证旧数据兼容性：
  - 在目标 MySQL 环境执行 `database/migrate_v225.sql` 或按其逻辑完成迁移。
  - 校验旧 `authors`、旧 `paper_summary` 与订阅 token 数据是否按预期完成回填。
- 进行全链路生产联调：
  - 配置 Kimi API Key。
  - 执行真实抓取、评分、AI 解析、Reviewer 拒稿补位与前端浏览链路验证。
- 评估前端体积优化：
  - 当前 build 可通过，但主 chunk 仍超过 Vite 默认 500 kB 告警线。

## 8. 持续维护规则
- 以后在本仓库每次完成重要开发、修复、架构调整或协作约束变化后，更新本文件。
- 更新时保留历史阶段记录，采用追加或局部修订，不丢弃已有开发上下文。

## 9. 最新进展记录

### [2026-04-20] 前端概念稿收口、真实后端联调与本地 MySQL 重建
- 当前工作分支：`codex/frontend-concept-redesign`。
- 已完成前端视觉重构概念稿：
  - 保留 Vue 3 + Vite 技术栈，不更换框架。
  - 首页、详情页、候选池页、分类页、退订页完成暖白/炭黑/低饱和强调色的编辑化视觉改造。
  - 移动端 Header 改为抽屉式导航，并补齐遮罩关闭、路由切换关闭、Esc 关闭与 body scroll lock。
  - 首页和详情页的方向标签已改为可点击入口，可直接跳转到对应方向页。
  - 失败的液态玻璃按钮方案已回滚；主按钮当前采用稳定纯黑高对比样式，移动端不启用复杂动态玻璃效果。
- 已新增运行时 mock 预览能力：
  - `VITE_USE_MOCK_BRIEF_DATA=true` 时使用 `frontend/src/mocks/` 数据。
  - 默认不设置该变量，正式运行和普通本地运行继续请求真实后端 API。
- 已重建本机 MySQL 环境：
  - 卸载旧 Oracle MySQL 与旧 Homebrew 数据目录。
  - 使用 Homebrew 安装 MySQL `9.6.0_2`。
  - 本地 root 密码设为 `password`。
  - `backend/scripts/setup_local_db.py` 已重新初始化 `ai_paper_summary` 数据库并通过 schema 校验。
- 为加速联调，已从生产服务器导出并导入最近有内容的两期数据：
  - `2026-04-18`: Focus 5、Watching 9、Candidate 26。
  - `2026-04-19`: Focus 5、Watching 10、Candidate 35。
  - 本地 `paper` 共 90 条，`paper_ai_trace` 共 145 条。
  - 本地 `system_task_log` 中两期均为 `SUCCESS`。
- 已完成真实后端接口联调：
  - 本地后端运行在 `127.0.0.1:8000`。
  - 本地前端运行在 `127.0.0.1:4173`，使用 `VITE_API_BASE_URL=http://127.0.0.1:8000`，未启用 mock。
  - `/api/v1/papers/calendar`、`/api/v1/papers`、`include_candidates=true` 候选池接口均返回真实本地 MySQL 数据。
- README 首页截图 `image/readme-home-v2.png` 已使用真实 API 数据重新截取，尺寸保持 `1365 x 900`。
- 重要踩坑记录：
  - `.mobile-only { display: block !important; }` 曾覆盖移动端按钮容器的 flex 布局，导致订阅按钮和菜单按钮垂直错位；后续不要把需要 flex 对齐的容器直接挂 `.mobile-only`。
  - 用户明确否定液态玻璃按钮方案；后续不要再恢复动态玻璃、黑色光晕或文字边缘发白的按钮效果。
 - 详情页事实卡字段已进一步收口：
   - 第二张信息卡不再展示 `venue`，而是展示 `authors[].affiliation` 聚合后的“作者单位”。
   - 已通过真实生产接口验证：论文 `paper_id=6652`（GameWorld）返回的 `authors[*].affiliation` 全为空字符串，且 `venue=null`；因此该字段缺失不是前端展示 bug，而是上游源数据未提供。
   - 前端当前策略为：有 affiliation 时做去空、去重、压缩展示；若源数据未提供，则明确展示“论文源未提供作者单位”，不再显示空白或误用 `venue` 冒充机构信息。
 - `Detailed_PRD.md` 已同步这条当前实现语义：
   - 详情页事实卡固定展示作者、作者单位、arXiv 编号。
   - 作者单位缺失时必须明确提示，不得将 `venue` 伪装为作者单位。
# Gemini CLI - 专属工作总结与上下文记忆

## 1. 角色定位与职责
*   **我的角色**: 开发 AI (Gemini CLI)。负责该项目的全栈开发工作（前端 Vue 3、后端 Python FastAPI、数据库 MySQL 的代码实现与部署配置）。
*   **协同者 (Codex)**: 负责对我 (Gemini CLI) 输出的代码和架构进行 Review。**强制约束：我 (Gemini CLI) 绝对不能修改 `CODEX_MEMORY.md` 文件。**

## 2. 核心戒律 (Core Mandates)
*   **无损修改原则**: 在对 `Detailed_PRD.md` 或任何核心文档进行修改时，**严禁大幅删除、概括或压缩原本已存在的规格内容**。修改必须是**增量式**或**精准局部修订**。
*   **历史累积原则**: `geminicli.md` 必须记录项目全生命周期的进展，更新时应采用追加或保留历史的方式，严禁丢弃之前阶段的工作记录。
*   **规格物理化**: 所有的正则表达式、数据库定义、Taxonomy 关键词集等必须在文档中保持物理显式。

## 3. 工作进展记录

### [2026-03-23] 第一阶段：需求分析与架构初始化 (已完成)
*   **动作**: 
    1.  完成了初始 PRD 编写与项目目录结构创建 (`frontend/`, `backend/`, `database/`)。
    2.  明确了 FastAPI + Vue 3 + MySQL 的技术栈。
    3.  实现了基础 API 路由 (`papers.py`, `subscribe.py`) 及 SQLAlchemy 模型骨架。
*   **核心产出**: 前后端工程骨架、基础模型层契约。

### [2026-03-24] 第二阶段：v2.0+ 架构升级与评分引擎实装 (已完成)
*   **v2.0 概念引入**: 发布 `Detailed_PRD.md v2.0`，引入 T+3 节奏、8 类信号评分引擎、Focus/Watching 分层展示。
*   **v2.3 架构精进**: 
    1.  实现了 `GET /api/v1/rss`。
    2.  在 `Sources.vue` 和 `Topic.vue` 落地了服务器端分页，解决了数据硬截断问题。
    3.  集成了 Semantic Scholar API，实装学术影响力 (Citations) 信号。
*   **v2.10 规格硬核化**: 
    1.  补齐了 AI Pipeline 的 Markdown 契约、正则提取规则。
    2.  明确了三级幂等定义（Paper/Summary/Task）。
*   **v2.17 全规格回归**: 
    1.  找回了被意外压缩的 15 个分类方向关键词集、全量 DDL 规格及 API 详细 Payload。
    2.  合入了“双语亮点项数强对齐审计”与“Candidate 物理 NULL 语义”。
*   **v2.25 最终精度收口**: 
    1.  实装了 GitHub Trending 专项爬虫，实现开源热度真实数据驱动。
    2.  修正了物理 Schema 与 API 参数中的拼写错误 (typos)。
    3.  锁定了正则转义安全规则 (`re.escape`) 与 Parser 零前缀审计。

## 4. 下一步计划 (待执行)
*   **代码全量对齐 (v2.25 规格重构)**:
    1.  **物理架构对齐**: 按照最新 DDL 更新 `schema.sql` 和 `domain.py`（执行字段迁移与状态隔离）。
    2.  **引擎加固**: 在 `scorer.py` 中实装分域匹配与正则安全规则。
    3.  **Parser 重构**: 在 `ai_processor.py` 中实装 zip 算法与零前缀校验。
    4.  **流水线升级**: 在 `pipeline.py` 中实装包含 Editor 的补位 (Backfill) 逻辑与 3/8 质量基准线。
*   **全链路生产联调**: 配置 Kimi API Key，执行全流程验证。

## 5. 关键备忘录
*   **PRD 是唯一真理来源**: 严禁在 PRD 中使用占位符，文档必须与代码实现 100% 对齐。
*   **NULL 语义**: 在 `paper_summary` 中，Candidate 的解读字段必须显式存储为 NULL。
*   **无损更新**: 以后任何对 PRD 的修改必须基于 v2.25 增量进行。
