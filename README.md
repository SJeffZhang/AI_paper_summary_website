# AI 论文简报 (AI Paper Summary)

为 AI 开发者提供高确定性、双语对齐、历史可追溯的每日论文简报系统。

本项目围绕“抓取真实论文源 -> 评分排序 -> AI 生成双语解读 -> 快照落库 -> Web / RSS / 订阅分发”这条主链构建，目标不是做一个简单的论文聚合站，而是做一个对技术从业者更友好的每日 AI 论文 briefing 产品。

<p align="center">
  <img src="./image/Title%20Image.png" alt="AI Paper Summary 标题图" width="100%" />
</p>

## 1. 当前项目状态

当前仓库已经具备一套可运行的全栈实现：

- 后端使用 FastAPI + SQLAlchemy + MySQL 提供论文列表、详情、订阅、退订和 RSS 接口。
- 前端使用 Vue 3 + Element Plus 提供首页、详情页、候选池页、方向聚合页和分类页。
- 真实生产链路已接入 Kimi API，采用 `Editor -> Writer -> Reviewer` 三阶段生成双语内容。
- 评分策略已经切换为“数量优先发布”：
  - 每天优先产出最多 `5` 篇 `Focus`
  - 再产出最多 `12` 篇 `Watching`
  - 实际数量取决于当天真实供给与 AI 生成结果
- `paper_summary` 是按 `issue_date` 存储的快照真相表，历史期号可回溯。
- `paper_ai_trace` 会把 `Editor / Writer / Reviewer` 的中间产物写入数据库，默认用于审计、排障与质检，不在前端直接展示。

## 2. 这个项目解决什么问题

面向 AI 开发者，每天的论文量很大，但真正值得看的论文往往被埋在大量信息里。这个项目试图解决 4 个实际问题：

1. `论文太多，筛选成本高`
   系统会聚合多个真实源，按统一规则评分，而不是只依赖单一榜单。
2. `只看标题和摘要，判断价值成本高`
   对入选论文生成中英文双语解读，并保留重点亮点与应用场景。
3. `历史内容不可追溯`
   每个 `issue_date` 都会生成自己的快照，后续查询不会被“最新状态”覆盖。
4. `AI 结果不透明`
   AI 三阶段中间产物会入库，失败轮次也会留痕，方便复盘问题来源。

## 3. 当前产品能力

### 3.1 用户可见功能

- `首页 /`
  按期号展示 `Focus` 和 `Watching`，支持中英切换，并提供进入论文分类页的按钮。
- `论文详情 /paper/:id`
  展示论文基础元数据、双语一句话总结、亮点、应用场景；Candidate 不显示 narrative。
- `候选池 /sources/:date`
  展示指定期号的全量候选池、总分、加分项、档位和候选原因。
- `方向聚合 /topic/:name`
  以固定方向 Taxonomy 聚合历史论文。
- `分类总览 /topics`
  提供方向入口页。

### 3.2 后端能力

- 多源抓取：Hugging Face Daily Papers、arXiv、GitHub Trending、Semantic Scholar
- 评分引擎：8 类信号 + 固定方向 Taxonomy
- 标题本地化：Kimi 生成 `title_zh`
- 三阶段 AI 生成：`Editor -> Writer -> Reviewer`
- 中间产物留痕：逐篇写入 `paper_ai_trace`
- 订阅管理：验证 token、退订 token、24 小时有效期、写接口限流
- RSS 输出：仅发布 `focus / watching`

## 3.3 前端页面预览

以下截图来自当前本地运行中的真实前端页面：

