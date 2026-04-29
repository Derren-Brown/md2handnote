from __future__ import annotations

from dataclasses import dataclass

from .errors import ParseError


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int


@dataclass(frozen=True)
class ParseResult:
    tokens: list[Token]
    warnings: list[str]


def parse_markdown(text: str) -> ParseResult:
    tokens: list[Token] = []
    warnings: list[str] = []
    lines = text.splitlines()
    in_block_math = False
    block_start_line = 0
    block_parts: list[str] = []
    in_code_fence = False

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            warnings.append(f"Line {index}: code fences are treated as plain text in the MVP")

        if in_block_math:
            close_at = _find_unescaped_double_dollar(line)
            if close_at is None:
                block_parts.append(line)
                continue

            before = line[:close_at]
            after = line[close_at + 2 :]
            if before:
                block_parts.append(before)
            tokens.append(Token("block_math", "\n".join(block_parts).strip(), block_start_line))
            in_block_math = False
            block_parts = []
            if after.strip():
                tokens.extend(_parse_inline_line(after, index))
            tokens.append(Token("line_break", "", index))
            continue

        if not stripped:
            tokens.append(Token("blank_line", "", index))
            continue

        _warn_unsupported_markdown(line, index, warnings, in_code_fence)

        cursor = 0
        while True:
            open_at = _find_unescaped_double_dollar(line, cursor)
            if open_at is None:
                remainder = line[cursor:]
                if remainder:
                    tokens.extend(_parse_inline_line(remainder, index))
                tokens.append(Token("line_break", "", index))
                break

            before = line[cursor:open_at]
            if before:
                tokens.extend(_parse_inline_line(before, index))

            close_at = _find_unescaped_double_dollar(line, open_at + 2)
            if close_at is None:
                in_block_math = True
                block_start_line = index
                first_part = line[open_at + 2 :]
                block_parts = [first_part] if first_part else []
                break

            formula = line[open_at + 2 : close_at].strip()
            tokens.append(Token("block_math", formula, index))
            cursor = close_at + 2

    if in_block_math:
        raise ParseError(f"Unclosed block math starting at line {block_start_line}")
    if in_code_fence:
        warnings.append("Code fence was not closed; content was treated as plain text")

    return ParseResult(tokens=tokens, warnings=warnings)


def _parse_inline_line(line: str, line_no: int) -> list[Token]:
    tokens: list[Token] = []
    cursor = 0
    while cursor < len(line):
        open_at = _find_unescaped_single_dollar(line, cursor)
        if open_at is None:
            text = line[cursor:]
            if text:
                tokens.append(Token("text", text, line_no))
            break

        if open_at > cursor:
            tokens.append(Token("text", line[cursor:open_at], line_no))

        close_at = _find_unescaped_single_dollar(line, open_at + 1)
        if close_at is None:
            raise ParseError(f"Unclosed inline math starting at line {line_no}")
        formula = line[open_at + 1 : close_at].strip()
        tokens.append(Token("inline_math", formula, line_no))
        cursor = close_at + 1

    return tokens


def _find_unescaped_double_dollar(line: str, start: int = 0) -> int | None:
    i = start
    while i < len(line) - 1:
        if line[i : i + 2] == "$$" and not _is_escaped(line, i):
            return i
        i += 1
    return None


def _find_unescaped_single_dollar(line: str, start: int = 0) -> int | None:
    i = start
    while i < len(line):
        if line[i] == "$" and not _is_escaped(line, i):
            if i + 1 < len(line) and line[i + 1] == "$":
                i += 2
                continue
            if i > 0 and line[i - 1] == "$":
                i += 1
                continue
            return i
        i += 1
    return None


def _is_escaped(line: str, index: int) -> bool:
    slash_count = 0
    i = index - 1
    while i >= 0 and line[i] == "\\":
        slash_count += 1
        i -= 1
    return slash_count % 2 == 1


def _warn_unsupported_markdown(
    line: str, line_no: int, warnings: list[str], in_code_fence: bool
) -> None:
    stripped = line.lstrip()
    if in_code_fence:
        return
    if stripped.startswith("#"):
        warnings.append(f"Line {line_no}: headings are treated as plain text in the MVP")
    elif stripped.startswith(("- ", "* ", "+ ")) or _looks_like_ordered_list(stripped):
        warnings.append(f"Line {line_no}: lists are treated as plain text in the MVP")
    elif stripped.startswith(">"):
        warnings.append(f"Line {line_no}: block quotes are treated as plain text in the MVP")
    elif stripped.startswith("!["):
        warnings.append(f"Line {line_no}: images are not supported in the MVP")
    elif "|" in stripped and stripped.count("|") >= 2:
        warnings.append(f"Line {line_no}: tables are treated as plain text in the MVP")


def _looks_like_ordered_list(text: str) -> bool:
    number = ""
    for char in text:
        if char.isdigit():
            number += char
            continue
        return bool(number) and text.startswith(number + ". ")
    return False
