# std
from typing import Any
import typer


def tgbt_error(
    summary: str,
    next: str = "",
    actual: dict[str, Any] = dict(),
    expect: dict[str, Any] = dict(),
    exc_obj: int | BaseException = 1,
) -> BaseException:
    """
    エラー情報を表示した上で適切な例外を投げて終了する。
    tgbt が継続不能になったらこの関数を呼び出す。
    通常は
    ```
    raise tgbt_error("エラーの短い説明", "次に取るべきアクション")
    ```
    のような使い方をする。
    """
    # エラー内容をダンプ
    typer.echo(f"summary: {summary}")
    typer.echo(f"next: {next}")
    typer.echo(f"actual: {actual}")
    typer.echo(f"expect: {expect}")

    # 適切な例外を返す
    if isinstance(exc_obj, int):
        return typer.Exit(code=exc_obj)
    else:
        return exc_obj
