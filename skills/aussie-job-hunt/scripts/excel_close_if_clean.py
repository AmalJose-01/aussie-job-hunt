#!/usr/bin/env python3
"""Close the tracker in Excel only if the open copy's Applications sheet matches the file on disk.

Usage: excel_close_if_clean.py <path to Job_Applications_Tracker.xlsx>   (macOS + Microsoft Excel)
Exit 0 = tracker not open, or open with no real edits and now closed (safe to write).
Exit 2 = real unsaved edits; ask the user to save and close it first.
Excel marks the workbook unsaved just from recalculating TODAY(), so compare content instead of trusting `saved`.
"""
import subprocess, sys, openpyxl

import os
PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("JOB_HUNT_DIR", os.path.expanduser("~/Documents/job-hunt")), "Job_Applications_Tracker.xlsx")
NAME = os.path.basename(PATH)

def osa(script):
    return subprocess.run(["osascript", "-e", script], capture_output=True, text=True)

open_books = osa('tell application "Microsoft Excel" to get name of every workbook').stdout
if NAME not in open_books:
    sys.exit(0)

ws = openpyxl.load_workbook(PATH, read_only=True)["Applications"]
disk = [f"{r[1] or ''}|{r[2] or ''}|{r[10] or ''}|{len(str(r[11] or ''))}" for r in ws.iter_rows(min_row=2, values_only=True) if r[1]]
n = len(disk) + 1
res = osa(f'''tell application "Microsoft Excel"
set ws to worksheet "Applications" of workbook "{NAME}"
set out to ""
repeat with r from 2 to {n + 5}
set b to value of range ("B" & r) of ws
if b is not "" then set out to out & b & "|" & (value of range ("C" & r) of ws) & "|" & (value of range ("K" & r) of ws) & "|" & (length of ((value of range ("L" & r) of ws) as text)) & linefeed
end repeat
return out
end tell''')
excel = [l for l in res.stdout.strip("\n").split("\n") if l]
if res.returncode != 0 or excel != disk:
    print("Open tracker differs from disk (real unsaved edits) - ask the user to save and close it.")
    sys.exit(2)
osa(f'tell application "Microsoft Excel" to close workbook "{NAME}" saving no')
print("closed (no real changes)")
