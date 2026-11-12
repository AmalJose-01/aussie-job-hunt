#!/usr/bin/env python3
"""Build Australian-standard resumes and cover letters as .docx (raw OOXML, no dependencies).

Usage:
  build_docs.py resume <profile.json> [--variant KEY] [--out DIR]
  build_docs.py letter <letter.json> --profile <profile.json> [--out DIR]

All candidate details come from profile.json (see examples/profile.example.json).
"""
import argparse, datetime, json, os, sys, zipfile
from xml.sax.saxutils import escape

FONT, ACCENT, GREY = "Calibri", "1F3864", "555555"
TEXT_W = 11906 - 2 * 1000  # A4 width minus margins (twips)

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""

STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}" w:eastAsia="{FONT}"/><w:sz w:val="20"/><w:szCs w:val="20"/><w:color w:val="222222"/><w:lang w:val="en-AU"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="252" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:pPr><w:spacing w:after="20"/></w:pPr><w:rPr><w:b/><w:color w:val="{ACCENT}"/><w:sz w:val="44"/><w:szCs w:val="44"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:pPr><w:keepNext/><w:spacing w:before="200" w:after="80"/>
<w:pBdr><w:bottom w:val="single" w:sz="6" w:space="2" w:color="{ACCENT}"/></w:pBdr><w:outlineLvl w:val="0"/></w:pPr>
<w:rPr><w:b/><w:caps/><w:color w:val="{ACCENT}"/><w:spacing w:val="10"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListBullet"><w:name w:val="List Bullet"/><w:basedOn w:val="Normal"/><w:pPr><w:numPr><w:numId w:val="1"/></w:numPr><w:spacing w:after="20"/><w:ind w:left="300" w:hanging="220"/></w:pPr></w:style>
</w:styles>"""

NUMBERING = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="singleLevel"/>
<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/>
<w:pPr><w:ind w:left="300" w:hanging="220"/></w:pPr><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/></w:rPr></w:lvl></w:abstractNum>
<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
</w:numbering>"""

TAB = "<w:r><w:tab/></w:r>"


def run(text, b=False, i=False, color=None, sz=None):
    rpr = ("<w:b/>" if b else "") + ("<w:i/>" if i else "")
    if color: rpr += f'<w:color w:val="{color}"/>'
    if sz: rpr += f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
    rpr = f"<w:rPr>{rpr}</w:rPr>" if rpr else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def para(runs, style=None, jc=None, before=None, after=None, tab=False, keep=False):
    ppr = f'<w:pStyle w:val="{style}"/>' if style else ""
    if keep: ppr += "<w:keepNext/>"
    if tab: ppr += f'<w:tabs><w:tab w:val="right" w:pos="{TEXT_W}"/></w:tabs>'
    if before is not None or after is not None:
        ppr += "<w:spacing" + (f' w:before="{before}"' if before is not None else "") + (f' w:after="{after}"' if after is not None else "") + "/>"
    if jc: ppr += f'<w:jc w:val="{jc}"/>'
    return f"<w:p><w:pPr>{ppr}</w:pPr>{''.join(runs)}</w:p>"


def heading(t): return para([run(t)], style="Heading1")


def bullet(item):
    if isinstance(item, str):
        return para([run(item)], style="ListBullet")
    runs = [run(item["label"], b=True), run(" " + item["text"])] if item.get("label") else [run(item["text"])]
    return para(runs, style="ListBullet")


def role(title, org, dates, sub=None):
    out = [para([run(title, b=True, sz=21), run(f"  |  {org}" if org else "", sz=21), TAB, run(dates or "", color=GREY, sz=20)],
                tab=True, before=120, after=20, keep=True)]
    if sub:
        out.append(para([run(sub, i=True, color=GREY)], after=40, keep=True))
    return out


class Doc:
    """Collects body paragraphs and hyperlink relationships."""

    def __init__(self):
        self.body, self.links = [], []

    def link(self, url, text, sz=19):
        rid = f"rIdL{len(self.links) + 1}"
        self.links.append((rid, url))
        return (f'<w:hyperlink r:id="{rid}" w:history="1"><w:r><w:rPr><w:color w:val="1F5C99"/><w:u w:val="single"/>'
                f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/></w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:hyperlink>')

    def header(self, profile, headline):
        c = profile["contact"]
        sep = run("  |  ", color=GREY, sz=19)
        parts = []
        if c.get("phone"): parts.append(run(c["phone"], color=GREY, sz=19))
        if c.get("email"): parts.append(self.link(f"mailto:{c['email']}", c["email"]))
        if c.get("linkedin_url"): parts.append(self.link(c["linkedin_url"], c.get("linkedin_text") or "LinkedIn"))
        if c.get("location"): parts.append(run(c["location"], color=GREY, sz=19))
        joined = []
        for i, p in enumerate(parts):
            if i: joined.append(sep)
            joined.append(p)
        self.body += [para([run(profile["name"])], style="Title"),
                      para([run(headline, b=True, color=GREY, sz=22)], after=40),
                      para(joined, after=60)]

    def save(self, path, title, author):
        sect = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
                '<w:pgMar w:top="900" w:right="1000" w:bottom="900" w:left="1000" w:header="500" w:footer="500" w:gutter="0"/></w:sectPr>')
        document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
                    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                    f"<w:body>{''.join(self.body)}{sect}</w:body></w:document>")
        rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>'
                + "".join(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
                          f'Target="{escape(url)}" TargetMode="External"/>' for rid, url in self.links)
                + "</Relationships>")
        core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                f'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{escape(title)}</dc:title>'
                f"<dc:creator>{escape(author)}</dc:creator></cp:coreProperties>")
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", CONTENT_TYPES)
            z.writestr("_rels/.rels", RELS)
            z.writestr("word/_rels/document.xml.rels", rels)
            z.writestr("word/document.xml", document)
            z.writestr("word/styles.xml", STYLES)
            z.writestr("word/numbering.xml", NUMBERING)
            z.writestr("docProps/core.xml", core)
        return path


