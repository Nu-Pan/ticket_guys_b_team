# `ticket_guys_b_team` State Machine Specification

## 1. 文書の目的

本書は `ticket_guys_b_team` における主要オブジェクトの状態遷移を定義する。

対象は以下とする。

* Plan の状態遷移
* Ticket の状態遷移
* active Ticket の定義
* Ticket 依存と開始条件
* `run` における反復オーケストレーションと状態変化の関係
* 異常終了時の扱い

本書は状態値と遷移規則に集中し、CLI の入出力形式やファイル schema の詳細は別文書へ委譲する。

---

## 2. 共通原則

### 2.1 現在状態の正本

現在状態の正本は front matter とする。

* Plan の現在状態は Plan file の front matter を正本とする
* Ticket の現在状態は Ticket file の front matter を正本とする
* execution log と session record は監査証跡であり、状態の正本ではない

front matter と監査証跡が矛盾した場合、現在状態の解釈は front matter を優先する。

### 2.2 `run` は反復処理である

`run --plan-id ...` は単一 Ticket 実行コマンドではない。

1 回の `run` は、以下を必要に応じて反復するオーケストレーションである。

1. Plan と active Ticket 群を見て、新規 Ticket が必要か判断する
2. 必要なら新規 Ticket を作成する
3. 実行可能な `todo` Ticket を 1 件選び、実行する
4. 実行結果を Ticket に要約として書き戻す
5. 実行結果を踏まえてフォローアップ Ticket を作成する
6. フォローアップ作成有無が確定した Ticket を `settled` にする

### 2.3 `approve` 状態は持たない

MVP では Plan の独立した `approved` 状態を持たない。

Plan を実行に移す意思決定は `run` 開始で表現する。

### 2.4 直列実行のみを許可する

本仕様では、run と wrapper 呼び出しを直列実行のみとする。

* 同一 run 内で複数 Ticket を並列実行してはならない
* wrapper 呼び出し列は全順序を持たなければならない
* 同一 repository に対して同時に複数の state-mutating `tgbt` を持ってはならない

### 2.5 Plan 更新は revision を進める

既存 Plan を `tgbt plan docs --plan-id ...` で更新した場合、`plan_revision` は単調増加で進まなければならない。

更新後に再生成される Ticket は、新しい `plan_revision` に属する。

### 2.6 active Ticket の定義

対象 Plan を `P`、その現在 revision を `R = P.plan_revision` とする。

**active Ticket 集合**とは、`.tgbt/tickets/` に現存し、かつ以下を満たす Ticket file 集合をいう。

* canonical filename discovery に含まれる Ticket file であること
* `plan_id == P.plan_id`
* `plan_revision == R`

状態値による除外は行わない。したがって、active Ticket には `todo` / `running` / `done` / `settled` を含める。

以下は active ではない。

* canonical filename に一致しない `.tgbt/tickets/` 配下の file
* `plan_revision != R` の過去 Ticket
* 削除済み Ticket
* 退避先へ移動済み Ticket

**unsettled active Ticket** とは、active Ticket のうち `status in {todo, running, done}` を満たすものをいう。

### 2.7 repository lock と状態遷移

Plan または Ticket の front matter を変更しうる処理は、repository lock の保持下でのみ行ってよい。

MVP では、state mutation を行う `tgbt` コマンドはすべてこれに該当する。現時点では `tgbt env`、`tgbt plan docs`、`tgbt run` が対象である。

### 2.8 異常終了時の失敗モデル

本書で定義する状態遷移は、**成功した command が publish した canonical state** に対してのみ適用する。

state-mutating command が非 0 終了した場合、またはプロセスが中断した場合、その repository state は未定義とする。`tgbt` はその途中状態からの継続実行や自動修復を保証しない。

ユーザーは既知の安全な snapshot へ restore してから retry しなければならない。

---

## 3. Plan State Machine

### 3.1 状態一覧

Plan の状態は以下とする。

* `draft`
* `running`
* `settled`

### 3.2 各状態の意味

#### `draft`

人間がレビュー・修正している状態。

* `tgbt plan docs` による作成直後は `draft`
* 既存 Plan を更新した場合も `draft`
* `draft` の Plan は active run を持たない

#### `running`

Plan に対する `run` オーケストレーションが進行中であることを表す論理状態。

* Ticket 生成と Ticket 実行がこの状態で行われる
* 一部 Ticket が `todo` / `running` / `done` でもよい
* `running` は論理状態であり、同時実行許可を意味しない

#### `settled`

