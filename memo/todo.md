# custom linter を組み込みたい

- 全てを仕様書で書くのではなく、出来るだけ custom linter を書くことにしたい
- そのあたりの一般原則の言語化が必要

# permissions によるファイルアクセス権制御

- codex cli がバグってるっぽい
- permissions を使うと、それが原因で bwrap によるサンドボックス実行に失敗する
- bwrap 外でのエスカーレション実行にフォールバックするが、なぜか承認 UI が出てこない
- 多分 codex cli のバグ修正を待つしか無くて、それまでは指示文にアクセス禁止ルールを書くしか無い


# tgbt 起動時の Codex CLI 関係チェック

- tgbt からの呼び出し時、基本的には更新チェックは OFF ということにした
- なので、専用の仕組みを用意して、チェックが走るようにしたい
- あと、事前にユーザーが Codex CLI を直接起動してログイン状態にする必要があるけど、その案内も必要だろう
- Codex CLI の設定が正しいかどうかはスキーマと照合する必要がある（存在しないキーを指定した時に、それがエラーにならない）

# plan id の省略

- plan id として latest を指定したら、最新のプランが選択されるようにする

# codex 実行結果の監査ログ

- 必要な対応は以下の通り
    - Codex CLI 呼び出しログの保存先を `<repo-root>/.tgbt/.codex/audit_logs` から `<repo-root>/.tgbt/logs/codex_call` に変更する
    - Codex CLI 実行時の環境（config.toml とか schema とかの設定すべて）を Codex CLI ログに含める
    - `tgbt` 呼び出し自体のログを `<repo-root>/.tgbt/logs/tgbt_call` に保存する
    - `tgbt plan` の結果の `<repo-root>/.tgbt/logs/plan`, `<repo-root>/.tgbt/logs/plan_read` への保存（要 oracle 書き換え）
    - `tgbt init` で起きたことの `<repo-root>/.tgbt/logs/init` への保存
