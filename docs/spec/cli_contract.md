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
Codex の live / stub 切り替えと業務レベル出力契約の詳細は `codex_cli_wrapper.md` を、front matter と state file の commit 規則および異常終了時の扱いは `state_write_protocol.md` を参照する。

---

## 2. 基本方針

* 人間が触る主要インターフェースは CLI とする
* CLI は内部フレームワーク概念を隠蔽し、業務概念を提供する
* 人間は Plan、Ticket、run という概念で操作できるべきである
* `plan` は親コマンドとし、PoC では `docs` のみを公開する
* `env` は repo-local Codex runtime を合法化する独立サブコマンドとして公開する
* `run` 側は細分化しない
* Codex を呼び出すコマンドは wrapper 経由でのみ行う
* 失敗時も、原因と次に取るべき行動が短く理解できる出力を返す
* 同一 repository に対する state-mutating `tgbt` は repository lock により 1 本だけ許可する
* MVP では集約ビューのための `status` / `state` サブコマンドを設けない
* 独立した `approve` コマンドは設けない
* `run` は直列実行のみを提供する
* `stub` は strict replay 用途に限定する
* state-mutating command の非 0 終了またはプロセス中断後の repository state は未定義であり、継続利用する前にユーザーが安全な snapshot へ restore しなければならない

---

## 3. エントリポイント

正規の CLI 名は `tgbt` とする。

起動導線として以下を提供する。

```text
bin/tgbt
```

利用者は `bin/` を `$PATH` に追加したうえで `tgbt` を実行する。

`bin/tgbt` は起動導線にすぎず、対象 repository の決定に script 自身の配置位置を使ってはならない。
script の配置位置は、launcher 自身の実行に必要な runtime や entrypoint を見つける用途にのみ使ってよい。

例:

```bash
tgbt plan docs "ここに要件を書く"
```

---

## 4. コマンド体系

CLI は最低限以下のコマンドを提供する。

* `tgbt plan`
* `tgbt env`
* `tgbt plan docs`
* `tgbt run`

MVP では `ticket` を独立コマンドにしない。Ticket の生成・更新・settle は `run` の内部オーケストレーションが担う。
MVP では `status` / `state` / `review-queue` / `artifacts` を導入しない。

---

## 5. 共通契約

### 5.1 終了コード

* 正常終了時は 0 を返す
* 以下の異常系は非 0 を返す
  * 入力不正
  * Plan 不整合
  * Ticket 不整合
  * strict replay 不整合
  * 実行失敗
  * ログ保存失敗
  * lock 取得失敗
  * business output validation 失敗
  * hard limit 超過

### 5.2 エラー出力方針

エラー表示は少なくとも以下を短く示す。

* 原因
* 影響範囲
* 次に取るべき行動

例:

```text
ERROR: strict replay source was not found
Impact: top-level run stopped before wrapper execution
Next: restore pre-run state and required session record under .tgbt/codex/
```

### 5.3 永続化方針

* 成功時も失敗時も、可能な限り状態更新とログ保存を行う
* 実行時に起きた事実はログへ保存する
* Codex 呼び出しでは session record を保存または参照する
* ログ保存自体に失敗した場合も、その失敗を標準エラー等へ可能な限り残す
* 現在状態の正本は front matter とする
* 採番の正本は `.tgbt/system/counters.json` とする
* execution log、env audit log、session record は監査証跡として扱う
* authoritative mutable state の各 file commit は `state_write_protocol.md` に従う
* 複数ファイル mutation の repository-wide atomicity は提供しない

### 5.4 出力方針

* 人間向けの簡潔な標準出力を返す
* 機械処理向けには JSON 出力を将来拡張してよい
* MVP では人間可読性を優先するが、ログと成果物パスが追跡できることを維持する
* 各コマンドは、更新または参照すべきファイルのパスを返す
* CLI が表示する path は、repository root を起点に解決した filesystem absolute path でなければならない
* 仕様書中の absolute path 例示は `<repo-root>/...` を用いる

### 5.5 対象 repository の解決

本仕様でいう `repository root` は、top-level `tgbt` process が開始された時点の current working directory を指す。

