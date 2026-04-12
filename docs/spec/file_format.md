# `ticket_guys_b_team` File Format Specification

## 1. 文書の目的

本書は `ticket_guys_b_team` が読み書きする主要ファイルの形式を定義する。

対象は以下とする。

* Plan file
* Ticket file
* Execution log file
* Env audit log file
* Codex session record file
* Codex runtime file
* Counter state file
* Repository lock file

本書はファイル形式と保存規約に集中し、CLI 契約や詳細な状態遷移は扱わない。atomic write-replace と異常終了後の扱いそのものは `state_write_protocol.md` を参照する。

---

## 2. 基本方針

* 主要オブジェクトはファイルとして永続化する
* 主要ファイルは人間可読な形式を優先する
* 機械処理対象のログは JSON Lines または JSON を用いる
* 生成物は一貫した命名規則とディレクトリ構造に従う
* 実行失敗時も可能な限りファイルを保存する
* live 実行の記録は stub 実行にそのまま転用可能でなければならない
* 現在状態の正本は Markdown front matter とする
* `.tgbt/system/counters.json` は採番の正本とする
* execution log、env audit log、session record は監査証跡であり、状態の正本ではない
* repository lock は state mutation の直列化に使う control artifact である

front matter と監査証跡が衝突した場合、現在状態の解釈は front matter を優先する。

---

## 3. 既定ディレクトリ構造

成果物の既定配置は `.tgbt/` 配下とする。

```text
.tgbt/
  .codex/
    config.toml
  instructions.md
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

* `.tgbt/plans/`: Plan file
* `.tgbt/tickets/`: Ticket file
* `.tgbt/logs/`: `run` の execution log と `env` の audit log
* `.tgbt/codex/`: Codex CLI wrapper の session record
* `.tgbt/.codex/config.toml`: `CODEX_HOME` 配下の repo-local Codex CLI runtime 設定
* `.tgbt/instructions.md`: `tgbt` が Codex CLI を起動する際に `model_instructions_file` から参照する repo-local runtime 指示。人間向け文書ではない
* `.tgbt/system/counters.json`: 採番の正本
* `.tgbt/system/locks/`: repository 全体の state mutation を禁止する lock artifact

追跡対象の正本は `docs/spec/` 配下に置き、`.tgbt/` 配下の runtime file は Git 追跡対象外として扱う。

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

要件:

* 新規 Plan 作成時は、作成日の日付を `YYYYMMDD` として用い、`.tgbt/plans/` 配下の `plan-YYYYMMDD-NNN.md` に一致する既存 file を走査して `NNN` の最大値に 1 を加えた値を採用しなければならない
* 走査対象に含めるのは canonical 形式に一致する file のみとし、不一致な file 名は採番根拠に含めてはならない
* 欠番があっても再利用してはならない
* 新規作成された Plan の `plan_revision` は 1 で開始しなければならない
* `plan_id` 採番は `counters.json` の責務ではなく、`next_plan_seq` のような field を要求しない

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

### 4.7 path 文字列の表現

保存先の規約を示す節では、repository root からの canonical relative path を用いる。

本書でいう `repository root` は、特に別記がない限り、top-level `tgbt` process が開始された時点の current working directory を指す。

一方、ファイル内容や JSON field に格納される path 文字列は、特に別記がない限り filesystem absolute path とする。
本書中の absolute path 例示は `<repo-root>/...` を用いる。

### 4.8 Codex runtime の共通ルール

`tgbt` が Codex CLI を起動する場合、runtime file は少なくとも以下を満たさなければならない。

* `CODEX_HOME` は `<repo-root>/.tgbt/.codex` を指す
* `<repo-root>/.tgbt/.codex/config.toml` は profile `tgbt-worker` を定義する
* profile `tgbt-worker` は `model_instructions_file = "<repo-root>/.tgbt/instructions.md"` を持つ
* `tgbt env` は `<repo-root>/.tgbt/instructions.md` を deterministic に create-or-replace しなければならない
* `<repo-root>/.tgbt/instructions.md` は人間向け文書ではなく、`tgbt` の各サブコマンドから起動される Codex CLI に共通で適用する基礎指示の runtime file でなければならない
* `<repo-root>/.tgbt/instructions.md` は追跡対象 Markdown をそのまま copy したものではなく、本仕様の内容契約を満たす application 生成物でなければならない
* Codex runtime は `~/.codex` と `<repo-root>/.codex` に依存してはならない

`.tgbt/instructions.md` は少なくとも以下を明示しなければならない。

* `tgbt` から渡される task 指示を最優先の作業指示として扱うこと
* repository 内の関連文書を読むときは `docs/` 配下を正本として扱うこと
* skills を使用してはならないこと
* sub agent を使用してはならないこと
* `~/.codex` や repository 直下 `.codex/` に依存してはならないこと
* Codex CLI の設定正本は repo-local runtime であること
* `AGENTS.md` は repository bootstrap の参照物として読んでよいが、runtime 指示の正本ではないこと

MVP では、`tgbt` が意味論上管理する runtime input path は以下に限定する。

* `<repo-root>/.tgbt/.codex/config.toml`
* `<repo-root>/.tgbt/instructions.md`

`<repo-root>/.tgbt/.codex/` 配下に他の file や directory が存在しても、それらは Codex CLI private state として扱う。
`tgbt` は、それらを bootstrap 整合判定、repo-local runtime 検証、Codex 実行方針の入力として読んではならない。

### 4.9 Ticket file discovery の共通ルール

`.tgbt/tickets/` 配下で Ticket file として発見対象に含めてよいのは、canonical filename に一致する file のみとする。

canonical filename:

```text
worker-NNNN.md
```

要件:

* active Ticket 集合の構築、依存解決、実行候補選択、既存 Ticket 読み取りの discovery では、basename が `worker-NNNN.md` に一致する file だけを走査対象に含めてよい
* canonical filename に一致しない file は、`.tgbt/tickets/` 配下に残っていても Ticket file discovery の対象に含めてはならない
* canonical filename に一致する file については、front matter の `ticket_id` が filename 由来の `ticket_id` と一致しなければならない
* canonical filename に一致する file の parse や validation に失敗した場合は、無視ではなく Ticket 不整合として失敗しなければならない

---

## 5. Plan File Format

### 5.1 保存先

```text
.tgbt/plans/<plan_id>.md
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

