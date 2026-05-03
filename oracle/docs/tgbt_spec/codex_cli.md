
# tgbt からの Codex CLI 利用についての規則

- Codex CLI とは `codex` コマンドの事を指す
- 何らかの作業を実行させるには `codex exec` を使う
- 必要に応じて `--profile`, `--output-schema` などのオプションを使用しても良い
- `codex` コマンド実行時のカレントは、必ず `<repo-root>` とする
- 環境変数 `$CODEX_HOME` を用いて、 `~/.codex` ではなく `<repo-root>/.tgbt/.codex` を参照させる（リポジトリ外の設定を参照させない）
- Codex CLI の挙動設定（プロファイルを含む）は `<repo-root>/.tgbt/.codex/config.toml` で記述する
- `tgbt` による Codex CLI 呼び出しの前に、以下の事を `tgbt` 責任で保証する必要がある
    - 「`<repo-root>` 配下の Codex CLI の挙動に関係するすべての設定ファイル（`<repo-root>/.tgbt/.codex/config.toml` など）」が正しい状態になる
    - `tgbt` から Codex CLI を呼び出した時の挙動が `tgbt` の想定したものになる

# Codex CLI 実行可能性の事前チェック

- Codex CLI 実行可能性は、必ず事前チェックをすること
- この事前チェックは Codex CLI の呼び出し（本命処理）よりも前のタイミングであればいつでも良い
- 事前チェックに失敗した場合 `tgbt` の実行自体をエラー終了とする
- 事前チェックは smoke test で行う
    - 実際に Codex CLI の呼び出しを行い、正しくレスポンスが返ってくることを確認する
    - Codex CLI への依頼内容は最小限で良い
- 消費トークン節約のため、１度 smoke test に合格したら、その日の間は smoke test 再実行を省略する
