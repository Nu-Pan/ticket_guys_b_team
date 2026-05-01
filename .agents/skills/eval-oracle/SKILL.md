---
name: eval-oracle
description: Evaluate tgbt oracle content without editing it. Use when reporting contradictions, ROUTING.md entry-list drift, typo, or reference inconsistencies from existing oracle text.
---

# Eval Oracle

## Overview

`<tgbt-root>/oracle/**` は人間が責任を持つ断片的な正本仕様であり、AI は編集しない。
この skill は、AI が oracle を読み、現存記述同士の矛盾、routing の過不足、typo などの初歩的問題を評価して人間へ返すための作業原則を定める。
`ROUTING.md` とファイルシステム上の実体との照合は、可能な限り bundled script で機械的に確認する。

## Guardrails

- `<tgbt-root>/oracle/**` は読むだけにする。作成、編集、削除、整形、移動をしない。
- `<tgbt-root>/oracle` は不完全であることを前提に扱う。未記載、網羅漏れ、抽象仕様の不足は問題として指摘しない。
- oracle の修正方向を示す場合も、仕様を勝手に確定しない。最終判断と修正は人間に委ねる。
- 評価結果は回答として報告し、レビュー記録や中間ドキュメントとして永続化しない。

## Evaluation Scope

### 評価する

- 複数の oracle ファイル間、または同一ファイル内での論理的な矛盾。
- 同じ概念、用語、パス、コマンド、責務についての説明が衝突している箇所。
- 各階層の `ROUTING.md` のファイル・ディレクトリリストと、同階層の実ファイル・ディレクトリ構成との過不足。
- 参照先ファイルや routing の記述と実ファイル構成の不整合。
- typo、明らかな脱字、誤字、Markdown 構造の軽微な破綻。
- 表記ゆれのうち、読み手や実装者が別概念として誤解しそうなもの。

### 評価しない

- oracle に書かれていない仕様や要求の不足。ただし、既存 oracle ファイルが同階層の `ROUTING.md` に載っていない場合は routing の不足として評価する。
- 正本仕様として何が望ましいかというプロダクト判断。
- 実装が oracle に追従しているかどうかの網羅的確認。
- `<tgbt-root>/README.md`、`<tgbt-root>/memo/**`、AI 管理ドキュメントを含む一般的なドキュメントレビュー。
- typo 修正や文章改善の直接編集。

## Workflow

1. `<tgbt-root>/AGENTS.md` を読み、作業制約を確認する。
2. `<tgbt-root>/oracle/docs/ROUTING.md` と対象階層の `ROUTING.md` から、依頼に関係する oracle ファイルだけを辿る。
3. routing の過不足を含む評価では、`<tgbt-root>` から次を実行する。

```bash
./.venv/bin/python .agents/skills/eval-oracle/scripts/check_routing.py
```

4. `check_routing.py` の結果は、機械的に確認できた事実として扱う。script が失敗した場合は、失敗理由と手動確認範囲を分ける。
5. 必要に応じて `rg` で関連語、ファイル名、コマンド名、同じ概念の別表記を検索する。
6. 明示された記述同士を比較し、矛盾、typo、参照不整合、routing の過不足だけを抽出する。
7. 不完全性に由来する未記載事項は指摘から外す。
8. 判断できないものは推測で埋めず、「未確定」として必要な追加判断を示す。

## Routing Check Script

- `scripts/check_routing.py` は、`<tgbt-root>/oracle/docs/` 配下の `ROUTING.md` と実ファイル・実ディレクトリの過不足を照合する。
- 検出結果は、`ROUTING.md` 自体がない、`ROUTING.md` にあるが実体がない、実体はあるが `ROUTING.md` にない、に分けて扱う。
- `ROUTING.md` の説明文の妥当性、概念衝突、typo は script に任せず、oracle 本文を読んで評価する。

## Reporting Rules

- 評価対象を一文で言い換え、findings を先に並べる。なければ「指摘なし」と書く。
- finding は重要度順に並べ、問題種別、根拠ファイル、影響、必要なら人間向けの確認観点を示す。
- 「事実」「推論」「未確定事項」を混同しない。
- routing の過不足は、「`ROUTING.md` 自体がない」「`ROUTING.md` にあるが実体がない」「実体はあるが `ROUTING.md` にない」を区別して報告する。
- 最後に、評価しなかった範囲や残る不確定事項を短く添える。
- 問題が見つからない場合は、その範囲で矛盾や typo を見つけられなかったと明示し、網羅性を保証しない。
