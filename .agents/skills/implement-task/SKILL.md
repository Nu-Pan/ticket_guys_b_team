---
name: implement-task
description: tgbt リポジトリで、人間が切ったスコープ内の具体的な実装修正を進めるためのスキル。Use when Codex needs to implement or fix a class, function, or localized behavior in tgbt itself, avoid adding tests for tgbt development, and avoid making product-level design decisions.
---

# Implement Task

## Overview

人間が定義した具体的な変更要求を、既存実装・必要な `oracle` 断片の範囲で安全に実装へ落とす。
AI は low-level な実装、局所的な整合調整、局所確認を担当し、抽象設計や仕様策定は人間へ返す。

## Non-Negotiables

- 最初に repository root の `AGENTS.md` を確認し、その制約を外さない。
- `README.md`、`oracle/**`、`memo/**`、`AGENTS.md` は編集しない。
- `README.md` と `memo/**` は閲覧もしない。
- `oracle/` は人間が管理する断片的な正本仕様であり、必要なときだけ参照し、完全仕様として未記載部分を補完しない。
- 参照した `oracle` の明示内容と実装が衝突する場合は、`oracle` を正本として扱い、衝突箇所を人間へ明示する。
- `docs/` のような AI 管理の中間ドキュメントは作成・更新しない。
- 人間が切っていない抽象設計、仕様策定、プロダクト判断を AI が引き取らない。
- 変更は最小限に留め、要求を満たすために必要な局所差分を優先する。
- tgbt 自体の開発では、テストを追加・更新しない。
- tgbt を使った別プロジェクトの開発方針と混同しない。tgbt 利用側の開発でテストを用意する方針は、この skill の対象外である。
- 実装だけでなく、変更内容に対応する局所確認まで責務に含める。

## Task Boundary

### この skill が扱うこと

- 既存設計の範囲で関数・クラス・分岐・入出力を実装または修正する。
- 既存の public interface を維持したまま、局所的な bug fix や整合調整を行う。
- 実装後に型チェックや import 確認など、テスト実装を伴わない局所確認を行う。

### この skill が扱わないこと

- プロダクトビジョン、要求定義、抽象アーキテクチャ設計を決めること。
- 複数の妥当な振る舞いがあり、既存コードや `oracle` 断片から決め切れない仕様判断を行うこと。
- 大規模リファクタ、責務分割の再設計、広範囲な public API 変更を独断で進めること。
- 「完全仕様」を AI が推定して未実装部分を広げること。
- tgbt 自体の開発でテストを新規作成・更新すること。

## Evidence Order

- まず user request を、どの関数・クラス・コマンド・入出力を触る話かに分解する。
- 挙動の根拠は、実装、必要な `oracle` 断片の順で集める。ただし正本判断は `oracle` の明示内容を優先する。
- `oracle` を読むときは `oracle/docs/ROUTING.md` と各階層の `ROUTING.md` から必要なファイルだけ辿る。
- Python 実装を触るときは `oracle/docs/dev_rule/ROUTING.md` で所在を確認してから `oracle/docs/dev_rule/python_coding.md` を読む。
- `.venv`、依存追加、ツール実行方法が論点なら `oracle/docs/dev_rule/ROUTING.md` で所在を確認してから `oracle/docs/dev_rule/environment.md` を読む。
- テスト方針や確認方法が論点なら `oracle/docs/dev_rule/ROUTING.md` で所在を確認してから `oracle/docs/dev_rule/test_policy.md` を読む。
- AI 管理ドキュメントを作りたくなる作業では `oracle/docs/dev_rule/ROUTING.md` で所在を確認してから `oracle/docs/dev_rule/ai_docs.md` を読み、作成しない方針を守る。
- 既存テストが残っていても、tgbt 自体の開発における新規テスト作成・更新の根拠にしない。
- この `ticket_guys_b_team` repository 上で `tgbt` を実行して自己開発させない。smoke test が必要で、実行場所や手順が既存コード・参照した `oracle` 断片から決め切れない場合は、人間へ確認する。
- unit test では live mode を使わない。

## Workflow

1. 対象を局所化する。`rg` で関連シンボル、呼び出し元、エラーメッセージを拾う。
2. 既存コードを読み、人間が切った変更範囲を越えずに済む実装方針を選ぶ。
3. high-level な仕様判断が必要か確認する。必要なら、その論点を明示して人間へ返す。
4. 最小差分で実装する。新しい抽象化は、重複や破綻を避けるために必要な場合だけ導入する。
5. tgbt 自体の開発では、変更に対応するテストを追加または更新しない。
6. 変更対象に近い単位で `./.venv/bin/python -m pyright ...` や import 確認など、テスト実装を伴わない確認を実行する。`tgbt` 自己実行も避ける。
7. 実装結果、確認したコマンド、残る不確定事項をまとめて報告する。

## Escalation Rules

- 既存コード・必要な `oracle` 断片を読んでも正しい振る舞いを一意に決められないなら、人間に確認する。
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
- テストを追加・更新していないことと、実行した確認コマンドを添える。
- high-level 判断を避けるために据え置いた論点があれば明示する。
- 既存実装や `oracle` 断片から決め切れない点が残る場合は、未確定事項として人間確認を促す。

## Default execution pattern

1. 対象コードを特定する
2. `oracle/docs/ROUTING.md` と各階層の `ROUTING.md` から、必要な `oracle/docs/dev_rule/*.md` と `oracle/docs/tgbt_spec/*.md` だけ読む
3. 最小差分で実装する
4. tgbt 自体の開発ではテストを追加・更新しない
5. `.venv/bin/python -m pyright` など、テスト実装を伴わない局所確認を実行する
6. 変更点、検証結果、未確定事項を報告する
