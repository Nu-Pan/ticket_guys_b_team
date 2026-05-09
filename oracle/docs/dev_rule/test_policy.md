
# `tgbt` テスト実装ポリシー

- テストは「仕様を網羅的に固定するもの」ではなく、「tgbt 側（非 AI 部分）の機械的な退行を検知する最小の安全網」と定義する。
- Codex CLI の実呼び出し、AI 出力品質、プロダクト判断、oracle の未記載仕様は通常テスト対象にしない。
- 原則テスト対象にするのは、純粋関数、schema validation、path 変換、Markdown/prompt rendering、入力正規化、終了コード判定、AI 呼び出しに到達しない CLI error path。
- ファイルシステムを使う場合は、一時 repo に限定し、実 `<tgbt-root>` や通常の `<repo-root>/.tgbt` を汚さない。
- AI 呼び出しを含むテストは通常 test suite から除外し、必要なら手動 smoke / diagnostic として別扱いにする。
- テスト追加は「修正対象の近傍に明確な退行リスクがある場合」に限り、網羅率目標は置かない。
- oracle の正本性を壊さないため、テストが oracle の代替仕様にならないよう、期待値は機械的に明白なものへ限定する。
