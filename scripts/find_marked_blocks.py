#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Print inclusive source line ranges enclosed by standalone marker comments.

Each matching block is printed as ``START END``, one block per line.
Without ``--name``, all named and legacy unnamed blocks are returned::

    uv run --script scripts/find_marked_blocks.py -f main.py
    uv run --script scripts/find_marked_blocks.py -f main.py -n calculate_total
    uv run --script scripts/find_marked_blocks.py -f main.py \
        -n calculate_total --start-mark BEGIN_WORK --end-mark END_WORK
"""

import argparse
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find source lines between marker comments.")
    parser.add_argument("-f", "--file", required=True, help="File to search")
    parser.add_argument("-n", "--name", default=None,
                        help="Only return blocks with this name (default: all blocks)")
    parser.add_argument("--start-mark", default="MARKER_START",
                        help="Opening marker text (default: MARKER_START)")
    parser.add_argument("--end-mark", default="MARKER_END",
                        help="Closing marker text (default: MARKER_END)")
    return parser.parse_args(argv)


def find_blocks(source: str, start_mark: str, end_mark: str,
                name: str | None = None) -> list[tuple[int, int]]:
    if not start_mark or not end_mark or start_mark == end_mark:
        raise ValueError("start and end marks must be nonempty and different")
    if any("\n" in mark or "\r" in mark for mark in (start_mark, end_mark)):
        raise ValueError("marks cannot contain newlines")
    opening = f"# {start_mark}"
    closing = f"# {end_mark}"
    if name is not None and (not name.strip() or "\n" in name or "\r" in name):
        raise ValueError("name must be nonempty and contain no newlines")

    def marker_name(line: str, mark: str) -> tuple[bool, str | None]:
        if line == mark:
            return True, None
        if line.startswith(mark + ": "):
            return True, line[len(mark) + 2:]
        return False, None

    blocks = []
    open_line = None
    open_name = None
    for number, line in enumerate(source.splitlines(), 1):
        marker = line.strip()
        is_start, found_name = marker_name(marker, opening)
        is_end, end_name = marker_name(marker, closing)
        if name is not None:
            is_start = is_start and found_name == name
            is_end = is_end and end_name == name
        if is_start:
            if open_line is not None:
                raise ValueError(f"nested start mark on line {number}")
            open_line = number
            open_name = found_name
        elif is_end:
            if open_line is None:
                raise ValueError(f"end mark on line {number} has no start mark")
            if end_name != open_name:
                raise ValueError(f"end mark on line {number} has a different name")
            if number == open_line + 1:
                raise ValueError(f"empty marked block on lines {open_line}-{number}")
            blocks.append((open_line + 1, number - 1))
            open_line = None
            open_name = None
    if open_line is not None:
        raise ValueError(f"start mark on line {open_line} has no end mark")
    return blocks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    target = Path(args.file).resolve()
    if not target.is_file():
        print(f"error: file not found: {target}", file=sys.stderr)
        return 2
    try:
        with target.open("r", newline="") as stream:
            blocks = find_blocks(stream.read(), args.start_mark, args.end_mark, args.name)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for start_line, end_line in blocks:
        print(start_line, end_line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
