# Source SQL table mapping

`redive_master_db_diff` は、ゲーム更新後にテーブル名・列名がハッシュ化されることがあります。
ハッシュ名を固定値だけで参照せず、次の手順で再特定します。

## 1. 基準スキーマを取得

`roboninon.db` を解析用に取得し、対象テーブルの列順・型・主キーを確認します。

```python
import sqlite3

with sqlite3.connect("roboninon.db") as db:
    for table in ("unit_data", "enemy_parameter"):
        print(table)
        print(db.execute(f"PRAGMA table_info({table})").fetchall())
```

`roboninon.db` は過去の列対応を確認するための開発時資料であり、実行時のデータ供給元ではありません。実行時はGitHub checkout内の対応SQLを `master_data.source_sql.build_database()` が一時SQLiteへ正規化します。

## 2. SQL候補を絞る

参照元リポジトリを shallow clone し、各SQLファイルについて次を集計します。

- `CREATE TABLE` の列数
- `INSERT` 行数
- 主キー候補の値
- 既知の値（例: キャラID `100101`、ボスID `401908408`、名前 `ヒヨリ`）

```powershell
rg -l "100101|ヒヨリ|401908408|メデューサ" . --glob "*.sql"
```

候補テーブルの列数と行数が、基準DBの対象テーブルと一致することを確認します。

## 3. 列位置を照合

候補SQLをSQLiteに一時投入し、基準DBと同じ主キーの行を比較します。
値の一致率が高い列を対応列として採用します。名前だけで決めず、次を複数確認します。

- 主キー
- キャラ名・ボス名
- HP
- ID参照列
- 日付・数値列

## 4. 採用条件

次をすべて満たした候補だけを生成処理に採用します。

- 主キーの重複がない
- 既知IDの値が一致する
- 名前列・HP列が一致する
- 対象行数が大きく乖離しない
- `pytest` と生成結果の件数確認に通る

一致しない場合は、ハッシュ名が変わったと判断して処理を止めます。名前検索だけで自動採用しません。

## 現在確認済みの対応

- `unit_data`: `v1_ed1b52317ac09b3d790c8feebcfb4fb224b0a1cf16034f167e128f147a09da36.sql`
- `enemy_parameter`: `v1_7ce15cd873f0e35053e2a1c15111fa91cec7710d5d3ab887d94179e883f46cea.sql`
- `clan_battle_schedule`: `v1_74bde0aea50434815d2e25b3a60c6596637b9692ef1fabf603685065610b9f98.sql`

これらの固定値とアンカーIDは `master_data/source_sql.py` で検証します。将来の更新で列位置が変わった場合は例外で停止し、対応表を更新してから再開します。
