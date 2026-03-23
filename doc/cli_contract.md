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
* 独立した `approve` コマンドは設けない

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
* `tgbt run`

MVP では `ticket` を独立コマンドにしない。Ticket の生成・更新・クローズは `run` の内部オーケストレーションが担う。
MVP では `status` / `state` / `review-queue` / `artifacts` を導入しない。

---

## 5. 共通契約

### 5.1 終了コード

* 正常終了時は 0 を返す
* 以下の異常系は非 0 を返す

  * 入力不正
  * Plan 不整合
  * Ticket 不整合
  * manifest 不整合
  * 実行失敗
  * ログ保存失敗

### 5.2 エラー出力方針

エラー表示は少なくとも以下を短く示す。

* 原因
* 影響範囲
* 次に取るべき行動

例:

```text
ERROR: --stub-manifest is required in stub mode
Impact: top-level run was not started
Next: rerun with --codex-cli-mode stub --stub-manifest <path>
```

### 5.3 永続化方針

* 成功時も失敗時も、可能な限り状態更新とログ保存を行う
* 実行時に起きた事実はログへ保存する
* Codex 呼び出しでは session record を保存する
* ログ保存自体に失敗した場合も、その失敗を標準エラー等へ可能な限り残す
* 現在状態の正本は front matter とする
* execution log と session record は監査証跡として扱う

### 5.4 出力方針

* 人間向けの簡潔な標準出力を返す
* 機械処理向けには JSON 出力を将来拡張してよい
* MVP では人間可読性を優先するが、ログと成果物パスが追跡できることを維持する
* 各コマンドは、更新または参照すべきファイルのパスを返す

### 5.5 モード用語

本仕様で扱う実行モードは `codex_cli_mode` のみである。

#### `codex_cli_mode`

内部の Codex 呼び出しをどう扱うかを表す。

* `live`
* `stub`

`run` は常に実行コマンドであり、dry-run / preflight / validate は現時点では提供しない。

---

## 6. `plan` コマンド

### 6.1 目的

人間要望から Plan を生成または更新する。

### 6.2 入力

以下のいずれかを受け付ける。

* 自然言語要求
* 既存 `plan_id` と追記指示

例:

```bash
tgbt plan "CLI で plan / run を扱えるようにしたい"
```

