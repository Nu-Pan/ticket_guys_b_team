# `ticket_guys_b_team` Codex CLI Wrapper Specification

## 1. 文書の目的

本書は `ticket_guys_b_team` において `codex exec` をラップするコンポーネントの仕様を定義する。

対象は以下とする。

* wrapper の責務
* live / stub モードの定義
* 共通 request / result モデル
* live 記録の保存方法
* stub による replay 方法
* CLI / 状態遷移 / ファイル形式との接続点

本書は wrapper 境界の仕様に集中し、Plan / Ticket の状態遷移や CLI の全体契約は別文書を参照する。

---

## 2. 背景

worker Ticket の実行では、最終的に `codex exec` を呼び出したい。
しかし application 層から直接 `codex exec` を呼ぶ設計にすると、以下の問題が起きやすい。

* テスト時に外部依存が強すぎる
* token 消費や実行時間が大きい
* live 実行の入出力を再現しづらい
* CLI 層と process spawn の責務が混ざる
* 回帰テスト時に過去パターンを再利用しづらい

そのため、`codex exec` は wrapper で抽象化し、live / stub の切替を wrapper の責務として閉じ込める。

---

## 3. 用語定義

### 3.1 wrapper

`codex exec` 呼び出しを抽象化するコンポーネント。
外部からは共通の request を受け取り、共通の result を返す。

### 3.2 live モード

実際に `codex exec` を起動するモード。
本番用の既定モードである。

### 3.3 stub モード

`codex exec` を起動せず、既存の session record を読み出して result を返すモード。
テスト用モードである。

### 3.4 session record

wrapper 呼び出しの request / response を保存した JSON artifact。
live 実行の記録であり、stub の再生元にもなる。

### 3.5 replay

session record の内容を使って、process spawn なしに result を再現すること。

---

## 4. 設計原則

* application 層は `codex exec` を直接呼ばない
* live / stub で返却型を変えてはならない
* live 記録は stub でそのまま再利用できなければならない
* wrapper は監査記録とテスト再現性の両方を支える
* secret を不用意に記録してはならない
* session record の schema 変更は後方互換性を意識する
* `--stub-record` 明示指定を必須とし、自動推定をしない

---

## 5. wrapper の責務

wrapper は少なくとも以下を担う。

* `codex exec` 向け request の正規化
* live / stub の分岐
* live 実行時の process spawn
* stdout / stderr / return code / last message の収集
* session record の保存
* stub 時の record 読み込みと replay
* 呼び出し結果の共通 result 化

wrapper が担わないものは以下とする。

* Plan / Ticket の状態遷移決定
* 受け入れゲートの最終判定
* CLI の parse / pretty print
* Ticket のスケジューリング

---

## 6. application 層から見た公開インターフェース

実装形式は class, protocol, function object のいずれでもよいが、意味論としては以下を満たすこと。

```python
class CodexCliWrapper(Protocol):
    def execute(self, request: CodexCliRequest) -> CodexCliResult:
        ...
```

---

## 7. `CodexCliRequest` の必須概念

`CodexCliRequest` は少なくとも以下を表現できること。

* `ticket_id`
* `plan_id`
* `run_id`
* `codex_call_id`
* `codex_cli_mode`
* `cwd`
* `prompt_text`
* `model`
* `reasoning_effort`
* `stub_record_path | None` (`codex_cli_mode=stub` のとき必須)

必要に応じて以下を持ってよい。

* `input_files`
* `timeout_sec`
* `extra_args`
* `env_allowlist`
* `metadata`

---

## 8. `CodexCliResult` の必須概念

`CodexCliResult` は少なくとも以下を表現できること。

* `ticket_id`
* `run_id`
* `codex_call_id`
* `codex_cli_mode`
* `returncode`
* `stdout`
* `stderr`
* `last_message_text`
* `session_record_path`
* `replayed_from | None`
* `generated_artifacts`
* `stop_reason`

必要に応じて以下を持ってよい。

* `raw_command`
* `duration_ms`
* `warnings`
* `truncated_fields`

---

## 9. live モード

### 9.1 目的

本当に `codex exec` を起動し、worker 実行を進める。

### 9.2 動作

少なくとも以下の順で処理する。

1. request を検証する
2. `codex exec` の argv を構築する
3. process を起動する
4. stdout / stderr / return code を収集する
5. 最終メッセージ文字列を抽出する
6. session record を `artifacts/codex/` に保存する
7. 共通 result を返す

### 9.3 既定値

* `tgbt run` における既定 `codex_cli_mode` は `live`
* user が明示的に `stub` を選ばない限り `live` を使う

### 9.4 保存要件

live 実行で保存する session record は、追加変換なしで stub source として読めなければならない。

---

## 10. stub モード

### 10.1 目的

`codex exec` を起動せず、過去記録を返してテストを成立させる。

### 10.2 動作

少なくとも以下の順で処理する。

1. request に `stub_record_path` が明示指定されていることを検証する
2. 指定された record を読み込む
3. record schema を検証する
4. record の result を共通 result に復元する
5. 必要なら現在 run 用 session record を新規保存してもよい
6. 共通 result を返す

### 10.3 重要制約

* process spawn を行ってはならない
* network / token 消費を発生させてはならない
* 返却される result の意味は live と同一でなければならない

---

## 11. stub replay source の明示指定

`stub` モードでは replay source の明示指定を必須とする。

要件:

* request の `stub_record_path` が指定されていなければならない
* wrapper は Ticket metadata、prompt 内容、既定パス、最新成功 record などから自動推定してはならない
* 指定された path は存在し、読み取り可能で、schema 互換でなければならない
* 失敗理由は人間が読める形で返さなければならない

この方針により、stub は「何となく近い応答を返すモード」ではなく、特定 record の replay モードとして扱う。

---

## 12. live 記録を stub に転用する仕組み

### 12.1 要件

* live session record は、そのまま stub source として使えること
* 変換専用コマンドを必須にしてはならない
* stub 実行時に元 record を破壊してはならない

### 12.2 推奨運用

1. 開発者が live で worker を 1 回実行する
2. `artifacts/codex/...json` が保存される
3. テストではその path を `--stub-record` に渡す
4. wrapper は同 record を replay する

---

## 13. error model

wrapper は少なくとも以下を区別できることが望ましい。

* `CodexSpawnError`
* `CodexExecutionError`
* `StubRecordRequiredError`
* `StubRecordNotFoundError`
* `StubRecordSchemaError`
* `SessionRecordWriteError`

application 層はこれらを `blocked` または `failed` に写像できればよい。

---

## 14. logging / artifacts との接続

wrapper 実行時、少なくとも以下の事実を execution log へ反映できることが望ましい。

* wrapper 開始
* wrapper 終了
* `codex_cli_mode`
* `session_record_path`
* `replayed_from`
* `returncode`

artifact としては少なくとも以下を生成できることが望ましい。

* `artifacts/codex/<ticket_id>-<run_id>-<codex_call_id>.json`

MVP では別個の last message file を必須にしない。
最終メッセージは session record の `last_message_text` から取得する。

---

## 15. secret / privacy 取り扱い

session record に以下を無加工で保存してはならない。

* API key
* access token
* 秘密の環境変数
* 私密なローカルパスが不要に露出する情報

必要に応じて、保存前にマスクまたは除去を行う。
