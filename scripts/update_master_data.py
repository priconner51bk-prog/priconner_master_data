from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / ".upstream"
INPUT = ROOT / ".input"
DB_PATH = INPUT / "master_data_source.db"
OUTPUT = ROOT / "dist"
UNIT_STATUS = Path(
    os.environ.get(
        "PRICONNER_UNIT_STATUS_PATH",
        str(ROOT.parent / "priconner_data_tool" / "priconner_data" / "UnitStatus.csv"),
    )
)
UPSTREAM_URL = "git@github.com:esterTion/redive_master_db_diff.git"

sys.path.insert(0, str(ROOT))
from master_data.source_sql import build_database


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    print("$", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def ensure_dist_clean() -> None:
    result = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", "dist"],
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("dist has pre-existing uncommitted changes; refusing to overwrite or publish it")


def checkout_upstream() -> None:
    if not (UPSTREAM / ".git").exists():
        UPSTREAM.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--depth", "1", UPSTREAM_URL, str(UPSTREAM)])
        return

    status = subprocess.run(
        ["git", "-C", str(UPSTREAM), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        raise RuntimeError(f"upstream checkout has local changes: {UPSTREAM}")
    run(["git", "-C", str(UPSTREAM), "fetch", "--depth", "1", "origin"])
    branch = subprocess.check_output(
        ["git", "-C", str(UPSTREAM), "branch", "--show-current"],
        text=True,
    ).strip()
    if not branch:
        raise RuntimeError(f"upstream checkout is detached: {UPSTREAM}")
    run(["git", "-C", str(UPSTREAM), "reset", "--hard", f"origin/{branch}"])


def build_source_db() -> None:
    build_database(UPSTREAM, DB_PATH)


def sync_google_sheets() -> None:
    webhook_url = os.environ.get("APPS_SCRIPT_WEBHOOK_URL")
    webhook_token = os.environ.get("APPS_SCRIPT_WEBHOOK_TOKEN")
    if not webhook_url or not webhook_token:
        print("Webhook secrets are not configured; skipping Google Sheets sync.")
        return

    payload = json.loads((OUTPUT / "master_data.json").read_text(encoding="utf-8"))
    body = json.dumps({"token": webhook_token, "payload": payload}).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
            if not isinstance(result, dict) or not result.get("ok"):
                raise RuntimeError(result)
            print(result)
            return
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, RuntimeError, TimeoutError) as exc:
            last_error = exc
            if attempt == 2:
                raise RuntimeError("Google Sheets webhook failed after 3 attempts") from exc
            print(f"Google Sheets webhook attempt {attempt + 1} failed; retrying.", flush=True)
            time.sleep(2 ** attempt)
    raise RuntimeError("Google Sheets webhook failed") from last_error


def publish_dist() -> None:
    run(["git", "add", "--", "dist"])
    changed = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", "dist"],
        cwd=ROOT,
        check=False,
    )
    if changed.returncode == 0:
        print("dist is unchanged; nothing to publish.")
        return
    run(["git", "commit", "--only", "dist", "-m", "chore: update master data"])
    run(["git", "push"])


def main() -> int:
    ensure_dist_clean()
    checkout_upstream()
    build_source_db()
    # Run the repository tests before generating dist/.  If a scheduled run
    # fails here, the next run must still be able to start.  Generating first
    # leaves dist/ dirty on a test failure, which then makes
    # ensure_dist_clean() reject every retry.
    run([sys.executable, "-m", "pytest", "-q"])
    generate_command = [
        sys.executable,
        "scripts/generate_master_data.py",
        "--upstream",
        str(UPSTREAM),
        "--db",
        str(DB_PATH),
        "--output",
        str(OUTPUT),
        "--force",
    ]
    if UNIT_STATUS.is_file():
        generate_command.extend(["--unit-status", str(UNIT_STATUS)])
    run(generate_command)
    sync_google_sheets()
    publish_dist()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
