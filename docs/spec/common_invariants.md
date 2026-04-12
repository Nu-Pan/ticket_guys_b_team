# `ticket_guys_b_team` Common Invariants

## 1. 文書の目的

本書は、複数の仕様文書で共有する横断前提を定義する。

本書が扱うのは、文書間で同じ意味を保つべき共通不変条件である。個別コマンドの入出力、状態遷移、ファイル schema、保存手順の詳細は各専用文書を参照する。

---

## 2. 共通用語

### 2.1 `repository root`

`repository root` は、top-level `tgbt` process が開始された時点の current working directory を指す。

`tgbt` は、親 directory の探索や VCS root の自動検出を行ってはならない。

### 2.2 `state-mutating command`

`state-mutating command` とは、repository 内の canonical state または control artifact を更新しうる `tgbt` コマンドを指す。

MVP では以下が該当する。

* `tgbt env`
* `tgbt plan docs`
* `tgbt run`

### 2.3 `authoritative mutable state`

現在状態の正本として扱う mutable artifact を指す。

MVP では以下を含む。

* Plan file の front matter
* Ticket file の front matter
* `.tgbt/system/counters.json`

### 2.4 `audit artifact`

実行事実や外部入出力を残すための監査証跡を指す。現在状態の正本ではない。

MVP では以下を含む。

* execution log
* env audit log
* session record

### 2.5 `control artifact`

状態更新の制御や runtime 適用に使う artifact を指す。現在状態の正本ではない。

MVP では以下を含む。

* repository lock file
* `<repo-root>/.tgbt/.codex/config.toml`
* `<repo-root>/.tgbt/instructions.md`

---

## 3. 現在状態の解釈

現在状態は authoritative mutable state から解釈しなければならない。

* Plan の現在状態は Plan file の front matter を正本とする
* Ticket の現在状態は Ticket file の front matter を正本とする
* 採番の正本は `.tgbt/system/counters.json` とする
* audit artifact は監査証跡として扱い、現在状態の正本として扱ってはならない

authoritative mutable state と audit artifact が衝突した場合は、authoritative mutable state を優先する。

---

## 4. 排他と失敗契約

### 4.1 repository lock

同一 repository に対する state mutation は、repository lock によって直列化しなければならない。

MVP では、同一 repository に対して同時に実行可能な state-mutating `tgbt` は 1 本だけである。

### 4.2 異常終了後の扱い

state-mutating command が非 0 終了した場合、またはプロセスが中断した場合、その repository state は未定義とする。

`tgbt` は、その途中状態からの継続実行、内部 rollback、自動 recovery を保証しない。利用者は次の state-mutating command の前に、既知の安全な snapshot へ restore しなければならない。

ここでいう safe snapshot とは、少なくとも Plan / Ticket / counters / lock file を含む repository 全体が整合していた時点へ戻せる外部 snapshot を指す。MVP では git による restore を主な運用として想定する。

stale lock が残った場合は、他プロセス停止を確認したうえで手動除去を許容する。

---

## 5. Codex 呼び出しの共通前提

### 5.1 実行モード

Codex を呼び出す `plan` / `run` 系コマンドが扱う実行モードは `codex_cli_mode` のみとする。

* `live`: 実際に `codex exec` を起動する
* `stub`: strict replay source を読み込み、redaction 済み result を再生する

`stub` は近似応答モードではなく、strict replay モードである。

### 5.2 strict replay

strict replay では、現在の request と source record の request が、保存用 canonicalization と redaction を適用したうえで一致していなければならない。

また、通常の自動 stub テストでは、この前提条件は test harness / fixture が自己完結に満たすものとし、テスト実行者に既存 repository 状態の手動 restore や `.tgbt/` 調整を要求しない。

### 5.3 repo-local runtime

`tgbt` が Codex CLI を起動する実行では、runtime を repo-local に固定しなければならない。

* `CODEX_HOME` は `<repo-root>/.tgbt/.codex` を指す
* `<repo-root>/.tgbt/.codex/config.toml` は required profile set `tgbt-drafting` / `tgbt-worker` / `tgbt-review` を定義しなければならない
* `codex exec` は call ごとに required profile set のいずれかを明示指定する
* `plan_drafting` / `ticket_planning` は `tgbt-drafting`、`ticket_execution` は `tgbt-worker`、`followup_planning` は `tgbt-review` を使う
* required profile set の各 profile は `model_instructions_file = "<repo-root>/.tgbt/instructions.md"` を参照する
* `~/.codex` と repository 直下 `.codex/` に依存してはならない
* `tgbt env` は `<repo-root>/.tgbt/.codex/config.toml` の required profile set と `<repo-root>/.tgbt/instructions.md` を create-or-replace する
* `tgbt` が Codex CLI を起動する実行では skills と sub agent を使用してはならない

repo-local runtime file の内容契約は `operational_artifacts.md` を参照する。
