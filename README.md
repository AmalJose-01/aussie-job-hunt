# Aussie Job Hunt

A [Claude Code](https://claude.com/claude-code) plugin for job hunting in Australia. Claude searches SEEK and LinkedIn, reads and scores each job against your profile, writes Australian-standard resumes and cover letters, helps you apply, and logs every application in an Excel tracker.

## What it does

- **Search:** SEEK and LinkedIn for the job types and locations you choose (e.g. iOS, React, full stack or analyst roles in Ballarat, Melbourne or remote). On first run Claude asks for your roles, locations, work mode, seniority and pay, and saves them to `profile.json`; say "change my job search" to update them.
- **Score:** every job 0–100 from its full description: skills, seniority, location, eligibility and salary. You get a shortlist with honest gaps.
- **Check eligibility:** citizenship, PR and clearance requirements, "remote but must live in…" rules, and Victorian Public Service ongoing roles.
- **Clean, consistent documents:** resumes and cover letters share one look (Calibri, navy name and section headings with a rule, grey contact line, compact bullets), built as .docx with no dependencies.
- **Write in the Australian style:** Australian spelling, STAR achievements, no hype, key selection criteria, two-page resumes with key points only.
- **ATS check:** an ATS-style keyword score (0–100) for your resume against each job ad, like Jobscan. It lists matched keywords, true keywords you should add, honest gaps you should leave out, and format problems.
- **Build documents:** resumes and cover letters as Word files from your `profile.json` (no extra Python packages needed).
- **Apply in your browser:** through Claude in Chrome. Claude stops for logins, declarations and anything your profile doesn't answer.
- **Track:** an Excel tracker with separate sheets for Submitted, Needs User Input, Ready, Skipped and Interviews & Outcomes.

## Install

In Claude Code:

```
/plugin marketplace add AmalJose-01/aussie-job-hunt
/plugin install aussie-job-hunt@aussie-job-hunt
```

You also need:
- **Claude in Chrome** (the browser extension) to search and apply.
- **Python 3**, plus `pip3 install --user openpyxl` for the tracker.
- **Microsoft Word on macOS** (optional) to export PDFs automatically.

## Set up your profile

1. Create your workspace folder: `mkdir -p ~/Documents/job-hunt` (or set `JOB_HUNT_DIR` to a folder of your choice).
2. Copy `examples/profile.example.json` to `~/Documents/job-hunt/profile.json` and fill in **your real details only**: experience, projects, skills, education and resume variants.
3. Fill in `never_claim` with skills you don't have. Claude will never put them in a resume, letter or form.
4. Ask Claude: "find jobs", "apply to this job <link>" or "build my resume".

Check a resume against a job ad (save the ad text to `jd.txt` first):

```
python3 skills/aussie-job-hunt/scripts/ats_score.py ~/Documents/job-hunt/Alex_Citizen_fullstack_Resume.docx ~/Documents/job-hunt/jd.txt "Full Stack Developer" --profile ~/Documents/job-hunt/profile.json
```

Build a resume yourself:

```
python3 skills/aussie-job-hunt/scripts/build_docs.py resume ~/Documents/job-hunt/profile.json --variant fullstack --out ~/Documents/job-hunt
```

## How the ATS score works

Most employer systems (PageUp, Workday, SuccessFactors) don't show you a score. They store your resume as text, and recruiters filter or rank by the ad's keywords. The score here imitates that:

| Part | Points |
|---|---|
| Hard skills in the ad (required ones count double) | 60 |
| Exact job title in your resume | 10 |
| Soft skills the ad asks for | 10 |
| Years of experience | 10 |
| Format: contact details, headings, no tables or images, dates | 10 |

It works for any profession. The hard skills come from three places:

1. **A built-in list for the ad's field.** There are lists for software and nursing roles, and the field is picked from the ad's wording. Any other field (trades, accounting, teaching, retail…) uses "general", which has no built-in list.
2. **Your own skills.** Every item in `profile.json` → `skills` that the ad mentions counts, plus any extra terms you list in `ats.hard_skills`.
3. **Keywords from the ad itself.** Phrases from the ad's bullet points, repeated phrases, acronyms (AHPRA, EWP, NDIS) and names (Xero, Excel). These count half as much as listed skills, so one odd phrase can't swing the score.

You can tune it in `profile.json`:

```json
"ats": {
  "field": "nursing",
  "hard_skills": ["Medication administration", "Wound care"],
  "core_skills": ["Communication", "Infection control"],
  "ignore_keywords": ["Medical Ward"]
}
```

`field` is `auto` (the default), `software`, `nursing` or `general`; `--field` on the command line overrides it. `hard_skills` is a list of phrases, or an object mapping a skill name to a regex. `core_skills` replaces the field's list of basic skills every resume should show. `ignore_keywords` drops ad keywords that aren't really skills.

An ATS matches words, not meaning. If you build React apps, also write "React (SPA)". If you design SQL Server databases, write "relational database design". Only add what's true. Skills on your `never_claim` list are always reported as honest gaps, never as keywords to add.

### Running it

Save the full job ad as a text file, then run:

```bash
python3 skills/aussie-job-hunt/scripts/ats_score.py <resume.docx|pdf> jd.txt "Job Title" --profile profile.json
```

Add `--json` for machine-readable output. The skill runs this for you after building each resume and records the score in the tracker's **ATS Score** column.

### Example output

```text
ATS score: 82/100  (field: software)
  hard skills (60)   42.0
  job title (10)     10
  soft skills (10)   10.0
  experience (10)    10
  format (10)        10.0
Matched: Full stack, Azure, Agile, Testing, Integrations, Architecture
Missing, can add if true: Kubernetes
Missing, honest gap (never claim): AWS (required)
Soft skills missing: -
Format issues: none
Exact job title in resume: yes
Keywords taken from the ad: software developer
Core software skills missing: none
```

### What each line means

| Line | What it tells you | What to do |
|---|---|---|
| **ATS score** and the five parts | The total out of 100 and how it splits across the table above. | Aim for 75 or more. The hard-skills part moves the score most. |
| **Matched** | Skills from the ad that your resume already names. | Nothing; keep them. |
| **Missing, can add if true** | Skills in the ad that your resume doesn't mention. "(required)" means the ad lists it before any "nice to have" section, so it counts double. | Add the ad's exact word to your summary, skills or a bullet, but only if it's true. Then rebuild and re-check. |
| **Missing, honest gap (never claim)** | Missing skills on your `never_claim` list. | Never add these. Mention the gap plainly in the cover letter with how you'd close it. |
| **Soft skills missing** | Soft skills the ad asks for (communication, stakeholder engagement, ownership and so on) that your resume doesn't show. | Add them to the summary where your profile supports them. |
| **Format issues** | Parsing problems: missing email or phone, missing standard headings, no dates, tables or images. | Fix them; an ATS may drop content it can't read. |
| **Exact job title in resume** | Whether the ad's title appears word for word (usually in the headline). | Use the ad's title in the headline when it fairly describes you. |
| **Keywords taken from the ad** | Phrases the script pulled from the ad itself, on top of the built-in and profile skill lists. They appear in Matched or Missing like any other skill. | If one isn't a real skill, add it to `ats.ignore_keywords`. |
| **Core *field* skills missing** | Basic skills every resume in that field should show, whatever the ad says. Software: problem solving, communication, teamwork, attention to detail, debugging/troubleshooting, testing, Agile, Git and documentation. Nursing: patient assessment, medication safety, infection control, documentation, communication, teamwork, person-centred care, escalation and time management. Other fields: communication, teamwork, problem solving, attention to detail and time management. | Add them in plain words where true. |

### Reading the score

- **75–100:** a strong keyword match; apply.
- **60–74:** add any true missing keywords, then decide. Honest gaps stay out.
- **Below 60:** the ad's core skills probably aren't yours. Consider skipping, or explain the gaps in the cover letter.

The ATS score measures keyword coverage only. It is separate from the 0–100 fit score the skill gives each job (skills, seniority, location, visa and salary). It's an estimate like Jobscan, not any employer's real score.

## Privacy and security

- **Your data stays on your computer.** Your profile, resumes, cover letters and tracker live only in your workspace folder. The plugin has no server, no account and no database, so there's nothing to log in to and nothing that stores other people's data.
- **Nothing personal goes in this repo.** `.gitignore` blocks profiles, resumes, letters and trackers. Keep your workspace outside any repo you push.
- **No passwords, OTPs or ID numbers.** Claude never creates accounts and never types passwords, one-time codes (SMS or email OTPs) or ID numbers. When a site needs a login or verification code, you enter it yourself.
- **You approve outward actions.** Claude asks before sending messages or emails, accepting terms, or submitting applications, unless you've explicitly turned on automatic applying with clear rules.
- **Protect your device.** Turn on full-disk encryption (FileVault on macOS, BitLocker on Windows) and a screen lock, because your workspace holds personal information.

## Honesty rules

The skill never invents skills, metrics or experience. It only uses what's in your profile, and it states real gaps plainly in cover letters. Australian employers check claims, and this keeps you safe.

## Running the tests

The tests use only the example profile, example letter and the template tracker, never your own data.

```
pip3 install -r requirements-dev.txt
python3 -m pytest -q tests
```

GitHub Actions runs them on every push to `main` and on every pull request. The Excel-closing script is macOS-only, so its tests use a fake `osascript`.

## Licence

MIT. See [LICENSE](LICENSE).
