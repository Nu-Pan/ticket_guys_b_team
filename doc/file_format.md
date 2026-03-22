# `ticket_guys_b_team` File Format Specification

## 1. 文書の目的

本書は `ticket_guys_b_team` が読み書きする主要ファイルの形式を定義する。
対象は以下とする。

* Plan file
* Ticket file
* Execution log file
* Codex session record file

本書はファイル形式と保存規約に集中し、CLI 契約や詳細な状態遷移は扱わない。

---

## 2. 基本方針

* 主要オブジェクトはファイルとして永続化する
* 主要ファイルは人間可読な形式を優先する
* 機械処理対象のログは JSON Lines または JSON を用いる
* 生成物は一貫した命名規則とディレクトリ構造に従う
* 実行失敗時も可能な限りファイルを保存する
* live 実行の記録は stub 実行にそのまま転用可能でなければならない
* ファイルが唯一の正本である

---

## 3. 既定ディレクトリ構造

成果物の既定配置は `artifacts/` 配下とする。

```text
artifacts/
  plans/
  tickets/
  logs/
  codex/
```

各ディレクトリの役割は以下の通りとする。

* `artifacts/plans/`: Plan file
* `artifacts/tickets/`: Ticket file
* `artifacts/logs/`: 実行ログ JSONL
* `artifacts/codex/`: Codex CLI wrapper の session record

MVP では `reviews/` や `messages/` を first-class な保存先として持たない。
必要な最終メッセージは session record 内の `last_message_text` に含める。

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
* `ticket_id` は一意でなければならない
* `run_id` は `run` 実行ごとに新規採番しなければならない
* `codex_call_id` は 1 回の wrapper 呼び出しごとに一意でなければならない

### 4.5 YAML front matter

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
* `title`
* `status`
* `created_at`
* `updated_at`

`status` は以下のいずれかでなければならない。

* `draft`
* `approved`

### 5.3 本文構造

Plan file 本文は以下のセクションをこの順序で含む。

1. 目的
2. スコープ外
3. 成果物
4. 制約
5. 受け入れ条件
6. 未確定事項
7. 想定リスク
8. 検証戦略

### 5.4 例

```md
---
plan_id: plan-20260321-001
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

# 検証戦略
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
* `ticket_type`
* `status`
* `plan_id`
* `created_at`
* `updated_at`

`ticket_type` は MVP では以下のみを許可する。

* `worker`

`status` は以下のいずれかでなければならない。

* `todo`
* `running`
* `blocked`
* `done`
* `failed`

### 6.3 推奨メタデータ

必要に応じて以下を追加してよい。

* `depends_on`
* `artifacts`
* `run_history`
* `default_codex_cli_mode`
* `blocking_reason`

依存関係の正規表現は本文の `Dependencies` セクションまたは明示的な YAML 項目のどちらか一方に統一することが望ましい。

### 6.4 本文構造

Ticket file 本文は以下のセクションをこの順序で含む。

1. Title
2. Purpose
3. Dependencies
4. Acceptance Criteria
5. Verification
6. Notes
7. Artifacts

### 6.5 Dependencies の表現

Dependencies では、各依存を `ticket_id` と `required_state` の組で表現する。

例:

```md
# Dependencies
- ticket_id: worker-000
  required_state: done
```

`required_state` は Ticket 状態値のいずれかでなければならない。

### 6.6 Artifacts の推奨記載

worker Ticket では、少なくとも以下を記載できることが望ましい。

```md
# Artifacts
- artifacts/logs/worker-001-run-0003.jsonl
- artifacts/codex/worker-001-run-0003-call-0001.json
```

### 6.7 例

```md
---
ticket_id: worker-001
ticket_type: worker
status: todo
plan_id: plan-20260321-001
created_at: 2026-03-21T10:10:00+09:00
updated_at: 2026-03-21T10:10:00+09:00
default_codex_cli_mode: live
---

# Title
CLI エントリポイントを実装する

# Purpose
...

# Dependencies
- ticket_id: worker-000
  required_state: done

# Acceptance Criteria
...

# Verification
...

# Notes
...

# Artifacts
- artifacts/logs/worker-001-run-0003.jsonl
- artifacts/codex/worker-001-run-0003-call-0001.json
```

---

## 7. Execution Log File Format

### 7.1 保存先

```text
artifacts/logs/<ticket_id>-<run_id>.jsonl
```

1 run につき 1 ファイルとする。

### 7.2 形式

JSON Lines を用いる。各行は独立した JSON object とする。

### 7.3 必須フィールド

各イベントは最低限以下を含むことが望ましい。

* `timestamp`
* `event_type`
* `plan_id`
* `ticket_id`
* `run_id`

状態更新イベントでは、以下も含める。

* `before_status`
* `after_status`

wrapper 関連イベントでは、以下も含めることが望ましい。

* `codex_cli_mode`
* `session_record_path`
* `replayed_from`
* `returncode`

### 7.4 代表イベント例

* `run_started`
* `status_changed`
* `wrapper_started`
* `wrapper_finished`
* `acceptance_gate_passed`
* `acceptance_gate_blocked`
* `acceptance_gate_failed`
* `run_finished`

---

## 8. Codex Session Record File Format

### 8.1 保存先

```text
artifacts/codex/<ticket_id>-<run_id>-<codex_call_id>.json
```

### 8.2 目的

* live 実行の証跡を保存する
* stub 実行の replay source として使う

### 8.3 必須トップレベル項目

* `schema_version`
* `recorded_at`
* `request`
* `result`

### 8.4 `request` に含める項目

少なくとも以下を含める。

* `ticket_id`
* `plan_id`
* `run_id`
* `codex_call_id`
* `codex_cli_mode`
* `cwd`
* `prompt_text`
* `model`
* `reasoning_effort`

`stub` の replay source として使うため、request 側にも mode を明示してよい。

### 8.5 `result` に含める項目

少なくとも以下を含める。

* `returncode`
* `stdout`
* `stderr`
* `last_message_text`
* `generated_artifacts`
* `stop_reason`
* `session_record_path`
* `replayed_from`

### 8.6 例

```json
{
  "schema_version": "1",
  "recorded_at": "2026-03-21T13:45:00+09:00",
  "request": {
    "ticket_id": "worker-001",
    "plan_id": "plan-20260321-001",
    "run_id": "run-0003",
    "codex_call_id": "call-0001",
    "codex_cli_mode": "live",
    "cwd": "/repo",
    "prompt_text": "CLI エントリポイントを実装せよ",
    "model": "gpt-5-codex",
    "reasoning_effort": "high"
  },
  "result": {
    "returncode": 0,
    "stdout": "...",
    "stderr": "",
    "last_message_text": "実装を完了しました",
    "generated_artifacts": [
      "src/cli.py"
    ],
    "stop_reason": "completed",
    "session_record_path": "artifacts/codex/worker-001-run-0003-call-0001.json",
    "replayed_from": null
  }
}
```

---

## 9. source of truth 原則

MVP では、状態確認専用の集約ファイルや専用サブコマンドを前提にしない。
状態の正本は以下である。

* Plan file の front matter
* Ticket file の front matter
* Execution log file
* Codex session record file

CLI はこれらの保存先を返すだけでよい。