```bash
tgbt plan --plan-id plan-20260321-001 "stub manifest を追加する"
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
* `running` または `closed` の Plan を更新した場合も `draft` に戻す

### 6.5 Ticket 破棄規則

既存 Plan を更新した場合、その Plan に属する active Ticket 集合は破棄対象とする。

ここでいう active Ticket とは、少なくとも `artifacts/tickets/` 上で当該 `plan_id` に属する Ticket file を指す。

MVP では以下を許容する。

* active Ticket file を削除する
* active Ticket file を別保管先へ退避する

ただし、どちらの場合でも ticket id 採番は巻き戻してはならない。
execution log と session record は監査証跡として保持してよい。

### 6.6 失敗条件

* 出力先へ書き込めない
* 入力が空である
* 対象 `plan_id` が見つからない
* front matter 更新に失敗した
* active Ticket 破棄処理に失敗した

### 6.7 MVP 制約

* 必須セクションを並べたテンプレート草案生成に留めてよい
* 要望内容の深い自動解釈や高度な要件抽出は未実装でよい

---

## 7. `run` コマンド

### 7.1 目的

指定した Plan を起点に、必要 Ticket の生成、Ticket 実行、実行結果サマリー反映、フォローアップ Ticket 生成を反復し、Plan を完了まで進める。

### 7.2 入力

* `--plan-id <plan_id>`
* `--codex-cli-mode {live|stub}`
* `--stub-manifest <path>` (`stub` のとき必須)

例:

```bash
tgbt run --plan-id plan-20260321-001
```

```bash
tgbt run --plan-id plan-20260321-001 --codex-cli-mode stub --stub-manifest artifacts/stub_manifests/plan-20260321-001-run-0003.json
```

### 7.3 出力

* 更新後の Plan 状態
* 生成または更新された Ticket file の一覧
* 実行ログ保存先
* 主要な session record 保存先

例:

```text
Plan: plan-20260321-001
Status: running
Log: artifacts/logs/plan-20260321-001-run-0003.jsonl
Updated tickets:
- artifacts/tickets/worker-0001.md
- artifacts/tickets/worker-0002.md
```

完了時の例:

```text
Plan: plan-20260321-001
Status: closed
Log: artifacts/logs/plan-20260321-001-run-0003.jsonl
```

### 7.4 前提条件

* Plan file が存在すること
* Plan front matter が妥当であること
* Plan status が `draft` または `running` であること
* `stub` のときは stub manifest が存在し、読み取り可能で、schema 互換であること

### 7.5 高水準アルゴリズム

`run` は少なくとも以下を反復する。

1. Plan と既存 Ticket 群を見て、新規 Ticket が必要か判断する
2. 必要なら新規 Ticket を 0 件以上作成する
3. 依存解決済みの `todo` Ticket を選んで実行する
4. 実行結果サマリーを Ticket に反映し、その Ticket を `done` にする
5. `done` Ticket の follow-up 要否を整理する
6. 必要な follow-up Ticket を作成した後、元 Ticket を `closed` にする
7. 新規 Ticket 作成不要かつ active Ticket がすべて `closed` なら Plan を `closed` にして終了する

### 7.6 Ticket 生成契約

* 1 Plan から生成される Ticket 枚数は固定しない
* 新規 Ticket の枚数と内容は AI が判断する
* Ticket id は `worker-0001` のような単調増加採番とし、巻き戻さない
* 依存グラフは Ticket の `depends_on` 記述を正本として解決する

### 7.7 Ticket 実行契約

* 実行対象は `todo` Ticket に限る
* 対象 Ticket の依存が満たされたときのみ実行してよい
* MVP では直列実行を既定としてよい
* agent 実行が終了したら、成功・失敗を問わず、結果サマリーを書き戻せた Ticket は `done` に遷移してよい
* その後、follow-up Ticket 整理が済んだら `closed` に遷移する

### 7.8 stub 契約

`stub` モードでは top-level `run` が内部で複数回の Codex 呼び出しを行う可能性があるため、単一 `--stub-record` は用いない。

代わりに `--stub-manifest` を受け取り、orchestration 層が manifest に従って各 wrapper 呼び出しへ単一 `stub_record_path` を配る。

要件:

* `--stub-manifest` は `stub` 時に必須
* manifest は wrapper 呼び出し順に消費される
* manifest の `call_purpose` は現在の呼び出し目的と整合していなければならない
* manifest が不足した場合、その `run` は失敗とする

### 7.9 失敗条件

* Plan file が存在しない
* Plan status が `closed` である
* front matter が壊れている
* active Ticket 群の読み取りに失敗した
* Ticket file の生成または更新に失敗した
* `stub` 時に manifest 指定がない
* manifest schema が不正である
* manifest が途中で不足する
* wrapper 実行前 validation に失敗した
* 実行ログ保存に失敗した

### 7.10 失敗時の状態更新

* Ticket 実行前に失敗した場合、その Ticket は `todo` のままでよい
* Ticket 実行が終了し、結果サマリーを書き戻せた場合、その Ticket は `done` にしてよい
* top-level `run` が途中失敗した場合、Plan は `running` のまま残してよい

### 7.11 MVP 制約

* active Ticket の集約表示専用コマンドは持たない
* Ticket 実行の並列化は必須ではない
* 自動受け入れゲートの厳密仕様は本契約に含めない

---

## 8. 返却メッセージの推奨トーン

CLI は簡潔で、人間が次の行動を理解できる出力を返す。

望ましい性質:

* 短い
* 失敗理由が明確
* 保存先がすぐ分かる
* 再実行時に必要な引数が分かる

