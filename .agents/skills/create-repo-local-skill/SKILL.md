---
name: create-repo-local-skill
description: Create, update, or review tgbt repo-local skills under `.agents/skills`. Use when maintaining skill instructions or metadata, aligning with oracle and `$skill-creator`, or validating skills without editing `~/.codex`.
---

# Create Repo Local Skill

## Overview

`tgbt` 用の repo-local skill を `.agents/skills` に作成・更新・メンテナンスする。
upstream の `$skill-creator` を必ず併用し、repo 固有の正本情報は `oracle`、Codex skill 一般の外部根拠は OpenAI 公式 docs と upstream skill-creator で確認する。
詳細な作成手順は upstream skill-creator を優先し、公式 docs は現在の配置・trigger・metadata 方針の確認に使う。

## Guardrails

- 新規・更新・メンテナンス対象は `.agents/skills/<skill-name>` 配下に限定する。
- `~/.codex` 配下には書き込まない。system skill は read と bundled script の実行だけに使う。
- skill は「tgbt 上で AI エージェントが行う目的別作業指示」として書く。`tgbt` の正本仕様や作業ログを書かない。
- `SKILL.md` は実行時に必要な指示へ絞る。補足説明用の `README.md`、`docs/`、`QUICK_REFERENCE.md` などは追加しない。
- user が対象 skill を指定していない場合は、repo-local skill 全体をメンテナンス対象として扱う。

## Workflow

### 1. Load upstream skill-creator

- まず `/home/happy/.codex/skills/.system/skill-creator/SKILL.md` を読み、以後の作業では `$skill-creator` の手順を使う。
- 初期化、metadata 生成、validation は upstream scripts を優先する。

### 2. Check repo-local rules when needed

- `AGENTS.md` を確認する。
- repo-local skill の原則は、`oracle/docs/ROUTING.md` と `oracle/docs/dev_rule/ROUTING.md` を辿って `oracle/docs/dev_rule/codex_skill.md` を参照する。
- AI 管理ドキュメント、`.venv`、依存導入、`oracle` の扱いが論点になる場合だけ、対応する `oracle/docs/dev_rule/*.md` を読む。

### 3. Decide targets and mode

- user が skill 名を指定した場合は、その `.agents/skills/<skill-name>` だけを対象にする。
- user が対象を指定せず repo-local skill のメンテナンスを依頼した場合は、`.agents/skills/*` を対象にする。
- `.agents/skills/<skill-name>` が存在しない場合は新規作成として扱う。
- 既存 skill の修正・確認が明示されている場合は既存更新として扱う。
- 既存 skill があり、user の意図が新規作成か更新か曖昧な場合だけ確認する。
- 既存更新では `init_skill.py` を再実行しない。`SKILL.md` と必要な bundled resources だけを編集する。

### 4. Fix the install root and naming

- install 先は常に `.agents/skills` に固定する。
- upstream が既定で使う `$CODEX_HOME/skills` や `~/.codex/skills` は使わない。
- skill 名は lowercase letters, digits, hyphens only の hyphen-case にする。

### 5. Create new skills

新規作成では upstream の `init_skill.py` を repo-local path で実行する。

```bash
./.venv/bin/python /home/happy/.codex/skills/.system/skill-creator/scripts/init_skill.py <skill-name> --path .agents/skills
```

- `scripts/`, `references/`, `assets/` は、実行時に直接役立つ場合だけ追加または更新する。
- `SKILL.md` には、対象タスクをどう進めるかの実務原則と repo 固有 guardrails を書く。

### 6. Maintain existing skills

既存更新では `init_skill.py` を使わず、既存内容を読んで必要最小限の差分にする。各 skill は次の観点で確認する。

- `oracle` の明示内容や `AGENTS.md` と矛盾していないか。
- `SKILL.md` に、シンプル化・短縮可能な冗長指示が残っていないか。
- 繰り返しが多い、または機械的に検証すべき処理を `scripts/` に切り出す余地があるか。
- OpenAI 公式 Codex skills docs と upstream `$skill-creator` の現在の guidance から見て、description、progressive disclosure、bundled resources、metadata に問題がないか。
- 一般的な skill best practices から見て、1 skill 1 job になっているか、入出力や手順が曖昧でないか。

OpenAI 公式 docs を参照する場合は、公式ドメインの最新 docs を使う。特に description は implicit invocation の trigger になるため、用途と境界を前方に寄せて簡潔に書く。

### 7. Generate or refresh UI metadata

- `.agents/skills/<skill-name>/agents/openai.yaml` が存在しない場合や `SKILL.md` と明らかにずれている場合は、upstream の `generate_openai_yaml.py` で生成または再生成する。
- `display_name`, `short_description`, `default_prompt` は対象 skill の用途を読んで決める。
- `default_prompt` には必ず `$<skill-name>` を明示する。

```bash
./.venv/bin/python /home/happy/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py .agents/skills/<skill-name> --interface display_name="..." --interface short_description="..." --interface default_prompt="Use $<skill-name> ..."
```

### 8. Validate

- 最後に upstream の `quick_validate.py` で対象 skill を検証する。複数 skill をメンテナンスした場合は全件検証する。
- validation に落ちたら、frontmatter と naming と metadata を修正して再実行する。

```bash
./.venv/bin/python /home/happy/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/<skill-name>
```

## Reporting Rules

- 対象 skill 名と、新規作成か既存更新かを明示する。
- 更新した path、参照した主な `oracle` / 公式 docs / upstream skill-creator、使った upstream script、validation 結果を報告する。編集しない review の場合は、更新なしと findings を明示する。
- `~/.codex` 配下を編集していないことを明示する。