* `tgbt` は、top-level `tgbt` process が開始された時点の current working directory を対象 repository として扱わなければならない
* `bin/tgbt` は、script 自身の checkout 位置ではなく、呼び出し時の current working directory を対象 repository として扱わなければならない
* 対象 repository は invocation current working directory そのものであり、親 directory の探索や VCS root の自動検出を行ってはならない
* `plan` / `run` が参照・更新する `.tgbt/`、Plan file、Ticket file、log、session record は、すべてこの対象 repository 配下に解決しなければならない
* wrapper request の `cwd` は、この対象 repository を指す filesystem absolute path でなければならない
* `cwd` が filesystem root などの明らかに不適切な directory を指していても、本仕様では自動的に checkout 位置へ補正してはならない。妥当性検証を導入する場合でも、補正ではなく明示的失敗として扱う

この規則により、たとえば `~/pure_stuff` で `tgbt plan docs ...` を実行した場合、対象 repository は `~/pure_stuff` である。

### 5.6 モード用語

本仕様で扱う実行モードは `codex_cli_mode` のみである。
これは Codex を呼び出す `plan` / `run` 系コマンドにだけ適用される。

#### `codex_cli_mode`

内部の Codex 呼び出しをどう扱うかを表す。

* `live`
* `stub`

`plan` / `run` は常に実行コマンドであり、dry-run / preflight / validate は現時点では提供しない。

### 5.7 repository lock

同一 repository に対して state mutation を行う `tgbt` コマンドは、repository lock を取得しなければならない。

MVP では、state mutation を行う `tgbt` コマンドはすべて lock 対象とする。現時点では少なくとも以下が該当する。

* `tgbt env`
* `tgbt plan docs`
* `tgbt run`

新規 Plan 作成も既存 Plan 更新も、Plan file 作成・更新、active Ticket 集合の破棄・退避、front matter 更新を行う前に lock を取得しなければならない。

MVP では stale lock の自動回収を行わない。既存 lock が残っている場合、利用者は他プロセス停止を確認したうえで手動除去してよい。

### 5.8 異常終了後の扱い

state-mutating command が非 0 終了した場合、またはプロセスが中断した場合、その repository state は support 対象外の途中状態として扱う。

利用者は次の state-mutating command の前に、少なくとも以下を行わなければならない。

1. repository 全体を既知の安全な snapshot へ restore する
2. stale lock が残っていれば除去する
3. 指示や入力を見直して retry する

---

## 6. `env` / `plan docs`

### 6.1 `tgbt env`

#### 6.1.1 目的

`<repo-root>` 配下の Codex CLI の挙動に関わる一式を、tgbt の操作対象として合法な状態へ one-shot で整える。

#### 6.1.2 入力

自然言語による positional argument は受け付けない。
`--codex-cli-mode` は受け付けない。

application は Codex wrapper を呼び出してはならない。
application は repository bootstrap の現状をローカルに観測し、deterministic な補修処理だけで完結しなければならない。

対象とする bootstrap 現状は、MVP では以下に限定する。

* `AGENTS.md`
* `.tgbt/.codex/config.toml`
* `.tgbt/instructions.md`
* repository 直下 `.codex/` の存在有無

#### 6.1.3 高水準アルゴリズム

`tgbt env` は少なくとも以下を直列実行する。

1. repository lock を取得する
2. 既存 `.tgbt/logs/env-latest.jsonl` があれば、より新しい invocation に対して stale な `latest` が残らないよう invalidation する
3. 現在状態の runtime 合法性と bootstrap diagnostics を観測する
4. 既に合法なら補修は行わず、current invocation の env audit log を publish した後に成功終了する
5. 非合法なら自動修正対象の runtime file を deterministic に再生成する
6. 合法性を再検証する
7. `docs/spec/file_format.md` の `Env Audit Log File Format` に従って `.tgbt/logs/env-latest.jsonl` を publish する
8. runtime が合法なら成功終了し、必要なら diagnostics を表示してよい

`tgbt env` は一般的な loop orchestration や env Plan iteration を持たない。
補修処理は 1 回だけ実行し、Plan file / Ticket file / session record / run log を生成してはならない。

