import os
import subprocess
from shutil import which
from pathlib import Path

import pytest

from tests.conftest import FRONTEND_DIR


pytestmark = pytest.mark.smoke


def _resolve_npm_binary() -> str:
    return which("npm") or "/opt/homebrew/bin/npm"


def test_frontend_build_smoke(tmp_path):
    out_dir = tmp_path / "frontend-build"
    env = dict(os.environ)
    env["PATH"] = f"/opt/homebrew/bin:{env.get('PATH', '')}"
    result = subprocess.run(
        [_resolve_npm_binary(), "run", "build", "--", "--outDir", str(out_dir)],
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert out_dir.exists()
