"""
lcir.py - runs the Locked Changed-Input Record (LCIR).

The rule: write your prediction in docs/lcir/prediction.md with AI closed,
commit and push it, THEN run this script. The script refuses to run if the
prediction is unfinished, uncommitted, or edited after its commit, so the
record proves the prediction came first.

    python lcir.py --change reserve_min_pct=80

Changes you can make (one per run, units in the name):
    target_return_pct=6.0      reserve_min_pct=80        loss_limit_pct=-10
    annual_cost_bps=150        grid_step=10              window_months=36 | all
    gs2_shift_pts=2            vt_shift_pts=-1           ief_shift_pts=1
    lqd_shift_pts=1            bil_source=history

It writes docs/lcir/result.md (before/after, prediction commit, run time) and
copies the record into docs/validation-and-ai-use.md between the LCIR markers.
"""
import argparse
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timezone

import engine as e

PRED = e.ROOT / "docs" / "lcir" / "prediction.md"
RESULT = e.ROOT / "docs" / "lcir" / "result.md"
VALID = e.ROOT / "docs" / "validation-and-ai-use.md"
REVIEW = "2026-09-30"
START, END = "<!-- LCIR-START -->", "<!-- LCIR-END -->"


def git(*args):
    return subprocess.run(["git", *args], cwd=e.ROOT, capture_output=True, text=True)


def check_prediction(skip_git: bool) -> dict:
    if not PRED.exists():
        sys.exit("docs/lcir/prediction.md is missing.")
    text = PRED.read_text(encoding="utf-8")
    if "<<" in text or ">>" in text:
        sys.exit("prediction.md still has <<blanks>>. Fill every one, AI closed, then commit.")
    info = {"text": text, "commit": "not verified (--skip-git-check)", "commit_time": "",
            "remote": ""}
    if skip_git:
        return info
    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        sys.exit("This folder is not a git repository. Commit the prediction first.")
    log = git("log", "-1", "--format=%H|%cI", "--", PRED.relative_to(e.ROOT).as_posix())
    if not log.stdout.strip():
        sys.exit("prediction.md has never been committed. Run:\n  git add docs/lcir/prediction.md\n"
                 "  git commit -m \"LCIR prediction (AI off)\"\n  git push\nthen run this again.")
    if git("diff", "--quiet", "HEAD", "--", PRED.relative_to(e.ROOT).as_posix()).returncode != 0:
        sys.exit("prediction.md was edited after its last commit. A locked prediction cannot "
                 "change after it is committed. Undo the edit (git checkout -- docs/lcir/prediction.md).")
    sha, when = log.stdout.strip().split("|")
    info.update(commit=sha, commit_time=when)
    pushed = git("branch", "-r", "--contains", sha)
    info["remote"] = "yes" if pushed.stdout.strip() else "NOT YET PUSHED - run git push"
    url = git("remote", "get-url", "origin").stdout.strip()
    if url:
        url = url.removesuffix(".git").replace("git@github.com:", "https://github.com/")
        info["link"] = f"{url}/commit/{sha}"
    return info


def apply_change(key: str, value: str):
    m, kw, desc = e.MAPLE, {}, ""
    v = value.strip()
    if key == "target_return_pct":
        old, m = m.target_return * 100, replace(m, target_return=float(v) / 100)
        desc = f"Return objective {old:.2f}% -> {float(v):.2f}% (modeled net, % a year)"
    elif key == "reserve_min_pct":
        old, m = m.reserve_min * 100, replace(m, reserve_min=float(v) / 100)
        desc = f"Reserve minimum in BIL {old:.0f}% -> {float(v):.0f}% of the portfolio"
    elif key == "loss_limit_pct":
        old, m = m.loss_limit * 100, replace(m, loss_limit=float(v) / 100)
        desc = f"Worst 12-month loss limit {old:.1f}% -> {float(v):.1f}%"
    elif key == "annual_cost_bps":
        old, m = m.annual_cost_bps, replace(m, annual_cost_bps=float(v))
        desc = f"Annual cost {old:.0f} bp -> {float(v):.0f} bp a year"
    elif key == "grid_step":
        old, m = m.grid_step, replace(m, grid_step=int(v))
        desc = f"Weight grid {old} -> {int(v)} percentage points"
    elif key == "window_months":
        kw["window_months"] = None if v == "all" else int(v)
        desc = f"Estimation window 60 months -> {v} months"
    elif key == "bil_source":
        kw["bil_source"] = v
        desc = f"BIL expected return source gs2 -> {v}"
    elif key.endswith("_shift_pts"):
        fund = {"gs2": "BIL", "vt": "VT", "ief": "IEF", "lqd": "LQD"}[key.split("_")[0]]
        kw["mu_shift"] = {fund: float(v) / 100}
        desc = (f"{'GS2 signal (BIL expected return)' if fund == 'BIL' else fund + ' expected return'}"
                f" shifted {float(v):+.2f} percentage points")
    else:
        sys.exit(f"Unknown change '{key}'. See the list at the top of lcir.py.")
    return m, kw, desc


