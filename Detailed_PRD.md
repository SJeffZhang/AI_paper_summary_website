# AI论文简报 - 详细需求与系统设计文档 (PRD) - v2.25 (物理规格拼写纠正版)

## 1. 项目愿景与发布准则
### 1.1 项目定位
为 AI 开发者提供**高确定性、双语对齐、历史可追溯**的每日技术简报。

### 1.2 唯一选择权与发布基准 (Quantity-First Tiers & Authority)
**唯一选择权**: 系统排序引擎 (Scorer) 拥有绝对的候选论文“入选权”。AI 环节 (Editor) 仅负责对已入选论文生成定调简报，无权剔除 or 增加。
系统按以下**非重叠**逻辑进行筛选，优先保证当期有稳定内容产出：
1.  **分档过滤 (Thresholding)**: 
    *   `Focus 候选集`: 评分 $\ge 80$ 分。
    *   `Watching 候选集`: $50 \le$ 评分 $< 80$ 分。
2.  **强制截断与归档 (Capacity & Archiving)**: 
    *   将 `Focus 候选集` 按分数倒序排列，优先截取前 5 篇传入 Focus 解读流。
    *   若 `Focus 候选集` 不足 5 篇，则从剩余候选中按总分倒序补足，直到达到 5 篇或候选耗尽。
    *   在剔除已进入 Focus 的论文后，将 `Watching 候选集` 按分数倒序排列，截取最多 12 篇传入 Watching 解读流。
    *   **Candidate 归档与原子溯源规则**: 满足以下条件的论文在 `paper_summary` 中标记为 `category = 'candidate'`：
        *   `low_score`: 评分 $< 50$ 的全量抓取论文。**原子写入**: `category = 'candidate'`, `candidate_reason = 'low_score'`。
        *   `capacity_overflow`: 评分 $\ge 50$ 但在 Top 5/12 容量限制之外的论文。**原子写入**: `category = 'candidate'`, `candidate_reason = 'capacity_overflow'`。
        *   `reviewer_rejected`: 进入了解读流但最终被 Reviewer 标记为 `REJECTED` 的论文。**原子写入**: `category = 'candidate'`, `candidate_reason = 'reviewer_rejected'`。
    *   **阈值语义说明**: `score >= 80` 与 `50 <= score < 80` 是优先分档规则，而非最终发布的绝对硬门槛。在数量优先模式下，系统允许将高分但未达阈值的剩余论文补位进入 Focus，以保证当期有稳定产出。
3.  **数量优先发布策略 (Quantity-First Release Policy)**:
    *   **日常发布目标**: 系统优先保证当期有内容产出，不再以 `Focus < 3` 或 `Watching < 8` 作为日常发布失败条件。
    *   **Focus 选取规则**:
        *   优先选择所有 `score >= 80` 的论文，按分数倒序截取前 5 篇。
        *   若 `score >= 80` 的论文不足 5 篇，则从剩余候选中按总分倒序补足，直到达到 5 篇或候选耗尽。
    *   **Watching 选取规则**:
        *   在剔除已进入 Focus 的论文后，从 `50 <= score < 80` 的论文中按分数倒序截取最多 12 篇。
        *   Watching 允许少于 8 篇，必要时可为 0 篇。
    *   **后置审计与补位状态迁移 (Backfill & State Transition)**:
        *   若 Reviewer 剔除导致 Focus 或 Watching 数量下降，系统应从对应候选集中按分数倒序递推补位，直到恢复目标数量或候选耗尽。
        *   **排除规则 (Blacklist)**: 在当期任务中，任何曾被标记为 `REJECTED` 的论文将永久进入“补位黑名单”，严禁在该期号内再次被提取补位。
        *   **正向迁移 (Promotion)**: 补位流程通过 **UPDATE (原子更新)** 将记录从 `candidate` 变迁至 `focus/watching`，填充 narrative 字段，且**必须将 `candidate_reason` 物理重置为 NULL**。
        *   **逆向迁移 (Demotion)**: 若 Reviewer 拒绝某篇论文，系统必须通过 **UPDATE (原子更新)** 将其 `category` 设为 `candidate`，`candidate_reason = 'reviewer_rejected'`，且必须将所有 narrative 解读字段**物理重置为 NULL**。
    *   **日常失败条件**:
        *   当日抓取结果为空；
        *   AI 流水线解析/审核/持久化失败；
        *   任务执行过程发生不可恢复异常。

