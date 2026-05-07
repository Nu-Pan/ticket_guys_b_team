# custom linter を組み込みたい

- 全てを仕様書で書くのではなく、出来るだけ custom linter を書くことにしたい
- そのあたりの一般原則の言語化が必要

# permissions によるファイルアクセス権制御

- codex cli がバグってるっぽい
- permissions を使うと、それが原因で bwrap によるサンドボックス実行に失敗する
- bwrap 外でのエスカーレション実行にフォールバックするが、なぜか承認 UI が出てこない
- 多分 codex cli のバグ修正を待つしか無くて、それまでは指示文にアクセス禁止ルールを書くしか無い

# tgbt 起動時の Codex CLI 関係チェック

- tgbt からの呼び出し時、基本的には更新チェックは OFF ということにした
- なので、専用の仕組みを用意して、チェックが走るようにしたい
- あと、事前にユーザーが Codex CLI を直接起動してログイン状態にする必要があるけど、その案内も必要だろう
- Codex CLI の設定が正しいかどうかはスキーマと照合する必要がある（存在しないキーを指定した時に、それがエラーにならない）

## codex  呼び出し情報に git ステータスを含めたい

- codex 実行前の git commit hash

## Task Prompt が結構ガバガバそう

- あんまり腹落ちしてない
- Read targets とか結構怪しいし
- もっと詰める必要がある

## 知識システムの扱い

- Codex CLI から呼び出せるようにする必要アリ
- 知識システムからの Codex CLI の呼び出しか、知識システム外での Codex CLI 呼び出しか、どちらなのかによってプロンプトが変わってくるので、それも oracle に組み込む必要がある



oracle/docs/tgbt_spec/tgbt_call_rules.md で tgbt による入れ子呼び出しの規則を記述しました。
oracle/docs/tgbt_spec/structured_prompt.md でプロンプトの構成を記述しました。
これらの内容を元に


## カテゴリ 1: Codex prompt 組み立て基盤

Codex CLI にわたすプロンプトブロックの構成を oracle の記述内容に追従させてください。

想定作業:
- Fixed prompt を常時先頭に挿入する仕組みを作る。
- Execution context / Authority rules / Oracle rules / Access restrictions / Input interpretation /
Workspace file handling / Scope and autonomy / Conflict and uncertainty handling / Output discipline
を prompt block として実体化する。
- Knowledge system rules を Fixed prompt と Structured output の間に挿入できるようにする。
- Structured output を oracle の階層に合わせ、Structured output rules / Schema-specific rules / Caller
schema rules をまとめて扱えるようにする。
- caller 側 schema prompt、つまり呼び出しごとに変わる schema 説明を渡す口を作る。

根拠:

- oracle は最終順序を Fixed prompt → Knowledge system rules → Structured output → Task prompt としてい
る: oracle/docs/tgbt_spec/structured_prompt.md:314
- 現実装は output_schema がある場合だけ Structured output rules と Schema-specific rules を先頭に足して
おり、固定プロンプトも Knowledge system rules も caller schema rules もない: src/agent_wrapper/
codex_wrapper.py:108, src/agent_wrapper/codex_wrapper.py:320
- prompt block の木構造と Markdown rendering 自体は既にあるので、土台は使えそう: src/schemas/
markdown.py:25

カテゴリ 2: 既存タスク prompt の構造化追従

必要作業:

- tgbt plan の新規作成・更新 prompt を、oracle の推奨 block 構成に寄せる。
- 知識システム内部の各 AI 呼び出し prompt も、少なくとも Task / Authority rules / Input handling
rules / Read targets / Task-specific rules / Operational parameters / Inputs / Uncertainty handling /
Self check の観点で整理する。
- ファイル本文や既存 JSON を data として扱う指示を、個別 prompt に散らすのではなく共通ルールと task-
specific rules に分離する。
- Read targets は「path / 目的 / data or instruction」を明示する形式へ寄せる。

根拠:

- oracle はタスク prompt の推奨 block 構成を明記している: oracle/docs/tgbt_spec/
structured_prompt.md:145
- tgbt plan 新規作成は現状 Quality rules と User instruction 中心で、推奨構成にはなっていない: src/
sub_commands/plan/tgbt_plan.py:111
- plan 更新も Update rules / Existing plan JSON / New user instruction の個別構成: src/sub_commands/
plan/tgbt_plan.py:153
- 知識システムの prompt も Question / Task / 候補一覧などの ad hoc block が多く、oracle の標準構成には
未統一: src/state/knowledge_system.py:231, src/state/knowledge_system.py:381, src/state/
knowledge_system.py:417

カテゴリ 3: Knowledge system rules と公開 knowledge search 呼び出し

必要作業:

- Codex CLI 呼び出しごとに「知識システムを使う」「使わない」を明示する API を CodexWrapper.run 付近に追
加する。
- 通常の repo 調査系 Codex 呼び出しでは、Knowledge system rules により tgbt knowledge search を使わせ
る。
- 知識システム自身が内部で Codex CLI を呼ぶ場合は、再帰を避けるため Knowledge system rules を「使わな
い」側に切り替える。
- tgbt knowledge search 相当の CLI サブコマンドを公開する。現状 KnowledgeSystem.search() はあるが、CLI
入口がない。
- 必要なら knowledge improve の公開有無も oracle の「公開インターフェース」に合わせて整理する。

