"""Shared fixtures."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from organizer.models import DateGrouping, OrganizerConfig


@pytest.fixture
def config() -> OrganizerConfig:
    """Default settings."""
    return OrganizerConfig()


@pytest.fixture
def flat_config() -> OrganizerConfig:
    """No date grouping - simpler paths to assert on."""
    return OrganizerConfig(date_grouping=DateGrouping.NONE)


@pytest.fixture
def messy_folder(tmp_path: Path) -> Path:
    """A cluttered folder that mimics a real Downloads directory."""
    files = [
        "vacation.jpg",
        "invoice.pdf",
        "budget.xlsx",
        "song.mp3",
        "movie.mp4",
        "archive.zip",
        "script.py",
        "mystery.xyz",
    ]
    for name in files:
        (tmp_path / name).write_text("content")

    (tmp_path / "existing_folder").mkdir()
    (tmp_path / ".hidden_file").write_text("secret")

    return tmp_path


def set_mtime(file: Path, year: int, month: int) -> None:
    """Force a file's modification time, to test date grouping."""
    timestamp = time.mktime((year, month, 15, 12, 0, 0, 0, 0, -1))
    os.utime(file, (timestamp, timestamp))
