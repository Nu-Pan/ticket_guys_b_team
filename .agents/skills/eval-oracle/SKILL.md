---
name: eval-oracle
description: Evaluate existing tgbt oracle text without editing it. Use for contradictions, typos, path/context mixups, permission-boundary conflicts, and wording issues; do not use for ROUTING.md correctness.
---

# Eval Oracle

## Overview

`<tgbt-root>/oracle/**` の既存記述を読み、論理的な矛盾、typo、誤解を招く表記ゆれ、パス文脈や AI 権限境界の衝突を評価して人間へ返す。

## Guardrails

- `<tgbt-root>/oracle/**` は読むだけにする。作成、編集、削除、整形、移動をしない。
- `<tgbt-root>/oracle` は不完全であることを前提に扱い、未記載、網羅漏れ、抽象仕様の不足は指摘しない。
- `ROUTING.md` の正しさ、実ファイル構成との一致、routing 本文の妥当性は評価しない。必要なら `$update-oracle-docs-routing` の対象として報告する。
- oracle の修正方向を示す場合も、仕様を勝手に確定しない。最終判断と修正は人間に委ねる。
- 評価結果は回答として報告し、レビュー記録や中間ドキュメントとして永続化しない。

## Scope

評価する:

- 複数の oracle ファイル間、または同一ファイル内での論理的な矛盾。
- 同じ概念、用語、パス、コマンド、責務についての説明が衝突している箇所。
- `<tgbt-root>` と `<repo-root>` などの文脈依存パス表記が、別文脈の意味で使われている箇所。
- AI が編集禁止、閲覧禁止、編集可能とされる対象や境界が、別の oracle 本文の明示記述と衝突している箇所。
- スキル間の責務分担や、あるスキルの対象外事項と別スキルの対象事項が衝突している箇所。
- oracle 本文が参照しているファイル、コマンド、概念名が、別の oracle 本文の明示記述と衝突している箇所。
- typo、明らかな脱字、誤字、読み手が意味を取り違える Markdown 構造の破綻。
- 表記ゆれのうち、読み手や実装者が別概念として誤解しそうなもの。

評価しない:

- oracle に書かれていない仕様や要求の不足。
- 正本仕様として何が望ましいかというプロダクト判断。
- 実装が oracle に追従しているかどうかの網羅的確認。
- `ROUTING.md` の存在、フォーマット、見出し、本文、実ファイル構成との一致。
- `<tgbt-root>/README.md`、`<tgbt-root>/memo/**`、AI 管理ドキュメントを含む一般的なドキュメントレビュー。
- typo 修正や文章改善の直接編集。

## Workflow

1. `<tgbt-root>/AGENTS.md` を読み、作業制約を確認する。
2. `<tgbt-root>/oracle/docs/ROUTING.md` と対象階層の `ROUTING.md` から、依頼に関係する oracle ファイルだけを辿る。
3. 必要に応じて `rg` で関連語、ファイル名、コマンド名、同じ概念の別表記を検索する。
4. 明示された記述同士を比較し、評価対象の問題だけを抽出する。不完全性に由来する未記載事項は外す。
5. 判断できないものは推測で埋めず、「未確定」として必要な追加判断を示す。

## Reporting Rules

- 評価対象を一文で言い換え、findings を先に並べる。なければ「指摘なし」と書く。
- finding は重要度順に並べ、問題種別、根拠ファイル、影響、必要なら人間向けの確認観点を示す。
- 「事実」「推論」「未確定事項」を混同しない。
- `ROUTING.md` に関する問題を見つけた場合は、この skill の finding には含めず、`$update-oracle-docs-routing` の対象外事項として短く分離する。
- 問題が見つからない場合は、その範囲で矛盾や typo を見つけられなかったと明示し、網羅性を保証しない。
- 最後に、評価しなかった範囲や残る不確定事項を短く添える。