---

## 2. 全局业务逻辑规范 (Business Logic)

### 2.1 跑批节奏 (T+3 Rule)
*   **规则**: 每日 (UTC+8) 执行跑批，处理发布于 3 天前的 arXiv 论文。
*   **日期语义**: 
    *   `arxiv_publish_date`: 论文原始发布日。
    *   `issue_date`: 简报期号/发布日 (即 `arxiv_publish_date + 3`)。
    *   `fetch_date`: 数据采集基准日 (即 `issue_date - 3`)。

### 2.2 幂等性与任务状态机 (Idempotency)
1.  **Paper-Level**: `arxiv_id` 唯一。重复抓取执行 `UPDATE` 更新元数据（如 upvotes）。
2.  **Summary-Level**: `(paper_id, issue_date)` 联合唯一。确保同一批次内不会出现重复解读快照。
3.  **Task-Level**: `system_task_log` 表以 `issue_date` 唯一。
    *   **状态机**: `RUNNING` -> `SUCCESS` / `FAILED`。
    *   **防重入**: 若当日任务已处于 `SUCCESS` 状态，严禁自动重跑，必须由管理员显式清除状态。

### 2.3 历史回填执行约束 (Historical Backfill Execution)
*   **适用范围**: 用于补齐历史 `issue_date` 的数据库记录，由专门回填脚本批量触发。
*   **语义说明**: 历史回填默认沿用与日常发布一致的选题、AI 流和持久化契约，不额外引入更严格的供给门槛。
*   **执行目标**: 优先补齐历史期的可展示内容；若某个 `issue_date` 外部抓取结果为空，该天可独立失败而不阻塞整段回填。
*   **可追溯性**: 历史补齐必须通过明确的批处理入口执行，并在 `system_task_log` 中留下对应 `issue_date` 的任务记录。

---

## 3. 评分引擎与 Taxonomy 策略

### 3.1 评分与分类执行契约 (Matching Protocol)
所有基于关键词的评分（机构/信号）和分类（Taxonomy）匹配必须遵循以下形式化规则：
1.  **大小写语义**: 统一采用 **大小写不敏感 (Case-Insensitive)** 匹配。
2.  **匹配算法**: 必须采用 **单词边界匹配**。在拼接正则前，**必须先对关键词执行字面量转义**（如 Python 的 `re.escape()`），然后再包装为 `\b(?:escaped_keyword)\b`。严禁中间子串匹配。
3.  **匹配源范围与物理字段 (Scope & Data Source)**:
    *   **顶尖机构**: 仅匹配 `paper.authors` JSON 数组中各元素的 `affiliation` 字段。
    *   **顶会收录**: 仅匹配 `paper.venue` 字段。
    *   **评分信号 (含代码可用) & Taxonomy**: 匹配论文标题 (`title_original`) 和 摘要 (`abstract`)。

### 3.2 8类信号判定逻辑
| 信号 | 加分 | 触发逻辑 |
| :--- | :--- | :--- |
| **顶尖机构** | +20 | 匹配下述 45 个机构全量白名单。 |
| **HF 推荐** | +30 | 存在于当日 Hugging Face Daily 列表。 |
| **社区热度** | 0-40 | `[10, 50)`: +10; `[50, 100)`: +20; `[100, ∞)`: +40 upvotes。 |
| **顶会收录** | +25 | 匹配关键词：ICLR, NeurIPS, CVPR, ICML, ACL, EMNLP。 |
| **代码可用** | +20 | 标题或摘要包含 github.com 链接或 Official Code 声明。 |
| **从业者相关性**| +15 | 匹配关键词：Deploy, Quantization, RAG, Inference, Agent。 |
| **学术影响力** | 0-30 | **计算公式**: `score = min(30, citations * 2)`。 |
| **开源热度** | +25 | 代码库位于抓取的 GitHub Trending 实时日榜。 |

