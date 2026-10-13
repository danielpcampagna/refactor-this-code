#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["rope"]
# ///
"""Extract lines from a Python file into a new method/function using rope.

Run ad-hoc, no project install needed:

    uv run --script extract.py --file main.py --start-line 5 --end-line 6 --name new_helper
    uv run --script extract.py -f main.py -s 14 -e 15 -n new_helper --no-apply
    uv run --script extract.py -f main.py -s 14 -e 15 -n new_helper --project .
"""

import argparse
import sys
from pathlib import Path

from rope.base import libutils
from rope.base.project import Project
from rope.refactor.extract import ExtractMethod


def lines_to_offsets(source: str, start_line: int, end_line: int) -> tuple[int, int]:
    """Convert 1-indexed inclusive lines to rope character offsets.

    Start = beginning of start_line, end = end of end_line, so the
    informed lines are fully included in the extraction (replaces the
    old MARKER_START / MARKER_END comment search).
    """
    lines = source.splitlines(keepends=True)
    total = len(lines)
    if total == 0:
        raise ValueError("target file is empty")
    if not (1 <= start_line <= end_line <= total):
        raise ValueError(f"invalid line range [{start_line}, {end_line}], file has {total} lines")
    start = sum(len(l) for l in lines[: start_line - 1])
    end = sum(len(l) for l in lines[:end_line])
    return start, end


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Extract given lines into a new method/function via rope."
    )
    p.add_argument("-f", "--file", required=True, help="Python file to refactor")
    p.add_argument(
        "-s",
        "--start-line",
        type=int,
        required=True,
        help="First line to extract (1-indexed, inclusive)",
    )
    p.add_argument(
        "-e",
        "--end-line",
        type=int,
        required=True,
        help="Last line to extract (1-indexed, inclusive)",
    )
    p.add_argument("-n", "--name", required=True, help="Name of the new method/function")
    p.add_argument(
        "-p",
        "--project",
        default=None,
        help="Rope project root. Defaults to the target file's parent dir. "
        "Only needed when the file imports siblings or you want an explicit root.",
    )
    p.add_argument(
        "--no-apply",
        action="store_true",
        help="Preview only: print the changeset description without writing.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    target = Path(args.file).resolve()
    if not target.is_file():
        print(f"error: file not found: {target}", file=sys.stderr)
        return 2

    # Default project root = folder containing the target file, so an
    # ad-hoc script needs no --project in the common single-file case.
    project_root = Path(args.project).resolve() if args.project else target.parent
    try:
        rel = target.relative_to(project_root)
    except ValueError:
        print(f"error: file {target} is not inside project root {project_root}", file=sys.stderr)
        return 2

    # libutils resolves an absolute path against the project root,
    # so pass the absolute target (a bare relative name would resolve
    # against the cwd, not the project root).
    project = Project(str(project_root), ropefolder=None)
    try:
        resource = libutils.path_to_resource(project, str(target))
        source = resource.read()
        try:
            start, end = lines_to_offsets(source, args.start_line, args.end_line)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        extractor = ExtractMethod(project, resource, start, end)
        changes = extractor.get_changes(args.name)
        print(changes.get_description())
        if not args.no_apply:
            project.do(changes)
    finally:
        project.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