* `plan_kind`
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
.tgbt/tickets/<ticket_id>.md
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
`Artifacts` セクションに記載する path は filesystem absolute path とする。

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

---

## 7. Run Execution Log File Format

### 7.1 保存先

推奨保存先:

```text
.tgbt/logs/<plan_id>-<run_id>.jsonl
```

この section は `tgbt run` が保存する execution log にのみ適用する。
`.tgbt/logs/env-latest.jsonl` の schema は **本 section ではなく** `8. Env Audit Log File Format` に従う。

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

path を表す event field は filesystem absolute path とする。

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

## 8. Env Audit Log File Format

### 8.1 保存先

```text
.tgbt/logs/env-latest.jsonl
```

`env-latest.jsonl` は履歴台帳ではなく、**最新の 1 回の `tgbt env` invocation** に対応する固定 path artifact とする。
より新しい invocation が開始された後は、旧 invocation の file が canonical path に残存してはならない。
最新 invocation の audit artifact を publish できなかった場合、canonical path が不在になることは許容する。

### 8.2 目的

`env-latest.jsonl` は、`tgbt env` が実施した bootstrap 観測、deterministic な補修試行、および最終検証結果を保存する audit artifact である。

### 8.3 役割と境界

* authoritative mutable state ではない
* `tgbt run` の execution log ではない
* Codex session record ではない
* stub replay source ではない
* 1 invocation の途中経過と最終 verdict を、human / machine の双方が追跡できることを目的とする
* より新しい invocation が開始された後に、旧 invocation の stale artifact を `latest` として残す用途に使ってはならない

front matter や runtime file の現在状態と audit artifact が衝突した場合、現在状態の解釈は authoritative mutable file を優先する。

### 8.4 JSON Lines と event stream

`env-latest.jsonl` は JSON Lines とし、1 行が 1 event を表す。

