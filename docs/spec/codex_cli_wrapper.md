# `ticket_guys_b_team` Codex CLI Wrapper Specification

## 1. 文書の目的

本書は `ticket_guys_b_team` において `codex exec` をラップするコンポーネントの仕様を定義する。

対象は以下とする。

* wrapper の責務
* live / stub モードの定義
* 共通 request / result モデル
* Codex 業務レベル出力契約
* live 記録の保存方法
* stub による replay 方法
* model / reasoning_effort の供給源
* session record の redaction 方針
* CLI / 状態遷移 / ファイル形式との接続点

本書は wrapper 境界の仕様に集中し、Plan / Ticket の状態遷移や CLI の全体契約は別文書を参照する。canonical markdown の commit 手順は `state_write_protocol.md` を参照する。

---

## 2. 背景

`ticket_guys_b_team` の `plan` / `run` は、以下のような複数種類の Codex 呼び出しを行いうる。

* Plan 草案生成のための呼び出し
* Ticket 生成のための呼び出し
* Ticket 実行のための呼び出し
* follow-up Ticket 整理のための呼び出し

application 層から直接 `codex exec` を呼ぶ設計にすると、以下の問題が起きやすい。

* テスト時に外部依存が強すぎる
* token 消費や実行時間が大きい
* live 実行の入出力を再現しづらい
* CLI 層と process spawn の責務が混ざる
* 1 top-level `run` に複数回の Codex 呼び出しがあると stub の扱いが壊れやすい
* application が自由形式の自然言語出力を都度解釈すると、Plan / Ticket 更新ロジックが実装ごとに分岐する

そのため、`codex exec` は wrapper で抽象化し、live / stub の切替と構造化出力の validation を wrapper の責務として閉じ込める。

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

### 3.6 strict replay

current request と source record request を、**保存用 canonicalization と redaction** を適用したうえで比較し、`codex_cli_mode` / `stub_record_path` を除いて完全一致していることを検証したうえで replay すること。

### 3.7 top-level run

CLI の `tgbt run --plan-id ...` による 1 回のオーケストレーション。
1 top-level run は複数回の wrapper 呼び出しを含みうる。

### 3.8 business output

`call_purpose` ごとに schema が定義された、application 層が解釈するための構造化 payload。
自由形式テキストではなく JSON object として扱う。

---

## 4. 設計原則

* application 層は `codex exec` を直接呼ばない
* live / stub で返却型を変えてはならない
* live 記録は stub でそのまま再利用できなければならない
* wrapper は監査記録とテスト再現性の両方を支える
* wrapper は自由形式の自然言語ではなく、purpose ごとの business output を application へ返さなければならない
* wrapper が返す business output は proposal payload であり、canonical markdown そのものではない
* secret を不用意に記録してはならない
* session record の schema 変更は後方互換性を意識する
* stub では 1 wrapper 呼び出しにつき 1 `stub_record_path` の明示指定を必須とし、自動推定をしない
* stub は strict replay とし、近似的な応答再現を許容しない
* live 実行では `CODEX_HOME=<repo-root>/.tgbt/.codex` を使い、user-global な `~/.codex` と repository 直下 `.codex/` に依存してはならない
* live 実行では profile `tgbt-worker` を明示指定しなければならない
* `tgbt` が Codex CLI を起動する実行では skills と sub agent を使用してはならない
* MVP では model / reasoning_effort の task 別最適化を行わず、固定既定値と環境変数 override のみを許容する

---

## 5. wrapper の責務

wrapper は少なくとも以下を担う。

* `codex exec` 向け request の正規化
* live / stub の分岐
* live 実行時の process spawn
* stdout / stderr / return code / last message の収集
* purpose ごとの business output parse / validate
* proposal payload を application が canonical state へ写像できる形に保つこと
* session record の保存
* stub 時の record 読み込みと replay
* strict replay request 検証
* redaction 済みの共通 result 化

wrapper が担わないものは以下とする。

* Plan / Ticket の状態遷移決定そのもの
* Ticket 依存解決
* top-level run の反復制御
* stub source path の採番や ID 決定
* CLI の parse / pretty print
* Ticket id の実採番
* Plan front matter の最終決定

