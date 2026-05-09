
# 概要・前提

- 「対象はリポジトリ全体」系の作業をそのままプロンプトに書くのは筋が悪い
    - e.g. 「`<tgbt-root>/src` 配下のスクリプトを再帰的に列挙し、それら全てに対して、 `oracle` で述べたコーディング規約に違反していないかチェックしてください。」
- N 個のファイルに対して同じ処理を適用する必要が有るのであれば、それは N 回の Codex CLI 呼び出しに分割するべきだろう
- この要件を満たす開発用の補助スクリプトを用意し、それをユーザーが呼び出すこととする

# スクリプトの基本仕様

- `<tgbt-root>/dev_scripts/fanout_codex_exec.py` に実装する
- 引数としてサブコマンド（＝作業タイプ）だけを受け付ける
- 引数としてプロンプトは受け取らず、各サブコマンドでハードコードする
- 新しくやりたいことが増えた場合はサブコマンドを都度増やす
- 呼び出された時のカレントがどこであっても正しく動作すること

# 引数 `--dangerously-bypass-approvals-and-sandbox`

- どうしても必要な場合は `codex exec` の呼び出しに `--dangerously-bypass-approvals-and-sandbox` を付けても良いとする
- これは、 `<tgbt-root>/.agents` のような、どうしても読み取り専用を外せない対象の編集作業を想定している

# 実行ログの扱い

- 実行ログは標準出力に流しつつ `<tgbt-root>/dev_scripts/logs/fanout-file-codex/*.log` に tee する
- 全処理完了後、標準出力にログファイルのパスを出力する
- tee したログファイルは、人間がエディタで閲覧するための集約ログである
- `tgbt` 自体の開発に関するログであるため、 `tgbt` のログ出力先仕様 (`oracle/docs/tgbt_spec/logs.md`) と混同してはいけない

# git 関係の規約

- `fanout_codex_exec.py` が呼ばれた時点で...
    - git 上に未コミットの変更が存在する場合、エラーを出して終了する（事前に git 的にクリーンな状態にするのはユーザーの責任とする）
    - fanout ループに入る前に「ローカルの default branch の最新コミット」から「この fanout 処理専用のブランチ」を作成・チェックアウトする
- 個別の `codex exec` を呼び出しについて...
    - それが成功した場合は、その時点での未コミットの変更を全てコミットする
    - それが失敗した場合は、その時点での未コミットの変更は全て破棄する
    - これは git 的にクリーンな状態にしてから次の `codex exec` にターンを回す事を意図している
- `fanout_codex_exec.py` 終了時点で...
    - 「全ての成功した作業の結果がコミットされた専用ブランチ」が存在することとする（それをマージするかはユーザーの任意）

# `tgbt` 仕様と `fanout_codex_exec.py` の関係

- `fanout_codex_exec.py` は `tgbt` を開発するための便利スクリプトである
- よって `fanout_codex_exec.py` の仕様は「`<rgbt-root>/oracle/docs/tgbt_spec` 配下で述べられている `tgbt` の仕様」とは無関係である
- e.g. `CODEX_HOME=<repo-root>/.tgbt/.codex` とするような操作はしてはいけない（そもそも `fanout_codex_exec.py` の実行パスは `<tgbt-root>` 配下である）

# 使用するモデル

- GPT-5.5
- reasoning effort: medium

# 各サブコマンド仕様

## `update-oracle-docs-routing`

- 対象
    - `<tgbt-root>/oracle/docs` 配下の全てのディレクトリ（`docs` 自身・サブディレクトリを含む）
- プロンプト
    ```
    `<対象ディレクトリパス>` だけを対象にスキル $update-oracle-docs-routing を実行してください。
    ```
- 備考
    - なし

## `create-repo-local-skill`

- 対象
    - `<tgbt-root>/.agents/skills/` 直下のディレクトリを対象とする
- プロンプト
    ```
    `<対象ディレクトリパス>` だけを対象にスキル $create-repo-local-skill を実行してください。
    ```
- 備考
    -  `<tgbt-root>/.agents` 配下は AI 編集不可であるため `--dangerously-bypass-approvals-and-sandbox` を使用する

## `apply-oracle-to-implements-light`

- 対象
    - `<tgbt-root>/oracle/docs/` 配下の全ての `*.md` ファイル（ただし `ROUTING.md` は除外）
- プロンプト
    ```
    `<対象 oracle ファイルパス>` だけを対象にスキル $apply-oracle-to-implements を実行してください。
    ```
- 備考
    - なし

## `apply-oracle-to-implements-heavy`

- 対象
    - グループ A : `<tgbt-root>/oracle/docs/` 配下の全ての `*.md` ファイル（`ROUTING.md` は除外）
    - グループ B : `<tgbt-root>/src` 配下の全ての `.py` ファイル（`.gitignore` の対象は除外）
    - グループ A, B の組み合わせ全てが対象
- プロンプト
    ```
    スキル $apply-oracle-to-implements を使用し、 `<対象ソースファイルパス>` が `<対象 oracle ファイルパス>` の内容と整合するかチェックし、必要があれば修正してください。
    ```
- 備考
    - なし
