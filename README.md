# ArxivDaily

面向 AI 开发者的双语论文日报系统。

它不是简单的论文聚合页，而是一条完整的生产链：抓取真实论文源，按规则打分筛选，对入选论文生成中文标题和双语解读，按 `issue_date` 快照落库，并通过 Web 界面和邮件日报对外分发。

<p align="center">
  <img src="./image/Title%20Image.png" alt="ArxivDaily 标题图" width="100%" />
</p>

## 项目现在能做什么

- 聚合 `Hugging Face Daily Papers` 与 `arXiv` 多个 AI 方向的论文数据。
- 使用 `GitHub Trending` 和 `Semantic Scholar` 为论文补充开源热度与学术影响信号。
- 通过 8 类规则信号对论文打分，并按“数量优先”策略产出最多 `5` 篇 `Focus` 和最多 `12` 篇 `Watching`。
- 对入选论文执行单篇隔离的 `Editor -> Writer -> Reviewer` 三阶段 LLM 链路，生成中文标题与双语摘要。
- 将 `paper`、`paper_summary`、`paper_ai_trace`、`system_task_log` 等关键数据落到 MySQL，支持历史回看与排障。
- 提供首页、论文详情、候选池、方向聚合、分类总览、订阅/退订页面。
- 支持每日自动更新、每日简报邮件发送、任务失败告警邮件，以及 Ubuntu 单机部署。

## 页面预览

当前前端的真实页面形态如下：

<table>
  <tr>
    <td align="center" width="50%">
      <img src="./image/readme-home-v2.png" alt="首页预览" width="100%" />
      <br />
      <strong>首页</strong>
      <br />
      每页只展示一天内容，右侧日历可快速跳转
    </td>
    <td align="center" width="50%">
      <img src="./image/readme-detail.png" alt="论文详情页预览" width="100%" />
      <br />
      <strong>论文详情页</strong>
      <br />
      展示双语一句话总结、亮点与应用场景
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="./image/readme-sources.png" alt="候选池预览" width="100%" />
      <br />
      <strong>候选池明细</strong>
      <br />
      展示保留到快照中的全部候选论文、总分与加分项
    </td>
    <td align="center" width="50%">
      <img src="./image/readme-topics.png" alt="分类页预览" width="100%" />
      <br />
      <strong>分类总览页</strong>
      <br />
      提供固定方向 taxonomy 的入口
    </td>
  </tr>
  <tr>
    <td align="center" colspan="2">
      <img src="./image/readme-topic-agent.png" alt="方向页预览" width="100%" />
      <br />
      <strong>方向聚合页</strong>
      <br />
      用技术方向聚合历史论文，适合做专题浏览
    </td>
  </tr>
</table>

## 核心规则

### 1. 数据来源

当前抓取链路使用这 4 类真实外部来源：

- `Hugging Face Daily Papers API`
- `arXiv API`
- `GitHub Trending`
- `Semantic Scholar`

其中：

- Hugging Face 与 arXiv 提供论文主数据。
- GitHub Trending 用于判断论文是否命中开源热度信号。
- Semantic Scholar 用于计算 `academic_influence` 分数。

### 2. 时间规则

- `issue_date`：简报发布日期
- `fetch_date = issue_date - 3 天`

日常任务会优先抓 `issue_date - 3` 的论文；如果当天供给为空，会继续向前回退最多 `3` 天寻找非空抓取结果。

### 3. 评分机制

每篇论文会基于以下 8 类信号打分：

1. 顶级机构作者
2. Hugging Face Daily 推荐
3. 社区热度（upvotes）
4. 顶会/重要 venue
5. 是否存在代码信号
6. 工程实践相关关键词
7. 学术影响力（由 citationCount 换算）
8. GitHub Trending 开源趋势

方向标签由标题和摘要中的 taxonomy 关键词规则推断，例如 `Agent`、`RAG`、`Reasoning`、`Vision_Image`、`Safety_Alignment` 等。

### 4. 发布策略

当前实现已经切换到“数量优先发布”：

- `Focus`
  - 优先选取 `score >= 80` 的论文
  - 若不足 `5` 篇，则从剩余高分论文中继续补位，直到达到 `5` 篇或候选耗尽
- `Watching`
  - 在剔除已进入 Focus 的论文后，从 `50 <= score < 80` 中按分数倒序取最多 `12` 篇
  - 可以少于 `12`，必要时也可以为 `0`
