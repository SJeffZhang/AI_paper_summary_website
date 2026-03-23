# Gemini CLI - 专属工作总结与上下文记忆

## 1. 角色定位与职责
*   **我的角色**: 开发 AI (Gemini CLI)。负责该项目的全栈开发工作（前端 Vue 3、后端 Python FastAPI、数据库 MySQL 的代码实现与部署配置）。
*   **协同者 (Codex)**: 负责对我 (Gemini CLI) 输出的代码和架构进行 Review。Codex 拥有专属的工作文件 (`CODEX_MEMORY.md`)。**强制约束：我 (Gemini CLI) 绝对不能修改 `CODEX_MEMORY.md` 文件。**
*   **当前项目**: AI 论文简报网站 (AI Paper Summary Website)。
*   **工作模式**: 每次对话前，我必须读取此文档以恢复上下文状态，确保开发工作的连贯性。

## 2. 工作进展记录

### [2026-03-23] 需求分析与架构设计阶段 (已完成)
*   **动作**: 
    1.  完成了初始 PRD 和开发文档的编写。
    2.  根据用户反馈进行了深度重构，产出了**《详细需求与系统设计文档 (PRD) - 冻结版》** (`Detailed_PRD.md`)。
    3.  完成了项目基础目录结构的创建 (`frontend/`, `backend/`, `database/`)。
*   **核心产出**:
    *   明确了前后端分离架构和技术栈 (Vue 3 + Element Plus, FastAPI, MySQL)。
    *   冻结了全局业务概念（时区 UTC+8、批次与期号 `issue_date` 的严格定义，且所有前端参数及归档跳转均统一使用 `issue_date`）。
    *   完成了实施级的核心算法规则（改为使用 Hugging Face Daily Papers API 根据 `upvotes` 点赞数排序初筛，取代原先的自定义打分公式；AI 流水线采用基于 Markdown 契约的 Editor / Writer / Reviewer 多阶段处理与校验）。
    *   设计了具备**补跑幂等性**的数据库表结构，明确了失败重跑为 `UPDATE` 覆盖机制，并增加了关键联合唯一约束。
    *   设计了具备**双重确认**与安全验证机制的订阅链路，以及基于单参数 Token 的退订逻辑。为 Token 字段增加了 `UNIQUE` 约束，同时明确了 JSON 与非 JSON (RSS/Redirect) 的 API 响应界限。
    *   明确了 Hugging Face API 返回数据到数据库字段 (`arxiv_id`, `pdf_url`, `arxiv_publish_date`) 的归一化映射规则。
    *   **重构了 AI 处理管线 (Agentic Workflow)**: 将单纯的 API 调用重构为“编辑 (Editor)、写手 (Writer)、审核员 (Reviewer)”的三角色流水线。
    *   **确立了基于 Markdown 的鲁棒性契约**: 彻底摒弃了不稳定的 JSON 数据交换，更新了 `backend/prompts/` 下的 prompt，强制所有 Agent 输出带有特定标题和列表结构的 Markdown 文本。后端通过正则表达式和 Markdown AST 进行数据提取，从根本上解决了大模型 JSON 格式损坏的痛点。
    *   **完善了 AI 流水线的强一致性与边界控制**: 
        *   在 PRD 中增加了 Editor 产出的**来源校验**（提取的 ID 必须唯一且属于候选子集），以及 Writer 产出的**强一致性比对**（提取的 `arxiv_id` 必须与 Editor 输出的 ID 集合完全相等，严禁遗漏或篡改）。
        *   修改了 Reviewer Prompt，强制要求输出**`拒绝名单 (rejected IDs)`**，并在后端增加了**语义校验**（保证拒绝对齐）。明确了 Writer 重写时必须**输出全量选题集（过审 + 修改）**，以及在重试耗尽后如何利用最后一次合法名单精准剔除问题论文（按篇舍弃），这使得“按篇舍弃”在代码层面具备了完全的可执行性。

### [2026-03-24] 编码实施阶段 (进行中)
*   **动作**:
    1.  修正了 `backend/app/models/domain.py` 中的 `TinyInt` 导入错误并补全了 `PaperSummary` 的联合唯一约束。
    2.  在 `backend/app/main.py` 中实现了全局异常处理器。
    3.  解耦了前端重定向 URL，同步更新了 `config.py` 和 `.env`。
    4.  安装了 `email-validator` 依赖。
    5.  编写了 `database/schema.sql`。
    6.  实现了 `GET /api/v1/rss` 接口。
    7.  实现了订阅接口的单 IP 限流 (5次/小时)。
    8.  **[深度重构与契约增强]** 完善了自动化跑批流水线 (`backend/app/services/pipeline.py`)：
        *   **Editor 重试机制**：为 Editor 阶段增加了受控的 2 次重试逻辑，确保初筛阶段的鲁棒性。
        *   **Writer/Reviewer 闭环重写**：将结构校验失败（如 ID 不匹配、重复 ID）纳入重试循环，不再直接中断整批任务。
        *   **Reviewer 语义校验**：实现了对 `REJECTED` 状态的严苛校验，确保拒绝名单非空且属于有效 ID 子集。
        *   **数据完整性强制保证**：重构了 `parse_final_summaries`，对“一句话总结”、“核心亮点”、“应用场景”等必填项进行非空和结构校验，杜绝残缺数据入库。
        *   **[新增] ID 唯一性强校验**：在 Editor 和 Writer 阶段均增加了对 ID 重复的严格检查，确保产出的简报不包含重复章节。
        *   **错误反馈机制**：重试时会将具体的解析错误或审核意见回灌给 LLM，提高纠错成功率。
    9.  验证了后端应用可正常启动，并对 Crawler 和 Filter 进行了单元验证。

*   **核心产出**: 
    *   完全对齐 PRD 强契约要求的 AI 跑批引擎。
    *   具备自我纠错能力的 Agentic Workflow 编排实现。

## 3. 下一步计划 (待执行)
*   开始实现核心 AI 跑批流水线 (`backend/app/services/pipeline.py`)：
    1.  实现 `Crawler Module` 从 Hugging Face 获取数据。
    2.  实现 `Filter Module` 按点赞数排序。
    3.  实现 `AI Processor Module` (Editor -> Writer -> Reviewer) 的 Markdown 契约逻辑。
*   完善前端对统一响应格式的处理逻辑。


## 4. 关键备忘录
*   严格遵守 `Detailed_PRD.md` 中定义的字段契约（如 `authors` 和 `core_highlights` 必须为 JSON 数组）。
*   所有定时跑批任务的编写必须确保绝对的**幂等性**。
*   开发过程中，随时准备接受 Codex 的代码 Review 反馈并进行修正。
