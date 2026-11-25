import json, shutil, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "aussie-job-hunt" / "scripts"
EXAMPLES = ROOT / "examples"
TEMPLATE = ROOT / "skills" / "aussie-job-hunt" / "templates" / "Job_Applications_Tracker.xlsx"

sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def profile():
    return json.loads((EXAMPLES / "profile.example.json").read_text())


@pytest.fixture
def letter():
    return json.loads((EXAMPLES / "letter.example.json").read_text())


@pytest.fixture
def tracker(tmp_path):
    """A copy of the template tracker in a temp folder, so tests never touch the repo copy."""
    path = tmp_path / "Job_Applications_Tracker.xlsx"
    shutil.copy(TEMPLATE, path)
    return path
