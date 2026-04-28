# local
from util.error import tgbt_error


def tgbt_plan_docs_impl(
    instruction: str,
    plan_id: str | None,
) -> None:
    """
    `tgbt plan docs` の実装。
    """
    # 現時点では指示文入力だけを実装し、本体は既存通り未実装とする。
    _ = (
        instruction,
        plan_id,
    )
    raise tgbt_error(
        "tgbt plan docs は未実装です",
        "将来の作業として tgbt plan docs を実装する必要があります",
    )
