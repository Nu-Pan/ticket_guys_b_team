# `codex_cli.md`

- `tgbt` から Codex CLI を利用する際の規則について記述している
- `codex` コマンドの呼び出し規約、事前チェック、ファイル閲覧指示、Codex CLI プロファイル設定を扱う

# `dot_tgbt_dir.md`

- `<repo-root>/.tgbt` の扱いについて記述している
- `.tgbt` の作成タイミング、Codex CLI 用 `CODEX_HOME`、git 管理対象の切り分けを扱う

# `instruction_input.md`

- `tgbt` の各サブコマンドで指示文を受け取る方法について記述している
- 標準入力入力、エディタ入力、人間指示ファイルのテンプレートと抽出規則を扱う

# `knowledge_system.md`

- `tgbt` 上で実装するべき AI 用知識システムの仕様について記述している
- 知識ソースファイル、内部状態ファイル、公開・非公開インターフェース、正規化処理を扱う

# `logs.md`

- `tgbt` のログについて記述している
- ログの用途、保存先、Codex CLI 呼び出しログ、`tgbt` コマンド呼び出しログを扱う

# `oracle.md`

- 「`tgbt` を使って任意のリポジトリ `<repo-root>` 上で開発作業を行う」際の `<repo-root>/oracle` について記述している
- `<repo-root>/oracle` の基本方針、狙い、`tgbt` コマンドとの連携、`oracle/tests` を扱う

# `plan_spec.md`

- `tgbt plan ...` サブコマンドによるプランニング処理の正本仕様を記述している
- plan の役割、編集フロー、レビュー観点、保存形式、plan id 指定方法、ログの扱いを記述している

# `structured_prompt.md`

- `tgbt` が AI に渡す指示文を構造化・構築（結合）する方法についての正本仕様を記述している
- プロンプトブロック、Structured Output 用スキーマ、Codex CLI 向けタスクプロンプト、固定プロンプトブロックを扱う

# `tgbt_call_rules.md`

- `tgbt` コマンドの呼び出し規則の正本仕様を記述している
- コマンドの並列実行、stack 的再入処理、例外許可、ファイルロックによる排他制御を扱う
