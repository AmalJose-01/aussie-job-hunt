#!/usr/bin/env python3
"""ATS-style match score: resume (.docx or .pdf) vs job description (text file).

Usage: python3 ats_score.py <resume.docx|pdf> <job_description.txt> ["Job Title"] [--profile profile.json] [--json]

With --profile, missing skills on the profile's never_claim list are reported as
honest gaps (never add them) instead of keywords to add.

Works like Jobscan-type checkers used by recruiters: keyword coverage (hard skills
weighted by required vs nice-to-have), job-title match, soft skills, experience
years and parse/format checks. It is an estimate, not any employer's real score.
"""
import json, re, subprocess, sys, zipfile

# canonical skill -> regex (case-insensitive). Order doesn't matter.
HARD = {
    "C#": r"c#|c sharp", ".NET": r"\.net\b|dotnet", "ASP.NET Core": r"asp\.net( core)?",
    "Web API": r"web ?api", "REST APIs": r"\brest(ful)?\b", "APIs": r"\bapis?\b",
    "Backend services": r"back-?end", "Front-end": r"front-?end", "Full stack": r"full[- ]?stack",
    "React": r"\breact(\.js|js)?\b(?! native)", "React Native": r"react native", "Angular": r"\bangular",
    "Vue": r"\bvue", "Next.js": r"next\.?js", "SPA": r"\bspa\b|single[- ]page",
    "TypeScript": r"typescript", "JavaScript": r"javascript|\bjs\b", "HTML/CSS": r"\bhtml|\bcss",
    "Node.js": r"node\.?js|\bnode\b", "Express": r"\bexpress(\.js)?\b",
    "SQL Server": r"sql server|t-?sql|mssql", "SQL": r"\bsql\b", "Relational databases": r"relational",
    "Stored procedures": r"stored proc", "MySQL": r"mysql", "MongoDB": r"mongo", "PostgreSQL": r"postgres",
    "Database design": r"database design|data model|schema", "Reporting": r"reporting|reports?\b",
    "Azure": r"\bazure\b", "Azure DevOps": r"azure devops", "Azure Functions": r"azure functions|\bfunctions\b",
    "App Services": r"app services?", "AWS": r"\baws\b", "Docker": r"docker", "Kubernetes": r"kubernetes|\bk8s",
    "Git": r"\bgit\b|github|gitlab", "CI/CD": r"ci/cd|continuous (integration|delivery)|github actions|pipelines?",
    "Agile": r"agile|scrum|sprints?|iterative", "Testing": r"\btest(ing|s)?\b|unit test|qa\b",
    "Integrations": r"integrat", "ERP": r"\berp\b|pronto|\bsap\b|dynamics", "Microservices": r"microservice|distributed",
    "Observability": r"observab|logging|monitoring", "Architecture": r"architect", "Security / auth": r"jwt|oauth|authenticat|authori[sz]|rbac",
    "AI / LLM": r"\bai\b|llm|machine learning|claude|copilot", "Python": r"python", "Java": r"\bjava\b", "PHP": r"\bphp",
    "Swift / iOS": r"swift|\bios\b", "Microsoft 365": r"microsoft 365|m365|office 365", "Power Platform": r"power (apps|automate|platform)",
    "GraphQL": r"graphql", "Stripe / payments": r"stripe|payments?", "Legacy modernisation": r"legacy|migrat|moderni[sz]",
    "Performance": r"performance|optimi[sz]",
}
SOFT = {
    "Communication": r"communicat", "Stakeholder engagement": r"stakeholder", "Problem solving": r"problem[- ]solv|troubleshoot|root cause",
    "Autonomy / ownership": r"autonom|ownership|own(ed|ing)? ", "Collaboration": r"collaborat|team", "Documentation": r"document",
    "Continuous improvement": r"continuous improvement|improv", "Mentoring": r"mentor",
}
# Minimum developer skills every resume should show in plain words, whatever the ad says.
CORE = {
    "Problem solving": r"problem[- ]solv", "Communication": r"communicat", "Teamwork / collaboration": r"collaborat|team",
    "Attention to detail": r"attention to detail|detail[- ]oriented", "Debugging / troubleshooting": r"debug|troubleshoot|root[- ]cause",
    "Testing": r"\btest(ing|s|ed)?\b", "Agile": r"agile|scrum|kanban", "Git / version control": r"\bgit\b|github|version control",
    "Documentation": r"document",
}
# Filled from profile.json -> never_claim when --profile is given. Missing ones are honest gaps.
NEVER_CLAIM = []
PREF_SPLIT = r"(nice to have|set you apart|desirable|preferred|bonus|advantage|highly regarded|would be great|plus)"


def text_of(path):
    if path.lower().endswith(".pdf"):
        return subprocess.run(["mdls", "-raw", "-name", "kMDItemTextContent", path], capture_output=True, text=True).stdout
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf8")
        has_tbl = "<w:tbl>" in xml or "<w:tbl " in xml
        has_img = any(n.startswith("word/media/") for n in z.namelist())
        hdr = " ".join(z.read(n).decode("utf8") for n in z.namelist() if re.match(r"word/header\d*\.xml", n))
    xml = re.sub(r"</w:p>", "\n", xml)
    t = re.sub(r"<[^>]+>", "", xml)
    text_of.flags = {"tables": has_tbl, "images": has_img, "header_text": bool(re.sub(r"<[^>]+>", "", hdr).strip())}
    return t