<table>
  <tr>
    <td align="center" width="50%">
      <img src="./image/readme-home.png" alt="首页预览" width="100%" />
      <br />
      <strong>首页</strong>
      <br />
      按期号展示，并提供候选池与分类入口
    </td>
    <td align="center" width="50%">
      <img src="./image/readme-detail.png" alt="详情页预览" width="100%" />
      <br />
      <strong>论文详情页</strong>
      <br />
      展示双语一句话总结、亮点和应用场景
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="./image/readme-sources.png" alt="候选池预览" width="100%" />
      <br />
      <strong>原始候选池明细</strong>
      <br />
      展示候选论文、总分、加分项、档位和候选原因
    </td>
    <td align="center" width="50%">
      <img src="./image/readme-topics.png" alt="分类页预览" width="100%" />
      <br />
      <strong>论文分类页</strong>
      <br />
      提供固定方向 Taxonomy 的总览入口
    </td>
  </tr>
  <tr>
    <td align="center" colspan="2">
      <img src="./image/readme-topic-agent.png" alt="方向页预览" width="100%" />
      <br />
      <strong>方向聚合页</strong>
      <br />
      以技术方向聚合历史论文，便于专题浏览
    </td>
  </tr>
</table>

## 4. 核心业务规则

### 4.1 T+3 跑批规则

- `arxiv_publish_date`: 论文原始发布日期
- `issue_date`: 简报发布日期
- `fetch_date = issue_date - 3 天`

也就是说，系统每天跑批时，会抓取 3 天前发布的论文。

### 4.2 数量优先发布策略

当前产品决策已经从早期“硬性 3/8 基线”切换成“数量优先”：

- `Focus`
  - 优先选择 `score >= 80` 的论文
  - 若不足 5 篇，则从剩余论文中按总分补足到 5 篇或候选耗尽
- `Watching`
  - 在剔除已进入 `Focus` 的论文后，从 `50 <= score < 80` 中按分数倒序截取最多 12 篇
  - `Watching` 允许少于 12，必要时可以为 0
- `Candidate`
  - `low_score`: 分数低于 50
  - `capacity_overflow`: 达到阈值但未进入容量窗口
  - `reviewer_rejected`: 进入 AI 流后被 Reviewer 剔除

### 4.3 AI 生成链路

每个批次中的入选论文都走同一条主链：

1. `Editor`
   逐篇确定写作角度、核心痛点、具体解法
2. `Writer`
   生成双语一句话总结、亮点、应用场景
3. `Reviewer`
   给出 `PASSED / REJECTED` 审核结论

注意：

- 日常发布和历史回填当前共用同一条 `Pipeline.run(...)` 主链
- 历史回填并没有绕开 `Editor -> Writer -> Reviewer`
- AI 中间过程默认只入库，不直接展示到前端

## 5. 技术架构

### 5.1 技术栈

- 后端：FastAPI、SQLAlchemy、PyMySQL、Pydantic Settings
- 前端：Vue 3、Vue Router、Element Plus、Vite
- 数据库：MySQL 8
- LLM：Kimi API（Moonshot OpenAI 兼容接口）

### 5.2 架构分层

```text
外部数据源
  -> Crawler
  -> Scorer
  -> AIProcessor (Title Localization / Editor / Writer / Reviewer)
  -> Pipeline
  -> MySQL (paper / paper_summary / paper_ai_trace / system_task_log / subscriber)
  -> FastAPI API
  -> Vue Web UI / RSS / 邮件订阅
```

### 5.2.1 结构图

<p align="center">
  <img src="./image/Structural%20diagram.png" alt="AI Paper Summary 结构图" width="100%" />
</p>

### 5.3 关键数据表

- `paper`
  静态元数据表，存 `arxiv_id`、双语标题、作者、venue、abstract、pdf_url 等。
- `paper_summary`
  以 `issue_date` 为核心的期号快照表，是前端查询和历史回溯的真相源。
- `paper_ai_trace`
  存储 `Editor / Writer / Reviewer` 的逐篇中间产物与 attempt 留痕。
- `system_task_log`
  记录每个期号的任务状态、抓取数量、处理数量和错误日志。
- `subscriber`
  管理订阅状态、验证 token、退订 token 及过期时间。

