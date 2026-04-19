---
name: investigate-tgbt
description: tgbt リポジトリ内の事柄について、実装・テスト・開発ドキュメントを根拠に調査し、現状挙動や制約を説明するためのスキル。Use when Codex needs to answer repo-specific questions, trace behavior through code and tests, compare conflicting evidence, summarize the current implementation, or perform scoped investigation without making product-level design decisions.
---

# Investigate TGBT

## Overview

調査対象を repo 内の具体的な根拠へ分解し、事実・推論・未確定事項を分けて説明する。
人間が保持する抽象仕様を勝手に補完せず、現に読める成果物から言えることだけを積み上げる。

## Non-Negotiables

- 最初に `AGENTS.md` を確認し、その制約を外さない。
- `memo/` は読まない。編集もしない。
- `README.md`、`oracle/**`、`AGENTS.md` は編集しない。
- `oracle/` は人間が管理する断片的な正本仕様であり、網羅的ではない前提で扱う。調査対象がその断片仕様そのものに関係するときだけ参照し、未記載部分を補完しない。
- プロダクトビジョンや抽象設計の確定は人間の責務だと理解する。調査では、repo から観測できる事実の整理に徹する。
- repository root の `./.codex/` と runtime state の `./.tgbt/.codex/` を混同しない。両者は役割が違う可能性があるので、必ず実装とテストで意味を確認する。

## Evidence Order

- 実装済み挙動を知りたいときは、まず既存テストと実装を優先する。
- 開発ルールや作業手順を知りたいときは、`AGENTS.md` と `docs/*.md` を優先する。
- `docs/ROUTING.md` が存在して内容もあるなら最初に読む。空なら relevant な `docs/*.md` を直接当たる。
- `README.md` は人間向け概要として扱い、AI にとっての一次根拠にはしない。
- `docs/*.md` が削除済みパスや空ファイルを参照していたら、その文書は stale 候補として扱い、現存するコード・テスト側の証拠で裏を取る。
- 根拠同士が食い違う場合は、勝手に整合させず、どのファイルのどの主張が衝突しているかを明示する。

## Investigation Workflow

1. 質問を次のどれに近いか切り分ける: CLI 表面、内部状態、Plan 系フロー、env 系フロー、テスト期待値、開発ルール。
2. `rg` で対象シンボル、コマンド名、エラーメッセージ、関連テストを広く拾う。
3. 調査の起点として、以下のような代表ファイルから読む。
   - CLI 表面: `src/main.py`, `bin/tgbt`, `tests/stub/test_main.py`, `tests/stub/test_bin_tgbt.py`
   - init 系: `src/env_service.py`, `src/env_runtime.py`, `docs/dev_environment.md`
   - Plan 系: `src/plan_service.py`, `src/plan_drafting.py`, `tests/stub/test_main.py`
   - 状態管理: `src/state_io.py` とその利用箇所
4. 証拠の鎖が切れたときだけ隣接モジュールへ広げる。無関係なファイルを広く読むより、入口から呼び出し先を辿る。
5. 調査タスクでは、コード編集、依存追加、live 実行、既存 state を汚すコマンドを既定動作にしない。必要なら理由を明確にしてから行う。
6. 「意図された完全仕様」を問われても、repo から確定できるのは現状実装・現存ドキュメント・既存テストの範囲だけだと明示する。

## Reporting Rules

- まず結論を述べ、その後に根拠ファイルを添える。
- 事実、そこからの推論、未確定事項を分ける。
- 「現状の実装」と「人間が意図した完全仕様」を混同しない。
- repo 内の根拠だけでは決め切れない場合は、欠けている情報を具体的に示して人間確認が必要だと書く。
- 問題の切り分け中に空ファイル、古い文書、片側だけ更新されたテストなどを見つけたら、その不整合自体を調査結果に含める。

## Default Answer Shape

- 調査対象を一文で言い換える。
- 最重要の findings を先に並べる。
- 各 finding に根拠ファイルを付ける。
- 必要なら「未確定事項」または「追加で見るべき箇所」を短く添える。
