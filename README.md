# priconner_master_data

`priconner_data_tool` の SQLite (`unit_data`, `enemy_parameter`) から、共有参照用の characters / clan_battle_bosses を決定論的に生成する基盤です。

現段階では取得 transport は既存処理を温存し、`generate()` に取得済み SQLite と upstream commit SHA を渡します。revision が同じ場合は重い抽出・生成を行わず `NO_CHANGE` を返します。

## 定期更新

GitHub Actions は使用せず、`priconner_clan_battle_task_scheduler` の
`projects.json` に登録した `scripts/update_master_data.py` から更新します。
このジョブは upstream checkout、source DB の取得、`dist/` の生成、pytest、
Google Sheets 同期、変更がある場合のコミット・push を順に実行します。

Google Sheets 同期を有効にする場合は、scheduler を実行する Windows ユーザーの
環境変数 `APPS_SCRIPT_WEBHOOK_URL` と `APPS_SCRIPT_WEBHOOK_TOKEN` を設定します。
未設定の場合は同期をスキップします。

`apps_script/Code.gs` は、Google Sheetsの3タブを検証し、GitHub Contents APIへJSONを同期します。`GITHUB_REPO`、`GITHUB_TOKEN`、任意の`GITHUB_PATH`はApps ScriptのScript Propertiesに設定します。aliasは複数IDに一致し得るため、利用側は候補一覧を表示し、1件に暗黙解決しません。
