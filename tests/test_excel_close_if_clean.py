"""excel_close_if_clean.py drives Excel via osascript (macOS only).

These tests put a fake `osascript` on PATH that answers from files, so the
compare-and-close logic runs anywhere.
"""
import os, stat, subprocess, sys

import openpyxl
import pytest

from conftest import SCRIPTS

FAKE = """#!/bin/sh
script="$2"
echo "$script" >> "$FAKE_DIR/calls.log"
case "$script" in
  *"name of every workbook"*) cat "$FAKE_DIR/open_books" ;;
  *"set out to"*) cat "$FAKE_DIR/excel_rows"; exit $(cat "$FAKE_DIR/rc" 2>/dev/null || echo 0) ;;
  *"close workbook"*) : ;;
esac
"""

ROWS = [("2026-11-01", "Acme", "Dev", None, None, None, None, None, None, None, "Submitted", "notes here", None),
        ("2026-11-02", "Beta", "QA", None, None, None, None, None, None, None, "Skipped", None, None)]
MATCHING = "Acme|Dev|Submitted|10\nBeta|QA|Skipped|0\n"


@pytest.fixture
def fake(tmp_path, tracker):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    exe = bindir / "osascript"
    exe.write_text(FAKE)
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    wb = openpyxl.load_workbook(tracker)
    for i, r in enumerate(ROWS, 2):
        for j, v in enumerate(r, 1):
            wb["Applications"].cell(i, j, v)
    wb.save(tracker)

    def run(open_books, excel_rows="", rc=0):
        (tmp_path / "open_books").write_text(open_books)
        (tmp_path / "excel_rows").write_text(excel_rows)
        (tmp_path / "rc").write_text(str(rc))
        env = dict(os.environ, PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}", FAKE_DIR=str(tmp_path))
        p = subprocess.run([sys.executable, str(SCRIPTS / "excel_close_if_clean.py"), str(tracker)],
                           capture_output=True, text=True, env=env)
        log = tmp_path / "calls.log"
        p.calls = log.read_text() if log.exists() else ""
        log.unlink(missing_ok=True)
        return p
    return run


def test_not_open_exits_zero(fake):
    r = fake("Other.xlsx")
    assert r.returncode == 0
    assert "close workbook" not in r.calls


def test_open_and_clean_closes(fake):
    r = fake("Job_Applications_Tracker.xlsx", MATCHING)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "closed (no real changes)" in r.stdout
    assert 'close workbook "Job_Applications_Tracker.xlsx" saving no' in r.calls


def test_unsaved_edits_exit_two(fake):
    r = fake("Job_Applications_Tracker.xlsx", "Acme|Dev|Interview|10\nBeta|QA|Skipped|0\n")
    assert r.returncode == 2
    assert "differs from disk" in r.stdout
    assert "close workbook" not in r.calls


def test_extra_row_in_excel_exit_two(fake):
    r = fake("Job_Applications_Tracker.xlsx", MATCHING + "Gamma|Dev|Submitted|0\n")
    assert r.returncode == 2


def test_osascript_error_exit_two(fake):
    r = fake("Job_Applications_Tracker.xlsx", MATCHING, rc=1)
    assert r.returncode == 2
