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
