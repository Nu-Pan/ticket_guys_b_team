# `ticket_guys_b_team` Product Vision

## 1. 文書の目的

本書は `ticket_guys_b_team` の背景・目的・設計思想を説明する文書である。

本書は詳細仕様書ではない。状態遷移、ファイル形式、CLI 契約、Codex CLI wrapper 契約などの実装判断に必要な詳細は、分割された仕様文書を参照する。

---

## 2. プロダクト概要

`ticket_guys_b_team` は、仕様レビュー駆動の AI 開発支援を、人間が扱いやすい形に整理して実行するための CLI フロントエンドである。

本プロダクトの中心課題は、エージェントそのものの性能ではない。むしろ、人間要望を Plan に落とし、人間がそれをレビューし、AI が必要 Ticket を生成・実行し、結果とフォローアップを追跡可能な形で残す運用を壊れにくくすることにある。

MVP では、利用者が主に意識すべき Ticket 種別は worker 1 種である。内部的には実装・チェック・リファクタ等のテンプレート差があり得て、`ticket_kind` のような形で情報が露出してもよいが、利用者体験として複数 Ticket 型の理解を前提にはしない。

---

## 3. 解決したい問題

ソフトウェア開発へ AI エージェントを導入するとき、問題になりやすいのは実装能力そのものよりも、運用の曖昧さである。

典型的には以下のような問題が起きる。

* 要望が曖昧なまま下流へ流れる
* 仕様レビューを飛ばして実装が始まる
* 実行単位の切り方が曖昧で、どこから再開すべきか分からない
* その時点で処理を打ち切ってよいのか分からない
* 実行失敗時に、何が起きたか追跡できない
* `codex exec` への依存が強すぎて、テストが重い、遅い、高コストになる
* 過去の実行結果を再現したいが、入力と出力が実行基盤の内部に埋もれてしまう
* 並列実行によって順序依存の差分が発生し、再現性が失われる
* repository 上の複数 state mutation が競合し、Plan / Ticket / counter が壊れる

`ticket_guys_b_team` は、これらを「エージェントが賢く解いてくれること」に期待するのではなく、Plan、Ticket、状態、成果物、実行記録を構造化することによって抑制する。

---

## 4. 基本思想

### 4.1 上流で意図を固定し、承認は `run` 開始で表す

本プロダクトは、「まず走らせて後で人間が見る」思想を取らない。

人間は通常 `tgbt plan docs` で Plan を編集し、実行に進める意思決定は `tgbt run --plan-id ...` によって表す。例外として `tgbt env` は repo-local runtime 合法化専用の deterministic な bootstrap repair command として扱う。MVP では独立した `approve` サブコマンドを持たず、「run を開始すること」が運用上の承認に相当する。

### 4.2 Ticket は Plan 実行中に増減してよい

Plan から最初に固定枚数の Ticket を切り出し、それを消化したら終わり、という前提は置かない。

`run` は、Plan と既存 Ticket 群を見て必要なら新規 Ticket を作り、実行結果に応じてフォローアップ Ticket を足し、役目を終えた Ticket を `settled` に進める反復処理として扱う。

### 4.3 人間は意味を判断し、AI は処理を回す

人間の主責務は、Plan の意味と意図の判断である。AI の主責務は、Plan 草案化、Ticket 生成、Ticket 実行、実行結果要約、フォローアップ Ticket 生成、記録整理である。

利用者に直接見せる概念は plan / ticket / run であり、内部のエージェントランタイムやワークフローエンジンの詳細はそのまま露出しない。

### 4.4 live / stub を分離し、live 記録を再利用可能な資産として扱う

本プロダクトは、live 実行と stub 実行を同じものとして曖昧に扱わない。

* live は、本当に `codex exec` を呼び出す本番系の経路である
* stub は、過去の session record を strict replay するテスト系の経路である

重要なのは、業務上の状態遷移は共通のまま、外部依存だけを差し替えられることである。live 実行で得た session record は、単なる監査ログではなく、回帰テスト、バグ再現、結合テスト、fixture 化に使える資産として扱う。

通常の stub テスト運用では、この資産と必要状態をテスト fixture / harness 側へ閉じ込め、開発者は環境セットアップ後に単にテストを実行すればよい状態を目指す。strict replay の成立条件を、日常のテスト実行者による手動 restore 作業へ転嫁しない。

### 4.5 直列実行のみを採る

本プロダクトは、並列 Ticket 実行を採用しない。

理由は以下のとおりである。

* Ticket 生成と follow-up 生成が run の途中で起きるため、実行順序差が業務結果差に直結する
* 単一リポジトリ上での並列変更は、監査証跡の解釈を難しくする
* strict replay は wrapper 呼び出し列が全順序であることと相性がよい
* 再現性と追跡可能性を主価値に置く本プロダクトの基本思想と、並列化による非決定性が衝突する