orchestration 層は、現在の request identity から canonical な `stub_record_path` を決定し、wrapper はそれを replay するだけとする。

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

* `plan_id`
* `plan_revision`
* `ticket_id | None`
* `run_id | None`
* `codex_call_id`
* `call_purpose`
* `codex_cli_mode`
* `cwd`
* `prompt_text`
* `model`
* `reasoning_effort`
* `stub_record_path | None` (`codex_cli_mode=stub` のとき必須)

path を表す request field は、少なくとも以下の意味論を満たすこと。

* `cwd` は filesystem absolute path
* `cwd` は top-level `tgbt` process 開始時の current working directory を absolute path 化したもの
* `stub_record_path` は filesystem absolute path

### 7.1 runtime の固定値

`CodexCliRequest` には field として露出しなくてよいが、live 実行時の wrapper は少なくとも以下を内部固定値として解決しなければならない。

* `CODEX_HOME = <repo-root>/.tgbt/.codex`
* `codex_profile = tgbt-worker`
* `model_instructions_file = <repo-root>/.tgbt/instructions.md`

`<repo-root>/.tgbt/instructions.md` は `tgbt env` が生成する repo-local runtime file であり、人間向け文書として扱ってはならない。
live 実行時の wrapper は、process spawn の直前に `.tgbt/.codex/config.toml` と `.tgbt/instructions.md` の runtime 契約を検証しなければならない。
wrapper は `.tgbt/instructions.md` の生成元として `docs/spec/*.md` や `AGENTS.md` を直接 copy source にしてはならない。
既存 runtime file の内容をそのまま信頼して継承してはならない。
また、repository 直下 `.codex/` や `.tgbt/.codex/` 配下の他 file を runtime 入力として参照してはならない。

### 7.2 `call_purpose` の値

MVP では以下のみを使用する。

* `plan_drafting`
* `ticket_planning`
* `ticket_execution`
* `followup_planning`

`ticket_id` は Ticket に直接紐づかない呼び出しでは `None` を許容する。
`plan_drafting` では `run_id = None` を許容する。

### 7.3 `model` / `reasoning_effort` の供給源

MVP では、orchestration 層が各 wrapper 呼び出しの前に resolved 値を request へ埋め込む。

解決順序は以下とする。

1. 環境変数 `TGBT_CODEX_MODEL`
2. 既定値 `gpt-5.2-codex`

`reasoning_effort` の解決順序は以下とする。

1. 環境変数 `TGBT_CODEX_REASONING_EFFORT`
2. 既定値 `high`

MVP では以下を要件とする。

* 1 top-level `run` の全 wrapper 呼び出しは、同じ resolved `model` / `reasoning_effort` を使うこと
* `plan` の 1 回の wrapper 呼び出しも、同じ解決規則で得た `model` / `reasoning_effort` を使うこと
* `reasoning_effort` は `minimal | low | medium | high | xhigh` のいずれかでなければならない
* 無効な override 値は fail-fast で拒否しなければならない
* purpose ごとの軽量化・重み付け最適化は行わない

resolved 値は strict replay identity の一部であり、session record に保存される。

### 7.4 `plan_drafting` request context

wrapper は `prompt_text` の内部 schema を parse / validate しなくてよい。
ただし、`plan_drafting` request を構築する orchestration 層は、Codex が call site ごとの判断材料を機械的に読めるよう、**構造化された入力コンテキスト** を `prompt_text` へ直列化しなければならない。

`tgbt plan docs` から発行する `plan_drafting` request では、`prompt_text` 内の入力コンテキストは少なくとも以下の意味論を保持しなければならない。

* `plan_kind = "docs"`
* `request_text`
* `target_scope = "docs"`
* `plan_identity = { plan_id, plan_revision }`
* 必要なら `existing_plan`

この request は human request を含んでよいが、application が構造化し、strict replay で同一性比較できる形に正規化しなければならない。

`existing_plan` を含める場合は、少なくとも以下を表現できなければならない。

