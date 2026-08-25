"""Tests for the organizing logic."""

from __future__ import annotations

from pathlib import Path

import pytest

from organizer.core import OrganizerError, organize, plan
from organizer.models import DateGrouping, OrganizerConfig

from .conftest import set_mtime


# --- Categorization -----------------------------------------------------

@pytest.mark.parametrize(
    "suffix, expected",
    [
        (".jpg", "images"),
        (".JPG", "images"),          # case does not matter
        (".pdf", "documents"),
        (".xlsx", "spreadsheets"),
        (".mp3", "audio"),
        (".mp4", "video"),
        (".zip", "archives"),
        (".py", "code"),
        (".xyz", "other"),           # unknown extension
        ("", "other"),               # no extension
    ],
)
def test_category_for(config: OrganizerConfig, suffix: str, expected: str) -> None:
    assert config.category_for(suffix) == expected


# --- Planning touches nothing -------------------------------------------

def test_plan_does_not_move_anything(messy_folder: Path, config: OrganizerConfig) -> None:
    before = sorted(p.name for p in messy_folder.iterdir())

    report = plan(messy_folder, config)

    after = sorted(p.name for p in messy_folder.iterdir())
    assert before == after
    assert report.dry_run is True
    assert len(report.moves) == 8


def test_dry_run_leaves_folder_untouched(messy_folder: Path, config: OrganizerConfig) -> None:
    organize(messy_folder, config, dry_run=True)
    assert (messy_folder / "vacation.jpg").exists()
    assert not (messy_folder / "images").exists()


# --- Execution ----------------------------------------------------------

def test_apply_moves_files(messy_folder: Path, flat_config: OrganizerConfig) -> None:
    report = organize(messy_folder, flat_config, dry_run=False)

    assert report.dry_run is False
    assert (messy_folder / "images" / "vacation.jpg").exists()
    assert (messy_folder / "documents" / "invoice.pdf").exists()
    assert (messy_folder / "other" / "mystery.xyz").exists()
    assert not (messy_folder / "vacation.jpg").exists()


def test_skips_directories_and_hidden(messy_folder: Path, flat_config: OrganizerConfig) -> None:
    organize(messy_folder, flat_config, dry_run=False)

    assert (messy_folder / "existing_folder").is_dir()
    assert (messy_folder / ".hidden_file").exists()


def test_include_hidden_option(messy_folder: Path) -> None:
    config = OrganizerConfig(date_grouping=DateGrouping.NONE, skip_hidden=False)
    organize(messy_folder, config, dry_run=False)

    assert not (messy_folder / ".hidden_file").exists()
    assert (messy_folder / "other" / ".hidden_file").exists()


# --- Date grouping ------------------------------------------------------

def test_groups_by_month(tmp_path: Path, config: OrganizerConfig) -> None:
    old = tmp_path / "old.jpg"
    new = tmp_path / "new.jpg"
    old.write_text("x")
    new.write_text("y")
    set_mtime(old, 2023, 5)
    set_mtime(new, 2026, 8)

    organize(tmp_path, config, dry_run=False)

    assert (tmp_path / "images" / "2023-05" / "old.jpg").exists()
    assert (tmp_path / "images" / "2026-08" / "new.jpg").exists()


def test_groups_by_year(tmp_path: Path) -> None:
    config = OrganizerConfig(date_grouping=DateGrouping.YEAR)
    photo = tmp_path / "photo.jpg"
    photo.write_text("x")
    set_mtime(photo, 2024, 3)

    organize(tmp_path, config, dry_run=False)

    assert (tmp_path / "images" / "2024" / "photo.jpg").exists()


# --- Name collisions ----------------------------------------------------

def test_name_collision_gets_suffix(tmp_path: Path, flat_config: OrganizerConfig) -> None:
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "photo.jpg").write_text("existing")
    (tmp_path / "photo.jpg").write_text("new")

    organize(tmp_path, flat_config, dry_run=False)

    assert (tmp_path / "images" / "photo.jpg").read_text() == "existing"
    assert (tmp_path / "images" / "photo_1.jpg").read_text() == "new"


# --- Size filter --------------------------------------------------------

def test_min_size_filter(tmp_path: Path) -> None:
    config = OrganizerConfig(date_grouping=DateGrouping.NONE, min_size_bytes=100)
    (tmp_path / "tiny.jpg").write_text("x")
    (tmp_path / "big.jpg").write_text("x" * 200)

    report = organize(tmp_path, config, dry_run=False)

    assert len(report.moves) == 1
    assert (tmp_path / "tiny.jpg").exists()
    assert (tmp_path / "images" / "big.jpg").exists()


# --- Errors -------------------------------------------------------------

def test_missing_folder_raises(tmp_path: Path, config: OrganizerConfig) -> None:
    with pytest.raises(OrganizerError, match="not found"):
        plan(tmp_path / "does_not_exist", config)


def test_file_instead_of_folder_raises(tmp_path: Path, config: OrganizerConfig) -> None:
    a_file = tmp_path / "a.txt"
    a_file.write_text("x")

    with pytest.raises(OrganizerError, match="not a folder"):
        plan(a_file, config)


# --- Report -------------------------------------------------------------

def test_report_counts(messy_folder: Path, flat_config: OrganizerConfig) -> None:
    report = plan(messy_folder, flat_config)
    counts = report.counts_by_category

    assert counts["images"] == 1
    assert counts["documents"] == 1
    assert counts["other"] == 1
    assert report.total_bytes > 0


def test_running_twice_is_safe(messy_folder: Path, flat_config: OrganizerConfig) -> None:
    """A second run must not re-sort what the first run already placed."""
    organize(messy_folder, flat_config, dry_run=False)
    second = organize(messy_folder, flat_config, dry_run=False)

    assert second.moves == []