したがって、本仕様では run と wrapper 呼び出しを将来的にも直列実行のみとする。

### 4.6 repository への state mutation は常に排他する

本プロダクトは、`run` だけを排他し、`plan` 更新は自由に走らせる、という設計を取らない。

同一 repository に対しては、少なくとも Plan front matter、Ticket front matter、counter、session record 配置に影響する `tgbt` コマンドを 1 本だけ許可する。これにより、Plan 更新と run の競合、複数 run の競合、採番競合をまとめて防ぐ。

### 4.7 Codex runtime は repository-local に侵襲的に合わせる

本プロダクトは、対象 repository の既存 Codex CLI 設定に受動的に従う設計を取らない。

`tgbt` が Codex CLI を worker として起動する場合、runtime は常に repository-local に固定する。

* `CODEX_HOME` は `<repo-root>/.tgbt/.codex` を使う
* user-global な `~/.codex` には依存しない
* repository 直下 `.codex/` を worker runtime の正本として扱わない
* `.tgbt/instructions.md` は人間向け文書ではなく、`tgbt env` が生成する repo-local runtime 指示として扱う
* `.tgbt/instructions.md` には、`tgbt` の各サブコマンドから起動される Codex CLI に共通する基礎的指示を含める
* 要検討事項を増やさないため、`tgbt` が Codex CLI を起動する実行では skills と sub agent を使わない

---

## 5. プロダクトが大事にする価値

* **明確さ**: Plan revision、Ticket 状態、Ticket 依存、実行可否が読み解けること
* **追跡可能性**: 実行入力、結果、成果物、`plan_revision` / `run_id` / `codex_call_id` の対応が復元できること
* **分離**: 背景説明と厳密仕様、CLI 層と `codex exec` 直接呼び出し、業務概念と実行基盤詳細を混ぜないこと
* **安全な自動化**: 未整理の要望から直接実装へ飛ばず、失敗時にも状態と記録を残し、repository 全体の同時 state mutation を禁止すること
* **再現可能性**: stub によって過去の live 結果を再現でき、外部トークン消費や外部依存を避けられ、通常の stub テストは既存 repository 状態に依存せず実行できること

---

## 6. 対象範囲

初期バージョンで対象とするのは、単一リポジトリに対する CLI ベースの実行支援である。

主に以下を扱う。

* 人間要望からの Plan 草案生成と更新
* `run --plan-id` による Plan 実行開始
* Plan からの Ticket 生成
* Ticket 実行の統制
* 実行結果サマリーの Ticket への反映
* フォローアップ Ticket 生成
* `codex exec` をラップする wrapper 経由の実行
* live 記録の保存
* strict replay による再現実行
* 実行結果とログ、成果物パスの整理

初期バージョンでは、以下は主対象としない。

* Web UI
* 複数リポジトリ横断実行
* 分散ワーカー実行
* 並列 Ticket 実行
* 汎用エージェントプラットフォーム化
* エージェントランタイムの詳細設定を人間へ露出すること
* `run` にぶら下がる dry-run / preflight / validate 専用モード
* 専用の `status` / `state` 集約コマンド
* review / integration / root といった補助 Ticket 型
* 自動受け入れゲートの厳密仕様
* 任意 record を割り当てる manifest ベース replay
* あらゆる外部ツールを一般化した replay framework

MVP では、まず Plan / Ticket / run / wrapper の整合性を固める。自動受け入れゲートは将来拡張として別途仕様化する。

---

## 7. 想定ユーザー体験

理想的な利用体験は次のようなものである。

1. 人間が曖昧な要望を書く
2. AI が Plan 草案を生成し、人間が必要なだけ修正する
3. 人間が `run --plan-id` を開始する
4. AI が Plan と既存 Ticket 群を見て必要 Ticket を作り、依存関係に従って直列実行する
5. AI が Ticket ごとの実行結果を要約として書き戻し、必要ならフォローアップ Ticket を追加する
6. 追加 Ticket が不要で、active Ticket がすべて `settled` になったら Plan が `settled` になる

ここで重要なのは、人間を外すことではなく、人間の判断を本当に必要な箇所へ圧縮することである。

---

## 8. 人間と AI の役割分担

### 人間

* Plan のレビューと修正指示
* `run` を開始する意思決定
* 機械的に判定できない例外判断
* live 記録を fixture として採用するかの判断
* 最終意思決定

### AI

* Plan 草案生成
* Ticket 生成と更新
* Ticket 実行
* 実行結果サマリーの作成
* フォローアップ Ticket 生成
* ログと成果物の整理
* live 記録の保存と stub 再生の実行
