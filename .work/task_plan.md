# priconner_master_data タスク計画

## 優先順位

### P0: 基盤を検証可能にする

- [~] P0-1 upstream の実データ取得経路を `priconner_master_data` に移管する（checkout revision境界を実装。取得transportは未完）
  - 入力: `esterTion/redive_master_db_diff`
  - 条件: commit SHA を先に確認し、同一SHAなら `NO_CHANGE`
  - 既存の `priconner_data_tool` の取得処理は削除しない
- [ ] P0-2 upstream revision の保存形式を確定する
  - `schema_version`, `source`, `source_commit`, `generated_at`
- [ ] P0-3 実DBを fixture として固定する
  - 取得元revisionと入力ファイルのハッシュを記録
- [ ] P0-4 生成物を atomic に切り替える
  - 一時ファイル生成後に rename
  - 途中状態を配布対象にしない

### P1: 初期データを完成させる

- [x] P1-1 characters の旧処理出力を全件保存する
  - 現行基準: `unit_data`, `unit_id < 190000`, ID昇順
- [x] P1-2 clan battle bosses の旧処理条件を実装し、実DB出力40件を生成する
  - 現行基準: `enemy_parameter`, `enemy_id`、既知unit、HP条件等を明示
- [x] P1-3 新旧キャラクター出力を機械比較する（ID 387/387、名称 387/387一致）
- [x] P1-4 新旧クラバトボス出力を機械比較する（実DBで完全一致）
- [ ] P1-5 ID重複、名称欠損、不正ID、alias衝突を fail-closed で検証する
- [ ] P1-6 同一入力から同一データ出力になることを検証する

### P2: Google Sheets を入力・確認面として整備する

- [x] P2-1 作成済みSheetに実データを投入する（characters 387件、clan_battle_bosses 40件、metadata）
  - `characters`: `id`, `name`, `aliases`
  - `clan_battle_bosses`: `id`, `name`, `aliases`
  - `metadata`: revision情報
- [x] P2-5 `characters.name_en` を追加し、旧互換英名をID対応で投入する
- [x] P2-6 クラバトボスに月・クラバトIDを追加し、月別5種で識別可能にする
- [x] P2-7 全データ表の列順を `id, name, name_en, aliases` に統一する
- [x] P2-2 aliasを上流由来データと分離して管理する（Sheets直接編集 + 動的派生処理）
- [x] P2-3 Google Sheetsの編集内容をJSON生成入力へ反映する方針を決める（Apps ScriptからGitHub JSONへ同期）
- [x] P2-4 文字コード、空欄、重複、ID型を検証する（Apps Script側に実装）

### P3: GitHub配信を構築する

- [ ] P3-1 GitHub接続を確認する
  - 現在 `priconner51bk-prog` のリポジトリ一覧は空
- [ ] P3-2 配信先リポジトリとブランチを確定する
- [x] P3-3 JSON/CSVを生成するCIまたは更新スクリプトを追加する（workflow/CLI追加）
- [x] P3-4 revision変更時だけ生成・commitする
- [ ] P3-5 配布URL、バージョン、schema versionを公開する
- [ ] P3-6 認証情報をリポジトリへ保存しない

実行場所の推奨案は `.work/deployment_plan.md` に記録した。第一候補は GitHub Actions + GitHub Pages/Raw、Raspberry Piは既存bot用に温存する。

### P4: 利用側を段階移行する

- [ ] P4-1 `priconner_data_tool` の利用箇所を一覧化する
- [x] P4-2 新マスターを読む互換ローダーを追加する（`master_data.loader.MasterData`）
- [ ] P4-3 まず読み取り専用の比較モードで運用する
- [ ] P4-4 各BOT、TL関連ツール、Explorerを個別に移行する
- [ ] P4-5 旧DB参照と新マスターの一致を確認する
- [ ] P4-6 全利用側の移行完了後に旧取得処理を整理する

### P5: 運用化

- [ ] P5-1 定期更新ジョブを追加する
- [ ] P5-2 更新失敗・schema変更・欠損時の通知を追加する
- [ ] P5-3 更新履歴と生成ログを保存する
- [ ] P5-4 ロールバック可能なrevision管理を追加する
- [ ] P5-5 外部公開前のレビューと手動確認を定義する

## 推奨実行順

```text
P0-1 → P0-2 → P0-3 → P0-4
  → P1-1/P1-2 → P1-3/P1-4 → P1-5/P1-6
  → P2-1/P2-2 → P3-1/P3-2 → P3-3/P3-4
  → P4 → P5
```

## 現在の次アクション

P0-1: upstreamの取得transportを実装し、既存SQLite入力との変換境界を完成させる。