- `Candidate`
  - `low_score`：分数低于 `50`
  - `capacity_overflow`：分数达到档位但超出容量窗口
  - `reviewer_rejected`：进入 AI 生产链但最终未通过发布门禁

### 5. 候选池上限

每天最终只保留评分前 `50` 名论文进入 `paper_summary` 快照。超过 `50` 的论文不会进入当天候选池页面。

## AI 生产链

### 当前实现

入选论文会按“单篇隔离”的方式执行同一条主链：

1. `Editor`
   - 确定写作角度、核心痛点、具体解法
2. `Writer`
   - 生成中文/英文一句话总结、亮点和应用场景
3. `Reviewer`
   - 做最后一轮质量门禁，决定通过或拒绝

每个阶段的输出和失败重试都会写入 `paper_ai_trace`，用于审计和排障，不直接在前端展示。

### 当前模型配置

当前仓库默认接入的是：

- `MiniMax-M2.5`
- OpenAI 兼容调用方式
- `KIMI_BASE_URL=https://api.minimaxi.com/v1`

为了兼容历史实现，部分环境变量仍沿用 `KIMI_*` 前缀，但当前默认服务商已经是 `MiniMax`，不是 Moonshot Kimi。

## 数据落库方式

### 关键数据表

- `paper`
  - 论文静态元数据，如 `arxiv_id`、中英文标题、作者、venue、abstract、pdf_url
- `paper_summary`
  - 以 `issue_date` 为核心的快照表，是首页、详情页、候选池和方向页的查询真相源
- `paper_ai_trace`
  - `Editor / Writer / Reviewer` 的中间产物与状态留痕
- `system_task_log`
  - 每个期号任务的抓取数量、处理数量、成功/失败状态与错误日志
- `subscriber`
  - 邮件订阅状态、验证 token、退订 token
- `notification_delivery_log`
  - 日报邮件与任务告警邮件的发送审计与幂等留痕

### 一个实现细节

当前 `paper` 表并不持久化原始 `citationCount`。系统会在打分阶段实时获取引用数，并把换算后的 `academic_influence` 分数落到 `paper_summary.score_reasons` 中。

## 系统结构

```text
External Sources
  -> Crawler
  -> Scorer
  -> Pipeline
     -> Title Localization
     -> Editor
     -> Writer
     -> Reviewer
  -> MySQL
  -> FastAPI API
  -> Vue Web UI / Email Digest
```

<p align="center">
  <img src="./image/Structural%20diagram.png" alt="ArxivDaily 结构图" width="100%" />
</p>

## 前后端能力边界

### 前端

- 首页 `/`
  - 每页只展示一个 `issue_date`
  - 右侧日历可快速跳转
  - 无数据日期显示为灰色
- 详情页 `/paper/:id`
  - 展示双语解读与论文基础信息
- 候选池页 `/sources/:date`
  - 展示当天保留到快照中的全部候选论文
- 方向页 `/topic/:name`
  - 某个固定方向下的历史论文聚合
- 分类总览页 `/topics`
  - 展示全部方向入口
- 退订页 `/unsubscribe`
  - 供邮件中的退订链接回跳使用

### 后端

- 论文列表、详情、候选池、日历数据接口
- 邮件订阅、邮箱验证、退订接口
- 每日更新、历史回填、日报发送、cron 安装脚本
- Ubuntu `systemd + nginx + cron` 的生产部署资产

## 仓库结构

```text
.
├── backend/
│   ├── app/
│   │   ├── api/v1/            # FastAPI 路由
│   │   ├── core/              # 配置与规格常量
│   │   ├── db/                # SQLAlchemy engine / session
│   │   ├── models/            # ORM 模型
│   │   ├── schemas/           # Pydantic 模型
│   │   └── services/          # crawler / scorer / ai_processor / pipeline / mailer
│   ├── prompts/               # Editor / Writer / Reviewer 提示词
│   ├── scripts/               # 跑批、回填、发报、部署辅助脚本
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── api/
│   │   ├── router/
│   │   └── views/
│   └── package.json
├── database/
│   ├── schema.sql
│   └── migrate_v225.sql
├── deploy/linux/
│   ├── ai-paper-summary.nginx.conf
│   ├── ai-paper-summary-backend.service
│   └── DEPLOY.md
├── tests/
│   ├── backend/
│   ├── frontend/
│   ├── live/
│   ├── smoke/
│   └── fixtures/
└── Detailed_PRD.md
```

