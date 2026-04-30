# local
from util.error import tgbt_error


def create_plan(instruction: str) -> str:
    pass


def udate_plan(
    instruction: str,
    plan_id: str | None,
):
    pass


def tgbt_plan_docs_impl(
    instruction: str,
    plan_id: str | None,
) -> None:
    """
    `tgbt plan docs` の実装。
    """
    if plan_id is None:
        create_plan(instruction)
    else:
        udate_plan(instruction, plan_id)
