"""The memo must say what the executed output says. Each number the memo quotes
is recomputed here from output/results.json (run python run_analysis.py first)."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "output" / "results.json"
MEMO = (ROOT / "docs" / "decision-memo.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def r():
    if not RES.exists():
        pytest.skip("run python run_analysis.py first")
    return json.loads(RES.read_text(encoding="utf-8"))


def p(x, nd=2):
    return f"{x * 100:.{nd}f}%"


def test_decision_numbers(r):
    w = r["weights"]
    assert round(w["BIL"] * 100) == 75 and round(w["VT"] * 100) == 25
    assert "75% BIL / 25% VT" in MEMO
    assert p(r["exp_return"]) in MEMO                      # 6.04%
    assert p(r["signal"]["value"]) in MEMO                  # 4.22%
    assert p(r["break_even"]["BIL_breakeven"]) in MEMO      # 4.83%


def test_menu_and_screen_numbers(r):
    menu = {round(x["loss_limit"], 3): x for x in r["tradeoff"]}
    assert round(menu[-0.2]["BIL"]) == 65 and round(menu[-0.2]["VT"]) == 35
    assert p(abs(menu[-0.2]["worst12"]), 1) in MEMO          # 18.5%


def test_walk_forward_numbers(r):
    m = {x["strategy"]: x for x in r["walk_forward_metrics"]}
    assert p(m["Maple process (GS2 signal)"]["annual_return"]) in MEMO      # 4.13%
    assert p(m["Equal weight"]["annual_return"]) in MEMO                    # 4.19%
    assert p(m["Benchmark 60% VT / 40% LQD"]["annual_return"]) in MEMO      # 7.55%
    feasible = sum(1 for y in r["walk_forward_yearly"] if y["feasible"])
    assert f"{feasible} of {len(r['walk_forward_yearly'])}" in MEMO          # 1 of 13
    y21 = [y for y in r["walk_forward_yearly"] if y["decision_date"] == "2021-09-30"][0]
    assert p(abs(y21["process_next_12m"]), 1) in MEMO                       # 16.4%


def test_signal_forecast_numbers(r):
    assert f"{r['signal_forecast_mae']['gs2'] * 100:.2f} pts" in MEMO      # 0.44 pts
    assert f"{r['signal_forecast_mae']['trailing'] * 100:.2f} pts" in MEMO  # 1.21 pts


def test_live_month(r):
    assert p(r["october_2026_live_return"]) in MEMO                        # -0.14%


def test_stress_numbers(r):
    aw = r["all_worst_at_once"]
    assert p(abs(aw["75/25"]), 1) in MEMO and p(abs(aw["30/30/10/30"]), 1) in MEMO   # 12.0%, 21.4%


def test_lab20_pilot_loss_quoted_correctly():
    import sys
    sys.path.insert(0, str(ROOT))
    import engine as e
    prices = e.load_prices()
    hist = e.loss_history(prices, "2026-09-30", e.MAPLE)
    loss, _ = e.worst_12m(e.constant_mix_monthly(hist, [0.55, 0, 0, 0.45]))
    assert p(abs(loss), 1) in MEMO                                              # 23.5%
