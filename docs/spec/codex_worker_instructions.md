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
* `<repo-root>/.tgbt/.codex/config.toml` に profile `tgbt-worker` を定義する
* profile `tgbt-worker` の `model_instructions_file` を `<repo-root>/.tgbt/instructions.md` に設定する
* `<repo-root>/.tgbt/instructions.md` を、本書の内容要件を満たす形で生成する

`<repo-root>/.tgbt/instructions.md` は runtime file であり、Git の正本ではない。

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

---

## 6. 変更管理

worker の基本指示を変更したい場合は、まず本書を更新する。

runtime file である `.tgbt/instructions.md` を直接編集して正本化してはならない。
