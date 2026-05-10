# std
import subprocess
from collections.abc import Sequence

# local
from state.path import TGBT_PATH
from util.error import tgbt_error

_PLAN_BRANCH_PREFIX = "tgbt-plan"
_HUMAN_MANAGED_PATHS = ("oracles", "oraclesmemo")


def plan_branch_name(plan_id: str) -> str:
    """plan id に対応する plan branch 名を返す."""
    # plan id から一意に決まる branch 名にして、plan schema 変更を避ける。
    return f"{_PLAN_BRANCH_PREFIX}/{plan_id}"


def prepare_new_plan_branch(plan_id: str) -> None:
    """新規 plan 用に clean 確認と plan branch 作成を行う."""
    # 新規 plan 開始時は、人間が事前に clean な状態へ整える前提にする。
    assert_git_worktree_clean(
        summary="git の未コミット差分があるため新規 plan を開始できません",
        next_message="変更を commit するか破棄してから `tgbt plan` を再実行してください。",
    )

    # default branch の最新ローカルコミットを起点に plan branch を作成する。
    default_branch = _resolve_default_branch()
    branch_name = plan_branch_name(plan_id)
    _run_git(["switch", default_branch])
    _run_git(["switch", "-c", branch_name])


def prepare_existing_plan_branch(plan_id: str) -> None:
    """既存 plan の更新・実行前に plan branch と clean 状態を確認する."""
    # plan id から決まる branch を、既存 plan の plan branch 設定として扱う。
    expected_branch = plan_branch_name(plan_id)
    actual_branch = current_branch_name()
    if actual_branch != expected_branch:
        raise tgbt_error(
            "plan branch をチェックアウトしていないため処理を開始できません",
            "対象 plan の plan branch を checkout してから再実行してください。",
            actual={"current_branch": actual_branch, "plan_id": plan_id},
            expect={"branch": expected_branch},
        )


def commit_human_managed_changes_for_plan_update() -> None:
    """plan 更新前に人間管理ファイルの差分だけを自動 commit する."""
    # plan 更新では oracles/oraclesmemo の人間管理差分だけを先に保存する。
    changed_paths = _changed_paths_for_pathspecs(_HUMAN_MANAGED_PATHS)
    if len(changed_paths) == 0:
        return

    _run_git(["add", "--", *_HUMAN_MANAGED_PATHS])
    _commit_staged_changes("tgbt plan: commit human-managed changes")


def assert_git_worktree_clean(summary: str, next_message: str) -> None:
    """git の未コミット差分が無いことを確認する."""
    # porcelain 出力が 1 行でもあれば、追跡・未追跡を問わず未コミット差分として扱う。
    status = _git_stdout(["status", "--porcelain"])
    if status != "":
        raise tgbt_error(
            summary,
            next_message,
            actual={"git_status": status},
            expect={"git_status": ""},
        )


def auto_commit_uncommitted_changes(message: str) -> None:
    """未コミット差分があればまとめて自動 commit する."""
    # 差分が無い場合は、git commit を呼ばず正常に何もしない。
    if _git_stdout(["status", "--porcelain"]) == "":
        return

    _run_git(["add", "-A"])
    _commit_staged_changes(message)


def current_branch_name() -> str:
    """現在 checkout している branch 名を返す."""
    # detached HEAD は plan branch ではないため、git の出力をそのまま検証に使う。
    return _git_stdout(["branch", "--show-current"])


def _resolve_default_branch() -> str:
    """origin HEAD を優先して default branch 名を解決する."""
    # origin HEAD が設定済みなら、それを default branch として使う。
    remote_default = _git_stdout(
        ["symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"],
        check=False,
    )
    if remote_default.startswith("refs/remotes/origin/"):
        default_branch = remote_default.removeprefix("refs/remotes/origin/")
        _assert_local_branch_exists(default_branch)
        return default_branch

    # remote が無い repo でも動けるよう、代表的な local branch 名だけ補助的に見る。
    for candidate in ("main", "master"):
        if _local_branch_exists(candidate):
            return candidate

    raise tgbt_error(
        "default branch の解決に失敗しました",
        "origin/HEAD を設定するか、local に main または master branch を用意してください。",
        actual={"origin_head": remote_default},
        expect={"default_branch": "origin/HEAD, main, or master"},
    )


def _assert_local_branch_exists(branch_name: str) -> None:
    """local branch が存在することを確認する."""
    # default branch の最新ローカルコミットを起点にするため、local branch を必須にする。
    if not _local_branch_exists(branch_name):
        raise tgbt_error(
            "local default branch が見つかりません",
            "origin の default branch に対応する local branch を作成してから再実行してください。",
            actual={"branch": branch_name},
        )


def _local_branch_exists(branch_name: str) -> bool:
    """local branch が存在するか判定する."""
    # show-ref の終了コードだけを branch 存在判定に使う。
    completed = _run_git(
        ["show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
        check=False,
    )
    return completed.returncode == 0


def _changed_paths_for_pathspecs(pathspecs: Sequence[str]) -> list[str]:
    """指定 pathspec 配下の未コミット変更 path を返す."""
    # porcelain v1 の先頭 3 文字以降は path なので、rename 表記もそのまま path 情報として扱う。
    output = _git_stdout(["status", "--porcelain", "--", *pathspecs])
    if output == "":
        return []
    return [line[3:] for line in output.splitlines()]


def _commit_staged_changes(message: str) -> None:
    """stage 済み差分を commit する."""
    # staged 差分が無いときは commit せず、呼び出し元の意図を no-op として扱う。
    if _run_git(["diff", "--cached", "--quiet"], check=False).returncode == 0:
        return

    _run_git(["commit", "-m", message])


def _run_git(
    args: Sequence[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """`<repo-root>` で git コマンドを実行する."""
    # git 操作対象は tgbt の開発 repo ではなく、tgbt が操作する repo root に固定する。
    completed = subprocess.run(
        ["git", *args],
        cwd=TGBT_PATH.repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and completed.returncode != 0:
        raise tgbt_error(
            "git コマンドの実行に失敗しました",
            "git の状態を確認してから再実行してください。",
            actual={
                "command": ["git", *args],
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
        )
    return completed


def _git_stdout(
    args: Sequence[str],
    *,
    check: bool = True,
) -> str:
    """git コマンドの stdout を末尾改行なしで返す."""
    # 値として扱いやすいよう、git 出力の前後空白はここで落とす。
    return _run_git(args, check=check).stdout.strip()
