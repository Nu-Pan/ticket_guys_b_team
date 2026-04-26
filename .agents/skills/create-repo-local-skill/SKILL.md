---
name: create-repo-local-skill
description: tgbt の repo-local なスキルを `.agents/skills` 配下に新規作成または安全に更新するためのスキル。Use when Codex needs to create a new repository-local skill for this tgbt repo, package purpose-specific agent principles as a skill, automatically follow the upstream `$skill-creator` workflow, and avoid writing anything under `~/.codex`.
---

# Create Repo Local Skill

## Overview

`tgbt` 用の repo-local skill を `.agents/skills` に作る。
workflow 自体は upstream の `$skill-creator` を使い、その出力先と制約だけをこの repo 向けに固定する。

## Non-Negotiables

- 最初に repository root の `AGENTS.md` を確認し、その制約を外さない。
- `README.md`、`oracle/**`、`memo/**`、`AGENTS.md` は編集しない。
- `oracle/**` は skill 内容の整合確認のために読むことはできるが、正本仕様として扱い、AI は更新しない。
- 新規スキルは `.agents/skills/<skill-name>` にのみ作成する。
- `~/.codex` 配下には書き込まない。system skill の read のみ許可する。
- 新規スキルは「tgbt 上で AI エージェントが何かを行う際の目的別原則」を package するものとして設計する。`tgbt` の正本仕様を書かない。
- 新規・更新する skill は AI が読む作業指示であり、`docs/` のような AI 管理の中間ドキュメントを作らない。
- `.agents/skills/<skill-name>` が既に存在する場合は、自動上書きしない。更新対象として扱うかを user に確認する。
- user が既存 skill の確認や修正を明示した場合は、対象 skill を既存更新として扱う。

## Workflow

### 1. Load upstream skill-creator immediately

- まず `/home/happy/.codex/skills/.system/skill-creator/SKILL.md` を読み、以後の作業では `$skill-creator` の手順を使う。
- この skill は upstream workflow の router であり、初期化・metadata 生成・validation は upstream scripts を優先する。

### 2. Check repo-local rules

- `AGENTS.md` を読んだうえで、必要な `oracle/dev_rule/*` だけ読む。
- repo-local skill の原則は `oracle/dev_rule/codex_skill.md` を参照する。
- AI 管理ドキュメント禁止の前提は `oracle/dev_rule/ai_docs.md` を参照する。
- `.venv` や依存導入が論点になる場合は `oracle/dev_rule/environment.md` を参照する。

### 3. Fix the install root to this repository

- skill の install 先は常に `.agents/skills` に固定する。
- upstream が既定で使う `$CODEX_HOME/skills` や `~/.codex/skills` は使わない。
- skill 名は lowercase letters, digits, hyphens only の hyphen-case に正規化する。

### 4. Create the new skill safely

- target directory が未作成なら、upstream の `init_skill.py` を repo-local path で実行する。
- command pattern は次を基準にする。

```bash
./.venv/bin/python /home/happy/.codex/skills/.system/skill-creator/scripts/init_skill.py <skill-name> --path .agents/skills
```

- resources は本当に必要なものだけ選ぶ。不要なら `scripts/`, `references/`, `assets/` を作らない。
- 新規スキルの本文では、対象タスクをどう進めるかの実務原則と repo 固有の guardrails を優先して書く。
- 補足説明のためだけに `README.md`、`docs/`、`QUICK_REFERENCE.md` のような文書を追加しない。

### 5. Generate or refresh UI metadata

- `agents/openai.yaml` は upstream の `generate_openai_yaml.py` で生成または再生成する。
- `display_name`, `short_description`, `default_prompt` は新規スキルの用途を読んで決める。
- `default_prompt` には必ず `$<skill-name>` を明示する。

```bash
./.venv/bin/python /home/happy/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py .agents/skills/<skill-name> --interface default_prompt="Use $<skill-name> ..."
```

### 6. Validate before finishing

- 最後に upstream の `quick_validate.py` で生成結果を検証する。
- validation に落ちたら、frontmatter と naming と metadata を修正して再実行する。

```bash
./.venv/bin/python /home/happy/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/<skill-name>
```

## Default execution pattern

1. user request から新規スキルの目的と concrete examples を整理する
2. `$skill-creator` の観点で必要 resource を決める
3. `oracle/dev_rule/codex_skill.md` と `oracle/dev_rule/ai_docs.md` の制約を確認する
4. 必要なら `init_skill.py` を `--path .agents/skills` 付きで実行する
5. `SKILL.md` を repo-local の原則に合わせて仕上げる
6. 必要なら `generate_openai_yaml.py` で `agents/openai.yaml` を揃える
7. `quick_validate.py` を通して完了する

## Reporting Rules

- どの skill 名で作るかを最初に明示する。
- 新規作成か既存更新かを明示する。
- 作成した path と使った upstream script を最後に報告する。
- validation の結果を最後に添える。
