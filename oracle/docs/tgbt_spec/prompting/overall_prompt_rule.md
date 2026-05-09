
# 最終的なプロンプト規則

## 前提

- 「結局 `tgbt` から AI に渡すプロンプトはどう有るべきなのか？」この問いに、このドキュメントは答える
- このドキュメントを起点に各種関係ドキュメントを読めば、答えが得られるものとする

## プロンプトブロック

- `tgbt` から AI に渡す「最終的なプロンプト」は「プロンプトの断片ブロック」から構築する
- この断片のことを「プロンプトブロック」と呼ぶ
- 詳細は `<tgbt-root>/oracle/docs/tgbt_spec/prompting/prompt_block_basic_rules.md` を参照

## プロンプトブロック順序

1. Fixed prompt
    - `<tgbt-root>/oracle/docs/tgbt_spec/prompting/fixed_prompt.md`
    - あらゆる Codex CLI 呼び出しで共通する固定プロンプト
2. Knowledge system rules
    - `<tgbt-root>/oracle/docs/tgbt_spec/prompting/knowledge_system_rules.md`
    - 知識システムの利用についての指示
    - 呼び出し元次第で内容が変わるため、独立したブロックにしている
3. Structure output
    - `<tgbt-root>/oracle/docs/tgbt_spec/prompting/structured_output.md`
    - Codex CLI から構造化出力を得るために必要な指示を記述するブロック
    - スキーマクラスから機械的に合成される
4. Task prompt
    - `<tgbt-root>/oracle/docs/tgbt_spec/prompting/task_prompt.md`
    - タスク固有のプロンプト要件ごとに内容は異なる

## レンダリング済みプロンプトが意味論的に満たすべき品質要件

- 上述の内容から、ブロック構成や、ブロック内で何を述べるべきかは確定するが、これだけでは不十分
- 「レンダリングされた完全プロンプト」と「`tgbt` が元々意図していたこと」とがドリフトしないように「結合後ドメイン」上での施策が必要である（合成の誤謬の回避）
- そこで、レンダリング済みプロンプトが意味論的に満たすべき品質要件を定義する
- 詳細は `<tgbt-root>/oracle/docs/tgbt_spec/prompting/quality_requirements.md` を参照
