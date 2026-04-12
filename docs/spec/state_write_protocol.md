# `ticket_guys_b_team` State Write Protocol

## 1. 文書の目的

本書は `ticket_guys_b_team` における front matter と state file の安全な書き換え規則を定義する。

対象は以下とする。

* authoritative mutable state の所有権
* AI 出力を canonical state へ反映する方法
* 単一ファイルの atomic write-replace 規則
* 複数ファイル mutation の扱い
* 異常終了時の失敗モデル

本書は「どう保存するか」を扱う。共通前提は `common_invariants.md`、Plan / Ticket file format は `file_format.md`、運用 artifact は `operational_artifacts.md`、状態遷移は `state_machine.md`、Codex request / result 契約は `codex_cli_wrapper.md` を参照する。

---

## 2. 基本原則

* canonical state を commit してよいのは application のみとする
* AI は canonical markdown を直接書き換えてはならず、構造化された proposal payload だけを返す
* authoritative mutable file の in-place overwrite を禁止する
* authoritative mutable file の公開は validate 済み candidate に対する atomic write-replace でのみ行う
* 複数ファイル更新に対する論理的 atomicity は提供しない
* execution log、env audit log、session record は監査証跡であり、rollback 対象として扱わない
* state-mutating command の失敗後の扱いは `common_invariants.md` の restore 契約に従う

---

## 3. ファイル分類

### 3.1 authoritative mutable state

以下は現在状態の正本であり、本書の commit 規則に従って書き換えなければならない。

* `.tgbt/plans/*.md`
* `.tgbt/tickets/*.md`
* `.tgbt/system/counters.json`

### 3.2 control artifact

以下は状態更新の制御用 artifact である。

* `.tgbt/system/locks/repository.lock.json`
* `.tgbt/.codex/config.toml`
* `.tgbt/instructions.md`

### 3.3 audit artifact

以下は監査証跡であり、現在状態の正本ではない。

* `.tgbt/logs/*.jsonl`
* `.tgbt/codex/*.json`

### 3.4 temporary / candidate file

atomic write-replace の途中で使う temp file は、target と同一 directory かつ同一 filesystem 上に配置しなければならない。

temp file は commit 成功後に残してはならない。途中失敗で残留した temp file は state の正本として扱ってはならず、後続処理で best-effort cleanup を行ってよい。

---

## 4. ownership と AI proposal の扱い

### 4.1 canonical file の所有者

Plan / Ticket の canonical file は application が render する。

application は少なくとも以下を所有する。

* front matter 全体
* 必須 section の骨格と順序
* `plan_id` / `plan_revision` / `ticket_id`
* `status`
* `created_at` / `updated_at` / `settled_at`
* `depends_on` の正規化済み表現
* artifact path の記録

ここで記録する artifact path は、filesystem absolute path とする。

AI は canonical markdown 全文を正本として返してはならない。

### 4.2 Codex CLI 呼び出しとしての具体化

`codex_cli_wrapper.md` で定義する business output は、canonical markdown ではなく proposal payload として扱う。

MVP の call purpose では、application は少なくとも以下のように payload を section へ写像する。

* `plan_drafting.title` → Plan の `title`
* `plan_drafting.sections.purpose` → Plan の `目的`
* `plan_drafting.sections.out_of_scope` → Plan の `スコープ外`
* `plan_drafting.sections.deliverables` → Plan の `成果物`
* `plan_drafting.sections.constraints` → Plan の `制約`
* `plan_drafting.sections.acceptance_criteria` → Plan の `受け入れ条件`
* `plan_drafting.sections.open_questions` → Plan の `未確定事項`
* `plan_drafting.sections.risks` → Plan の `想定リスク`
* `plan_drafting.sections.execution_strategy` → Plan の `実行方針`
* `ticket_planning.tickets[].title` → Ticket の `Title`
* `ticket_planning.tickets[].purpose` → Ticket の `Purpose`
* `ticket_planning.tickets[].depends_on` → Ticket の `Dependencies`
* `ticket_planning.tickets[].execution_instructions` → Ticket の `Execution Instructions`
* `ticket_execution.summary` → Ticket の `Run Summary`
* `ticket_execution.generated_artifacts` → Ticket の `Artifacts`
* `ticket_execution.followup_hints` → Ticket の `Follow-up Notes`
* `followup_planning.tickets[]` → follow-up Ticket の `Title` / `Purpose` / `Dependencies` / `Execution Instructions`

したがって、実装上は「本文セクション文章を JSON object として受け取り、application が parse / validate したうえで canonical markdown に埋め込む」という形を正規とする。
`ticket_execution.generated_artifacts` に含まれる path は filesystem absolute path とし、application は Ticket の `Artifacts` へそのまま反映する。