* current `title`
* current `plan_revision`
* canonical section text 一式

`tgbt env` は Codex wrapper を呼び出さない bootstrap command であり、本節の request context 契約の対象外とする。

---

## 8. `CodexCliResult` の必須概念

`CodexCliResult` は少なくとも以下を表現できること。

* `plan_id`
* `plan_revision`
* `ticket_id | None`
* `run_id | None`
* `codex_call_id`
* `call_purpose`
* `codex_cli_mode`
* `returncode`
* `stdout`
* `stderr`
* `last_message_text`
* `business_output`
* `session_record_path`
* `replayed_from | None`
* `generated_artifacts`
* `stop_reason`
* `redaction_report`

`business_output` は、purpose ごとの schema に従う parse / validate 済みの object でなければならない。
また、path を表す result field は少なくとも以下の意味論を満たすこと。

* `session_record_path` は保存または参照した session record の filesystem absolute path
* `replayed_from` は strict replay source の filesystem absolute path
* `generated_artifacts` の各要素は filesystem absolute path

---

## 9. Codex 業務レベル出力契約

### 9.1 共通ルール

4 つの `call_purpose` について、Codex の最終メッセージは **単一の JSON object** でなければならない。

* Markdown fence を付けてはならない
* JSON の前後に説明文を付けてはならない
* top-level は object でなければならない
* `call_purpose` を payload 内にも明示し、request の `call_purpose` と一致しなければならない
* wrapper は parse と schema validation に失敗した場合、その呼び出しを失敗として扱わなければならない

各 payload は少なくとも以下の共通フィールドを含む。

* `schema_name`
* `schema_version`
* `call_purpose`
* `summary`

MVP の `schema_version` はすべて `1` とする。

application はこれらの payload を parse / validate したうえで current state に merge し、canonical file を render する。Codex に Plan / Ticket の canonical markdown 全文を business output として返させてはならない。

### 9.2 `plan_drafting` payload

`plan_drafting` は、人間要望と必要なら既存 Plan を見て、Plan 草案または更新後 Plan の proposal を返す。

schema:

```json
{
  "schema_name": "plan_drafting",
  "schema_version": 1,
  "call_purpose": "plan_drafting",
  "summary": "...",
  "title": "...",
  "sections": {
    "purpose": "...",
    "out_of_scope": "...",
    "deliverables": "...",
    "constraints": "...",
    "acceptance_criteria": "...",
    "open_questions": "...",
    "risks": "...",
    "execution_strategy": "..."
  }
}
```

要件:

* `title` は空文字列であってはならない
* `sections` は上記 8 keys をすべて含まなければならない
* `sections` の値は canonical Plan file の各 section を render するための proposal field として扱う
* application は immutable front matter を保持し、`title` と section proposal を current state に merge して canonical Plan markdown を render する
* Codex に canonical Plan markdown 全文を書かせてはならない

### 9.3 `ticket_planning` payload

`ticket_planning` は、Plan と active Ticket 群を見て、新規 Ticket が必要かを返す。

schema:

```json
{
  "schema_name": "ticket_planning",
  "schema_version": 1,
  "call_purpose": "ticket_planning",
  "summary": "...",
  "needs_new_tickets": true,
  "tickets": [
    {
      "client_ticket_ref": "new-1",
      "title": "...",
      "purpose": "...",
      "ticket_kind": "implementation",
      "depends_on": [
        {
          "ticket_ref": "worker-0001",
          "required_state": "settled"
        }
      ],
      "execution_instructions": "..."
    }
  ]
}
```

要件:

* `needs_new_tickets=false` のとき `tickets=[]` でなければならない
* `client_ticket_ref` は payload 内で一意でなければならない
* `depends_on[].ticket_ref` は、既存 `ticket_id` または同 payload 内の `client_ticket_ref` を参照してよい
* `depends_on[].required_state` は MVP では `settled` のみ許可する
* actual `ticket_id` の採番は orchestration 層が行う
* application は model が返した `client_ticket_ref` を actual `ticket_id` に解決して Ticket file を作成する
* `title` / `purpose` / `depends_on` / `execution_instructions` は canonical Ticket file の各 section を render するための proposal field として扱う

