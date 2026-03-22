# `ticket_guys_b_team` CLI Contract

## 1. 文書の目的

本書は `ticket_guys_b_team` の CLI 契約を定義する。
対象は以下とする。

* CLI の責務
* エントリポイント
* コマンド体系
* 各コマンドの入力、出力、前提条件、失敗条件
* MVP の制約

本書は CLI 利用者および CLI 実装者向けの契約文書であり、詳細なファイル形式や状態遷移そのものは別文書を参照する。
Codex の live / stub 切り替えの詳細は `codex_cli_wrapper.md` を参照する。

---

## 2. 基本方針

* 人間が触る主要インターフェースは CLI とする
* CLI は内部フレームワーク概念を隠蔽し、業務概念を提供する
* 人間は Plan、Ticket、run という概念で操作できるべきである
* 内部のエージェント実行基盤やワークフローエンジンの詳細は CLI から直接露出しない
* Codex 呼び出しは wrapper 経由でのみ行う
* 失敗時も、原因と次に取るべき行動が短く理解できる出力を返す
* MVP では集約ビューのための `status` / `state` サブコマンドを設けない

---

## 3. エントリポイント

正規の CLI 名は `tgbt` とする。

起動導線として以下を提供する。

```text
bin/tgbt
```

利用者は `bin/` を `$PATH` に追加したうえで `tgbt` を実行する。

例:

```bash
tgbt plan "ここに要件を書く"
```

---

## 4. コマンド体系

CLI は最低限以下のコマンドを提供する。

* `tgbt plan`
* `tgbt approve`
* `tgbt run`

MVP では `ticket` を独立コマンドにしない。`approve` が承認時に必要な worker Ticket を生成または更新する。
MVP では `status` / `state` / `review-queue` / `artifacts` を導入しない。

---

## 5. 共通契約

### 5.1 終了コード

* 正常終了時は 0 を返す
* 以下の異常系は非 0 を返す

  * 仕様不足
  * 承認不足
  * 依存未解決
  * 検証失敗
  * 実行失敗
  * 入力不正
  * stub record 指定不備

### 5.2 エラー出力方針

エラー表示は少なくとも以下を短く示す。

* 原因
* 影響範囲
* 次に取るべき行動

例:

```text
ERROR: --stub-record is required in stub mode
Impact: worker execution was not started
Next: rerun with --codex-cli-mode stub --stub-record <path>
```

### 5.3 永続化方針

* 成功時も失敗時も、可能な限り状態更新とログ保存を行う
* 実行時に起きた事実はログへ保存する
* worker 実行では codex session record を保存する
* ログ保存自体に失敗した場合も、その失敗を標準エラー等へ可能な限り残す

### 5.4 出力方針

* 人間向けの簡潔な標準出力を返す
* 機械処理向けには JSON 出力を将来拡張してよい
* MVP では人間可読性を優先するが、ログと成果物パスが追跡できることを維持する
* 各コマンドは、更新または参照すべきファイルのパスを返す

### 5.5 モード用語

本仕様で扱う実行モードは `codex_cli_mode` のみである。

#### `codex_cli_mode`

worker Ticket 内部で Codex をどう扱うかを表す。

* `live`
* `stub`

`run` は常に実行コマンドであり、dry-run / preflight / validate は現時点では提供しない。

---

## 6. `plan` コマンド

### 6.1 目的

人間要望から仕様書兼実行計画書の草案を生成または更新する。

### 6.2 入力

以下のいずれかを受け付ける。

* 自然言語要求
* 既存 `plan_id` と追記指示

例:

```bash
tgbt plan "CLI で plan / approve / run を扱えるようにしたい"
```

```bash
tgbt plan --plan-id plan-20260321-001 "検証戦略を追記する"
```

### 6.3 出力

* `artifacts/plans/<plan_id>.md` を生成または更新する
* 実行結果として少なくとも `plan_id` と保存先を表示する

例:

```text
Created: artifacts/plans/plan-20260321-001.md
Status: draft
```

### 6.4 状態遷移

* 新規生成時は `draft`
* 更新時も `draft`
* このコマンド単体では `approved` に遷移しない
* `approved` 済み Plan を更新した場合も `draft` に戻す

### 6.5 失敗条件

* 出力先へ書き込めない
* 入力が空である
* 対象 `plan_id` が見つからない
* front matter 更新に失敗した

### 6.6 MVP 制約

* 必須セクションを並べたテンプレート草案生成に留める
* 要望内容の深い自動解釈や高度な要件抽出は未実装でよい

---

## 7. `approve` コマンド

### 7.1 目的

指定した Plan を `approved` に遷移させる。
承認成功時には、その Plan に対応する worker Ticket を生成または更新する。

### 7.2 入力

* `plan_id`

例:

```bash
tgbt approve plan-20260321-001
```

### 7.3 出力

* 更新後状態
* 生成または更新された Ticket file の保存先
* 不足がある場合は不足理由一覧

例:

```text
Plan: plan-20260321-001
Status: approved
Ticket: artifacts/tickets/worker-001.md
```

または

```text
Approval rejected
Missing:
- 検証戦略
```

### 7.4 遷移ルール

* `draft` の Plan のみ `approved` にできる
* 承認成功時は worker Ticket を生成または更新する
* 生成または更新される Ticket の既定状態は `todo` とする

### 7.5 承認前バリデーション

最低限以下を確認する。

* 必須項目が存在すること
* 未確定事項について、次フェーズ進行可否が明示されていること
* 検証戦略が空でないこと

### 7.6 失敗条件

* Plan file が存在しない
* 現在状態から要求遷移が許可されていない
* 必須項目が不足している
* Ticket file の生成または更新に失敗した

---

## 8. `run` コマンド

### 8.1 目的

指定した worker Ticket を実行する。

### 8.2 入力

* `ticket_id`
* `--codex-cli-mode {live|stub}`
* `--stub-record <path>` (`stub` のとき必須)

例:

```bash
tgbt run worker-001
```

```bash
tgbt run worker-001 --codex-cli-mode stub --stub-record artifacts/codex/worker-001-run-0001-call-0001.json
```

### 8.3 前提条件

* Ticket が存在すること
* Ticket が worker であること
* 対応 Plan が `approved` であること
* 依存 Ticket がすべて required state を満たしていること
* Ticket 状態が `todo` であること

### 8.4 出力

* 更新後 Ticket 状態
* Ticket file の保存先
* run log の保存先
* codex session record の保存先
* 次に見るべきものの短い案内

例:

```text
Ticket: worker-001
Status: blocked
PlanFile: artifacts/plans/plan-20260321-001.md
TicketFile: artifacts/tickets/worker-001.md
Log: artifacts/logs/worker-001-run-0003.jsonl
CodexSession: artifacts/codex/worker-001-run-0003-call-0001.json
Next: open the ticket file and log
```

### 8.5 実行ルール

* 実行開始時に `todo -> running` へ更新する
* wrapper 実行後に自動受け入れゲートを実行する
* 成功なら `done` にする
* 判定不能または人間判断待ちなら `blocked` にする
* 明確な失敗なら `failed` にする

### 8.6 失敗条件

* Ticket file が存在しない
* Ticket が worker でない
* Plan が `approved` でない
* 依存未解決
* `stub` なのに `--stub-record` が無い
* wrapper 実行失敗
* ログ保存失敗

### 8.7 MVP 制約

* 並列実行は扱わない
* 1 回の `run` は 1 Ticket のみを扱う
* 人間向けの集約一覧出力は持たない
