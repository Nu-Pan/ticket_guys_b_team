# 注意

- このファイルでは「`<tgbt-root>` 上で Codex CLI を用いて `tgbt` 自体の開発を行う」際の `<tgbt-root>/oracle` について記述する
- 「`tgbt` を使って任意のリポジトリ(`<repo-root>`)上で開発作業を行う」際の `<repo-root>/oracle` については `<tgbt-root>/oracle/docs/tgbt_spec/oracle.md` を参照すること
- これら２パターンは根本的に前提が異なるため、混同してはいけない

# 基本的な考え方

- `<tgbt-root>/oracle` は AI による編集は禁止で人間が手動で真面目にメンテナンスする
- `<tgbt-root>/oracle` に書いてる事があらゆる事柄の正本情報である
- `<tgbt-root>/oracle` には網羅性は無く、人間が本当に重要だと思っていることだけが言語化されている
- 逆に言えば `<tgbt-root>/oracle` に書いてないことは、人間からすると Don't Care であり、 AI による裁量が許される

# 狙い

- 人間の頭の中にある `tgbt` のビジョン・設計意図を明文化する
- 人間によって適切に分割されたミクロな作業を AI が実行する際に、作業品質を向上させるためのヒントとする
