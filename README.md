# priconner_master_data

`priconner_data_tool` の SQLite (`unit_data`, `enemy_parameter`) から、共有参照用の characters / clan_battle_bosses を決定論的に生成する基盤です。

現段階では取得 transport は既存処理を温存し、`generate()` に取得済み SQLite と upstream commit SHA を渡します。revision が同じ場合は重い抽出・生成を行わず `NO_CHANGE` を返します。

## GitHub Actions

`.github/workflows/update-master-data.yml` が upstream checkout の revision を確認し、変更時だけ source DB を取得して `dist/` の JSON/CSV を更新します。Google Sheets 同期は配信生成とは独立した処理として追加します。

`apps_script/Code.gs` は、Google Sheetsの3タブを検証し、GitHub Contents APIへJSONを同期します。`GITHUB_REPO`、`GITHUB_TOKEN`、任意の`GITHUB_PATH`はApps ScriptのScript Propertiesに設定します。aliasは複数IDに一致し得るため、利用側は候補一覧を表示し、1件に暗黙解決しません。
