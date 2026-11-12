#!/usr/bin/env python3
"""Rebuild the per-status sheets in the job tracker from the master "Applications" sheet.

"Applications" stays the master log (always append new rows there). This script
regenerates one sheet per status group, newest first, and refreshes Summary counts.
Run after every tracker change:  python3 group_tracker.py <path to Job_Applications_Tracker.xlsx>
"""
import sys
from copy import copy
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

import os
PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("JOB_HUNT_DIR", os.path.expanduser("~/Documents/job-hunt")), "Job_Applications_Tracker.xlsx")

# sheet name -> (statuses, tab colour)
GROUPS = [
    ("Submitted", ["Submitted"], "2E7D32"),
    ("Needs User Input", ["Needs user input"], "E65100"),
    ("Ready (Not Submitted)", ["Ready (not submitted)"], "F9A825"),
    ("Skipped", ["Skipped"], "757575"),
    ("Interviews & Outcomes", ["Interview", "Offer", "Rejected", "Unconfirmed"], "1565C0"),
]
STATUS_COL = 11  # K
LAST = 2000

wb = openpyxl.load_workbook(PATH)
src = wb["Applications"]
header = [c for c in src[1]]
widths = {k: v.width for k, v in src.column_dimensions.items()}
rows = [r for r in src.iter_rows(min_row=2) if any(c.value not in (None, "") for c in r)]

# master sheet tidy-up: header frozen, filter over every row
src.freeze_panes = "A2"
src.auto_filter.ref = f"A1:L{src.max_row}"
src.sheet_properties.tabColor = "1F4E78"

import datetime as _dt
def datekey(v):
    """Dates appear as datetime, Excel serial numbers or 'YYYY-MM-DD' text; normalise to ISO text."""
    if isinstance(v, (_dt.datetime, _dt.date)):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, (int, float)):
        return (_dt.date(1899, 12, 30) + _dt.timedelta(days=int(v))).isoformat()
    return str(v or "")[:10]

def known(status):
    return any(status in g[1] for g in GROUPS)

for name, statuses, colour in GROUPS:
    if name in wb.sheetnames:
        del wb[name]
    ws = wb.create_sheet(name)
    ws.sheet_properties.tabColor = colour
    for i, h in enumerate(header, 1):
        c = ws.cell(1, i, h.value)
        c.font, c.fill, c.alignment, c.border = copy(h.font), copy(h.fill), copy(h.alignment), copy(h.border)
    picked = [r for r in rows if (r[STATUS_COL - 1].value or "").strip() in statuses]
    if name == "Needs User Input":  # also catch any status not covered by a group
        picked += [r for r in rows if not known((r[STATUS_COL - 1].value or "").strip())]
    picked.sort(key=lambda r: datekey(r[0].value), reverse=True)
    for ri, r in enumerate(picked, 2):
        for ci, c in enumerate(r, 1):
            n = ws.cell(ri, ci, datekey(c.value) if ci == 1 else c.value)
            if c.has_style:
                n.font, n.alignment, n.number_format = copy(c.font), copy(c.alignment), c.number_format
            tgt = c.hyperlink.target if c.hyperlink else None
            if tgt and not any(ch.isspace() for ch in tgt):
                n.hyperlink = tgt
            elif ci == 5 and isinstance(c.value, str) and c.value.startswith("http") and not any(ch.isspace() for ch in c.value.strip()):
                n.hyperlink = c.value
                n.font = Font(color="0563C1", underline="single")
    for k, w in widths.items():
        ws.column_dimensions[k].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:L{max(2, len(picked) + 1)}"

# Summary: counts per group (live formulas on the master sheet)
s = wb["Summary"]
s.sheet_properties.tabColor = "6A1B9A"
start = 11
s.cell(start, 1, "By sheet").font = Font(bold=True)
for i, (name, statuses, _) in enumerate(GROUPS, start + 1):
    f = "+".join(f'COUNTIF(Applications!K2:K{LAST},"{st}")' for st in statuses)
    s.cell(i, 1, name)
    s.cell(i, 2, "=" + f)

# order: Summary, Applications (All), then status sheets
order = ["Summary", "Applications"] + [g[0] for g in GROUPS]
wb._sheets = [wb[n] for n in order] + [x for x in wb._sheets if x.title not in order]
wb.active = 0
wb.save(PATH)
print({g[0]: sum(1 for r in rows if (r[STATUS_COL - 1].value or "").strip() in g[1]) for g in GROUPS}, "total", len(rows))
