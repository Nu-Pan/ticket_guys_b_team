# `ticket_guys_b_team` State Machine Specification

## 1. 文書の目的

本書は `ticket_guys_b_team` における主要オブジェクトの状態遷移を定義する。

対象は以下とする。

* Plan の状態遷移
* Ticket の状態遷移
* Ticket 依存と開始条件
* `run` における反復オーケストレーションと状態変化の関係

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

1. Plan と既存 Ticket 群を見て、新規 Ticket が必要か判断する
2. 必要なら新規 Ticket を作成する
3. 実行可能な `todo` Ticket を実行する
4. 実行結果を Ticket に要約として書き戻す
5. 実行結果を踏まえてフォローアップ Ticket を作成する
6. フォローアップ作成済みの Ticket を `closed` にする

### 2.3 `approve` 状態は持たない

MVP では Plan の独立した `approved` 状態を持たない。

Plan を実行に移す意思決定は `run` 開始で表現する。

---

## 3. Plan State Machine

### 3.1 状態一覧

Plan の状態は以下とする。

* `draft`
* `running`
* `closed`

### 3.2 各状態の意味

#### `draft`

人間がレビュー・修正している状態。

* `tgbt plan` による作成直後は `draft`
* 既存 Plan を更新した場合も `draft`
* `draft` の Plan はまだ active run を持たない

#### `running`

Plan に対する `run` オーケストレーションが進行中、または進行途中で再開可能な状態。

* Ticket 生成と Ticket 実行がこの状態で行われる
* 一部 Ticket が `todo` / `running` / `done` でもよい

#### `closed`

Plan に対して新規 Ticket が不要であり、active Ticket 群がすべて閉じた最終状態。

* `todo` / `running` / `done` Ticket を残してはならない
* 再度変更したい場合は `tgbt plan --plan-id ...` で `draft` へ戻す

### 3.3 許可される遷移

* `draft -> running`
* `running -> closed`
* `running -> draft`
* `closed -> draft`

### 3.4 遷移規則

#### `draft -> running`

`run --plan-id ...` 開始時に遷移してよい。

条件:

* Plan file が存在すること
* 必須 front matter が妥当であること
* stub 実行時は stub manifest が妥当であること

#### `running -> closed`

以下をすべて満たしたときに遷移してよい。

* AI が「新規 Ticket 作成不要」と判断していること
* 対象 Plan に属する active Ticket が `closed` のみであること

#### `running -> draft` / `closed -> draft`

`plan --plan-id ...` によって Plan 本文が更新されたときに遷移してよい。

この遷移では、対象 Plan に属する active Ticket 集合を破棄し、以後の `run` で新しい Ticket 集合を作り直す。

---

## 4. Ticket State Machine

### 4.1 状態一覧

Ticket の状態は以下とする。

* `todo`
* `running`
* `done`
* `closed`

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

その Ticket に対する agent 実行が終了し、実行結果サマリーが Ticket に反映された状態。

重要なのは、`done` は「agent 実行が終わった」ことを表し、成功・失敗の区別自体は別 metadata で表すことだという点である。

#### `closed`

その Ticket の実行結果に対して、必要なフォローアップ Ticket 作成まで完了した最終状態。

* フォローアップ不要なら `done` 直後に `closed` へ進んでよい
* フォローアップが必要なら、作成後に `closed` へ進む

### 4.3 許可される遷移

* `todo -> running`
* `running -> done`
* `done -> closed`

MVP では `blocked` / `failed` を Ticket 状態値として持たない。
失敗情報は状態ではなく execution outcome と run log に表す。

### 4.4 開始条件

Ticket を `running` にしてよいのは、以下をすべて満たすときのみである。

* 対応する Plan が `running` であること
* Ticket が `todo` であること
* `depends_on` に列挙されたすべての依存 Ticket が `required_state` を満たしていること

### 4.5 `done` の条件

Ticket を `done` にしてよいのは、少なくとも以下を満たすときのみである。

* Ticket に対する wrapper 呼び出しが終了していること
* 実行結果サマリーが Ticket file に書き戻されていること
* 実行ログが保存されていること
* session record が必要な場合は保存されていること

### 4.6 `closed` の条件

Ticket を `closed` にしてよいのは、少なくとも以下を満たすときのみである。

* Ticket が `done` であること
* その実行結果に対するフォローアップ Ticket 作成の有無が確定していること
* 必要な follow-up Ticket が作成済みであること、または不要であることが明示されていること

---

## 5. Ticket 依存の解釈

### 5.1 依存の source

依存グラフは Ticket に記載された依存情報を正本として解決する。

Plan から直接依存グラフを推論してはならない。

### 5.2 `required_state`

各依存は `ticket_id` と `required_state` の組で表現する。

MVP では、依存先の既定 `required_state` を `closed` とすることを推奨する。

理由は、`done` 直後の Ticket はまだフォローアップ作成が終わっていない可能性があり、下流 Ticket の開始条件としては不十分なことがあるためである。

---

## 6. `run` と状態更新の関係

### 6.1 Ticket 生成フェーズ

`run` 中の Ticket 生成フェーズでは、AI は対象 Plan と既存 Ticket 群を参照し、必要に応じて新規 Ticket を作成する。

このとき新規 Ticket の初期状態は `todo` とする。

### 6.2 Ticket 実行フェーズ

`run` 中の Ticket 実行フェーズでは、依存解決済みの `todo` Ticket を選び、`running` に遷移させて実行する。

MVP では直列実行を既定としてよい。

### 6.3 実行結果反映フェーズ

Ticket の agent 実行が終了したら、実行結果サマリーを Ticket に追記し、`done` に遷移させる。

成功・失敗・追加対応要否などは状態値ではなく metadata で表す。

### 6.4 フォローアップ整理フェーズ

`done` Ticket に対して follow-up Ticket 作成有無を判定し、必要なものを作成した後、その Ticket を `closed` に遷移させる。

---

## 7. 失敗時の扱い

### 7.1 Ticket 実行前の失敗

stub manifest 不備、wrapper 起動前の validation error、ファイル書き込み失敗など、Ticket 実行前に失敗した場合は、その Ticket を `todo` のまま残してよい。

### 7.2 Ticket 実行後の失敗

agent 実行が終了し、その結果が失敗であっても、結果サマリーを書き戻せたなら Ticket は `done` に遷移してよい。

その後、必要に応じて follow-up Ticket を作成し、元 Ticket を `closed` に遷移させる。

### 7.3 stale `running`

プロセスクラッシュ等により stale な `running` Ticket が残る可能性はある。

MVP では自動復旧を必須とせず、front matter を手動で `todo` へ戻す、または実行ログを見て `done` へ補正する運用を許容する。

---

## 8. live / stub 共通原則

* `codex_cli_mode` が `live` でも `stub` でも、Plan / Ticket の業務状態値は同じでなければならない
* `stub` だから状態判定を緩めてはならない
* live と stub の差は、外部呼び出しの有無と session record の取得方法に限定する