1 回の `tgbt env` invocation は、同一 `repo_root` に属する record だけで構成されなければならない。
複数 invocation の record を 1 ファイルへ混在させてはならない。
より新しい invocation が開始された後に、その invocation の record を publish できないにもかかわらず、旧 invocation の record 群を canonical path に残してはならない。

MVP の正常系では、record は次の決定的順序で並ばなければならない。

1. `env_observed`
2. `env_reconciled`
3. `env_validated`

`env_validated` は runtime を最終判定できた invocation の最終 record とする。
`env_failed` は、env audit log 自体は publish できるが最終 validation verdict を記録できない失敗に限って使用してよく、その場合は最終 record でなければならない。

### 8.5 共通 field

各 record は最低限以下を含まなければならない。

* `schema_name`
* `schema_version`
* `command_name`
* `timestamp`
* `repo_root`
* `event_type`

要件:

* `schema_name` は `env_audit` でなければならない
* `schema_version` は MVP では `1` とする
* `command_name` は `env` でなければならない
* `timestamp` はタイムゾーン付き ISO 8601 文字列でなければならない
* `repo_root` は invocation current working directory に解決された filesystem absolute path でなければならない
* path を表す field は filesystem absolute path とする

### 8.6 Issue Object Schema

`blocking_issues` と `diagnostics` の各要素は、自由形式文字列ではなく issue object として扱う。

最低限以下を含まなければならない。

* `code`
* `severity`
* `subject`
* `path`
* `message`
* `repair_policy`

MVP の `subject` は以下のみを使用する。

* `repo_local_codex_config`
* `runtime_instructions`
* `agents_md`
* `repo_root_codex_dir`

MVP の `repair_policy` は以下のみを使用する。

* `auto_repair`
* `observe_only`

### 8.7 Repair Action Object Schema

`env_reconciled.actions` の各要素は repair action object とする。

最低限以下を含まなければならない。

* `subject`
* `path`
* `action_type`
* `result`
* `message`

MVP では以下を要件とする。

* `subject` は `repo_local_codex_config` または `runtime_instructions` のみ
* `action_type` は `create_or_replace_file` のみ
* `result` は `updated` または `unchanged` のみ

### 8.8 Event Type ごとの要件

`env_observed`:

* 初回観測結果を表す
* `blocking_issues` と `diagnostics` を必須とする
* `blocking_issues` の item は `severity = blocking`、`diagnostics` の item は `severity = diagnostic` でなければならない

`env_reconciled`:

* 補修試行 phase を表す
* `repair_attempted` と `actions` を必須とする
* 初回から合法だった場合は `repair_attempted = false` かつ `actions = []` とする
* 非合法だった場合は `repair_attempted = true` とし、auto-repair 対象に対して実施した action を `actions` に記録する

`env_validated`:

* 最終 validation verdict を表す
* `outcome`、`goal_reached`、`blocking_issues`、`diagnostics` を必須とする
* `outcome` は `already_legal`、`legalized`、`illegal` のいずれかでなければならない
* `goal_reached = true` は `outcome != illegal` と整合しなければならない

`env_failed`:

* `env_validated` を保存できない failure を表す
* `failure_stage`、`cause`、`diagnostics` を必須とする
* `failure_stage` は `observation`、`repair`、`validation` のいずれかでなければならない
* `env_failed` を publish できた場合、その file 全体は current invocation を表していなければならない

### 8.9 Formal Schema

schema:

```json
{
  "type": "object",
  "oneOf": [
    { "$ref": "#/$defs/env_observed" },
    { "$ref": "#/$defs/env_reconciled" },
    { "$ref": "#/$defs/env_validated" },
    { "$ref": "#/$defs/env_failed" }
  ],
  "$defs": {
    "event_base": {
      "type": "object",
      "properties": {
        "schema_name": { "type": "string", "const": "env_audit" },
        "schema_version": { "type": "integer", "const": 1 },
        "command_name": { "type": "string", "const": "env" },
        "timestamp": { "type": "string", "format": "date-time" },
        "repo_root": { "type": "string" },
        "event_type": { "type": "string" }
      },
      "required": [
        "schema_name",
        "schema_version",
        "command_name",
        "timestamp",
        "repo_root",
        "event_type"
      ]
    },
    "issue_base": {
      "type": "object",
      "properties": {
        "code": { "type": "string" },
        "severity": { "type": "string", "enum": ["blocking", "diagnostic"] },
        "subject": {
          "type": "string",
          "enum": [
            "repo_local_codex_config",
            "runtime_instructions",
            "agents_md",
            "repo_root_codex_dir"
          ]
        },
        "path": { "type": ["string", "null"] },
        "message": { "type": "string" },
        "repair_policy": {
          "type": "string",
          "enum": ["auto_repair", "observe_only"]
        }
      },
      "required": [
        "code",
        "severity",
        "subject",
        "path",
        "message",
        "repair_policy"
      ]
    },
    "blocking_issue": {
      "allOf": [
        { "$ref": "#/$defs/issue_base" },
        {
          "type": "object",
          "properties": {
            "severity": { "const": "blocking" }
          },
          "required": ["severity"]
        }
      ]
    },
    "diagnostic_issue": {
      "allOf": [
        { "$ref": "#/$defs/issue_base" },
        {
          "type": "object",
          "properties": {
            "severity": { "const": "diagnostic" }
          },
          "required": ["severity"]
        }
      ]
    },
    "repair_action": {
      "type": "object",
      "properties": {
        "subject": {
          "type": "string",
          "enum": [
            "repo_local_codex_config",
            "runtime_instructions"
          ]
        },
        "path": { "type": "string" },
        "action_type": {
          "type": "string",
          "const": "create_or_replace_file"
        },
        "result": {
          "type": "string",
          "enum": ["updated", "unchanged"]
        },
        "message": { "type": "string" }
      },
      "required": [
        "subject",
        "path",
        "action_type",
        "result",
        "message"
      ]
    },
    "env_observed": {
      "allOf": [
        { "$ref": "#/$defs/event_base" },
        {
          "type": "object",
          "properties": {
            "event_type": { "const": "env_observed" },
            "blocking_issues": {
              "type": "array",
              "items": { "$ref": "#/$defs/blocking_issue" }
            },
            "diagnostics": {
              "type": "array",
              "items": { "$ref": "#/$defs/diagnostic_issue" }
            }
          },
          "required": ["event_type", "blocking_issues", "diagnostics"]
        }
      ]
    },
    "env_reconciled": {
      "allOf": [
        { "$ref": "#/$defs/event_base" },
        {
          "type": "object",
          "properties": {
            "event_type": { "const": "env_reconciled" },
            "repair_attempted": { "type": "boolean" },
            "actions": {
              "type": "array",
              "items": { "$ref": "#/$defs/repair_action" }
            }
          },
          "required": ["event_type", "repair_attempted", "actions"]
        }
      ]
    },
    "env_validated": {
      "allOf": [
        { "$ref": "#/$defs/event_base" },
        {
          "type": "object",
          "properties": {
            "event_type": { "const": "env_validated" },
            "outcome": {
              "type": "string",
              "enum": ["already_legal", "legalized", "illegal"]
            },
            "goal_reached": { "type": "boolean" },
            "blocking_issues": {
              "type": "array",
              "items": { "$ref": "#/$defs/blocking_issue" }
            },
            "diagnostics": {
              "type": "array",
              "items": { "$ref": "#/$defs/diagnostic_issue" }
            }
          },
          "required": [
            "event_type",
            "outcome",
            "goal_reached",
            "blocking_issues",
            "diagnostics"
          ]
        }
      ]
    },
    "env_failed": {
      "allOf": [
        { "$ref": "#/$defs/event_base" },
        {
          "type": "object",
          "properties": {
            "event_type": { "const": "env_failed" },
            "failure_stage": {
              "type": "string",
              "enum": ["observation", "repair", "validation"]
            },
            "cause": { "type": "string" },
            "diagnostics": {
              "type": "array",
              "items": { "$ref": "#/$defs/diagnostic_issue" }
            }
          },
          "required": ["event_type", "failure_stage", "cause", "diagnostics"]
        }
      ]
    }
  }
}
```

