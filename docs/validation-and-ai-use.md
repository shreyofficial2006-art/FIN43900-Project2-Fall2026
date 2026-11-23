# Validation and AI Use - Maple Education Fund app

> **AI disclosure:** I used Anthropic Claude (Opus 5.5, in the Claude app) to write the code, retrieve the data and draft the documents. Every use is listed in section 6. The analysis and the decision are mine. **Education, not investment advice.**

Review date: **30 September 2026**. Data retrieved 19 November 2026 (prices through 30 October 2026). Sources, definitions and the as-of rule are in the [data card](data-card.md). Executed output: [`output/results.md`](../output/results.md).

## 1. The claims the decision rests on, and how each was challenged

| # | Claim (highest risk first) | Challenge | Result |
|---|---|---|---|
| 1 | The 6.5% objective cannot be met inside the 10% reserve and the -15% loss limit | (a) Re-ran the screen on fund prices only; (b) every estimation window; (c) the objective-vs-loss menu; (d) bond estimates raised to yield-like levels | **Qualified.** True on every window except 36 months (VT estimate 20.2%) and true unless bond expected returns are raised about 6 points. With yield-like bond estimates, 30/30/10/30 meets 6.5% at -14.9%. Hence redesign item 3 in the memo. |
| 2 | On VT's own prices the screen understates 2008 | VT starts 26-Jun-2008. Added Jun-2007 to Jun-2008 with a VT proxy (40% VTSMX / 60% VGTSX; tracking error 2.3%/yr, correlation 0.996 against VT when both exist) | **Confirmed.** 65/35 shows -9.3% on fund prices and -18.5% with the full crisis. The full-crisis screen is the default; the app can switch it off. |
| 3 | 75/25 is robust to the return estimates | One-at-a-time stress: VT -1/-3 pts, cash -1 pt, signal off, costs 35/75 bp, reserve 20% | **Confirmed.** Weights unchanged in all of them; only the modeled return moves. The loss limit, not the estimates, sets the mix. |
| 4 | The GS2 signal is a better cash forecast than history | 13 reviews, 2013-2025: GS2 known on each 30 Sep vs BIL's realised next 12 months | **Confirmed:** mean absolute error 0.44 pts vs 1.21 pts for the trailing average. **But** in the walk-forward test the process with the signal earned 4.13%/yr vs 4.58% without it: better cash estimates did not mean better portfolio returns. |
| 5 | No look-ahead | Changed every price after the review date (x3 and x0.5) and re-ran: decision unchanged. GS2 read from the vintage dated the review date; a date without a vintage is refused | **Confirmed** by tests `test_no_look_ahead_in_estimates`, `test_backtest_uses_only_known_data`, `test_gs2_is_point_in_time`. |
| 6 | The process deserves adoption | Walk-forward test against equal weight, inverse volatility and the 60/40 benchmark, same costs | **Rejected for now.** Objective reachable in 1 of 13 reviews; 4.13%/yr vs 4.19% equal weight; one loss-limit breach (-16.4%, year to Sep-2022). This is why the memo says PILOT, not adopt. |

## 2. Known answers and tests

`python -m pytest -q` → **36 passed** (Python 3.12 clean environment and Python 3.13, 19-Nov-2026; see section 5).