def summarise(prices, vint, m, kw):
    d = e.run_scenario(prices, vint, REVIEW, m, kw.get("window_months", 60),
                       kw.get("bil_source", "gs2"), kw.get("mu_shift"))
    aw = None if d.result.weights is None else e.all_worst_at_once(prices, REVIEW, d.result.weights, m)[0]
    _, spread = e.stability(prices, vint, REVIEW, m, kw.get("bil_source", "gs2"),
                            mu_shift=kw.get("mu_shift"))
    verb, _ = e.recommendation(d, spread)
    r = d.result
    bil_mu = d.inputs.mu[0]
    return {"weights": "-" if r.weights is None else e.fmt_w(r.weights),
            "VT weight": "-" if r.weights is None else f"{r.weights[3] * 100:.0f}%",
            "BIL expected return": f"{bil_mu:.2%}",
            "Modeled net return": "-" if r.exp_return is None else f"{r.exp_return:.2%}",
            "Volatility": "-" if r.vol is None else f"{r.vol:.2%}",
            "Worst 12-month loss": "-" if r.worst12 is None else f"{r.worst12:.1%}",
            "All-worst-at-once loss": "-" if aw is None else f"{aw:.1%}",
            "Meets objective": "yes" if r.feasible else "no",
            "Window spread (pts)": f"{spread:.0f}",
            "Recommendation": verb}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--change", required=True, help="one change, e.g. reserve_min_pct=80")
    ap.add_argument("--skip-git-check", action="store_true",
                    help="only for a test run; the record will say 'not verified'")
    a = ap.parse_args()
    if "### Locked Changed-Input Record" in VALID.read_text(encoding="utf-8"):
        sys.exit("The Locked Changed-Input Record has already been run and written into "
                 "docs/validation-and-ai-use.md. It is locked; a second run would overwrite it.")
    pred = check_prediction(a.skip_git_check)
    key, _, value = a.change.partition("=")
    m, kw, desc = apply_change(key.strip(), value)
    prices, vint = e.load_prices(), e.load_gs2_vintages()
    before = summarise(prices, vint, e.MAPLE, {})
    after = summarise(prices, vint, m, kw)
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    rows = "\n".join(f"| {k} | {before[k]} | {after[k]} |" for k in before)
    link = pred.get("link", "")
    body = f"""### Locked Changed-Input Record

**Prediction (verbatim from `docs/lcir/prediction.md`, written AI-off):**

{pred['text'].strip()}

**Lock:** prediction committed at `{pred['commit']}` ({pred['commit_time']}); pushed to GitHub: {pred['remote']}. {('[Commit on GitHub](' + link + ')') if link else ''}

**Run (AI closed):** `python lcir.py --change {a.change}` at {run_at}, review date {REVIEW}, data files unchanged (prices sha256 `{run_sha(e.PRICES_CSV)}`).

**Changed input:** {desc}. Everything else at its base value.

| Measure | Before (base) | After (changed) |
|---|---|---|
{rows}

"""
    student = """
**Reconciliation (Shrey writes this after the run, AI closed):** <<did each line of my prediction match? which did not?>>

**Actual decision effect:** <<does the committee recommendation change? from what to what, and why?>>

**Failure diagnosis (only if the prediction missed; otherwise write "not needed"):** <<the first assumption, unit, sign or rule that broke - do not rewrite the prediction>>
"""
    RESULT.write_text("# Locked Changed-Input Record - machine record\n\n" + body +
                      "\nThe reconciliation is in docs/validation-and-ai-use.md, section 7.\n", encoding="utf-8")
    body = body + student
    v = VALID.read_text(encoding="utf-8")
    if START in v and END in v:
        pre, rest = v.split(START, 1)
        _, post = rest.split(END, 1)
        VALID.write_text(pre + START + "\n" + body + "\n" + END + post, encoding="utf-8")
    print(f"Before: {before['weights']} -> After: {after['weights']} | "
          f"{before['Recommendation']} -> {after['Recommendation']}")
    print("Wrote docs/lcir/result.md and the LCIR section of docs/validation-and-ai-use.md.")
    print("Now open docs/validation-and-ai-use.md, section 7, and fill the three lines marked")
    print("with double angle brackets yourself (AI closed). Then commit and push.")


def run_sha(path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


if __name__ == "__main__":
    main()
