import os
import sqlite3
from pathlib import Path

import pytest

from master_data.pipeline import extract


DATA_TOOL = Path(os.environ.get("PRICONNER_DATA_TOOL_ROOT", "D:/git/priconner_data_tool"))
DB = DATA_TOOL / "priconner_data" / "roboninon.db"
UNIT_STATUS = DATA_TOOL / "priconner_data" / "UnitStatus.csv"


@pytest.mark.skipif(not DB.is_file() or not UNIT_STATUS.is_file(), reason="legacy data_tool fixture unavailable")
def test_boss_output_matches_legacy_gui_selection(tmp_path):
    actual = extract(DB, UNIT_STATUS)["clan_battle_bosses"]
    with sqlite3.connect(DB) as conn:
        legacy = [
                {"id": int(enemy_id), "name": name_jp, "hp": hp, "aliases": [name_jp]}
            for enemy_id, unit_id, hp, name_jp in conn.execute(
                "SELECT enemy_id, unit_id, hp, name_jp FROM enemy_parameter "
                "WHERE enemy_id LIKE '4019%' ORDER BY enemy_id"
            )
                if hp >= 1_000_000_000
        ]
    months = [int(str(row["id"])[4:6]) for row in legacy]
    current = __import__("datetime").datetime.now().month
    counts = {m: months.count(m) for m in set(months)}
    complete = [m for m, count in counts.items() if count >= 5 and m <= current]
    target = max(complete) if complete else max(months)
    legacy = [row for row in legacy if int(str(row["id"])[4:6]) == target]
    assert actual == legacy
