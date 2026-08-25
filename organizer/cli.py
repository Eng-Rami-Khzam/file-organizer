"""Command-line interface."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .core import OrganizerError, organize
from .models import DateGrouping, OrganizeReport, OrganizerConfig

logger = logging.getLogger(__name__)


def _human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def _parse_size(value: str) -> int:
    """Convert '10MB', '500KB' or a raw byte count into bytes."""
    text = value.strip().upper()
    multipliers = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}

    for suffix, factor in multipliers.items():
        if text.endswith(suffix):
            number = text[: -len(suffix)].strip()
            try:
                return int(float(number) * factor)
            except ValueError as e:
                raise argparse.ArgumentTypeError(f"invalid size: {value}") from e

    try:
        return int(text)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"invalid size: {value}") from e


def print_report(report: OrganizeReport) -> None:
    if not report.moves:
        print("Nothing to organize - folder is already tidy.")
        return

    header = "PLAN (dry run)" if report.dry_run else "DONE"
    print(f"\n{header}")
    print("=" * 60)

    for move in report.moves:
        relative = move.destination.relative_to(move.source.parent)
        print(f"  {move.source.name}")
        print(f"    -> {relative}")

    print("-" * 60)
    for category, count in sorted(report.counts_by_category.items()):
        print(f"  {category:<16} {count:>4} files")

    print("-" * 60)
    print(f"  {len(report.moves)} files, {_human_size(report.total_bytes)}")

    if report.skipped:
        print(f"  {len(report.skipped)} skipped")
    if report.failed:
        print(f"  {len(report.failed)} failed")
        for path, reason in report.failed:
            print(f"    {path.name}: {reason}")

    if report.dry_run:
        print("\n  Run again with --apply to move the files.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="file-organizer",
        description="Organize a messy folder by file type and modification date.",
    )
    parser.add_argument("folder", type=Path, help="folder to organize")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually move files (default is a dry run)",
    )
    parser.add_argument(
        "--by-date",
        choices=[g.value for g in DateGrouping],
        default=DateGrouping.MONTH.value,
        help="date sub-folder granularity (default: month)",
    )
    parser.add_argument(
        "--min-size",
        type=_parse_size,
        default=0,
        metavar="SIZE",
        help="ignore files smaller than this (e.g. 500KB, 10MB)",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="also organize hidden files",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose logging")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)-8s %(message)s",
    )

    config = OrganizerConfig(
        date_grouping=DateGrouping(args.by_date),
        min_size_bytes=args.min_size,
        skip_hidden=not args.include_hidden,
    )

    try:
        report = organize(args.folder, config, dry_run=not args.apply)
    except OrganizerError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print_report(report)
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