*   **顶尖机构全量白名单 (Whitelist)**:
    Google, DeepMind, OpenAI, Meta, FAIR, Microsoft, Anthropic, NVIDIA, Stanford, MIT, UC Berkeley, Carnegie Mellon, CMU, Harvard, Oxford, Cambridge, Princeton, ETH Zurich, Tsinghua University, Peking University, THU, PKU, Shanghai Jiao Tong, SJTU, Fudan University, Zhejiang University, ZJU, Huawei, Noah's Ark, Baidu, Tencent, Alibaba, DAMO Academy, ByteDance, TikTok, Kuaishou, SenseTime, MEGVII, IBM Research, Amazon, Salesforce, Apple AI, Hugging Face, Allen Institute, AI21.

### 3.3 技术方向分类规范 (Taxonomy Rules)
*   **单选原则**: 每篇论文必须且仅能归属于一个固定方向。
*   **优先级匹配**: 按以下固定枚举与关键词集顺序执行正则匹配，第一命中即为最终归属。
    1.  **Agent**: `agent, tool use, autonomous, planning`
    2.  **Reasoning**: `reasoning, chain-of-thought, cot, math, theorem`
    3.  **Training_Opt**: `quantization, lora, peft, distributed training, optimization, memory-efficient`
    4.  **RAG**: `rag, retrieval-augmented, vector database, long-context`
    5.  **Multimodal**: `multimodal, vision-language, vlm, cross-modal`
    6.  **Code_Intelligence**: `code generation, code completion, program synthesis`
    7.  **Vision_Image**: `diffusion, image generation, segmentation, stable diffusion`
    8.  **Video**: `video generation, video understanding, sora, temporal consistency`
    9.  **Safety_Alignment**: `rlhf, alignment, red teaming, jailbreak, safety, toxicity`
    10. **Robotics**: `robotics, embodied ai, manipulation, navigation`
    11. **Audio**: `audio generation, speech recognition, tts, asr`
    12. **Interpretability**: `interpretability, mechanistic, attention map, explainable`
    13. **Benchmarking**: `benchmark, evaluation, dataset, metric`
    14. **Data_Engineering**: `synthetic data, data curation, data pipeline, pre-training data`
    15. **Industry_Trends**: `survey, review, perspective, roadmap`

---

## 4. AI 生产流水线强契约 (Strict AI Contracts)

### 4.1 阶段一：Editor (选题与定调)
*   **输出模板 (强制执行)**: 
    ```markdown
    ## 论文: [arxiv_id]
    - **写作角度**: [为 Writer 指定切入点]
    - **核心痛点**: [原有问题描述]
    - **具体解法**: [方案简述]
    ```
*   **提取正则与重试规则**: 
    *   **Block 切分算法**: 
        1. `blocks = re.split(r"## 论文: \[(.*?)\]", output)`
        2. **零前缀校验**: `blocks[0]` 必须为空或仅包含空白字符。若包含杂质文本，直接判定解析失败并触发重试。
        3. `records = list(zip(blocks[1::2], blocks[2::2]))` (注: 索引 0 已校验，跳过)。
    *   **完整性校验 (Integrity Check)**: 
        1. 记录数校验: `len(records)` 必须等于该批次输入的论文总数。
        2. ID 集合校验: `set(extracted_ids)` 必须与输入的 `set(input_arxiv_ids)` 完全一致。
    *   **属性提取 (针对每条 record 的 content)**: `re.search(r"- \*\*写作角度\*\*: (.*?)\n", block)`, `re.search(r"- \*\*核心痛点\*\*: (.*?)\n", block)`, `re.search(r"- \*\*具体解法\*\*: (.*?)\n", block)`。
    *   **失败终态**: 校验失败重试 2 次。若最终不通过，整批任务标记为 `FAILED`。

