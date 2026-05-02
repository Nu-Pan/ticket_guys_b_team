
# スキルの扱いについての原則

- 開発作業一般に関する断片的な正本情報は `<tgbt-root>/oracle` に書く
- そのうえで、個別具体的な `tgbt` の開発作業の指示（パターン別指示）は `<tgbt-root>/.agents/skills/*` にリポジトリローカルなスキルとしてパッケージングする
- 基本的に、人間が AI に何かを依頼する時はリポジトリ固有スキルを指定することとする
- リポジトリ固有スキルから作業指示がロードされる事を前提に、作業方法についての指示は `<tgbt-root>/AGENTS.md` に極力書かない
- `$HOME/.codex` 配下の system skill の編集は禁止

# スキル `create-repo-local-skill`

- リポジトリローカルなスキルのメンテナンス・新規作成は `<tgbt-root>/.agents/skills/create-repo-local-skill` を用いることとする
- `create-repo-local-skill` はシステムスキル `skill-creator` を必ず併用するものとする
- `create-repo-local-skill` は、追加の指示が無い場合、リポジトリローカルなスキル全てのメンテナンスを行う
- `create-repo-local-skill` は各スキルに対して、以下の観点でメンテナンスを行う
    - 人間がメンテナンスする正本情報 (e.g. `<tgbt-root>/oracle`) と `SKILL.md` とに矛盾がないか
    - `SKILL.md` の内容に、シンプル化・短縮可能な余地 (e.g. 明らかに無駄・冗長な記述) がないか
    - `SKILL.md` の内容に、スクリプト化可能な余地がないか
    - OpenAI 公式ドキュメントと照らし合わせて、問題・改善の余地がないか
    - 一般的なベストプラクティスと照らし合わせて、改善の余地がないか
