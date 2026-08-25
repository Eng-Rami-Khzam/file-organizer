"""File Organizer — tidy a messy folder by type and date."""

from .core import OrganizerError, apply, organize, plan
from .models import (
    DateGrouping,
    OrganizeReport,
    OrganizerConfig,
    PlannedMove,
)

__version__ = "1.0.0"

__all__ = [
    "DateGrouping",
    "OrganizeReport",
    "OrganizerConfig",
    "OrganizerError",
    "PlannedMove",
    "apply",
    "organize",
    "plan",
]
