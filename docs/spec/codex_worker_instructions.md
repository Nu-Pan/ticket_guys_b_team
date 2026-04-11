# `ticket_guys_b_team` Codex Worker Instructions Specification

## 1. 文書の目的

本書は、`tgbt` が Codex CLI を worker として起動する際の基本指示を定義する。

この文書は追跡対象の正本であり、runtime では `<repo-root>/.tgbt/instructions.md` が本書をもとに生成される。

---

## 2. 適用範囲

本書の指示は、`tgbt` が worker execution のために起動する Codex CLI にのみ適用する。

以下には直接適用しない。

* 人間が手元で対話的に使う Codex CLI 全般
* repository 開発時の bootstrap としての `AGENTS.md`
* OpenAI developer docs や別ツールの一般的な利用規約

ただし、`AGENTS.md` と worker 指示が衝突しうる場合、worker runtime では本書を正本として扱う。

---

## 3. runtime 生成契約

`tgbt` は worker 起動前に、少なくとも以下を満たさなければならない。

* `CODEX_HOME=<repo-root>/.tgbt/.codex` を設定する
* live worker execution ごとに `<repo-root>/.tgbt/.codex/config.toml` を正本契約どおり再生成する
* 再生成した `<repo-root>/.tgbt/.codex/config.toml` に profile `tgbt-worker` を定義する
* 再生成した profile `tgbt-worker` の `model_instructions_file` を `<repo-root>/.tgbt/instructions.md` に設定する
* live worker execution ごとに `<repo-root>/.tgbt/instructions.md` を、本書の内容要件を満たす形で再生成する

`<repo-root>/.tgbt/instructions.md` は runtime file であり、Git の正本ではない。

`tgbt` は、既存の `.tgbt/.codex/config.toml` や `.tgbt/instructions.md` の内容を次回 worker 実行へ継承してはならない。
各 live worker execution は、その直前に再生成された runtime file だけを `tgbt` 管理下の入力として扱わなければならない。

`<repo-root>/.tgbt/.codex/` 配下に `config.toml` 以外の file や directory が存在してもよい。
それらは Codex CLI private state であり、`tgbt` の worker runtime 契約の正本として扱ってはならない。

---

## 4. 必須指示

runtime 生成される `.tgbt/instructions.md` は、少なくとも以下を明示しなければならない。

* `tgbt` から渡される task 指示を最優先の作業指示として扱うこと
* repository 内の関連文書を読むときは、`docs/` 配下を正本として扱うこと
* skills を使用してはならないこと
* sub agent を使用してはならないこと
* `~/.codex` や repository 直下 `.codex/` に依存してはならないこと
* Codex CLI の設定正本は repo-local runtime であること

---

## 5. 実行境界

worker は task 実行者であり、repository bootstrap の調停者ではない。

したがって、worker 指示では少なくとも以下を前提とする。

* worker は `.tgbt/instructions.md` と `tgbt` からの task 指示に従う
* `AGENTS.md` は repository 開発時の参照として読んでよいが、worker runtime の正本ではない
* worker に対して skills / sub agent の利用判断を委ねない

`tgbt env` は、repository bootstrap の現状確認のために `AGENTS.md` と `.tgbt/instructions.md` の両方を参照してよい。
ただし、この用途でも runtime 正本は `.tgbt/instructions.md` 側であり、`AGENTS.md` は bootstrap 整合性を確認するための参照物として扱う。

repository 直下 `.codex/` が存在しても、それは `env` の bootstrap 観測対象にとどまる。
live worker execution の runtime 入力として用いてはならない。

---

## 6. 変更管理

worker の基本指示を変更したい場合は、まず本書を更新する。

runtime file である `.tgbt/instructions.md` を直接編集して正本化してはならない。
