# 無料実行基盤案

## 推奨構成

| パート | 実行場所 | 理由 |
|---|---|---|
| データ読み込み | GitHub Actions | 公開リポジトリなら標準runnerが無料。upstreamのrevision確認と取得に向く |
| Google Sheets更新 | Google Apps Script または GitHub Actions | Sheets側の編集を正とするならApps Script。生成データを正とするならActionsからSheets API |
| JSON生成・配信 | GitHub Actions + GitHub Pages/Raw | 生成・検証・commit・配信を同じrevision単位で管理できる |

## 第一候補

1. GitHub Actionsがupstreamのcommit SHAを取得
2. SHAが前回と同じなら終了 (`NO_CHANGE`)
3. 変更時だけDB/SQLを取得し、必要データを抽出
4. Google Sheetsを更新（運用上Sheetsを編集面にする場合のみ）
5. JSON/CSVを生成し、テスト後にcommit
6. GitHub PagesまたはRaw URLで配布

## 判断

- Raspberry Piは既存botの実行環境として温存する
- GitHub Actionsを主実行基盤にする
- Google Sheetsは編集・確認面に限定し、配布元はGitHub JSONにする
- aliasはSheetsの手動管理領域として上流データと分離する
- GitHub Actionsの認証情報はSecretsに置き、リポジトリへ保存しない

## 無料枠上の注意

- GitHub Actionsは公開リポジトリの標準runner利用が無料
- private repositoryではアカウントの無料分を消費するため、公開可否を先に決める
- Apps Scriptはgmail.comのconsumer accountでtrigger総実行90分/日、1回6分などの制限がある
- Sheets APIはユーザー単位で読み書き各60 requests/minute。まとめて更新する

## 未解決の外部条件

- `priconner51bk-prog` 配下の配信先リポジトリが未確認
- 公開リポジトリにするかprivateにするか未決定
- Google Sheetsを編集面にするか、生成結果の閲覧面にするか未決定
