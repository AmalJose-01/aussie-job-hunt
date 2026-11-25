#!/usr/bin/env python3
"""ATS-style match score: resume (.docx or .pdf) vs job description (text file).

Usage: python3 ats_score.py <resume.docx|pdf> <job_description.txt> ["Job Title"] [--profile profile.json] [--field NAME] [--json]

Works for any profession. Hard skills come from three places:
  1. a built-in list for the ad's field (software or nursing, detected from the ad, or set with
     --field / profile.json -> ats.field; "general" uses no built-in list),
  2. the profile's own skills (profile.json -> skills[].items) and ats.hard_skills,
  3. keywords pulled from the ad itself (bullet points, repeated phrases, acronyms, names).
Ad keywords count half as much as listed skills, so one odd phrase can't swing the score.

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
    "Time management": r"time management|prioriti[sz]", "Attention to detail": r"attention to detail|detail[- ]oriented",
}
# Minimum developer skills every resume should show in plain words, whatever the ad says.
CORE = {
    "Problem solving": r"problem[- ]solv", "Communication": r"communicat", "Teamwork / collaboration": r"collaborat|team",
    "Attention to detail": r"attention to detail|detail[- ]oriented", "Debugging / troubleshooting": r"debug|troubleshoot|root[- ]cause",
    "Testing": r"\btest(ing|s|ed)?\b", "Agile": r"agile|scrum|kanban", "Git / version control": r"\bgit\b|github|version control",
    "Documentation": r"document",
}

# Nursing and clinical roles (registered, enrolled and aged care nurses, midwives).
NURSING_HARD = {
    "AHPRA registration": r"ahpra|nmba|registered with (the )?(nursing|ahpra)",
    "Patient assessment": r"(patient|clinical|nursing|health|comprehensive) assessments?|assess(ing|ment of)? patients?",
    "Care planning": r"care plan", "Medication administration": r"medication|administer(ing)? medic|drugs? admin",
    "Deteriorating patient / escalation": r"deteriorat|escalat|\bmet calls?\b|rapid response",
    "Wound care": r"wound( care| management)?", "Pressure injury prevention": r"pressure (injur|area|ulcer)",
    "Infection prevention and control": r"infection (prevention|control)( and control)?", "Clinical documentation": r"clinical documentation|nursing notes|documentation",
    "Electronic medical record (EMR)": r"\bemr\b|\bdmr\b|electronic (medical|health|patient) record",
    "Clinical handover": r"handover|isbar|isobar", "Discharge planning": r"discharge planning",
    "IV cannulation / therapy": r"cannulat|\biv\b|intravenous", "BLS / CPR": r"\bbls\b|basic life support|\bcpr\b",
    "ALS": r"\bals\b|advanced life support", "Acute care": r"\bacute( care)?\b", "Aged care": r"aged care|residential care|gerontolog",
    "Dementia care": r"dementia", "Palliative care": r"palliative|end[- ]of[- ]life", "Mental health": r"mental health",
    "Critical care / ICU": r"critical care|intensive care|\bicu\b", "Emergency / triage": r"emergency department|\btriage",
    "Perioperative / theatre": r"perioperative|theatre|recovery room|\bpacu\b", "Paediatrics": r"paediatric|pediatric",
    "Midwifery": r"midwi", "Immunisation": r"immuni[sz]|vaccinat", "Falls prevention": r"falls? (prevention|risk|management)",
    "Multidisciplinary team": r"multi-?disciplinary|allied health", "Person-centred care": r"(person|patient)[- ]cent(red|ered)( care)?",
    "NSQHS Standards": r"nsqhs|national safety and quality", "Aged Care Quality Standards": r"aged care quality standards",
    "NDIS": r"\bndis\b", "Working with Children Check": r"working with children", "Police check": r"(national )?police check",
    "Driver's licence": r"driver'?s? licen[cs]e",
}
NURSING_CORE = {
    "Patient assessment": r"assess", "Medication safety": r"medication", "Infection control": r"infection",
    "Clinical documentation": r"document", "Communication": r"communicat", "Teamwork": r"team|collaborat|multi-?disciplinary",
    "Person-centred care": r"(person|patient)[- ]cent", "Escalation of care": r"escalat|deteriorat",
    "Time management": r"time management|priorit",
}
GENERAL_CORE = {
    "Communication": r"communicat", "Teamwork": r"team|collaborat", "Problem solving": r"problem[- ]solv|troubleshoot",
    "Attention to detail": r"attention to detail|detail[- ]oriented|accura", "Time management": r"time management|priorit|deadline",
}
# field -> how to recognise it in an ad, its hard-skill list and its core skills.
# Fields without a list (and any field in "general") rely on keywords pulled from the ad itself.
FIELDS = {
    "software": {"signals": r"\b(software|developers?|programming|coding|devops|full[- ]?stack|front[- ]?end|back[- ]?end|apis?|typescript|javascript)\b",
                 "hard": HARD, "core": CORE},
    "nursing": {"signals": r"\b(nurs\w*|patients?|clinical|ahpra|ward|aged care|midwi\w*|hospital)\b",
                "hard": NURSING_HARD, "core": NURSING_CORE, "noise": {"care", "patient", "patients", "nursing", "clinical"}},
    "general": {"signals": None, "hard": {}, "core": GENERAL_CORE},
}

# Filled from profile.json -> never_claim when --profile is given. Missing ones are honest gaps.
NEVER_CLAIM = []
# Filled from profile.json when --profile is given (see load_profile).
PROFILE = {"field": "auto", "hard": {}, "phrases": [], "core": None, "ignore": []}
PREF_SPLIT = r"(nice to have|set you apart|desirable|preferred|bonus|advantage|highly regarded|would be great|plus)"

# Words that never make a keyword on their own: grammar, and the filler every job ad uses.
STOP = set("""a an the and or of to in on for with at by from as is are be been being will would can could should must may might
our your you we us they them their this that these those it its into within across about over under per via who what which when where
how all any each other such than then also including include includes etc eg ie i if not no do does have has had get able""".split())
AD_NOISE = set("""role roles position positions job jobs candidate candidates applicant applicants experience experienced ability abilities
demonstrated demonstrable proven strong excellent good great high highly sound solid key skill skills knowledge understanding minimum
year years plus current currently required requirement requirements essential desirable preferred regarded advantage bonus opportunity
opportunities join joining team teams work working environment seeking looking responsibilities responsibility duties criteria
selection apply application applications company organisation organization employer culture benefits benefit salary package packaging
super superannuation full time part permanent casual contract fixed term hours day days week weeks month months new busy based offer
offers provide provides providing ensure ensuring support supporting deliver delivering undertake undertaking contribute contributing
participate participating closely make making well using use line lines safe safely accurate qualification qualifications certification
certificate post graduate postgraduate level grade including along help various wide range variety successful ideal passionate
motivated dedicated committed exciting rewarding dynamic fast paced paced location located available availability today now please
click contact enquiries confidential policy policies""".split())
# Action verbs that open bullet points ("Develop ...", "Administer ..."). Dropped from the start of a keyword.
VERBS = set("""achieve administer analyse analyze apply assess assist attend build collaborate complete conduct coordinate create
deliver deploy design develop document drive educate engage establish evaluate execute facilitate follow identify implement improve
lead liaise maintain manage monitor own perform plan prepare prioritise prioritize promote recognise recognize report research
respond review run schedule set share solve supervise train troubleshoot undertake update write""".split())
PLACES = set("""australia australian vic victoria nsw qld wa sa tas act nt melbourne sydney brisbane perth adelaide hobart canberra
darwin ballarat bendigo geelong regional metro remote hybrid onsite cbd""".split())
TOKEN = r"[A-Za-z][A-Za-z0-9+#'&-]*(?:[./][A-Za-z0-9+#]+)*"
BULLET = r"^\s*([-*•‣▪◦·–]|\d+[.)])\s+"


def stem(w):
    """Crude stem so 'administer' matches 'administration' and 'plans' matches 'planning'."""
    w = w.lower().strip(".'")
    for suf in ("ings", "ing", "ies", "es", "ed", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            w = w[:-len(suf)]
            break
    return w[:-2] if len(w) >= 8 else w


def phrase_re(phrase):
    """Regex that finds a phrase's words in one line, in any order, allowing other word endings."""
    words = [w for w in re.findall(TOKEN, phrase) if w.lower() not in STOP]
    return "".join(rf"(?=.*(?<![\w#]){re.escape(stem(w))}[\w-]*)" for w in words) + ".*" if words else r"(?!x)x"


