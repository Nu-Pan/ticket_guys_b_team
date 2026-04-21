# docs ルーティング

`docs/` は `tgbt` 開発のための詳細ガイド置き場であり、正本仕様の置き場ではない。
この文書は、現在の `docs/` にある文書の入口だけを案内する。

## `docs/ROUTING.md`

`docs/` 全体の入口である。どの文書から読むべきかを判断したいときに読む。

## `docs/dev_environment.md`

[開発環境](./dev_environment.md)。`.venv` の作成、依存導入、Python 実行環境、ツール実行の前提を確認したいときに読む。

## `docs/python.md`

[Python 実装ルール](./python.md)。型ヒント、import、docstring、コメント、依存追加、`pyright` 実行方針を確認したいときに読む。

## `docs/test_policy.md`

[テスト方針](./test_policy.md)。テスト追加・修正、live/stub の扱い、実装変更に対する確認方針を確認したいときに読む。

## 下位ディレクトリ

現在の `docs/` 直下に、追加の `ROUTING.md` を持つ下位ディレクトリは存在しない。

# 典型的な読み順

1. 開発環境が未作成なら、まず [開発環境](./dev_environment.md) を読む
2. Python コードを編集するなら、次に [Python 実装ルール](./python.md) を読む
3. 実装確認やテスト追加を行うなら、最後に [テスト方針](./test_policy.md) を読む
