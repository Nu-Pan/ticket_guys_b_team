# `ticket_guys_b_team` State Write Protocol

## 1. 文書の目的

本書は `ticket_guys_b_team` における front matter と state file の安全な書き換え規則を定義する。

対象は以下とする。

* authoritative mutable state の所有権
* AI 出力を canonical state へ反映する方法
* 単一ファイルの atomic write-replace 規則
* 複数ファイル更新の transaction 規則
* transaction journal と preimage backup の扱い
* rollback-first recovery 規則

本書は「どう保存するか」を扱う。ファイル schema は `file_format.md`、状態遷移そのものは `state_machine.md`、Codex 呼び出しの request / result 契約は `codex_cli_wrapper.md` を参照する。

---

## 2. 基本原則

* canonical state を commit してよいのは application のみとする
* AI は canonical markdown を直接書き換えてはならず、構造化された proposal payload だけを返す
* authoritative mutable file の in-place overwrite を禁止する
* authoritative mutable file の公開は validate 済み candidate に対する atomic write-replace でのみ行う
* 複数ファイル更新は transaction journal により論理的 atomicity を与える
* rollback の判断根拠は backup の有無ではなく transaction journal とする
* recovery 方針は rollback-first とする
* execution log と session record は監査証跡であり、rollback 対象にしない

---

## 3. ファイル分類

### 3.1 authoritative mutable state

以下は現在状態の正本であり、本書の commit 規則に従って書き換えなければならない。

* `artifacts/plans/*.md`
* `artifacts/tickets/*.md`
* `artifacts/system/counters.json`

### 3.2 control artifact

以下は状態更新の制御用 artifact である。

* `artifacts/system/locks/repository.lock.json`
* `artifacts/system/txns/*.json`
* `artifacts/system/backups/<txn_id>/...`

### 3.3 audit artifact

以下は監査証跡であり、現在状態の正本ではない。

* `artifacts/logs/*.jsonl`
* `artifacts/codex/*.json`

### 3.4 temporary / candidate file

atomic write-replace の途中で使う temp file は、target と同一 directory かつ同一 filesystem 上に配置しなければならない。

temp file は commit 成功後に残してはならない。途中失敗で残留した temp file は recovery から除外してよいが、後続処理で best-effort cleanup を行うことが望ましい。

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

AI は canonical markdown 全文を正本として返してはならない。

### 4.2 Codex CLI 呼び出しとしての具体化

`codex_cli_wrapper.md` で定義する business output は、canonical markdown ではなく proposal payload として扱う。

MVP の `run` 系 call purpose では、application は少なくとも以下のように payload を section へ写像する。

* `ticket_planning.tickets[].title` → Ticket の `Title`
* `ticket_planning.tickets[].purpose` → Ticket の `Purpose`
* `ticket_planning.tickets[].depends_on` → Ticket の `Dependencies`
* `ticket_planning.tickets[].execution_instructions` → Ticket の `Execution Instructions`
* `ticket_execution.summary` → Ticket の `Run Summary`
* `ticket_execution.generated_artifacts` → Ticket の `Artifacts`
* `ticket_execution.followup_hints` → Ticket の `Follow-up Notes`
* `followup_planning.tickets[]` → follow-up Ticket の `Title` / `Purpose` / `Dependencies` / `Execution Instructions`

したがって、実装上は「本文セクション文章を JSON object として受け取り、application が parse / validate したうえで canonical markdown に埋め込む」という形を正規とする。

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

`repository.lock.json`、execution log、session record、transaction journal の初回作成は write-replace ではなく、原子的な non-overwrite create で行わなければならない。

---

## 7. transaction 規則

### 7.1 目的

複数ファイル更新では、各ファイルが individually atomic でも repository 全体として矛盾した状態が見えうる。

そのため、本仕様では transaction journal を用いて論理的 atomicity を持たせる。

### 7.2 transaction journal の state

transaction journal の `state` は以下のいずれかとする。

* `preparing`
* `committing`
* `committed`
* `aborted`

### 7.3 transaction 開始前の前提

state-mutating command は、repository lock 取得後かつ新規 mutation 開始前に、未完了 transaction の有無を確認しなければならない。

`preparing` または `committing` の transaction が見つかった場合は、通常処理へ進む前に rollback-first recovery を完了させなければならない。

### 7.4 transaction の標準手順

複数ファイル mutation は少なくとも以下の順で行う。