def phrase_span_re(phrase):
    """Regex for the phrase's words next to each other, in order (used to blank out covered text)."""
    words = [re.escape(stem(w)) + r"[\w-]*" for w in re.findall(TOKEN, phrase) if w.lower() not in STOP]
    return r"\W+(?:(?:and|or|of|the|&)\W+)?".join(words) if words else r"(?!x)x"


def extract_keywords(jd, covered, noise=(), limit=15):
    """Pull likely hard-skill keywords out of the ad itself (RAKE-style: runs of content words).

    Text already covered by a known skill, a soft skill or the job title (the `covered` regexes) is
    blanked out first, so the ad keywords only add what the lists missed. Bullet points, repeated
    phrases, acronyms and capitalised names (Excel, Xero, Salesforce) rank highest. The ad's location
    and the profile's ignore_keywords are left out.
    """
    for p in covered:
        jd = re.sub(rf"[\w-]*(?:{p})[\w-]*", " , ", jd, flags=re.I)
    lines = [l for l in jd.splitlines() if l.strip()]
    bullets = sum(bool(re.match(BULLET, l)) for l in lines)
    ignore = {i.lower() for i in PROFILE["ignore"]} | set(noise)
    seen = {}  # keyword -> [count, first line no., original spelling, in a bullet, proper noun]
    for n, line in enumerate(lines):
        is_bullet = bool(re.match(BULLET, line)) or bullets < 3
        for chunk in re.split(r"[,;:()\[\]|!?]|\s[/–—-]\s|\.(?:\s|$)", re.sub(BULLET, "", line)):
            run, starts = [], []
            for pos, tok in enumerate(re.findall(TOKEN + r"|\S", chunk) + [""]):
                low = tok.lower().strip(".")
                if (tok and re.fullmatch(TOKEN, tok) and low not in STOP and low not in AD_NOISE and low not in PLACES
                        and not (not run and low in VERBS)):
                    run.append(tok.strip("."))
                    starts.append(pos)
                    continue
                phrases = [run] if 1 <= len(run) <= 3 else [run[i:i + 2] for i in range(0, len(run) - 1, 2)]
                for words in phrases:
                    if not words:
                        continue
                    p = " ".join(words)
                    proper = len(words) == 1 and starts[0] > 0 and p[0].isupper()
                    e = seen.setdefault(p.lower(), [0, n, p, False, False])
                    e[0] += 1
                    e[3] = e[3] or is_bullet
                    e[4] = e[4] or proper
                run, starts = [], []
    picked = []
    for k, (c, n, p, bullet, proper) in seen.items():
        acronym = bool(re.fullmatch(r"[A-Z][A-Z0-9&+#]{1,6}s?", p))
        if k in ignore or len(k) < 3 and not acronym:
            continue
        if len(k.split()) == 1 and not (acronym or proper or c >= 2):
            continue
        if not (bullet or c >= 2 or acronym):
            continue
        picked.append(((c * 2 + len(k.split()) + 3 * bullet + 2 * acronym + proper), -n, p))
    picked.sort(reverse=True)
    out = []
    for *_, p in picked:
        if not any(re.search(phrase_re(p), q, re.I) or re.search(phrase_re(q), p, re.I) for q in out):
            out.append(p)
    return out[:limit]


