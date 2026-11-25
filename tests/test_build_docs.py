import re, subprocess, sys, zipfile

import pytest

import build_docs
from conftest import EXAMPLES, SCRIPTS

PARTS = {"[Content_Types].xml", "_rels/.rels", "word/_rels/document.xml.rels", "word/document.xml",
         "word/styles.xml", "word/numbering.xml", "docProps/core.xml"}


def doc_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf8")
    return re.sub(r"<[^>]+>", "", xml.replace("</w:p>", "\n"))


def headings(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf8")
    return re.findall(r'<w:pStyle w:val="Heading1"/>.*?<w:t xml:space="preserve">([^<]*)</w:t>', xml)


@pytest.mark.parametrize("variant", ["fullstack", "frontend", "product"])
def test_resume_is_valid_docx(profile, tmp_path, variant):
    path = build_docs.build_resume(profile, variant, str(tmp_path))
    assert path.endswith(f"Alex_Citizen_{variant}_Resume.docx")
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert PARTS <= set(z.namelist())
        # every XML part must parse
        import xml.dom.minidom
        for n in PARTS:
            xml.dom.minidom.parseString(z.read(n))
        rels = z.read("word/_rels/document.xml.rels").decode()
    assert "mailto:alex.citizen@example.com" in rels
    assert "linkedin.com/in/alex-citizen-example" in rels


def test_resume_content(profile, tmp_path):
    text = doc_text(build_docs.build_resume(profile, "fullstack", str(tmp_path)))
    for s in ["Alex Citizen", "0400 000 000", "Melbourne, VIC", "Software Developer", "Example Co",
              "BookIt", "Bachelor of Information Technology", "Microsoft AZ-900", "Available on request"]:
        assert s in text
    assert profile["resume_variants"]["fullstack"]["summary"] in text


def test_section_order_default_and_projects_first(profile, tmp_path):
    h = headings(build_docs.build_resume(profile, "fullstack", str(tmp_path)))
    assert h.index("EXPERIENCE") < h.index("PROJECTS")
    h = headings(build_docs.build_resume(profile, "product", str(tmp_path)))
    assert h.index("PROJECTS") < h.index("EXPERIENCE")


def test_skills_order(profile, tmp_path):
    text = doc_text(build_docs.build_resume(profile, "frontend", str(tmp_path)))
    order = [text.index(l + ":") for l in ["Frontend", "Quality", "Backend", "Data", "Delivery", "AI"]]
    assert order == sorted(order)


def test_xml_escaping(profile, tmp_path):
    profile["resume_variants"]["fullstack"]["summary"] = "R&D <fast> \"quotes\""
    path = build_docs.build_resume(profile, "fullstack", str(tmp_path))
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode()
    assert "R&amp;D &lt;fast&gt;" in xml


def test_unknown_variant_exits(profile, tmp_path):
    with pytest.raises(SystemExit, match="Unknown variant 'nope'"):
        build_docs.build_resume(profile, "nope", str(tmp_path))


def test_referees_can_be_omitted(profile, tmp_path):
    profile["referees_on_request"] = False
    assert "REFEREES" not in headings(build_docs.build_resume(profile, "fullstack", str(tmp_path)))


def test_letter(profile, letter, tmp_path):
    path = build_docs.build_letter(letter, profile, str(tmp_path))
    assert path.endswith("Alex_Citizen_Cover_Letter_Example_Co.docx")
    text = doc_text(path)
    assert "Re: Full Stack Developer (Ref 12345)" in text
    assert "Dear Hiring Manager," in text
    assert "Kind regards," in text
    # "##" paragraphs become plain bold subheadings without the marker
    assert "React, TypeScript and .NET in production" in text
    assert "##" not in text


def test_letter_date_and_default_headline(profile, letter, tmp_path):
    letter["date"] = "1 January 2027"
    del letter["headline"]
    text = doc_text(build_docs.build_letter(letter, profile, str(tmp_path)))
    assert "1 January 2027" in text
    assert profile["resume_variants"]["fullstack"]["headline"] in text


def test_cli(tmp_path):
    run = lambda *a: subprocess.run([sys.executable, str(SCRIPTS / "build_docs.py"), *a],
                                    capture_output=True, text=True)
    r = run("resume", str(EXAMPLES / "profile.example.json"), "--out", str(tmp_path / "out"))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "out" / "Alex_Citizen_fullstack_Resume.docx").exists()
    r = run("letter", str(EXAMPLES / "letter.example.json"), "--out", str(tmp_path))
    assert r.returncode != 0 and "--profile is required" in r.stderr
    r = run("letter", str(EXAMPLES / "letter.example.json"), "--profile", str(EXAMPLES / "profile.example.json"), "--out", str(tmp_path))
    assert r.returncode == 0, r.stderr
