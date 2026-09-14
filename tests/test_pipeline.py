import sqlite3
from pathlib import Path

import pytest

from master_data.pipeline import NO_CHANGE, SchemaError, derive_alias, extract, generate, generate_from_upstream, read_upstream_revision
from master_data.loader import MasterData, MasterDataError


def db(tmp_path: Path) -> Path:
    p = tmp_path / "input.db"
    c = sqlite3.connect(p)
    c.execute("create table unit_data (unit_id integer, unit_name text, unit_name_jp text)")
    c.execute("create table enemy_parameter (enemy_id integer, unit_id integer, name text, name_jp text, hp integer)")
    c.executemany("insert into unit_data values (?,?,?)", [(100101, "Hiyori", "ヒヨリ"), (100201, "Yui", "ユイ")])
    c.executemany("insert into enemy_parameter values (?,?,?,?,?)", [(40190101, 300001, "Boss", "ボス", 2000000000)])
    c.commit(); c.close()
    return p


def test_extract_and_deterministic_revision(tmp_path):
    p = db(tmp_path); out = tmp_path / "out"
    assert extract(p)["characters"][0]["name_en"] == "Hiyori"
    row = extract(p)["characters"][0]
    assert row["aliases"] == [row["name"]]
    assert generate(p, out, "abc", "2026-01-01T00:00:00+00:00") == "UPDATED"
    first = (out / "master_data.json").read_bytes()
    assert generate(p, out, "abc", "2099-01-01T00:00:00+00:00") == NO_CHANGE
    assert (out / "master_data.json").read_bytes() == first


def test_bosses_apply_legacy_gui_filters(tmp_path):
    p = db(tmp_path)
    c = sqlite3.connect(p)
    c.execute("insert into enemy_parameter values (40190102,300001,'small','small',1000000)")
    c.close()
    status = tmp_path / "UnitStatus.csv"
    status.write_text("unit_id,unit_name_jp,unit_name\n300001,ボス正式名,Boss Unit\n", encoding="utf-8")
    assert extract(p, status)["clan_battle_bosses"] == [{"id": 40190101, "name": "ボス", "aliases": ["ボス"]}]


def test_schema_change_fails_closed(tmp_path):
    p = tmp_path / "bad.db"; c = sqlite3.connect(p)
    c.execute("create table unit_data (unit_id integer, unit_name text)")
    c.execute("create table enemy_parameter (enemy_id integer, unit_id integer, name text, name_jp text)"); c.commit(); c.close()
    with pytest.raises(SchemaError): extract(p)


def test_upstream_revision_reads_truth_version_and_commit(tmp_path):
    import subprocess
    source = tmp_path / "upstream"; source.mkdir()
    (source / "!TruthVersion.txt").write_text("10069600\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(source), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(source), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(source), "config", "user.name", "test"], check=True)
    subprocess.run(["git", "-C", str(source), "add", "."], check=True)
    subprocess.run(["git", "-C", str(source), "commit", "-qm", "fixture"], check=True)
    revision = read_upstream_revision(source)
    assert revision["truth_version"] == "10069600"
    assert len(revision["source_commit"]) == 40


def test_generate_from_upstream_uses_revision_gate(tmp_path):
    import subprocess
    source = tmp_path / "upstream"; source.mkdir()
    (source / "!TruthVersion.txt").write_text("1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(source), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(source), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(source), "config", "user.name", "test"], check=True)
    subprocess.run(["git", "-C", str(source), "add", "."], check=True)
    subprocess.run(["git", "-C", str(source), "commit", "-qm", "fixture"], check=True)
    input_db = db(tmp_path)
    result = generate_from_upstream(source, input_db, tmp_path / "out", "2026-01-01T00:00:00+00:00")
    assert result == "UPDATED"
    assert generate_from_upstream(source, input_db, tmp_path / "out", "2099-01-01T00:00:00+00:00") == NO_CHANGE


def test_consumer_loader_resolves_ids_and_explicit_aliases():
    data = {"schema_version": "1", "source_commit": "a" * 40,
            "characters": [{"id": 1, "name": "One", "aliases": ["one"]}],
            "clan_battle_bosses": []}
    master = MasterData(data)
    assert master.get("characters", 1)["name"] == "One"
    assert master.get("characters", "one")["id"] == 1
    with pytest.raises(KeyError): master.get("characters", "unknown")
    ambiguous = MasterData({**data, "characters": [{"id": 1, "name": "A", "aliases": ["x"]}, {"id": 2, "name": "B", "aliases": ["x"]}]})
    assert [r["id"] for r in ambiguous.find("characters", "x")] == [1, 2]
    with pytest.raises(MasterDataError): ambiguous.get("characters", "x")


def test_dynamic_alias_only_removes_trailing_variant_parentheses():
    assert derive_alias("スズナ（サマー）") == "スズナ"
    assert derive_alias("Suzuna (Summer)") == "Suzuna"
    assert derive_alias("スズナ") is None
    assert derive_alias("名前（途中）追加") is None


def test_known_mojibake_character_name_is_repaired(tmp_path):
    p = tmp_path / "tia.db"
    c = sqlite3.connect(p)
    c.execute("create table unit_data (unit_id integer, unit_name text, unit_name_jp text)")
    c.execute("create table enemy_parameter (enemy_id integer, unit_id integer, name text, name_jp text, hp integer)")
    c.execute("insert into unit_data values (140301, 'Tia', '��')")
    c.commit(); c.close()
    row = next(x for x in extract(p)["characters"] if x["id"] == 140301)
    assert row["name"] == "ティア"
    assert row["name_en"] == "Tia"
