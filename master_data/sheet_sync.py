"""Pure update rules shared by Sheets synchronization tests and adapters."""

from copy import deepcopy

from .pipeline import derive_alias


def upsert_rows(current: list[dict], source: list[dict]) -> list[dict]:
    """Update names by stable ID, preserve fields, and append new source IDs."""
    result = deepcopy(current)
    by_id = {int(row["id"]): row for row in result}
    for incoming in source:
        row_id = int(incoming["id"])
        if row_id in by_id:
            row = by_id[row_id]
            row["name"] = incoming["name"]
            if "hp" in incoming:
                row["hp"] = incoming["hp"]
            if not row.get("aliases"):
                alias = derive_alias(row["name"]) or row["name"].strip()
                if alias:
                    row["aliases"] = [alias]
        else:
            row = deepcopy(incoming)
            row.setdefault("name_en", "")
            row.setdefault("aliases", [])
            if not row["aliases"]:
                alias = derive_alias(row["name"]) or row["name"].strip()
                if alias:
                    row["aliases"] = [alias]
            result.append(row)
            by_id[row_id] = row
    return sorted(result, key=lambda row: int(row["id"]))