runtime の最終 verdict を判定できた invocation は、最終 record を `env_validated` としなければならない。
env audit log 自体は publish できるが最終 verdict を保存できない failure は `env_failed` で表してよい。
current invocation の env audit log を保存できなかった場合、`.tgbt/logs/env-latest.jsonl` が不在になることは許容するが、前回 invocation の artifact を stale な `latest` として残してはならない。

#### 6.1.4 出力

* 初回から合法なら `Status: already_legal` を表示して成功終了する
* 補修後に合法化できた場合は `Status: legalized` を表示して成功終了する
* file を更新した場合は `Updated files:` に absolute path を表示してよい
* bootstrap 観測で利用者に伝えるべき事項があれば `Diagnostics:` を表示してよい
* current invocation の env audit log を publish できた場合は、その記録先を `Log: <absolute path>` として表示する
* 失敗時は diagnostics を表示し、必要なら `Updated files:`、`Diagnostics:`、`Remaining issues:`、`Log:` を伴ってよい

#### 6.1.5 失敗条件

* repository lock を取得できない
* bootstrap 観測または runtime file 再生成に失敗した
* one-shot の補修後も repo-local runtime の blocking issue が残る
* env audit log を保存できない

#### 6.1.6 MVP 制約

* `tgbt env` は bootstrap repair command であり、AI orchestration command ではない
* legality 判定対象は `.tgbt/.codex/config.toml` と `.tgbt/instructions.md` の 2 要素に限定する
* `AGENTS.md` と repository 直下 `.codex/` は bootstrap 観測対象だが、blocking issue や自動修正対象には含めない

### 6.2 `tgbt plan`

* 子コマンド必須の親コマンドとして扱う
* 現時点で公開する子コマンドは `docs` のみとする
* `plan` 配下の実行サブコマンドは、共通 option として `--codex-cli-mode {live|stub}` を受け付ける
* `plan` 配下の `--codex-cli-mode` 既定値は `live` とする
* `tgbt plan` 単独実行は入力不正として扱い、usage を表示して非 0 終了する

### 6.3 `tgbt plan docs`

#### 6.3.1 目的

`<repo-root>/docs` 配下のドキュメント修正作業の Plan を生成または更新する。
PoC では、コード修正作業を計画対象に含めてはならない。

#### 6.3.2 入力

以下を受け付ける。

* 自然言語要求
* `--plan-id <plan_id>` （既存 Plan を更新するときのみ）
* `--codex-cli-mode {live|stub}` (`plan` 共通 option)

例:

```bash
tgbt plan docs "CLI 仕様書の参照関係を整理したい"
```

```bash
tgbt plan docs --plan-id plan-20260321-001 "strict replay の説明を整理する"
```

```bash
tgbt plan docs --codex-cli-mode stub "strict replay fixture から docs 修正 Plan を再生成する"
```

#### 6.3.3 出力

* `<repo-root>/.tgbt/plans/<plan_id>.md` を生成または更新する
* 実行結果として少なくとも `Updated: <absolute path>`、`Plan revision: <plan_revision>`、`Status: draft` を表示する
* 主要な session record 参照先を `Session record: <absolute path>` として表示する

例:

```text
Updated: <repo-root>/.tgbt/plans/plan-20260321-001.md
Plan revision: 2
Status: draft
Session record: <repo-root>/.tgbt/codex/plan-20260321-001-rev-2-call-0001-plan_drafting.json
```

#### 6.3.4 状態遷移

* 新規生成時は `draft`
* 更新時も `draft`
* `running` または `settled` の Plan を更新した場合も `draft` に戻す
* `--plan-id` を指定しない新規作成では、`plan_id` は `file_format.md` の `plan_id` 採番規則に従って決定する
* 既存 Plan を更新した場合、`plan_revision` は 1 増加する
* 既存 Plan を更新して active Ticket 集合を破棄または退避する処理は、repository lock を取得したときにのみ行ってよい
* `plan_drafting` payload を proposal として扱い、application が canonical Plan markdown を render する

#### 6.3.5 Plan 内容制約

