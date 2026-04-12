# `ticket_guys_b_team` File Format Specification

## 1. 文書の目的

本書は `ticket_guys_b_team` が読み書きする Plan file と Ticket file の形式を定義する。

本書は canonical markdown file の形式に集中する。runtime file、log、session record、counter、lock などの運用 artifact は `operational_artifacts.md` を参照する。現在状態の解釈は `common_invariants.md`、保存手順は `state_write_protocol.md` を参照する。

---

## 2. 基本方針

* 主要オブジェクトは人間可読な file として永続化する
* canonical markdown file は YAML front matter を正本とする
* 生成物は一貫した命名規則と directory 構造に従う
* path 文字列は、特に別記がない限り filesystem absolute path とする

---

## 3. 既定ディレクトリ構造

成果物の既定配置は `.tgbt/` 配下とする。

```text
.tgbt/
  plans/
  tickets/
  logs/
  codex/
  system/
```

各 directory の役割は以下の通りとする。

* `.tgbt/plans/`: Plan file
* `.tgbt/tickets/`: Ticket file
* `.tgbt/logs/`: execution log と env audit log
* `.tgbt/codex/`: session record
* `.tgbt/system/`: counters と lock artifact

追跡対象の正本は `docs/spec/` 配下に置く。`.tgbt/` 配下の runtime file と運用 artifact は Git 追跡対象外として扱う。

---

## 4. 共通表現規則

### 4.1 エンコーディング

* すべてのテキスト file は UTF-8 を前提とする
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

要件:

* 新規 Plan 作成時は、作成日の日付を `YYYYMMDD` として用い、`.tgbt/plans/` 配下の `plan-YYYYMMDD-NNN.md` に一致する既存 file を走査して `NNN` の最大値に 1 を加えた値を採用しなければならない
* 走査対象に含めるのは canonical 形式に一致する file のみとし、不一致な file 名は採番根拠に含めてはならない
* 欠番があっても再利用してはならない
* 新規作成された Plan の `plan_revision` は 1 で開始しなければならない
* `plan_id` 採番は `counters.json` の責務ではない

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

* Markdown ベースの canonical file は YAML front matter を先頭に持つ
* YAML front matter は `---` で開始し、`---` で終了する

### 4.7 path 文字列

保存先の規約を示す節では、repository root からの canonical relative path を用いる。

一方、file 内容や JSON field に格納される path 文字列は、特に別記がない限り filesystem absolute path とする。本書中の absolute path 例示は `<repo-root>/...` を用いる。

### 4.8 Ticket file discovery

`.tgbt/tickets/` 配下で Ticket file として discovery 対象に含めてよいのは、canonical filename に一致する file のみとする。

canonical filename:

```text
worker-NNNN.md
```

要件:

* active Ticket 集合の構築、依存解決、実行候補選択、既存 Ticket 読み取りの discovery では、basename が `worker-NNNN.md` に一致する file だけを走査対象に含めてよい
* canonical filename に一致しない file は Ticket file discovery の対象に含めてはならない
* canonical filename に一致する file については、front matter の `ticket_id` が filename 由来の `ticket_id` と一致しなければならない
* canonical filename に一致する file の parse や validation に失敗した場合は、無視ではなく Ticket 不整合として失敗しなければならない

---

## 5. Plan File Format

### 5.1 保存先

```text
.tgbt/plans/<plan_id>.md
```

1 Plan につき 1 file とする。

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

* `plan_kind`
* `last_run_id`
* `settled_at`
* `closure_reason`

### 5.4 本文構造

Plan file 本文は以下の section をこの順序で含む。

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
.tgbt/tickets/<ticket_id>.md
```

1 Ticket につき 1 file とする。

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

`required_state` は MVP では `settled` のみ許可する。`todo` / `running` / `done` は validation で拒否しなければならない。

### 6.5 本文構造

Ticket file 本文は以下の section をこの順序で含む。

1. Title
2. Purpose
3. Dependencies
4. Execution Instructions
5. Run Summary
6. Follow-up Notes
7. Artifacts

### 6.6 Run Summary の扱い

`Run Summary` には、最新の agent 実行結果の短い summary を追記または更新する。

ここには少なくとも以下を残せることが望ましい。

* 実行の要点
* 成功 / 失敗の要約
* 主要成果物
* follow-up が必要かどうか

### 6.7 Artifacts の記載

`Artifacts` section に記載する path は filesystem absolute path とする。

```md
# Artifacts
- <repo-root>/.tgbt/logs/plan-20260321-001-run-0003.jsonl
- <repo-root>/.tgbt/codex/worker-0002-run-0003-call-0002-ticket_execution.json
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
