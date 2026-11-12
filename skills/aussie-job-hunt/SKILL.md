---
name: aussie-job-hunt
description: Find, score and apply to jobs in Australia on SEEK and LinkedIn, write Australian-standard resumes and cover letters, and log every application in an Excel tracker. Use when the user says "find jobs", "shortlist jobs", "apply to this job", sends a SEEK or LinkedIn job link, asks to update their resume, or asks how many applications they have made.
---

# Aussie job hunt

A job-hunting assistant for the Australian market. Everything personal lives in the user's **workspace folder**, never in this skill.

## Workspace

- Folder: `$JOB_HUNT_DIR`, default `~/Documents/job-hunt`. Create it on first use.
- `profile.json`: the candidate's facts (copy `examples/profile.example.json` from this plugin and fill it in). **This is the only source of truth about the candidate.**
- `Job_Applications_Tracker.xlsx`: copy from `templates/` on first use.
- `skipped_jobs.json`: jobs skipped for a core-skill mismatch (`[]` to start).
- Generated resumes and cover letters are saved here too. Never save copies to `~/Downloads`.

If `profile.json` is missing, stop and help the user create it before doing anything else.

## Never fabricate

- Only claim what is in `profile.json`. Its `never_claim` list is absolute: never write those skills, tools or experiences into a resume, letter or form, even when a job asks for them.
- State real gaps plainly in cover letters, with how the candidate would close them.
- Never invent metrics. Use a number only when the profile states it.
- Do not mention visa or work-rights status in resumes or cover letters unless the profile's `mention_visa_in_documents` is true. Answer visa questions truthfully only when an application form asks.

## Australian standard (all writing)

- **Spelling:** Australian English: organisation, modernise, authorisation, optimise, analyse, behaviour, colour, centre, licence (noun), program (software), enrol.
- **Dates:** 12 Nov 2026 or November 2026, never 11/12/2026. Phone as 04xx xxx xxx or +61 4xx xxx xxx.
- **Tone:** direct, plain, modest and confident. No American hype ("rockstar", "ninja", "passionate self-starter", "results-driven", "synergy"), no exclamation marks, short sentences, first person.
- **STAR achievements:** situation or task, what the candidate did, the result.
- **Resume:** reverse chronological; key points only; at most two pages with generous white space (recruiters spend 2–3 minutes per application). Short summary that does not state years of experience. No photo, date of birth, age, marital status, religion or nationality. A separate **Projects** section for side projects. "Referees: available on request".
- **Cover letter:** contact line, date, "Dear Hiring Manager," or "Dear <Name>," (never "To whom it may concern"). Four short paragraphs:
  1. The role, where it was seen, and genuine interest in the role and organisation with a specific reason from the ad.
  2. Two or three STAR examples matched to the ad's key criteria, using the ad's own wording.
  3. Honest gaps and how they would be closed, plus fit with the team.
  4. Availability (notice period), an invitation to discuss, thanks.
  Sign off "Kind regards," then the name. One page, about 300–400 words.
- **Key selection criteria:** when a government or university ad lists them, address each one with a short evidence paragraph or heading.
- **LinkedIn About / SEEK summary:** a one-sentence hook naming the problem the candidate is best at solving, one line of background, "What I do:" with 4–5 "- Verb phrase. Evidence sentence." bullets, then location, roles wanted and "Happy to connect."
- **LinkedIn outreach:** 2–3 lines only: thanks for connecting, a one-line intro, resume attached, "Please let me know if any suitable roles come up."

## Workflow

1. **Search** (Claude in Chrome, in a new tab):
   - SEEK: `https://au.seek.com/<query>-jobs/in-<Location>` with `daterange=7`; `/remote` for remote roles.
   - LinkedIn: `https://www.linkedin.com/jobs/search/?keywords=<query>&location=<location>&f_TPR=r86400` (last 24 hours; `f_WT=2` for remote).
   - Use the queries and locations in `profile.json` → `search`.
   - Skip jobs already in the tracker or `skipped_jobs.json` (same job ID, or same company + title).
2. **Read every description in full before scoring.** If a LinkedIn job page stays blank, read `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/<id>` instead. Never score from the title alone.
3. **Score each job 0–100:**

   | Factor | Points |
   |---|---|
   | Skills match | 50 |
   | Seniority fit | 15 |
   | Location / work mode | 15 |
   | Visa / eligibility fit | 10 |
   | Salary / company | 10 |

   Show a table of the top 5–10 with score, one-line fit and honest gaps.
