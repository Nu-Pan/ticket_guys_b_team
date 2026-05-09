# `skills`

- `<tgbt-root>/.agents/skills` 配下に実装される「リポジトリローカルなスキル」についての原則・規則を記述している
- スキル個別の正本仕様断片も記述している

# `ai_docs.md`

- AI による編集可能な中間ドキュメントを置かない規則を記述している
- `<tgbt-root>/oracle` を正本とし、中間ドキュメントのメンテナンスを避ける理由を記述している

# `environment.md`

- `tgbt` の開発環境、文字エンコード、Python 実行環境について記述している
- `<tgbt-root>/.venv` の作成・利用・依存追加の手順と関連文書を記述している

# `fanout_file_codex.md`

- `tgbt` 上での Codex CLI 呼び出しをファイル単位呼び出しに機械的に展開する補助スクリプトの正本仕様を記述している
- 対象列挙、プロンプト入力、個別実行、ログ、git 操作、派生ヘルパースクリプトについて記述している

# `oracle.md`

- `<tgbt-root>` 上で Codex CLI を用いて `tgbt` 自体の開発を行う際の `<tgbt-root>/oracle` の取り扱いについて記述

# `oracle_docs_routing_policy.md`

- `<tgbt-root>/oracle/docs` 配下の `ROUTING.md` による目次・ルーティング規則を記述している
- `ROUTING.md` の配置、役割、AI 編集可能な例外、機械チェック向けフォーマットを記述している

# `path_notation_rule.md`

- ファイル・ディレクトリのパス表記に関する正本ルールを記述している
- `<tgbt-root>`、`<repo-root>`、`CODEX_HOME`、`HOME`、絶対パスの使い分けを記述している

# `python_coding.md`

- Python コードを編集・確認するときの実装規約を記述
- 型ヒント、import、docstring、コメント、依存管理、型チェック、関数分割、非公開識別子について記述

# `test_policy.md`

- `tgbt` 開発時のテスト方針として、テストを原則用意しない理由を記述している
- 実運用をデバッグと兼ねる前提や、Codex CLI 呼び出しのテストが難しい事情を記述している