## 本地启动

### 1. 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-test.txt
cp .env.example .env
```

至少需要配置这些环境变量：

```env
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/ai_paper_summary
BACKEND_PUBLIC_URL=http://127.0.0.1:8000
FRONTEND_URL=http://127.0.0.1:5173

MINIMAX_API_KEY=your-api-key
KIMI_BASE_URL=https://api.minimaxi.com/v1
KIMI_MODEL=MiniMax-M2.5

SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_FROM_EMAIL=no-reply@example.com
OWNER_ALERT_EMAIL=you@example.com
```

初始化数据库：

```bash
cd backend
./venv/bin/python scripts/setup_local_db.py
```

如果你本机是 Oracle 安装包版 MySQL，仓库还提供了一个系统 MySQL 引导脚本：

```bash
cd backend
./venv/bin/python scripts/setup_local_mysql.py
```

启动后端：

```bash
cd backend
./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. 前端

```bash
cd frontend
npm install
```

开发环境 `.env.local`：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

启动前端：

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

生产构建：

```bash
cd frontend
npm run build
```

`frontend/.env.production` 当前保持为空字符串，因为前端生产环境直接请求同源 `/api/v1/...`，由 `nginx` 负责反向代理。

## 日常运行与运维脚本

### 日更任务

```bash
cd backend
./venv/bin/python scripts/run_daily_update_job.py
```

- 按上海时区计算当日 `issue_date`
- 调用共享的 `run_issue_pipeline(...)`
- 失败时向 `OWNER_ALERT_EMAIL` 发告警邮件

### 每日简报邮件

```bash
cd backend
./venv/bin/python scripts/send_daily_digest.py
```

- 只会在当日 `issue_date` 成功生成后发送
- 只发送给 `subscriber.status = 1` 的有效订阅用户
- 发送前会刷新退订 token

### 跑一次完整流水线

```bash
cd backend
./venv/bin/python scripts/run_pipeline_once.py
```

### 指定日期回填

```bash
cd backend
./venv/bin/python scripts/backfill_issue_range.py --start-date 2026-02-13 --end-date 2026-03-30
```

当前历史回填和日常发布共享同一条入口：

- [backend/app/services/issue_pipeline_runner.py](/Users/zhangshijie/Desktop/Project/AI_paper_summary_website/backend/app/services/issue_pipeline_runner.py)

这意味着两者都会调用同一套：

- `Crawler`
- `Scorer`
- `Pipeline.run(...)`
- `Editor -> Writer -> Reviewer`

## Ubuntu 生产部署

仓库已经提供了 Linux 单机部署资产：

- `nginx` 配置：`deploy/linux/ai-paper-summary.nginx.conf`
- `systemd` 服务：`deploy/linux/ai-paper-summary-backend.service`
- 部署说明：`deploy/linux/DEPLOY.md`

当前推荐的生产形态是：

- `MySQL`：本机服务
- `FastAPI`：`uvicorn` 监听 `127.0.0.1:8000`
- `Vue`：`frontend/dist` 交给 `nginx` 托管
- `systemd`：托管后端服务
- `cron`：`08:00` 更新、`08:30` 发日报

安装 cron：

```bash
cd backend
./venv/bin/python scripts/install_linux_cron.py
```

## GitHub Actions CI/CD

仓库现在约定使用两条 GitHub Actions workflow：

- `CI`
  - 触发：`pull_request` 到 `main`、`push` 到 `main`
  - 内容：
    - 后端：`tests/backend + tests/smoke`
    - 外网：`tests/live`
    - 前端：`npm run test:run` + `npm run build`
- `Deploy`
  - 触发：
    - `CI` 在 `main` 分支的 `push` 成功后自动触发
    - 或手动 `workflow_dispatch`
  - 内容：
    - 通过 SSH 登录现有 Ubuntu 服务器
    - 更新 `/srv/ai-paper-summary`
    - 用 GitHub `production` Environment Secrets 渲染并覆盖 `backend/.env`
    - 执行 `setup_local_db.py`
    - 重建前端并重启 `ai-paper-summary-backend`
    - 做本机后端与 `arxivdaily.tech` 入口健康检查

### GitHub Secrets / Environment Secrets

推荐把部署 workflow 绑定到 GitHub `production` Environment，并把敏感值放在该 Environment Secrets 下。

部署连接类：

