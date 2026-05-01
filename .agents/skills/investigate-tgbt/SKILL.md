---
name: investigate-tgbt
description: Investigate tgbt repo behavior from code, oracle, and relevant existing tests. Use when answering repo-specific questions without editing files or inferring product intent.
---

# Investigate TGBT

## Overview

調査対象を repo 内の具体的な根拠へ分解し、事実・推論・未確定事項を分けて説明する。
人間が保持する抽象仕様を勝手に補完せず、現に読める成果物から言えることだけを積み上げる。

## Guardrails

- 最初に `AGENTS.md` を確認し、repo 固有の読み取り・編集制約を外さない。
- `oracle/` は人間が管理する断片的な正本仕様であり、網羅的ではない前提で扱う。調査対象がその断片仕様そのものに関係するときだけ参照する。
- 参照した `oracle` の明示内容と実装・既存テストが衝突する場合は、`oracle` を正本として扱い、衝突箇所を事実として分けて報告する。
- プロダクトビジョンや抽象設計の確定は人間の責務だと理解する。調査では、repo から観測できる事実の整理に徹する。
- repository root の `./.codex/` と runtime state の `./.tgbt/.codex/` を混同しない。両者は役割が違う可能性があるので、必ず実装を中心に、必要なら関連する既存テストも証拠として意味を確認する。
- この `ticket_guys_b_team` repository 上で `tgbt` を実行して自己開発させない。unit test の live mode も使わない。
- 調査結果は回答として報告し、中間ドキュメントや調査メモとして永続化しない。

## Evidence Order

- 実装済み挙動を知りたいときは、まず実装を優先する。既存テストが残っている場合は、過去または周辺期待値の証拠として必要な範囲で読む。
- 開発ルールや作業手順を知りたいときは、`AGENTS.md` と `oracle/docs/ROUTING.md`、`oracle/docs/dev_rule/ROUTING.md` から辿れる該当ファイルを優先する。
- tgbt の仕様断片を知りたいときは、`oracle/docs/ROUTING.md` と各階層の `ROUTING.md` から関連する `oracle/docs/tgbt_spec/*.md` を辿る。
- `README.md` と `memo/**` は読まない。
- 根拠同士が食い違う場合は、勝手に整合させず、どのファイルのどの主張が衝突しているかを明示する。

## Investigation Workflow

1. 質問を次のどれに近いか切り分ける: CLI 表面、内部状態、Plan 系フロー、env 系フロー、残存する既存テストの期待値、開発ルール。
2. `rg` で対象シンボル、コマンド名、エラーメッセージを広く拾う。既存テストが論点に関係するときだけ、追加で関連テストを確認する。
3. 調査の起点として、必要に応じて以下の代表ファイルから読む。
   - CLI 表面: `src/main.py`, `bin/tgbt`
   - init 系: `src/sub_commands/init/tgbt_init.py`, `src/agent_wrapper/codex_wrapper_live.py`
   - Plan 系: `src/sub_commands/plan/docs/tgbt_plan_docs.py`
   - run 系: `src/sub_commands/run/tgbt_run.py`
   - 状態管理: `src/state/path.py` とその利用箇所
   - 開発ルール: `oracle/docs/dev_rule/ROUTING.md` から関連ファイル
   - 仕様断片: `oracle/docs/tgbt_spec/ROUTING.md` から関連ファイル
4. 証拠の鎖が切れたときだけ隣接モジュールへ広げる。無関係なファイルを広く読むより、入口から呼び出し先を辿る。
5. 調査タスクでは、コード編集、依存追加、既存 state を汚すコマンドを既定動作にしない。`tgbt` 自己実行と unit test の live mode は行わない。
6. 調査結果は回答として報告し、`docs/` などの中間ドキュメントとして永続化しない。

## Reporting Rules

- 調査対象を一文で言い換え、最重要の findings を先に並べる。
- 各 finding に根拠ファイルを付ける。
- 事実、そこからの推論、未確定事項を分ける。
- 「現状の実装」と「人間が意図した完全仕様」を混同しない。
- repo 内の根拠だけでは決め切れない場合は、欠けている情報を具体的に示して人間確認が必要だと書く。
- 問題の切り分け中に空ファイル、古い参照、片側だけ更新されたテストなどを見つけたら、その不整合自体を調査結果に含める。
- 必要なら「未確定事項」または「追加で見るべき箇所」を短く添える。
