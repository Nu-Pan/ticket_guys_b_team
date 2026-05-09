# `fixed_prompt.md`

- Codex CLI への依頼内容に関わらず毎回挿入する固定プロンプトの正本情報。
- execution context、権威順位、oracle・アクセス制限、入力解釈、workspace 取り扱い、出力規律などの基本原則を扱う。

# `knowledge_system_rules.md`

- 知識システム利用に関するプロンプトブロックの正本情報。
- caller が知識システムかどうかに応じて、利用指示を注入する場合と再帰呼び出しを禁止する場合の切り分けを扱う。

# `overall_prompt_rule.md`

- tgbt が Codex CLI に渡す最終プロンプト全体の構成規則。
- Fixed prompt、Knowledge system rules、Structured Output、Task prompt の順序と、結合後プロンプトの品質要件への導線を扱う。

# `prompt_block_basic_rules.md`

- プロンプトブロックによるプロンプト構築の基本規則。
- ブロックの木構造、JSON 表現、Markdown 見出しへのレンダリング、Python 上での遅延合成方針を扱う。

# `quality_requirements.md`

- レンダリング済みプロンプトが意味論的に満たすべき品質要件。
- 意図とのドリフト、暗黙知依存、入力の権威順位、作業範囲、完了条件、不確実性、出力形式、prompt injection 耐性をレビュー観点として扱う。

# `structured_output.md`

- Structured Output を使うための正本情報。
- Pydantic schema クラス、`--output-schema` 用 JSON、スキーマバリデーション、スキーマ付属プロンプト、caller 側プロンプト、定数管理を扱う。

# `task_prompt.md`

- Codex CLI 向けタスクプロンプトの構成規約。
- Task、Authority rules、Input handling rules、Read targets、Task-specific rules、Operational parameters、Inputs、Uncertainty handling、Self check などの推奨 block 構成を扱う。
