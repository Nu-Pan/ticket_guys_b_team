# この文書を読むべき時

- `AGENTS.md`、`.codex/**/*`、または Codex 自己改善ルールを記録する文書を追加・変更するとき
- `profiles`、`developer_instructions`、permissions など Codex の挙動設定を改善するとき

# 読まなくてよい時

- `ticket_guys_b_team` 本体の仕様確認や実装だけを行うとき
- テスト追加・修正や開発環境整備が主目的で、Codex 自体の設定は触らないとき

# 目的

この文書は、Codex エージェント自身の挙動をこのリポジトリ上で改善するときの最小ルールを定義する。

# 基本方針

- profile 名の自己認識に依存しない
- セッションごとの行動契約は `developer_instructions` を正本とする
- repo 全体の入口、作業分類、文書ルーティングは `AGENTS.md` を正本とする
- 実際の編集可能範囲は `.codex/config.toml` の permissions を hard gate とする
- repo から確認できる事実は先に回収し、Codex 契約の確認が必要なときだけ OpenAI developer docs MCP を使う
- まずは Codex が自己改善を始められる最小ハーネスを優先し、周辺自動化へ広げない
- ユーザーの明示的な許可が無い限り、対象範囲を広げない

# 最初に確認するもの

- `AGENTS.md`
- `.codex/config.toml`
- 変更対象の `.codex/**/*`
- 変更対象ファイルに既存の未コミット差分がある場合は、その内容
- Codex や OpenAI developer docs の契約確認が必要な場合だけ、OpenAI developer docs MCP

# ルールの置き場所

- `developer_instructions`
    - そのセッションで直ちに守る行動契約を書く
    - profile 名を推測しなくても成立する自己完結な指示にする
- `AGENTS.md`
    - repo 全体のブートストラップ兼ルータだけを書く
    - Codex 自己改善タスクの入口は示してよいが、詳細な編集可能範囲を重複記載しない
- `.codex/config.toml` の permissions
    - 実際に書ける場所を強制する
    - 文章上のルールだけに依存しない

# 編集対象

- `AGENTS.md`
- `.codex/**/*`
- `doc/task/codex_self_improvement.md`

# 通常は編集しない対象

- `README.md`
- 上記以外の `doc/**/*.md`
- `ticket_guys_b_team` 本体コード
- テストコード
- 依存関係や開発環境設定
- skills、hooks、周辺自動化の追加実装

# OpenAI Docs

- Codex CLI、`config.toml`、profiles、permissions、slash commands、OpenAI developer docs に関わる確認では、必ず OpenAI developer docs MCP を使う
- 記憶だけで設定キーや契約を断定しない

# 実装中の原則

- `developer_instructions` には、そのセッションで必要な最小限の行動契約だけを書く
- `AGENTS.md` には、Codex 自己改善タスクの導線と参照先だけを書く
- 詳細ルールはこの文書に集約し、`AGENTS.md` と `developer_instructions` に同じ細則を重複させない
- 書き込み権限の最小化を優先し、必要以上に writable roots や permissions を広げない
- 指示と権限のどちらかが矛盾する場合は、実装に進まずユーザー確認を行う

# 自己レビュー

最低 1 回、以下を点検すること。

- `developer_instructions`、`AGENTS.md`、permissions の責務分離が崩れていないか
- profile 名の自己認識を前提にしたルールが紛れ込んでいないか
- 編集可能範囲が必要以上に広がっていないか
- 同じルールが複数箇所に重複していないか

# 報告時に必ず含めること

- 何を変更したか
- なぜその変更で Codex 自己改善の最小ハーネスとして成立すると判断したか
- 実行した確認内容
- 残っている制約や未解決事項
- `AGENTS.md`、`.codex/config.toml`、この文書の間に矛盾があればその内容
