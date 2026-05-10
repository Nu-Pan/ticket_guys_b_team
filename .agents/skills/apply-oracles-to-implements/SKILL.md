---
name: apply-oracles-to-implements
description: Reflect tgbt oracles changes or specified oracles documents into tgbt implementation. Use for implementation-followup work where oracles is authoritative over code, including fixing contradictions, required cascading bugs, and removing implementation that oracles makes obsolete.
---

# Apply Oracles To Implements

## Overview

`<tgbt-root>/oracles` の明示内容を正本として扱い、`tgbt` の実装を追従させる。目的は oracles と実装の矛盾解消であり、リファクターや品質改善そのものをゴールにしない。

## Guardrails

- `<tgbt-root>/oracles/**` は閲覧のみ許可され、編集してはいけない。
- `<tgbt-root>/README.md`、`<tgbt-root>/AGENTS.md`、`<tgbt-root>/memo/**` は編集してはいけない。`memo/**` は閲覧も禁止。
- `<tgbt-root>/docs` のような AI 管理ドキュメントを作成してはいけない。
- `<tgbt-root>` と `<repo-root>` のパス表記を混同してはいけない。判断に関わる場合は `<tgbt-root>/oracles/docs/dev_rule/path_notation_rule.md` を読む。
- oracles に未記載の仕様は、既存実装と局所文脈から必要最小限だけ判断する。
- high-level な仕様判断、public interface 変更、依存追加、永続データ形式変更、大規模リファクタが必要なら、人間確認事項として切り出す。
- テスト追加を前提にしない。必要な場合だけ `<tgbt-root>/oracles/docs/dev_rule/test_policy.md` に従い、確認は変更対象に近い `pyright`、import 確認、必要最小限の smoke 確認を優先する。
- 作業中に追加修正してよいのは、発見した致命的な実装問題、または根本問題の解決に必要な連鎖的問題に限る。

## Oracles Scope

- 人間が oracles ファイル、変更内容、再チェック範囲を指定している場合は、その指示を優先する。
- 指定がない場合は、直近の変更内容に基づく実装追従作業とみなす。
- その場合は、git の未コミット変更と直近数コミットを見て、oracles の意味論的な変更内容を把握する。
- `oracles/docs` を調べるときは各階層の `ROUTING.md` を辿り、必要な `.md` だけ読む。

## Workflow

### 1. Gather context

- `<tgbt-root>/AGENTS.md` を確認する。
- 対象 oracles と、関連する実装ファイル・呼び出し元・既存 state を必要最小限だけ読む。
- `<tgbt-root>` と `<repo-root>` の解釈が作業結果に影響するなら `<tgbt-root>/oracles/docs/dev_rule/path_notation_rule.md` を読む。
- Python を編集または検査するなら `<tgbt-root>/oracles/docs/dev_rule/python_coding.md` を読む。
- 確認方針を決めるなら `<tgbt-root>/oracles/docs/dev_rule/test_policy.md` を読む。
- oracles、実装、ユーザー指示が衝突する場合は oracles を正本として扱い、衝突内容を隠さず明示する。

### 2. Plan before editing

実装計画では、oracles の変更または指定範囲を具体的な実装対象へ対応付ける。対象は関数、クラス、コマンド、入出力など、AI が扱える low-level な単位へ局所化する。

計画の自己レビュー観点:

- oracles の各明示内容が、変更対象ファイルや実装単位へ対応付いているか。
- oracles と実装・既存 state・ユーザー指示の衝突を明示しているか。
- 人間確認が必要な high-level 判断を実装作業へ混ぜていないか。
- 既存設計、既存責務、既存 import 構造に沿っているか。
- 変更対象と読み取り対象が必要最小限か。
- `<tgbt-root>` と `<repo-root>` を取り違えた対象設定になっていないか。
- 編集・閲覧制約に反する作業を含んでいないか。
- テスト追加を前提にせず、必要な場合だけ `<tgbt-root>/oracles/docs/dev_rule/test_policy.md` に沿っているか。
- 確認方法が変更対象に近い最小限のものになっているか。
- 不確実性、未確認事項、連鎖的に発生しうる問題を明示しているか。

### 3. Implement narrowly

- oracles と矛盾する実装を修正する。
- oracles の内容から不要と判断できる実装は削除する。
- 根本問題の解決に必要な連鎖的問題は同じ作業内で修正してよい。
- 要求を満たす上で必要のない整形、責務移動、抽象化、public interface 変更、依存追加、永続データ形式変更は避ける。
- 既存の呼び出し元、保存形式、エラー処理、ログ、prompt/schema の意味論を不必要に変えない。

### 4. Review and verify

実装後に次を自己レビューする:

- 実装結果が oracles の明示内容と矛盾していないか。
- oracles を編集したり、oracles の意味を勝手に読み替えたりしていないか。
- oracles に未記載の仕様判断を最小限に留めているか。
- 余計なリファクターや範囲外修正が混ざっていないか。
- 確認で出たエラーを要求範囲内で修正し、範囲外の既存エラーは報告対象にしているか。

確認は `pyright`、import 確認、最小限の smoke 確認など、変更対象に近いものを選ぶ。確認できない場合は理由を報告する。

## Reporting

通常の完了報告に加えて、人間がフォローアップ作業を作れる情報を含める。

- 参照した oracles と、それに対応して変更した実装箇所。
- 今回修正した問題と、修正しなかった問題の区別。
- 未解決の問題点・リスク。
- 人間判断がないと実行に移せないこと。
- 実行した確認内容と結果、または実行できなかった確認と理由。
- 次に作成するとよさそうなフォローアップ作業候補。
