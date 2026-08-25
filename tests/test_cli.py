"""Tests for the command-line interface."""

from __future__ import annotations

from pathlib import Path

import pytest

from organizer.cli import _human_size, _parse_size, build_parser, main


@pytest.mark.parametrize(
    "text, expected",
    [
        ("1024", 1024),
        ("1KB", 1024),
        ("10MB", 10 * 1024**2),
        ("1.5MB", int(1.5 * 1024**2)),
        ("2GB", 2 * 1024**3),
        ("500kb", 500 * 1024),
    ],
)
def test_parse_size(text: str, expected: int) -> None:
    assert _parse_size(text) == expected


def test_parse_size_rejects_garbage() -> None:
    with pytest.raises(Exception):
        _parse_size("abc")


@pytest.mark.parametrize(
    "num_bytes, expected",
    [
        (512, "512.0 B"),
        (1024, "1.0 KB"),
        (1024**2, "1.0 MB"),
    ],
)
def test_human_size(num_bytes: int, expected: str) -> None:
    assert _human_size(num_bytes) == expected


def test_parser_defaults_to_dry_run() -> None:
    args = build_parser().parse_args(["somefolder"])
    assert args.apply is False
    assert args.by_date == "month"


def test_main_dry_run_does_not_move(messy_folder: Path, capsys) -> None:
    exit_code = main([str(messy_folder), "--by-date", "none"])

    assert exit_code == 0
    assert (messy_folder / "vacation.jpg").exists()

    output = capsys.readouterr().out
    assert "PLAN (dry run)" in output
    assert "--apply" in output


def test_main_apply_moves(messy_folder: Path, capsys) -> None:
    exit_code = main([str(messy_folder), "--by-date", "none", "--apply"])

    assert exit_code == 0
    assert (messy_folder / "images" / "vacation.jpg").exists()
    assert "DONE" in capsys.readouterr().out


def test_main_missing_folder_returns_error(tmp_path: Path, capsys) -> None:
    exit_code = main([str(tmp_path / "nope")])

    assert exit_code == 1
    assert "Error" in capsys.readouterr().err
