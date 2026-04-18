# Docs Refactor Rules

## Repo-specific rules

- `docs/` は `tgbt` 開発のための詳細情報置き場であり、仕様の正本を書いてはいけない。
- `README.md`、`oracle/**`、`memo/**`、`AGENTS.md` はこの skill の編集対象外である。
- `docs/ROUTING.md` は `docs` の入口であり、内容が空なら再構築対象として扱う。
- 現在の worktree に存在しない `docs/tech/*`、`docs/spec/*`、`docs/task/*` への参照は stale 候補として扱う。

## Practical decision rules

- 旧構造を丸ごと復元するのではなく、現行ファイル群を基準にルーティングを組み直す。
- 文書の役割が入口、ルール、詳細ガイドのどれか曖昧なら、先に役割を決めてから rename や統合を行う。
- 参照更新は移動や rename と同じ変更セットで行う。後回しにしない。
- `docs/` の再編では、文書の正しさよりも導線の明瞭さ、参照の健全性、重複の少なさを優先する。
- 削除された旧文書名を本文で案内し続けない。必要なら現行パスへ言い換える。
