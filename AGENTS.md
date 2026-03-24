# 前提

- このリポジトリでは `ticket_guys_b_team` を開発する
- 人間向けの説明は `README.md` に書いてある
- プロダクト仕様の正本は `doc/spec/*.md` にある
- この `AGENTS.md` は、AI エージェントが最初に読むブートストラップ兼ルータである
- 詳細ルールは `doc/task/*.md` と `doc/tech/*.md` に分離している
- 「`ticket_guys_b_team` が実現する AI エージェントのワークフロー」と「`ticket_guys_b_team` 自体の開発中に遵守するべき AI エージェントの行動原則」は異なる

# 絶対ルール

## OpenAI Docs

Always use the OpenAI developer documentation MCP server if you need to work with the OpenAI API, ChatGPT Apps SDK, Codex, or other OpenAI developer docs, without me having to explicitly ask.

## 禁止事項

- `AGENTS.md` を AI エージェントが編集すること
- `doc/**/*.md` を AI エージェントが編集すること
- 未承認の仕様から直接実装を始めること
- 必要な文書を読まずに、推測だけで仕様判断を行うこと

# 最初にやること

- まず、今回の依頼が何の作業かを判定すること
    - 調査
    - 実装
    - テスト修正・追加
    - 開発環境整備
- 以後は、その作業に必要な文書だけを読むこと
- `doc/spec/spec_overview.md` は、プロダクト仕様を読み始める入口として扱うこと

# 作業タイプごとの必読文書

## 1. 調査

必読:

- `doc/task/research.md`

条件付き:

- 仕様確認が必要なら `doc/spec/spec_overview.md`
- その後、必要な仕様文書だけを追加で読む
- コード実行やテスト実行を伴う調査に進む場合だけ `doc/tech/python.md` と `doc/tech/test_policy.md`

通常は不要:

- `doc/tech/dev_environment.md`
- 実装向けの詳細規約一式

## 2. 実装

必読:

- `doc/task/implementation.md`
- `doc/spec/spec_overview.md`

条件付き:

- 変更対象に関係する仕様文書のみ
- Python コードを編集するなら `doc/tech/python.md`
- テストを追加・修正するなら `doc/tech/test_policy.md`
- 環境構築や依存追加が必要なら `doc/tech/dev_environment.md`

## 3. テスト修正・追加

必読:

- `doc/tech/test_policy.md`

条件付き:

- 対象機能の仕様確認に必要な `doc/spec/*.md`
- Python テストを編集するなら `doc/tech/python.md`
- 環境依存の操作が必要なら `doc/tech/dev_environment.md`

## 4. 開発環境整備

必読:

- `doc/tech/dev_environment.md`

条件付き:

- Python パッケージやコード変更を伴うなら `doc/tech/python.md`
- テスト実行まで行うなら `doc/tech/test_policy.md`
- 作業対象の意味を確認する必要がある場合のみ `doc/spec/spec_overview.md`

# 仕様文書の選び方

`doc/spec/spec_overview.md` を読んだ後は、必要なものだけ読むこと。

- 背景・設計思想・MVP の価値判断が必要なら `doc/spec/product_vision.md`
- 状態遷移や `settled` / active の意味が必要なら `doc/spec/state_machine.md`
- 保存先、front matter、命名規則、採番規則が必要なら `doc/spec/file_format.md`
- CLI の入出力、失敗条件、コマンド責務が必要なら `doc/spec/cli_contract.md`
- `codex exec` の live / stub、strict replay、request/result モデルが必要なら `doc/spec/codex_cli_wrapper.md`

# 作業完了時の最低要件

- 実施したことを報告すること
- 完了と判断した根拠を報告すること
- 未解決事項、制約、未知の失敗があれば必ず報告すること
- 実装と `doc/spec/*.md` の間に差異を見つけた場合は、その内容を報告すること