text_of.flags = {}


def is_never(skill, pat):
    return any(n.lower() == skill.lower() or re.search(pat, n, re.I) for n in NEVER_CLAIM)


def found(pat, txt):
    return re.search(pat, txt, re.I) is not None


def score(resume_path, jd, title=""):
    rt = text_of(resume_path)
    flags = getattr(text_of, "flags", {})
    m = re.search(PREF_SPLIT, jd, re.I)
    req_txt, pref_txt = (jd[:m.start()], jd[m.start():]) if m else (jd, "")

    hard = []
    for k, p in HARD.items():
        in_req, in_pref = found(p, req_txt), found(p, pref_txt)
        if not (in_req or in_pref):
            continue
        w = 2 if in_req else 1
        hard.append({"skill": k, "weight": w, "required": in_req, "in_resume": found(p, rt), "never_claim": is_never(k, p)})
    hw = sum(h["weight"] for h in hard) or 1
    hard_pct = sum(h["weight"] for h in hard if h["in_resume"]) / hw

    soft = [{"skill": k, "in_resume": found(p, rt)} for k, p in SOFT.items() if found(p, jd)]
    soft_pct = (sum(s["in_resume"] for s in soft) / len(soft)) if soft else 1

    tw = [w for w in re.findall(r"[a-z#.+]+", title.lower()) if len(w) > 2 and w not in {"the", "and", "with", "senior", "junior", "mid"}]
    title_pct = (sum(found(re.escape(w).replace("\\ ", "[- ]?"), rt) for w in tw) / len(tw)) if tw else 1
    exact_title = bool(title) and found(re.escape(title).replace("\\ ", "[- ]?"), rt)

    yrs = [int(y) for y in re.findall(r"(\d+)\+?\s*(?:years|yrs)", jd, re.I)]
    years_ok = (not yrs) or max(yrs) <= 10

    fmt = {
        "email": found(r"[\w.+-]+@[\w-]+\.[\w.]+", rt), "phone": found(r"(\+61 ?|0)4\d{2} ?\d{3} ?\d{3}", rt),
        "skills heading": found(r"^\s*(skills|technical skills)", rt.replace("\n", "\n")) or found(r"\nskills", rt),
        "experience heading": found(r"experience", rt), "education heading": found(r"education", rt),
        "no tables": not flags.get("tables", False), "no images": not flags.get("images", False),
        "contact not only in header": not flags.get("header_text", False) or found(r"@", rt),
        "dates on roles": len(re.findall(r"(19|20)\d{2}", rt)) >= 4,
    }
    fmt_pct = sum(fmt.values()) / len(fmt)

    total = round(60 * hard_pct + 10 * (1 if exact_title else title_pct) + 10 * soft_pct + 10 * (1 if years_ok else 0.5) + 10 * fmt_pct)
    return {
        "score": total,
        "parts": {"hard skills (60)": round(60 * hard_pct, 1), "job title (10)": round(10 * (1 if exact_title else title_pct), 1),
                  "soft skills (10)": round(10 * soft_pct, 1), "experience (10)": 10 if years_ok else 5, "format (10)": round(10 * fmt_pct, 1)},
        "matched": [h["skill"] for h in hard if h["in_resume"]],
        "missing_can_add": [h["skill"] + (" (required)" if h["required"] else "") for h in hard if not h["in_resume"] and not h["never_claim"]],
        "missing_honest_gap": [h["skill"] + (" (required)" if h["required"] else "") for h in hard if not h["in_resume"] and h["never_claim"]],
        "soft_missing": [s["skill"] for s in soft if not s["in_resume"]],
        "format_fail": [k for k, v in fmt.items() if not v],
        "exact_title_in_resume": exact_title,
        "core_missing": [k for k, p in CORE.items() if not found(p, rt)],
    }


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--profile" in argv:
        i = argv.index("--profile")
        NEVER_CLAIM.extend(json.load(open(argv[i + 1])).get("never_claim", []))
        del argv[i:i + 2]
    args = [a for a in argv if a != "--json"]
    if len(args) < 2:
        sys.exit(__doc__)
    r = score(args[0], open(args[1]).read(), args[2] if len(args) > 2 else "")
    if "--json" in sys.argv:
        print(json.dumps(r, indent=1))
    else:
        print(f"ATS score: {r['score']}/100")
        for k, v in r["parts"].items():
            print(f"  {k:18} {v}")
        print("Matched:", ", ".join(r["matched"]) or "-")
        print("Missing, can add if true:", ", ".join(r["missing_can_add"]) or "-")
        print("Missing, honest gap (never claim):", ", ".join(r["missing_honest_gap"]) or "-")
        print("Soft skills missing:", ", ".join(r["soft_missing"]) or "-")
        print("Format issues:", ", ".join(r["format_fail"]) or "none")
        print("Exact job title in resume:", "yes" if r["exact_title_in_resume"] else "no")
        print("Core developer skills missing:", ", ".join(r["core_missing"]) or "none")
