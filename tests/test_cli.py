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
    assert args.revision_range == "origin/main..HEAD"