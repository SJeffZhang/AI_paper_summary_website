# AI论文简报 - 详细需求与系统设计文档 (PRD) - 冻结版

## 1. 项目概述
### 1.1 项目背景与目标
“AI论文简报”旨在解决AI/ML领域学术论文数量庞大、阅读门槛高的问题。通过自动化拉取 Hugging Face 每日更新的最新 AI 论文，利用 AI（Kimi API）进行筛选和通俗化总结，为没有机器学习专业背景的从业者、学生及爱好者提供每日 3-5 篇的高质量中文简报。

### 1.2 核心链路
定时拉取 HF Daily Papers -> 根据点赞数排序初筛 -> Kimi大模型精读与总结 -> MySQL入库 -> Web端展示/RSS生成/邮件推送。

---

## 2. 系统架构与目录结构
项目采用前后端分离架构，代码组织在当前项目的三个子文件夹中：
*   **`frontend/`**: 前端 Web 项目代码（基于 Vue 3 + Element Plus）。
*   **`backend/`**: 后端 API 与自动化脚本代码（基于 Python + FastAPI）。
*   **`database/`**: 数据库初始化的 SQL 脚本与迁移文件（基于 MySQL）。

---

## 3. 全局业务概念约定 (核心契约)
为保证前后端和数据跑批的一致性，作如下强制约定：
1.  **时区设置**: 整个系统（包含数据库、服务器Cron、日志）统一采用 **UTC+8 (北京时间)**。
2.  **批次与期号 (`issue_date`)**: 
    *   系统的基础数据组织单元为“期 (Issue)”，格式为 `YYYY-MM-DD`。
    *   每天 **02:00 (UTC+8)** 执行跑批任务，生成的简报归属于当天的 `issue_date`（例如 10月25日凌晨2点跑批，生成的简报 `issue_date = '2023-10-25'`）。
    *   抓取时间窗口：每天通过 Hugging Face API 拉取前一日 (`date=昨天`) 社区点赞最高的新发布论文。
3.  **字段类型严格一致**:
    *   `authors` (作者): 严格使用 **JSON 数组** 存储 (例如 `["Author A", "Author B"]`)。
    *   `core_highlights` (核心亮点): 严格使用 **JSON 数组** 存储，每一项为一条亮点的字符串。
    *   原论文发布时间统一命名为 `arxiv_publish_date`，简报期号统一命名为 `issue_date`，避免混用。

---

## 4. 前端详细设计 (Vue 3 + Element Plus)

### 4.1 整体布局 (Layout)
*   **Header (顶栏)**: 包含产品 Logo（左侧）、导航菜单（首页、往期归档、关于）、功能区（RSS订阅图标、邮件订阅按钮）。Element组件：`<el-menu>`, `<el-button>`, `<el-dialog>`。
*   **Footer (底栏)**: 版权信息、免责声明、GitHub源码链接等。
*   **Main (内容区)**: 基于 `<router-view>` 进行页面切换，配合 `<el-main>` 容器，最大宽度限制为 `800px`。

### 4.2 页面清单与细节
#### 4.2.1 首页 (Home - `/`)
*   **功能**: 展示“最新一期”或“指定期号”的 3-5 篇论文简报。
*   **交互**:
    *   **日期切换器**: 顶部提供 `<el-date-picker>` 或左右箭头，按 `issue_date` 切换。
    *   **简报列表**: `<el-card>` 循环渲染。
*   **卡片设计**:
    *   **一句话总结**: 大字号加粗，高亮显示。
    *   **核心亮点**: 无序列表展示（取 JSON 数组的前两项）。
    *   **操作区**: “阅读全文”与“查看原论文”按钮。

#### 4.2.2 详情页 (Detail - `/paper/:id`)
*   **功能**: 展示某篇论文由 AI 总结的完整中文内容。
*   **设计**:
    *   顶部：返回列表按钮（使用 Element Plus 规范组件：`<el-button :icon="Back">返回</el-button>`，需 import `@element-plus/icons-vue`）。
    *   标题：**原论文英文标题**及其作者列表（遍历 JSON 渲染）。
    *   **AI 总结模块**：
        1.  **💡 一句话总结** (`<el-alert>` 高亮)。
        2.  **✨ 核心亮点** (完整列表)。
        3.  **🚀 应用场景**。
    *   底部：`<el-collapse>` 内含原论文的英文摘要 (Abstract) 和 PDF 链接。

#### 4.2.3 往期归档页 (Archive - `/archive`)
*   **功能**: 以时间轴或日历视图展示历史简报记录。
*   **交互**: 点击某一天，跳转至 `/?issue_date=YYYY-MM-DD`。