### 4.2 阶段二：Writer (双语撰写与层级/对称审计)
*   **输出模板 (强制执行)**:
    ```markdown
    ## [arxiv_id]
    - **一句话总结**: [中文内容]
    - **One-line Summary**: [English Content]
    - **核心亮点**:
      - [亮点1_CN]
    - **Core Highlights**:
      - [亮点1_EN]
    - **应用场景**: [中文内容]
    - **Application Scenarios**: [English Content]
    ```
*   **机械级解析规则**:
    1.  **Block 切分算法**: 
        1. `blocks = re.split(r"## \[(.*?)\]", writer_output)`
        2. **零前缀校验**: `blocks[0]` 必须为空或仅包含空白字符。若包含杂质文本，直接判定解析失败并触发重试。
        3. `records = list(zip(blocks[1::2], blocks[2::2]))`。
    2.  **完整性校验 (Integrity Check)**:
        1. 记录数校验: `len(records)` 必须等于该批次输入的论文总数。
        2. ID 集合校验: `set(extracted_ids)` 必须与输入集合完全一致。
    3.  **属性提取 (针对 content)**:
        *   中文总结: `re.search(r"- \*\*一句话总结\*\*: (.*?)\n", block)`
        *   英文总结: `re.search(r"- \*\*One-line Summary\*\*: (.*?)\n", block) `
        *   中文亮点: `re.search(r"- \*\*核心亮点\*\*:\n(.*?)\n- \*\*Core Highlights\*\*:", block, re.S)`
        *   英文亮点: `re.search(r"- \*\*Core Highlights\*\*:\n(.*?)\n- \*\*应用场景\*\*:", block, re.S)`
        *   中文场景: `re.search(r"- \*\*应用场景\*\*: (.*?)\n", block)`
        *   英文场景: `re.search(r"- \*\*Application Scenarios\*\*: (.*?)(?:\n|$)", block, re.S)`
*   **硬性审计校验规则**:
    1.  **非空校验**: 所有 6 个提取出的文本块必须全非空。
    2.  **双语对称校验**: `核心亮点 (CN)` 与 `Core Highlights (EN)` 的列表项数量必须完全一致。
    3.  **层级长度约束**: `Focus` 亮点数量 $\in [3, 5]$，`Watching` 亮点数量 $\in [1, 2]$。
    4.  **失败终态**: 审计失败重试 2 次。若最终不达标，该批次任务正式 `FAILED`。

### 4.3 阶段三：Reviewer (结论与剔除)
*   **输出模板 (强制执行)**: 
    必须且只能出现以下两种块结构之一，正则匹配必须严格校验括号。
    *   **全量通过态**:
        ```markdown
        - **整体结论**: PASSED
        - **拒绝名单**: []
        ```
    *   **触发剔除态**:
        ```markdown
        - **整体结论**: REJECTED
        - **拒绝名单**: [arxiv_id_1, arxiv_id_2]
        ```
*   **提取规则与终态**:
    *   结论: `re.search(r"- \*\*整体结论\*\*: (PASSED|REJECTED)", output)`。
    *   名单: `re.search(r"- \*\*拒绝名单\*\*: \[(.*?)\]", output)`。
    *   **失败终态**: 若解析连续 2 次失败，或剔除后篇数跌破基准且补位耗尽，任务正式标记为 `FAILED` 并持久化错误日志。