### 8.10 例

```json
{"schema_name":"env_audit","schema_version":1,"command_name":"env","timestamp":"2026-03-21T11:00:00+09:00","repo_root":"<repo-root>","event_type":"env_observed","blocking_issues":[{"code":"missing_runtime_instructions","severity":"blocking","subject":"runtime_instructions","path":"<repo-root>/.tgbt/instructions.md","message":".tgbt/instructions.md was not found","repair_policy":"auto_repair"}],"diagnostics":[{"code":"missing_agents_md","severity":"diagnostic","subject":"agents_md","path":"<repo-root>/AGENTS.md","message":"AGENTS.md was not found","repair_policy":"observe_only"}]}
{"schema_name":"env_audit","schema_version":1,"command_name":"env","timestamp":"2026-03-21T11:00:01+09:00","repo_root":"<repo-root>","event_type":"env_reconciled","repair_attempted":true,"actions":[{"subject":"runtime_instructions","path":"<repo-root>/.tgbt/instructions.md","action_type":"create_or_replace_file","result":"updated","message":"regenerated shared runtime instructions for tgbt Codex invocations"}]}
{"schema_name":"env_audit","schema_version":1,"command_name":"env","timestamp":"2026-03-21T11:00:02+09:00","repo_root":"<repo-root>","event_type":"env_validated","outcome":"legalized","goal_reached":true,"blocking_issues":[],"diagnostics":[{"code":"missing_agents_md","severity":"diagnostic","subject":"agents_md","path":"<repo-root>/AGENTS.md","message":"AGENTS.md was not found","repair_policy":"observe_only"}]}
```

### 8.11 要件

* `env-latest.jsonl` は 1 回の `tgbt env` invocation に対して 1 ファイルでなければならない
* invocation 完了後に残す record 群は、その invocation の phase を監査できる最小集合でなければならない
* runtime の最終 verdict を判定できた場合、最終 record は `env_validated` でなければならない
* `env_failed` を保存した場合、それは最終 record でなければならない
* より新しい invocation が開始された後は、旧 invocation の `env-latest.jsonl` を stale artifact として canonical path に残してはならない
* current invocation の env audit log を保存できなかった場合、canonical path が不在になることは許容する
* `blocking_issues` と `diagnostics` は、CLI 表示だけのために情報を欠落させた自由形式文字列へ劣化させてはならない
* `repair_action` は observe-only subject を含んではならない

---

## 9. Codex Session Record File Format

### 9.1 保存先

推奨保存先:

```text
.tgbt/codex/<scope>-<run_id>-<codex_call_id>-<call_purpose>.json
```

これは `run_id != null` の wrapper 呼び出しで使う。

`<scope>` は **決定的に** 以下とする。

* `ticket_id != null` のとき `<scope> = <ticket_id>`
* `ticket_id == null` のとき `<scope> = <plan_id>`

`plan_drafting` では以下を使う。

```text
.tgbt/codex/<plan_id>-rev-<plan_revision>-<codex_call_id>-plan_drafting.json
```

例:

```text
.tgbt/codex/plan-20260321-001-run-0003-call-0001-ticket_planning.json
.tgbt/codex/worker-0001-run-0003-call-0002-ticket_execution.json
.tgbt/codex/plan-20260321-001-rev-2-call-0007-plan_drafting.json
```

ここで示す保存先は repository root からの canonical relative path である。record 内に保存される `result.session_record_path` と `result.replayed_from` は、対応する filesystem absolute path とする。

### 9.2 目的

session record は 1 回の wrapper 呼び出しの request / response を保存する JSON artifact である。

### 9.3 必須フィールド

最低限以下を含むこと。

* `schema_version`
* `plan_id`
* `plan_revision`
* `ticket_id` (`ticket` に紐づかない call では `null` 可)
* `run_id` (`plan_drafting` では `null` 可)
* `codex_call_id`
* `call_purpose`
* `codex_cli_mode`
* `request`
* `result`
* `saved_at`

### 9.4 `call_purpose` の値

MVP では以下のみを使用する。

* `plan_drafting`
* `ticket_planning`
* `ticket_execution`
* `followup_planning`

