# テスト方針

- テストを追加・修正するとき
- 実装変更に対する確認方法を決めるとき

# 読まなくてよい時

- 仕様確認だけを行うとき
- コード変更もテスト変更も行わないとき

# 基本

- 実際の運用がデバッグを兼ねる前提で、テストは必要最小限に保つ
- テストには `pytest` を使う
- テスト以外のチェックとして `pyright` を使う
- テストファイルは `tests/` 配下に置く
- 現在の worktree で確認できる既存テスト用ディレクトリは `tests/unit/` のみである
- 個別テストの行数が必要以上に膨らまないように努力する
- そのために、テスト用コンポーネントの共通化や構造化を行ってよい

# live / stub の扱い

`CodexCliMode` には live / stub があるが、単体テスト実行時に live モードを使わない。

- live 実行はトークン消費を伴うため、通常のテスト確認フローへ混ぜない
- live / stub の違いが論点になる場合は、既存実装を根拠に判断する
- stub を使うテストや確認では、既存 repository 状態、既存 `.tgbt/`、stale lock、手動 restore の有無に依存させない

# 実装者向けルール

- 変更内容に対応するテストを追加または更新する
- テスト変更だけで仕様差分を吸収しようとせず、まず仕様と実装のどちらが正なのかを確認する
- この `docs/` 配下の文書と既存テストが矛盾する場合、既存テストを正本扱いし、文書記述だけを根拠に挙動を決めない
- 単体テストでは live モードを使わない
- stub ベースの確認やテストを追加する場合、必要な record や state はテストスコープ内で閉じる
- テスト実行者に、live 実行、手動 snapshot restore、既存 state の掃除を前提条件として要求しない

# 関連コード

- live / stub の実装は `src/agent_wrapper/agent_wrapper.py` と `src/agent_wrapper/codex_wrapper_live.py` を参照する
- `tgbt plan docs` のフローは `src/main.py`、`src/cmd/plan/docs/service.py`、`src/cmd/plan/docs/drafting.py` を参照する
- state の読み書きは `src/state/io.py` と `src/state/path.py` を参照する

# カバレッジ

- カバレッジは以下のように計測できる

```bash
.venv/bin/python -m pytest --cov=...
```

- カバレッジ 90% を目標とする

# 関連文書

- 実装ルールは [python.md](./python.md) を参照する
- 実行環境や依存導入の前提は [dev_environment.md](./dev_environment.md) を参照する
