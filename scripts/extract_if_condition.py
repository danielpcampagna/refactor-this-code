#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["rope"]
# ///
"""Extract an ``if`` or ``elif`` condition into a function or method.

Select the lines containing the complete header, including its closing colon::

    uv run --script scripts/extract_if_condition.py -f main.py -s 5 -e 8 -n is_ready
    uv run --script scripts/extract_if_condition.py -f main.py -s 5 -e 8 -n is_ready --no-apply
"""

import argparse
import ast
import io
import sys
import tokenize
from pathlib import Path

from rope.base import libutils
from rope.base.project import Project
from rope.refactor.extract import ExtractMethod


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract an if condition via rope.")
    parser.add_argument("-f", "--file", required=True, help="Python file to refactor")
    parser.add_argument("-s", "--start-line", type=int, required=True,
                        help="First line of the if/elif header (1-indexed)")
    parser.add_argument("-e", "--end-line", type=int, required=True,
                        help="Last line of the if/elif header (1-indexed)")
    parser.add_argument("-n", "--name", required=True,
                        help="Name of the new method/function")
    parser.add_argument("-p", "--project", default=None,
                        help="Rope project root. Defaults to the target file's parent dir.")
    parser.add_argument("--no-apply", action="store_true",
                        help="Preview only: print the changeset description without writing.")
    return parser.parse_args(argv)


def condition_offsets(source: str, start_line: int, end_line: int) -> tuple[int, int]:
    """Find the condition of the if/elif header selected by inclusive lines."""
    lines = source.splitlines(keepends=True)
    if not 1 <= start_line <= end_line <= len(lines):
        raise ValueError(f"invalid line range [{start_line}, {end_line}], file has {len(lines)} lines")

    tree = ast.parse(source)
    candidates = [node for node in ast.walk(tree)
                  if isinstance(node, ast.If) and node.lineno == start_line]
    if len(candidates) != 1:
        raise ValueError(f"expected one if/elif header starting on line {start_line}")
    condition = candidates[0].test

    # Token positions use character columns; AST positions use UTF-8 byte columns.
    # Locate the header colon to distinguish it from colons in nested expressions.
    header_end = None
    depth = 0
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.start[0] < start_line:
            continue
        if token.type == tokenize.OP:
            if token.string in "([{":
                depth += 1
            elif token.string in ")]}":
                depth -= 1
            elif token.string == ":" and depth == 0:
                header_end = token.start[0]
                break
    if header_end != end_line:
        raise ValueError(f"selected lines must cover the complete if/elif header "
                         f"[{start_line}, {header_end}]")

    def offset(line: int, byte_column: int) -> int:
        prefix = lines[line - 1].encode("utf-8")[:byte_column].decode("utf-8")
        return sum(map(len, lines[:line - 1])) + len(prefix)

    return (offset(condition.lineno, condition.col_offset),
            offset(condition.end_lineno, condition.end_col_offset))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    target = Path(args.file).resolve()
    if not target.is_file():
        print(f"error: file not found: {target}", file=sys.stderr)
        return 2

    project_root = Path(args.project).resolve() if args.project else target.parent
    try:
        target.relative_to(project_root)
    except ValueError:
        print(f"error: file {target} is not inside project root {project_root}",
              file=sys.stderr)
        return 2

    project = Project(str(project_root), ropefolder=None)
    try:
        resource = libutils.path_to_resource(project, str(target))
        try:
            start, end = condition_offsets(resource.read(), args.start_line, args.end_line)
        except (SyntaxError, tokenize.TokenError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        changes = ExtractMethod(project, resource, start, end).get_changes(args.name)
        print(changes.get_description())
        if not args.no_apply:
            project.do(changes)
    finally:
        project.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