#### 4.2.4 邮件订阅与退订 (Security & Double Opt-in)
*   **订阅弹窗**: 输入 Email，点击提交。系统提示：“验证邮件已发送，请前往邮箱点击确认链接完成订阅”。
*   **退订页面 (`/unsubscribe`)**: 接收 URL 上的 `token` 参数，页面加载后自动调用后端退订接口，展示成功或失效的反馈。

---

## 5. 后端模块详细设计 (实施级)

### 5.1 自动化管线模块 (Pipeline)
所有流水线任务必须具备**幂等性**。
*   **任务启动拦截**: 任务启动前，检查 `system_task_log` 表中是否存在当日 `issue_date` 的 `SUCCESS` 记录，若存在则跳过，防止重复跑批污染数据。
*   **失败重试机制**: 若当日已有 `FAILED` 记录或因意外中断，重跑时将直接对 `system_task_log` 中同一 `issue_date` 的记录执行 `UPDATE`（覆盖原日志及重置状态为 `RUNNING`），而不允许执行 `INSERT`。这由数据库表中 `issue_date` 的 `UNIQUE` 约束强保证。

1.  **Crawler Module (`crawler.py`)**:
    *   拉取 Hugging Face Daily Papers API (`https://huggingface.co/api/daily_papers?date=YYYY-MM-DD`)。
    *   获取昨日的所有前沿 AI 论文数据（包含点赞数）。
    *   **字段归一化映射 (Mapping)**:
        *   HF API 返回的是一个列表，遍历每一项，提取 `item["paper"]["id"]` 作为 `arxiv_id`（形如 `2603.19216`）。
        *   `pdf_url` 需后端手动拼接：`https://arxiv.org/pdf/{arxiv_id}.pdf`。
        *   发布时间需从 `item["publishedAt"]` (格式如 `2026-03-19T13:58:11.000Z`) 解析并截取日期部分 `YYYY-MM-DD` 存入 `arxiv_publish_date`。
        *   点赞数对应字段为 `item["paper"]["upvotes"]`。
        *   作者列表需从 `item["paper"]["authors"]` 中遍历提取 `name` 字段组成数组。
    *   **失败兜底**: 设置 Timeout=30s，最多重试 3 次。
2.  **Filter Module (`filter.py`) - 社区点赞排序筛选**:
    *   直接使用 Hugging Face 社区返回的真实点赞数 (`upvotes` 字段) 作为唯一的质量衡量标准。
    *   将获取到的论文按 `upvotes` 从高到低进行降序排序。
    *   截取排名前 15 的论文进入下一环节。
3.  **AI Agentic Workflow Module (`ai_processor.py`) - 强契约的多角色处理管线**:
    系统在与大语言模型（如 Kimi API）交互时，采用“编辑(Editor) -> 写手(Writer) -> 审核(Reviewer)”的三阶段流水线。由于大模型在输出合法 JSON 时存在不稳定性，**所有环节的数据交换必须采用严谨结构化的 Markdown 文本**。后端将通过**正则表达式和 Markdown 节点树解析**来提取结构化数据。
    
    *   **步骤一：编辑 (Editor Agent)**
        *   **输入**: Top 15 论文的元数据列表（包含 Title, Abstract, Upvotes 等）。
        *   **Prompt**: 使用 `backend/prompts/editor_prompt.md`。
        *   **输出契约 (Structured Markdown)**: 挑选 3-5 篇论文，输出包含特定二级标题 `## 论文: [arxiv_id]` 及固定加粗列表项（写作角度、痛点、解法等）的 Markdown 报告。
        *   **校验机制 (强制来源与唯一性)**: 后端不仅要正则解析提取字段，还必须校验：1. 提取的 `arxiv_id` 必须互不重复。2. **每一个 `arxiv_id` 都必须存在于输入阶段的 Top 15 候选集中**。如果解析出的论文数量不在 3-5 篇的范围内、关键节点缺失、存在重复 ID 或“幻觉” ID，直接触发重试（上限2次）。
    
    *   **步骤二：写手 (Writer Agent)**
        *   **输入**: Editor 产出的《采编简报》 + 对应论文的原始数据。
        *   **Prompt**: 使用 `backend/prompts/writer_prompt.md`。
        *   **输出契约 (Structured Markdown)**: 每篇简报必须以 `## [arxiv_id]` 开头，并严格包含 `- **一句话总结**:`、`- **核心亮点**:` (及其子列表)、`- **应用场景**:` 的 Markdown 格式。
        *   **校验机制 (一致性强制保证)**: 后端在将 Writer 产出送去审核之前，必须通过正则提取所有的 `arxiv_id`。并且进行**集合强一致性比对**：Writer 输出的 ID 集合必须与 Editor 指定的 ID 集合完全相等。如果出现漏写、多写或篡改 ID，后端直接拒绝并触发 Writer 重写（不进入审核阶段）。
    
    *   **步骤三：审核员 (Reviewer Agent) & 决策与持久化**
        *   **输入**: Writer 产出的包含最终简报内容的完整 Markdown 文本。
        *   **Prompt**: 使用 `backend/prompts/reviewer_prompt.md`。
        *   **输出契约 (Structured Markdown)**: 必须返回包含 `- **整体结论**: [PASSED 或 REJECTED]`，以及 `- **拒绝名单**: [arxiv_id1, arxiv_id2]` 的 Markdown 报告。
        *   **校验机制 (拒绝对齐)**: 当返回 `REJECTED` 时，后端必须校验：`拒绝名单` 必须非空，且其中列出的所有 `arxiv_id` 必须是当前 Writer 输出集合的严格子集（防幻觉 ID）。若校验失败，视同当前 Agent 输出无效并要求重试。
        *   **机制路线**: 
            1. 后端正则匹配 Reviewer 输出中的整体结论和拒绝名单，并执行上述校验。
            2. 若 `REJECTED` 且校验通过：提取详细意见，将其追加到 Writer Agent 的历史对话中。**关键约定：后端强制要求 Writer Agent 在重写时，必须“输出全量选题集（即上一轮通过的论文 + 本轮修改后的论文）”，以此保证每轮产出的 Markdown 都是完整且最新的全量集合**。最多重试 2 次。如果 2 次重写后 Reviewer 依然返回 `REJECTED`，后端将正则提取最后一次审核报告中的 `拒绝名单`，在提取最终入库数据时，直接将这批 ID 从持久化列表中剔除（按篇舍弃）。如果当次跑批被舍弃后导致最终可入库数量 < 3 篇，则触发告警并标记当日任务为 `FAILED`（整体回滚）。
            3. 若匹配到 `PASSED`（或达到重试上限但可入库数量 >=3）：后端从 Writer Agent 最后一次生成的（全量）Markdown 产物中，利用正则剥离出未被拒绝的 `arxiv_id`、`one_line_summary`、`core_highlights` 及 `application_scenarios`，与数据库 `paper` 表对应后进行持久化入库。
    
    *   **成本与熔断控制**: 任何一个 Agent 在耗尽重试次数后依然无法输出可通过正则解析的合格 Markdown 结构，则中止当次跑批，触发告警，当日任务标记为 `FAILED`，数据库执行防污染回滚。

