---
name: implement-task
description: tgbt リポジトリで、人間が切ったスコープ内の具体的な実装修正を進めるためのスキル。Use when Codex needs to implement or fix a class, function, or localized behavior, update matching tests, and avoid making product-level design decisions.
---

# Implement Task

## Overview

人間が定義した具体的な変更要求を、既存実装・既存テスト・必要な `oracle` 断片の範囲で安全に実装へ落とす。
AI は low-level な実装、局所的な整合調整、対応テストの更新を担当し、抽象設計や仕様策定は人間へ返す。

## Non-Negotiables

- 最初に repository root の `AGENTS.md` を確認し、その制約を外さない。
- `README.md`、`oracle/**`、`memo/**`、`AGENTS.md` は編集しない。
- `README.md` と `memo/**` は閲覧もしない。
- `oracle/` は人間が管理する断片的な正本仕様であり、必要なときだけ参照し、完全仕様として未記載部分を補完しない。
- `docs/` のような AI 管理の中間ドキュメントは作成・更新しない。
- 人間が切っていない抽象設計、仕様策定、プロダクト判断を AI が引き取らない。
- 変更は最小限に留め、要求を満たすために必要な局所差分を優先する。
- 実装だけでなく、変更内容に対応するテスト追加・更新と局所検証まで責務に含める。

## Task Boundary

### この skill が扱うこと

- 既存設計の範囲で関数・クラス・分岐・入出力を実装または修正する。
- 既存の public interface を維持したまま、局所的な bug fix や整合調整を行う。
- 変更に対応する stub テストや unit テストを追加・更新する。
- 実装後に型チェックと対象テストを実行し、差分が狙いどおりか確認する。

### この skill が扱わないこと

- プロダクトビジョン、要求定義、抽象アーキテクチャ設計を決めること。
- 複数の妥当な振る舞いがあり、既存コードやテストから決め切れない仕様判断を行うこと。
- 大規模リファクタ、責務分割の再設計、広範囲な public API 変更を独断で進めること。
- 「完全仕様」を AI が推定して未実装部分を広げること。

## Evidence Order

- まず user request を、どの関数・クラス・コマンド・テストを触る話かに分解する。
- 挙動の根拠は、既存テスト、実装、必要な `oracle` 断片の順で集める。
- `oracle` を読むときは `oracle/ROUTING.md` と各階層の `ROUTING.md` から必要なファイルだけ辿る。
- Python 実装を触るときは `oracle/dev_rule/python_coding.md` を読む。
- `.venv`、依存追加、ツール実行方法が論点なら `oracle/dev_rule/environment.md` を読む。
- テスト追加・修正や確認方法が論点なら `oracle/dev_rule/test_policy.md` を読む。
- AI 管理ドキュメントを作りたくなる作業では `oracle/dev_rule/ai_docs.md` を読み、作成しない方針を守る。
- `oracle` と既存テストが衝突する場合は、勝手に整合させず、衝突箇所を人間へ返す。

## Workflow

1. 対象を局所化する。`rg` で関連シンボル、呼び出し元、既存テスト、エラーメッセージを拾う。
2. 既存コードと既存テストを読み、人間が切った変更範囲を越えずに済む実装方針を選ぶ。
3. high-level な仕様判断が必要か確認する。必要なら、その論点を明示して人間へ返す。
4. 最小差分で実装する。新しい抽象化は、重複や破綻を避けるために必要な場合だけ導入する。
5. 変更に対応するテストを追加または更新する。stub テストは既存 repository 状態や既存 `.tgbt/` に依存させない。
6. 変更対象に近い単位で `./.venv/bin/python -m pyright ...` と `./.venv/bin/python -m pytest ...` を実行する。
7. 実装結果、確認したコマンド、残る不確定事項をまとめて報告する。

## Escalation Rules

- 既存コード・既存テスト・必要な `oracle` 断片を読んでも正しい振る舞いを一意に決められないなら、人間に確認する。
- public interface の変更、依存追加、永続データ形式変更、複数モジュールをまたぐ再設計が必要なら、先に人間へ返す。
- 「この設計そのものが妥当か」を判断しない。必要なら、現状の問題点と low-level では吸収できない理由だけ整理して返す。
- 要求が広すぎる場合は、実装可能な単位へ分解したうえで、どこから先が high-level 判断かを明示する。

## Implementation Expectations

- Python コードでは型ヒントを必ず書き、`Any` の濫用を避ける。
- `from __future__ import annotations` は使わない。
- docstring は google style で書き、シグネチャを見れば分かる情報を冗長に繰り返さない。
- コードの意味的な小さいブロックごとに、そのブロックで何をしているかのコメントを日本語で書く。
- ログメッセージは英語にする。
- 相対 import を優先し、回避可能な循環参照を増やさない。
- オーバーエンジニアリングを避け、狙った修正に必要な最小限の責務追加に留める。

## Reporting Rules

- 何を実装または修正したかを先に一文で述べる。
- 追加・更新したテストと、実行した確認コマンドを添える。
- high-level 判断を避けるために据え置いた論点があれば明示する。
- 既存実装や既存テストから決め切れない点が残る場合は、未確定事項として人間確認を促す。

## Default execution pattern

1. 対象コードと既存テストを特定する
2. 必要な `oracle/dev_rule/*.md` と `oracle/tgbt_spec/*.md` だけ読む
3. 最小差分で実装する
4. 対応テストを追加・更新する
5. `.venv/bin/python -m pyright` と対象 `.venv/bin/python -m pytest` を実行する
6. 変更点、検証結果、未確定事項を報告する
