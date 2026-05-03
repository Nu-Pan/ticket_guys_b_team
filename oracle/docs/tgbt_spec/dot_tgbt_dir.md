
# `<repo-root>/.tgbt` ディレクトリの扱いについて

- tgbt 用のシステム領域として、リポジトリルート(`<repo-root>`)直下に `.tgbt` ディレクトリを用意する
- tgbt 起動時のカレントディレクトリからルートに向かって辿っていった時に、最初に見つかった「`.git` が直下に存在するディレクトリ」を `<repo-root>` とする
- `.tgbt` ディレクトリは `tgbt` の各処理で必要になったタイミングで動的に作成される
- tgbt から Codex CLI を呼び出す時は、環境変数 `CODEX_HOME = <repo-root>/.tgbt/.codex` とする
    - tgbt からの Codex CLI 呼び出しを出来るだけ隔離するための措置
- git 管理
    - `<repo-root>/.tgbt/.codex` は codex の状態ファイル等が含まれるため git 管理対象としない
    - それ以外は git 管理対象とする（e.g. `<repo-root>/.tgbt/logs`）
