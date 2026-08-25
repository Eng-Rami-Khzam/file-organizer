"""Configuration and result models."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class DateGrouping(str, Enum):
    """How files are grouped into date sub-folders."""

    NONE = "none"
    YEAR = "year"
    MONTH = "month"


DEFAULT_CATEGORIES: dict[str, list[str]] = {
    "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".heic"],
    "documents": [".pdf", ".doc", ".docx", ".txt", ".md", ".odt", ".rtf"],
    "spreadsheets": [".xls", ".xlsx", ".csv", ".ods"],
    "presentations": [".ppt", ".pptx", ".odp"],
    "video": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".webm"],
    "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
    "archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "code": [".py", ".js", ".ts", ".java", ".c", ".cpp", ".go", ".rs", ".html", ".css"],
    "installers": [".exe", ".msi", ".dmg", ".deb", ".rpm", ".apk"],
}


class OrganizerConfig(BaseModel):
    """Settings that control how a folder is organized."""

    model_config = ConfigDict(extra="forbid")

    categories: dict[str, list[str]] = Field(default_factory=lambda: dict(DEFAULT_CATEGORIES))
    other_folder: str = Field(default="other", min_length=1)
    date_grouping: DateGrouping = DateGrouping.MONTH
    skip_hidden: bool = True
    min_size_bytes: int = Field(default=0, ge=0)

    def category_for(self, suffix: str) -> str:
        """Return the folder name that a given file extension belongs to."""
        suffix = suffix.lower()
        for category, extensions in self.categories.items():
            if suffix in extensions:
                return category
        return self.other_folder


class PlannedMove(BaseModel):
    """A single move the organizer intends to perform."""

    model_config = ConfigDict(extra="forbid")

    source: Path
    destination: Path
    # Stored explicitly rather than derived from the path, because the
    # destination layout changes with the date-grouping setting.
    category: str
    size_bytes: int = Field(ge=0)


class OrganizeReport(BaseModel):
    """Outcome of a planning or execution run."""

    model_config = ConfigDict(extra="forbid")

    moves: list[PlannedMove] = Field(default_factory=list)
    skipped: list[Path] = Field(default_factory=list)
    failed: list[tuple[Path, str]] = Field(default_factory=list)
    dry_run: bool = True

    @property
    def total_bytes(self) -> int:
        return sum(move.size_bytes for move in self.moves)

    @property
    def counts_by_category(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for move in self.moves:
            counts[move.category] = counts.get(move.category, 0) + 1
        return counts
