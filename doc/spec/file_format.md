# `ticket_guys_b_team` File Format Specification

## 1. 文書の目的

本書は `ticket_guys_b_team` が読み書きする主要ファイルの形式を定義する。

対象は以下とする。

* Plan file
* Ticket file
* Execution log file
* Codex session record file
* Counter state file
* Repository lock file

本書はファイル形式と保存規約に集中し、CLI 契約や詳細な状態遷移は扱わない。

---

## 2. 基本方針

* 主要オブジェクトはファイルとして永続化する
* 主要ファイルは人間可読な形式を優先する
* 機械処理対象のログは JSON Lines または JSON を用いる
* 生成物は一貫した命名規則とディレクトリ構造に従う
* 実行失敗時も可能な限りファイルを保存する
* live 実行の記録は stub 実行にそのまま転用可能でなければならない
* 現在状態の正本は Markdown front matter とする
* `artifacts/system/counters.json` は採番の正本とする
* execution log と session record は監査証跡であり、状態の正本ではない

front matter と監査証跡が衝突した場合、現在状態の解釈は front matter を優先する。

---

## 3. 既定ディレクトリ構造

成果物の既定配置は `artifacts/` 配下とする。

```text
artifacts/
  plans/
  tickets/
  logs/
  codex/
  system/
    counters.json
    locks/
      repository.lock.json
```

各ディレクトリの役割は以下の通りとする。

* `artifacts/plans/`: Plan file
* `artifacts/tickets/`: Ticket file
* `artifacts/logs/`: 実行ログ JSONL
* `artifacts/codex/`: Codex CLI wrapper の session record
* `artifacts/system/counters.json`: 採番の正本
* `artifacts/system/locks/`: repository 全体の state mutation を禁止する lock artifact

---

## 4. 共通ルール

### 4.1 エンコーディング

* すべてのテキストファイルは UTF-8 を前提とする
* BOM は付与しないことを推奨する

### 4.2 改行

* 改行コードは LF を推奨する
* 実装上必要であれば読み込み時に CRLF も許容してよい

### 4.3 時刻表現

* 日時はタイムゾーン付き ISO 8601 文字列を推奨する
* 例: `2026-03-21T13:45:00+09:00`

### 4.4 識別子

* `plan_id` は一意でなければならない
* `plan_revision` は同一 `plan_id` の中で単調増加しなければならない
* `ticket_id` は一意でなければならない
* `run_id` は 1 回の top-level `run` ごとに一意でなければならない
* `codex_call_id` は 1 回の wrapper 呼び出しごとに一意でなければならない

### 4.5 採番規則

#### `plan_id`

推奨形式:

```text
plan-YYYYMMDD-NNN
```

#### `plan_revision`

同一 `plan_id` に対して、1 から始まる単調増加整数を推奨する。

要件:

* Plan 更新時に増加する
* 過去 revision を再利用してはならない
* 既存 Ticket の破棄や退避で巻き戻してはならない

#### `ticket_id`

推奨形式:

```text
worker-NNNN
```

要件:

* 1 から単調増加で採番する
* 既存番号を再利用してはならない
* ある Plan の Ticket を破棄しても番号は巻き戻してはならない

#### `run_id`

推奨形式:

```text
run-NNNN
```

#### `codex_call_id`

推奨形式:

```text
call-NNNN
```

### 4.6 YAML front matter

* Markdown ベースの主要ファイルは YAML front matter を先頭に持つ
* YAML front matter は `---` で開始し、`---` で終了する

---

## 5. Plan File Format

### 5.1 保存先

```text
artifacts/plans/<plan_id>.md
```

1 Plan につき 1 ファイルとする。

### 5.2 必須メタデータ

Plan file の YAML front matter は最低限以下を含む。

* `plan_id`
* `plan_revision`
* `title`
* `status`
* `created_at`
* `updated_at`

`status` は以下のいずれかでなければならない。

* `draft`
* `running`
* `settled`

### 5.3 推奨メタデータ

必要に応じて以下を追加してよい。

* `last_run_id`
* `settled_at`
* `closure_reason`

### 5.4 本文構造

Plan file 本文は以下のセクションをこの順序で含む。

1. 目的
2. スコープ外
3. 成果物
4. 制約
5. 受け入れ条件
6. 未確定事項
7. 想定リスク
8. 実行方針

### 5.5 例

```md
---
plan_id: plan-20260321-001
plan_revision: 1
title: CLI 初期実装
status: draft
created_at: 2026-03-21T10:00:00+09:00
updated_at: 2026-03-21T10:00:00+09:00
---

# 目的
...

# スコープ外
...

# 成果物
...

# 制約
...

# 受け入れ条件
...

# 未確定事項
...

# 想定リスク
...

# 実行方針
...
```

---

## 6. Ticket File Format

### 6.1 保存先

