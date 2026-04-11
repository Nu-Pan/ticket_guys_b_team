# 前提

- このリポジトリでは `ticket_guys_b_team` を開発する
- 人間向けの説明は `README.md` に書いてある
- プロダクト仕様の正本は `docs/spec/*.md` にある
- この `AGENTS.md` は、AI エージェントが最初に読むブートストラップ兼ルータである
- 詳細ルールは `docs/task/*.md` と `docs/tech/*.md` に分離している
- `tgbt` が Codex CLI を worker として起動する際の基本指示の正本は `docs/spec/codex_worker_instructions.md` であり、runtime では `.tgbt/instructions.md` が生成される
- `tgbt` worker 実行では skills と sub agent を使用しない
- 「`ticket_guys_b_team` が実現する AI エージェントのワークフロー」と「`ticket_guys_b_team` 自体の開発中に遵守するべき AI エージェントの行動原則」は異なる

# 絶対ルール

## 禁止事項

- 明示的な許可指示が無い状況で `AGENTS.md` を AI エージェントが編集すること
- 明示的な許可指示が無い状況で `docs/**/*.md` を AI エージェントが編集すること
- 未承認の仕様から直接実装を始めること
- 必要な文書を読まずに、推測だけで仕様判断を行うこと

# 最初にやること

- まず、今回の依頼が何の作業かを判定すること
    - 調査
    - 実装
    - テスト修正・追加
    - 開発環境整備
    - Codex 自己改善
- 以後は、その作業に必要な文書だけを読むこと
- `docs/spec/spec_overview.md` は、プロダクト仕様を読み始める入口として扱うこと

# 作業タイプごとの必読文書

## 1. 調査

必読:

- `docs/task/research.md`

条件付き:

- 仕様確認が必要なら `docs/spec/spec_overview.md`
- その後、必要な仕様文書だけを追加で読む
- コード実行やテスト実行を伴う調査に進む場合だけ `docs/tech/python.md` と `docs/tech/test_policy.md`

通常は不要:

- `docs/tech/dev_environment.md`
- 実装向けの詳細規約一式

## 2. 実装

必読:

- `docs/task/implementation.md`
- `docs/spec/spec_overview.md`

条件付き:

- 変更対象に関係する仕様文書のみ
- Python コードを編集するなら `docs/tech/python.md`
- テストを追加・修正するなら `docs/tech/test_policy.md`
- 環境構築や依存追加が必要なら `docs/tech/dev_environment.md`

## 3. テスト修正・追加

必読:

- `docs/tech/test_policy.md`

条件付き:

- 対象機能の仕様確認に必要な `docs/spec/*.md`
- Python テストを編集するなら `docs/tech/python.md`
- 環境依存の操作が必要なら `docs/tech/dev_environment.md`

## 4. 開発環境整備

必読:

- `docs/tech/dev_environment.md`

条件付き:

- Python パッケージやコード変更を伴うなら `docs/tech/python.md`
- テスト実行まで行うなら `docs/tech/test_policy.md`
- 作業対象の意味を確認する必要がある場合のみ `docs/spec/spec_overview.md`

## 5. Codex 自己改善

必読:

- `docs/spec/codex_worker_instructions.md`

条件付き:

- runtime 生成物の現状確認が必要なら `<repo-root>/.tgbt/.codex/config.toml`
- runtime 指示の現状確認が必要なら `<repo-root>/.tgbt/instructions.md`
- 変更対象の `.tgbt/.codex/**/*`

通常は不要:

- `docs/spec/*.md`
- `docs/tech/*.md`
- `ticket_guys_b_team` 本体実装向けの文書一式

# 仕様文書の選び方

`docs/spec/spec_overview.md` を読んだ後は、必要なものだけ読むこと。

- 背景・設計思想・MVP の価値判断が必要なら `docs/spec/product_vision.md`
- 状態遷移や `settled` / active の意味が必要なら `docs/spec/state_machine.md`
- 保存先、front matter、命名規則、採番規則が必要なら `docs/spec/file_format.md`
- front matter の安全な書き換え、atomic write-replace、複数ファイル mutation の扱い、失敗後の restore 前提契約が必要なら `docs/spec/state_write_protocol.md`
- CLI の入出力、失敗条件、コマンド責務が必要なら `docs/spec/cli_contract.md`
- `codex exec` の live / stub、strict replay、request/result モデルが必要なら `docs/spec/codex_cli_wrapper.md`
- worker 用の repo-local runtime と `.tgbt/instructions.md` の正本を確認したいなら `docs/spec/codex_worker_instructions.md`

# 作業完了時の最低要件

- 実施したことを報告すること
- 完了と判断した根拠を報告すること
- 未解決事項、制約、未知の失敗があれば必ず報告すること
- 実装と `docs/spec/*.md` の間に差異を見つけた場合は、その内容を報告すること