### 9.4 `ticket_execution` payload

`ticket_execution` は、1 Ticket の実行結果を返す。

schema:

```json
{
  "schema_name": "ticket_execution",
  "schema_version": 1,
  "call_purpose": "ticket_execution",
  "summary": "...",
  "execution_outcome": "succeeded",
  "generated_artifacts": [
    "<repo-root>/path/to/file"
  ],
  "followup_hints": [
    "..."
  ]
}
```

要件:

* `execution_outcome` は `succeeded | failed | needs_followup` のいずれかでなければならない
* `summary` は Ticket の `Run Summary` にそのまま転記できる長さと粒度を想定する
* `generated_artifacts` は filesystem absolute path とする
* `followup_hints` は `Follow-up Notes` を render するための補足情報であり、直接 Ticket を生成する権限は持たない
* application は `summary` / `generated_artifacts` / `followup_hints` を current Ticket state に merge し、canonical Ticket markdown を再 render する

### 9.5 `followup_planning` payload

`followup_planning` は、`done` Ticket を `settled` に進める前に、追加 Ticket の要否を返す。

schema:

```json
{
  "schema_name": "followup_planning",
  "schema_version": 1,
  "call_purpose": "followup_planning",
  "summary": "...",
  "followup_required": true,
  "settle_source_ticket": true,
  "tickets": [
    {
      "client_ticket_ref": "follow-1",
      "title": "...",
      "purpose": "...",
      "ticket_kind": "check",
      "depends_on": [
        {
          "ticket_ref": "worker-0007",
          "required_state": "settled"
        }
      ],
      "execution_instructions": "..."
    }
  ]
}
```

要件:

* `followup_required=false` のとき `tickets=[]` でなければならない
* `settle_source_ticket` は MVP では必須であり、`true` でなければならない
* application は必要な follow-up Ticket を作成し終えた後にのみ source Ticket を `settled` に進めてよい
* `tickets` の item schema は `ticket_planning` と同一とする
* `tickets[]` は follow-up Ticket の canonical markdown を render するための proposal field である

### 9.6 妥当でない出力の扱い

以下は wrapper 失敗とする。

* JSON parse 不能
* top-level が object でない
* `call_purpose` 不一致
* schema 必須 field 欠落
* enum 値不正
* `plan_drafting.title` が空である
* `plan_drafting.sections` の必須 key が欠落している
* `needs_new_tickets=false` なのに `tickets` が空でない
* `followup_required=false` なのに `tickets` が空でない
* `settle_source_ticket != true`

---

## 10. live モード

### 10.1 目的

本当に `codex exec` を起動し、Codex 呼び出しを進める。

### 10.2 動作

少なくとも以下の順で処理する。

1. request を検証する
2. repo-local runtime 設定を検証する
3. `codex exec` の argv を構築する
4. process を起動する
5. stdout / stderr / return code を収集する
6. 最終メッセージ文字列を抽出する
7. business output を parse / validate する
8. redaction を適用する
9. canonical path に session record を保存する
10. redaction 済みの共通 result を返す

repo-local runtime 設定の検証では、少なくとも以下を確認しなければならない。

* `CODEX_HOME` が `<repo-root>/.tgbt/.codex` を指すこと
* `<repo-root>/.tgbt/.codex/config.toml` が存在し、profile `tgbt-worker` を定義していること
* profile `tgbt-worker` が `model_instructions_file = "<repo-root>/.tgbt/instructions.md"` を指していること
* `.tgbt/instructions.md` の内容契約が `docs/spec/file_format.md` の Codex runtime 共通ルールと整合すること

### 10.3 既定値

* `tgbt plan` / `tgbt run` における既定 `codex_cli_mode` は `live`
* user が明示的に `stub` を選ばない限り `live` を使う

### 10.4 保存要件

live 実行で保存する session record は、追加変換なしで stub source として読めなければならない。

canonical 保存先の relative path は、`run_id != null` の呼び出しでは以下で決定しなければならない。

