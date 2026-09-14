from master_data.sheet_sync import upsert_rows


def test_existing_alias_and_metadata_are_preserved():
    current = [{"id": 1, "name": "旧名", "name_en": "Old", "aliases": ["手動alias"], "release": "202608"}]
    source = [{"id": 1, "name": "新名（サマー）", "name_en": "New", "aliases": []}]
    result = upsert_rows(current, source)
    assert result == [{"id": 1, "name": "新名（サマー）", "name_en": "Old", "aliases": ["手動alias"], "release": "202608"}]


def test_new_row_is_added_and_empty_alias_is_derived():
    result = upsert_rows([], [{"id": 2, "name": "スズナ（サマー）"}])
    assert result == [{"id": 2, "name": "スズナ（サマー）", "name_en": "", "aliases": ["スズナ"]}]


def test_new_plain_name_gets_self_alias():
    result = upsert_rows([], [{"id": 3, "name": "ルルィ"}])
    assert result == [{"id": 3, "name": "ルルィ", "name_en": "", "aliases": ["ルルィ"]}]
