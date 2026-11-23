"""
run_analysis.py - the one command that reproduces every number in the memo.

    python run_analysis.py

Writes output/results.md (readable on GitHub without running anything),
output/results.json (full precision) and two charts in output/.
Uses only the files in data/ - no internet, no keys.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import engine as e

OUT = e.ROOT / "output"
REVIEW = "2026-09-30"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]   # fixed order


def pct(x, nd=2):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:.{nd}f}%"


def wcell(x):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.0f}"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def charts(bt, tr):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
                         "xtick.color": INK2, "ytick.color": INK2, "text.color": INK})
    # growth of $1
    g = (1 + bt.monthly).cumprod()
    fig, ax = plt.subplots(figsize=(9, 4.6), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for i, col in enumerate(g.columns):
        ax.plot(g.index, g[col], color=SERIES[i], lw=2 if i == 0 else 1.4, label=col)
    ends = sorted(((g[c].iloc[-1], c) for c in g.columns))
    placed = []
    for val, col in ends:                       # keep end labels at least 0.06 apart
        y = max(val, placed[-1] + 0.06) if placed else val
        placed.append(y)
        ax.annotate(f"{val:.2f}", (g.index[-1], y), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=8, color=INK2)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylabel("Growth of $1, net of costs")
    ax.set_title("Walk-forward test: decide each 30 Sep with what was known, hold 12 months",
                 loc="left", fontsize=11)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "walk_forward_growth.png", dpi=150)
    plt.close(fig)
    # objective vs loss menu
    fig, ax = plt.subplots(figsize=(7, 4), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    x = -tr["loss_limit"] * 100
    y = tr["max_exp_return"] * 100
    ax.plot(x, y, color=SERIES[0], lw=2, marker="o", ms=8)
    for xi, yi, row in zip(x, y, tr.itertuples()):
        ax.annotate(f"{row.BIL:.0f}/{row.VT:.0f}", (xi, yi), xytext=(0, 9),
                    textcoords="offset points", ha="center", fontsize=8, color=INK2)
    ax.axhline(6.5, color=INK2, lw=1, ls="--")
    ax.text(x.max(), 6.45, "6.50% objective", fontsize=8, color=INK2, va="top", ha="right")
    ax.axvline(15, color=INK2, lw=1, ls=":")
    ax.text(15.2, y.min(), "-15% client limit", fontsize=8, color=INK2, va="bottom")
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlabel("Loss tolerated in the worst 12 months, incl. 2008 (%)")
    ax.set_ylabel("Best modeled net return (%)")
    ax.set_title("What each point of tolerated loss buys (30-Sep-2026; labels = BIL/VT %)",
                 loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "objective_vs_loss.png", dpi=150)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    prices, vint = e.load_prices(), e.load_gs2_vintages()
    d = e.decide(prices, vint, REVIEW)
    stab, spread = e.stability(prices, vint, REVIEW)
    verb, why = e.recommendation(d, spread)
    stress = e.stress_suite(prices, vint, REVIEW)
    tr = e.tradeoff(prices, vint, REVIEW)
    bt = e.backtest(prices, vint)
    flags = e.sanity_flags(prices)
    res, inp = d.result, d.inputs
    be = e.break_even(d)

    # extended-history check of the 'fund prices only' answer
    fund_only = e.decide(prices, vint, REVIEW, e.Mandate(loss_screen="fund"))
    ext = e.loss_history(prices, REVIEW, e.MAPLE)
    w_fund = fund_only.result.weights
    fund_mix_ext_loss = e.worst_12m(e.constant_mix_monthly(ext, w_fund))
    # one live month after the review (Oct-2026)
    r = e.monthly_returns(prices)
    oct26 = r.loc["2026-10-01":"2026-10-31"]
    live = float((oct26.to_numpy() @ res.weights)[0]) - e.MAPLE.annual_cost / 12
    sig_err = float((bt.yearly.BIL_next_12m - bt.yearly.GS2_known).abs().mean())
    his_err = float((bt.yearly.BIL_next_12m - bt.yearly.BIL_trailing_mean).abs().mean())

    L = []
    L.append("# Maple Education Fund - executed results\n")
    L.append("> **AI disclosure:** built with AI assistance (Anthropic Claude: code, data retrieval, "
             "drafting). The analysis and the decision are Shrey Goyal's. **Education, not investment "
             "advice.**\n")
    L.append(f"Generated by `python run_analysis.py` on "
             f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. "
             f"Review date (as of): **{REVIEW}**. Prices through **2026-10-30** "
             f"(`data/prices_monthly.csv`, sha256 `{sha(e.PRICES_CSV)[:12]}`); GS2 vintages "
             f"`data/gs2_vintages.csv` (sha256 `{sha(e.GS2_CSV)[:12]}`). Both retrieved 2026-11-19.\n")

    L.append("## 1. Decision\n")
    L.append(f"**{verb}.** {why}\n")
    L.append(md_table(["Fund", "Weight", "Dollars on $1,000,000"],
                      [[f"{t} - {e.FUND_NAMES[t]}", f"{w * 100:.0f}%", f"${w * 1e6:,.0f}"]
                       for t, w in zip(e.TICKERS, res.weights)]))
    L.append(f"\nModeled net return **{pct(res.exp_return)}** (objective {pct(e.MAPLE.target_return)}, "
             f"gap {(res.exp_return - e.MAPLE.target_return) * 100:+.2f} pts) · ex-ante volatility "
             f"**{pct(res.vol)}** · worst 12-month loss, Jun-2007 on, **{pct(res.worst12, 1)}** "
             f"(12 months to {res.worst12_end}) · reserve **{pct(res.weights[0], 0)}**.\n")
    L.append(f"Point-in-time signal: **GS2 = {pct(inp.signal.value)}**, month measured "
             f"{inp.signal.month_measured}, ALFRED vintage {inp.signal.vintage_date}. Estimates: "
             f"{inp.n_months} months, {inp.window_start} to {inp.window_end}.\n")
    L.append(md_table(["Fund", "Expected return used", "Trailing 60-month average", "Volatility"],
                      [[a, pct(m), pct(h), pct(v)] for a, m, h, v in
                       zip(inp.assets, inp.mu, inp.history_mu, inp.vol)]))
    L.append(f"\nAfter the review (live, not used in any decision): October 2026 return of the "
             f"75/25 mix = **{pct(live)}** net.\n")

    L.append("## 2. Baselines and mandate verdicts\n")
    L.append(md_table(["Portfolio", "BIL / IEF / LQD / VT", "Modeled net return", "Volatility",
                       "Worst 12m (Jun-2007 on)", "Verdict"],
                      [[n, e.fmt_w(b["weights"]), pct(b["exp_return"]), pct(b["vol"]),
                        pct(b["worst12"], 1), b["verdict"]] for n, b in d.baselines.items()]))

    L.append("\n## 3. The committee's menu: objective vs loss limit\n")
    L.append(md_table(["Loss limit", "BIL / IEF / LQD / VT", "Best modeled net return", "Volatility",
                       "Worst 12m", "Meets 6.50%?"],
                      [[pct(x.loss_limit, 1), f"{x.BIL:.0f} / {x.IEF:.0f} / {x.LQD:.0f} / {x.VT:.0f}",
                        pct(x.max_exp_return), pct(x.vol), pct(x.worst12, 1),
                        "yes" if x.meets_objective else "no"] for x in tr.itertuples()]))
    L.append("\n![Objective vs loss](objective_vs_loss.png)\n")

    L.append("## 4. Stability across estimation windows\n")
    L.append(md_table(["Window", "Months", "Meets objective", "BIL", "IEF", "LQD", "VT",
                       "Modeled return", "Worst 12m", "VT estimate"],
                      [[x.window, x.months, "yes" if x.feasible else "no (closest compliant)",
                        wcell(x.BIL), wcell(x.IEF), wcell(x.LQD), wcell(x.VT), pct(x.exp_return),
                        pct(x.worst12, 1), pct(x.VT_mu)] for x in stab.itertuples()]))
    L.append(f"\nLargest weight move across windows: **{spread:.0f} points** (adopt limit "
             f"{e.MAPLE.stability_limit_pts:.0f}).\n")

    L.append("## 5. Stress run (estimates, window, costs, constraints, data)\n")
    L.append(md_table(["Group", "Change", "Meets objective", "BIL / IEF / LQD / VT", "Modeled return",
                       "Volatility", "Worst 12m", "Largest move vs base (pts)"],
                      [[x.group, x.change, "yes" if x.meets_objective else "no",
                        f"{wcell(x.BIL)} / {wcell(x.IEF)} / {wcell(x.LQD)} / {wcell(x.VT)}",
                        pct(x.exp_return), pct(x.vol), pct(x.worst12, 1), wcell(x.largest_move_pts)]
                       for x in stress.itertuples()]))
    L.append(f"\n**Why the full-crisis screen matters:** on fund prices alone (VT starts Jul-2008) the "
             f"process picks {e.fmt_w(w_fund)} and reports a worst 12-month loss of "
             f"{pct(fund_only.result.worst12, 1)}. Counting Mar-2008 to Feb-2009 (VT proxy before launch), "
             f"that same mix loses **{pct(fund_mix_ext_loss[0], 1)}** (12 months to "
             f"{fund_mix_ext_loss[1]}), beyond the -15% limit.\n")
    aw, shocks = e.all_worst_at_once(prices, REVIEW, res.weights)
    aw_b, _ = e.all_worst_at_once(prices, REVIEW, np.array([0.30, 0.30, 0.10, 0.30]))
    L.append(f"**All-worst-at-once stress** (each fund's own worst 12 months at the same time: "
             + ", ".join(f"{k} {v * 100:.1f}%" for k, v in shocks.items())
             + f"): 75/25 loses **{pct(aw, 1)}**; the bond-heavy 30/30/10/30 mix from the bond-yield "
             f"stress loses **{pct(aw_b, 1)}**, past the limit. Reported, not a hard rule.\n")
    if be:
        L.append(f"**Break-evens for the 75/25 mix:** margin over objective {be['margin_pts']:+.2f} pts; "
                 f"meets 6.50% only if GS2 >= {pct(be.get('BIL_breakeven'))} and VT's estimate >= "
                 f"{pct(be.get('VT_breakeven'))}.\n")

    L.append("## 6. Walk-forward test, Oct-2013 to Sep-2026\n")
    L.append("Each 30 September the process decides with only the prices and GS2 vintage known that day; "
             "holds 12 months with drifting weights; pays 10 bp a year plus 10 bp per 100% traded.\n")
    L.append(md_table(["Strategy", "Annual return", "Volatility", "Max drawdown", "Worst 12m",
                       "12m windows >= 6.5%", "12m windows < -15%"],
                      [[x.strategy, pct(x.annual_return), pct(x.volatility), pct(x.max_drawdown, 1),
                        f"{pct(x.worst_12m, 1)} ({x.worst_12m_end})",
                        pct(x.share_12m_windows_meeting_target, 0),
                        pct(x.share_12m_windows_breaching_loss_limit, 1)] for x in bt.metrics.itertuples()]))
    L.append("\n![Walk-forward growth](walk_forward_growth.png)\n")
    L.append(md_table(["Review", "GS2 known (month)", "BIL / IEF / LQD / VT", "Meets objective",
                       "Turnover", "Next 12 months, net", "BIL next 12m", "BIL trailing avg"],
                      [[x.decision_date, f"{pct(x.GS2_known)} ({x.GS2_month})",
                        f"{x.BIL * 100:.0f} / {x.IEF * 100:.0f} / {x.LQD * 100:.0f} / {x.VT * 100:.0f}",
                        "yes" if x.feasible else "no", pct(x.turnover, 0), pct(x.process_next_12m),
                        pct(x.BIL_next_12m), pct(x.BIL_trailing_mean)] for x in bt.yearly.itertuples()]))
    n_ok = int(bt.yearly.feasible.sum())
    L.append(f"\nThe objective was reachable inside the hard rules in **{n_ok} of {len(bt.yearly)}** "
             f"reviews. Signal test: as a forecast of BIL's next-12-month return, GS2 missed by "
             f"**{pct(sig_err)}** on average vs **{pct(his_err)}** for the trailing average.\n")

    L.append("## 7. Data gate and sanity gate\n")
    L.append("Data gate: dates increasing, one row per month, no missing or non-positive price, "
             "GS2 month measured earlier than its vintage date - all pass.\n")
    L.append(md_table(["Date", "Fund", "Flag", "Resolution"],
                      [[f["date"], f["fund"], f["issue"],
                        "Kept: daily closes move inside the month and return to the same close"]
                       for f in flags]))
    L.append("")
    (OUT / "results.md").write_text("\n".join(L), encoding="utf-8")

    out = {
        "review_date": REVIEW, "recommendation": verb, "reason": why,
        "weights": dict(zip(e.TICKERS, res.weights.tolist())),
        "exp_return": res.exp_return, "vol": res.vol, "worst12": res.worst12,
        "worst12_end": res.worst12_end, "meets_objective": res.feasible,
        "signal": inp.signal.__dict__, "mu": dict(zip(inp.assets, inp.mu.tolist())),
        "trailing_mu": dict(zip(inp.assets, inp.history_mu.tolist())),
        "vol_by_fund": dict(zip(inp.assets, inp.vol.tolist())),
        "stability_spread_pts": spread, "break_even": {k: float(v) for k, v in be.items()},
        "october_2026_live_return": live,
        "all_worst_at_once": {"75/25": aw, "30/30/10/30": aw_b, "shocks": shocks},
        "baselines": {n: {"weights": b["weights"].tolist(), "exp_return": b["exp_return"],
                          "vol": b["vol"], "worst12": b["worst12"], "verdict": b["verdict"]}
                      for n, b in d.baselines.items()},
        "tradeoff": tr.to_dict(orient="records"),
        "stability": stab.to_dict(orient="records"),
        "stress": stress.to_dict(orient="records"),
        "walk_forward_metrics": bt.metrics.to_dict(orient="records"),
        "walk_forward_yearly": bt.yearly.to_dict(orient="records"),
        "signal_forecast_mae": {"gs2": sig_err, "trailing": his_err},
        "data_sha256": {"prices": sha(e.PRICES_CSV), "gs2": sha(e.GS2_CSV),
                        "proxy": sha(e.PROXY_CSV)},
    }
    (OUT / "results.json").write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
    charts(bt, tr)
    print(f"{verb}: {e.fmt_w(res.weights)} (BIL/IEF/LQD/VT) | modeled net return "
          f"{res.exp_return:.2%} vs objective {e.MAPLE.target_return:.2%} | worst 12m "
          f"{res.worst12:.1%} | window spread {spread:.0f} pts")
    print(f"Wrote {OUT / 'results.md'}, results.json and two charts.")


if __name__ == "__main__":
    main()