### 5.2 订阅安全模块 (Security)
*   **双重确认 (Double Opt-in)**: 用户提交邮箱后，生成 `uuid4` 作为 `verify_token`，存入数据库（状态为未验证），有效期 24 小时。向用户发送包含验证链接 `https://domain.com/api/v1/subscribe/verify?token=xxx` 的邮件。用户点击后，状态变更为 Active。
*   **安全退订**: 每日推送的邮件底部包含退订链接 `https://domain.com/unsubscribe?token=xxx`，此 Token 必须与用户表绑定的独立 `unsubscribe_token` 一致，避免恶意遍历退订。
*   **限流**: 针对 `/api/v1/subscribe` 接口，单 IP 限制 5次/小时。

---

## 6. API 接口设计 (严格契约)

统一定义 HTTP Header `Content-Type: application/json`，统一响应包裹（**例外：6.4 确认订阅接口为 302 重定向，6.6 RSS 接口为 application/xml**）：
```json
{
  "code": 200,      // 200: 成功, 400: 参数错误, 429: 限流, 500: 服务器错误
  "msg": "success", // 错误信息描述
  "data": { ... }   // 业务 payload
}
```

### 6.1 获取指定日期的简报列表
*   **接口**: `GET /api/v1/papers`
*   **参数**: `issue_date` (Query, 格式 `YYYY-MM-DD`, 不传默认取系统最新一期的 date)
*   **响应**:
```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "id": 101,
      "arxiv_id": "2310.12345",
      "title": "Attention Is All You Need",
      "one_line_summary": "提出了一种完全基于注意力机制的网络架构，摒弃了传统的RNN和CNN。",
      "core_highlights": [
        "并行计算效率高",
        "长距离依赖处理好"
      ],
      "issue_date": "2023-10-25"
    }
  ]
}
```

