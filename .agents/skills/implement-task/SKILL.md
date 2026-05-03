---
name: implement-task
description: Implement a scoped low-level change in tgbt. Use for localized function, class, command, or behavior changes that avoid tests, broad refactors, and product-level decisions.
---

# Implement Task

## Overview

人間が定義した具体的な変更要求を、既存実装と必要な `<tgbt-root>/oracle` 断片の範囲で実装する。
AI の責務は low-level なコード変更、局所的な整合調整、局所確認までに限る。

## Guardrails

- 最初に `<tgbt-root>/AGENTS.md` を確認し、repo 固有の読み取り・編集制約を外さない。
- 変更は要求を満たすために必要な局所差分へ留める。
- tgbt 自体の開発では、テストを追加・更新しない。
- AI 管理の中間ドキュメントや作業ログを作成・更新しない。
- `<tgbt-root>/oracle` は必要なときだけ参照し、未記載仕様を補完しない。
- 参照した `<tgbt-root>/oracle` と実装が衝突する場合は、`<tgbt-root>/oracle` を正本として扱い、衝突箇所を人間へ返す。

## Scope

扱う作業:

- 既存設計の範囲で関数・クラス・分岐・入出力を実装または修正する。
- 既存 public interface を維持したまま、局所的な bug fix や整合調整を行う。
- 実装後に型チェックや import 確認など、テスト実装を伴わない局所確認を行う。

扱わない作業:

- プロダクトビジョン、要求定義、抽象アーキテクチャ設計を決める。
- 複数の妥当な振る舞いがあり、既存コードや `<tgbt-root>/oracle` 断片から決め切れない仕様判断を行う。
- 大規模リファクタ、責務分割の再設計、広範囲な public API 変更を進める。
- tgbt 自体の開発でテストを新規作成・更新する。

## Evidence Order

- まず user request を、触る関数・クラス・コマンド・入出力へ分解する。
- 挙動の根拠は既存実装から集め、必要な場合だけ `<tgbt-root>/oracle` を読む。
- `<tgbt-root>/oracle` を読むときは `<tgbt-root>/oracle/docs/ROUTING.md` と各階層の `ROUTING.md` から必要なファイルだけ辿る。
- Python 実装を触るときは `<tgbt-root>/oracle/docs/dev_rule/ROUTING.md` で所在を確認してから `<tgbt-root>/oracle/docs/dev_rule/python_coding.md` を読む。
- `<tgbt-root>/.venv`、依存追加、ツール実行方法が論点なら `<tgbt-root>/oracle/docs/dev_rule/ROUTING.md` で所在を確認してから `<tgbt-root>/oracle/docs/dev_rule/environment.md` を読む。
- テスト方針や確認方法が論点なら `<tgbt-root>/oracle/docs/dev_rule/ROUTING.md` で所在を確認してから `<tgbt-root>/oracle/docs/dev_rule/test_policy.md` を読む。
- 正本判断は `<tgbt-root>/oracle` の明示内容を優先する。ただし `<tgbt-root>/oracle` を完全仕様として扱わない。

## Workflow

1. 対象を局所化する。`rg` で関連シンボル、呼び出し元、エラーメッセージを拾う。
2. 既存コードを読み、人間が切った変更範囲を越えずに済む実装方針を選ぶ。
3. high-level な仕様判断、public interface 変更、依存追加、永続データ形式変更、複数モジュールをまたぐ再設計が必要なら、人間へ返す。
4. 最小差分で実装する。新しい抽象化は、重複や破綻を避けるために必要な場合だけ導入する。
5. テストを追加・更新せず、変更対象に近い単位で `<tgbt-root>/.venv/bin/python -m pyright ...` や import 確認などを実行する。
6. この `<tgbt-root>` 上で `tgbt` を実行して自己開発させない。smoke test が必要で手順を一意に決められない場合は、人間へ確認する。

## Reporting Rules

- 何を実装または修正したかを先に一文で述べる。
- テストを追加・更新していないことと、実行した確認コマンドを添える。
- high-level 判断を避けるために据え置いた論点や、既存実装・`<tgbt-root>/oracle` から決め切れない点があれば明示する。