1. repository lock を保持する
2. 未完了 transaction がないこと、または recovery 済みであることを確認する
3. `artifacts/system/txns/<txn_id>.json` を `state=preparing` で create する
4. 変更対象 authoritative file ごとに preimage backup の要否を確定する
5. 既存 file がある場合は preimage backup を保存する
6. すべての candidate content を構築し、validation を完了する
7. transaction journal を `state=committing` に更新する
8. 各 target を atomic write-replace または atomic create で公開する
9. transaction journal を `state=committed` に更新する

この手順では、authoritative mutable state の publish は `state=committing` 以降にのみ行ってよい。

### 7.5 transaction の粒度

少なくとも以下は 1 transaction として可視化しなければならない。

* 既存 Plan 更新時の `plan_revision` 更新と active Ticket 退避・破棄
* 採番を伴う Ticket 作成時の `counters.json` 更新と Ticket file 作成
* `done` source Ticket の settle と follow-up Ticket 作成
* Plan を `settled` にする最終更新

---

## 8. rollback-first recovery

### 8.1 基本方針

recovery 方針は rollback-first とする。

つまり、未完了 transaction を見つけた場合、実装は「途中まで進んだ変更を完了しようと推測する」のではなく、preimage backup を用いて transaction 開始前の authoritative state へ戻すことを優先する。

### 8.2 recovery 手順

少なくとも以下の順を守ること。

1. repository lock を保持する
2. `state in {preparing, committing}` の transaction journal を列挙する
3. 各 transaction の target 一覧と backup 情報を読む
4. preimage がある target は backup から atomic write-replace で restore する
5. preimage がない create-only target は削除または無効化する
6. transaction journal を `state=aborted` に更新し、`abort_reason=recovery_rollback` を残す
7. recovery が完了して初めて新しい mutation を開始する

### 8.3 rollback 対象外

以下は rollback 対象外とする。

* execution log
* session record
* 失敗した試行の監査情報

理由は、これらが「その試行があった」という事実の記録であり、現在状態の正本ではないためである。

### 8.4 recovery 失敗時

backup 不足、restore 失敗、journal 破損などにより rollback を完了できない場合、新しい state mutation は開始してはならない。

その command は fail-fast で停止し、人間に manual recovery を要求しなければならない。

---

## 9. command ごとの推奨 transaction 単位

### 9.1 `plan` 新規作成

新規 Plan 作成だけなら単一 file create で足りるが、実装簡素化のため transaction journal を使ってもよい。

### 9.2 `plan --plan-id ...` 更新

以下を 1 transaction とする。

* current Plan の読み込み
* `plan_revision` 増加
* Plan 本文の再 render
* 旧 revision の active Ticket 退避または破棄

### 9.3 `run` 開始

以下を 1 transaction とすることを推奨する。

* `run_id` 採番
* `counters.json` 更新
* Plan の `status=running` 化
* `last_run_id` / `updated_at` 更新

execution log の `run_started` は audit artifact なので transaction 外で作成してよい。

### 9.4 planning による Ticket 作成

以下を 1 transaction とする。

* `ticket_id` 群の採番
* `counters.json` 更新
* 新規 Ticket file 群の作成

### 9.5 Ticket 実行完了

session record と execution log は先に保存してよい。

その後、少なくとも以下を 1 transaction とする。

* Ticket file の `Run Summary` 更新
* `execution_outcome` 更新
* `generated_artifacts` 反映
* `status=done` への遷移

### 9.6 follow-up 整理と settle

以下を 1 transaction としなければならない。

* 必要な follow-up Ticket の採番
* `counters.json` 更新
* follow-up Ticket file 作成
* source Ticket の `status=settled` 化
* 必要なら Plan の `status=settled` 化

`done` source Ticket を先に `settled` にしてから follow-up Ticket を別 transaction で作ることは禁止する。

---

## 10. 保証と非保証

### 10.1 保証すること

* authoritative mutable file では途中書き込み済みの壊れた内容を公開しないこと
* 未完了 transaction は次回 mutation 前に rollback-first recovery の対象になること
* front matter と counters の commit は validation 済み candidate に限定されること
* audit artifact を壊さずに state だけを戻せること

### 10.2 保証しないこと

* クラッシュ直後に、transaction 中の複数 file が常に外部から完全に一貫して見えること
* stale lock の自動除去
* audit artifact の完全無欠な削除や巻き戻し

本仕様が保証するのは、「途中クラッシュ後も recovery を経れば canonical state を transaction 開始前へ戻せること」である。
