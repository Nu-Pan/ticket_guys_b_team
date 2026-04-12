# ticket_guys_b_team

## ticket_guys_b_team とは

- `ticket_guys_b_team` は、仕様レビュー駆動のマルチエージェント開発を人間向けに整理して実行するためのフロントエンドである
- 詳しくは [docs/spec/spec_overview.md](docs/spec/spec_overview.md) を参照

## 開発環境など

- [AGENTS.md](AGENTS.md)
- Codex CLI の worker runtime は `CODEX_HOME=<repo-root>/.tgbt/.codex` を前提とする
- runtime 生成物は `.tgbt/.codex/config.toml` と `.tgbt/instructions.md`
- `.tgbt/instructions.md` は人間向け文書ではなく、Codex CLI に読ませる repo-local runtime 指示である
- `tgbt env` が `.tgbt/.codex/config.toml` と `.tgbt/instructions.md` を自動生成・合法化する
