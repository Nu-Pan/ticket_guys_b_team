

# パス表記ルール

- `<tgbt-root>/oracle/docs/dev_rule/path_notation_rule.md` で述べている `<repo-root>`, `<tgbt-root>` について
- これらは `tgbt` のソースコード上も有効なパス文字列として扱わなくてはならない
- e.g.
    - glob の対象として `<repo-root>/.agents/skills` が指定された場合
    - `/home/happy/pure_stuff/.agents/skills` のような、実際の `tgbt` 操作対象リポジトリの絶対パスに展開出来なければならない
- この規則の意図
    - ソースコードを含む `tgbt` 全体に `<repo-root>`, `<tgbt-root>` 表記を浸透させる
    - それにより「`tgbt` の開発」と「`tgbt` による開発」の混同を防ぎやすくする事を狙う
