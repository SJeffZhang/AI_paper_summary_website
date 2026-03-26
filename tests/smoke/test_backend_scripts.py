import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import BACKEND_DIR


pytestmark = pytest.mark.smoke


def test_backend_compileall_smoke():
    result = subprocess.run(
        [sys.executable, "-m", "compileall", "app", "scripts"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


@pytest.mark.parametrize(
    "script_name",
    [
        "backfill_title_zh.py",
        "backfill_issue_range.py",
        "run_daily_update_job.py",
        "send_daily_digest.py",
        "install_linux_cron.py",
    ],
)
def test_backend_script_import_smoke(script_name):
    script_path = BACKEND_DIR / "scripts" / script_name
    spec = importlib.util.spec_from_file_location("backfill_title_zh", script_path)

    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(module.main)