* 対象範囲は `<repo-root>/docs` 配下の文書修正に限定する
* 実装コード、テストコード、環境構築コマンドの変更を deliverable に含めてはならない
* 仕様修正からコード修正へ進む流れを前提にし、コード実装は後続作業として扱う

#### 6.3.6 Ticket 破棄規則

既存 Plan を更新した場合、その Plan の直前 `plan_revision` に属する active Ticket 集合は破棄対象とする。

ここでいう active Ticket とは、更新前 revision を current revision とみなしたとき、`.tgbt/tickets/` 上に現存する当該 `plan_id` / `plan_revision` の Ticket file 集合を指す。

MVP では以下を許容する。

* active Ticket file を削除する
* active Ticket file を別保管先へ退避する

ただし、どちらの場合でも ticket id 採番は巻き戻してはならない。
execution log、env audit log、session record は監査証跡として保持してよい。

#### 6.3.7 失敗条件

* 出力先へ書き込めない
* 入力が空である
* 対象 `plan_id` が見つからない
* repository lock を取得できない
* front matter 更新に失敗した
* candidate validation に失敗した
* active Ticket 破棄処理に失敗した
* `plan_revision` 更新に失敗した
* wrapper 実行に失敗した
* `plan_drafting` payload の validation に失敗した
* `stub` 時に source record が存在しない
* `stub` 時に strict replay request 検証に失敗した
* `codex_call_id` 採番または `counters.json` 更新に失敗した

#### 6.3.8 MVP 制約

* `tgbt plan docs` は Codex wrapper を通じて `plan_drafting` payload を受け取り、application が canonical Plan markdown を render する
* `plan_drafting` は canonical markdown 全文ではなく proposal payload を返す
* `stub` は strict replay であり、近似的な応答再現を許容しない

---

## 7. `run` コマンド

### 7.1 目的

指定した Plan を起点に、必要 Ticket の生成、Ticket 実行、実行結果サマリー反映、フォローアップ Ticket 生成を反復し、Plan を `settled` まで進めるか、途中失敗で停止する。

### 7.2 入力

* `--plan-id <plan_id>`
* `--codex-cli-mode {live|stub}`

例:

```bash
tgbt run --plan-id plan-20260321-001
```

```bash
tgbt run --plan-id plan-20260321-001 --codex-cli-mode stub
```

### 7.3 出力

* 更新後の Plan 状態
* 生成または更新された Ticket file の一覧
* 実行ログ保存先
* 主要な session record 参照先または保存先
* `Log`、`Updated tickets`、`Session record` に表示する path は absolute path とする

例:

```text
Plan: plan-20260321-001
Plan revision: 2
Status: settled
Log: <repo-root>/.tgbt/logs/plan-20260321-001-run-0003.jsonl
Updated tickets:
- <repo-root>/.tgbt/tickets/worker-0007.md
- <repo-root>/.tgbt/tickets/worker-0008.md
```

### 7.4 前提条件

* Plan file が存在すること
* Plan front matter が妥当であること
* Plan status が `draft` であること
* repository lock を取得できること
* `stub` のときは strict replay の前提が満たされていること

strict replay の前提とは、少なくとも以下を指す。

* 対象 repository 状態が再現したい run 開始前の状態へ戻されていること
* Plan / Ticket front matter が再現したい run 開始前の状態へ戻されていること
* `.tgbt/system/counters.json` が再現したい run 開始前の状態へ戻されていること
* canonical path に必要な source record が存在すること

これは `tgbt` の業務契約として必要な前提である。通常の `pytest` ベース stub テストでは、これらの前提は test harness / fixture が一時 directory、fixture file、ダミー state を用いて自前で満たすものとし、テスト実行者に既存 repository 状態の手動 restore や `.tgbt/` 調整を要求しない。

### 7.5 高水準アルゴリズム

`run` は少なくとも以下を反復する。

