"""Organizing logic: plan first, then execute."""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from .models import DateGrouping, OrganizeReport, OrganizerConfig, PlannedMove

logger = logging.getLogger(__name__)


class OrganizerError(Exception):
    """Raised when a folder cannot be organized."""


def _date_folder(file: Path, grouping: DateGrouping) -> str:
    """Build the date sub-folder name from the file's modification time."""
    if grouping is DateGrouping.NONE:
        return ""

    modified = datetime.fromtimestamp(file.stat().st_mtime)
    if grouping is DateGrouping.YEAR:
        return modified.strftime("%Y")
    return modified.strftime("%Y-%m")


def _unique_destination(destination: Path, taken: set[Path]) -> Path:
    """Return a path that overwrites nothing.

    Checks both the filesystem and the paths already claimed during this
    run. The second check matters because planning happens before any file
    is moved, so two sources with the same name would otherwise be planned
    onto the same destination and one would be lost.
    """
    if destination not in taken and not destination.exists():
        return destination

    stem, suffix = destination.stem, destination.suffix
    counter = 1
    while True:
        candidate = destination.with_name(f"{stem}_{counter}{suffix}")
        if candidate not in taken and not candidate.exists():
            return candidate
        counter += 1


def _should_skip(file: Path, config: OrganizerConfig, category_names: set[str]) -> bool:
    """Decide whether an entry is left untouched."""
    if file.is_dir():
        return True
    if config.skip_hidden and file.name.startswith("."):
        return True
    if file.name in category_names:
        return True
    try:
        if file.stat().st_size < config.min_size_bytes:
            return True
    except OSError:
        return True
    return False


def plan(source: Path, config: OrganizerConfig) -> OrganizeReport:
    """Build the move plan without touching a single file."""
    if not source.exists():
        raise OrganizerError(f"Source folder not found: {source}")
    if not source.is_dir():
        raise OrganizerError(f"Source is not a folder: {source}")

    report = OrganizeReport(dry_run=True)
    category_names = set(config.categories) | {config.other_folder}
    taken: set[Path] = set()

    # iterdir(), not rglob(): only top-level entries are considered, so
    # files already sorted into category folders are ignored on re-runs.
    for item in sorted(source.iterdir()):
        if _should_skip(item, config, category_names):
            report.skipped.append(item)
            continue

        try:
            category = config.category_for(item.suffix)
            date_part = _date_folder(item, config.date_grouping)
            target_dir = source / category / date_part if date_part else source / category
            destination = _unique_destination(target_dir / item.name, taken)
            taken.add(destination)

            report.moves.append(
                PlannedMove(
                    source=item,
                    destination=destination,
                    category=category,
                    size_bytes=item.stat().st_size,
                )
            )
        except OSError as e:
            logger.warning("cannot inspect %s: %s", item.name, e)
            report.failed.append((item, str(e)))

    logger.info("planned %d moves, skipped %d", len(report.moves), len(report.skipped))
    return report


def apply(report: OrganizeReport) -> OrganizeReport:
    """Execute a plan produced by plan().

    A file that cannot be moved is recorded and the run continues, so one
    locked file does not cancel hundreds of valid moves.
    """
    executed = OrganizeReport(dry_run=False, skipped=report.skipped)

    for move in report.moves:
        try:
            move.destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(move.source), str(move.destination))
            executed.moves.append(move)
            logger.debug("moved %s -> %s", move.source.name, move.destination)
        except OSError as e:
            logger.error("failed to move %s: %s", move.source.name, e)
            executed.failed.append((move.source, str(e)))

    logger.info("moved %d files, %d failed", len(executed.moves), len(executed.failed))
    return executed


def organize(source: Path, config: OrganizerConfig, dry_run: bool = True) -> OrganizeReport:
    """Plan the moves, and carry them out when dry_run is False."""
    report = plan(source, config)
    if dry_run:
        return report
    return apply(report)
