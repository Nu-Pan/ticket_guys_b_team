# この文書を読むべき時

- コード変更を伴う実装作業を行うとき
- 不具合修正、機能追加、リファクタを実際に進めるとき

# 読まなくてよい時

- 調査だけで終わるとき
- 環境整備だけが目的のとき

# 目的

この文書は、実装タスクで読むべき文書の順序と、実装前後に守るべき最小ルールを定義する。

# 実装前の手順

## 1. 入口仕様を読む

- まず `doc/spec/spec_overview.md` を読む
- 変更対象に対応する仕様文書だけを追加で読む

## 2. 関連仕様を絞る

- CLI の追加・変更: `doc/spec/cli_contract.md`
- 状態遷移や run の流れに関わる変更: `doc/spec/state_machine.md`
- front matter、保存先、採番、artifact の形式に関わる変更: `doc/spec/file_format.md`
- front matter の安全な書き換え、atomic write-replace、transaction、recovery に関わる変更: `doc/spec/state_write_protocol.md`
- `codex exec` 呼び出し、live / stub、strict replay に関わる変更: `doc/spec/codex_cli_wrapper.md`
- どの設計判断が MVP の意図に沿うか迷う: `doc/spec/product_vision.md`

## 3. 技術文書を必要な分だけ読む

- Python を編集するなら `doc/tech/python.md`
- テストを追加・修正するなら `doc/tech/test_policy.md`
- `.venv`、依存関係、実行環境を触るなら `doc/tech/dev_environment.md`

# 実装中の原則

- 仕様と矛盾しない最小限の変更を行うこと
- 命名、責務、入出力を明確に保つこと
- オーバーエンジニアリングを避けること
- 意図がコードから読み取りにくい場合は、短いコメントや `NOTE` を使って補うこと
- 仕様に書かれていない挙動を勝手に追加しないこと

# テストと検証

- 変更内容に対応するテストを実装または更新すること
- 静的検査と動作確認を行うこと
- Python の型チェックやテスト方針は `doc/tech/python.md` と `doc/tech/test_policy.md` に従うこと

# 実装完了時のチェックリスト

- 変更内容が要求を満たしている
- 仕様と実装の間に新しい矛盾を作っていない
- 必要なテストを更新した
- 静的検査と実行確認の結果を説明できる
- 未解決事項や制約を説明できる

# 報告時に必ず含めること

- 何を変更したか
- なぜその変更で要求を満たすと判断したか
- 実行した確認内容
- 残っている制約や懸念
- `doc/spec/*.md` との差分を見つけた場合はその内容
