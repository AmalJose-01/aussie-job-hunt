import json, subprocess, sys, zipfile

import pytest

import ats_score
import build_docs
from conftest import EXAMPLES, SCRIPTS

JD = """Full Stack Developer
We need a developer with 3+ years of React, TypeScript and C# / .NET experience.
You will build REST APIs on SQL Server, work in an Agile team and communicate with stakeholders.
Experience with Kubernetes is required.
Nice to have: Python, Docker.
"""


@pytest.fixture
def resume(profile, tmp_path):
    return build_docs.build_resume(profile, "fullstack", str(tmp_path))


@pytest.fixture(autouse=True)
def clean_never_claim(monkeypatch):
    monkeypatch.setattr(ats_score, "NEVER_CLAIM", [])


def skills(lst):
    return {s.replace(" (required)", "") for s in lst}


def test_text_of_docx(resume):
    t = ats_score.text_of(resume)
    assert "Alex Citizen" in t
    assert ats_score.text_of.flags == {"tables": False, "images": False, "header_text": False}


def test_score_example_resume(resume):
    r = ats_score.score(resume, JD, "Full Stack Developer")
    assert 0 <= r["score"] <= 100
    assert r["score"] == round(sum(r["parts"].values()))
    assert {"React", "TypeScript", "C#", ".NET", "REST APIs", "SQL Server", "Agile"} <= set(r["matched"])
    assert "Kubernetes (required)" in r["missing_can_add"]
    assert "Python" in r["missing_can_add"]  # preferred-only, so no "(required)"
    assert r["missing_honest_gap"] == []
    assert r["exact_title_in_resume"] is True
    assert r["format_fail"] == []
    assert r["parts"]["experience (10)"] == 10


def test_never_claim_moves_gaps(resume, profile, monkeypatch):
    monkeypatch.setattr(ats_score, "NEVER_CLAIM", profile["never_claim"])
    r = ats_score.score(resume, JD, "Full Stack Developer")
    assert {"Kubernetes", "Python"} <= skills(r["missing_honest_gap"])
    assert not {"Kubernetes", "Python"} & skills(r["missing_can_add"])


def test_required_vs_preferred_weighting(resume):
    req = ats_score.score(resume, "Must know Docker.", "")
    pref = ats_score.score(resume, "Must know React. Nice to have Docker.", "")
    assert req["parts"]["hard skills (60)"] == 0
    # React (weight 2) matched, Docker (weight 1) missing -> 2/3 of 60
    assert pref["parts"]["hard skills (60)"] == 40.0


def test_long_experience_halves_score(resume):
    assert ats_score.score(resume, "15+ years of React", "")["parts"]["experience (10)"] == 5


def test_empty_jd_and_title(resume):
    r = ats_score.score(resume, "", "")
    assert r["matched"] == [] and r["missing_can_add"] == []


def test_format_flags_tables_and_images(resume, tmp_path):
    bad = tmp_path / "bad.docx"
    with zipfile.ZipFile(resume) as src, zipfile.ZipFile(bad, "w") as dst:
        for n in src.namelist():
            data = src.read(n)
            if n == "word/document.xml":
                data = data.replace(b"<w:body>", b"<w:body><w:tbl></w:tbl>")
            dst.writestr(n, data)
        dst.writestr("word/media/image1.png", b"x")
    r = ats_score.score(str(bad), JD, "")
    assert {"no tables", "no images"} <= set(r["format_fail"])


def test_core_missing(resume):
    r = ats_score.score(resume, JD, "")
    # the example resume shows these in plain words
    assert "Communication" not in r["core_missing"]
    assert "Problem solving" not in r["core_missing"]


def test_cli_json(resume, tmp_path):
    jd = tmp_path / "jd.txt"
    jd.write_text(JD)
    r = subprocess.run([sys.executable, str(SCRIPTS / "ats_score.py"), resume, str(jd), "Full Stack Developer",
                        "--profile", str(EXAMPLES / "profile.example.json"), "--json"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert "Kubernetes (required)" in out["missing_honest_gap"]


def test_cli_text_and_usage(resume, tmp_path):
    jd = tmp_path / "jd.txt"
    jd.write_text(JD)
    r = subprocess.run([sys.executable, str(SCRIPTS / "ats_score.py"), resume, str(jd)], capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.startswith("ATS score: ")
    r = subprocess.run([sys.executable, str(SCRIPTS / "ats_score.py")], capture_output=True, text=True)
    assert r.returncode != 0 and "Usage" in r.stderr
