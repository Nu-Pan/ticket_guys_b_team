# `ticket_guys_b_team` Specification Overview

## 1. 文書の目的

本書は `ticket_guys_b_team` の仕様群に対する入口文書である。

`ticket_guys_b_team` は、人間が要件を Plan として整理し、その Plan を起点に AI が必要 Ticket を逐次生成・実行・整理していくための CLI フロントエンドである。

本書自体は詳細仕様を網羅しない。詳細は各分割文書を参照する。

---

## 2. 全体像

本仕様の現在の中核概念は以下である。

* **Plan**: 人間がレビューしながら磨く仕様書兼実行方針。`plan_id` に加えて `plan_revision` を持つ
* **Ticket**: Plan 実行中に AI が必要に応じて作成する作業単位。各 Ticket は特定の `plan_revision` に属する
* **Run**: 1 つの Plan に対して、Ticket 生成と Ticket 実行を反復するオーケストレーション
* **Repository Lock**: 同一 repository に対する state mutation を 1 本に直列化する排他制御
* **Codex CLI Wrapper**: `codex exec` 呼び出しを live / stub で抽象化し、構造化された業務出力を返す境界

重要な点は、MVP では独立した `approve` コマンドを持たないこと、そして `tgbt run --plan-id ...` が Plan の実行開始と Ticket オーケストレーションをまとめて担うことである。

また、本仕様では run と wrapper 呼び出しを **直列実行のみ** とし、並列 Ticket 実行は採用しない。

---

## 3. 仕様文書マップ

現在、一次参照先として扱う仕様文書は以下の 5 本である。

* `product_vision.md`: 背景、解決したい問題、設計思想、人間と AI の役割分担、MVP で重視する価値
* `state_machine.md`: Plan / Ticket の状態遷移、active Ticket の定義、Ticket 依存、`run` の反復モデル、`settled` の意味
* `file_format.md`: Plan / Ticket / log / session record / counters / repository lock の形式、保存先、命名規則
* `cli_contract.md`: CLI の責務、コマンド体系、各コマンドの入力、出力、前提条件、失敗条件
* `codex_cli_wrapper.md`: `codex exec` 呼び出しの抽象化、live / stub、strict replay、request / result モデル、業務レベル出力契約

責務分離の原則は次の通りとする。

* 本書は入口と参照案内のみを担う
* `product_vision.md` は背景・目的・設計思想を担う
* `state_machine.md` は状態遷移と active Ticket の意味を担う
* `file_format.md` はファイル形式だけを担う
* `cli_contract.md` は CLI 契約だけを担う
* `codex_cli_wrapper.md` は Codex 呼び出し抽象化と出力契約だけを担う

---

## 4. 実装者向けの推奨参照順

### 4.1 CLI から先に作る場合

1. `cli_contract.md`
2. `state_machine.md`
3. `file_format.md`
4. `codex_cli_wrapper.md`
5. 必要に応じて `product_vision.md`

### 4.2 永続化層から先に作る場合

1. `file_format.md`
2. `state_machine.md`
3. `codex_cli_wrapper.md`
4. `cli_contract.md`
5. 必要に応じて `product_vision.md`

### 4.3 実行オーケストレーションから先に作る場合

1. `state_machine.md`
2. `cli_contract.md`
3. `file_format.md`
4. `codex_cli_wrapper.md`
5. 必要に応じて `product_vision.md`

---

## 5. MVP での簡略化方針

MVP では、以下を意図的に削る。

* 独立した `approve` サブコマンド
* `status` / `state` のような状態集約サブコマンド
* review / integration / root といった補助 Ticket 型
* 自動受け入れゲートの厳密仕様
* 並列 Ticket 実行
* stub manifest による任意 record 割り当て
* call purpose ごとの model / reasoning 最適化
* 進捗不変ループ検出のような高度な停止判定

MVP では、Plan 更新・Ticket 生成・Ticket 実行・実行結果の要約保存・フォローアップ Ticket 生成の流れを最優先で固める。

---

## 6. 共通前提

現在状態の正本は Markdown front matter とする。

* Plan の現在状態は Plan file の front matter を正本とする
* Ticket の現在状態は Ticket file の front matter を正本とする
* `artifacts/system/counters.json` は採番の正本とする
* execution log と session record は監査証跡であり、状態の正本ではない

front matter と監査証跡が衝突した場合、現在状態の解釈は front matter を優先する。

同一 repository に対する state mutation は、repository lock によって直列化される。

* `tgbt run` は repository lock を取得してから開始する
* 既存 Plan を更新する `tgbt plan --plan-id ...` も repository lock を取得してから実行する
* MVP では、同一 repository に対して同時に実行可能な state-mutating `tgbt` は 1 本だけである

active Ticket は、対象 Plan の **現在 `plan_revision`** に属し、かつ `artifacts/tickets/` に現存する Ticket file 集合を意味する。

* active Ticket には `todo` / `running` / `done` / `settled` を含める
* 過去 revision の Ticket は、同じ directory に残っていても active ではない
* 削除または退避された Ticket は active ではない

live / stub の差異は `codex_cli_mode` と session record の取得経路に限定する。

* `live`: 実際に `codex exec` を起動する
* `stub`: strict replay source を読み込み、redaction 済みの構造化 result を再生する

`stub` は「近い応答を返すモード」ではなく、**実行開始前の状態を復元したうえで、同一の run / call 系列を再生するモード**として扱う。
