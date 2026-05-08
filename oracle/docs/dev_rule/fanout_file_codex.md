
# 概要・前提

- 「対象はリポジトリ全体」系の作業をそのままプロンプトに書くのは筋が悪い
    - e.g. 「`<tgbt-root>/src` 配下のスクリプトを再帰的に列挙し、それら全てに対して、 `oracle` で述べたコーディング規約に違反していないかチェックしてください。」
- N 個のファイルに対して同じ処理を適用する必要が有るのであれば、それは N 回の Codex CLI 呼び出しに分割するべきだろう
- この要件を満たす開発用の補助スクリプトを用意し、それをユーザーが呼び出すこととする

# スクリプトの基本仕様

- 最低限必要な情報として「再帰的に列挙する対象となるディレクトリ」「展開対象となるプロンプト」を受け取る
- 該当ファイルを glob で機械的に列挙し、それぞれのファイルに対して個別に `codex exec` を起動する
- 個別の `codex exec` に渡すプロンプトには、最低限必要な定型文が追加される

# ファイルシステム上の配置

- `<tgbt-root>/dev_scripts/fanout-file-codex.sh` に実装する

# プロンプトの受け取り方

- `oracle/docs/tgbt_spec/instruction_input.md` の同様の方向性を取る
- つまり、エディタ起動・標準入力の２経路での入力を受け付ける
- 与えられたプロンプトが実質空文字の場合はエラー終了させる

# 対象ファイルの指定方法

- 「対象ディレクトリパス」と「ファイルパターン」を引数で受け取る
- 「対象ディレクトリパス」を起点に「ファイルパターン」とマッチするファイルが再帰的に列挙される
- 「ファイルパターン」が `<dir>` である場合、ファイルでは無くディレクトリを列挙する

# 個別の `codex exec` 呼び出し

- 以下のようなプロンプトを機械的に合成して `codex exec` に渡す
    ```
    `<対象ファイルパス>` だけを対象に、以下に述べる作業を行ってください。

    <`fanout-file-codex.sh` に渡されたプロンプト>
    ```

## 引数 `--dangerously-bypass-approvals-and-sandbox`

- `fanout-file-codex.sh` の引数として `--dangerously-bypass-approvals-and-sandbox` を受け付ける
- この引数が渡された場合 `codex exec` の呼び出しに `--dangerously-bypass-approvals-and-sandbox` が追加される
- `<tgbt-root>/.agents` のような、どうしても読み取り専用を外せない対象の編集作業をやらせる時に使う事を想定している

# 実行ログの扱い

- 実行ログは標準出力に流しつつ `<tgbt-root>/dev_scripts/logs/fanout-file-codex/*.log` に tee する
- 全処理完了後、標準出力にログファイルのパスを出力する
- tee したログファイルは、人間がエディタで閲覧するための集約ログである
- `tgbt` 自体の開発に関するログであるため、 `tgbt` のログ出力先仕様 (`oracle/docs/tgbt_spec/logs.md`) と混同してはいけない

# `fanout_file_codex.sh` をベースとした派生ヘルパースクリプト

## `fanout_update_oracle_docs_routing.sh`

- スキル `update-oracle-docs-routing` を `<tgbt-root>/oracle/docs` 配下の全てのディレクトリ（`docs` 自身・サブディレクトリを含む）に対して適用するスクリプト
- プロンプトとして `$update-oracle-docs-routing を使用してください` だけを入力する

## `fanout_create_repo_local_skill.sh`

- スキル `fanout_create-repo-local-skill` を全てのスキルに対して適用するスクリプト
- `--dangerously-bypass-approvals-and-sandbox` を使用する
- プロンプトとして `$create-repo-local-skill を使用してください` だけを入力する


## `fanout_apply_oracle_to_implements.sh`

- スキル `apply-oracle-to-implements` を `<tgbt-root>/stacle/docs` 配下の全てのファイルについて実行するスクリプト
- プロンプトとして `$apply-oracle-to-implements を使用してください` だけを入力する