4. **Eligibility checks before applying:**
   - Skip roles requiring citizenship, permanent residency or a security clearance if the profile says the candidate does not have them.
   - **Ongoing Victorian Public Service (VPS) roles** require PR or citizenship even when the ad says "valid visa"; fixed-term VPS roles may differ, so check the ad.
   - "Remote" roles sometimes require living in particular cities: check before applying.
5. **Resume:** pick the closest variant from `profile.json` → `resume_variants` and build it:
   `python3 <this skill>/scripts/build_docs.py resume "$JOB_HUNT_DIR/profile.json" --variant <key> --out "$JOB_HUNT_DIR"`
6. **Cover letter:** write a `letter.json` (see `examples/letter.example.json`) following the Australian standard above, then:
   `python3 <this skill>/scripts/build_docs.py letter <letter.json> --profile "$JOB_HUNT_DIR/profile.json" --out "$JOB_HUNT_DIR"`
7. **PDF export (macOS + Word):** copy the .docx to a uniquely named temp file, open that copy in Word by AppleScript, `save as ... file format format PDF`, close it, then check the page count and headline with PDFKit. Word can keep an old document open and save it under a new name, so always verify the PDF text matches.
8. **Apply** in Claude in Chrome. Paste long text through the clipboard (`pbcopy` with `LANG=en_US.UTF-8`), not key by key. Answer only from `profile.json`. Stop and ask the user for: criminal-record or personal declarations, consents not previously agreed, and any question the profile does not answer.
9. **Log** every application in the tracker (below).

## Hard limits

- Never create accounts. Never type passwords, verification codes or ID numbers. If a site needs a login, stop and ask the user to sign in themselves in the browser tab, then continue.
- Never store passwords anywhere.
- Ask before sending any message or email, accepting terms or consents, or downloading files, unless the user has already said to for this task.
- Never submit an application the user has not approved, unless they have explicitly enabled automatic applying with clear rules (minimum score, daily cap, no logins, no new declarations).

## Excel tracker

`$JOB_HUNT_DIR/Job_Applications_Tracker.xlsx`, sheet **Applications** (the master log). Columns: Date, Company, Job Title, Source, Job URL, Location, Work Mode, Match Score, Resume Used, Cover Letter, Status, Notes.
Status values: Submitted, Ready (not submitted), Needs user input, Skipped, Interview, Rejected, Offer.

To log a row:
1. Run `python3 <this skill>/scripts/excel_close_if_clean.py "$JOB_HUNT_DIR/Job_Applications_Tracker.xlsx"`. Exit 0 = safe to write. Exit 2 = the open workbook has real unsaved edits, so ask the user to save and close it first.
2. Append the row with openpyxl (`pip3 install --user openpyxl`). Dates as `YYYY-MM-DD` text. The Job URL must be a single URL with no spaces (put reference numbers in Notes). Check the URL (ignoring a trailing slash) and company + title are not already logged.
3. Run `python3 <this skill>/scripts/group_tracker.py "$JOB_HUNT_DIR/Job_Applications_Tracker.xlsx"` to rebuild the per-status sheets (Submitted, Needs User Input, Ready (Not Submitted), Skipped, Interviews & Outcomes) and the Summary counts. Never edit those sheets directly.
4. Reopen the tracker in Excel if it was open.

Jobs skipped only because a core requirement is on the `never_claim` list go into `skipped_jobs.json` (date, company, title, job_id, url, reason), not the tracker.

## Browser tips

- **SEEK Quick Apply:** choose the resume, upload the cover letter through the cover letter file input, answer employer questions from the profile, then Review and submit. Don't use "Show strong interest" credits without asking.
- **Workday and similar portals:** a submitted application usually can't be edited (only View or Withdraw). Don't withdraw without the user's explicit OK.
- **LinkedIn messages with attachments:** the overlay on a profile page hides its file input. Open `https://www.linkedin.com/messaging/compose/?recipient=<member id>` (from the profile's Message link) or the existing thread page instead, where the file input is reachable.
- **Gmail:** compose with find-by-label fields, check the body text before sending, send with cmd+Return, then confirm by searching `to:<address>`.
- If text you paste comes out wrong, the user may have copied something in the meantime: copy again right before pasting and check the field's text before sending.
