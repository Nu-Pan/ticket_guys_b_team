
# `ROUTING.md` についてのルール

- `<tgbt-root>/oracle/docs/` 配下の各階層には `ROUTING.md` が存在する
- `ROUTING.md` には、同一階層のファイル・ディレクトリの目次情報が記述されている
- `ROUTING.md` を辿れば、適切な .md ファイルにアクセス可能である
- 「`<tgbt-root>/oracle` 直下」には `ROUTING.md` を作成しない
- `<tgbt-root>/oracle/docs/ROUTING.md` の存在は `<tgbt-root>/AGENTS.md` から辿ることが出来る

# `ROUTING.md` のフォーマット

機械的なチェックを可能とするために `ROUTING.md` は以下のフォーマットに従うものとする

```
# `dir_A`

- dir_A の説明
- ...

# `dir_B`

- dir_B の説明
- ...

# `file_A.md`

- file_A.md の説明
- ...

# `file_B.md`

- file_B.md の説明
- ...
```
