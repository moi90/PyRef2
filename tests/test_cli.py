from __future__ import annotations

from pyref2.cli.commands import build_parser


def test_parse_analyze_revisions_range_argument() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "analyze-revisions",
            "--repo",
            "/tmp/repo",
            "origin/main..HEAD",
        ]
    )

    assert args.command == "analyze-revisions"
    assert args.repo == "/tmp/repo"
    assert args.revision_spec == "origin/main..HEAD"


def test_parse_analyze_revisions_markdown_format() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "analyze-revisions",
            "--format",
            "markdown",
            "--repo",
            "/tmp/repo",
            "origin/main..HEAD",
        ]
    )

    assert args.command == "analyze-revisions"
    assert args.format == "markdown"


def test_parse_analyze_revisions_single_commit_argument() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "analyze-revisions",
            "--repo",
            "/tmp/repo",
            "HEAD",
        ]
    )

    assert args.command == "analyze-revisions"
    assert args.revision_spec == "HEAD"


def test_parse_analyze_revisions_without_revision_spec() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "analyze-revisions",
            "--repo",
            "/tmp/repo",
        ]
    )

    assert args.command == "analyze-revisions"
    assert args.revision_spec is None