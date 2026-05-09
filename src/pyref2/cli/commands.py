"""CLI entrypoints for invoking PyRef2 analysis workflows."""

from __future__ import annotations

import argparse
import sys

from pyref2.service import (
    analyze_files,
    analyze_revision_range,
    analyze_trees,
    serialize_findings,
    write_findings,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyref2", description="PyRef2 refactoring analysis CLI")
    subparsers = parser.add_subparsers(dest="command")

    analyze_files_parser = subparsers.add_parser(
        "analyze-files",
        help="Analyze refactorings between two Python files",
    )
    analyze_files_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format (default: json)",
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
    analyze_files_parser.add_argument(
        "--output",
        required=False,
        help="Optional output path (content follows --format)",
    )

    analyze_tree_parser = subparsers.add_parser(
        "analyze-tree",
        help="Analyze refactorings between two source tree revisions",
    )
    analyze_tree_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format (default: json)",
    )
    analyze_tree_parser.add_argument(
        "--before-root",
        required=True,
        help="Path to the older source tree revision",
    )
    analyze_tree_parser.add_argument(
        "--after-root",
        required=True,
        help="Path to the newer source tree revision",
    )
    analyze_tree_parser.add_argument(
        "--output",
        required=False,
        help="Optional output path (content follows --format)",
    )

    analyze_revisions_parser = subparsers.add_parser(
        "analyze-revisions",
        help="Analyze refactorings between two Git revisions or a revision range",
    )
    analyze_revisions_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format (default: json)",
    )
    analyze_revisions_parser.add_argument(
        "--repo",
        required=True,
        help="Path to the Git repository to analyze",
    )
    analyze_revisions_parser.add_argument(
        "revision_range",
        help="Git revision range like origin/main..HEAD",
    )
    analyze_revisions_parser.add_argument(
        "--output",
        required=False,
        help="Optional output path (content follows --format)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    # Keep CLI thin: parse args, delegate to service, print/emit output.
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze-files":
        findings = analyze_files(args.before, args.after)
        if args.output:
            write_findings(args.output, findings, output_format=args.format)
            print(f"Wrote {len(findings)} findings to {args.output}")
        else:
            print(serialize_findings(findings, output_format=args.format))
        return 0

    if args.command == "analyze-tree":
        findings = analyze_trees(args.before_root, args.after_root)
        if args.output:
            write_findings(args.output, findings, output_format=args.format)
            print(f"Wrote {len(findings)} findings to {args.output}")
        else:
            print(serialize_findings(findings, output_format=args.format))
        return 0

    if args.command == "analyze-revisions":
        findings = analyze_revision_range(args.repo, args.revision_range)

        if args.output:
            write_findings(args.output, findings, output_format=args.format)
            print(f"Wrote {len(findings)} findings to {args.output}")
        else:
            print(serialize_findings(findings, output_format=args.format))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