根拠:

- oracle は Knowledge system rules を Codex CLI 呼び出しごとに切り替えるとしている: oracle/docs/
tgbt_spec/structured_prompt.md:225
- oracle は tgbt knowledge search を stack 再入の例外例としている: oracle/docs/tgbt_spec/
tgbt_call_rules.md:15
- 知識検索自体の仕様は公開インターフェースとして書かれている: oracle/docs/tgbt_spec/
knowledge_system.md:119
- 現 CLI は plan と run だけで、knowledge サブコマンドがない: src/main.py:28, src/main.py:62
- 実装上の検索本体は既に KnowledgeSystem.search() として存在する: src/state/knowledge_system.py:124

カテゴリ 4: tgbt 呼び出しの排他・再入制御

必要作業:

- root call id 管理を追加する。
- ルートレベル tgbt 起動時に UUID を生成する。
- Codex CLI 起動時に TGBT_ROOT_CALL_ID を環境変数として渡す。
- tgbt 起動時に TGBT_ROOT_CALL_ID が存在する場合は非ルート呼び出しとして扱う。
- 非ルート呼び出しでは、再入許可されたサブコマンドだけロックなしで実行し、それ以外はエラー終了する。
- ロック例外判定を --help だけでなく「副作用を持たないサブコマンド」と「再入許可サブコマンド」に拡張す
る。
- lock / root_call_id / reentrant 여부を tgbt call log に載せるか検討する。これはログから実行経緯を追え

根拠:

- oracle は .tgbt/tgbt.lock の flock、非ブロッキング失敗、main 関数の早い段階での取得を指定している:
oracle/docs/tgbt_spec/tgbt_call_rules.md:29
- oracle は TGBT_ROOT_CALL_ID による stack 再入判定を指定している: oracle/docs/tgbt_spec/
tgbt_call_rules.md:42
- 現実装には repo lock はある: src/main.py:75, src/util/tgbt_repo_lock.py:13
- ただし現実装の lock 例外は help だけで、TGBT_ROOT_CALL_ID は参照も設定もされていない: src/main.py:79,
src/agent_wrapper/codex_wrapper.py:86

カテゴリ 5: tgbt 内の Codex CLI fork-join 並列呼び出し防止

必要作業:

- CodexWrapper か _run_codex_cli 周辺にプロセス内同期プリミティブを追加する。
- Codex CLI 呼び出し中に別の Codex CLI 呼び出しが始まった場合、ブロックせず例外を投げるか、oracle の
「例外を投げる」に合わせたエラーにする。
- smoke test も同じ guard の対象にするかを決める。現状は _run_codex_cli() が smoke test から再帰的に呼
ばれるので、guard を単純に置くと壊れる可能性がある。
- 知識システムの連続 AI 呼び出しは直列なので基本的には維持でよいが、将来並列化されないようテストまたは
実装境界で守る。

根拠:

- oracle は「1つの tgbt 呼び出し上で複数の Codex CLI 呼び出しが fork-join 的に並列に動くのは禁止」とし
ている: oracle/docs/tgbt_spec/tgbt_call_rules.md:10
- 実装指定は「python プロセス内同期プリミティブで排他制御」「並列呼び出し検知時は例外」: oracle/docs/
tgbt_spec/tgbt_call_rules.md:37
- 現状 _run_codex_cli は直接 subprocess.run しており、同期プリミティブは見当たらない: src/
agent_wrapper/codex_wrapper.py:141

カテゴリ 6: ログ仕様の拡充・検証

必要作業:

- 既存ログはかなり追従済みなので、主に不足分の確認と追加でよい。
- Codex CLI 呼び出しログについて、環境として CODEX_HOME 以外に TGBT_ROOT_CALL_ID を追加する。
- Codex CLI 呼び出しログに「Knowledge system rules を使ったか」「最終 prompt block 順序」「fixed prompt
version 相当」を残すと、追加仕様のデバッグに効く。
- tgbt call log に root/reentrant/lock 取得対象/lock 例外理由を残す。
- 仕様上「関連ログのパス、あるいは関連要素の ID」なので、root_call_id を related ID として扱う設計もあ
り得る。

根拠:

- oracle は Codex CLI 呼び出しログに実行時環境、config、schema などの設定すべてを含めるとしている:
oracle/docs/tgbt_spec/logs.md:21
- oracle は tgbt 呼び出しログに実行結果、引数、関連ログパスまたは関連要素 ID を含めるとしている:
oracle/docs/tgbt_spec/logs.md:28
- 現実装は Codex log に command / cwd / CODEX_HOME / config.toml / prompt / schema / stdout/stderr /
structured response を保存している: src/agent_wrapper/codex_wrapper.py:170
- 現実装は tgbt call log に argv / exit_code / error / related log paths を保存している: src/util/
tgbt_call_log.py:65