```text
.tgbt/codex/<scope>-<run_id>-<codex_call_id>-<call_purpose>.json
```

`<scope>` は以下とする。

* `ticket_id != null` のとき `<scope> = <ticket_id>`
* `ticket_id == null` のとき `<scope> = <plan_id>`

`plan_drafting` では以下を使う。

```text
.tgbt/codex/<plan_id>-rev-<plan_revision>-<codex_call_id>-plan_drafting.json
```

wrapper が result に格納する `session_record_path` は、上記 canonical 保存先を repository root から解決した filesystem absolute path としなければならない。

### 10.5 `codex exec` 起動契約

live 実行で wrapper が `codex exec` を起動するときは、少なくとも以下を満たさなければならない。

* process 環境変数 `CODEX_HOME` に `<repo-root>/.tgbt/.codex` を渡す
* argv で profile `tgbt-worker` を明示指定する
* runtime 指示は `model_instructions_file` 経由で `<repo-root>/.tgbt/instructions.md` を参照させる
* worker prompt または runtime 指示で skills 使用禁止を明示する
* worker prompt または runtime 指示で sub agent 使用禁止を明示する

---

## 11. stub モードと strict replay

### 11.1 目的

`codex exec` を起動せず、過去記録を返してテストを成立させる。

通常の `pytest` ベース stub テストでは、必要な source record と request identity を test harness / fixture が自己完結に用意し、テスト実行者は単にテストを実行すればよい状態を目指す。

### 11.2 動作と制約

少なくとも以下の順で処理する。

1. request に `stub_record_path` が明示指定されていることを検証する
2. 指定された record を読み込む
3. record schema を検証する
4. current request を保存用 canonicalization + redaction に通す
5. strict replay request 検証を行う
6. source record の result をもとに current result を構築する
7. 共通 result を返す

要件と制約は以下の通りとする。

* process spawn を行ってはならない
* network / token 消費を発生させてはならない
* 新しい session record を保存してはならない
* wrapper は Ticket metadata、prompt 内容、既定パス、最新成功 record などから source を自動推定してはならない
* 指定された path は存在し、読み取り可能で、schema 互換でなければならない
* source record の `request` と current request の canonicalized value は、`codex_cli_mode` と `stub_record_path` を除いて完全一致しなければならない
* source record の top-level identity (`plan_id`, `plan_revision`, `ticket_id`, `run_id`, `codex_call_id`, `call_purpose`) も current request と整合していなければならない
* 失敗理由は人間が読める形で返さなければならない
* 返却される result の意味は live と同一でなければならない

stub で返す `CodexCliResult` は、source record の result を土台にしつつ、少なくとも以下を current 実行文脈へ合わせて構築する。

* `codex_cli_mode = stub`
* `session_record_path = stub_record_path`
* `replayed_from = stub_record_path`

それ以外の identity フィールドは source record と current request が一致している前提で返す。

### 11.3 top-level `run` との関係

1 top-level `run` では複数回の wrapper 呼び出しが発生しうる。`plan` でも 1 回の wrapper 呼び出しが発生しうる。

本仕様では manifest を使わず、以下の責務分離を採る。

* CLI / orchestration 層: 現在の request identity から canonical な `stub_record_path` を決定する
* wrapper 層: 与えられた単一 `stub_record_path` を strict replay する

つまり、stub の最小単位は wrapper 呼び出しであり、top-level `run` はその複数回実行を束ねる。

この設計が成立する前提は、repository 状態、front matter、counters が再生対象 run 開始前の状態へ復元されていることである。

ただし、この前提は日常のテスト実行者に手動 restore を要求することを意味しない。通常の自動 stub テストでは、test harness / fixture が一時 directory と fixture data を用いて整合状態を構築してよい。

また、live session record はそのまま stub source として使えなければならず、変換専用コマンドを必須にしてはならない。stub 実行時に元 record を破壊してはならない。

---

## 12. session record の redaction 方針

### 12.1 基本原則

redaction は live 実行時の result 返却前、および session record 保存前に適用しなければならない。

したがって、stub で再生される値は redaction 済みである。MVP では、redaction によって fixture の期待値が変わる場合、テスト側を redaction 後の値へ合わせる。