1. repository lock を取得する
2. `run_id` を採番する
3. Plan を `running` にする
4. Plan と active Ticket 群を見て、新規 Ticket が必要か判断する
5. 必要なら `ticket_planning` payload に従って新規 Ticket を 0 件以上作成する
6. active Ticket 集合の依存グラフを検証する
7. 依存解決済みの `todo` Ticket があれば、そのうち最小 `ticket_id` を選んで実行する
8. `ticket_execution` payload、実行結果サマリー、実行ログ、必要な session record を保存できた場合のみ、その Ticket を `done` にする
9. `done` Ticket に対して `followup_planning` を行う
10. 必要な follow-up Ticket を作成した後、元 Ticket を `settled` にする
11. 新規 Ticket 作成不要かつ active Ticket がすべて `settled` なら Plan を `settled` にして終了する
12. runnable な `todo` Ticket が 0 件で、かつ unsettled active Ticket が残る場合は run を失敗させる
13. `max_run_loop_count` または `max_new_ticket_count_per_run` に達した時点で、その run を強制停止する
14. repository lock を解放する

### 7.6 stub 契約

`stub` モードでは、`tgbt plan docs` / `run` とも manifest を用いない。

代わりに orchestration 層が、現在の wrapper 呼び出しに対して canonical path を決定し、単一 `stub_record_path` として wrapper に渡す。

```text
.tgbt/codex/<scope>-<run_id>-<codex_call_id>-<call_purpose>.json
```

`run_id != null` の wrapper 呼び出しでは、`<scope>` は以下とする。

* `ticket_id != null` のとき `<scope> = <ticket_id>`
* `ticket_id == null` のとき `<scope> = <plan_id>`

`plan_drafting` では以下を使う。

```text
.tgbt/codex/<plan_id>-rev-<plan_revision>-<codex_call_id>-plan_drafting.json
```

要件:

* `stub` は strict replay であり、保存用 canonicalization + redaction 後の current request と source record request は `codex_cli_mode` / `stub_record_path` を除いて完全一致しなければならない
* source record が不足した場合、その `run` は失敗とする
* source record の identity が不一致なら、その `run` は失敗とする
* `plan_drafting` では `run_id = null` を使う
* `stub` は新しい `run_id` / `codex_call_id` 系列を生成するためのモードではない
* 通常の自動 stub テストでは、必要な source record と整合 state は orchestration の外側にある test harness / fixture が自己完結に用意する

### 7.7 hard limit

MVP では以下の hard limit を固定値として持つ。

* `max_run_loop_count = 512`
* `max_new_ticket_count_per_run = 256`

いずれかに達した時点で、その top-level `run` は失敗として強制停止しなければならない。Plan は `settled` でなくてもよい。

### 7.8 失敗条件

* Plan file が存在しない
* Plan status が `draft` ではない
* front matter が壊れている
* active Ticket 群の読み取りに失敗した
* Ticket file の生成または更新に失敗した
* candidate validation に失敗した
* repository lock 取得に失敗した
* `stub` 時に source record が存在しない
* source record schema が不正である
* strict replay request 検証に失敗した
* wrapper 実行前 validation に失敗した
* business output validation に失敗した
* 依存先 Ticket の不存在、`required_state` が `settled` 以外、循環依存が検出された
* runnable な `todo` Ticket が 0 件で、かつ unsettled active Ticket が残っている
* `max_run_loop_count` または `max_new_ticket_count_per_run` に達した
* 実行ログ保存に失敗した

### 7.9 失敗時の状態更新

* `tgbt` は非正常終了後の repository 状態を継続実行対象として扱わない
* `tgbt` は内部 rollback や自動 recovery を試みない
* 利用者は safe snapshot へ restore してから retry しなければならない
* repository lock は可能な限り解放しなければならない
* stale lock が残った場合は、他プロセス停止確認後に手動除去を許容する

### 7.10 MVP 制約

* active Ticket の集約表示専用コマンドは持たない
* Ticket 実行の並列化は提供しない
* 自動受け入れゲートの厳密仕様は本契約に含めない
* strict replay は「事前状態と整合するテスト環境」を前提とする
* ただし通常の stub テストでは、その整合状態は test harness / fixture が構築するものであり、既存 repository 状態への手動依存を意味しない
* progress invariance のような高度なループ検出は行わない

---

## 8. 返却メッセージの推奨トーン

CLI は簡潔で、人間が次の行動を理解できる出力を返す。

望ましい性質:

* 短い
* 失敗理由が明確
* 保存先がすぐ分かる
* 再実行時に必要な引数が分かる
