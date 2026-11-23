"""lcir.py must refuse an unfinished or uncommitted prediction, and record a run."""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def copy_repo(tmp):
    """A copy of the project with a blank prediction and an empty LCIR section,
    so these tests behave the same before and after the real record is made."""
    dst = tmp / "repo"
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__"))
    valid = dst / "docs" / "validation-and-ai-use.md"
    text = valid.read_text(encoding="utf-8")
    start, end = "<!-- LCIR-START -->", "<!-- LCIR-END -->"
    pre, rest = text.split(start, 1)
    _, post = rest.split(end, 1)
    valid.write_text(pre + start + "\n*Not yet run.*\n" + end + post, encoding="utf-8")
    (dst / "docs" / "lcir" / "prediction.md").write_text("Blank <<prediction>>\n", encoding="utf-8")
    result = dst / "docs" / "lcir" / "result.md"
    if result.exists():
        result.unlink()
    return dst


def run(dst, *args):
    return subprocess.run([sys.executable, "lcir.py", *args], cwd=dst, capture_output=True, text=True)


def git(dst, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=dst,
                          capture_output=True, text=True)


def test_refuses_blank_prediction(tmp_path):
    dst = copy_repo(tmp_path)
    out = run(dst, "--change", "annual_cost_bps=35", "--skip-git-check")
    assert out.returncode != 0 and "blanks" in (out.stdout + out.stderr)


def test_refuses_uncommitted_then_runs_after_commit(tmp_path):
    dst = copy_repo(tmp_path)
    pred = dst / "docs" / "lcir" / "prediction.md"
    pred.write_text("A finished test prediction with no blanks.\n", encoding="utf-8")
    git(dst, "init", "-q")
    out = run(dst, "--change", "annual_cost_bps=35")
    assert out.returncode != 0 and "never been committed" in (out.stdout + out.stderr)
    git(dst, "add", "-A")
    git(dst, "commit", "-qm", "prediction")
    out = run(dst, "--change", "annual_cost_bps=35")
    assert out.returncode == 0, out.stderr
    rec = (dst / "docs" / "validation-and-ai-use.md").read_text(encoding="utf-8")
    assert "A finished test prediction" in rec and "Annual cost 10 bp -> 35 bp" in rec
    out = run(dst, "--change", "annual_cost_bps=35")
    assert out.returncode != 0 and "locked" in (out.stdout + out.stderr)


def test_refuses_prediction_edited_after_commit(tmp_path):
    dst = copy_repo(tmp_path)
    pred = dst / "docs" / "lcir" / "prediction.md"
    pred.write_text("A finished test prediction with no blanks.\n", encoding="utf-8")
    git(dst, "init", "-q")
    git(dst, "add", "-A")
    git(dst, "commit", "-qm", "prediction")
    pred.write_text("edited after the commit\n", encoding="utf-8")
    out = run(dst, "--change", "annual_cost_bps=35")
    assert out.returncode != 0 and "edited after" in (out.stdout + out.stderr)