```text
artifacts/tickets/<ticket_id>.md
```

1 Ticket につき 1 ファイルとする。

### 6.2 必須メタデータ

Ticket file の YAML front matter は最低限以下を含む。

* `ticket_id`
* `plan_id`
* `plan_revision`
* `status`
* `created_at`
* `updated_at`

`status` は以下のいずれかでなければならない。

* `todo`
* `running`
* `done`
* `settled`

### 6.3 推奨メタデータ

必要に応じて以下を追加してよい。

* `ticket_kind`
* `depends_on`
* `execution_outcome`
* `settled_at`

`ticket_kind` の例:

* `implementation`
* `check`
* `refactor`
* `cleanup`
* `other`

`execution_outcome` の例:

* `succeeded`
* `failed`
* `needs_followup`

### 6.4 `depends_on` の表現

依存は `ticket_id` と `required_state` の組で表現する。

例:

```yaml
depends_on:
  - ticket_id: worker-0001
    required_state: settled
```

`required_state` は MVP では **`settled` のみ許可**する。
`todo` / `running` / `done` は不正値として validation で拒否しなければならない。

### 6.5 本文構造

Ticket file 本文は以下のセクションをこの順序で含む。

1. Title
2. Purpose
3. Dependencies
4. Execution Instructions
5. Run Summary
6. Follow-up Notes
7. Artifacts

### 6.6 Run Summary の扱い

`Run Summary` には、最新の agent 実行結果の短いサマリーを追記または更新する。

ここには少なくとも以下を残せることが望ましい。

* 実行の要点
* 成功 / 失敗の要約
* 主要成果物
* follow-up が必要かどうか

### 6.7 Artifacts の推奨記載

worker Ticket では、少なくとも以下を記載できることが望ましい。

```md
# Artifacts
- artifacts/logs/plan-20260321-001-run-0003.jsonl
- artifacts/codex/worker-0002-run-0003-call-0002-ticket_execution.json
```

### 6.8 例

```md
---
ticket_id: worker-0002
plan_id: plan-20260321-001
plan_revision: 1
status: todo
ticket_kind: implementation
depends_on:
  - ticket_id: worker-0001
    required_state: settled
created_at: 2026-03-21T10:30:00+09:00
updated_at: 2026-03-21T10:30:00+09:00
---

# Title
CLI に `run --plan-id` を追加する

# Purpose
Plan 実行の起点となるコマンドを実装する。

# Dependencies
- worker-0001 must be settled

# Execution Instructions
...

# Run Summary
...

# Follow-up Notes
...

# Artifacts
...
```

---

## 7. Execution Log File Format

### 7.1 保存先

推奨保存先:

```text
artifacts/logs/<plan_id>-<run_id>.jsonl
```

1 top-level `run` につき 1 ファイルを推奨する。

### 7.2 1 行 1 event

execution log は JSON Lines とし、1 行が 1 event を表す。

### 7.3 必須フィールド

各 event は最低限以下を含むことが望ましい。

* `timestamp`
* `event_type`
* `plan_id`
* `plan_revision`
* `run_id`

### 7.4 推奨フィールド

必要に応じて以下を追加してよい。

* `ticket_id`
* `codex_call_id`
* `call_purpose`
* `codex_cli_mode`
* `session_record_path`
* `replayed_from`
* `message`
* `limit_name`

### 7.5 `event_type` の例

* `run_started`
* `ticket_planning_started`
* `tickets_created`
* `ticket_execution_started`
* `ticket_execution_finished`
* `ticket_settled`
* `run_finished`
* `run_failed`
* `run_limit_exceeded`

### 7.6 例

```json
{"timestamp":"2026-03-21T11:00:00+09:00","event_type":"run_started","plan_id":"plan-20260321-001","plan_revision":1,"run_id":"run-0003"}
{"timestamp":"2026-03-21T11:00:10+09:00","event_type":"ticket_execution_started","plan_id":"plan-20260321-001","plan_revision":1,"run_id":"run-0003","ticket_id":"worker-0001","codex_call_id":"call-0002","call_purpose":"ticket_execution"}
```

---

## 8. Codex Session Record File Format

### 8.1 保存先

推奨保存先:

```text
artifacts/codex/<scope>-<run_id>-<codex_call_id>-<call_purpose>.json
```

`<scope>` は **決定的に** 以下とする。

* `ticket_id != null` のとき `<scope> = <ticket_id>`
* `ticket_id == null` のとき `<scope> = <plan_id>`

例:

```text
artifacts/codex/plan-20260321-001-run-0003-call-0001-ticket_planning.json
artifacts/codex/worker-0001-run-0003-call-0002-ticket_execution.json
```

### 8.2 目的

session record は 1 回の wrapper 呼び出しの request / response を保存する JSON artifact である。

### 8.3 必須フィールド

