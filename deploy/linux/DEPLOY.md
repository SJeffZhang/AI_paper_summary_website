# Ubuntu Production Deployment

This project is deployed as a single-host Ubuntu stack:

- `nginx` serves `frontend/dist`
- `uvicorn` serves FastAPI on `127.0.0.1:8000`
- `mysql-server` stores application data
- `cron` runs the daily update and digest jobs

## Target layout

```text
/srv/ai-paper-summary/
├── backend/
│   ├── .env
│   ├── runtime/logs/
│   └── venv/
└── frontend/
    └── dist/
```

## 1. Install system dependencies

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv mysql-server nginx curl
```

Install Node.js 20 LTS:

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

## 2. Clone or update the repository

```bash
sudo mkdir -p /srv
sudo chown ubuntu:ubuntu /srv
cd /srv
git clone https://github.com/Mr-silence/AI_paper_summary_website.git ai-paper-summary
cd /srv/ai-paper-summary
```

If the repo already exists:

```bash
cd /srv/ai-paper-summary
git pull origin main
```

## 3. Configure the backend

```bash
cd /srv/ai-paper-summary/backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env
mkdir -p runtime/logs
```

Edit `backend/.env` with the production values if you are doing the first bootstrap or manual recovery.
If GitHub Actions auto-deploy is enabled, the deploy workflow will overwrite `backend/.env`
from GitHub `production` Environment Secrets on every release.

Manual `.env` baseline:

- `DATABASE_URL=mysql+pymysql://ai_paper_summary:<strong-password>@localhost:3306/ai_paper_summary`
- `MYSQL_UNIX_SOCKET=`
- `BACKEND_PUBLIC_URL=http://43.155.154.193`
- `FRONTEND_URL=http://43.155.154.193`
- `MINIMAX_API_KEY=<your-minimax-api-key>`
- `KIMI_API_KEY=<optional-legacy-key>`
- `SMTP_HOST=smtp.gmail.com`
- `SMTP_PORT=587`
- `SMTP_USERNAME=z1332556430@gmail.com`
- `SMTP_PASSWORD=<gmail-app-password>`
- `SMTP_FROM_EMAIL=z1332556430@gmail.com`
- `SMTP_FROM_NAME=AI Paper Summary`
- `SMTP_USE_STARTTLS=true`
- `SMTP_USE_SSL=false`
- `OWNER_ALERT_EMAIL=z1332556430@gmail.com`

## 4. Configure MySQL

```bash
sudo mysql
```

```sql
CREATE DATABASE IF NOT EXISTS ai_paper_summary
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'ai_paper_summary'@'localhost' IDENTIFIED BY '<strong-password>';
GRANT ALL PRIVILEGES ON ai_paper_summary.* TO 'ai_paper_summary'@'localhost';
FLUSH PRIVILEGES;
```

Run schema validation or migration:

```bash
cd /srv/ai-paper-summary/backend
./venv/bin/python scripts/setup_local_db.py
```

For an existing pre-v2.25 database:

```bash
./venv/bin/python scripts/setup_local_db.py --migrate-existing --backfill-title-zh
```

## 5. Build the frontend

```bash
cd /srv/ai-paper-summary/frontend
npm install
npm run build
```

`frontend/.env.production` keeps `VITE_API_BASE_URL` empty, because the frontend API adapter already requests `/api/v1/...` directly and production should avoid adding a second `/api` prefix.

## 6. Install systemd and nginx configs

```bash
sudo cp /srv/ai-paper-summary/deploy/linux/ai-paper-summary-backend.service /etc/systemd/system/
sudo cp /srv/ai-paper-summary/deploy/linux/ai-paper-summary.nginx.conf /etc/nginx/sites-available/ai-paper-summary
sudo ln -sf /etc/nginx/sites-available/ai-paper-summary /etc/nginx/sites-enabled/ai-paper-summary
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl daemon-reload
sudo systemctl enable mysql
sudo systemctl enable ai-paper-summary-backend
sudo systemctl enable nginx
sudo systemctl restart ai-paper-summary-backend
sudo nginx -t
sudo systemctl restart nginx
```

Notes:

