from pathlib import Path

from master_data.source_sql import SOURCE_FILES, build_database


def _sql(table: str, columns: int, rows: list[tuple]) -> str:
    names = ", ".join(f"'c{i}' INTEGER" for i in range(columns))
    values = "\n".join(
        f"INSERT INTO '{table}' VALUES ({', '.join(repr(value) for value in row)});"
        for row in rows
    )
    return f"CREATE TABLE '{table}' ({names});\n{values}\n"


def test_build_database_from_github_sql(tmp_path: Path):
    source = tmp_path / "upstream"
    source.mkdir()
    unit = [0] * 25
    unit[2], unit[3], unit[17] = 100101, 100101, "ヒヨリ"
    enemy = [0] * 45
    enemy[6], enemy[9], enemy[20], enemy[34] = 319601, 2080000000, 401909401, "フロストハウンド"
    schedule = [0] * 13
    schedule[3], schedule[7] = "2026/09/25 5:00:00", 9
    for key, rows, columns in (
        ("unit_data", [tuple(unit)], 25),
        ("enemy_parameter", [tuple(enemy), tuple([0] * 20 + [401908408] + [0] * 24)], 45),
        ("clan_battle_schedule", [tuple(schedule)], 13),
    ):
        (source / SOURCE_FILES[key]).write_text(
            _sql(Path(SOURCE_FILES[key]).stem, columns, rows), encoding="utf-8"
        )

    output = tmp_path / "source.db"
    build_database(source, output)
    import sqlite3
    with sqlite3.connect(output) as conn:
        assert conn.execute("SELECT unit_id, unit_name_jp FROM unit_data").fetchone() == (100101, "ヒヨリ")
        assert conn.execute("SELECT enemy_id, hp FROM enemy_parameter WHERE enemy_id=401909401").fetchone() == (401909401, 2080000000)
        assert conn.execute("SELECT release_month, start_time FROM clan_battle_schedule").fetchone() == (9, "2026/09/25 5:00:00")