### 4.3 許可される更新粒度

application は AI proposal をそのまま丸ごと採用してはならない。

少なくとも以下を守ること。

* immutable field は application 側で保持し、AI proposal から更新してはならない
* 許可された field だけを current state に merge する
* merge 後の candidate 全体に対して validation を再実行する
* validation 失敗時は canonical path に公開してはならない

---

## 5. validation 規則

authoritative mutable state に入る candidate は、commit 前に最低限以下の validation を通過しなければならない。

### 5.1 構文 validation

* UTF-8 として読めること
* Markdown front matter / JSON として parse できること
* 必須 field が欠落していないこと

### 5.2 schema validation

* `status` が許可 enum に入っていること
* `plan_revision` と counter 値が整数範囲内であること
* `depends_on.required_state == settled` を満たすこと
* 必須 section が正しい順序で存在すること

### 5.3 invariant validation

* immutable field が不正に変更されていないこと
* `updated_at >= created_at` を満たすこと
* `plan_revision` が巻き戻っていないこと
* `ticket_id` が既存と衝突していないこと
* `state_machine.md` で許可された遷移に一致すること

### 5.4 referential validation

* 依存先 Ticket が存在すること
* active Ticket 定義と矛盾しないこと
* follow-up Ticket 作成結果が source Ticket の state change と整合すること

---

## 6. 単一ファイル write-replace 規則

### 6.1 適用対象

以下の authoritative mutable file には本規則を必須適用する。

* Plan file
* Ticket file
* `counters.json`

### 6.2 禁止事項

* target file の in-place overwrite
* 「存在確認してから rename / create」方式
* validate 前の candidate 公開
* 別 filesystem 上で生成した temp file の cross-device move

### 6.3 commit 手順

単一ファイル更新は少なくとも以下の順で行う。

1. current state から candidate content を構築する
2. candidate を parse / validate する
3. target と同一 directory に temp file を新規作成する
4. temp file へ candidate content を完全に書き出す
5. 可能なら flush / fsync 相当を行う
6. target path に対して atomic replace primitive を実行する
7. 可能なら parent directory に対して durability 確保を行う
8. commit 後に temp file が残っていれば cleanup する

atomic replace primitive は、少なくとも同一 volume / filesystem 内で「旧内容か新内容のどちらかだけが見える」意味論を持たなければならない。

### 6.4 create-only file の扱い

`repository.lock.json`、execution log、session record の初回作成は write-replace ではなく、原子的な non-overwrite create で行わなければならない。

---

## 7. 複数ファイル mutation の扱い

### 7.1 基本方針

複数ファイル mutation でも、各 target への publish 自体は個別の atomic write-replace または atomic create で行う。

ただし repository 全体としての論理的 atomicity は与えない。したがって、途中失敗時には「一部の file だけが新状態で、他は旧状態」という中間状態が観測されうる。

### 7.2 実装上の最低要件

state-mutating command は、command 全体の candidate 一式を最初の publish 前にすべて確定しなくてもよい。

その代わり、publish は **phase 単位**で扱い、各 phase で実際に公開する artifact 群について、publish 前に少なくとも以下を済ませること。

* 当該 phase に必要な current state 読み取り
* 当該 phase で公開する candidate 群の構築
* 当該 phase の candidate 群に対する validation
* repository lock が必要な command では、その lock 取得

後続 phase が wrapper 出力や follow-up planning 結果に依存する場合、その依存 payload を取得して validation 完了する前に、当該 payload に依存する authoritative mutable state を publish してはならない。

これにより、「その phase で避けられた validation failure によって publish 後に止まる」類の avoidable failure を減らす。

### 7.3 publish 順序

複数ファイル mutation の publish 順序は implementation-defined でよいが、同じ入力と同じ current state に対して決定的であることが望ましい。

推奨は以下である。

* まず audit artifact を保存してよい
* ID 予約や wrapper 実行記録に必要な `counters.json`、lock file、audit artifact は、後続 phase の authoritative mutable state より先に publish してよい
* authoritative mutable state は、command ごとに定めた決定的順序で publish する
* wrapper 出力や follow-up planning 結果に依存する authoritative mutable state は、対応する payload の validation 完了後にのみ publish してよい
* `counters.json` を更新する command では、採番済み番号の再利用を避けるため、`counters.json` を早い段階で publish してよい

### 7.4 途中失敗時の扱い

state-mutating command が非 0 終了した場合、またはプロセスが中断した場合、その repository state は `tgbt` の継続実行対象外とする。

`tgbt` は次回起動時に内部 rollback や自動 recovery を試みない。ユーザーは以下を実行しなければならない。

