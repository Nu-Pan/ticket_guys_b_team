
# tgbt からの Codex CLI 利用についての規則

- Codex CLI とは `codex` コマンドの事を指す
- 何らかの作業を実行させるには `codex exec` を使う
- 必要に応じて `--profile`, `--output-schema` などのオプションを使用しても良い
- `codex` コマンド実行時のカレントは、必ず `<repo-root>` とする
- 環境変数 `$CODEX_HOME` を用いて、 `~/.codex` ではなく `<repo-root>/.tgbt/.codex` を参照させる（リポジトリ外の設定を参照させない）
- Codex CLI の挙動設定（プロファイルを含む）は `<repo-root>/.tgbt/.codex/config.toml` で記述する
- `tgbt init` の実行によって…
    - 「`<repo-root>` 配下の Codex CLI の挙動に関係するすべての設定ファイル（`<repo-root>/.tgbt/.codex/config.toml` など）」が正しい状態になる
    - `tgbt` から Codex CLI を呼び出した時の挙動が `tgbt` の想定したものになる
