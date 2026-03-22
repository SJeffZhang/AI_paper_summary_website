# AI论文简报 - 详细需求与系统设计文档 (PRD)

## 1. 项目概述
### 1.1 项目背景与目标
“AI论文简报”旨在解决AI/ML领域学术论文数量庞大、阅读门槛高的问题。通过自动化拉取 arXiv 每日更新的论文，利用 AI（Kimi API）进行筛选和通俗化总结，为没有机器学习专业背景的从业者、学生及爱好者提供每日 3-5 篇的高质量中文简报。
### 1.2 核心链路
定时抓取 -> 算法/规则初筛 -> Kimi大模型精读与总结 -> MySQL入库 -> Web端展示/RSS生成/邮件推送。

---

## 2. 系统架构与目录结构
项目采用前后端分离架构，代码组织在当前项目的三个子文件夹中：
*   **`frontend/`**: 前端 Web 项目代码（基于 Vue 3 + Element Plus）。
*   **`backend/`**: 后端 API 与自动化脚本代码（推荐使用 Python + FastAPI，便于数据处理与 AI 调用）。
*   **`database/`**: 数据库初始化的 SQL 脚本与迁移文件（基于 MySQL）。

---

## 3. 前端详细设计 (Vue 3 + Element Plus)

### 3.1 整体布局 (Layout)
*   **Header (顶栏)**: 包含产品 Logo（左侧）、导航菜单（首页、往期归档、关于）、以及功能区（RSS订阅图标、邮件订阅按钮）。Element组件：`<el-menu>`, `<el-button>`, `<el-dialog>`(用于订阅弹窗)。
*   **Footer (底栏)**: 版权信息、免责声明、GitHub源码链接等。
*   **Main (内容区)**: 基于 `<router-view>` 进行页面切换，配合 `<el-main>` 容器，最大宽度限制（如 800px）以保证最佳阅读体验。

### 3.2 页面清单与细节
#### 3.2.1 首页 (Home - `/`)
*   **功能**: 展示“今日”或“最新一期”的 3-5 篇论文简报。
*   **交互**:
    *   **日期切换器**: 顶部提供 `<el-date-picker>` 或左右箭头，允许用户切换日期查看历史简报。
    *   **简报列表 (List)**: 使用 `<el-card>` 循环渲染当天的简报。
*   **卡片设计 (Card)**:
    *   **一句话总结**: 大字号加粗，高亮显示。
    *   **标签**: 使用 `<el-tag>` 标明领域（如 CV, NLP）或评分。
    *   **核心亮点**: 无序列表展示（节选前两点）。
    *   **操作区**: “阅读全文”按钮（跳转详情页）与“查看原论文”链接（新标签页打开 arXiv）。

#### 3.2.2 详情页 (Detail - `/paper/:id`)
*   **功能**: 展示某篇论文由 AI 总结的完整中文内容。
*   **设计**:
    *   顶部：返回列表按钮 `<el-button icon="el-icon-back">`。
    *   标题：**原论文英文标题**及其作者列表。
    *   **AI 总结模块**：
        1.  **💡 一句话总结**（区块高亮，使用 `<el-alert>` 或自定义 CSS 样式）。
        2.  **✨ 核心亮点**（详细的列表）。
        3.  **🚀 应用场景**（通俗易懂的落地场景描述）。
    *   底部：折叠面板 `<el-collapse>`，内含原论文的英文摘要 (Abstract) 和 PDF 下载按钮。

#### 3.2.3 往期归档页 (Archive - `/archive`)
*   **功能**: 以时间轴或日历视图展示历史简报记录。
*   **组件**: `<el-timeline>` 或 `<el-calendar>`。用户点击某一天，直接带参跳转至首页 (`/?date=YYYY-MM-DD`)。

#### 3.2.4 邮件订阅弹窗 (Subscribe Dialog)
*   **触发**: 点击顶栏的“订阅”按钮弹出。
*   **内容**: `<el-form>` 包含一个 Email 输入框 (`<el-input>`)。
*   **交互**: 提交时进行前端正则校验，调用后端订阅接口，成功后显示 `<el-message type="success">` 提示。

---

## 4. 后端模块详细设计

后端推荐采用 Python (FastAPI)，分为**定时任务进程**和**Web API 服务进程**。

### 4.1 核心模块划分
1.  **Crawler Module (`crawler.py`)**:
    *   通过 `urllib` 或 `requests` 调用 arXiv API (`export.arxiv.org/api/query`)。
    *   参数限制：检索过去 24 小时内的 `cs.AI`, `cs.CL`, `cs.CV`, `cs.LG` 类目论文。
    *   解析 XML 格式的返回结果。
2.  **Filter Module (`filter.py`)**:
    *   **初筛逻辑**：清洗抓取到的 300 篇论文，根据作者（是否来自顶级机构如 Google, Meta, Stanford）、标题是否包含当下热门关键词（如 LLM, Agent, Diffusion）进行权重打分，提取 Top 15。
3.  **AI Processor Module (`ai_processor.py`)**:
    *   将 Top 15 的标题和摘要拼接，调用 Kimi API 进行**复筛**，让大模型选出最适合大众科普的 3-5 篇。
    *   针对选出的 3-5 篇，再次并发调用 Kimi API，使用严格的 Prompt 生成 JSON 格式的总结（一句话总结、核心亮点、应用场景）。
4.  **Database ORM Module (`models.py`, `crud.py`)**:
    *   使用 SQLAlchemy 或 Tortoise ORM 连接 MySQL，负责数据的持久化写入和读取。
