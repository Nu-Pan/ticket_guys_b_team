---
name: eval-oracle
description: tgbt の `oracle/**` を AI が編集せずに評価し、ドキュメント間の論理矛盾、ROUTING.md のファイル・ディレクトリリスト過不足、typo などの初歩的問題を根拠付きで報告するための repo-local skill。Use when Codex needs to review oracle files for contradictions, ROUTING.md entry-list drift, or basic document issues without filling in missing specifications or modifying oracle content.
---

# Eval Oracle

## Overview

`oracle/**` は人間が責任を持つ断片的な正本仕様であり、AI は編集しない。
この skill は、AI が oracle を読み、明示された内容同士の矛盾や typo などの問題だけを評価して人間へ返すための作業原則を定める。
`ROUTING.md` とファイルシステム上の実体との照合は、可能な限り bundled script で機械的に確認する。

## Non-Negotiables

- 最初に repository root の `AGENTS.md` を確認し、その制約を外さない。
- `oracle/**` は読むだけにする。作成、編集、削除、整形、移動をしない。
- `README.md`、`oracle/**`、`memo/**`、`AGENTS.md` は編集しない。
- `README.md` と `memo/**` は読まない。
- `oracle/` は不完全であることを前提に扱う。未記載、網羅漏れ、抽象仕様の不足は問題として指摘しない。
- AI 管理の中間ドキュメントやレビュー記録を `docs/` などに永続化しない。
- oracle の修正案を提示する場合も、仕様を勝手に確定しない。最終判断と修正は人間に委ねる。

## Evaluation Scope

### 評価すること

- 複数の oracle ファイル間、または同一ファイル内での論理的な矛盾。
- 同じ概念、用語、パス、コマンド、責務についての説明が衝突している箇所。
- 参照先ファイルや routing の記述と実ファイル構成の不整合。
- 各階層の `ROUTING.md` のファイル・ディレクトリリストと、同階層の実ファイル・ディレクトリ構成との過不足。
- typo、明らかな脱字、誤字、Markdown 構造の軽微な破綻。
- 表記ゆれのうち、読み手や実装者が別概念として誤解しそうなもの。

### 評価しないこと

- oracle に書かれていない仕様や要求の不足。ただし、既存 oracle ファイルが同階層の `ROUTING.md` に載っていない場合は routing の不足として評価する。
- 正本仕様として何が望ましいかというプロダクト判断。
- 実装が oracle に追従しているかどうかの網羅的確認。
- README、memo、AI 管理ドキュメントを含む一般的なドキュメントレビュー。
- typo 修正や文章改善の直接編集。

## Workflow

1. `AGENTS.md` を読み、編集禁止範囲を確認する。
2. routing の過不足を含む評価では、まず `./.venv/bin/python .agents/skills/eval-oracle/scripts/check_routing.py` を repo root から実行する。
3. `check_routing.py` の結果を、機械的に確認できた事実として扱う。script が失敗した場合は、失敗理由と手動で確認できた範囲を区別する。
4. `oracle/docs/ROUTING.md` と対象階層の `ROUTING.md` から、依頼に関係する oracle ファイルだけを辿る。
5. `rg` で関連語、ファイル名、コマンド名、同じ概念の別表記を検索する。
6. 明示された記述同士を比較し、矛盾・typo・参照不整合・routing の過不足だけを抽出する。
7. 不完全性に由来する未記載事項は指摘から外す。
8. 指摘ごとに、対象ファイル、問題の種類、根拠、影響、必要なら人間が検討できる最小限の修正方向をまとめる。
9. 判断できないものは推測で埋めず、「未確定」としてどの追加判断が必要かを示す。

## Routing Check Script

- `scripts/check_routing.py` は、`oracle/docs/` 配下の各ディレクトリに `ROUTING.md` が存在するかを確認する。
- 各階層では、`ROUTING.md` 内の ``# `name` `` 形式の見出しをファイル・ディレクトリリストとして抽出し、同階層の実ファイル・実ディレクトリ一覧と照合する。
- 照合対象の実ファイルは同階層の Markdown ファイルとし、`ROUTING.md` 自体は除外する。
- script の検出結果は、`ROUTING.md` 自体がない、`ROUTING.md` にあるが実体がない、実体はあるが `ROUTING.md` にない、に分けて報告する。
- `ROUTING.md` の説明文の妥当性、概念衝突、typo は script に任せず、従来通り oracle 本文を読んで評価する。

## Reporting Rules

- 最初に、評価対象と結論を短く述べる。
- finding は重要度順に並べる。
- 各 finding には根拠ファイルを添える。
- 「事実」「推論」「未確定事項」を混同しない。
- oracle の欠落を埋める提案ではなく、現存記述の衝突や初歩的問題に限定して報告する。
- routing の過不足は、「`ROUTING.md` 自体がない」「`ROUTING.md` にあるが実体がない」「実体はあるが `ROUTING.md` にない」を区別して報告する。
- 問題が見つからない場合は、その範囲で矛盾や typo を見つけられなかったと明示し、網羅性を保証しない。

## Default Answer Shape

- 評価対象を一文で言い換える。
- findings を先に並べる。なければ「指摘なし」と書く。
- 各 finding で、問題種別、根拠、影響、必要なら人間向けの確認観点を示す。
- 最後に、評価しなかった範囲や残る不確定事項を短く添える。
