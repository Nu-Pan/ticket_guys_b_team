# local
from state.git import assert_git_worktree_clean, prepare_existing_plan_branch
from util.error import tgbt_error


def tgbt_run_impl(plan_id: str) -> None:
    """
    `tgbt run` の実装。
    """
    # run は plan branch 上の clean な状態からだけ開始する。
    prepare_existing_plan_branch(plan_id)
    assert_git_worktree_clean(
        summary="git の未コミット差分があるため run を開始できません",
        next_message="やり残しを `tgbt plan` に差し戻すか、差分を commit/破棄してから再実行してください。",
    )

    # run は未実装であることを CLI 利用者に明示して終了する。
    raise tgbt_error(
        "tgbt run は未実装です",
        "将来の作業として tgbt run を実装する必要があります",
    )