その時点の `plan_revision` に対して、新規 Ticket が不要であり、active Ticket 群がすべて `settled` になった終端状態。

* `todo` / `running` / `done` Ticket を active 集合に残してはならない
* `settled` は「受け入れ条件が満たされた」を必ずしも意味しない
* 再度変更したい場合は `tgbt plan docs --plan-id ...` で `draft` へ戻す

### 3.3 許可される遷移

* `draft -> running`
* `running -> settled`
* `running -> draft`
* `settled -> draft`

### 3.4 遷移規則

#### `draft -> running`

`run --plan-id ...` 開始時に遷移してよい。

条件:

* Plan file が存在すること
* 必須 front matter が妥当であること
* repository lock を取得できること
* stub 実行時は strict replay の前提条件が満たされていること

ここでいう strict replay の前提条件は product 契約上の要件である。通常の stub テストでは、テスト fixture / harness が isolation された state を構築して満たすものとし、既存 repository 状態への依存を前提にしない。

#### `running -> settled`

以下をすべて満たしたときに遷移してよい。

* AI が「新規 Ticket 作成不要」と判断していること
* 対象 Plan の active Ticket が `settled` のみであること

#### `running -> draft` / `settled -> draft`

`tgbt plan docs --plan-id ...` によって Plan 本文が更新されたときに遷移してよい。

この遷移では、対象 Plan の更新前 `plan_revision` に属する active Ticket 集合を破棄または退避し、`plan_revision` を進めたうえで、以後の `run` で新しい Ticket 集合を作り直す。

途中で異常終了した場合はその中間状態をサポートせず、restore 前提で扱う。

### 3.5 `tgbt env` の位置づけ

`tgbt env` は bootstrap repair command であり、Plan / Ticket state machine の一部ではない。

* `tgbt env` は repository lock を取得しうる state-mutating command だが、Plan state を生成・遷移させない
* `tgbt env` は Plan file / Ticket file / session record / run log を生成しない
* `tgbt env` の成功は repo-local runtime の合法化を意味し、`draft` / `running` / `settled` のいずれにも対応付けない

---

## 4. Ticket State Machine

### 4.1 状態一覧

Ticket の状態は以下とする。

* `todo`
* `running`
* `done`
* `settled`

### 4.2 各状態の意味

#### `todo`

未実行状態。

* AI により作成済み
* まだ実行されていない
* 依存が満たされれば実行候補になれる

#### `running`

実行中状態。

* その Ticket に対する agent 実行が進行中である
* 同一 Ticket を重複実行してはならない

#### `done`

その Ticket に対する agent 実行が終了し、実行結果サマリー、実行ログ、必要な session record の保存まで完了した状態。

重要なのは、`done` は「agent 実行が終わったうえで、必要な監査証跡の永続化まで完了した」ことを表し、成功・失敗の区別自体は別 metadata で表すことだという点である。

#### `settled`

その Ticket の実行結果に対して、必要なフォローアップ Ticket 作成まで完了した終端状態。

* フォローアップ不要なら `done` 直後に `settled` へ進んでよい
* フォローアップが必要なら、作成後に `settled` へ進む

### 4.3 許可される遷移

* `todo -> running`
* `running -> done`
* `done -> settled`

MVP では `blocked` / `failed` を Ticket 状態値として持たない。
失敗情報は状態ではなく execution outcome と run log に表す。

### 4.4 開始条件

Ticket を `running` にしてよいのは、以下をすべて満たすときのみである。

* 対応する Plan が `running` であること
* Ticket が `todo` であること
* Ticket が active Ticket であること
* `depends_on` に列挙されたすべての依存 Ticket が `required_state` を満たしていること

### 4.5 `done` の条件

Ticket を `done` にしてよいのは、少なくとも以下を満たすときのみである。

* Ticket に対する wrapper 呼び出しが終了していること
* 業務レベル出力契約に従う `ticket_execution` payload が妥当であること
* 実行結果サマリーが Ticket file に書き戻されていること
* 実行ログが保存されていること
* session record が必要な場合は保存されていること

### 4.6 `settled` の条件

Ticket を `settled` にしてよいのは、少なくとも以下を満たすときのみである。

* Ticket が `done` であること
* その実行結果に対する `followup_planning` payload が妥当であること
* `followup_planning.settle_source_ticket == true` であること
* 必要な follow-up Ticket が作成済みであること、または不要であることが明示されていること

---

## 5. Ticket 依存の解釈

### 5.1 依存の source

