---
name: implement-task
description: Implement a scoped low-level change in tgbt. Use when modifying a specified function, class, or localized behavior without adding tests or making product-level design decisions.
---

# Implement Task

## Overview

人間が定義した具体的な変更要求を、既存実装・必要な `<tgbt-root>/oracle` 断片の範囲で安全に実装へ落とす。
AI は low-level な実装、局所的な整合調整、局所確認を担当し、抽象設計や仕様策定は人間へ返す。

## Guardrails

- 最初に `<tgbt-root>/AGENTS.md` を確認し、repo 固有の読み取り・編集制約を外さない。
- `<tgbt-root>/oracle` は必要なときだけ参照し、完全仕様として未記載部分を補完しない。
- 参照した `<tgbt-root>/oracle` の明示内容と実装が衝突する場合は、`<tgbt-root>/oracle` を正本として扱い、衝突箇所を人間へ明示する。
- 人間が切っていない抽象設計、仕様策定、プロダクト判断を AI が引き取らない。
- 変更は要求を満たすために必要な局所差分へ留める。
- tgbt 自体の開発では、テストを追加・更新しない。
- 実装だけでなく、変更内容に対応する局所確認まで責務に含める。
- AI 管理の中間ドキュメントや作業ログを作成・更新しない。

## Task Boundary

### 扱う

- 既存設計の範囲で関数・クラス・分岐・入出力を実装または修正する。
- 既存の public interface を維持したまま、局所的な bug fix や整合調整を行う。
- 実装後に型チェックや import 確認など、テスト実装を伴わない局所確認を行う。

### 扱わない

- プロダクトビジョン、要求定義、抽象アーキテクチャ設計を決めること。
- 複数の妥当な振る舞いがあり、既存コードや `<tgbt-root>/oracle` 断片から決め切れない仕様判断を行うこと。
- 大規模リファクタ、責務分割の再設計、広範囲な public API 変更を独断で進めること。
- tgbt 自体の開発でテストを新規作成・更新すること。

## Evidence Order

- まず user request を、どの関数・クラス・コマンド・入出力を触る話かに分解する。
- 挙動の根拠は、実装、必要な `<tgbt-root>/oracle` 断片の順で集める。ただし正本判断は `<tgbt-root>/oracle` の明示内容を優先する。
- `<tgbt-root>/oracle` を読むときは `<tgbt-root>/oracle/docs/ROUTING.md` と各階層の `ROUTING.md` から必要なファイルだけ辿る。
- Python 実装を触るときは `<tgbt-root>/oracle/docs/dev_rule/ROUTING.md` で所在を確認してから `<tgbt-root>/oracle/docs/dev_rule/python_coding.md` を読む。
- `<tgbt-root>/.venv`、依存追加、ツール実行方法が論点なら `<tgbt-root>/oracle/docs/dev_rule/ROUTING.md` で所在を確認してから `<tgbt-root>/oracle/docs/dev_rule/environment.md` を読む。
- テスト方針や確認方法が論点なら `<tgbt-root>/oracle/docs/dev_rule/ROUTING.md` で所在を確認してから `<tgbt-root>/oracle/docs/dev_rule/test_policy.md` を読む。
- この `<tgbt-root>` 上で `tgbt` を実行して自己開発させない。smoke test が必要で、実行場所や手順が既存コード・参照した `<tgbt-root>/oracle` 断片から決め切れない場合は、人間へ確認する。
- 既存テストが残っていても、tgbt 自体の開発における新規テスト作成・更新の根拠にしない。unit test では live mode を使わない。

## Workflow

1. 対象を局所化する。`rg` で関連シンボル、呼び出し元、エラーメッセージを拾う。
2. 既存コードを読み、人間が切った変更範囲を越えずに済む実装方針を選ぶ。
3. high-level な仕様判断が必要か確認する。必要なら、その論点を明示して人間へ返す。
4. 最小差分で実装する。新しい抽象化は、重複や破綻を避けるために必要な場合だけ導入する。
5. tgbt 自体の開発では、変更に対応するテストを追加または更新しない。
6. 変更対象に近い単位で `<tgbt-root>/.venv/bin/python -m pyright ...` や import 確認など、テスト実装を伴わない確認を実行する。`tgbt` 自己実行も避ける。
7. 実装結果、確認したコマンド、残る不確定事項をまとめて報告する。

## Escalation Rules

- 既存コード・必要な `<tgbt-root>/oracle` 断片を読んでも正しい振る舞いを一意に決められないなら、人間に確認する。
- public interface の変更、依存追加、永続データ形式変更、複数モジュールをまたぐ再設計が必要なら、先に人間へ返す。
- 「この設計そのものが妥当か」を判断しない。必要なら、現状の問題点と low-level では吸収できない理由だけ整理して返す。
- 要求が広すぎる場合は、実装可能な単位へ分解したうえで、どこから先が high-level 判断かを明示する。

## Reporting Rules

- 何を実装または修正したかを先に一文で述べる。
- テストを追加・更新していないことと、実行した確認コマンドを添える。
- high-level 判断を避けるために据え置いた論点があれば明示する。
- 既存実装や `<tgbt-root>/oracle` 断片から決め切れない点が残る場合は、未確定事項として人間確認を促す。
