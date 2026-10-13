#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Surround inclusive source lines with standalone marker comments.

When no name is supplied, both comments receive the same generated UUID.

    uv run --script scripts/mark_block.py -f main.py -s 5 -e 8
    uv run --script scripts/mark_block.py -f main.py -s 5 -e 8 -n calculate_total
    uv run --script scripts/mark_block.py -f main.py -s 5 -e 8 \
        -n calculate_total --start-mark BEGIN_WORK --end-mark END_WORK
"""

import argparse
import sys
import uuid
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mark a block of source lines.")
    parser.add_argument("-f", "--file", required=True, help="File to mark")
    parser.add_argument("-s", "--start-line", type=int, required=True,
                        help="First block line (1-indexed, inclusive)")
    parser.add_argument("-e", "--end-line", type=int, required=True,
                        help="Last block line (1-indexed, inclusive)")
    parser.add_argument("-n", "--name", default=None,
                        help="Block name appended to both markers (default: generated UUID)")
    parser.add_argument("--start-mark", default="MARKER_START",
                        help="Opening marker text (default: MARKER_START)")
    parser.add_argument("--end-mark", default="MARKER_END",
                        help="Closing marker text (default: MARKER_END)")
    return parser.parse_args(argv)


def mark_block(source: str, start_line: int, end_line: int,
               start_mark: str, end_mark: str, name: str | None = None) -> str:
    lines = source.splitlines(keepends=True)
    if not 1 <= start_line <= end_line <= len(lines):
        raise ValueError(f"invalid line range [{start_line}, {end_line}], file has {len(lines)} lines")
    for label, mark in (("start", start_mark), ("end", end_mark)):
        if not mark or "\n" in mark or "\r" in mark:
            raise ValueError(f"{label} mark must be nonempty and contain no newlines")
    if start_mark == end_mark:
        raise ValueError("start and end marks must differ")
    if name is None:
        name = str(uuid.uuid4())
    if not name.strip() or "\n" in name or "\r" in name:
        raise ValueError("name must be nonempty and contain no newlines")
    start_mark = f"{start_mark}: {name}"
    end_mark = f"{end_mark}: {name}"

    first_line = lines[start_line - 1]
    indent = first_line[:len(first_line) - len(first_line.lstrip(" \t"))]
    newline = "\r\n" if "\r\n" in source else "\n"
    selected = lines[start_line - 1:end_line]
    if not selected[-1].endswith(("\n", "\r")):
        selected[-1] += newline
    return "".join(lines[:start_line - 1] + [f"{indent}# {start_mark}{newline}"]
                   + selected + [f"{indent}# {end_mark}{newline}"] + lines[end_line:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    target = Path(args.file).resolve()
    if not target.is_file():
        print(f"error: file not found: {target}", file=sys.stderr)
        return 2
    try:
        with target.open("r", newline="") as stream:
            source = stream.read()
        name = args.name if args.name is not None else str(uuid.uuid4())
        result = mark_block(source, args.start_line, args.end_line,
                            args.start_mark, args.end_mark, name)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    with target.open("w", newline="") as stream:
        stream.write(result)
    print(f"marked lines {args.start_line}-{args.end_line} in {target} (name: {name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
