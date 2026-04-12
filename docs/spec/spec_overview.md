# `ticket_guys_b_team` Specification Overview

## 1. 文書の目的

本書は `ticket_guys_b_team` の仕様群に対する入口文書である。

`ticket_guys_b_team` は、人間が要件を Plan として整理し、その Plan を起点に AI が必要 Ticket を逐次生成・実行・整理していくための CLI フロントエンドである。

本書自体は詳細仕様を網羅しない。詳細は各分割文書を参照する。

本書および `docs/spec/*.md` は `ticket_guys_b_team` の正本仕様である。既存実装、既存テスト、過去メモがこれらと矛盾する場合でも、仕様判断は `docs/spec/*.md` を優先する。

---

## 2. 中核概念

本仕様の中核概念は以下である。

* **Plan**: 人間がレビューしながら磨く仕様書兼実行方針
* **Ticket**: Plan 実行中に AI が必要に応じて作成する作業単位
* **Run**: Ticket 生成と Ticket 実行を反復する top-level オーケストレーション
* **Codex CLI Wrapper**: `codex exec` を `plan` / `run` から抽象化する境界
* **Repo-Local Runtime**: `<repo-root>/.tgbt/.codex/config.toml` の required profile set と `.tgbt/instructions.md` に固定される Codex 実行環境

MVP では独立した `approve` コマンドを持たない。`tgbt run --plan-id ...` が Plan 実行開始を表す。

---

## 3. 仕様文書マップ

一次参照先として扱う仕様文書は以下の 8 本である。

* `product_vision.md`: 背景、解決したい問題、設計思想、価値、役割分担
* `common_invariants.md`: 文書横断の共通前提、artifact 区分、失敗契約、repo-local runtime の共通不変条件
* `state_machine.md`: Plan / Ticket の状態遷移、active Ticket、Ticket 依存、`run` の反復モデル
* `file_format.md`: Plan / Ticket file の形式、保存先、ID 規則、discovery 規則
* `operational_artifacts.md`: runtime file、execution log、env audit log、session record、counters、repository lock の形式
* `state_write_protocol.md`: canonical state の所有権、atomic write-replace、複数ファイル mutation の publish 規則
* `cli_contract.md`: CLI の責務、コマンド体系、各コマンドの入力、出力、前提条件、失敗条件
* `codex_cli_wrapper.md`: `codex exec` 呼び出しの抽象化、live / stub、strict replay、request / result モデル、業務レベル出力契約

責務分離の原則は次の通りとする。

* 本書は入口と参照案内のみを担う
* `product_vision.md` は背景と価値判断を担う
* `common_invariants.md` は横断前提のみを担う
* `state_machine.md` は状態遷移のみを担う
* `file_format.md` は Plan / Ticket file format のみを担う
* `operational_artifacts.md` は運用 artifact の形式のみを担う
* `state_write_protocol.md` は保存手順のみを担う
* `cli_contract.md` は CLI 契約のみを担う
* `codex_cli_wrapper.md` は wrapper 境界契約のみを担う

---

## 4. 推奨参照順

### 4.1 CLI から先に作る場合

1. `cli_contract.md`
2. `common_invariants.md`
3. `state_machine.md`
4. `file_format.md`
5. `operational_artifacts.md`
6. `state_write_protocol.md`
7. `codex_cli_wrapper.md`
8. 必要に応じて `product_vision.md`

### 4.2 永続化層から先に作る場合

1. `common_invariants.md`
2. `file_format.md`
3. `operational_artifacts.md`
4. `state_write_protocol.md`
5. `state_machine.md`
6. `codex_cli_wrapper.md`
7. `cli_contract.md`
8. 必要に応じて `product_vision.md`

### 4.3 実行オーケストレーションから先に作る場合

1. `state_machine.md`
2. `common_invariants.md`
3. `cli_contract.md`
4. `file_format.md`
5. `operational_artifacts.md`
6. `state_write_protocol.md`
7. `codex_cli_wrapper.md`
8. 必要に応じて `product_vision.md`

---

## 5. MVP で意図的に含めないもの

* 独立した `approve` サブコマンド
* `status` / `state` のような状態集約サブコマンド
* review / integration / root といった補助 Ticket 型
* 自動受け入れゲートの厳密仕様
* 並列 Ticket 実行
* transaction journal / preimage backup / rollback-first recovery
* stub manifest による任意 record 割り当て
* call purpose ごとの model / reasoning 最適化
* `tgbt` の Codex CLI 実行における skills / sub agent 利用
* 進捗不変ループ検出のような高度な停止判定

MVP では、Plan 草案生成、Ticket 生成、Ticket 実行、実行結果の要約保存、follow-up Ticket 生成の流れを最優先で固める。
