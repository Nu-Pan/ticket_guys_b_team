# docs ルーティング

`docs/` は `tgbt` 開発のための詳細ガイド置き場であり、正本仕様の置き場ではない。
ここでは「今ある文書の入口」に徹し、必要な話題ごとに読む先を案内する。

# 最初に見る文書

- 開発環境の作成、`.venv`、依存導入、ツール実行方法を確認したいときは [dev_environment.md](./dev_environment.md)
- Python 実装時の型ヒント、import、docstring、コメント、`pyright` 実行方針を確認したいときは [python.md](./python.md)
- テスト追加・修正、live/stub の使い分け、確認方針を確認したいときは [test_policy.md](./test_policy.md)

# 読み進め方

1. 環境をまだ作っていないなら、先に [dev_environment.md](./dev_environment.md) を読む
2. Python コードを触るなら、続けて [python.md](./python.md) を読む
3. 実装確認やテスト追加を行うなら、最後に [test_policy.md](./test_policy.md) を読む