### 4.4 AI 过程留痕 (中间产物入库)
*   `Editor -> Writer -> Reviewer` 的中间产物必须落库，不能只保留最终 narrative。
*   留痕粒度要求：
    1. 以 `paper_summary` 为锚点逐篇存储；
    2. 至少记录 `stage`、`attempt_no`、`stage_status`、`content`；
    3. `Editor` 与 `Writer` 存逐篇块内容，`Reviewer` 存本轮审核结论文本；
    4. 若同一批次出现重试，必须保留每一轮 attempt，不能用最后一轮覆盖前一轮。
*   产品呈现要求：
    1. AI 过程留痕默认用于数据库审计、排障与质检，不要求在前端详情页直接展示；
    2. `candidate` 若曾进入 AI 流且后续被 Reviewer 剔除，也应保留过程留痕；
    3. narrative 字段在 `candidate` 状态下仍必须物理为 `NULL`，但 AI trace 不应被清空。

---

## 5. 数据库全量物理规格 (Database Dialect: MySQL 8.0+)

### 5.1 `paper` (静态元数据)
| 字段 | 类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK, AUTO_INCREMENT | - |
| `arxiv_id` | VARCHAR(50) | UNIQUE, NOT NULL | 核心凭证 |
| `title_zh` | VARCHAR(500) | NOT NULL | 中文本地化标题 |
| `title_original` | VARCHAR(500) | NOT NULL | 论文原始标题 (英文) |
| `authors` | JSON | NOT NULL | **作者规格**: `[{"name": "...", "affiliation": "..."}]` |
| `venue` | VARCHAR(255) | NULL | **顶会/期刊锚点**: 如 ICLR 2024, arXiv journal-ref |
| `abstract` | TEXT | NOT NULL | 原始摘要 |
| `pdf_url` | VARCHAR(255) | NOT NULL | PDF链接 |
| `upvotes` | INT | DEFAULT 0 | 社区点赞 |
| `arxiv_publish_date` | DATE | INDEX, NOT NULL | 原始发布日期 |

### 5.2 `paper_summary` (期号快照与解读)
**物理 NULL 约束**: 当 `category = 'candidate'` 时，表中的解读字段 (9-14) **必须存储为物理 NULL 值**。当 `category != 'candidate'` 时，`candidate_reason` **必须清空为 NULL**。
| 字段 | 类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| 1. `id` | INT | PK, AUTO_INCREMENT | - |
| 2. `paper_id` | INT | FK(paper.id), NOT NULL | 关联主表 |
| 3. `issue_date` | DATE | INDEX, NOT NULL | 发布期号 |
| 4. `score` | INT | NOT NULL, DEFAULT 0 | 总分快照 |
| 5. `score_reasons` | JSON | NULL | 加分明细快照 |
| 6. `category` | ENUM('focus', 'watching', 'candidate') | INDEX, NOT NULL | 档位快照 |
| 7. `candidate_reason`| ENUM('low_score', 'capacity_overflow', 'reviewer_rejected') | NULL | 候选原因 (仅 category=candidate 时有效) |
| 8. `direction` | ENUM('Agent', 'Reasoning', 'Training_Opt', 'RAG', 'Multimodal', 'Code_Intelligence', 'Vision_Image', 'Video', 'Safety_Alignment', 'Robotics', 'Audio', 'Interpretability', 'Benchmarking', 'Data_Engineering', 'Industry_Trends') | INDEX, NOT NULL | 分类快照 |
| 9. `one_line_summary` | TEXT | NULL | 中文一句话总结 |
| 10. `one_line_summary_en` | TEXT | NULL | 英文一句话总结 |
| 11. `core_highlights` | JSON | NULL | 中文核心亮点 (List) |
| 12. `core_highlights_en` | JSON | NULL | 英文核心亮点 (List) |
| 13. `application_scenarios` | TEXT | NULL | 中文应用场景 |
| 14. `application_scenarios_en`| TEXT | NULL | 英文应用场景 |
*   **UK约束**: `UNIQUE KEY uk_paper_issue (paper_id, issue_date)`。

