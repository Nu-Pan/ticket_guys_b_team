# `ticket_guys_b_team` Product Vision

## 1. 文書の目的

本書は `ticket_guys_b_team` の背景、目的、設計思想を説明する。

本書は実装契約を定義する文書ではない。状態遷移、CLI 契約、file format、wrapper 契約などの詳細は分割された仕様文書を参照する。

---

## 2. プロダクト概要

`ticket_guys_b_team` は、仕様レビュー駆動の AI 開発支援を CLI として扱いやすく整理するためのフロントエンドである。

中心課題は、エージェントそのものの性能ではない。人間要望を Plan に落とし、人間がそれをレビューし、AI が必要 Ticket を生成・実行し、結果と follow-up を追跡可能な形で残す運用を壊れにくくすることにある。

MVP では、利用者が主に意識すべき Ticket 種別は worker 1 種である。内部的に `ticket_kind` が露出してもよいが、利用者体験として複数 Ticket 型の理解を前提にしない。

---

## 3. 解決したい問題

ソフトウェア開発へ AI エージェントを導入するとき、問題になりやすいのは実装能力そのものよりも運用の曖昧さである。

典型的には以下の問題が起きる。

* 要望が曖昧なまま下流へ流れる
* 仕様レビューを飛ばして実装が始まる
* 実行単位の切り方が曖昧で、どこから再開すべきか分からない
* その時点で処理を打ち切ってよいのか分からない
* 実行失敗時に何が起きたか追跡できない
* `codex exec` への依存が強すぎて、テストが重い、遅い、高コストになる
* 過去の実行結果を再現したいが、入力と出力が実行基盤の内部に埋もれる
* 並列実行によって順序依存の差分が発生し、再現性が失われる
* repository 上の複数 state mutation が競合し、Plan / Ticket / counter が壊れる

`ticket_guys_b_team` は、これらを「エージェントが賢く解いてくれること」ではなく、Plan、Ticket、状態、成果物、実行記録を構造化することで抑制する。

---

## 4. 基本思想

### 4.1 上流で意図を固定する

本プロダクトは、「まず走らせて後で人間が見る」思想を取らない。

人間は通常 `tgbt plan docs` で Plan を編集し、`tgbt run --plan-id ...` で実行開始を表す。MVP では独立した `approve` サブコマンドを持たない。

### 4.2 Ticket は実行中に増減してよい

Plan から最初に固定枚数の Ticket を切り出し、それを消化したら終わり、という前提は置かない。

`run` は、Plan と既存 Ticket 群を見て必要なら新規 Ticket を作り、実行結果に応じて follow-up Ticket を足し、役目を終えた Ticket を `settled` に進める反復処理として扱う。

### 4.3 人間は意味を判断し、AI は処理を回す

人間の主責務は Plan の意味と意図の判断である。AI の主責務は Plan 草案化、Ticket 生成、Ticket 実行、実行結果要約、follow-up Ticket 生成、記録整理である。

利用者に直接見せる概念は plan / ticket / run であり、内部のエージェント runtime や workflow engine の詳細はそのまま露出しない。

### 4.4 live / stub を分離する

本プロダクトは live 実行と stub 実行を同じものとして曖昧に扱わない。

* live は実際に `codex exec` を呼び出す経路である
* stub は過去の session record を strict replay する経路である

live 実行で得た session record は、監査ログであると同時に、回帰テスト、バグ再現、結合テスト、fixture 化に使える資産として扱う。

### 4.5 直列実行を採る

本プロダクトは並列 Ticket 実行を採用しない。

理由は以下の通りである。

* Ticket 生成と follow-up 生成が run の途中で起きる
* 単一 repository 上の並列変更は追跡を難しくする
* strict replay は wrapper 呼び出し列が全順序であることと相性がよい
* 再現性と追跡可能性を主価値に置く

### 4.6 repository 単位で排他する

本プロダクトは `run` だけを排他し、`plan` 更新は自由に走らせる設計を取らない。

同一 repository に対する state mutation は 1 本に直列化し、Plan 更新と run の競合、複数 run の競合、採番競合をまとめて防ぐ。

### 4.7 Codex runtime は repo-local に固定する

本プロダクトは、対象 repository の既存 Codex CLI 設定に受動的に従う設計を取らない。

`tgbt` が Codex CLI を worker として起動する場合、runtime は repo-local に固定し、skills と sub agent は使用しない。

---

## 5. プロダクトが重視する価値

* **明確さ**: Plan revision、Ticket 状態、Ticket 依存、実行可否が読み解けること
* **追跡可能性**: 実行入力、結果、成果物、`plan_revision` / `run_id` / `codex_call_id` の対応が復元できること
* **分離**: 背景説明と厳密仕様、CLI 層と `codex exec` 直接呼び出し、業務概念と実行基盤詳細を混ぜないこと
* **安全な自動化**: 未整理の要望から直接実装へ飛ばず、失敗時にも状態と記録を残すこと
* **再現可能性**: stub によって過去の live 結果を再現でき、通常の stub テストは既存 repository 状態に依存せず実行できること

---

## 6. 対象範囲

初期バージョンで対象とするのは、単一 repository に対する CLI ベースの実行支援である。

主に以下を扱う。

* 人間要望からの Plan 草案生成と更新
* `run --plan-id` による Plan 実行開始
* Plan からの Ticket 生成
* Ticket 実行の統制
* 実行結果 summary の Ticket への反映
* follow-up Ticket 生成
* `codex exec` をラップする wrapper 経由の実行
* live 記録の保存
* strict replay による再現実行
* 実行結果と log、成果物 path の整理

初期バージョンでは、以下は主対象としない。

* Web UI
* 複数 repository 横断実行
* 分散 worker 実行
* 並列 Ticket 実行
* 汎用エージェントプラットフォーム化
* エージェント runtime の詳細設定を人間へ露出すること
* `run` にぶら下がる dry-run / preflight / validate 専用モード
* 専用の `status` / `state` 集約コマンド
* review / integration / root といった補助 Ticket 型
* 自動受け入れゲートの厳密仕様
* 任意 record を割り当てる manifest ベース replay

---

## 7. 想定ユーザー体験

理想的な利用体験は次の通りである。

1. 人間が曖昧な要望を書く
2. AI が Plan 草案を生成し、人間が必要なだけ修正する
3. 人間が `run --plan-id` を開始する
4. AI が Plan と既存 Ticket 群を見て必要 Ticket を作り、依存関係に従って直列実行する
5. AI が Ticket ごとの実行結果を要約として書き戻し、必要なら follow-up Ticket を追加する
6. 追加 Ticket が不要で、active Ticket がすべて `settled` になったら Plan が `settled` になる

重要なのは、人間を外すことではなく、人間の判断を本当に必要な箇所へ圧縮することである。

---

## 8. 人間と AI の役割分担

### 8.1 人間

* Plan のレビューと修正指示
* `run` を開始する意思決定
* 機械的に判定できない例外判断
* live 記録を fixture として採用するかの判断
* 最終意思決定

### 8.2 AI

* Plan 草案生成
* Ticket 生成と更新
* Ticket 実行
* 実行結果 summary の作成
* follow-up Ticket 生成
* log と成果物の整理
* live 記録の保存と stub 再生の実行