def detect_field(jd):
    if PROFILE["field"] in FIELDS:
        return PROFILE["field"]
    hits = {f: len(re.findall(v["signals"], jd, re.I)) for f, v in FIELDS.items() if v["signals"]}
    best = max(hits, key=hits.get)
    return best if hits[best] >= 2 else "general"


def load_profile(path):
    """Read never_claim and the optional "ats" block, and use the profile's own skills as keywords."""
    prof = json.load(open(path))
    NEVER_CLAIM.extend(prof.get("never_claim", []))
    ats = prof.get("ats", {})
    PROFILE["field"] = ats.get("field", "auto")
    hard = ats.get("hard_skills", {})
    if isinstance(hard, dict):
        PROFILE["hard"].update(hard)
    else:
        PROFILE["phrases"].extend(hard)
    if ats.get("core_skills"):
        cs = ats["core_skills"]
        PROFILE["core"] = cs if isinstance(cs, dict) else {c: phrase_re(c) for c in cs}
    PROFILE["ignore"] = ats.get("ignore_keywords", [])
    for group in prof.get("skills", []):
        for item in re.split(r",(?![^()]*\))", group.get("items", "")):
            name = re.sub(r"\s*\(.*?\)", "", item).strip()
            if name and len(name.split()) <= 4:
                PROFILE["phrases"].append(name)


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
    return any(n.lower() == skill.lower() or re.search(pat, n, re.I) or re.search(phrase_re(n), skill, re.I) for n in NEVER_CLAIM)


