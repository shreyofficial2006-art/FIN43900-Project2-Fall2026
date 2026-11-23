"""
engine.py - every finance calculation for the Maple Education Fund app.

The app (app.py), the report script (run_analysis.py), the changed-input
runner (lcir.py) and the tests all import from this file. Nothing else in
the repository computes a return, a volatility or an allocation.

Conventions (the same everywhere):
  * Monthly simple return  r_t = P_t / P_{t-1} - 1, on Adj Close prices.
  * Annual expected return = mean of monthly returns x 12 (arithmetic).
  * Annual covariance      = sample covariance of monthly returns x 12
                             (n - 1 denominator), i.e. corr x vol x vol.
  * Portfolio return       = w . mu - annual cost;  volatility = sqrt(w' S w).
  * Worst 12-month loss    = lowest compounded return over any 12 straight
                             months of the constant mix (rebalanced monthly).
  * Weights are on a 5-point grid, long-only, and sum to exactly 100%.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
PRICES_CSV = ROOT / "data" / "prices_monthly.csv"
GS2_CSV = ROOT / "data" / "gs2_vintages.csv"

TICKERS = ["BIL", "IEF", "LQD", "VT"]
FUND_NAMES = {
    "BIL": "1-3 Month T-Bill ETF (cash reserve)",
    "IEF": "7-10 Year Treasury ETF",
    "LQD": "Investment-grade corporate bond ETF",
    "VT": "Total World Stock ETF",
}
TOL = 1e-12  # floating-point tolerance only; never an economic allowance


# ---------------------------------------------------------------------------
# 1. The mandate (Maple Education Fund) - every rule the app checks
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Mandate:
    target_return: float = 0.065          # modeled net annual return objective
    reserve_min: float = 0.10             # at least 10% in reserve-eligible funds
    reserve_assets: tuple = ("BIL",)      # only BIL counts as the award reserve
    loss_limit: float | None = -0.15      # worst 12-month loss no worse than -15%
    grid_step: int = 5                    # weights in 5-point steps
    annual_cost_bps: float = 10.0         # advisory/custody drag, bp per year
    trading_cost_bps: float = 10.0        # bp per 100% of portfolio traded
    stability_limit_pts: float = 20.0     # max weight move across windows to adopt
    loss_screen: str = "extended"         # "extended": Jun-2007 on, VT proxy before
                                          # its Jun-2008 launch; "fund": fund prices only
    benchmark: tuple = (("BIL", 0.0), ("IEF", 0.0), ("LQD", 0.40), ("VT", 0.60))

    @property
    def annual_cost(self) -> float:
        return self.annual_cost_bps / 10_000.0

    @property
    def trading_cost(self) -> float:
        return self.trading_cost_bps / 10_000.0

    def benchmark_weights(self, assets) -> np.ndarray:
        b = dict(self.benchmark)
        return np.array([b.get(a, 0.0) for a in assets], dtype=float)


MAPLE = Mandate()


# ---------------------------------------------------------------------------
# 2. Data loading with a gate: refuse bad data instead of silently fixing it
# ---------------------------------------------------------------------------
class DataGateError(ValueError):
    """Raised when an input file breaks a stated data rule."""


def load_prices(path: Path | str = PRICES_CSV) -> pd.DataFrame:
    df = pd.read_csv(path)
    if list(df.columns[:1]) != ["date"]:
        raise DataGateError("first column must be 'date'")
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    df = df.set_index("date")
    if not df.index.is_monotonic_increasing or df.index.has_duplicates:
        raise DataGateError("dates must be strictly increasing with no duplicates")
    if df.isna().any().any():
        bad = df.index[df.isna().any(axis=1)][0].date()
        raise DataGateError(f"missing price on {bad}; the gate does not fill gaps")
    if (df <= 0).any().any():
        raise DataGateError("every price must be positive")
    months = df.index.to_period("M")
    gaps = (months[1:] - months[:-1]).map(lambda x: x.n)
    if any(g != 1 for g in gaps):
        raise DataGateError("months must be consecutive (one row per calendar month)")
    return df.astype(float)


def monthly_returns(prices: pd.DataFrame) -> pd.DataFrame:
    r = prices / prices.shift(1) - 1.0
    return r.iloc[1:]


def sanity_flags(prices: pd.DataFrame) -> list[dict]:
    """Second gate (Lab 16 lesson: on time is not the same as true).
    Flags, but does not delete, months where a non-cash fund's month-end
    Adj Close is exactly unchanged, and any monthly move beyond +/-25%."""
    flags = []
    r = monthly_returns(prices)
    for t in prices.columns:
        if t == "BIL":
            continue  # a T-bill fund at zero rates can legitimately not move
        for d, v in r[t].items():
            if v == 0.0:
                flags.append({"date": d.date().isoformat(), "fund": t,
                              "issue": "month-end Adj Close identical to prior month"})
            elif abs(v) > 0.25:
                flags.append({"date": d.date().isoformat(), "fund": t,
                              "issue": f"monthly return {v:+.1%} beyond +/-25%"})
    return flags


def load_gs2_vintages(path: Path | str = GS2_CSV) -> pd.DataFrame:
    v = pd.read_csv(path, dtype={"last_month_measured": str})
    v["vintage_date"] = pd.to_datetime(v["vintage_date"])
    v = v.sort_values("vintage_date").reset_index(drop=True)
    for _, row in v.iterrows():
        measured = pd.Period(row["last_month_measured"], freq="M")
        if measured >= pd.Period(row["vintage_date"], freq="M"):
            raise DataGateError(
                f"GS2 vintage {row['vintage_date'].date()} claims month {measured}, "
                "which cannot have been published yet")
    return v


@dataclass(frozen=True)
class Signal:
    value: float              # decimal, e.g. 0.0422
    month_measured: str       # e.g. "2026-08"
    vintage_date: str         # e.g. "2026-09-30"


def gs2_as_known(vintages: pd.DataFrame, decision_date) -> Signal:
    """GS2 as it could be read ON the decision date (ALFRED vintage).
    Uses only a vintage dated on or before the decision date, and only if it
    is the vintage for that exact date - a stale vintage is refused, because
    the app must never pretend an old reading is current."""
    d = pd.Timestamp(decision_date)
    exact = vintages[vintages["vintage_date"] == d]
    if exact.empty:
        raise DataGateError(
            f"no archived GS2 vintage for {d.date()}; add it from ALFRED before deciding")
    row = exact.iloc[0]
    return Signal(value=float(row["gs2_percent"]) / 100.0,
                  month_measured=str(row["last_month_measured"]),
                  vintage_date=row["vintage_date"].date().isoformat())


# ---------------------------------------------------------------------------
# 3. Estimates
# ---------------------------------------------------------------------------
@dataclass
class Inputs:
    assets: list
    mu: np.ndarray            # annual expected returns (decimal)
    cov: np.ndarray           # annual covariance
    window_start: str = ""
    window_end: str = ""
    n_months: int = 0
    bil_source: str = "history"
    signal: Signal | None = None
    history_mu: np.ndarray | None = None   # trailing means before any override

    @property
    def vol(self) -> np.ndarray:
        return np.sqrt(np.diag(self.cov))

    @property
    def corr(self) -> np.ndarray:
        v = self.vol
        return self.cov / np.outer(v, v)


def returns_through(returns: pd.DataFrame, decision_date) -> pd.DataFrame:
    """Only months that ended on or before the decision date (no look-ahead)."""
    d = pd.Timestamp(decision_date)
    return returns[returns.index <= d]


def estimate_inputs(returns: pd.DataFrame, decision_date, window_months: int | None = 60,
                    bil_source: str = "gs2", vintages: pd.DataFrame | None = None,
                    mu_override: dict | None = None) -> Inputs:
    hist = returns_through(returns, decision_date)
    win = hist if window_months is None else hist.iloc[-window_months:]
    if window_months is not None and len(win) < window_months:
        raise DataGateError(
            f"only {len(win)} months before {pd.Timestamp(decision_date).date()}, "
            f"{window_months} needed")
    if len(win) < 24:
        raise DataGateError("at least 24 months are needed to estimate a covariance")
    assets = list(win.columns)
    hist_mu = win.mean().to_numpy() * 12.0
    mu = hist_mu.copy()
    cov = win.cov().to_numpy() * 12.0
    signal = None
    if bil_source == "gs2":
        if vintages is None:
            raise DataGateError("bil_source='gs2' needs the GS2 vintages")
        signal = gs2_as_known(vintages, decision_date)
        mu[assets.index("BIL")] = signal.value
    elif bil_source != "history":
        raise ValueError("bil_source must be 'gs2' or 'history'")
    if mu_override:
        for a, val in mu_override.items():
            mu[assets.index(a)] = float(val)
    return Inputs(assets=assets, mu=mu, cov=cov,
                  window_start=win.index[0].strftime("%Y-%m"),
                  window_end=win.index[-1].strftime("%Y-%m"),
                  n_months=len(win), bil_source=bil_source, signal=signal,
                  history_mu=hist_mu)


def validate_cov(cov: np.ndarray) -> None:
    if not np.all(np.isfinite(cov)):
        raise ValueError("covariance has a non-finite value")
    if not np.allclose(cov, cov.T, atol=1e-12):
        raise ValueError("covariance matrix is not symmetric")
    v = np.sqrt(np.diag(cov))
    corr = cov / np.outer(v, v)
    if np.any(np.abs(corr) > 1 + 1e-9):
        raise ValueError("a correlation is outside -1 to 1")
    if np.min(np.linalg.eigvalsh(cov)) < -1e-10:
        raise ValueError("covariance matrix is not positive semidefinite")


def cov_from_corr(vol, corr) -> np.ndarray:
    vol = np.asarray(vol, float)
    corr = np.asarray(corr, float)
    if not np.allclose(corr, corr.T):
        raise ValueError("correlation table is not symmetric")
    if np.any(np.abs(corr) > 1):
        raise ValueError("a correlation is outside -1 to 1")
    return corr * np.outer(vol, vol)


# ---------------------------------------------------------------------------
# 4. Portfolio arithmetic
# ---------------------------------------------------------------------------
def port_return(w, mu, annual_cost: float = 0.0) -> float:
    return float(np.dot(w, mu)) - annual_cost


def port_vol(w, cov) -> float:
    w = np.asarray(w, float)
    return float(math.sqrt(max(w @ cov @ w, 0.0)))


def constant_mix_monthly(hist: pd.DataFrame, w) -> pd.Series:
    """Monthly returns of a mix rebalanced back to w every month."""
    return pd.Series(hist.to_numpy() @ np.asarray(w, float), index=hist.index)


def worst_12m(monthly: pd.Series) -> tuple[float, str]:
    """Lowest compounded 12-month return and the month it ended."""
    if len(monthly) < 12:
        return float("nan"), ""
    lg = np.log1p(monthly.to_numpy())
    roll = np.convolve(lg, np.ones(12), mode="valid")
    i = int(np.argmin(roll))
    return float(np.expm1(roll[i])), monthly.index[i + 11].strftime("%Y-%m")


def worst_12m_matrix(hist: pd.DataFrame, W: np.ndarray) -> np.ndarray:
    """Worst 12-month compounded return for many weight vectors at once."""
    if len(hist) < 12:
        return np.full(W.shape[0], np.nan)
    port = hist.to_numpy() @ W.T                      # T x K monthly returns
    lg = np.log1p(port)
    c = np.vstack([np.zeros(W.shape[0]), np.cumsum(lg, axis=0)])
    roll = c[12:] - c[:-12]                           # (T-11) x K
    return np.expm1(roll.min(axis=0))


def max_drawdown(monthly: pd.Series) -> float:
    wealth = np.cumprod(1 + monthly.to_numpy())
    peak = np.maximum.accumulate(np.concatenate([[1.0], wealth]))[1:]
    return float(np.min(wealth / peak - 1.0))


# ---------------------------------------------------------------------------
# 5. Baselines
# ---------------------------------------------------------------------------
def equal_weight(n: int) -> np.ndarray:
    return np.full(n, 1.0 / n)


def inverse_vol(vol) -> np.ndarray:
    inv = 1.0 / np.asarray(vol, float)
    return inv / inv.sum()


# ---------------------------------------------------------------------------
# 6. Mandate checks and the constrained search
# ---------------------------------------------------------------------------
def reserve_weight(w, assets, mandate: Mandate) -> float:
    return float(sum(w[i] for i, a in enumerate(assets) if a in mandate.reserve_assets))


def check_mandate(w, inputs: Inputs, mandate: Mandate,
                  loss_history: pd.DataFrame | None = None) -> list[dict]:
    """Every rule, its measured value, its limit and pass/FAIL."""
    w = np.asarray(w, float)
    rows = [
        {"rule": "Weights sum to 100%", "value": w.sum(), "limit": 1.0,
         "pass": abs(w.sum() - 1) < 1e-9},
        {"rule": "Long-only (lowest weight >= 0)", "value": w.min(), "limit": 0.0,
         "pass": w.min() >= -TOL},
        {"rule": f"Reserve ({'+'.join(mandate.reserve_assets)}) >= {mandate.reserve_min:.0%}",
         "value": reserve_weight(w, inputs.assets, mandate), "limit": mandate.reserve_min,
         "pass": reserve_weight(w, inputs.assets, mandate) >= mandate.reserve_min - TOL},
        {"rule": f"Modeled net return >= {mandate.target_return:.2%}",
         "value": port_return(w, inputs.mu, mandate.annual_cost),
         "limit": mandate.target_return,
         "pass": port_return(w, inputs.mu, mandate.annual_cost) >= mandate.target_return - TOL},
    ]
    if mandate.loss_limit is not None and loss_history is not None:
        loss, _ = worst_12m(constant_mix_monthly(loss_history, w))
        rows.append({"rule": f"Worst 12-month loss >= {mandate.loss_limit:.0%}",
                     "value": loss, "limit": mandate.loss_limit,
                     "pass": loss >= mandate.loss_limit - TOL})
    return rows


def verdict(rows: list[dict]) -> str:
    failed = [r["rule"] for r in rows if not r["pass"]]
    return "PASS" if not failed else "FAIL: " + "; ".join(failed)


def grid(n: int, step_points: int = 5) -> np.ndarray:
    if 100 % step_points:
        raise ValueError("grid step must divide 100")
    units = 100 // step_points
    out = []

    def rec(prefix, left, k):
        if k == 1:
            out.append(prefix + [left])
            return
        for u in range(left + 1):
            rec(prefix + [u], left - u, k - 1)

    rec([], units, n)
    return np.array(out, dtype=float) / units


@dataclass
class SearchResult:
    feasible: bool
    weights: np.ndarray | None
    exp_return: float | None
    vol: float | None
    worst12: float | None
    worst12_end: str | None
    n_candidates: int
    n_feasible: int
    fallback: bool = False
    note: str = ""


def search(inputs: Inputs, mandate: Mandate, loss_history: pd.DataFrame | None = None,
           allow_fallback: bool = False) -> SearchResult:
    """Lowest-volatility grid mix meeting every mandate rule.
    If no mix meets the return objective within the hard rules (reserve and
    loss limit), returns infeasible - or, when allow_fallback is True (the app,
    the report and the backtest), the highest-return mix that still obeys the
    hard rules, clearly flagged as a fallback ("objective not met")."""
    validate_cov(inputs.cov)
    W = grid(len(inputs.assets), mandate.grid_step)
    rets = W @ inputs.mu - mandate.annual_cost
    vars_ = np.einsum("ij,jk,ik->i", W, inputs.cov, W)
    res_idx = [i for i, a in enumerate(inputs.assets) if a in mandate.reserve_assets]
    reserve = W[:, res_idx].sum(axis=1)
    hard = reserve >= mandate.reserve_min - TOL
    w12 = (worst_12m_matrix(loss_history, W) if loss_history is not None
           else np.full(len(W), np.nan))
    if mandate.loss_limit is not None and loss_history is not None:
        hard &= w12 >= mandate.loss_limit - TOL
    ok = hard & (rets >= mandate.target_return - TOL)
    n_ok = int(ok.sum())
    if n_ok:
        cand = np.where(ok)[0]
        i = cand[np.argmin(vars_[cand])]   # ties keep the first enumerated mix
        return SearchResult(True, W[i], float(rets[i]), float(math.sqrt(vars_[i])),
                            float(w12[i]) if np.isfinite(w12[i]) else None,
                            _w12_end(loss_history, W[i]), len(W), n_ok)
    if allow_fallback and hard.any():
        cand = np.where(hard)[0]
        best = rets[cand].max()
        top = cand[np.abs(rets[cand] - best) < 1e-12]
        i = top[np.argmin(vars_[top])]
        return SearchResult(False, W[i], float(rets[i]), float(math.sqrt(vars_[i])),
                            float(w12[i]) if np.isfinite(w12[i]) else None,
                            _w12_end(loss_history, W[i]), len(W), 0, fallback=True,
                            note="no mix meets the return objective within the hard rules; "
                                 "holding the highest-return mix that obeys them")
    return SearchResult(False, None, None, None, None, None, len(W), 0,
                        note="no mix meets the objective within the mandate")


def _w12_end(loss_history, w):
    if loss_history is None:
        return None
    return worst_12m(constant_mix_monthly(loss_history, w))[1]


def loss_history(prices: pd.DataFrame, decision_date, mandate: Mandate) -> pd.DataFrame:
    """The monthly history the loss screen uses, ending on the decision date."""
    d = pd.Timestamp(decision_date)
    if mandate.loss_screen == "extended":
        x = extended_history(prices)
    elif mandate.loss_screen == "fund":
        x = monthly_returns(prices)
    else:
        raise ValueError("loss_screen must be 'extended' or 'fund'")
    return x[x.index <= d]


# ---------------------------------------------------------------------------
# 7. One decision at one date (what the committee sees)
# ---------------------------------------------------------------------------
WINDOWS = {"36 months": 36, "60 months (base)": 60, "120 months": 120, "All history": None}


@dataclass
class Decision:
    decision_date: str
    inputs: Inputs
    mandate: Mandate
    result: SearchResult
    baselines: dict = field(default_factory=dict)
    loss_history_months: int = 0


def decide(prices: pd.DataFrame, vintages: pd.DataFrame, decision_date,
           mandate: Mandate = MAPLE, window_months: int | None = 60,
           bil_source: str = "gs2", mu_override: dict | None = None) -> Decision:
    r = monthly_returns(prices)
    inputs = estimate_inputs(r, decision_date, window_months, bil_source, vintages, mu_override)
    loss_hist = loss_history(prices, decision_date, mandate)
    res = search(inputs, mandate, loss_hist, allow_fallback=True)
    base = {}
    for name, w in [("Equal weight", equal_weight(len(inputs.assets))),
                    ("Inverse volatility", inverse_vol(inputs.vol)),
                    ("Benchmark 60% VT / 40% LQD", mandate.benchmark_weights(inputs.assets))]:
        rows = check_mandate(w, inputs, mandate, loss_hist)
        base[name] = {"weights": w, "exp_return": port_return(w, inputs.mu, mandate.annual_cost),
                      "vol": port_vol(w, inputs.cov),
                      "worst12": worst_12m(constant_mix_monthly(loss_hist, w))[0],
                      "rules": rows, "verdict": verdict(rows)}
    if res.weights is not None:
        rows = check_mandate(res.weights, inputs, mandate, loss_hist)
        base["Maple process" + (" (closest compliant mix)" if res.fallback else "")] = {
            "weights": res.weights, "exp_return": res.exp_return, "vol": res.vol,
            "worst12": res.worst12, "rules": rows, "verdict": verdict(rows)}
    return Decision(pd.Timestamp(decision_date).date().isoformat(), inputs, mandate, res, base,
                    len(loss_hist))


def stability(prices, vintages, decision_date, mandate=MAPLE, bil_source="gs2",
              windows: dict = WINDOWS, mu_shift: dict | None = None) -> tuple[pd.DataFrame, float]:
    """The same decision on each estimation window (with the same expected-return
    shifts, if any); the largest weight move (percentage points) between windows."""
    rows, ws = [], []
    for label, m in windows.items():
        try:
            d = run_scenario(prices, vintages, decision_date, mandate, m, bil_source, mu_shift)
        except DataGateError:
            rows.append({"window": label, "months": "not enough history", "feasible": None,
                         "fallback": None})
            continue
        rr = d.result
        row = {"window": label, "months": f"{d.inputs.window_start} to {d.inputs.window_end}",
               "feasible": rr.feasible, "fallback": rr.fallback}
        for i, a in enumerate(d.inputs.assets):
            row[a] = None if rr.weights is None else round(rr.weights[i] * 100, 1)
        row["exp_return"] = rr.exp_return
        row["vol"] = rr.vol
        row["worst12"] = rr.worst12
        row["VT_mu"] = d.inputs.mu[d.inputs.assets.index("VT")]
        rows.append(row)
        if rr.weights is not None:
            ws.append(rr.weights)
    spread = 0.0
    for i in range(len(ws)):
        for j in range(i + 1, len(ws)):
            spread = max(spread, float(np.max(np.abs(ws[i] - ws[j]))) * 100)
    return pd.DataFrame(rows), spread


def recommendation(decision: Decision, spread_pts: float) -> tuple[str, str]:
    """The decision ladder:
    ALLOCATE  - a mix meets every rule and moves <= the stability limit across windows;
    PILOT     - a mix meets every rule but is unstable, OR no mix meets the return
                objective and the closest mix that obeys the hard rules is piloted
                while the committee re-sets the objective;
    REJECT    - not even the hard rules (reserve, loss limit) can be met."""
    m, res = decision.mandate, decision.result
    if res.weights is None:
        return ("REJECT", "No mix satisfies even the reserve and loss rules.")
    if res.fallback:
        return ("PILOT (objective not met)",
                f"No mix reaches the {m.target_return:.2%} objective inside the reserve and "
                f"loss rules. Closest compliant mix: {fmt_w(res.weights)} at "
                f"{res.exp_return:.2%}. The committee must choose: lower the objective or "
                f"loosen the loss limit. The app will not do either quietly.")
    if spread_pts > m.stability_limit_pts:
        return ("PILOT", f"Meets every rule, but moves {spread_pts:.0f} points across "
                f"estimation windows (adopt limit {m.stability_limit_pts:.0f}).")
    return ("ALLOCATE", f"Meets every rule and moves at most {spread_pts:.0f} points across "
            f"windows (limit {m.stability_limit_pts:.0f}).")

# ---------------------------------------------------------------------------
# 8. Walk-forward backtest: decide each 30 September with only what was
#    known then, hold 12 months (weights drift), pay costs, repeat.
# ---------------------------------------------------------------------------
@dataclass
class Backtest:
    yearly: pd.DataFrame
    monthly: pd.DataFrame        # net monthly returns per strategy
    metrics: pd.DataFrame


def _hold_year(r_year: pd.DataFrame, w0: np.ndarray, annual_cost: float):
    """Buy-and-hold for the year: weights drift with returns; fee accrues monthly."""
    w = w0.copy()
    out = []
    for _, row in r_year.iterrows():
        rv = row.to_numpy()
        gross = float(w @ rv)
        out.append(gross - annual_cost / 12.0)
        w = w * (1 + rv) / (1 + gross)
    return out, w


def backtest(prices, vintages, mandate: Mandate = MAPLE, first_year: int = 2013,
             last_year: int = 2025, window_months: int | None = 60) -> Backtest:
    r = monthly_returns(prices)
    strategies = ["Maple process (GS2 signal)", "Same process, history-only cash estimate",
                  "Equal weight", "Inverse volatility", "Benchmark 60% VT / 40% LQD"]
    drift = {s: None for s in strategies}
    monthly = {s: [] for s in strategies}
    idx = []
    yearly = []
    for y in range(first_year, last_year + 1):
        d = pd.Timestamp(f"{y}-09-30")
        nxt = r[(r.index > d) & (r.index <= pd.Timestamp(f"{y + 1}-09-30"))]
        if len(nxt) == 0:
            break
        loss_hist = loss_history(prices, d, mandate)
        inp_sig = estimate_inputs(r, d, window_months, "gs2", vintages)
        inp_his = estimate_inputs(r, d, window_months, "history", vintages)
        res_sig = search(inp_sig, mandate, loss_hist, allow_fallback=True)
        res_his = search(inp_his, mandate, loss_hist, allow_fallback=True)
        targets = {
            strategies[0]: res_sig.weights, strategies[1]: res_his.weights,
            strategies[2]: equal_weight(len(TICKERS)), strategies[3]: inverse_vol(inp_sig.vol),
            strategies[4]: mandate.benchmark_weights(inp_sig.assets),
        }
        info = {"decision_date": d.date().isoformat(),
                "GS2_known": inp_sig.signal.value, "GS2_month": inp_sig.signal.month_measured,
                "BIL_trailing_mean": inp_sig.history_mu[0],
                "BIL_next_12m": float(np.prod(1 + nxt["BIL"].to_numpy()) - 1),
                "feasible": res_sig.feasible, "history_only_feasible": res_his.feasible}
        for i, a in enumerate(TICKERS):
            info[a] = res_sig.weights[i]
        for s in strategies:
            w0 = targets[s]
            turnover = float(np.abs(w0 - drift[s]).sum()) if drift[s] is not None else float(np.abs(w0).sum())
            cost = turnover * mandate.trading_cost
            rets, drift[s] = _hold_year(nxt, w0, mandate.annual_cost)
            rets[0] -= cost
            monthly[s].extend(rets)
            if s == strategies[0]:
                info["turnover"] = turnover
                info["process_next_12m"] = float(np.prod(1 + np.array(rets)) - 1)
            if s == strategies[1]:
                info["history_only_VT"] = w0[3]
        idx.extend(list(nxt.index))
        yearly.append(info)
    mdf = pd.DataFrame(monthly, index=pd.DatetimeIndex(idx))
    return Backtest(pd.DataFrame(yearly), mdf, performance_table(mdf, mandate))


def performance_table(mdf: pd.DataFrame, mandate: Mandate = MAPLE) -> pd.DataFrame:
    rows = []
    for s in mdf.columns:
        x = mdf[s]
        n = len(x)
        ann = float(np.prod(1 + x.to_numpy()) ** (12 / n) - 1)
        vol = float(x.std(ddof=1) * math.sqrt(12))
        w12, w12_end = worst_12m(x)
        lg = np.log1p(x.to_numpy())
        roll = np.expm1(np.convolve(lg, np.ones(12), mode="valid"))
        rows.append({"strategy": s, "months": n, "annual_return": ann, "volatility": vol,
                     "max_drawdown": max_drawdown(x), "worst_12m": w12, "worst_12m_end": w12_end,
                     "share_12m_windows_meeting_target": float(np.mean(roll >= mandate.target_return)),
                     "share_12m_windows_breaching_loss_limit": float(np.mean(roll < (mandate.loss_limit or -1)))})
    return pd.DataFrame(rows)


def fmt_w(w, assets=TICKERS) -> str:
    return " / ".join(f"{x * 100:.0f}" for x in w)


def as_of_today() -> str:
    return date.today().isoformat()


# ---------------------------------------------------------------------------
# 9. Stress run at one decision date: estimates, window, costs, constraints
# ---------------------------------------------------------------------------
PROXY_CSV = ROOT / "data" / "stress_proxy_2007_2010.csv"
PROXY_US_WEIGHT = 0.40   # VT proxy = 40% VTSMX + 60% VGTSX (lowest tracking error
                         # vs VT over Jul-2008 to Dec-2010: 2.3% a year, corr 0.996)


def extended_history(prices: pd.DataFrame) -> pd.DataFrame:
    """Monthly returns from Jun-2007, with VT before its Jun-2008 launch replaced
    by the proxy. Used ONLY for the extended loss stress, never for estimates."""
    p = pd.read_csv(PROXY_CSV).set_index("month")
    pr = p / p.shift(1) - 1
    pre = pr.loc["2007-06":"2008-06"].copy()
    pre["VT"] = PROXY_US_WEIGHT * pre["VTSMX"] + (1 - PROXY_US_WEIGHT) * pre["VGTSX"]
    pre = pre[TICKERS]
    pre.index = pd.PeriodIndex(pre.index, freq="M").to_timestamp("M")
    actual = monthly_returns(prices)
    actual = actual.copy()
    actual.index = actual.index.to_period("M").to_timestamp("M")
    return pd.concat([pre, actual])


def all_worst_at_once(prices, decision_date, w, mandate: Mandate = MAPLE) -> tuple[float, dict]:
    """Hypothetical stress, reported but not a hard rule: every fund suffers its own
    worst 12-month return of the loss-screen history AT THE SAME TIME (e.g. stocks
    as in 2008 and bonds as in 2022). Returns the mix's loss and each fund's shock."""
    hist = loss_history(prices, decision_date, mandate)
    shocks = {a: worst_12m(hist[a])[0] for a in hist.columns}
    loss = float(sum(w[i] * shocks[a] for i, a in enumerate(hist.columns)))
    return loss, shocks


def break_even(decision: Decision) -> dict:
    """How far each estimate can move before the chosen mix fails the objective."""
    w, inp, m = decision.result.weights, decision.inputs, decision.mandate
    if w is None:
        return {}
    margin = port_return(w, inp.mu, m.annual_cost) - m.target_return
    out = {"margin_pts": margin * 100}
    for i, a in enumerate(inp.assets):
        if w[i] > 0:
            out[f"{a}_breakeven"] = inp.mu[i] - margin / w[i]
    return out


def run_scenario(prices, vintages, decision_date, mandate=MAPLE, window_months=60,
                 bil_source="gs2", mu_shift: dict | None = None) -> Decision:
    r = monthly_returns(prices)
    base_inp = estimate_inputs(r, decision_date, window_months, bil_source, vintages)
    override = None
    if mu_shift:
        override = {a: base_inp.mu[base_inp.assets.index(a)] + s for a, s in mu_shift.items()}
    return decide(prices, vintages, decision_date, mandate, window_months, bil_source, override)


def stress_suite(prices, vintages, decision_date) -> pd.DataFrame:
    base = run_scenario(prices, vintages, decision_date)
    bw = base.result.weights
    scen = [
        ("Base case", "-", {}),
        ("Estimates", "VT expected return -1 point", {"mu_shift": {"VT": -0.01}}),
        ("Estimates", "VT expected return -3 points", {"mu_shift": {"VT": -0.03}}),
        ("Estimates", "BIL (GS2 signal) -1 point: cash rates fall", {"mu_shift": {"BIL": -0.01}}),
        ("Estimates", "Signal off: BIL from 60-month history", {"bil_source": "history"}),
        ("Estimates", "IEF and LQD +6 points (to 4.2% / 5.2%; yield-like, see memo)",
         {"mu_shift": {"IEF": 0.06, "LQD": 0.06}}),
        ("Window", "Last 36 months", {"window_months": 36}),
        ("Window", "Last 120 months", {"window_months": 120}),
        ("Window", "All history since Jul-2008", {"window_months": None}),
        ("Costs", "Annual cost 10 -> 35 bp", {"mandate": replace(MAPLE, annual_cost_bps=35)}),
        ("Costs", "Annual cost 10 -> 75 bp", {"mandate": replace(MAPLE, annual_cost_bps=75)}),
        ("Constraints", "Reserve minimum 10% -> 20%", {"mandate": replace(MAPLE, reserve_min=0.20)}),
        ("Constraints", "Loss limit -15% -> -20% (looser)", {"mandate": replace(MAPLE, loss_limit=-0.20)}),
        ("Constraints", "Loss limit removed", {"mandate": replace(MAPLE, loss_limit=None)}),
        ("Data window", "Loss screen on fund prices only (VT from Jul-2008)",
         {"mandate": replace(MAPLE, loss_screen="fund")}),
        ("Constraints", "Grid 5 -> 10 points (coarser)", {"mandate": replace(MAPLE, grid_step=10)}),
    ]
    rows = []
    for group, label, kw in scen:
        d = run_scenario(prices, vintages, decision_date, **kw)
        res = d.result
        row = {"group": group, "change": label, "meets_objective": res.feasible}
        for i, a in enumerate(d.inputs.assets):
            row[a] = None if res.weights is None else res.weights[i] * 100
        row["exp_return"] = res.exp_return
        row["vol"] = res.vol
        row["worst12"] = res.worst12
        row["largest_move_pts"] = (None if res.weights is None
                                   else float(np.max(np.abs(res.weights - bw))) * 100)
        rows.append(row)
    return pd.DataFrame(rows)


def tradeoff(prices, vintages, decision_date, mandate: Mandate = MAPLE,
             limits=(-0.10, -0.125, -0.15, -0.175, -0.20, -0.25)) -> pd.DataFrame:
    """For each loss limit, the highest modeled net return any grid mix can reach
    while keeping the reserve and that limit. This is the committee's menu:
    it shows what each extra point of tolerated loss buys in expected return."""
    rows = []
    for L in limits:
        m = replace(mandate, loss_limit=L, target_return=10.0)   # unreachable target ->
        d = decide(prices, vintages, decision_date, m)            # search returns the
        res = d.result                                            # highest-return mix
        row = {"loss_limit": L}
        for i, a in enumerate(d.inputs.assets):
            row[a] = None if res.weights is None else res.weights[i] * 100
        row["max_exp_return"] = res.exp_return
        row["vol"] = res.vol
        row["worst12"] = res.worst12
        row["meets_objective"] = (res.exp_return is not None and
                                  res.exp_return >= mandate.target_return - TOL)
        rows.append(row)
    return pd.DataFrame(rows)
