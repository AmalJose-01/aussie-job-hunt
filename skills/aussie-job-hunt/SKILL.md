---
name: aussie-job-hunt
description: Find, score and apply to jobs in Australia on SEEK and LinkedIn for any role and location the user chooses (e.g. iOS, React, full stack, analyst), write Australian-standard resumes and cover letters, and log every application in an Excel tracker. Use when the user says "find jobs", "shortlist jobs", "apply to this job", sends a SEEK or LinkedIn job link, asks to update their resume, or asks how many applications they have made.
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

## Search setup (first run, and whenever the user asks to change it)

The skill works for any kind of job, not only software roles. Before the first search, ask the user these questions (one short message, skip any already answered in `profile.json` → `search`):

1. **Job types:** which roles to look for, e.g. iOS developer, React developer, full stack developer, data analyst, business analyst, nurse, accountant. Several are fine; ask which comes first.
2. **Locations:** suburbs, cities or states (e.g. Ballarat, Melbourne, All Victoria, Sydney), and whether to include **remote** roles anywhere in Australia. Ask if they are willing to relocate.
3. **Work mode:** on-site, hybrid, remote, or any.
4. **Seniority:** graduate/junior, mid, senior, or a range.
5. **Job type and pay (optional):** full time, part time, contract or casual; a minimum salary or rate.
6. **Exclude (optional):** words that rule a job out, e.g. "senior", "clearance", "PHP".

Save the answers to `profile.json` → `search` (see `examples/profile.example.json`):

- `roles`: each role with its `queries` (2–3 search phrases, e.g. "ios developer", "swift developer") and a `priority` (1 = apply first).
- `locations`: each with a `label`, its SEEK slug (`seek`, e.g. `in-Ballarat-Central-Highlands-VIC`, `in-Melbourne-VIC`, `in-All-Victoria-VIC`) and its LinkedIn text (`linkedin`, e.g. `Melbourne, Victoria, Australia`). If a SEEK slug is unknown, type the place into SEEK's location box and copy the slug from the results URL.
- `remote`, `willing_to_relocate`, `work_modes`, `seniority`, `employment_types`, `min_salary`, `exclude_keywords`, `days` (how recent; default 7).

Confirm the saved setup back to the user in a short table before searching. If the user asks for a one-off search ("find React jobs in Sydney"), use those values for this search only and don't overwrite the saved setup unless they say so.

## Never fabricate

- Only claim what is in `profile.json`. Its `never_claim` list is absolute: never write those skills, tools or experiences into a resume, letter or form, even when a job asks for them.
- State real gaps plainly in cover letters, with how the candidate would close them.
- Never invent metrics. Use a number only when the profile states it.
- Do not mention visa or work-rights status in resumes or cover letters unless the profile's `mention_visa_in_documents` is true. Answer visa questions truthfully only when an application form asks.

## Australian standard (all writing)

- **Spelling:** Australian English: organisation, modernise, authorisation, optimise, analyse, behaviour, colour, centre, licence (noun), program (software), enrol.
- **Dates:** 12 Nov 2026 or November 2026, never 11/12/2026. Phone as 04xx xxx xxx or +61 4xx xxx xxx.
- **Tone:** direct, plain, modest and confident. No American hype ("rockstar", "ninja", "passionate self-starter", "results-driven", "synergy"), no exclamation marks, short sentences, first person.
- **STAR achievements (cover letters):** situation or task, what the candidate did, the result.
- **Resume bullets:** one short keyword line each (about 8–15 words), no bold labels and no full sentences, so a recruiter can skim them and an ATS can match them. Leave white space between bullets.
- **ATS keywords (resume):** use the ad's exact words where they are true for the candidate. Name implied skills explicitly, e.g. "React (SPA)" for single-page apps, "relational database design" for SQL Server or MySQL work, "reporting queries", "Azure DevOps (Repos, Pipelines)". Put the soft skills ads ask for (communication, stakeholder engagement, ownership, continuous improvement) in the summary only when the profile supports them. An ATS matches words, not meaning.
- **Core skills (every resume):** for software roles, show problem solving, communication, teamwork, attention to detail, debugging/troubleshooting, testing, Agile, Git and documentation in plain words where true. `ats_score.py` lists any that are missing. For other professions, show that field's core skills the same way (for example data analysis, stakeholder reporting and Excel for analysts). Tailor the headline, summary, skills order and top bullets to each job; never send the same resume to every employer.
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

