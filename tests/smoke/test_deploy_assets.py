from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.smoke


def test_linux_deploy_assets_exist():
    assert (PROJECT_ROOT / "deploy" / "linux" / "ai-paper-summary.nginx.conf").exists()
    assert (PROJECT_ROOT / "deploy" / "linux" / "ai-paper-summary-backend.service").exists()
    assert (PROJECT_ROOT / "deploy" / "linux" / "DEPLOY.md").exists()
    assert (PROJECT_ROOT / "deploy" / "linux" / "backend.env.production.template").exists()


def test_github_actions_workflows_exist():
    ci_workflow = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
    deploy_workflow = PROJECT_ROOT / ".github" / "workflows" / "deploy.yml"

    assert ci_workflow.exists()
    assert deploy_workflow.exists()

    ci_content = ci_workflow.read_text(encoding="utf-8")
    deploy_content = deploy_workflow.read_text(encoding="utf-8")

    assert "pull_request:" in ci_content
    assert "tests/live" in ci_content
    assert "workflow_run:" in deploy_content
    assert "environment: production" in deploy_content


def test_frontend_production_env_uses_same_origin_api():
    env_path = PROJECT_ROOT / "frontend" / ".env.production"
    content = env_path.read_text(encoding="utf-8")
    assert "VITE_API_BASE_URL=" in content
    assert "VITE_API_BASE_URL=/api" not in content
