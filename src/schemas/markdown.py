# std
from dataclasses import dataclass
from typing import Protocol, Sequence


class HasText(Protocol):
    text: str


class HasIdText(HasText, Protocol):
    id: str


@dataclass(frozen=True)
class MarkdownSection:
    """
    Markdown document の section を表す。
    """

    title: str
    body: str


@dataclass(frozen=True)
class MarkdownPromptBlock:
    """
    AI に渡す prompt を構成する Markdown 見出しブロック。
    """

    title: str
    body: str = ""
    children: Sequence["MarkdownPromptBlock"] = ()


def _render_prompt_block(block: MarkdownPromptBlock, level: int) -> list[str]:
    """
    prompt block とその子孫を Markdown 行へ描画する。
    """
    lines = [f"{'#' * level} {block.title}", ""]

    # 本文は見出し直下の block 内容として配置する。
    body = block.body.strip()
    if body != "":
        lines.extend([body, ""])

    # 子 block は見出しレベルを 1 つ深くして順番通りに配置する。
    for child in block.children:
        lines.extend(_render_prompt_block(child, level + 1))

    return lines


def render_prompt(blocks: Sequence[MarkdownPromptBlock]) -> str:
    """
    Markdown 見出しブロック列から AI に渡す prompt を組み立てる。
    """
    lines: list[str] = []
    for block in blocks:
        lines.extend(_render_prompt_block(block, 1))

    if len(lines) > 0 and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def render_metadata_item(key: str, value: str) -> str:
    """
    Markdown document 先頭に置く metadata item を描画する。
    """
    return f"- {key}: `{value}`"


def render_id_text_items(items: Sequence[HasIdText]) -> str:
    """
    id と text を持つ schema item の Markdown list を描画する。
    """
    if len(items) == 0:
        return "- なし"

    return "\n".join(f"- `{item.id}` {item.text}" for item in items)


def render_plain_items(items: Sequence[str]) -> str:
    """
    文字列 item の Markdown list を描画する。
    """
    if len(items) == 0:
        return "- なし"

    return "\n".join(f"- {item}" for item in items)


def render_text_blocks(items: Sequence[HasText]) -> str:
    """
    text を持つ schema item を fenced code block として描画する。
    """
    if len(items) == 0:
        return "なし"

    return "\n\n".join(f"```text\n{item.text}\n```" for item in items)


def render_document(
    title: str,
    metadata: Sequence[str],
    sections: Sequence[MarkdownSection],
) -> str:
    """
    title、metadata、sections から Markdown document を組み立てる。
    """
    lines = [f"# {title}", ""]

    # 人間が先頭で補助情報を確認できるよう、metadata は section より前に集約する。
    for item in metadata:
        lines.append(item)
    if len(metadata) > 0:
        lines.append("")

    for section in sections:
        lines.extend(
            [
                f"## {section.title}",
                "",
                section.body,
                "",
            ]
        )

    if lines[-1] == "":
        lines.pop()
    return "\n".join(lines)