## 6. 目录结构

```text
.
├── backend/
│   ├── app/
│   │   ├── api/v1/            # FastAPI 路由
│   │   ├── core/              # 配置与全局规格
│   │   ├── db/                # SQLAlchemy engine / session
│   │   ├── models/            # ORM 模型
│   │   ├── schemas/           # Pydantic 响应模型
│   │   └── services/          # crawler / scorer / ai_processor / pipeline
│   ├── prompts/               # Editor / Writer / Reviewer 提示词
│   ├── scripts/               # 本地初始化、联调、回填脚本
│   ├── requirements.txt
│   └── requirements-test.txt
├── frontend/
│   ├── src/
│   │   ├── api/               # 前端 API 适配层
│   │   ├── router/            # Vue Router
│   │   └── views/             # 页面视图
│   └── package.json
├── database/
│   ├── schema.sql             # 全新库初始化脚本
│   └── migrate_v225.sql       # 存量库迁移脚本
├── tests/
│   ├── backend/               # 后端 unit / integration
│   ├── frontend/              # 前端 vitest
│   ├── live/                  # 真实外网 crawler 测试
│   ├── smoke/                 # 编译 / 导入 / build 烟测
│   └── fixtures/              # 测试样例
├── .nexus-map/                # 代码库结构知识图谱
└── Detailed_PRD.md            # 当前产品与系统真相规格
```

## 7. 环境要求

- Python `3.10+`
- Node.js `18+`
- MySQL `8.0+`
- 可用的 Kimi API Key

## 8. 快速启动

### 8.1 克隆仓库

```bash
git clone https://github.com/Mr-silence/AI_paper_summary_website.git
cd AI_paper_summary_website
```

### 8.2 后端配置

#### 1. 创建虚拟环境并安装依赖

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-test.txt
```

#### 2. 配置 `backend/.env`

```env
PROJECT_NAME="AI Paper Summary API"
DATABASE_URL="mysql+pymysql://root:password@localhost:3306/ai_paper_summary"
KIMI_API_KEY="your-kimi-api-key"
KIMI_BASE_URL="https://api.moonshot.cn/v1"
KIMI_MODEL="kimi-k2.5"
KIMI_TIMEOUT_SECONDS=60
KIMI_LONGFORM_TIMEOUT_SECONDS=180
KIMI_MAX_RETRIES=3
KIMI_TITLE_BATCH_SIZE=8
PIPELINE_PROBE_DAYS=14
MYSQL_UNIX_SOCKET=""
HUGGINGFACE_API_URL="https://huggingface.co/api/daily_papers"
FRONTEND_URL="http://127.0.0.1:5173"
```

#### 3. 初始化 MySQL 和数据库

推荐优先使用脚本，而不是直接手动跑 SQL：

```bash
cd backend
./venv/bin/python scripts/setup_local_mysql.py
./venv/bin/python scripts/setup_local_db.py
```

说明：

- `setup_local_mysql.py` 用于准备本机 MySQL 服务
- `setup_local_db.py` 会执行 schema 初始化、必要的列修正和 schema 校验

如果你是在已有旧库上迁移：

```bash
cd backend
./venv/bin/python scripts/setup_local_db.py --migrate-existing
```

#### 4. 检查 Kimi API 连通性

```bash
cd backend
./venv/bin/python scripts/check_kimi_api.py
```

#### 5. 启动后端

```bash
cd backend
./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

后端默认地址：

- API: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 8.3 前端配置

#### 1. 安装依赖

```bash
cd frontend
npm install
```

#### 2. 配置 `frontend/.env.local`

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

#### 3. 启动开发服务器

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

前端默认地址：