def found(pat, txt):
    return re.search(pat, txt, re.I) is not None


def score(resume_path, jd, title=""):
    rt = text_of(resume_path)
    flags = getattr(text_of, "flags", {})
    m = re.search(PREF_SPLIT, jd, re.I)
    req_txt, pref_txt = (jd[:m.start()], jd[m.start():]) if m else (jd, "")
    field = detect_field(jd)

    # Known skills: the field's list, the profile's own skills and ats.hard_skills. Then keywords from the ad.
    known = dict(FIELDS[field]["hard"])
    known.update(PROFILE["hard"])
    spans = list(known.values())
    for ph in PROFILE["phrases"]:
        if not any(re.search(p, ph, re.I) for p in known.values()):
            known[ph] = phrase_re(ph)
            spans.append(phrase_span_re(ph))
    covered = spans + list(SOFT.values()) + ([re.escape(title).replace("\\ ", "[- ]?")] if title else [])
    ad_words = {k: phrase_re(k) for k in extract_keywords(jd, covered, FIELDS[field].get("noise", ()))}

    hard = []
    for source, skills, weight in (("list", known, 2), ("ad", ad_words, 1)):
        for k, p in skills.items():
            in_req, in_pref = found(p, req_txt), found(p, pref_txt)
            if not (in_req or in_pref):
                continue
            w = weight if in_req else weight / 2
            hard.append({"skill": k, "weight": w, "required": in_req, "source": source,
                         "in_resume": found(p, rt), "never_claim": is_never(k, p)})
    hw = sum(h["weight"] for h in hard) or 1
    hard_pct = sum(h["weight"] for h in hard if h["in_resume"]) / hw if hard else 1

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
        "field": field,
        "ad_keywords": list(ad_words),
        "core_missing": [k for k, p in (PROFILE["core"] or FIELDS[field]["core"]).items() if not found(p, rt)],
    }


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--profile" in argv:
        i = argv.index("--profile")
        load_profile(argv[i + 1])
        del argv[i:i + 2]
    args = [a for a in argv if a != "--json"]
    if "--field" in args:
        i = args.index("--field")
        PROFILE["field"] = args[i + 1]
        del args[i:i + 2]
    if len(args) < 2:
        sys.exit(__doc__)
    r = score(args[0], open(args[1]).read(), args[2] if len(args) > 2 else "")
    if "--json" in sys.argv:
        print(json.dumps(r, indent=1))
    else:
        print(f"ATS score: {r['score']}/100  (field: {r['field']})")
        for k, v in r["parts"].items():
            print(f"  {k:18} {v}")
        print("Matched:", ", ".join(r["matched"]) or "-")
        print("Missing, can add if true:", ", ".join(r["missing_can_add"]) or "-")
        print("Missing, honest gap (never claim):", ", ".join(r["missing_honest_gap"]) or "-")
        print("Soft skills missing:", ", ".join(r["soft_missing"]) or "-")
        print("Format issues:", ", ".join(r["format_fail"]) or "none")
        print("Exact job title in resume:", "yes" if r["exact_title_in_resume"] else "no")
        print("Keywords taken from the ad:", ", ".join(r["ad_keywords"]) or "-")
        print(f"Core {r['field']} skills missing:", ", ".join(r["core_missing"]) or "none")
