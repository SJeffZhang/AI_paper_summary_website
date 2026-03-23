# AI论文简报 - 详细需求与系统设计文档 (PRD) - v2.3 (全链路闭环版)

## 1. 项目愿景与核心目标
### 1.1 项目定位
为 AI 开发者、研究员及从业者提供**高确定性、双语对齐**的每日技术简报。

### 1.2 核心价值主张
*   **信噪比优先**: 通过 8 类信号评分引擎筛选出当日 Top 15-20。
*   **双语强契约**: 确保所有解读内容中英文语义高度对齐，严禁缺失。
*   **来源透明化**: 展示全量候选池评分理由，建立算法公信力。

---

## 2. 全局业务规则 (Global Rules)

### 2.1 跑批节奏 (T+3 Rule)
*   **规则**: 每日 (UTC+8) 执行，处理 3 天前的 arXiv 论文。
*   **日期标识**: `issue_date` (简报发布日), `fetch_date` (数据采集日, 即 `issue_date - 3`)。

### 2.2 幂等性与唯一性 (Idempotency)
1.  **Paper**: `arxiv_id` 唯一。重复抓取执行 `UPDATE`。
2.  **Summary**: `(paper_id, issue_date)` 联合唯一索引。
3.  **Task**: `issue_date` 在 `system_task_log` 中唯一。`SUCCESS` 状态禁止重跑。

---

## 3. 评分引擎规格 (Scoring & Enrichment)

### 3.1 评分信号规格
| 信号 | 分值 | 触发逻辑 |
| :--- | :--- | :--- |
| **顶尖机构** | +20 | 匹配内置 40+ 核心机构名单。 |
| **HF 推荐** | +30 | 存在于当日 Hugging Face Daily 列表。 |
| **社区热度** | 0-40 | 10-50(+10), 50-100(+20), 100+(+40) upvotes。 |
| **顶会收录** | +25 | 识别 ICLR, NeurIPS, CVPR, ICML 等关键词。 |
| **代码可用** | +20 | 摘要含 github.com 链接或 Official Code 标识。 |
| **从业者相关性**| +15 | 匹配 Deploy, Quantization, RAG, Agent 等关键词。 |
| **学术影响力** | 0-30 | **公式**: `score = min(30, citations * 2)`。 |
| **开源热度** | +25 | 代码库位于 GitHub Trending 实时日榜。 |

### 3.2 富化范围 (Current Compromise)
*   受 API 频率限制，仅对 `upvotes` 排序前 **150** 篇候选论文执行 Semantic Scholar 引用抓取及 GitHub Trending 比对。

---

## 4. AI 生产流水线契约 (AI Pipeline Contract)

### 4.1 阶段一：Editor (分层选题)
*   **逻辑**: 按分数将候选切分为 Focus (Top 5) 和 Watching (Next 12) 两组并行/分层调用。
*   **输出正则**: `re.findall(r"## 论文: \[(.*?)\]", output)`。

### 4.2 阶段二：Writer (双语撰写)
*   **强契约格式**: 必须包含 `## [arxiv_id]`, `- **一句话总结**:`, `- **One-line Summary**:`, `- **核心亮点**:`, `- **Core Highlights**:`, `- **应用场景**:`, `- **Application Scenarios**:`.
*   **输出正则**: `re.split(r"## \[(.*?)\]", writer_output)`。

### 4.3 阶段三：Reviewer (审计容错)
*   **逻辑**: 返回 `PASSED` 或 `REJECTED` 及拒绝 ID 列表。若重试 2 次失败或解析崩溃，整批 (Batch) 任务标记为 FAILED。

---

## 5. 数据库全量 Schema (Database)

### 5.1 `paper` (元数据)
*   `id` (INT, PK, AI), `arxiv_id` (VARCHAR(50), UK, NOT NULL), `title` (VARCHAR(500)), `title_en` (VARCHAR(500)), `authors` (JSON), `abstract` (TEXT), `score` (INT), `score_reasons` (JSON), `category` (Enum, Index), `direction` (VARCHAR(50), Index), `arxiv_publish_date` (DATE, Index).

### 5.2 `paper_summary` (解读内容)
*   `id` (INT, PK, AI), `paper_id` (INT, FK), `one_line_summary` (VARCHAR(255)), `one_line_summary_en` (VARCHAR(255)), `core_highlights` (JSON), `core_highlights_en` (JSON), `application_scenarios` (TEXT), `application_scenarios_en` (TEXT), `issue_date` (DATE, Index).
*   **UK**: `uk_paper_issue` (`paper_id`, `issue_date`).

### 5.3 `subscriber` (订阅系统)
*   `id` (INT, PK), `email` (VARCHAR(255), UK), `status` (INT, 0:未验证, 1:活跃, 2:已退订), `verify_token` (VARCHAR(64), UK), `unsubscribe_token` (VARCHAR(64), UK), `token_expires_at` (DATETIME).

### 5.4 `system_task_log` (任务日志)
*   `id` (INT, PK), `issue_date` (DATE, UK), `status` (RUNNING/SUCCESS/FAILED), `fetched_count`, `processed_count`, `error_log` (TEXT).

---

## 6. API 契约与运维规范 (API & Ops)

### 6.1 统一响应格式 (仅限 JSON 接口)
*   `{ "code": 200, "msg": "success", "data": { ... } }`

### 6.2 全量 API 列表
1.  **GET /api/v1/papers**: 获取简报列表。
    *   **Params**: `page`, `limit` (max 100), `category`, `direction`, `issue_date`, `include_candidates` (bool).
2.  **GET /api/v1/papers/{id}**: 获取单篇详情。
3.  **POST /api/v1/subscribe**: 提交订阅。Body: `{ "email": "..." }`。**限流: 5次/小时/IP**。
4.  **GET /api/v1/subscribe/verify**: 激活。**例外: HTTP 302 重定向至前端**。
5.  **POST /api/v1/unsubscribe**: 退订。Body: `{ "token": "..." }`。**安全: 需校验 24h 有效期**。
6.  **GET /api/v1/rss**: 获取 RSS 订阅。**例外: 返回原始 XML 流**。

### 6.3 稳定性参数 (Timeout)
*   **Semantic Scholar**: 5s | **arXiv**: 30s | **LLM (Kimi)**: 60s。
*   **Token 有效期**: 统一设为 **24 小时**。
