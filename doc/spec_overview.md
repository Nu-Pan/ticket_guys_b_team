# `ticket_guys_b_team` Specification Overview

## 1. 文書の目的

本書は `ticket_guys_b_team` の仕様群に対する入口文書である。

`ticket_guys_b_team` は、人間が要件を Plan として整理し、その Plan を起点に AI が必要 Ticket を逐次生成・実行・整理していくための CLI フロントエンドである。

本書自体は詳細仕様を網羅しない。詳細は各分割文書を参照する。

---

## 2. 現在の仕様文書構成

現在、一次参照先として扱う仕様文書は以下の 5 本である。

* `product_vision.md`
* `state_machine.md`
* `file_format.md`
* `cli_contract.md`
* `codex_cli_wrapper.md`

本書はそれらへの入口として機能する。

---

## 3. 全体像

本仕様の現在の中核概念は以下である。

* **Plan**: 人間がレビューしながら磨く仕様書兼実行方針
* **Ticket**: Plan の実行中に AI が必要に応じて作成する作業単位
* **Run**: 1 つの Plan に対して、Ticket 生成と Ticket 実行を反復するオーケストレーション
* **Codex CLI Wrapper**: `codex exec` 呼び出しを live / stub で抽象化する境界

重要な点は、MVP では独立した `approve` コマンドを持たないこと、そして `tgbt run --plan-id ...` が Plan の実行開始と Ticket オーケストレーションをまとめて担うことである。

---

## 4. 仕様文書の読み方

最初に本書で全体像を確認し、その後は関心に応じて以下の文書を参照する。

### 4.1 プロダクト背景と設計思想

* `product_vision.md`

用途:

* プロダクトの背景
* 解決したい問題
* 基本思想
* 人間と AI の役割分担
* 初期バージョンで重視する価値
* live / stub 導入の意義

### 4.2 状態遷移仕様

* `state_machine.md`

用途:

* Plan の状態遷移
* Ticket の状態遷移
* Ticket 依存の扱い
* `run` の反復モデルにおける遷移原則
* front matter を正本とする状態管理ルール

### 4.3 ファイル形式仕様

* `file_format.md`

用途:

* Plan file format
* Ticket file format
* Execution log JSONL format
* Codex session record file format
* Stub manifest file format
* ディレクトリ構造と命名規則

### 4.4 CLI 契約

* `cli_contract.md`

用途:

* CLI の責務
* エントリポイント
* コマンド体系
* 各コマンドの入力、出力、前提条件、失敗条件
* `codex_cli_mode` の扱い
* `run` の反復オーケストレーション契約

### 4.5 Codex CLI Wrapper 仕様

* `codex_cli_wrapper.md`

用途:

* `codex exec` 呼び出しの抽象化
* live / stub モードの定義
* live 記録の保存と再利用
* 1 wrapper 呼び出しにつき 1 replay source を与える規約
* 共通 request / result モデル
* オーケストレーション層との接続規約

---

## 5. 実装者向けの推奨参照順

### 5.1 CLI から先に作る場合

1. `cli_contract.md`
2. `state_machine.md`
3. `file_format.md`
4. `codex_cli_wrapper.md`
5. 必要に応じて `product_vision.md`

### 5.2 永続化層から先に作る場合

1. `file_format.md`
2. `state_machine.md`
3. `codex_cli_wrapper.md`
4. `cli_contract.md`
5. 必要に応じて `product_vision.md`

### 5.3 実行オーケストレーションから先に作る場合

1. `state_machine.md`
2. `cli_contract.md`
3. `file_format.md`
4. `codex_cli_wrapper.md`
5. 必要に応じて `product_vision.md`

---

## 6. 文書ごとの責務分離

各文書の責務は重複させすぎないことを原則とする。

* 本書は入口と参照案内のみを担う
* `product_vision.md` は背景・目的・設計思想を担う
* `state_machine.md` は状態遷移だけを担う
* `file_format.md` はファイル形式だけを担う
* `cli_contract.md` は CLI 契約だけを担う
* `codex_cli_wrapper.md` は Codex 呼び出し抽象化だけを担う

---

## 7. MVP での簡略化方針

MVP では、以下を意図的に削る。

* 独立した `approve` サブコマンド
* `status` / `state` のような状態集約サブコマンド
* review / integration / root といった補助 Ticket 型
* 自動受け入れゲートの厳密仕様

MVP では、Plan 更新・Ticket 生成・Ticket 実行・実行結果の要約保存・フォローアップ Ticket 生成の流れを最優先で固める。

---

## 8. 正本と監査証跡

現在状態の正本は Markdown front matter とする。

* Plan の現在状態は Plan file の front matter を正本とする
* Ticket の現在状態は Ticket file の front matter を正本とする
* execution log と session record は監査証跡であり、状態の正本ではない

front matter と監査証跡が衝突した場合、現在状態の解釈は front matter を優先する。

---

## 9. live / stub の読み分け

live / stub の差異は `codex_cli_mode` と、top-level `run` が各 wrapper 呼び出しへ stub source をどう配るかに限定する。

* `live`: 実際に `codex exec` を起動する
* `stub`: top-level `run` に与えた stub manifest に従い、各 wrapper 呼び出しへ単一 session record を割り当てて replay する

`stub` は「近い応答を返すモード」ではなく、明示指定した record 群の replay モードとして扱う。

