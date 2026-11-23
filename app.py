"""
app.py - the Maple Education Fund allocation review, as a web app.

Run from the repository folder:
    python -m pip install -r requirements.txt
    python -m streamlit run app.py

The app holds no finance math of its own: every number comes from engine.py.
"""
from dataclasses import replace

import numpy as np
import pandas as pd
import streamlit as st

import engine as e

st.set_page_config(page_title="Maple Education Fund - Allocation Review", layout="wide")

AI_LINE = ("**AI disclosure:** built with AI assistance (Anthropic Claude for code, data "
           "retrieval and drafting; see docs/validation-and-ai-use.md). The analysis and the "
           "decision are Shrey Goyal's. **Education, not investment advice.**")


# ------------------------------------------------------------------ data (cached)
@st.cache_data
def load():
    p = e.load_prices()
    v = e.load_gs2_vintages()
    return p, v


@st.cache_data
def run_decision(date, target, reserve, loss, cost, step, stab, screen, window, bil_src, shifts):
    p, v = load()
    m = e.Mandate(target_return=target, reserve_min=reserve, loss_limit=loss,
                  annual_cost_bps=cost, grid_step=step, stability_limit_pts=stab, loss_screen=screen)
    d = e.run_scenario(p, v, date, m, window, bil_src, dict(shifts) or None)
    st_tab, spread = e.stability(p, v, date, m, bil_src, mu_shift=dict(shifts) or None)
    return d, st_tab, spread, m


@st.cache_data
def run_tradeoff(date, target, reserve, cost, step, screen):
    p, v = load()
    m = e.Mandate(target_return=target, reserve_min=reserve, annual_cost_bps=cost,
                  grid_step=step, loss_screen=screen)
    return e.tradeoff(p, v, date, m)


@st.cache_data
def run_stress(date):
    p, v = load()
    return e.stress_suite(p, v, date)


@st.cache_data
def run_backtest(target, reserve, loss, cost, tcost, step, screen):
    p, v = load()
    m = e.Mandate(target_return=target, reserve_min=reserve, loss_limit=loss, annual_cost_bps=cost,
                  trading_cost_bps=tcost, grid_step=step, loss_screen=screen)
    return e.backtest(p, v, m)


prices, vintages = load()
decision_dates = [d.date().isoformat() for d in vintages["vintage_date"]
                  if d.month == 9 and d.year >= 2013]

# ------------------------------------------------------------------ sidebar
st.sidebar.header("Decision")
date = st.sidebar.selectbox("Annual review date (as of)", decision_dates,
                            index=len(decision_dates) - 1,
                            help="Only dates with an archived GS2 vintage are offered: the app "
                                 "refuses to pretend an older reading is current.")
st.sidebar.header("Mandate (Maple Education Fund)")
target = st.sidebar.number_input("Return objective, modeled net (% a year)", 0.0, 15.0, 6.5, 0.25) / 100
reserve = st.sidebar.number_input("Reserve minimum in BIL (%)", 0.0, 100.0, 10.0, 5.0) / 100
use_loss = st.sidebar.checkbox("Apply the worst 12-month loss limit", True)
loss = (st.sidebar.number_input("Worst 12-month loss limit (%)", -60.0, 0.0, -15.0, 2.5) / 100
        if use_loss else None)
screen = st.sidebar.radio("Loss screen history",
                          ["extended", "fund"], index=0,
                          format_func=lambda s: {"extended": "Full 2008 crisis (Jun-2007 on; VT proxy "
                                                 "before its Jun-2008 launch)",
                                                 "fund": "Fund prices only (VT from Jul-2008)"}[s])
cost = st.sidebar.number_input("Annual cost (bp)", 0.0, 300.0, 10.0, 5.0)
step = st.sidebar.selectbox("Weight grid (points)", [5, 10, 20, 25], index=0)
stab = st.sidebar.number_input("Stability limit to adopt (points)", 0.0, 100.0, 20.0, 5.0)

st.sidebar.header("Estimates")
window_label = st.sidebar.selectbox("Estimation window", list(e.WINDOWS), index=1)
window = e.WINDOWS[window_label]
bil_src = st.sidebar.radio("BIL expected return", ["gs2", "history"],
                           format_func=lambda s: {"gs2": "GS2 as known on the review date (signal)",
                                                  "history": "Trailing average of BIL returns"}[s])