- Web UI: [http://127.0.0.1:5173](http://127.0.0.1:5173)

#### 4. 生产构建

```bash
cd frontend
npm run build
```

## 9. 运行脚本

### 9.1 运行一次完整流水线

```bash
cd backend
./venv/bin/python scripts/run_pipeline_once.py
```

行为说明：

- 先检查 prompt、MySQL、数据库、Kimi
- 再在最近 `PIPELINE_PROBE_DAYS` 天内自动探测可跑的 `issue_date`
- 然后执行一次完整的 `Pipeline.run(...)`

### 9.2 指定某个期号跑批

```bash
cd backend
PIPELINE_FIXED_ISSUE_DATE=2026-03-25 ./venv/bin/python scripts/run_pipeline_once.py
```

### 9.3 历史区间回填

```bash
cd backend
./venv/bin/python scripts/backfill_issue_range.py --start-date 2026-02-13 --end-date 2026-03-25
```

说明：

- 历史回填当前和日常发布共用同一条 `Pipeline.run(...)` 主链
- 会按期号逐天执行，并在 `system_task_log` 中留下结果

### 9.4 历史中文标题回填

```bash
cd backend
./venv/bin/python scripts/backfill_title_zh.py
```

适用场景：

- 旧库中 `title_zh` 仍是英文原题
- schema 已迁好，但历史数据契约还没补齐

## 10. 测试

### 10.1 后端主回归

```bash
cd backend
./venv/bin/pytest ../tests/backend ../tests/smoke
```

覆盖：

- unit：评分、AI parser、pipeline 规则、schema 校验
- integration：论文接口、订阅/退订接口
- smoke：导入、脚本、前端 build 烟测

### 10.2 真实外网 crawler 测试

```bash
cd backend
./venv/bin/pytest ../tests/live
```

说明：

- 这组测试会访问真实外网
- 当前主要覆盖 Hugging Face、arXiv、GitHub Trending、Semantic Scholar 和 crawler 合并链路
- 它不是完整的“Kimi + MySQL + API + 前端”全链路 E2E

### 10.3 前端测试

```bash
cd frontend
npm run test:run
```

### 10.4 常用本地校验

```bash
cd backend
./venv/bin/python -m compileall app scripts

cd frontend
npm run build
```

## 11. API 概览

统一响应 envelope：

```json
{
  "code": 200,
  "msg": "success",
  "data": {}
}
```

主要接口：

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/v1/papers` | `GET` | 获取论文列表，支持 `category`、`direction`、`issue_date`、`include_candidates` |
| `/api/v1/papers/{paper_id}` | `GET` | 获取论文详情 |
| `/api/v1/subscribe` | `POST` | 发起订阅 |
| `/api/v1/subscribe/verify` | `GET` | 验证订阅 |
| `/api/v1/unsubscribe` | `POST` | 执行退订 |
| `/api/v1/rss` | `GET` | 获取 RSS |

## 12. 当前测试与实现边界

这个 README 按当前仓库状态描述，但有几条边界需要明确：

- `tests/live` 当前只覆盖 crawler 真实外网探测，不等同于完整 live pipeline 回归。
- AI 中间产物虽然已入库，但默认不在前端展示。
- 前端和后端的主回归已经成体系，但真实 `Kimi + MySQL + 外网数据 + 前端页面` 的整条联调仍主要依赖脚本和人工验收。
- 当前已知仍有一些非阻塞告警：
  - SQLAlchemy `declarative_base()` deprecation
  - Element Plus `el-link underline` deprecation
  - Vite build 的大 chunk 警告

## 13. 进一步阅读

- 产品与系统真相规格：[Detailed_PRD.md](/Users/zhangshijie/Desktop/Project/AI_paper_summary_website/Detailed_PRD.md)
- 代码图谱入口：[.nexus-map/INDEX.md](/Users/zhangshijie/Desktop/Project/AI_paper_summary_website/.nexus-map/INDEX.md)
- 测试说明：[tests/README.md](/Users/zhangshijie/Desktop/Project/AI_paper_summary_website/tests/README.md)

## 14. 许可证

MIT License
