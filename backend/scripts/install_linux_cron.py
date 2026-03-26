import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT
RUNTIME_LOG_DIR = PROJECT_ROOT / "runtime" / "logs"
MANAGED_BLOCK_START = "# >>> AI_PAPER_SUMMARY_CRON >>>"
MANAGED_BLOCK_END = "# <<< AI_PAPER_SUMMARY_CRON <<<"


def build_cron_block(*, python_bin: str, repo_root: Path, backend_dir: Path, log_dir: Path) -> str:
    update_log = log_dir / "daily_update.log"
    digest_log = log_dir / "daily_digest.log"
    update_command = (
        f"cd {backend_dir} && {python_bin} scripts/run_daily_update_job.py "
        f">> {update_log} 2>&1"
    )
    digest_command = (
        f"cd {backend_dir} && {python_bin} scripts/send_daily_digest.py "
        f">> {digest_log} 2>&1"
    )
    lines = [
        MANAGED_BLOCK_START,
        f"# repo: {repo_root}",
        "CRON_TZ=Asia/Shanghai",
        f"0 8 * * * {update_command}",
        f"30 8 * * * {digest_command}",
        MANAGED_BLOCK_END,
    ]
    return "\n".join(lines)


def merge_managed_block(existing_crontab: str, managed_block: str) -> str:
    lines = existing_crontab.splitlines()
    start_index = next((idx for idx, line in enumerate(lines) if line.strip() == MANAGED_BLOCK_START), None)
    end_index = next((idx for idx, line in enumerate(lines) if line.strip() == MANAGED_BLOCK_END), None)

    if start_index is not None and end_index is not None and start_index <= end_index:
        preserved = lines[:start_index] + lines[end_index + 1 :]
    else:
        preserved = lines

    preserved_text = "\n".join(line for line in preserved if line.strip())
    if preserved_text:
        return preserved_text + "\n\n" + managed_block + "\n"
    return managed_block + "\n"


def read_existing_crontab() -> str:
    result = subprocess.run(
        ["crontab", "-l"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout
    if result.returncode == 1 and "no crontab for" in (result.stderr or "").lower():
        return ""
    raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "crontab -l failed")


def install_cron(managed_crontab: str) -> None:
    subprocess.run(
        ["crontab", "-"],
        input=managed_crontab,
        check=True,
        text=True,
        capture_output=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Install managed cron entries for AI Paper Summary on Linux.")
    parser.add_argument(
        "--python-bin",
        default=sys.executable,
        help="Python interpreter path that cron should use.",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print the managed cron block instead of installing it.",
    )
    args = parser.parse_args()

    RUNTIME_LOG_DIR.mkdir(parents=True, exist_ok=True)
    managed_block = build_cron_block(
        python_bin=args.python_bin,
        repo_root=PROJECT_ROOT.parent,
        backend_dir=BACKEND_DIR,
        log_dir=RUNTIME_LOG_DIR,
    )
    if args.print_only:
        print(managed_block)
        return

    existing_crontab = read_existing_crontab()
    merged_crontab = merge_managed_block(existing_crontab, managed_block)
    install_cron(merged_crontab)
    print("Linux cron entries installed successfully.")


if __name__ == "__main__":
    main()
