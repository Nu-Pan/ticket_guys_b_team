---
name: refactor-docs
description: "docs/ 配下の markdown 文書を再編し、階層整理、rename、docs/ROUTING.md の再構築、stale 参照や壊れたリンクの修復を安全に進めるためのスキル。Use when Codex needs to refactor repository-local development docs, reorganize documentation structure, repair docs/... references after moves, audit empty or orphaned docs, or rebuild navigation for docs/."
---

# Refactor Docs

## Overview

`docs/` を AI 管理下の開発文書として整えつつ、仕様の正本や人間専用領域を侵さずに再編する。
まず現状を棚卸しし、次に導線とリンクを揃え、最後に `docs/ROUTING.md` を現況に合わせて再構築する。

## Non-Negotiables

- 最初に repository root の `AGENTS.md` を確認し、その制約を外さない。
- `README.md`、`oracle/**`、`memo/**`、`AGENTS.md` は編集しない。
- `docs/` は開発詳細の置き場であり、`tgbt` の正本仕様を書き足さない。
- `oracle/` は人間が管理する断片的な正本仕様であり、必要なときだけ参照する。対応する断片が存在する範囲でのみ `docs/` と突き合わせ、未記載部分を AI が補完しない。
- 人間が意図した抽象仕様を補完しない。現在の worktree と既存文書から確定できる整理だけを行う。
- 削除済み文書を、根拠なく復活させない。必要なら current worktree、既存参照、周辺コードの三者で裏を取る。

## Workflow

### 1. Confirm current documentation state

- `docs/ROUTING.md` を開き、空ファイルか stale かを確認する。
- `find docs -type f` または `scripts/summarize_docs_tree.py docs` で inventory を作る。
- `git status --short docs .agents` で rename / delete / untracked の流れを把握する。

### 2. Decide the target structure from current evidence

- 現在存在する文書を軸に分類する。消えた旧階層を前提にしない。
- 再編は「参照される現行文書が分かりやすくなるか」で判断する。
- 大きく移動する前に、どの文書が index / routing / detailed guide の役割を持つかを一度言語化する。

### 3. Refactor docs safely

- 空ファイル、重複気味の文書、名称が古い文書を優先的に整理する。
- 文書移動や rename を行うときは、参照元更新を同じ作業単位に含める。
- `docs/ROUTING.md` は「今ある文書への入口」に徹し、仕様の要約や重複説明を書き込まない。

### 4. Reconcile docs with explicit oracle fragments

- 対象文書と対応する `oracle/` の断片が存在する場合だけ、その範囲で内容を突き合わせる。
- `docs/` の記述が明示 oracle 断片と衝突するなら、`docs/` 側を是正する。
- `oracle/` に書かれていない挙動や背景を、AI 判断で `docs/` に補完しない。
- `oracle/` に対応断片が見当たらない場合は、実装・既存 docs・既存参照から確定できる整理に留める。

### 5. Repair references

- `scripts/audit_docs_links.py .` を使い、`docs/...` 参照の壊れを洗う。
- markdown link だけでなく、インラインコード中の `docs/...` パスも監査対象にする。
- `docs` を参照する skill や開発ドキュメントも更新対象に含める。

### 6. Validate the new shape

- `docs/ROUTING.md` から各主要文書へ辿れることを確認する。
- 主要文書に残った `docs/...` 参照が実在パスを向くことを確認する。
- 明示 oracle 断片と対応する `docs/` 文書については、衝突が残っていないことを確認する。
- stale path、空ファイル、孤立文書が残るなら、残す理由を説明できる状態にする。

## Default execution pattern

1. `python3 .agents/skills/refactor-docs/scripts/summarize_docs_tree.py docs`
2. `python3 .agents/skills/refactor-docs/scripts/audit_docs_links.py .`
3. 対象 `docs/` に対応する `oracle/` 断片があるか確認し、明示差分だけを拾う
4. inventory と audit 結果から再編案を作る
5. 文書移動・rename・内容更新を行う
6. 同じ 2 つの script を再実行し、差分を確認する

## Resources

### `scripts/summarize_docs_tree.py`

`docs/` のツリー、各文書の H1、空ファイル、`ROUTING.md` に載せる候補を一覧化する。
再編前の inventory 作成と、再編後の導線確認に使う。

### `scripts/audit_docs_links.py`

`docs/...` 参照を静的に洗い、存在しない相対リンク、インラインコード中の stale path、`docs` 外から `docs` を参照している markdown を一覧化する。

### `references/docs-refactor-rules.md`

この repo で `docs/` を再編し、必要に応じて明示 oracle 断片との整合も取るときの判断基準だけをまとめた reference。迷ったときだけ読む。
