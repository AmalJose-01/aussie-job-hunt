# Aussie Job Hunt

A [Claude Code](https://claude.com/claude-code) plugin for job hunting in Australia. Claude searches SEEK and LinkedIn, reads and scores each job against your profile, writes Australian-standard resumes and cover letters, helps you apply, and logs every application in an Excel tracker.

## What it does

- **Search:** SEEK and LinkedIn, by your queries and locations, including remote roles.
- **Score:** every job 0–100 from its full description: skills, seniority, location, eligibility and salary. You get a shortlist with honest gaps.
- **Check eligibility:** citizenship, PR and clearance requirements, "remote but must live in…" rules, and Victorian Public Service ongoing roles.
- **Write in the Australian style:** Australian spelling, STAR achievements, no hype, key selection criteria, two-page resumes with key points only.
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

Build a resume yourself:

```
python3 skills/aussie-job-hunt/scripts/build_docs.py resume ~/Documents/job-hunt/profile.json --variant fullstack --out ~/Documents/job-hunt
```

## Privacy and security

- **Your data stays on your computer.** Your profile, resumes, cover letters and tracker live only in your workspace folder. The plugin has no server, no account and no database, so there's nothing to log in to and nothing that stores other people's data.
- **Nothing personal goes in this repo.** `.gitignore` blocks profiles, resumes, letters and trackers. Keep your workspace outside any repo you push.
- **No passwords, OTPs or ID numbers.** Claude never creates accounts and never types passwords, one-time codes (SMS or email OTPs) or ID numbers. When a site needs a login or verification code, you enter it yourself.
- **You approve outward actions.** Claude asks before sending messages or emails, accepting terms, or submitting applications, unless you've explicitly turned on automatic applying with clear rules.
- **Protect your device.** Turn on full-disk encryption (FileVault on macOS, BitLocker on Windows) and a screen lock, because your workspace holds personal information.

## Honesty rules

The skill never invents skills, metrics or experience. It only uses what's in your profile, and it states real gaps plainly in cover letters. Australian employers check claims, and this keeps you safe.

## Licence

MIT. See [LICENSE](LICENSE).