| Test | Known answer | Source of the answer |
|---|---|---|
| Lab 14 benchmark 40 IG / 60 equity | 6.80% return, **10.46%** volatility (9.90% would mean the correlation term is missing) | Lab 14 (course-authored, written before this code) |
| Lab 14 equal weight / inverse volatility | 5.20% / 5.21%; 84.3 / 6.0 / 7.0 / 2.6 at 3.77% / 1.05% | Lab 14 |
| Lab 14 correlation probe 0.25 → 0.50 | 11.00%; correlation 1.3 refused | Lab 14 |
| Lab 15 search | 0/20/25/55 at 6.51% / 9.44%; equity 8 → 7%: 0/10/10/80, 6.53% / 12.94%, 25-point move; correlation 0.50: 0/40/0/60, 6.52% / 9.73% | Lab 15 |
| Search is the true minimum | Equals an independent brute-force loop over all 1,771 grid mixes | Written separately from `engine.search` |
| Loss screen | The fast all-mixes calculation equals the one-mix-at-a-time worst 12 months | Two separate code paths |
| Annualisation | VT mean x 12 and sample s.d. x √12 equal the hand formula on the same 60 months | Hand formula in the test |
| Point-in-time signal | 30-Sep-2025 → 3.70% (Aug-2025); 30-Sep-2026 → 4.22% (Aug-2026); 30-Jun-2026 refused | ALFRED vintages; same values as Lab 20 |
| Data gate | a skipped month and a missing price are refused | - |
| Sanity gate | flags exactly the two VT months (Jul-2019, Jan-2024) | data card §4 |
| Extended history | adds exactly 13 months before Jul-2008 and leaves later months identical | - |
| Decision 2026 | 75/0/0/25 and every hard rule passes; loss limit -20% → 65/35 meets 6.5% | - |
| Costs | higher cost lowers the modeled return | - |
| The app itself (Streamlit AppTest) | default page shows PILOT (objective not met) and 6.04%; loss limit -20% → 6.81%; objective 6.0% → met; loss limit switched off and every review date 2013-2026 run without error | runs the real `app.py` |
| Locked Changed-Input Record runner | refuses a prediction with blanks, one never committed, or one edited after its commit; refuses a second run | `lcir.py` in a temporary copy |
| Documents match the output | memo numbers are found in `output/results.json` | `tests/test_docs.py` |
| Data refresh parser | keeps the last trading day of each month | synthetic Yahoo response |

The course rule applies: tests written with the same AI do not prove the code on their own. The **independent** evidence is the course-authored Lab 14/15 answers, the source checks in section 4, and my hand checks in section 4.

## 3. Sensitivity and robustness (full tables in `output/results.md` §4-§5)

- **Window:** 36 / 60 / 120 months / all history → 85/15 · 75/25 · 75/25 · 50/0/25/25. Largest move **35 points**, over the 20-point limit to adopt.
- **Estimates:** VT -1 and -3 pts, cash -1 pt, signal off → weights unchanged; modeled return 5.29-5.79%. Bonds +6 pts → 30/30/10/30 (45-point move).
- **Costs:** 35 bp and 75 bp a year → weights unchanged; 5.79% / 5.39%.
- **Constraints:** reserve 20% → unchanged; loss limit -20% or none → 65/35 meets 6.5%; 10-point grid → 80/20.
- **Data window:** fund prices only → 65/35 (the understated-2008 answer).
- **Walk-forward (13 reviews, costs included):** process 4.13%/yr, volatility 5.50%, worst 12 months -16.4%; equal weight 4.19%; benchmark 7.55% with -21.0% worst 12 months and no reserve.

## 4. Checks of AI output

### 4a. Issues found while building (by the AI's own checks; I re-verified the ones marked)

| What was found | How | What changed |
|---|---|---|
| The loss screen on VT's own prices starts mid-crisis and called 65/35 safe (-9.3%) | Data-window stress with a pre-launch proxy: -18.5% | Full-crisis screen became the default; the recommendation moved from 65/35 to 75/25 |
| Yahoo's monthly bars are labelled on the 1st of the month | Rebuilt month-ends from daily bars; compared every month: < 0.0002% apart for complete months | Daily-derived month-ends used, so each date is a real trading day |
| Adj Close levels differ from my Lab 15 download (BIL Sep-2026: 91.377 vs 91.070) | Compared monthly returns over the 60 shared months | Largest difference 0.0001 pt: levels re-based, returns unchanged; noted in the data card |
| Two VT months with an identical price | Sanity gate, then the daily price path | Real (same close twice); kept and documented |

### 4b. My own checks (independent of the AI)

| Check | What I did | What I found | Accept / qualify / correct / reject |
|---|---|---|---|
| C1 - recompute the decision numbers by hand | << e.g. In Google Sheets, from data/prices_monthly.csv, I computed VT's 60 monthly returns Oct-2021 to Sep-2026, their average x 12, and 0.75 x 4.22% + 0.25 x VT - 0.10% >> | << my numbers vs the app's 11.90% and 6.04% >> | << >> |
| C2 - the signal against its source | << opened the ALFRED vintage for 2026-09-30 and checked the last row >> | << >> | << >> |
| C3 - a second AI model cross-examines the central claim (the one shown in Video 1) | << which model, what I pasted, what it said >> | << the critique, and my check of it >> | << >> |

## 5. Reproducibility and cold run

