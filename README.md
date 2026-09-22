# priconner_master_data

GitHub の `esterTion/redive_master_db_diff` にあるハッシュ化SQLから必要なSQLiteを再構成し、共有参照用の characters / clan_battle_bosses を決定論的に生成する基盤です。

`scripts/update_master_data.py` は実行時に外部DBをダウンロードしません。GitHubのSQLを検証して `.input/master_data_source.db` を生成し、revision が同じ場合は重い抽出・生成を行わず `NO_CHANGE` を返します。SQLの列構成が変わった場合は停止して誤データの公開を防ぎます。

## 定期更新

GitHub Actions は使用せず、`priconner_clan_battle_task_scheduler` の
`projects.json` に登録した `scripts/update_master_data.py` から更新します。
このジョブは upstream checkout、source DB の取得、pytest、`dist/` の生成、
Google Sheets 同期、変更がある場合のコミット・push を順に実行します。
pytest が失敗しても、次回実行を妨げる `dist/` の中途半端な変更を残しません。

更新ジョブは毎月22〜30日のクラバト期間中、登録日の12:20・12:40・13:00
（日本時間）の3回だけ実行されます。GitHub Actions の workflow は削除済みです。

GitHub の `origin` は HTTPS ではなく、SSH
(`git@github-priconner51bk-prog:priconner51bk-prog/priconner_master_data.git`) を使用します。

Google Sheets 同期を有効にする場合は、scheduler を実行する Windows ユーザーの
環境変数 `APPS_SCRIPT_WEBHOOK_URL` と `APPS_SCRIPT_WEBHOOK_TOKEN` を設定します。
未設定の場合は同期をスキップします。

更新前に `dist/` に未コミット変更がある場合は、既存データの上書きや誤った
自動コミットを避けるため、更新ジョブは停止します。

`apps_script/Code.gs` は、Google Sheetsの3タブを検証し、GitHub Contents APIへJSONを同期します。`GITHUB_REPO`、`GITHUB_TOKEN`、任意の`GITHUB_PATH`はApps ScriptのScript Propertiesに設定します。aliasは複数IDに一致し得るため、利用側は候補一覧を表示し、1件に暗黙解決しません。
`clan_battle_bosses` はGitHubからの同期時に必ず5件へ差し替えます。`name_en`、`hp`、`release` 列が無い既存シートでも自動追加して値を反映します。既存IDのaliasは保持します。
