# この文書を読むべき時

- 開発環境をセットアップするとき
- `.venv` の作成、依存追加、ツール実行方法を確認するとき

# 読まなくてよい時

- 調査だけで終わるとき
- 既存環境の上でコードを読むだけのとき

# 基本環境

- WSL2 Ubuntu 24.04 on Windows 11
- vscode (with Remote Development Extension)
- `ticket_guys_b_team.code-workspace` を vscode で開いた環境
- Codex CLI が利用可能

# ファイルエンコード

- 原則として UTF-8 BOM なしで統一する
- ツール都合がある場合のみ例外を許容する

# Python 実行環境

- Python 3.12.3 を前提とする
- システムワイドの `python3` を直接使わない
- Python 仮想環境として `.venv` を使う
- Python インタプリタは `.venv/bin/python` を使う
- pip は `.venv/bin/python -m pip` を使う

# 仮想環境の管理

## `.venv` の新規作成

```bash
/usr/bin/python3 -m venv .venv
```

## `.venv` へのパッケージインストール

権限昇格付きでの実行が必要なら、ユーザーに依頼すること。

```bash
./.venv/bin/python -m pip install -e ."[test]"
```

## `.venv` への新規パッケージ追加

- `pyproject.toml` に依存関係を追記する
- その後、上記のインストール手順を実行する

# 注意事項

- 依存追加を、場当たり的なワークアラウンドで済ませない
- パッケージ導入ルールの詳細は `docs/tech/python.md` も参照する