1. **Search** (Claude in Chrome, in a new tab), using `profile.json` → `search`. Run every query of every role, in role `priority` order, in every location:
   - SEEK: `https://au.seek.com/<query-with-dashes>-jobs/<location seek slug>?daterange=<days>`. For remote roles: `https://au.seek.com/<query>-jobs/in-All-Australia` with SEEK's Work arrangement filter set to Remote. Add SEEK's work type filter when `employment_types` is set.
   - LinkedIn: `https://www.linkedin.com/jobs/search/?keywords=<query>&location=<location linkedin text>&f_TPR=r<days × 86400>`; for remote add `f_WT=2` with `location=Australia`. LinkedIn often widens the location, so filter results by location yourself.
   - Drop results whose title matches `exclude_keywords` or is clearly outside `seniority`.
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

   Location / work mode: full marks for a saved location or remote (if `remote` is true), fewer for a place the user would relocate to, none for a work mode they ruled out. Seniority fit is measured against `search.seniority`. Salary below `min_salary` loses the salary points but is not a reason to skip on its own.

   Order the shortlist by role `priority`, then by score. Show a table of the top 5–10 with role, location, score, one-line fit and honest gaps.
4. **Eligibility checks before applying:**
   - Skip roles requiring citizenship, permanent residency or a security clearance if the profile says the candidate does not have them.
   - **Ongoing Victorian Public Service (VPS) roles** require PR or citizenship even when the ad says "valid visa"; fixed-term VPS roles may differ, so check the ad.
   - "Remote" roles sometimes require living in particular cities: check before applying.
5. **Resume:** pick the closest variant from `profile.json` → `resume_variants` (keep one variant per role in `search.roles`, e.g. `ios`, `react`, `analyst`) and build it:
   `python3 <this skill>/scripts/build_docs.py resume "$JOB_HUNT_DIR/profile.json" --variant <key> --out "$JOB_HUNT_DIR"`
   The layout is fixed: Calibri, name in navy, grey headline and contact line, uppercase navy section headings with a rule underneath, compact "•" bullets, 1.27 cm margins (cover letters use the same header). For a new job, add a variant with its own `headline`, `summary` and `skills_order`. Optional variant keys: `projects_first: true` puts Projects above Experience when a side project is the best evidence for the role (keep Experience first otherwise), and `project_bullets: {"<project name>": [...]}` swaps in job-specific bullets for a project.
5b. **ATS check:** save the full job description to `$JOB_HUNT_DIR/jd.txt`, then run
   `python3 <this skill>/scripts/ats_score.py <resume.docx> "$JOB_HUNT_DIR/jd.txt" "<Job Title>" --profile "$JOB_HUNT_DIR/profile.json"`
   It gives an ATS-style keyword score out of 100 (hard skills 60, with required skills counting double those after "nice to have"/"desirable"; exact job title 10; soft skills 10; experience years 10; format 10) and lists matched keywords, keywords to add if true, honest gaps (from `never_claim`) and format problems. Show the user the score and missing keywords. If true keywords are missing, add them to `profile.json` (skills, summary or bullets) and rebuild; if the ad's key skills are honest gaps, address them in the cover letter instead. Never add a `never_claim` skill to raise the score. Record the score in the tracker's **ATS Score** column. This is an estimate like Jobscan, not any employer's real score; it differs from the 0–100 fit score in step 3.
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

`$JOB_HUNT_DIR/Job_Applications_Tracker.xlsx`, sheet **Applications** (the master log). Columns: Date, Company, Job Title, Source, Job URL, Location, Work Mode, Match Score, Resume Used, Cover Letter, Status, Notes, ATS Score (column M; add the header if an older tracker lacks it).
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
