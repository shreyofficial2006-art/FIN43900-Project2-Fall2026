"""Tests for engine.py. Run from the repository root:  python -m pytest -q

Known answers come from the course labs (Lab 14 and Lab 15 Meridian training
values), so they were fixed before this project's code existed. The rest test
the rules a committee relies on: no look-ahead, honest infeasibility, the
data gate, and that the app's search really is the lowest-risk passing mix."""
import itertools
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import engine as e  # noqa: E402

# ---------------- Lab 14 / Lab 15 Meridian training inputs ----------------
M_ASSETS = ["Bills", "10-year", "IG", "Equity"]
M_MU = np.array([0.035, 0.043, 0.050, 0.080])
M_VOL = np.array([0.005, 0.07, 0.06, 0.16])
M_CORR = np.array([[1.00, 0.10, 0.05, 0.00],
                   [0.10, 1.00, 0.80, -0.10],
                   [0.05, 0.80, 1.00, 0.25],
                   [0.00, -0.10, 0.25, 1.00]])
MERIDIAN = e.Mandate(target_return=0.065, reserve_min=0.03, reserve_assets=("Bills", "10-year"),
                     loss_limit=None, annual_cost_bps=0.0)


def meridian_inputs(mu=M_MU, corr=M_CORR):
    return e.Inputs(assets=M_ASSETS, mu=np.array(mu, float), cov=e.cov_from_corr(M_VOL, corr))


def pct(x, nd=2):
    return round(x * 100, nd)


def test_lab14_benchmark_known_answer():
    inp = meridian_inputs()
    w = np.array([0, 0, 0.4, 0.6])
    assert pct(e.port_return(w, inp.mu)) == 6.80
    assert pct(e.port_vol(w, inp.cov)) == 10.46        # 9.90 would mean the correlation term is missing


def test_lab14_equal_weight_and_inverse_vol():
    inp = meridian_inputs()
    ew = e.equal_weight(4)
    assert (pct(e.port_return(ew, inp.mu)), pct(e.port_vol(ew, inp.cov))) == (5.20, 5.21)
    iv = e.inverse_vol(M_VOL)
    assert [round(x * 100, 1) for x in iv] == [84.3, 6.0, 7.0, 2.6]
    assert (pct(e.port_return(iv, inp.mu)), pct(e.port_vol(iv, inp.cov))) == (3.77, 1.05)


def test_lab14_correlation_probe():
    corr = M_CORR.copy()
    corr[2, 3] = corr[3, 2] = 0.50
    inp = meridian_inputs(corr=corr)
    assert pct(e.port_vol(np.array([0, 0, 0.4, 0.6]), inp.cov)) == 11.00


def test_lab14_bad_correlation_refused():
    corr = M_CORR.copy()
    corr[2, 3] = corr[3, 2] = 1.3
    with pytest.raises(ValueError):
        e.cov_from_corr(M_VOL, corr)


def test_lab15_search_known_answers():
    res = e.search(meridian_inputs(), MERIDIAN)
    assert [round(x * 100) for x in res.weights] == [0, 20, 25, 55]
    assert (pct(res.exp_return), pct(res.vol)) == (6.51, 9.44)
    mu = M_MU.copy()
    mu[3] = 0.07                                          # equity 8.0 -> 7.0
    res2 = e.search(meridian_inputs(mu=mu), MERIDIAN)
    assert [round(x * 100) for x in res2.weights] == [0, 10, 10, 80]
    assert (pct(res2.exp_return), pct(res2.vol)) == (6.53, 12.94)
    assert round(np.max(np.abs(res2.weights - res.weights)) * 100) == 25
    corr = M_CORR.copy()
    corr[2, 3] = corr[3, 2] = 0.50
    res3 = e.search(meridian_inputs(corr=corr), MERIDIAN)
    assert [round(x * 100) for x in res3.weights] == [0, 40, 0, 60]
    assert (pct(res3.exp_return), pct(res3.vol)) == (6.52, 9.73)


def test_infeasible_objective_is_reported_not_lowered():
    res = e.search(meridian_inputs(), replace(MERIDIAN, target_return=0.20))
    assert res.feasible is False and res.weights is None


def test_search_is_truly_the_minimum():
    """Brute force, written independently of engine.grid / engine.search."""
    inp = meridian_inputs()
    best = None
    for a, b, c in itertools.product(range(21), repeat=3):
        d = 20 - a - b - c
        if d < 0:
            continue
        w = np.array([a, b, c, d]) / 20
        if w[0] + w[1] < 0.03 or w @ inp.mu < 0.065 - 1e-12:
            continue
        v = w @ inp.cov @ w
        if best is None or v < best[0] - 1e-15:
            best = (v, w)
    assert np.allclose(e.search(inp, MERIDIAN).weights, best[1])


def test_grid_size_and_sums():
    g = e.grid(4, 5)
    assert len(g) == math.comb(23, 3) == 1771
    assert np.allclose(g.sum(axis=1), 1.0) and g.min() >= 0


# ---------------- the real data and the point-in-time rule ----------------
@pytest.fixture(scope="module")
def data():
    return e.load_prices(), e.load_gs2_vintages()


def test_price_file_shape(data):
    p, _ = data
    assert list(p.columns) == e.TICKERS
    assert p.index[0] == pd.Timestamp("2008-06-30") and p.index[-1] == pd.Timestamp("2026-10-30")
    assert len(p) == 221