### 5.3 `paper_ai_trace` (AI 中间产物留痕)
| 字段 | 类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK, AUTO_INCREMENT | - |
| `paper_summary_id` | INT | FK(paper_summary.id), NOT NULL | 关联期号快照 |
| `stage` | ENUM('editor', 'writer', 'reviewer') | INDEX, NOT NULL | AI 角色阶段 |
| `stage_status` | ENUM('generated', 'accepted', 'rejected', 'invalid') | NOT NULL | 当前阶段在该论文上的状态；`invalid` 用于记录格式不合法、包装噪声或解析失败的原始输出 |
| `attempt_no` | INT | NOT NULL, DEFAULT 1 | 第几轮生成/审核 |
| `content` | TEXT | NOT NULL | 对应阶段的原始文本产物 |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | 产物入库时间 |
*   **UK约束**: `UNIQUE KEY uk_trace_summary_stage_attempt (paper_summary_id, stage, attempt_no)`。

### 5.4 `subscriber` (订阅系统)
| 字段 | 类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK, AUTO_INCREMENT | - |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | 邮箱 |
| `status` | INT | INDEX, DEFAULT 0 | 0:未验证, 1:活跃, 2:退订 |
| `verify_token` | VARCHAR(64) | UNIQUE, NULL | 激活令牌 |
| `unsub_token` | VARCHAR(64) | UNIQUE, NULL | 退订令牌 |
| `verify_expires_at` | DATETIME | NULL | 激活过期 (24h) |
| `unsub_expires_at` | DATETIME | NULL | 退订过期 (24h) |