### 9.5 `request` に含めることが望ましい項目

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

### 9.6 `result` に含めることが望ましい項目

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
`generated_artifacts` の各要素、`session_record_path`、`replayed_from` は filesystem absolute path とする。

### 9.7 要件

* live 実行の session record は、そのまま stub source として利用できること
* stub 実行時に元 record を破壊してはならないこと
* strict replay では、source record の `request` と current request を **同じ正規化・redaction 関数**に通した結果が、`codex_cli_mode` と `stub_record_path` を除いて一致しなければならないこと
* `plan_drafting` では `run_id = null` を許容すること
* `last_message_text` は、4 つの call purpose については redaction 後 `business_output` の canonical JSON serialization であることが望ましい

---

## 10. Counter State File Format

### 10.1 保存先

```text
.tgbt/system/counters.json
```

### 10.2 目的

`ticket_id` / `run_id` / `codex_call_id` の単調増加採番を保証するための正本である。

### 10.3 必須フィールド

最低限以下を含むこと。

* `next_ticket_seq`
* `next_run_seq`
* `next_codex_call_seq`
* `updated_at`

### 10.4 例

```json
{
  "next_ticket_seq": 12,
  "next_run_seq": 4,
  "next_codex_call_seq": 27,
  "updated_at": "2026-03-21T11:10:00+09:00"
}
```

### 10.5 要件

* 採番はこの file を正本として行うこと
* `plan_id` 採番はこの file の責務に含めず、`4.5 plan_id` の規則に従うこと
* `next_*` は **unsigned 64-bit 整数範囲**で扱わなければならない
* 実装は少なくとも `1 .. 18446744073709551615` の範囲を扱えなければならない
* 途中クラッシュや後続失敗による欠番を許容する
* 一度 `next_*` を進めて永続化したら、その番号は消費済みとみなし、`tgbt` 自身は巻き戻してはならない
* 外部 snapshot restore により repository 全体を過去時点へ戻す運用は、本 file 単体の巻き戻しとは別扱いとして許容する
* `ticket_id` は対応する Ticket file 作成を試みる直前に採番してよい
* `run_id` は repository lock 取得後、最初の run-scoped artifact を作る前に採番しなければならない
* `codex_call_id` は `plan` / `run` を問わず wrapper 実行を試みる直前に採番してよい
* repository lock により、この file の更新は state-mutating `tgbt` 間で直列化されること
* strict replay では、`run` 系 call についてはこの file を過去 run 開始前の状態へ戻すことで同じ `run_id` / `codex_call_id` 系列を再現できること
* `plan_drafting` については、この file を対象 call 実行前の状態へ戻すことで同じ `codex_call_id` 系列を再現できること

---


## 11. Repository Lock File Format

### 11.1 保存先

```text
.tgbt/system/locks/repository.lock.json
```

### 11.2 目的

repository 全体に対する同時 state mutation を禁止するための lock artifact である。

### 11.3 必須フィールド

最低限以下を含むこと。

* `command_name`
* `acquired_at`

### 11.4 推奨フィールド

必要に応じて以下を追加してよい。

* `plan_id`
* `run_id`
* `pid`
* `hostname`
* `command_line`

### 11.5 例

```json
{
  "command_name": "run",
  "plan_id": "plan-20260321-001",
  "run_id": "run-0003",
  "acquired_at": "2026-03-21T11:00:00+09:00"
}
```

### 11.6 要件

* lock 取得は、最終 lock path に対する **原子的な non-overwrite create** で行わなければならない
* 「存在確認してから作る」方式は禁止する
* 実装は `O_CREAT|O_EXCL` 相当、または同等の排他意味論を持つ OS primitive を使用しなければならない
* 既存 lock が存在する場合、新しい state-mutating `tgbt` は失敗しなければならない
* `plan` は新規作成・既存更新の別を問わず、Plan file 作成・更新、破棄・退避、front matter 更新を行う前に lock を取得しなければならない
* `run` 開始時に lock を取得し、終了時に解放すること
* MVP では stale lock の自動判定・自動回収は行わない
* stale lock の手動削除運用を許容してよい
