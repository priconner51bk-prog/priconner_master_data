from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import csv
from datetime import datetime, timezone
from pathlib import Path

NO_CHANGE = "NO_CHANGE"
SCHEMA_VERSION = "1"
SOURCE = "esterTion/redive_master_db_diff"
# Known replacement for the legacy DB's mojibake entry. Keep this explicit
# rather than silently guessing when a Japanese name is not decodable.
UNIT_NAME_JP_OVERRIDES = {140301: "ティア"}


class SchemaError(RuntimeError):
    pass


def derive_alias(name: str) -> str | None:
    """Derive only the conservative base name before a parenthesized variant."""
    import re
    base = re.sub(r"[（(].*[）)]\s*$", "", name).strip()
    return base if base and base != name else None


def apply_dynamic_aliases(rows: list[dict]) -> list[dict]:
    """空のaliasesに限り、名称から安全にaliasを1件補う。"""
    for row in rows:
        if not row.get("aliases"):
            alias = derive_alias(row["name"]) or row["name"].strip()
            if alias:
                row["aliases"] = [alias]
    return rows


def read_upstream_revision(source_dir: Path) -> dict[str, str]:
    """Read lightweight upstream identity without downloading/building data."""
    truth = source_dir / "!TruthVersion.txt"
    if not truth.is_file():
        raise FileNotFoundError(f"upstream revision file not found: {truth}")
    truth_version = truth.read_text(encoding="utf-8-sig").strip()
    if not truth_version:
        raise ValueError(f"empty upstream revision: {truth}")
    import subprocess
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(source_dir), "rev-parse", "HEAD"],
            text=True, stderr=subprocess.STDOUT,
        ).strip()
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"upstream is not a readable git checkout: {source_dir}") from exc
    if len(commit) != 40:
        raise ValueError(f"invalid upstream commit SHA: {commit!r}")
    return {"source_commit": commit, "truth_version": truth_version}


def _require(conn: sqlite3.Connection, table: str, columns: set[str]) -> None:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    actual = {row[1] for row in rows}
    if not columns <= actual:
        raise SchemaError(f"unsupported schema: {table}; missing={sorted(columns - actual)}")


def extract(db_path: Path, unit_status_path: Path | None = None, now: datetime | None = None, strict_boss_count: bool = False) -> dict:
    with sqlite3.connect(db_path) as conn:
        _require(conn, "unit_data", {"unit_id", "unit_name", "unit_name_jp"})
        _require(conn, "enemy_parameter", {"enemy_id", "unit_id", "name_jp", "name"})
        units = conn.execute("""SELECT unit_id, COALESCE(NULLIF(unit_name_jp,''), unit_name), unit_name
            FROM unit_data WHERE unit_id < 190000 ORDER BY unit_id""").fetchall()
        candidates = conn.execute("""SELECT enemy_id, unit_id, name, name_jp, hp
            FROM enemy_parameter WHERE enemy_id LIKE '4019%' AND hp >= 1000000000
            ORDER BY enemy_id""").fetchall()
    known_units: dict[int, str] | None = None
    if unit_status_path is not None:
        with unit_status_path.open(encoding="utf-8-sig", newline="") as f:
            known_units = {int(r["unit_id"]): (r["unit_name_jp"], r["unit_name"]) for r in csv.DictReader(f)}
    bosses = [(enemy_id, name_jp or (known_units[unit_id][0] if known_units is not None else name))
              for enemy_id, unit_id, name, name_jp, _ in candidates
               if known_units is None or unit_id in known_units]
    characters = [{"id": int(i), "name": UNIT_NAME_JP_OVERRIDES.get(int(i), jp), "name_en": en, "aliases": []} for i, jp, en in units]
    # 配布対象は開催中の1開催分だけ。未到着なら直近の開催分を維持する。
    if bosses:
        current_month = (now or datetime.now(timezone.utc)).month
        months = [int(str(i)[4:6]) for i, _ in bosses]
        counts = {m: months.count(m) for m in set(months)}
        complete = [m for m, count in counts.items() if count >= 5 and m <= current_month]
        target_month = max(complete) if complete else (current_month if current_month in counts else max(months))
        bosses = [(pair[0], pair[1]) for pair, month in zip(bosses, months) if month == target_month]
    clan_battle_bosses = [{"id": int(i), "name": n, "aliases": []} for i, n in bosses]
    if strict_boss_count and len(clan_battle_bosses) != 5:
        raise SchemaError(
            f"incomplete clan battle boss set: expected 5, got {len(clan_battle_bosses)}"
        )
    apply_dynamic_aliases(characters)
    apply_dynamic_aliases(clan_battle_bosses)
    _validate(characters, "characters")
    _validate(clan_battle_bosses, "clan_battle_bosses")
    return {"characters": characters, "clan_battle_bosses": clan_battle_bosses}


def _validate(rows: list[dict], kind: str) -> None:
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)) or any(i <= 0 for i in ids):
        raise ValueError(f"invalid or duplicate IDs in {kind}")
    if any(not isinstance(r["name"], str) or not r["name"].strip() for r in rows):
        raise ValueError(f"missing name in {kind}")
    aliases: dict[str, int] = {}
    for row in rows:
        for alias in row["aliases"]:
            aliases.setdefault(alias, row["id"])


def generate(db_path: Path, output_dir: Path, source_commit: str, now: str | None = None,
             unit_status_path: Path | None = None) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    meta_path = output_dir / "metadata.json"
    if meta_path.exists():
        old = json.loads(meta_path.read_text(encoding="utf-8"))
        if old.get("source_commit") == source_commit:
            return NO_CHANGE
    data = extract(db_path, unit_status_path=unit_status_path)
    metadata = {"schema_version": SCHEMA_VERSION, "source": SOURCE,
                "source_commit": source_commit,
                "generated_at": now or datetime.now(timezone.utc).isoformat()}
    payload = {**metadata, **data}
    _atomic_json(output_dir / "master_data.json", payload)
    for kind, rows in data.items():
        path = output_dir / f"{kind}.csv"
        fd, tmp = tempfile.mkstemp(dir=output_dir, prefix=f".{kind}.", suffix=".tmp", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
                fieldnames = ["id", "name"] + (["name_en"] if any("name_en" in row for row in rows) else []) + ["aliases"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow({**row, "aliases": json.dumps(row["aliases"], ensure_ascii=False, separators=(",", ":"))})
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    _atomic_json(meta_path, metadata)
    return "UPDATED"


def generate_from_upstream(source_dir: Path, db_path: Path, output_dir: Path,
                           now: str | None = None,
                           unit_status_path: Path | None = None) -> str:
    """Use upstream checkout identity as the only update gate for generation."""
    revision = read_upstream_revision(source_dir)
    return generate(db_path, output_dir, revision["source_commit"], now=now,
                    unit_status_path=unit_status_path)


def _atomic_json(path: Path, value: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
