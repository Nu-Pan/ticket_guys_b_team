---
name: update-oracle-docs-routing
description: Normalize, update, or review tgbt oracle/docs ROUTING.md files. Use only when a target directory under the tgbt oracle/docs tree is specified.
---

# Update Oracle Docs Routing

## Overview

`<tgbt-root>/oracle/docs` 配下の指定ディレクトリについて、直下の `ROUTING.md` を機械的に正規化し、その後にルーティング本文を AI が確認・修正する。
通常の `<tgbt-root>/oracle/**` は AI 編集禁止だが、`ROUTING.md` は `<tgbt-root>/oracle/docs/dev_rule/oracle_docs_routing_policy.md` により例外的に編集可能とする。

## Guardrails

- 対象ディレクトリが指定されていない場合は何もしない。
- 編集してよいのは、指定ディレクトリ直下の `ROUTING.md` だけ。
- `<tgbt-root>/oracle/docs` 配下でも、`ROUTING.md` 以外の oracle ファイルは読むだけにする。
- `<tgbt-root>/README.md`、`<tgbt-root>/AGENTS.md`、`<tgbt-root>/memo/**` は編集しない。`memo/**` は閲覧もしない。
- `<tgbt-root>/oracle/docs/dev_rule/oracle_docs_routing_policy.md` を `ROUTING.md` フォーマットの正本として扱う。
- ルーティング先の内容を調べるときは、指定ディレクトリ直下のファイル・ディレクトリに限定し、必要最小限だけ読む。

## Workflow

### 1. Confirm scope

- `<tgbt-root>/AGENTS.md` を確認する。
- 指定ディレクトリを `<tgbt-root>/oracle/docs` 配下のディレクトリとして解決する。相対パスは `<tgbt-root>` からの相対パスとして扱う。
- 対象が `<tgbt-root>/oracle/docs` 配下でない、または存在しないディレクトリなら作業を止めて報告する。

### 2. Run mechanical normalization

`<tgbt-root>` から bundled script を実行する。

```bash
./.venv/bin/python .agents/skills/update-oracle-docs-routing/scripts/normalize_routing.py <target-dir>
```

script は次を機械的に揃える。

- 指定ディレクトリ直下に `ROUTING.md` を作る。
- `ROUTING.md` の見出しを、指定ディレクトリ直下の `.md` ファイルと子ディレクトリに一致させる。
- `ROUTING.md` のフォーマットを `# \`entry\`` + 空行 + 箇条書き本文へ正規化する。
- 既存 entry の本文は、対応する実体が残っている限り保持する。
- 新規 entry には `TODO` 本文を置く。これは次の AI レビューで必ず具体化する。

### 3. Review routing text

指定ディレクトリ直下の `ROUTING.md` だけを編集対象として、各 entry の本文を確認・修正する。

レビュー観点:

- ルーティング先の実態と `ROUTING.md` 上の本文が整合しているか。
- 本文が 1 から 5 行程度に収まっているか。
- ルーティング先の全容を推測できる本文になっているか。
- ルーティング先の内容を概ねカバーしているか。
- 詳細に寄りすぎず、適度に抽象的か。
- 「このファイル」「このディレクトリ」など、ルーティング先を読まないと意味が分からない自己言及になっていないか。
- typo、脱字、Markdown の軽微な破綻がないか。

子ディレクトリ entry の本文を直す場合は、その子ディレクトリ直下の `ROUTING.md` を優先して読む。
`.md` ファイル entry の本文を直す場合は、その `.md` ファイルを必要最小限だけ読む。

### 4. Validate

最後に、`<tgbt-root>/oracle/docs` 配下全体の機械的な routing 整合を確認する。

```bash
./.venv/bin/python .agents/skills/update-oracle-docs-routing/scripts/check_routing.py
```

この skill 自体を編集した場合は、skill validation も実行する。

```bash
./.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" .agents/skills/update-oracle-docs-routing
```

## Reporting

- 対象ディレクトリと、更新した `ROUTING.md` を明示する。
- 機械的正規化で追加・削除・並べ替えされた entry を要約する。
- AI が本文を修正した entry と、修正理由を短く示す。
- 実行した validation と結果を報告する。
- 対象指定がなく何もしなかった場合は、その理由だけを報告する。
