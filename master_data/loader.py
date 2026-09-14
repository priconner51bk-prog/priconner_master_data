from __future__ import annotations

import json
from pathlib import Path


class MasterDataError(RuntimeError):
    pass


class MasterData:
    """Read-only consumer API for generated master_data.json."""

    def __init__(self, payload: dict):
        self.schema_version = payload.get("schema_version")
        self.source_commit = payload.get("source_commit")
        if not self.schema_version or not self.source_commit:
            raise MasterDataError("master data metadata is incomplete")
        self._tables = {}
        for kind in ("characters", "clan_battle_bosses"):
            rows = payload.get(kind)
            if not isinstance(rows, list):
                raise MasterDataError(f"missing table: {kind}")
            by_id = {int(row["id"]): row for row in rows}
            if len(by_id) != len(rows):
                raise MasterDataError(f"duplicate IDs: {kind}")
            aliases = {}
            for row in rows:
                for alias in row.get("aliases", []):
                    aliases.setdefault(alias, []).append(row["id"])
            self._tables[kind] = (by_id, aliases)

    @classmethod
    def from_json(cls, path: Path) -> "MasterData":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def get(self, kind: str, identifier: int | str) -> dict:
        if kind not in self._tables:
            raise MasterDataError(f"unknown table: {kind}")
        by_id, aliases = self._tables[kind]
        try:
            row = by_id.get(int(identifier))
        except (TypeError, ValueError):
            candidates = aliases.get(str(identifier), [])
            if len(candidates) > 1:
                raise MasterDataError(f"ambiguous alias: {kind}/{identifier}: {candidates}")
            row = by_id.get(candidates[0] if candidates else -1)
        if row is None:
            raise KeyError(f"{kind}: {identifier}")
        return dict(row)

    def find(self, kind: str, alias: str) -> list[dict]:
        """Return all rows for an alias; never silently chooses among variants."""
        if kind not in self._tables:
            raise MasterDataError(f"unknown table: {kind}")
        by_id, aliases = self._tables[kind]
        return [dict(by_id[i]) for i in aliases.get(str(alias), [])]
