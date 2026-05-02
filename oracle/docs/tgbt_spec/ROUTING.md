# `logs.md`

- `tgbt` のログについて記述している
- ログが何を指しているのか、どうやって・どこに永続化するのか

# `codex_cli.md`

- `tgbt` から Codex CLI を利用する際の規則について記述している
- `codex` コマンドの呼び出し規約に加えて、 Codex CLI の挙動の設定方法についても記述している

# `concurrency.md`

- `tgbt` 上における並列処理・並行処理の原則について記述している

# `dot_tgbt_dir.md`

- `<repo-root>/.tgbt` の扱いについて記述している

# `instruction_input.md`

- `tgbt` の各サブコマンドで指示文を受け取る方法について記述している

# `knowledge_system.md`

- `tgbt` 上で実装するべき AI 用知識システムの仕様について記述している
- システムの全体像、永続化の仕様、インターフェース仕様、…

# `oracle.md`

- 「`tgbt` を使って任意のリポジトリ `<repo-root>` 上で開発作業を行う」際の `<repo-root>/oracle` について記述している
- 基本的な考え方、狙い、 `tgbt` コマンドとの連携、テスト

# `plan_spec.md`

- `tgbt plan ...` サブコマンドによるプランニング処理の正本仕様を記述している
- 処理そのもの以外にも plan ファイルなどの関連物の正本仕様も記述している

# `structured_prompt.md`

- `tgbt` が AI に渡す指示文を構造化・構築（結合）する方法についての正本仕様を記述している