def build_resume(profile, variant, out):
    variants = profile.get("resume_variants", {})
    if variant not in variants:
        sys.exit(f"Unknown variant '{variant}'. Available: {', '.join(variants) or 'none'}")
    v = variants[variant]
    d = Doc()
    d.header(profile, v["headline"])
    d.body.append(heading("Summary"))
    d.body.append(para([run(v["summary"])], after=80))

    skills = profile.get("skills", [])
    order = v.get("skills_order")
    if order:
        rank = {lbl: i for i, lbl in enumerate(order)}
        skills = sorted(skills, key=lambda s: rank.get(s["label"], len(order)))
    if skills:
        d.body.append(heading("Skills"))
        for s in skills:
            d.body.append(bullet({"label": s["label"] + ":", "text": s["items"]}))

    if profile.get("experience"):
        d.body.append(heading("Experience"))
        for job in profile["experience"]:
            d.body += role(job["title"], job.get("org", ""), job.get("dates", ""), job.get("context"))
            for b in job.get("bullets", []):
                d.body.append(bullet(b))

    if profile.get("projects"):
        d.body.append(heading("Projects"))
        for p in profile["projects"]:
            d.body += role(p["name"], p.get("link", ""), p.get("tagline", ""))
            for b in p.get("bullets", []):
                d.body.append(bullet(b))

    edu = profile.get("education", []) + profile.get("certifications", [])
    if edu:
        d.body.append(heading("Education & Certifications"))
        for line in edu:
            d.body.append(para([run(line)], after=60))
    if profile.get("volunteering"):
        d.body.append(heading("Volunteering"))
        for line in profile["volunteering"]:
            d.body.append(para([run(line)], after=60))
    if profile.get("referees_on_request", True):
        d.body.append(heading("Referees"))
        d.body.append(para([run("Available on request")], after=60))

    prefix = profile.get("file_prefix") or profile["name"].replace(" ", "_")
    path = os.path.join(out, f"{prefix}_{variant}_Resume.docx")
    return d.save(path, f"{profile['name']} — Resume", profile["name"])


def build_letter(letter, profile, out):
    d = Doc()
    d.header(profile, letter.get("headline") or next(iter(profile["resume_variants"].values()))["headline"])
    d.body.append(para([], style="Heading1"))
    sp = dict(after=140)
    today = datetime.date.today()
    d.body.append(para([run(letter.get("date") or f"{today.day} {today:%B %Y}")], **sp))
    addr = []
    for i, line in enumerate(letter.get("addressee", [])):
        if i: addr.append("<w:r><w:br/></w:r>")
        addr.append(run(line))
    if addr: d.body.append(para(addr, **sp))
    if letter.get("re"): d.body.append(para([run(letter["re"], b=True)], **sp))
    d.body.append(para([run(letter.get("salutation", "Dear Hiring Manager,"), sz=21)], **sp))
    for t in letter["paragraphs"]:
        if t.startswith("##"):
            d.body.append(para([run(t[2:].strip(), b=True, sz=21)], after=40))
        else:
            d.body.append(para([run(t, sz=21)], jc="both", **sp))
    d.body.append(para([run(letter.get("sign_off", "Kind regards,"), sz=21), "<w:r><w:br/></w:r>", run(profile["name"], b=True, sz=21)]))
    prefix = profile.get("file_prefix") or profile["name"].replace(" ", "_")
    path = os.path.join(out, f"{prefix}_{letter.get('file_name', 'Cover_Letter')}.docx")
    return d.save(path, f"{profile['name']} — Cover Letter", profile["name"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=["resume", "letter"])
    ap.add_argument("source", help="profile.json for a resume, letter.json for a letter")
    ap.add_argument("--profile", help="profile.json (letters only)")
    ap.add_argument("--variant", help="resume variant key from profile.json")
    ap.add_argument("--out", default=".", help="output folder")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.kind == "resume":
        profile = json.load(open(a.source))
        variant = a.variant or next(iter(profile.get("resume_variants", {"": None})))
        print(build_resume(profile, variant, a.out))
    else:
        if not a.profile:
            sys.exit("--profile is required for letters")
        print(build_letter(json.load(open(a.source)), json.load(open(a.profile)), a.out))


if __name__ == "__main__":
    main()