5.  **Scheduler Module (`scheduler.py`)**:
    *   使用 `APScheduler` 每天凌晨 (如 02:00) 定时触发 `Crawler -> Filter -> AI Processor -> Database` 的完整流水线。
6.  **Notifier Module (`notifier.py`)**:
    *   每天入库完成后，拉取活跃订阅者的邮箱列表，使用 SMTP 库组装 HTML 邮件模板并批量发送。
    *   动态生成包含最新数据的 RSS XML 文件字符串（也可由 API 实时生成）。

---

## 5. API 接口设计 (RESTful)

统一响应格式 (JSON):
```json
{
  "code": 200,
  "msg": "success",
  "data": { ... } // 具体的业务数据
}
```

### 5.1 获取某日论文简报列表
*   **接口**: `GET /api/v1/papers`
*   **参数**: `date` (Query, 格式 `YYYY-MM-DD`, 不传默认取最新一天)
*   **响应**:
```json
"data": [
  {
    "id": 101,
    "arxiv_id": "2310.12345",
    "title": "Attention Is All You Need",
    "one_line_summary": "提出了一种完全基于注意力机制的网络架构，摒弃了传统的RNN和CNN。",
    "core_highlights": "[\"并行计算效率高\", \"长距离依赖处理好\"]",
    "publish_date": "2023-10-25"
  }
]
```

### 5.2 获取单篇论文详细总结
*   **接口**: `GET /api/v1/papers/{id}`
*   **参数**: `id` (Path, 论文ID)
*   **响应**:
```json
"data": {
    "id": 101,
    "arxiv_id": "2310.12345",
    "title": "Attention Is All You Need",
    "authors": "Ashish Vaswani, Noam Shazeer...",
    "abstract": "The dominant sequence transduction models...",
    "pdf_url": "https://arxiv.org/pdf/2310.12345.pdf",
    "one_line_summary": "...",
    "core_highlights": "...",
    "application_scenarios": "可用于机器翻译、文本摘要等各类自然语言处理任务。",
    "publish_date": "2023-10-25"
}
```

### 5.3 邮箱订阅 / 取消订阅
*   **接口**: `POST /api/v1/subscribe`
*   **请求体 (Body)**:
```json
{
  "email": "user@example.com",
  "action": "subscribe" // 可选: "subscribe" 或 "unsubscribe"
}
```
*   **响应**: `{"code": 200, "msg": "订阅成功"}`

### 5.4 获取 RSS 订阅源
*   **接口**: `GET /api/v1/rss`
*   **响应**: 直接返回 `application/xml` 格式的 RSS 2.0 字符串，供 RSS 阅读器解析。

---

## 6. 数据库详细设计 (MySQL)

所有的建表语句应存放在 `database/schema.sql` 中。

### 6.1 `paper` 表 (存储从 arXiv 抓取的原论文信息)
| 字段名 | 类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | INT | PRIMARY KEY, AUTO_INCREMENT | 自增主键 |
| `arxiv_id` | VARCHAR(50) | UNIQUE, NOT NULL | arXiv 唯一标识 (如 2310.12345) |
| `title` | VARCHAR(500) | NOT NULL | 论文英文原标题 |
| `authors` | TEXT | NOT NULL | 作者列表（逗号分隔或 JSON 格式存储）|
| `abstract` | TEXT | NOT NULL | 论文英文原摘要 |
| `pdf_url` | VARCHAR(255) | NOT NULL | PDF 链接 |
| `published_date` | DATE | NOT NULL | 论文在 arXiv 上的发布日期 |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | 记录入库时间 |

*索引*: `idx_published_date` (加速按日期查询)，`idx_arxiv_id`。

### 6.2 `paper_summary` 表 (存储经过 Kimi API 处理后的中文简报)
| 字段名 | 类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | INT | PRIMARY KEY, AUTO_INCREMENT | 自增主键 |
| `paper_id` | INT | NOT NULL | 外键，关联 `paper.id` |
| `one_line_summary`| VARCHAR(255)| NOT NULL | 一句话通俗总结 |
| `core_highlights` | TEXT | NOT NULL | 核心亮点 (存储 JSON 数组字符串) |
| `application_scenarios`| TEXT | NOT NULL | 应用场景说明 |
| `publish_date` | DATE | NOT NULL | 简报所属的分发日期 (用于前端按天查询) |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | 生成时间 |

*索引*: `idx_paper_id`，`idx_publish_date` (极为常用，前端首页按日期查询的核心索引)。

### 6.3 `subscriber` 表 (存储订阅用户)
| 字段名 | 类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | INT | PRIMARY KEY, AUTO_INCREMENT | 自增主键 |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | 用户的邮箱地址 |
| `status` | TINYINT | DEFAULT 1 | 状态: 1-正常订阅，0-已退订 |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | 订阅时间 |
| `updated_at` | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 状态更新时间 |

### 6.4 `system_task_log` 表 (记录每日自动化任务的执行状态，便于运维排错)
| 字段名 | 类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | INT | PRIMARY KEY, AUTO_INCREMENT | 自增主键 |
| `task_date` | DATE | NOT NULL | 任务对应日期 |
| `fetched_count` | INT | DEFAULT 0 | 当日拉取的论文总数 |
| `processed_count` | INT | DEFAULT 0 | 成功生成简报的论文数 (通常为 3-5) |
| `status` | VARCHAR(20) | NOT NULL | 任务状态 (SUCCESS, FAILED, PARTIAL) |
| `error_log` | TEXT | NULL | 失败时的详细报错信息 (如 API 超时) |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | 任务执行时间 |
