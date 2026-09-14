# 作業記録

- 目的: priconner_data_tool のマスターデータ取得・抽出責務を段階移管する
- 完了: fm-relay 運用ルール確認、現行 SQLite 参照箇所特定、初期抽出/更新管理実装、upstream revision読取、GitHub Actions workflow/CLI追加、JSON互換ローダー追加、単体テスト
- 未完了: upstream transport、alias 管理UI/ファイル、旧利用側の段階移行、Sheets→JSON実接続、GitHub実リポジトリ登録
- ボス抽出: 旧GUI条件（4019 prefix、HP 10億以上、UnitStatus既知）を実装し、実DBで40件を旧処理と完全比較。
- 比較結果: 実DBのキャラクターID・名称は旧処理と387/387一致。旧処理互換の`unit_name`を採用。
- Google Sheets: characters 387件、clan_battle_bosses 40件、metadataを投入し、A1:C4を再読込確認。
- 追加alias: 指定Sheetの`キャラ`略称を372件取り込み、ID空欄16件は除外。括弧付き名称の末尾を除去する動的派生ルールを追加。
- alias衝突: 94種類を確認。曖昧aliasを削除・推測解決せず、loaderの`find()`で候補一覧、`get()`で曖昧エラーとする方針へ変更。
- 正式名称: `characters.name` を指定Sheet `キャラ!名称` の和名へ更新。SQLiteの破損した`unit_name_jp`は正とせず、`name_en`は旧英名として分離。
- 名称補正: `characters!A359:C359` の `139101` を `キャル（覇瞳天星）`、alias `キャル` に修正。参照SheetではID空欄行だったため、IDはユーザー指摘の値を使用。
- 英名列: `characters!D1:D388` に `name_en` を追加し、387件をID順で投入。Apps Scriptも4列形式に対応。
- ボス整理: `clan_battle_bosses` を月別に識別できるよう `name_en`、`clan_battle_id`、`release_month` を追加。実DBの40件は2026年1〜8月の各5種。
- 利用側境界: `master_data.loader.MasterData` でID/明示alias参照と未知値エラーを提供。
- 変更ファイル: `master_data/__init__.py`, `master_data/pipeline.py`, `tests/test_pipeline.py`, `README.md`
- テスト: `python -m pytest -q`
- 停止理由: なし
- 次のアクション: CLI実行を確認し、旧GUIのボス選択条件を抽出処理へ移して実DBで全件比較する

## 2026-09-14 追加ループ

- 列順を `id, name, name_en, aliases` に統一し、Apps Script の読取仕様も更新。
- Google Sheets の characters / clan_battle_bosses を再投入し、bosses 40件を復元。
- CSVエクスポート固有の内部行番号列を除外して処理することを確認。
- テスト結果: `python -m pytest -q` → 8 passed。
- 未完了: characters の有効ID欠損15件の確認、boss日本語名対応、GitHub配信設定。