1. repository 全体を既知の安全な snapshot へ restore する
2. stale な `repository.lock.json` が残っていれば、他プロセスが停止していることを確認したうえで除去する
3. 指示または入力を見直して retry する

---

## 8. command ごとの推奨 publish 単位

### 8.1 `tgbt env`

`tgbt env` は Plan / Ticket の authoritative mutable state を更新してはならない。
更新対象は bootstrap repair に必要な control artifact と audit artifact に限定する。
`env-latest.jsonl` の freshness 制御のため、既存 audit artifact の invalidation や除去を伴ってよい。

少なくとも以下の phase に分けて扱ってよい。

1. bootstrap 前 phase
   * `repository.lock.json`
   * 既存 `.tgbt/logs/env-latest.jsonl` の invalidation または除去
2. bootstrap repair phase
   * `.tgbt/.codex/config.toml`
   * `.tgbt/instructions.md`
3. bootstrap audit phase
   * `.tgbt/logs/env-latest.jsonl`

`env-latest.jsonl` は `docs/spec/operational_artifacts.md` の `Env Audit Log File Format` に従う bootstrap audit artifact とする。
これは `run` 用 execution log や session record ではなく、`tgbt env` の観測・補修・検証結果だけを publish するために使う。
より新しい invocation が開始された後に前回 invocation の file を canonical path に残してはならず、current invocation の audit artifact を保存できなかった場合は path が不在でもよい。

`AGENTS.md` と repository 直下 `.codex/` は観測対象だが、自動修正対象に含めてはならない。
`tgbt env` は one-shot command として扱い、Plan file、Ticket file、session record、run log を publish してはならない。

### 8.2 `plan` 新規作成

新規 Plan 作成でも repository lock を取得しなければならない。

少なくとも以下の phase に分けて扱ってよい。

1. wrapper 前 phase
   * `codex_call_id` を反映した `counters.json`
2. wrapper 実行 phase
   * `plan_drafting` session record の保存または strict replay
3. wrapper 後 phase
   * `plan_drafting` payload の validation
   * 新規 Plan file

新規 Plan file は `plan_drafting` payload の validation 完了後にのみ publish してよい。
publish は決定的順序で行えばよいが、`counters.json` は wrapper 実行前に publish してよい。

### 8.3 `tgbt plan docs --plan-id ...` による既存 Plan 更新

既存 Plan 更新でも、少なくとも以下の phase に分けて扱ってよい。

1. wrapper 前 phase
   * `codex_call_id` を反映した `counters.json`
2. wrapper 実行 phase
   * `plan_drafting` session record の保存または strict replay
3. wrapper 後 phase
   * `plan_drafting` payload の validation
   * 更新後の Plan file
   * 破棄または退避対象となる active Ticket 群
   * 必要なら関連 metadata

publish は決定的順序で行えばよいが、途中失敗時に repository 全体の一貫性は保証されない。

avoidable failure を減らすため、active Ticket 群の削除または退避は `plan_drafting` payload の validation が完了した後にのみ行ってよい。

### 8.4 `run` 開始

`run` 開始時は、少なくとも以下を扱う。

* `run_id` を反映した `counters.json`
* `repository.lock.json`
* `run_started` を含む execution log
* Plan の `status=running` 更新

### 8.5 Ticket 生成

Ticket 生成では、少なくとも以下を扱う。

* `ticket_id` 採番を反映した `counters.json`
* 新規 Ticket file
* 必要に応じて execution log

### 8.6 Ticket 実行結果反映

Ticket 実行の完了後は、少なくとも以下を扱う。

* execution log
* session record
* source Ticket の `Run Summary` / `Artifacts` 更新
* source Ticket の `status=done` 更新

このとき `Artifacts` に反映する path は absolute path として扱う。

### 8.7 follow-up 整理

follow-up 整理では、少なくとも以下を扱う。

* 必要なら新規 follow-up Ticket file
* source Ticket の `status=settled` 更新
* 必要に応じて execution log

ここでも source Ticket の settle と follow-up Ticket 作成に repository-wide atomicity はない。途中失敗時は restore 前提で扱う。

---

## 9. 保証すること / しないこと

### 9.1 本仕様が保証すること

* 各 authoritative mutable file は validate 済み candidate として atomic に publish されること
* canonical state の所有権は application にあり、AI proposal は構造化 payload としてのみ受け入れること
* repository lock により、同一 repository に対する state-mutating command は直列化されること
* 非正常終了後は restore が必要であることを明示的な契約にすること

### 9.2 本仕様が保証しないこと

* 途中クラッシュ直後に、複数 file が常に外部から完全に一貫して見えること
* transaction journal や preimage backup を用いた内部 rollback
* 異常終了後の自動 recovery
* restore なしで壊れた途中状態から継続実行できること
