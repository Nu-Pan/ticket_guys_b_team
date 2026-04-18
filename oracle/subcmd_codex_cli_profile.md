## 概要

- `tgbt plan docs` のような内部で Codex CLI 呼び出しを行うサブコマンドについて、必ず tgbt 専用の profile を使う前提とする

## 仕様

- 対応する profile は `<repo-root>/.tgbt/.codex/config.toml` に記述する
- profile は tgbt のサブコマンドと１：１対応させない
- 複数のサブコマンド・フェーズから１つの profile を共通して使うことを前提とする
- 様々なシナリオをカバー出来る profile セットを用意する
- サブコマンド拡充に伴い profile セットも拡充する
- 各 profile で記述する要素は、できるだけ明示的に記述する方針を取る