最低限以下を含むこと。

* `schema_version`
* `plan_id`
* `plan_revision`
* `ticket_id` (`ticket` に紐づかない call では `null` 可)
* `run_id`
* `codex_call_id`
* `call_purpose`
* `codex_cli_mode`
* `request`
* `result`
* `saved_at`

### 8.4 `call_purpose` の値

MVP では以下のみを使用する。

* `ticket_planning`
* `ticket_execution`
* `followup_planning`

### 8.5 `request` に含めることが望ましい項目

* `plan_id`
* `plan_revision`
* `ticket_id`
* `run_id`
* `codex_call_id`
* `call_purpose`
* `codex_cli_mode`
* `cwd`
* `prompt_text`
* `model`
* `reasoning_effort`

ここで `request` は **保存用 canonical request** とする。
すなわち、strict replay 比較に使われる正規化・redaction 後の値を保存する。
raw request を lossless に保存することは要件としない。

### 8.6 `result` に含めることが望ましい項目

* `plan_id`
* `plan_revision`
* `ticket_id`
* `run_id`
* `codex_call_id`
* `call_purpose`
* `codex_cli_mode`
* `returncode`
* `stdout`
* `stderr`
* `last_message_text`
* `business_output`
* `generated_artifacts`
* `stop_reason`
* `session_record_path`
* `replayed_from`
* `redaction_report`

`business_output` は、`call_purpose` ごとの業務レベル出力契約に従って parse / validate 済みの構造化 payload を保持する。

### 8.7 要件

* live 実行の session record は、そのまま stub source として利用できること
* stub 実行時に元 record を破壊してはならないこと
* strict replay では、source record の `request` と current request を **同じ正規化・redaction 関数**に通した結果が、`codex_cli_mode` と `stub_record_path` を除いて一致しなければならないこと
* `last_message_text` は、3 つの call purpose については redaction 後 `business_output` の canonical JSON serialization であることが望ましい

---

## 9. Counter State File Format

### 9.1 保存先

```text
artifacts/system/counters.json
```

### 9.2 目的

`ticket_id` / `run_id` / `codex_call_id` の単調増加採番を保証するための正本である。

### 9.3 必須フィールド

最低限以下を含むこと。

* `next_ticket_seq`
* `next_run_seq`
* `next_codex_call_seq`
* `updated_at`

### 9.4 例

```json
{
  "next_ticket_seq": 12,
  "next_run_seq": 4,
  "next_codex_call_seq": 27,
  "updated_at": "2026-03-21T11:10:00+09:00"
}
```

### 9.5 要件

* 採番はこの file を正本として行うこと
* `next_*` は **unsigned 64-bit 整数範囲**で扱わなければならない
* 実装は少なくとも `1 .. 18446744073709551615` の範囲を扱えなければならない
* 途中クラッシュや後続失敗による欠番を許容する
* 一度 `next_*` を進めて永続化したら、その番号は消費済みとみなし、巻き戻してはならない
* `ticket_id` は対応する Ticket file 作成を試みる直前に採番してよい
* `run_id` は repository lock 取得後、最初の run-scoped artifact を作る前に採番しなければならない
* `codex_call_id` は wrapper 実行を試みる直前に採番してよい
* repository lock により、この file の更新は state-mutating `tgbt` 間で直列化されること
* strict replay では、この file を過去 run 開始前の状態へ戻すことで同じ `run_id` / `codex_call_id` 系列を再現できること

---

## 10. Repository Lock File Format

### 10.1 保存先

```text
artifacts/system/locks/repository.lock.json
```

### 10.2 目的

repository 全体に対する同時 state mutation を禁止するための lock artifact である。

### 10.3 必須フィールド

最低限以下を含むこと。

* `command_name`
* `acquired_at`

### 10.4 推奨フィールド

必要に応じて以下を追加してよい。

* `plan_id`
* `run_id`
* `pid`
* `hostname`
* `command_line`

### 10.5 例

```json
{
  "command_name": "run",
  "plan_id": "plan-20260321-001",
  "run_id": "run-0003",
  "acquired_at": "2026-03-21T11:00:00+09:00"
}
```

### 10.6 要件

* lock 取得は、最終 lock path に対する **原子的な non-overwrite create** で行わなければならない
* 「存在確認してから作る」方式は禁止する
* 実装は `O_CREAT|O_EXCL` 相当、または同等の排他意味論を持つ OS primitive を使用しなければならない
* 既存 lock が存在する場合、新しい state-mutating `tgbt` は失敗しなければならない
* `run` 開始時に lock を取得し、終了時に解放すること
* 既存 Plan を更新する `plan --plan-id ...` も、破棄・退避・front matter 更新を行う前に lock を取得しなければならない
* MVP では stale lock の自動判定・自動回収は行わない
* stale lock の手動削除運用を許容してよい