### 12.2 redaction 対象 field

少なくとも以下に redaction を適用する。

* `request.prompt_text`
* `result.stdout`
* `result.stderr`
* `result.last_message_text`
* `result.business_output` 配下のすべての string leaf

`plan_id`、`ticket_id`、`run_id`、`codex_call_id`、`call_purpose`、path 文字列は原則 redaction しない。ただし URL 中の credential を含む場合は例外とする。

### 12.3 redaction rule 一覧

適用順は以下とする。

1. **PEM private key block**  
   `-----BEGIN ... PRIVATE KEY-----` から対応する `-----END ... PRIVATE KEY-----` までを `<REDACTED:PEM_PRIVATE_KEY>` に置換する
2. **Authorization header / bearer credential**  
   `Authorization:` header の credential 部分、および standalone の `Bearer <token>` を `<REDACTED:AUTH_CREDENTIAL>` に置換する
3. **Cookie / Set-Cookie**  
   `Cookie:` と `Set-Cookie:` の value 全体を `<REDACTED:COOKIE>` に置換する
4. **URL userinfo**  
   `scheme://user:pass@host` の `user:pass` を `<REDACTED:CREDENTIALS>` に置換する
5. **assignment / mapping 形式の secret 値**  
   key 名が大文字小文字を無視して `api_key | apikey | token | access_token | refresh_token | secret | client_secret | password | passwd | session` のいずれかに一致する場合、`KEY=VALUE`、`KEY: VALUE`、`"key": "value"` などの value を `<REDACTED:SECRET>` に置換する
6. **既知 token pattern**  
   少なくとも以下の pattern を `<REDACTED:TOKEN>` に置換する
   * `sk-[A-Za-z0-9_-]{20,}`
   * `gh[pousr]_[A-Za-z0-9]{20,}`
   * `github_pat_[A-Za-z0-9_]+`
   * `xox[baprs]-[A-Za-z0-9-]+`

MVP では entropy ベースの曖昧なヒューリスティック redaction を必須としない。

### 12.4 保存形式

wrapper は、redaction を適用した件数と rule 名を `redaction_report` に保持してよい。

4 つの call purpose に対しては、`last_message_text` は redaction 後 `business_output` の canonical JSON serialization を保存することを推奨する。これにより parse 済み payload と raw text 表現がずれにくくなる。

### 12.5 strict replay との関係

strict replay request 検証は、raw request 同士ではなく、**保存用 canonicalization + redaction 後の request** 同士で行う。

したがって、secret が異なる raw prompt でも、redaction 後 canonical request が一致するなら replay 可能である。MVP ではこの挙動を許容する。

---

## 13. error model

wrapper は少なくとも以下を区別できることが望ましい。

* `CodexSpawnError`
* `CodexExecutionError`
* `CodexBusinessOutputError`
* `StubRecordRequiredError`
* `StubRecordNotFoundError`
* `StubRecordSchemaError`
* `StubReplayMismatchError`
* `SessionRecordWriteError`

application 層はこれらを top-level run 失敗、または Ticket 実行結果 metadata に写像できればよい。

---

## 14. logging / artifacts との接続

wrapper 実行時、少なくとも以下の事実を execution log へ反映できることが望ましい。

* wrapper 開始
* wrapper 終了
* `plan_revision`
* `call_purpose`
* `codex_cli_mode`
* `session_record_path`
* `replayed_from`
* `returncode`
* `business_output.schema_name`
* `business_output.schema_version`

artifact としては少なくとも以下を生成または参照できることが望ましい。

* `run_id != null` のとき `.tgbt/codex/<scope>-<run_id>-<codex_call_id>-<call_purpose>.json`
* `plan_drafting` のとき `.tgbt/codex/<plan_id>-rev-<plan_revision>-<codex_call_id>-plan_drafting.json`

これらは repository 内の canonical 保存先を表す。execution log や `CodexCliResult` に露出する path 文字列は、対応する filesystem absolute path を用いる。

MVP では別個の last message file を必須にしない。
