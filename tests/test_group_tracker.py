import datetime, subprocess, sys

import openpyxl

from conftest import SCRIPTS

ROWS = [
    # Date, Company, Title, Source, URL, Location, Mode, Match, Resume, Letter, Status, Notes, ATS
    (datetime.datetime(2026, 11, 1), "Acme", "Dev", "SEEK", "https://seek.com.au/job/1", "Melbourne", "Hybrid", 80, "fullstack", "yes", "Submitted", "", 75),
    ("2026-11-20", "Beta", "Dev", "LinkedIn", "https://linkedin.com/jobs/2", "Melbourne", "Remote", 70, "frontend", "no", "Submitted", "", 60),
    (46000, "Gamma", "Dev", "SEEK", "not a url", "Melbourne", "On-site", 60, "fullstack", "no", "Ready (not submitted)", "", None),
    ("2026-11-10", "Delta", "Dev", "SEEK", "", "Melbourne", "Hybrid", 50, "", "", "Needs user input", "", None),
    ("2026-11-11", "Eps", "Dev", "SEEK", "", "Melbourne", "Hybrid", 50, "", "", "Weird status", "", None),
    ("2026-11-12", "Zeta", "Dev", "SEEK", "", "Melbourne", "Hybrid", 50, "", "", "Skipped", "", None),
    ("2026-11-13", "Eta", "Dev", "SEEK", "", "Melbourne", "Hybrid", 50, "", "", "Interview", "", None),
    ("2026-11-14", "Theta", "Dev", "SEEK", "", "Melbourne", "Hybrid", 50, "", "", "Rejected", "", None),
]
GROUPS = ["Submitted", "Needs User Input", "Ready (Not Submitted)", "Skipped", "Interviews & Outcomes"]


def fill(path, rows=ROWS):
    wb = openpyxl.load_workbook(path)
    ws = wb["Applications"]
    for i, r in enumerate(rows, 2):
        for j, v in enumerate(r, 1):
            ws.cell(i, j, v)
    wb.save(path)


def run(path):
    return subprocess.run([sys.executable, str(SCRIPTS / "group_tracker.py"), str(path)], capture_output=True, text=True)


def col(ws, c):
    return [ws.cell(r, c).value for r in range(2, ws.max_row + 1)]


def test_groups_rows_by_status(tracker):
    fill(tracker)
    r = run(tracker)
    assert r.returncode == 0, r.stderr
    assert "total 8" in r.stdout
    wb = openpyxl.load_workbook(tracker)
    assert wb.sheetnames == ["Summary", "Applications"] + GROUPS
    assert col(wb["Submitted"], 2) == ["Beta", "Acme"]  # newest first
    assert col(wb["Ready (Not Submitted)"], 2) == ["Gamma"]
    # unknown statuses land in Needs User Input
    assert set(col(wb["Needs User Input"], 2)) == {"Delta", "Eps"}
    assert col(wb["Skipped"], 2) == ["Zeta"]
    assert col(wb["Interviews & Outcomes"], 2) == ["Theta", "Eta"]


def test_dates_normalised_and_links(tracker):
    fill(tracker)
    run(tracker)
    wb = openpyxl.load_workbook(tracker)
    sub = wb["Submitted"]
    assert col(sub, 1) == ["2026-11-20", "2026-11-01"]
    assert sub.cell(2, 5).hyperlink.target == "https://linkedin.com/jobs/2"
    ready = wb["Ready (Not Submitted)"]
    assert ready.cell(2, 1).value == "2025-12-09"  # Excel serial 46000
    assert ready.cell(2, 5).hyperlink is None


def test_summary_formulas_and_rerun_is_idempotent(tracker):
    fill(tracker)
    run(tracker)
    r = run(tracker)
    assert r.returncode == 0, r.stderr
    wb = openpyxl.load_workbook(tracker)
    assert wb.sheetnames == ["Summary", "Applications"] + GROUPS
    s = wb["Summary"]
    labels = {s.cell(r, 1).value: s.cell(r, 2).value for r in range(12, 17)}
    assert labels["Submitted"] == '=COUNTIF(Applications!K2:K2000,"Submitted")'
    assert labels["Interviews & Outcomes"].count("COUNTIF") == 4
    assert wb["Applications"].freeze_panes == "A2"


def test_empty_template(tracker):
    r = run(tracker)
    assert r.returncode == 0, r.stderr
    assert "total 0" in r.stdout
    wb = openpyxl.load_workbook(tracker)
    assert all(wb[g].max_row == 1 for g in GROUPS)