- `DEPLOY_HOST`
- `DEPLOY_PORT`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`
- `DEPLOY_KNOWN_HOSTS`

业务运行类：

- `DATABASE_URL`
- `MINIMAX_API_KEY`
- `KIMI_API_KEY`（可选，兼容旧变量）
- `BACKEND_PUBLIC_URL`
- `FRONTEND_URL`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_FROM_NAME`
- `SMTP_USE_STARTTLS`
- `SMTP_USE_SSL`
- `OWNER_ALERT_EMAIL`

可选覆盖的运行参数：

- `MYSQL_UNIX_SOCKET`
- `KIMI_BASE_URL`
- `KIMI_MODEL`
- `KIMI_TIMEOUT_SECONDS`
- `KIMI_LONGFORM_TIMEOUT_SECONDS`
- `KIMI_MAX_RETRIES`
- `KIMI_LONGFORM_MAX_RETRIES`
- `KIMI_TITLE_BATCH_SIZE`
- `PIPELINE_MAX_CATEGORY_ATTEMPTS`
- `PIPELINE_FOCUS_ATTEMPT_MULTIPLIER`
- `PIPELINE_WATCHING_ATTEMPT_MULTIPLIER`
- `PIPELINE_ENABLE_WATCHING`
- `PIPELINE_REVIEWER_STRICT`
- `PIPELINE_PROBE_DAYS`
- `SEMANTIC_SCHOLAR_TIMEOUT_SECONDS`
- `CRAWLER_CITATION_MAX_WORKERS`

固定写入 deploy 生成 `.env` 的默认值：

- `KIMI_MIN_REQUEST_INTERVAL_SECONDS=1.5`
- `KIMI_LONGFORM_MIN_REQUEST_INTERVAL_SECONDS=2.5`
- `KIMI_TITLE_LOCALIZATION_ATTEMPTS=4`
- `KIMI_EDITOR_MAX_TOKENS=1400`
- `KIMI_WRITER_FOCUS_MAX_TOKENS=1800`
- `KIMI_WRITER_WATCHING_MAX_TOKENS=1300`
- `KIMI_REVIEWER_MAX_TOKENS=512`

### 运行与安全约束

- `pull_request` 路径不会读取生产 Secrets
- 生产 `.env` 由 Actions 根据 `deploy/linux/backend.env.production.template` 渲染后覆盖到服务器
- 服务器上原有 `.env` 会先备份，再写入新版本
- 若仓库允许外部 fork PR，不要改成 `pull_request_target` 去跑带 Secrets 的逻辑
- 推荐给 `production` Environment 增加 required reviewers，至少为部署保留一层人工门禁
- 推荐在 GitHub 仓库设置里把 `backend-tests`、`live-tests`、`frontend-tests` 设为 `main` 的 required checks

## 测试

### 后端主回归

```bash
cd backend
./venv/bin/pytest ../tests/backend ../tests/smoke
```

### 真实外网 crawler 测试

```bash
cd backend
./venv/bin/pytest ../tests/live
```

### 前端测试

```bash
cd frontend
npm run test:run
```

### 常用烟测

```bash
cd backend
./venv/bin/python -m compileall app scripts

cd frontend
npm run build
```

## 当前边界与已知事实

- `tests/live` 只覆盖真实外网 crawler，不等同于完整的 `LLM + MySQL + API + 前端` 全链路回归。
- AI 中间产物已经落库，但默认不在前端显示。
- 当前 README 不再把 RSS 作为正式产品能力描述，因为这条需求目前不作为项目主功能承诺。
- 代码里仍保留一部分历史命名，例如 `KIMI_*` 配置前缀，但当前默认模型服务商是 `MiniMax`。
- Vite 生产构建目前仍会提示主 chunk 偏大，但不影响构建成功。

## 进一步阅读

- 产品规格：[Detailed_PRD.md](/Users/zhangshijie/Desktop/Project/AI_paper_summary_website/Detailed_PRD.md)
- 代码图谱入口：[.nexus-map/INDEX.md](/Users/zhangshijie/Desktop/Project/AI_paper_summary_website/.nexus-map/INDEX.md)
- 测试说明：[tests/README.md](/Users/zhangshijie/Desktop/Project/AI_paper_summary_website/tests/README.md)
- Linux 部署说明：[deploy/linux/DEPLOY.md](/Users/zhangshijie/Desktop/Project/AI_paper_summary_website/deploy/linux/DEPLOY.md)

## License

MIT
