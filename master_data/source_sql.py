from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path


SOURCE_FILES = {
    "unit_data": "v1_ed1b52317ac09b3d790c8feebcfb4fb224b0a1cf16034f167e128f147a09da36.sql",
    "enemy_parameter": "v1_7ce15cd873f0e35053e2a1c15111fa91cec7710d5d3ab887d94179e883f46cea.sql",
    "clan_battle_schedule": "v1_74bde0aea50434815d2e25b3a60c6596637b9692ef1fabf603685065610b9f98.sql",
}


class SourceSchemaError(RuntimeError):
    pass


def _load_rows(source_dir: Path, filename: str) -> list[tuple]:
    path = source_dir / filename
    if not path.is_file():
        raise FileNotFoundError(f"GitHub source SQL not found: {path}")
    table = path.stem
    with sqlite3.connect(":memory:") as conn:
        try:
            conn.executescript(path.read_text(encoding="utf-8"))
            return conn.execute(f'SELECT * FROM "{table}"').fetchall()
        except sqlite3.DatabaseError as exc:
            raise SourceSchemaError(f"cannot load GitHub source SQL: {path}") from exc


def build_database(source_dir: Path, output_path: Path) -> None:
    """Build the small normalized SQLite input used by the data pipeline.

    The upstream repository intentionally hashes table and column names.  The
    column positions below are checked against stable anchor values and the
    generated database is written atomically, so a changed upstream schema
    fails closed instead of publishing incorrect data.
    """
    units = _load_rows(source_dir, SOURCE_FILES["unit_data"])
    enemies = _load_rows(source_dir, SOURCE_FILES["enemy_parameter"])
    schedules = _load_rows(source_dir, SOURCE_FILES["clan_battle_schedule"])

    if not any(len(row) >= 25 and row[3] == 100101 for row in units):
        raise SourceSchemaError("unit_data mapping changed: character anchor 100101 is missing")
    if not any(len(row) >= 44 and row[20] == 401908408 for row in enemies):
        raise SourceSchemaError("enemy_parameter mapping changed: boss anchor 401908408 is missing")
    if not any(len(row) >= 13 and row[7] in range(1, 13) and str(row[3]).startswith("20") for row in schedules):
        raise SourceSchemaError("clan_battle_schedule mapping changed: start/release columns are missing")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix="master-data.", suffix=".db", dir=output_path.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        unit_rows: dict[int, tuple[int, str, str]] = {}
        for row in units:
            if len(row) >= 25:
                unit_id = int(row[3])
                unit_rows.setdefault(unit_id, (unit_id, str(row[17]), str(row[17])))
        conn = sqlite3.connect(temporary)
        try:
            conn.executescript(
                """
                CREATE TABLE unit_data (unit_id INTEGER, unit_name TEXT, unit_name_jp TEXT);
                CREATE TABLE enemy_parameter (
                    enemy_id INTEGER, unit_id INTEGER, name TEXT, name_jp TEXT, hp INTEGER
                );
                CREATE TABLE clan_battle_schedule (release_month INTEGER, start_time TEXT);
                """
            )
            conn.executemany(
                "INSERT INTO unit_data VALUES (?, ?, ?)",
                list(unit_rows.values()),
            )
            conn.executemany(
                "INSERT INTO enemy_parameter VALUES (?, ?, ?, ?, ?)",
                [
                    (int(row[20]), int(row[6]), str(row[34]), str(row[34]), int(row[9]))
                    for row in enemies
                    if len(row) >= 44
                ],
            )
            conn.executemany(
                "INSERT INTO clan_battle_schedule VALUES (?, ?)",
                [(int(row[7]), str(row[3])) for row in schedules if len(row) >= 13],
            )
            conn.commit()
        finally:
            conn.close()
        os.replace(temporary, output_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
