# Data card - Maple Education Fund app

> **AI disclosure:** data retrieval and this card were prepared with AI assistance (Anthropic Claude). Shrey Goyal owns the choices and checked the values listed under "Checks". **Education, not investment advice.**

Every number in the app, the memo and `output/results.md` comes from the three files below. Nothing is downloaded when the app runs.

## 1. Fund prices - `data/prices_monthly.csv`

| Field | Value |
|---|---|
| What it measures | Month-end **Adj Close** (price adjusted for distributions and splits) of BIL, IEF, LQD and VT, in US dollars per share. A monthly return computed from it is a total return, after the fund's own expense ratio. |
| Funds | BIL - State Street SPDR Bloomberg 1-3 Month T-Bill ETF; IEF - iShares 7-10 Year Treasury Bond ETF; LQD - iShares iBoxx $ Investment Grade Corporate Bond ETF; VT - Vanguard Total World Stock ETF |
| Source | Yahoo Finance chart API, the same source family as Labs 14-15. Request URLs and response hashes in [`data/provenance.json`](../data/provenance.json). |
| How it was built | Daily bars for 2007-01-01 onward; for each calendar month the **last trading day's** Adj Close is kept, so every date in the file is a real trading day (e.g. 2026-10-30). |
| Coverage | 2008-06-30 to 2026-10-30: 221 month-ends, 220 monthly returns. Starts in June 2008 because VT began trading on 26 June 2008. November 2026 is incomplete and excluded. |
| Retrieved | 2026-11-19 18:10 UTC. File sha256 `d411a2247724e82c70688b9356c334bf60aa0cb3fd9026529be8a666b8110728`. |
| Transformations | None in the file. The engine computes `r_t = P_t / P_(t-1) - 1`. No missing values were filled; no row was dropped or edited. |
| Point-in-time | Prices are final at the close, so a month-end price is knowable on that day. The engine uses only months that ended on or before the review date (tested: changing every later price leaves the decision unchanged). |
| Revisions | Yahoo re-bases old Adj Close **levels** each time a fund pays a distribution. Example: BIL's Sep-2026 level is 91.377 in Lab 15's 22-Oct download and 91.070 in this 19-Nov download. **Monthly returns do not change**: over the 60 months both files share, the largest return difference is 0.0001 percentage point. |
| Licence | Yahoo Finance data is for personal, non-commercial use. This repository keeps only derived month-end values needed to reproduce an educational result, with attribution; [`fetch_data.py`](../fetch_data.py) rebuilds the file from the source instead of relying on this copy. |
| Privacy | No personal data. The client (Maple Education Fund) is a fictional course case. |

## 2. The point-in-time signal - `data/gs2_vintages.csv`

| Field | Value |
|---|---|
| Series | **GS2** - Market Yield on U.S. Treasury Securities at 2-Year Constant Maturity, Quoted on an Investment Basis. Monthly average of business days, percent a year, not seasonally adjusted. |
| Source | Board of Governors of the Federal Reserve System, H.15 release; distributed by FRED and archived by **ALFRED**, Federal Reserve Bank of St. Louis. [FRED page](https://fred.stlouisfed.org/series/GS2) · [ALFRED page](https://alfred.stlouisfed.org/series?seid=GS2) |
| How it is used | On each review date the app reads the **ALFRED vintage dated that day** and takes its latest month. That yield is BIL's expected return for the next year (the 2-year yield is the market's price for rolling short Treasuries over the next two years). |
| What was knowable | On 30 September the latest published month is **August** (the September average is not complete or published until early October). 30-Sep-2026 vintage: August 2026 = **4.22%**. 30-Sep-2025 vintage: August 2025 = **3.70%**. The October 2026 value (4.74%) first appeared on 2 November 2026 (Lab 17). |
| Publication lag | About two days after month-end in Lab 17's check (October 2026 appeared 2 November). |
| Revisions | Each of the 18 vintages (2009-2026) was compared with the 19-Nov-2026 vintage: **0 changed values** in every one. No value in these vintages differs from today's, but the app still reads the vintage, not today's file, so a future revision cannot leak in. |
| Gate | The engine refuses (a) a vintage whose month measured is not earlier than its vintage date, and (b) a review date with no archived vintage - it will not reuse a stale reading. |
| Retrieved | 2026-11-19 18:14 UTC; one request per vintage, each response's sha256 in the file. |
| Licence | Federal Reserve data; free to use with citation of FRED/ALFRED. |
| Admit / quarantine / reject | **Admit** as BIL's expected return, read as-known on each review date (Lab 17 call). |

Signal test (walk-forward, 13 reviews 2013-2025): as a forecast of BIL's realised next-12-month return, GS2 missed by **0.44 points** on average; BIL's own trailing 60-month average missed by **1.21 points**. GS2 ran 0.08 points above the realised return on average (BIL's expense ratio and the 2-year vs 1-3 month maturity gap).

## 3. Stress-only file - `data/stress_proxy_2007_2010.csv`

| Field | Value |
|---|---|
| Purpose | Lets the loss screen see the **whole** 2008 crisis. VT's own history starts in June 2008, mid-crisis, so it misses March-May 2008 losses and makes equity look safer than it was. |
| Contents | Month-end Adj Close, May 2007 to Dec 2010, for BIL, IEF, LQD, VT and two Vanguard index mutual funds: VTSMX (Total Stock Market) and VGTSX (Total International Stock). Source: Yahoo Finance chart API, retrieved 2026-11-19; sha256 `a28325d4...`. |
| Proxy rule | Before VT existed (June 2007 to June 2008), VT's monthly return = **40% VTSMX + 60% VGTSX**. The 40/60 split had the lowest tracking error against VT over the 30 months when both exist (Jul-2008 to Dec-2010): 2.3% a year, correlation 0.996. |
| Where it is used | Only in the worst-12-month loss screen (`loss_screen="extended"`). Never in expected returns, volatilities or correlations. The app can switch it off ("Fund prices only"). |
| Effect | With the proxy, VT lost **47.4%** in the 12 months to February 2009. On VT's own prices the worst 12 months is milder because the window starts too late. |

## 4. Exclusions and sanity checks

- **Sanity gate flags** (kept, not deleted): VT's month-end Adj Close is identical in June and July 2019 (75.16 close) and in December 2023 and January 2024 (102.88 close). The daily data shows prices moving inside each month and returning to the same close, so both are real; both rows are kept.
- **BIL flat months**: BIL's price barely moved in 2010-2016 because T-bill yields were near zero. Not flagged; expected for a cash fund.
- **Not used**: money-market funds (their $1.00 price hides their return; BIL stands in for cash, as Lab 14 advised).

## 5. Checks a reviewer can repeat

| Check | How |
|---|---|
| File unchanged | `sha256sum data/prices_monthly.csv` (Mac: `shasum -a 256 ...`) must equal the value above. |
| A price against the source | Open [finance.yahoo.com/quote/VT/history](https://finance.yahoo.com/quote/VT/history/) and compare a recent month-end close; Adj Close levels may differ slightly if a distribution has been paid since 2026-11-19, returns will not. |
| A GS2 vintage | Open `https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=GS2&vintage_date=2026-09-30`: the last row is 2026-08-01, 4.22. |
| Rebuild from source | `python fetch_data.py` writes `data/refresh/` and prints the largest return difference against this snapshot. |