依存グラフは Ticket に記載された依存情報を正本として解決する。

Plan から直接依存グラフを推論してはならない。

### 5.2 `required_state`

各依存は `ticket_id` と `required_state` の組で表現する。

MVP では、`required_state` として **`settled` のみを許可する**。

理由は、本仕様の run が Ticket を直列実行し、`done` 到達後ただちに follow-up 整理を行って `settled` に進めるためである。

このため `todo` / `running` / `done` を依存条件として許可すると、仕様上は妥当でも実行時には観測不能または到達不能な依存を作れてしまう。

### 5.3 依存グラフの妥当性

active Ticket 集合に対する依存グラフは、少なくとも以下を満たさなければならない。

* `depends_on` に列挙された各 `ticket_id` が解決可能であること
* `required_state` が `settled` であること
* 循環依存が存在しないこと

これらを満たさない場合、`run` は依存不整合として失敗しなければならない。

---

## 6. `run` と状態更新の関係

### 6.1 Ticket 生成フェーズ

`run` 中の Ticket 生成フェーズでは、AI は対象 Plan と active Ticket 群を参照し、必要に応じて新規 Ticket を作成する。

このとき新規 Ticket の初期状態は `todo` とし、Plan の現在 `plan_revision` を引き継ぐ。

### 6.2 Ticket 実行フェーズ

`run` 中の Ticket 実行フェーズでは、依存解決済みの `todo` Ticket を 1 件選び、`running` に遷移させて実行する。

選択規則は決定的でなければならない。MVP では、**runnable な `todo` Ticket のうち最小の `ticket_id` を選ぶ**。

### 6.3 実行結果反映フェーズ

Ticket の agent 実行が終了したら、実行結果サマリーを Ticket に追記し、実行ログおよび必要な session record の保存まで完了したときにのみ、`done` に遷移させる。

成功・失敗・追加対応要否などは状態値ではなく metadata で表す。

### 6.4 フォローアップ整理フェーズ

`done` Ticket に対して follow-up Ticket 作成有無を判定し、必要なものを作成した後、その Ticket を `settled` に遷移させる。

### 6.5 runnable 不在時の扱い

runnable な `todo` Ticket が 0 件で、かつ unsettled active Ticket が残る場合、`run` は依存不整合または行き詰まりとして失敗しなければならない。

### 6.6 repository lock の扱い

同一 repository に対する state-mutating `tgbt` は 1 本だけ許可される。

既に lock を取得した別コマンドが存在する場合、新しい `run` は開始してはならない。

### 6.7 暴走防止の hard limit

MVP では、`run` に以下の hard limit を設ける。

* `max_run_loop_count = 512`
* `max_new_ticket_count_per_run = 256`

`max_run_loop_count` は、`run` の外側反復が 1 周進むたびに 1 増加する。
`max_new_ticket_count_per_run` は、その run 中に新規作成した Ticket 総数であり、初回 planning と follow-up planning の両方を含む。

これらのいずれかに達した時点で、その `run` は失敗として強制停止しなければならない。MVP では進捗不変判定は導入しない。

---

## 7. 失敗時の扱い

### 7.1 基本方針

state-mutating command が非 0 終了した場合、またはプロセスが中断した場合、その repository state は restore 前提の未定義状態とする。

したがって、以下を support 対象外とする。

* stale な `running` Ticket を自動補正して継続すること
* `running` の Plan をそのまま再開すること
* 部分更新済み repository を人手で少し直して継続実行すること

### 7.2 実運用上の扱い

失敗後の正規手順は以下である。

1. repository 全体を既知の安全な snapshot へ restore する
2. 他の `tgbt` プロセスが存在しないことを確認する
3. stale lock が残っていれば除去する
4. 入力や指示を見直して retry する

### 7.3 hard limit 到達時の扱い

`max_run_loop_count` または `max_new_ticket_count_per_run` に達した場合も、その top-level `run` は失敗である。

MVP では、hard limit 到達後の途中状態から継続する契約は持たない。通常の失敗と同様に restore 前提で扱う。

---

## 8. live / stub 共通原則

* `codex_cli_mode` が `live` でも `stub` でも、Plan / Ticket の業務状態値は同じでなければならない
* `stub` だから状態判定を緩めてはならない
* live と stub の差は、外部呼び出しの有無と session record の取得方法に限定する
* strict replay においても wrapper 呼び出し列の順序と identity は変えてはならない
* 通常の自動 stub テストでは、これらの前提条件を test harness / fixture が自己完結に満たすことを期待する