### 5.5 `system_task_log` (任务追踪)
| 字段 | 类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | INT | PK, AUTO_INCREMENT | - |
| `issue_date` | DATE | UNIQUE, NOT NULL | 绑定单一批次 |
| `status` | VARCHAR(20) | NOT NULL | `RUNNING`, `SUCCESS`, `FAILED` |
| `fetched_count` | INT | DEFAULT 0 | 采集候选数 |
| `processed_count` | INT | DEFAULT 0 | 成功解读数 |
| `error_log` | TEXT | NULL | 失败堆栈/详情 |
| `started_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | - |
| `finished_at` | DATETIME | NULL | - |

---

## 6. 全量 API 执行契约 (API Contracts)

### 6.1 统一 JSON 响应 Envelope
```json
{
  "code": 200, // 200: 成功, 400+: 业务/参数错误, 500+: 内部错误
  "msg": "success", 
  "data": { ... } // 失败时或无返回数据时为 null
}
```

### 6.2 接口清单与全量 Payload
1.  **GET /api/v1/papers** (列表分页)
    *   **Params**: `page` (int), `limit` (int, max 100), `category`, `direction`, `issue_date`, `include_candidates` (bool)。
    *   **Response Payload**: `{ "total": INT, "items": [ { "id", "arxiv_id", "title_zh", "title_original", "score", "category", "candidate_reason", "direction", "issue_date", "one_line_summary", "one_line_summary_en" } ] }`。
2.  **GET /api/v1/papers/{id}** (单篇详情)
    *   **Response Payload**: 包含列表字段 + `abstract`, `authors`, `venue`, `score_reasons`, `core_highlights`, `core_highlights_en`, `application_scenarios`, `application_scenarios_en`。
    *   **NULL 契约**: 
        *   若目标论文 `category == 'candidate'`，响应中所有的解读字段 (core_highlights 等) 必须显式返回 `null`。
        *   若目标论文 `category != 'candidate'`，响应中的 `candidate_reason` 必须返回 `null`。
    *   **作者单位缺失语义**:
        *   `authors` 中每个元素的 `affiliation` 允许为空字符串；上游来源未提供机构信息时，后端不得伪造作者单位。
        *   `venue` 仍作为评分与元数据字段保留，但不要求前端详情页将其作为“作者单位”兜底来源。
3.  **POST /api/v1/subscribe**: `{ "email": "..." }` $\rightarrow$ `{ "code": 200, "msg": "邮件已发送", "data": null }`。
4.  **GET /api/v1/subscribe/verify**: 验证激活。
    *   **Params**: `token` (string, required)。
    *   **Response**: **HTTP 302** 重定向至前端成功页。
5.  **POST /api/v1/unsubscribe**: `{ "token": "..." }` $\rightarrow$ `{ "code": 200, "msg": "退订成功", "data": null }`。
6.  **GET /api/v1/rss**: **原始 XML (application/xml)** 数据。结构包含 `<channel>` 下属 `<item>` (含 `title`, `link`, `description`, `pubDate`)。

---

## 7. 运维与安全规格 (Ops)
*   **超时配置**: Semantic Scholar (5s), arXiv (30s), KIMI 短请求 (60s), KIMI 长文本请求 (180s)。
*   **限流策略**: 针对 `/subscribe` 相关写入接口，限制 5 次/小时/IP。
*   **Token 有效期**: `verify_token` 与 `unsub_token` 统一设为 **24 小时**。

---

## 8. 前端体验与本地预览规格 (Frontend UX)

### 8.1 当前视觉定位
*   前端当前定位为“研究简报站”，不是后台管理系统。
*   视觉基调采用暖白页面底、炭黑正文、低饱和强调色与克制阴影，整体参考 Claude 式温和配色结构。
*   页面信息架构强调编辑化阅读节奏：
    *   首页以当期简报、Focus 主卡流、Watching 次级流、日历与方向入口组成主阅读路径。
    *   详情页以标题、核心摘要、亮点、应用场景和原论文信息组成长阅读路径。
    *   候选池页用于保留未入选论文和筛选原因，移动端应转为更适合阅读的信息卡片结构。

### 8.2 移动端与交互约束
*   移动端 Header 必须使用抽屉式导航，不应退回到横向导航自动换行。
*   抽屉导航至少支持：
    *   菜单按钮打开；
    *   遮罩点击关闭；
    *   `Esc` 关闭；
    *   路由切换后自动关闭；
    *   打开时锁定 body 滚动。
*   桌面端可交互模块允许轻微 hover / focus 反馈，动效应保持克制，避免强烈黑色光晕、大面积动态玻璃或持续动画背景。
*   移动端不启用复杂动态玻璃按钮效果；主按钮保持稳定纯黑高对比样式，保证文字清晰。
*   方向标签属于导航入口：首页与详情页中的方向标签必须可点击并跳转到对应方向页。

### 8.3 详情页事实卡展示规则
*   详情页顶部事实卡当前固定展示：作者、作者单位、arXiv 编号。
*   作者单位卡片的数据源为 `authors[].affiliation`，前端需先执行去空与去重。
*   当有效机构数为 1-2 个时，直接展示完整机构名；当机构数 >= 3 时，允许压缩展示，并通过悬停提示暴露完整列表。
*   若当前论文的 `authors[].affiliation` 全部为空，前端必须明确提示“论文源未提供作者单位 / Affiliation not provided by the source”，不得显示空白，也不应将 `venue` 伪装成作者单位。

### 8.4 Mock 预览开关
*   正式运行与普通本地运行默认请求真实后端 API。
*   仅当 `VITE_USE_MOCK_BRIEF_DATA=true` 时，前端才允许切换到运行时 mock provider。
*   mock provider 只服务本地视觉评审和无后端预览，不得成为生产默认路径。
*   前端 API 基准地址继续通过 `VITE_API_BASE_URL` 配置；未设置时使用现有默认值。

### 8.5 README 截图约束
*   README 首页截图使用 `image/readme-home-v2.png`。
*   当前截图尺寸固定为 `1365 x 900`，后续替换时应保持相同比例，避免 README 展示尺寸跳变。
*   正式截图应来自真实后端 API 数据，不应使用 mock 数据截图。