st.sidebar.caption("Shift any fund's expected return (percentage points):")
shifts = []
for t in e.TICKERS:
    s = st.sidebar.number_input(f"{t} shift (pts)", -10.0, 10.0, 0.0, 0.5, key=f"shift_{t}")
    if s:
        shifts.append((t, s / 100))
shifts = tuple(shifts)

# ------------------------------------------------------------------ header
st.title("Maple Education Fund - Annual Allocation Review")
st.markdown(AI_LINE)
st.caption("Client: Maple Education Fund, a fictional $1,000,000 scholarship reserve (course case). "
           "Seven-year horizon, reviewed every 30 September. Universe: BIL, IEF, LQD, VT. "
           f"Prices: Yahoo Finance Adj Close, retrieved 2026-11-19, last month 2026-10. "
           f"GS2: ALFRED vintages, retrieved 2026-11-19.")

try:
    d, stab_tab, spread, m = run_decision(date, target, reserve, loss, cost, step, stab, screen,
                                          window, bil_src, shifts)
except e.DataGateError as err:
    st.error(f"Data gate stopped the run: {err}")
    st.stop()
except ValueError as err:
    st.error(f"Input refused: {err}")
    st.stop()

verb, why = e.recommendation(d, spread)
res = d.result
colour = {"ALLOCATE": "green", "PILOT": "orange", "REJECT": "red"}.get(verb.split()[0], "orange")
st.markdown(f"### Recommendation as of {date}: :{colour}[{verb}]")
st.write(why)

tabs = st.tabs(["Decision", "Objective vs loss", "Stress run", "Walk-forward test", "Data card"])

