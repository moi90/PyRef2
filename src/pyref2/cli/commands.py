"""CLI entrypoints for invoking PyRef2 analysis workflows."""

from __future__ import annotations

import argparse
import sys

from pyref2.service import analyze_files, findings_to_json, write_findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyref2", description="PyRef2 refactoring analysis CLI")
    subparsers = parser.add_subparsers(dest="command")

    analyze_files_parser = subparsers.add_parser(
        "analyze-files",
        help="Analyze refactorings between two Python files",
    )
    analyze_files_parser.add_argument(
        "--before",
        required=True,
        help="Path to the older file revision",
    )
    analyze_files_parser.add_argument(
        "--after",
        required=True,
        help="Path to the newer file revision",
    )
    analyze_files_parser.add_argument("--output", required=False, help="Optional JSON output path")

    return parser


def main(argv: list[str] | None = None) -> int:
    # Keep CLI thin: parse args, delegate to service, print/emit output.
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze-files":
        findings = analyze_files(args.before, args.after)
        if args.output:
            write_findings(args.output, findings)
            print(f"Wrote {len(findings)} findings to {args.output}")
        else:
            print(findings_to_json(findings))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
