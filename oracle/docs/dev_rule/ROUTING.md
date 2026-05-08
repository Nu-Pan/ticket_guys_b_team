# `skills`

- `<tgbt-root>/.agents/skills` 配下に実装される「リポジトリローカルなスキル」についての原則・規則を記述している
- スキル個別の正本仕様断片も記述している

# `ai_docs.md`

- AI によるドキュメンテーションについての規則を記述している
- 要するに、AI による中間ドキュメンテーションを禁止しているのだが、その理由を記述している

# `environment.md`

- `tgbt` の開発環境、文字エンコード、Python 実行環境について記述
- `<tgbt-root>/.venv` の作成・利用・依存追加の手順と関連文書を記述

# `fanout_file_codex.md`

- `tgbt` 上での Codex CLI 呼び出しをファイル単位呼び出しに機械的に展開する補助スクリプトの正本仕様を記述
- 対象ファイル列挙、プロンプト入力、実行ログ、派生ヘルパースクリプトについて記述

# `oracle.md`

- `<tgbt-root>` 上で Codex CLI を用いて `tgbt` 自体の開発を行う際の `<tgbt-root>/oracle` の取り扱いについて記述

# `oracle_docs_routing_policy.md`

- `<tgbt-root>/oracle/docs` 配下ドキュメントの `ROUTING.md` によるルーティングについて記述

# `path_notation_rule.md`

- ファイル・ディレクトリのパスの表記方法の正本ルールを記述
- e.g. `<tgbt-root>`, `<repo-root>` の違い

# `python_coding.md`

- Python コードを編集・確認するときの実装規約を記述
- 型ヒント、import、docstring、コメント、依存管理、型チェック、関数分割、非公開識別子について記述

# `test_policy.md`

- `tgbt` 開発時のテスト方針として、テストを原則用意しない理由を記述