# ------------------------------------------------------------------ tab 1
with tabs[0]:
    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.subheader("The process's allocation")
        if res.weights is None:
            st.error(res.note)
        else:
            if res.fallback:
                st.warning("No mix meets the return objective inside the hard rules. Shown: the "
                           "highest-return mix that still obeys the reserve and loss rules.")
            alloc = pd.DataFrame({
                "Fund": [f"{t} - {e.FUND_NAMES[t]}" for t in e.TICKERS],
                "Weight": [f"{w * 100:.0f}%" for w in res.weights],
                "Dollars on $1,000,000": [f"${w * 1_000_000:,.0f}" for w in res.weights]})
            st.dataframe(alloc, hide_index=True, width="stretch")
            k1, k2, k3 = st.columns(3)
            k1.metric("Modeled net return", f"{res.exp_return:.2%}",
                      f"{(res.exp_return - m.target_return) * 100:+.2f} pts vs objective")
            k2.metric("Volatility (ex-ante)", f"{res.vol:.2%}")
            k3.metric("Worst 12-month loss", f"{res.worst12:.1%}")
            st.caption(f"Worst 12 months ended {res.worst12_end}; history from "
                       f"{'Jun-2007 (VT proxy before its launch)' if m.loss_screen == 'extended' else 'Jul-2008'}.")
            aw, _ = e.all_worst_at_once(prices, date, res.weights, m)
            st.caption(f"All-worst-at-once stress (each fund's own worst 12 months at the same "
                       f"time, e.g. 2008 stocks with 2022 bonds): **{aw:.1%}**. Reported, not a rule; "
                       f"it must pass before bonds enter the mix.")
    with c2:
        st.subheader("Point-in-time signal")
        sig = d.inputs.signal
        if sig:
            st.markdown(f"**GS2 = {sig.value:.2%}** (2-year Treasury yield, month measured "
                        f"**{sig.month_measured}**, read from the ALFRED vintage dated "
                        f"**{sig.vintage_date}**). Used as BIL's expected return. The September "
                        f"value is not published until early October, so it is not used.")
        else:
            st.markdown("Signal switched off: BIL's expected return is its trailing average.")
        st.markdown(f"Estimates use **{d.inputs.n_months} months**, "
                    f"{d.inputs.window_start} to {d.inputs.window_end}.")
        est = pd.DataFrame({"Fund": d.inputs.assets,
                            "Expected return": [f"{x:.2%}" for x in d.inputs.mu],
                            "Trailing average": [f"{x:.2%}" for x in d.inputs.history_mu],
                            "Volatility": [f"{x:.2%}" for x in d.inputs.vol]})
        st.dataframe(est, hide_index=True, width="stretch")

    st.subheader("Mandate verdicts: two baselines, the benchmark and the process")
    rows = []
    for name, b in d.baselines.items():
        rows.append({"Portfolio": name, "BIL / IEF / LQD / VT (%)": e.fmt_w(b["weights"]),
                     "Modeled net return": f"{b['exp_return']:.2%}", "Volatility": f"{b['vol']:.2%}",
                     "Worst 12m": f"{b['worst12']:.1%}", "Verdict": b["verdict"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    with st.expander("Every rule, every portfolio"):
        for name, b in d.baselines.items():
            st.markdown(f"**{name}**")
            st.dataframe(pd.DataFrame([{"Rule": r["rule"], "Measured": f"{r['value']:.4f}",
                                        "Limit": f"{r['limit']:.4f}",
                                        "Result": "pass" if r["pass"] else "FAIL"}
                                       for r in b["rules"]]), hide_index=True)

    be = e.break_even(d)
    if be:
        st.subheader("Monitoring triggers from the model")
        lines = [f"Margin over the objective: **{be['margin_pts']:+.2f} points**."]
        if "BIL_breakeven" in be:
            lines.append(f"The mix meets the objective only while BIL's expected return (GS2) is at "
                         f"least **{be['BIL_breakeven']:.2%}**.")
        if "VT_breakeven" in be:
            lines.append(f"... and VT's expected return is at least **{be['VT_breakeven']:.2%}**.")
        st.markdown(" ".join(lines))

# ------------------------------------------------------------------ tab 2
with tabs[1]:
    st.subheader("What each point of tolerated loss buys")
    st.write("For each loss limit, the highest modeled net return any mix can reach while keeping "
             "the reserve. The committee picks a row; the app does not pick it for them.")
    tr = run_tradeoff(date, target, reserve, cost, step, screen)
    show = tr.copy()
    show["loss_limit"] = show["loss_limit"].map(lambda x: f"{x:.1%}")
    for c in ["max_exp_return", "vol", "worst12"]:
        show[c] = show[c].map(lambda x: f"{x:.2%}")
    show = show.rename(columns={"loss_limit": "Loss limit", "max_exp_return": "Best modeled return",
                                "vol": "Volatility", "worst12": "Worst 12m",
                                "meets_objective": f"Meets {target:.2%}?"})
    st.dataframe(show, hide_index=True, width="stretch")
    st.line_chart(tr.assign(limit=-tr["loss_limit"] * 100).set_index("limit")["max_exp_return"] * 100,
                  x_label="Loss tolerated in the worst 12 months (%)",
                  y_label="Best modeled net return (%)")

# ------------------------------------------------------------------ tab 3
with tabs[2]:
    st.subheader("Window: the same decision on four estimation windows")
    s = stab_tab.copy()
    for c in ["exp_return", "vol", "worst12", "VT_mu"]:
        s[c] = s[c].map(lambda x: "-" if pd.isna(x) else f"{x:.2%}")
    s = s.rename(columns={"window": "Window", "months": "Months", "feasible": "Meets objective",
                          "fallback": "Closest compliant mix", "exp_return": "Modeled return",
                          "vol": "Volatility", "worst12": "Worst 12m", "VT_mu": "VT estimate"})
    st.dataframe(s, hide_index=True, width="stretch")
    st.markdown(f"Largest weight move across windows: **{spread:.0f} points** "
                f"(adopt only if at most {m.stability_limit_pts:.0f}).")
    st.subheader("Stress run at the base mandate (estimates, window, costs, constraints)")
    st.caption("Computed for the 30-Sep-2026 review with the base mandate, whatever the sidebar says.")
    ss = run_stress("2026-09-30").copy()
    for c in ["exp_return", "vol", "worst12"]:
        ss[c] = ss[c].map(lambda x: "-" if pd.isna(x) else f"{x:.2%}")
    ss = ss.rename(columns={"group": "Group", "change": "Change", "meets_objective": "Meets objective",
                            "exp_return": "Modeled return", "vol": "Volatility", "worst12": "Worst 12m",
                            "largest_move_pts": "Largest move vs base (pts)"})
    st.dataframe(ss, hide_index=True, width="stretch")
    st.subheader("The conditions that stop the process")
    st.markdown(
        "1. **No mix meets the objective inside the reserve and loss rules** - no new target "
        "weights; the committee must re-set the objective or the loss limit.\n"
        "2. **Data gate fails** - a missing GS2 vintage for the review date, a missing or "
        "non-consecutive month, or an unexplained sanity flag: no rebalance until fixed.\n"
        "3. **Weights move more than the stability limit across windows** - pilot only, never adopt.\n"
        "4. **The fund's realised 12-month loss passes the loss limit** - immediate committee review.\n"
        "5. **IEF or LQD enters the allocation** - the mix must also pass the all-worst-at-once "
        "stress (each fund's own worst 12 months together) before trading; the walk-forward test's one "
        "loss-limit breach came from stocks and bonds falling together in 2022.")

# ------------------------------------------------------------------ tab 4
with tabs[3]:
    st.subheader("Walk-forward test, Oct-2013 to Sep-2026")
    st.write("Each 30 September from 2013 to 2025 the process decides with only the prices and the "
             "GS2 vintage known that day, holds for 12 months (weights drift), pays the annual and "
             "trading costs, and repeats. Baselines get the same costs and annual rebalancing.")
    bt = run_backtest(target, reserve, loss, cost, 10.0, step, screen)
    met = bt.metrics.copy()
    for c in ["annual_return", "volatility", "max_drawdown", "worst_12m",
              "share_12m_windows_meeting_target", "share_12m_windows_breaching_loss_limit"]:
        met[c] = met[c].map(lambda x: f"{x:.2%}")
    met = met.rename(columns={"strategy": "Strategy", "months": "Months", "annual_return": "Annual return",
                              "volatility": "Volatility", "max_drawdown": "Max drawdown",
                              "worst_12m": "Worst 12m", "worst_12m_end": "Worst 12m ended",
                              "share_12m_windows_meeting_target": "12m windows meeting objective",
                              "share_12m_windows_breaching_loss_limit": "12m windows past loss limit"})
    st.dataframe(met, hide_index=True, width="stretch")
    growth = (1 + bt.monthly).cumprod()
    st.line_chart(growth, y_label="Growth of $1, net of costs",
                  color=["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"])
    yr = bt.yearly.copy()
    for c in ["GS2_known", "BIL_trailing_mean", "BIL_next_12m", "turnover", "process_next_12m",
              "history_only_VT", *e.TICKERS]:
        yr[c] = yr[c].map(lambda x: f"{x:.2%}")
    yr = yr.rename(columns={"decision_date": "Review", "GS2_known": "GS2 known",
                            "GS2_month": "GS2 month", "BIL_trailing_mean": "BIL trailing avg",
                            "BIL_next_12m": "BIL next 12m", "feasible": "Meets objective",
                            "history_only_feasible": "Meets (history-only)",
                            "turnover": "Turnover", "process_next_12m": "Process next 12m",
                            "history_only_VT": "VT (history-only)"})
    st.dataframe(yr, hide_index=True, width="stretch")
    err_sig = (bt.yearly.BIL_next_12m - bt.yearly.GS2_known).abs().mean()
    err_his = (bt.yearly.BIL_next_12m - bt.yearly.BIL_trailing_mean).abs().mean()
    st.markdown(f"**Does the signal earn its place?** As a forecast of BIL's next-12-month "
                f"return, GS2 missed by **{err_sig:.2%}** on average; the trailing average missed "
                f"by **{err_his:.2%}**.")

# ------------------------------------------------------------------ tab 5
with tabs[4]:
    st.subheader("Data card")
    st.markdown(
        "| Field | Prices | Signal (GS2) |\n|---|---|---|\n"
        "| Source | Yahoo Finance chart API, Adj Close | ALFRED / FRED, Federal Reserve Bank of St. Louis (Fed H.15) |\n"
        "| Measures | Month-end price incl. distributions | 2-year Treasury constant-maturity yield, monthly average, % |\n"
        "| Coverage | 2008-06-30 to 2026-10-30, 221 month-ends | One vintage per 30 September, 2009-2026 |\n"
        "| Publication lag | Prices final at the close | About 2 days after month-end; Sept value unknown on 30 Sept |\n"
        "| Revisions | Adj Close levels re-based at each distribution; returns unchanged | 0 revised values in every vintage vs 2026-11-19 |\n"
        "| Retrieved | 2026-11-19 | 2026-11-19 |\n"
        "| Full card | docs/data-card.md | docs/data-card.md |")
    flags = e.sanity_flags(prices)
    st.markdown("**Sanity gate flags (kept, investigated):**")
    st.dataframe(pd.DataFrame(flags), hide_index=True)
    st.caption("Both VT flags: the daily price path moves inside the month and returns to the same "
               "closing price (75.16 and 102.88). Checked against the daily data; kept.")
    st.line_chart(prices / prices.iloc[0], y_label="Adj Close, Jun-2008 = 1")

st.divider()
st.caption("Data: Yahoo Finance (prices); FRED/ALFRED, Federal Reserve Bank of St. Louis (GS2). "
           "Built with AI help; a learning demonstration, not investment advice.")
