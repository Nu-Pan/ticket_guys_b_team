import textwrap


def stdtqs(text: str) -> str:
    """
    triple-quoted string を正規化する。
    """
    lines = text.splitlines()

    # 先頭・末尾の空行だけを落としてから、共通インデントを解除する。
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while start < end and not lines[end - 1].strip():
        end -= 1

    return textwrap.dedent("\n".join(lines[start:end]))