- `requirements.txt` includes `cryptography`, because Ubuntu MySQL commonly defaults to `caching_sha2_password`, and `PyMySQL` needs that package to authenticate successfully.
- The three services that must survive reboot are `mysql`, `ai-paper-summary-backend`, and `nginx`.

## 7. Install cron jobs

```bash
cd /srv/ai-paper-summary/backend
./venv/bin/python scripts/install_linux_cron.py
crontab -l
```

The managed cron block installs:

- `08:00` Asia/Shanghai: `run_daily_update_job.py`
- `08:30` Asia/Shanghai: `send_daily_digest.py`

## 8. Data migration

From the source machine:

```bash
mysqldump --single-transaction --default-character-set=utf8mb4 ai_paper_summary > ai_paper_summary.sql
scp ai_paper_summary.sql ubuntu@43.155.154.193:/tmp/ai_paper_summary.sql
```

On the server:

```bash
mysql -u ai_paper_summary -p ai_paper_summary < /tmp/ai_paper_summary.sql
cd /srv/ai-paper-summary/backend
./venv/bin/python scripts/setup_local_db.py
```

## 9. Verification

```bash
systemctl status ai-paper-summary-backend
sudo systemctl status nginx
curl http://127.0.0.1:8000/
curl http://43.155.154.193/api/v1/papers
```

Manual digest test:

```bash
cd /srv/ai-paper-summary/backend
./venv/bin/python scripts/send_daily_digest.py --issue-date 2026-03-25 --recipient-override z1332556430+briefingtest@gmail.com
```

## 10. Rollback and diagnostics

Common commands:

```bash
sudo journalctl -u ai-paper-summary-backend -n 200 --no-pager
sudo tail -n 200 /var/log/nginx/ai-paper-summary.error.log
tail -n 200 /srv/ai-paper-summary/backend/runtime/logs/daily_update.log
tail -n 200 /srv/ai-paper-summary/backend/runtime/logs/daily_digest.log
```

## 11. GitHub Actions CI/CD

The repository now expects two workflows under `.github/workflows/`:

- `ci.yml`
  - runs on `pull_request` to `main` and `push` to `main`
  - executes:
    - `cd backend && python -m pytest ../tests/backend ../tests/smoke`
    - `cd backend && python -m pytest ../tests/live`
    - `cd frontend && npm ci && npm run test:run && npm run build`
- `deploy.yml`
  - runs automatically when `CI` succeeds for a `push` on `main`
  - also supports manual `workflow_dispatch`
  - connects to the Ubuntu server over SSH
  - renders `deploy/linux/backend.env.production.template`
  - uploads the rendered file to `/srv/ai-paper-summary/backend/.env`
  - updates code, validates config, runs `setup_local_db.py`, rebuilds frontend, restarts `ai-paper-summary-backend`, and performs health checks

Recommended GitHub `production` Environment Secrets:

Connection:

- `DEPLOY_HOST`
- `DEPLOY_PORT`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`
- `DEPLOY_KNOWN_HOSTS`

Runtime:

- `DATABASE_URL`
- `MINIMAX_API_KEY`
- `KIMI_API_KEY` (optional legacy fallback)
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

Optional runtime overrides:

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

The deploy workflow writes these production defaults directly and does not read them from GitHub Secrets:

- `KIMI_MIN_REQUEST_INTERVAL_SECONDS=1.5`
- `KIMI_LONGFORM_MIN_REQUEST_INTERVAL_SECONDS=2.5`
- `KIMI_TITLE_LOCALIZATION_ATTEMPTS=4`
- `KIMI_EDITOR_MAX_TOKENS=1400`
- `KIMI_WRITER_FOCUS_MAX_TOKENS=1800`
- `KIMI_WRITER_WATCHING_MAX_TOKENS=1300`
- `KIMI_REVIEWER_MAX_TOKENS=512`

Operational notes:

- The deploy job should be bound to the GitHub `production` Environment.
- CI jobs must not read production secrets.
- Do not use `pull_request_target` for code that touches deploy secrets.
- The workflow backs up the existing `.env` before replacing it.
- If you want one more manual gate before production, configure required reviewers on the `production` Environment.
