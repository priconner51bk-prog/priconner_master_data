from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / ".upstream"
INPUT = ROOT / ".input"
DB_PATH = INPUT / "roboninon.db"
OUTPUT = ROOT / "dist"
UPSTREAM_URL = "https://github.com/esterTion/redive_master_db_diff.git"
DB_URL = "https://roboninon.win/db/download"


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


def download_db() -> None:
    INPUT.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix="roboninon.", suffix=".db", dir=INPUT)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        request = urllib.request.Request(DB_URL, headers={"User-Agent": "priconner-master-data"})
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        temporary.replace(DB_PATH)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


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
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(result)
    print(result)


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
    download_db()
    run(
        [
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
    )
    run([sys.executable, "-m", "pytest", "-q"])
    sync_google_sheets()
    publish_dist()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