### 6.2 获取单篇详细总结
*   **接口**: `GET /api/v1/papers/{id}`
*   **响应**:
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "id": 101,
    "arxiv_id": "2310.12345",
    "title": "Attention Is All You Need",
    "authors": ["Ashish Vaswani", "Noam Shazeer"],
    "abstract": "The dominant sequence transduction models...",
    "pdf_url": "https://arxiv.org/pdf/2310.12345.pdf",
    "one_line_summary": "提出了一种完全基于注意力机制的网络架构...",
    "core_highlights": ["并行计算效率高", "长距离依赖处理好"],
    "application_scenarios": "可用于机器翻译、文本摘要等任务。",
    "issue_date": "2023-10-25",
    "arxiv_publish_date": "2017-06-12"
  }
}
```

### 6.3 订阅申请 (需后续验证)
*   **接口**: `POST /api/v1/subscribe`
*   **请求体**: `{"email": "user@example.com"}`
*   **响应**: `{"code": 200, "msg": "验证邮件已发送，请查收并确认"}`

### 6.4 确认订阅 (邮件链接回跳)
*   **接口**: `GET /api/v1/subscribe/verify?token=xxxxx`
*   **行为**: 校验 token，成功后将状态置为 Active，并 302 重定向至前端成功提示页。

### 6.5 安全退订
*   **接口**: `POST /api/v1/unsubscribe`
*   **请求体**: `{"token": "用户专属的退订Token"}` (因邮件退订链接中仅含 token，后端根据 unique token 即可定位用户，无需前端再传 email)
*   **响应**: `{"code": 200, "msg": "退订成功"}`

### 6.6 获取 RSS 订阅源 (非 JSON 响应)
*   **接口**: `GET /api/v1/rss`
*   **行为**: 查询最近 7 天的简报数据（通过联表查询 `paper` 和 `paper_summary`），按照 RSS 2.0 规范组装 XML。
*   **响应**: 返回 `Content-Type: application/xml` 格式的 RSS XML 字符串，供 RSS 阅读器直接解析。

---

## 7. 数据库详细设计 (MySQL - 防御性设计)

所有的建表语句应存放在 `database/schema.sql` 中。字符集统一使用 `utf8mb4`。

### 7.1 `paper` (原论文表)
| 字段名 | 类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | INT | PRIMARY KEY, AUTO_INCREMENT | 自增主键 |
| `arxiv_id` | VARCHAR(50) | UNIQUE, NOT NULL | arXiv 唯一标识 |
| `title` | VARCHAR(500) | NOT NULL | 论文英文原标题 |
| `authors` | JSON | NOT NULL | 作者列表 (JSON数组) |
| `abstract` | TEXT | NOT NULL | 论文英文原摘要 |
| `pdf_url` | VARCHAR(255) | NOT NULL | PDF 链接 |
| `upvotes` | INT | DEFAULT 0 | Hugging Face 社区点赞数 |
| `arxiv_publish_date`| DATE | NOT NULL | 原论文发布日期 |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | 记录入库时间 |

### 7.2 `paper_summary` (简报表)
| 字段名 | 类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | INT | PRIMARY KEY, AUTO_INCREMENT | 自增主键 |
| `paper_id` | INT | NOT NULL | 外键，关联 `paper.id` |
| `one_line_summary`| VARCHAR(255)| NOT NULL | 一句话通俗总结 |
| `core_highlights` | JSON | NOT NULL | 核心亮点 (JSON数组) |
| `application_scenarios`| TEXT | NOT NULL | 应用场景说明 |
| `issue_date` | DATE | NOT NULL | 简报所属期号 |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | 生成时间 |

**【关键约束】**: `UNIQUE KEY uk_paper_issue (paper_id, issue_date)`，**防止同一论文在同一期内被重复总结写入（补跑幂等性保证）**。
*索引*: `idx_issue_date` (前端高频查询)。

### 7.3 `subscriber` (订阅用户表)
| 字段名 | 类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | INT | PRIMARY KEY, AUTO_INCREMENT | 自增主键 |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | 用户的邮箱地址 |
| `status` | TINYINT | DEFAULT 0 | 0:待验证, 1:正常订阅, 2:已退订 |
| `verify_token` | VARCHAR(64) | UNIQUE, NULL | 订阅确认Token (防伪造) |
| `unsubscribe_token`| VARCHAR(64) | UNIQUE, NOT NULL | 退订Token (固定绑定用户) |
| `token_expires_at` | DATETIME | NULL | 确认Token过期时间 |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | 首次提交时间 |
| `updated_at` | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 状态更新时间 |

### 7.4 `system_task_log` (跑批任务日志表)
*注：当前设计为按 `issue_date` 的 UPDATE 覆盖策略以保证严格的幂等性。若未来需要分析完整的失败与重试历史，可考虑单独拓展一张 `system_task_attempt_log` 表。*
| 字段名 | 类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | INT | PRIMARY KEY, AUTO_INCREMENT | 自增主键 |
| `issue_date` | DATE | UNIQUE, NOT NULL | **批次期号唯一键，防止重复执行** |
| `status` | VARCHAR(20) | NOT NULL | RUNNING, SUCCESS, FAILED |
| `fetched_count` | INT | DEFAULT 0 | 抓取数 |
| `processed_count` | INT | DEFAULT 0 | 成功生成简报数 |
| `error_log` | TEXT | NULL | 失败详细堆栈 |
| `started_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | 任务开始时间 |
| `finished_at` | DATETIME | NULL | 任务结束时间 |
