import csv, json, sqlite3
from pathlib import Path

root = Path(r"D:\git\priconner_data_tool")
db = root / "priconner_data" / "roboninon.db"
with (root / "priconner_data" / "UnitStatus.csv").open(encoding="utf-8-sig", newline="") as f:
    units = {int(r["unit_id"]): r["unit_name"] for r in csv.DictReader(f)}
with sqlite3.connect(db) as c:
    schedule = {month: cb for cb, month in c.execute("select clan_battle_id, release_month from clan_battle_schedule")}
    rows = []
    for enemy_id, unit_id in c.execute("select enemy_id, unit_id from enemy_parameter where enemy_id like '4019%' and hp >= 1000000000 order by enemy_id"):
        if unit_id in units:
            month = int(str(enemy_id)[4:6])
            year = int(str(next(c.execute("select start_time from clan_battle_schedule where clan_battle_id = ?", (schedule.get(month),)), ("",))[0])[:4]) if schedule.get(month) else 0
            rows.append({"id": int(enemy_id), "name_en": units[unit_id], "clan_battle_id": schedule.get(month), "release": year * 100 + month})
print(json.dumps(rows, ensure_ascii=False))