| Run | Environment | Steps | First failure | Time |
|---|---|---|---|---|
| Clean environment (by the AI, 19-Nov-2026) | Fresh clone, new Python 3.12 virtual environment, Linux | `pip install -r requirements.txt` → `python run_analysis.py` → `python -m pytest -q` → `python -m streamlit run app.py` | none | see `output/cold-run.txt` |
| My own machine | << Windows or Mac, Python version >> | the README steps, nothing else | << none / what broke and the fix >> | << minutes >> |

Results are deterministic: the same data files give the same numbers (no random seeds, no network calls).

## 6. AI use record

**Tool:** Anthropic Claude, model shown as *Claude Opus 5.5*, in the Claude app (claude.ai), with its file workspace and a browser pane in the Claude desktop app. **Dates:** 19-23 November 2026. Earlier lab work reused here (Labs 13-20: the Maple mandate, the BIL/IEF/LQD/VT universe, the GS2 data card) was built with the course AI tools as disclosed in those lab repositories.

| Task | What the AI produced | My disposition and reason | Independent check |
|---|---|---|---|
| Data retrieval | Prices (Yahoo) and 19 GS2 vintages (ALFRED) through the browser pane, with hashes | Accept: file hash matched the browser's hash; returns match my Lab 15 file | C2; data card §5 |
| Engine and app code | `engine.py`, `app.py`, `run_analysis.py`, `lcir.py`, `fetch_data.py`, tests | Accept after tests: Lab 14/15 known answers reproduced exactly | Lab 14/15 answers; C1 |
| GS2 as BIL's expected return | The idea of using my Lab 17 series as the forward cash estimate | Accept: it answers the question I left open in Lab 15 (is BIL's trailing average a sound forward assumption?); forecast error 0.44 vs 1.21 pts | Walk-forward forecast test |
| -15% worst-12-month loss limit | Proposed as the client's answer to my Lab 15 question | << accept or change, and why - this is the client's risk tolerance >> | Objective-vs-loss menu |
| Full-crisis loss screen with proxy | Proposed after the data-window stress | Accept: the proxy tracks VT closely and is used only in the loss screen | Proxy tracking test, data card §3 |
| Benchmark 60% VT / 40% LQD | Kept from Lab 20 | Accept: the client-style policy benchmark, and it shows the reserve rule binding | - |
| Drafts of README, memo, data card, this record | Drafted from `output/results.md` | Edited and accepted; every memo number is checked against `results.json` by `tests/test_docs.py` | test_docs.py |
| Video speaking notes | Rehearsal outlines | Used as notes; the recordings are mine | - |
| Second-model review (C3) | << model, date >> | << >> | << >> |

**What the AI did well:** fast, consistent code with known-answer tests; found the 2008 data-window problem. **Where it needed checking:** it first built the loss screen on VT's own history, which looked safe and was not; its tests cannot vouch for its own code, so the course known answers and my hand checks carry the weight.

## 7. Locked Changed-Input Record

The prediction is written by me with AI closed in [`docs/lcir/prediction.md`](lcir/prediction.md), committed and pushed **before** the run. `python lcir.py --change ...` refuses to run if the prediction is unfinished, uncommitted or edited after the commit, then writes the before/after below and in [`docs/lcir/result.md`](lcir/result.md). The reconciliation lines are mine.

<!-- LCIR-START -->
*Not yet run.*
<!-- LCIR-END -->

## 8. Limitations and the action each one drives

| Limitation | Action |
|---|---|
| Bond expected returns are trailing averages (negative after 2022) | Pilot-year redesign: yield-based estimates with data cards; bonds can enter only if the mix also passes the all-worst-at-once stress (each fund's worst 12 months together) |
| VT before Jun-2008 is a proxy | Used only in the loss screen; the app shows both screens side by side |
| Arithmetic annual returns overstate compound growth (about 1.1 pts for VT, 0.07 for 75/25) | The objective is defined as a modeled arithmetic net return; stated in the memo |
| 13 annual decisions is a short test | No adoption on the backtest; pilot with quarterly triggers |
| A 2-year yield stands in for a 1-3 month bill fund; BIL's expense ratio is not deducted | Measured bias: GS2 ran 0.08 pts above BIL's realised return; covered by the -1 pt cash stress |
| 75% in bills carries reinvestment risk if rates fall | Trigger: GS2 < 3.5% → committee review |