def test_annualisation_matches_hand_formula(data):
    p, v = data
    r = e.monthly_returns(p)
    inp = e.estimate_inputs(r, "2026-09-30", 60, "history", v)
    vt = (p["VT"] / p["VT"].shift(1) - 1).loc["2021-10-01":"2026-09-30"]
    assert len(vt) == 60
    assert inp.mu[3] == pytest.approx(vt.mean() * 12)
    assert inp.vol[3] == pytest.approx(vt.std(ddof=1) * math.sqrt(12))


def test_gs2_is_point_in_time(data):
    _, v = data
    s25 = e.gs2_as_known(v, "2025-09-30")
    s26 = e.gs2_as_known(v, "2026-09-30")
    assert s25.value == pytest.approx(0.037) and s25.month_measured == "2025-08"
    assert s26.value == pytest.approx(0.0422) and s26.month_measured == "2026-08"
    with pytest.raises(e.DataGateError):
        e.gs2_as_known(v, "2026-06-30")        # no vintage archived for that date: refuse


def test_signal_replaces_only_bil(data):
    p, v = data
    r = e.monthly_returns(p)
    a = e.estimate_inputs(r, "2026-09-30", 60, "gs2", v)
    b = e.estimate_inputs(r, "2026-09-30", 60, "history", v)
    assert a.mu[0] == pytest.approx(0.0422)
    assert np.allclose(a.mu[1:], b.mu[1:]) and np.allclose(a.cov, b.cov)


def test_no_look_ahead_in_estimates(data):
    """Changing every price AFTER the decision date must not change the decision."""
    p, v = data
    d0 = e.decide(p, v, "2025-09-30")
    p2 = p.copy()
    p2.loc[p2.index > "2025-09-30"] *= 3.0
    d1 = e.decide(p2, v, "2025-09-30")
    assert np.allclose(d0.result.weights, d1.result.weights)
    assert d0.result.exp_return == pytest.approx(d1.result.exp_return)


def test_data_gate_refuses_gaps(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("date,BIL,IEF,LQD,VT\n2020-01-31,1,1,1,1\n2020-03-31,1,1,1,1\n")
    with pytest.raises(e.DataGateError):
        e.load_prices(bad)
    bad.write_text("date,BIL,IEF,LQD,VT\n2020-01-31,1,1,1,1\n2020-02-29,1,,1,1\n")
    with pytest.raises(e.DataGateError):
        e.load_prices(bad)


def test_sanity_flags_found_and_kept(data):
    p, _ = data
    flags = e.sanity_flags(p)
    assert {(f["date"], f["fund"]) for f in flags} == {("2019-07-31", "VT"), ("2024-01-31", "VT")}


def test_extended_history_only_adds_months_before_vt_launch(data):
    p, _ = data
    x = e.extended_history(p)
    actual = e.monthly_returns(p)
    assert x.index[0] == pd.Timestamp("2007-06-30")
    assert len(x) == len(actual) + 13
    assert np.allclose(x.iloc[13:].to_numpy(), actual.to_numpy())


def test_decision_2026_reports_the_conflict(data):
    p, v = data
    d = e.decide(p, v, "2026-09-30")
    assert d.result.feasible is False and d.result.fallback is True
    assert [round(x * 100) for x in d.result.weights] == [75, 0, 0, 25]
    assert all(r["pass"] for r in d.baselines["Maple process (closest compliant mix)"]["rules"]
               if "return" not in r["rule"])          # every HARD rule passes
    loose = e.decide(p, v, "2026-09-30", replace(e.MAPLE, loss_limit=-0.20))
    assert loose.result.feasible and [round(x * 100) for x in loose.result.weights] == [65, 0, 0, 35]


def test_costs_lower_return_never_raise_it(data):
    p, v = data
    a = e.decide(p, v, "2026-09-30")
    b = e.decide(p, v, "2026-09-30", replace(e.MAPLE, annual_cost_bps=75))
    assert b.result.exp_return < a.result.exp_return


def test_backtest_uses_only_known_data(data):
    p, v = data
    bt = e.backtest(p, v, last_year=2016)
    p2 = p.copy()
    p2.loc[p2.index > "2017-09-30"] *= 0.5             # crash the future
    bt2 = e.backtest(p2, v, last_year=2016)
    assert np.allclose(bt.yearly[e.TICKERS].to_numpy(), bt2.yearly[e.TICKERS].to_numpy())


def test_fetch_parser_keeps_last_trading_day_of_each_month():
    import json as _json
    import fetch_data as f
    # 2026-09-30 and 2026-10-30 at 09:30 New York (13:30 UTC), plus 2026-09-29
    ts = [1790775000 - 86400, 1790775000, 1793367000]
    payload = _json.dumps({"chart": {"error": None, "result": [{
        "timestamp": ts, "indicators": {"adjclose": [{"adjclose": [1.0, 2.0, 3.0]}]}}]}}).encode()
    out = f.month_ends_from_chart(payload, "2026-10")
    assert out == {"2026-09": ("2026-09-30", 2.0), "2026-10": ("2026-10-30", 3.0)}
    assert f.month_ends_from_chart(payload, "2026-09") == {"2026-09": ("2026-09-30", 2.0)}


def test_loss_screen_vectorised_equals_one_by_one(data):
    p, _ = data
    hist = e.loss_history(p, "2026-09-30", e.MAPLE)
    W = e.grid(4, 5)
    fast = e.worst_12m_matrix(hist, W)
    for i in range(0, len(W), 97):
        assert fast[i] == pytest.approx(e.worst_12m(e.constant_mix_monthly(hist, W[i]))[0], abs=1e-12)
