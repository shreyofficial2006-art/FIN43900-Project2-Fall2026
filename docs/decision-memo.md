# Investment Committee Memo - Maple Education Fund

> **AI disclosure:** I used Anthropic Claude (Opus 5.5, claude.ai) to write the code, retrieve the data and draft this memo; the full record is in [`validation-and-ai-use.md`](validation-and-ai-use.md). The analysis and the decision are mine. **Education, not investment advice.**

**To:** Investment Committee, Maple Education Fund ($1,000,000 scholarship reserve; fictional course client)
**From:** Shrey Goyal, portfolio analyst · **Meeting:** November 2026
**Review as of:** 30 September 2026 (fund prices through that date; GS2 as published by then). Data retrieved 19 November 2026.

## Decision: PILOT the allocation process for one year - do not adopt it

**Allocate the reserve to 75% BIL / 25% VT** (range: BIL 75-80%, VT 20-25%, IEF and LQD 0%) for the 2026-27 year, and run the Maple process as a one-year pilot, not as standing policy. Compared with my Lab 20 paper pilot (55% BIL / 45% VT), this moves 20 points ($200,000) from VT to BIL; under the full-2008 screen that 55/45 mix could have lost 23.5% in 12 months.

**What the committee is asked to do today**

1. **Approve the 75/25 allocation** for one annual cycle, reviewed quarterly against the triggers below.
2. **Resolve a conflict in the mandate by the March 2027 meeting.** The 6.5% return objective and the -15% worst-12-month loss limit cannot both be met. Choose one:
   - **A - keep the loss limit, set the objective to 6.0%** *(my recommendation: the limit protects the awards)*. 75/25 then meets every rule (modeled 6.04%, a thin 0.04-point margin).
   - **B - keep 6.5%, widen the loss limit to -20%.** The process would hold 65/35, which would have lost about **18.5% ($185,000)** in the 12 months to February 2009.
3. **Fund one redesign for the pilot year:** bond expected returns from yields, each with its own data card, so bonds are judged on fair estimates; a mix with bonds may be traded only if it also passes the all-worst-at-once stress.

## Why

| Evidence | Number | Where |
|---|---|---|
| Best return inside the reserve and -15% limit (2008 counted) | **6.04%**, 75/25, 0.46 pts short of 6.5% | results §1, §3 |
| VT's loss in the 12 months to Feb-2009 (proxy before Jun-2008) | **-47.4%** | data card §3 |
| The same screen on VT's own prices only | picks 65/35 and shows -9.3%; with the full crisis that mix loses **-18.5%** | results §5 |
| Mandate verdicts | Equal weight FAIL (return 3.28%); inverse volatility FAIL (3.78%); benchmark 60 VT/40 LQD FAIL (no reserve; -33.0% worst 12m) | results §2 |
| Walk-forward, 13 annual reviews, Oct-2013 to Sep-2026, after costs | 6.5% reachable inside the limits in **1 of 13** reviews; process **4.13%/yr** vs equal weight 4.19%, benchmark 7.55% (worst 12m -21.0%) | results §6 |
| The point-in-time signal | GS2 as known on 30-Sep-2026 = **4.22%** (August). As a forecast of BIL's next-year return it missed by 0.44 pts on average vs 1.21 pts for BIL's trailing average | data card §2 |

The allocation is set by the **loss limit**, not by the return estimates: cutting VT's expected return by 1 or 3 points, cutting the cash yield by 1 point, raising costs to 75 bp or raising the reserve to 20% leaves it at 75/25 and only lowers the modeled return. That is why I am comfortable allocating to it while not adopting the process: the main weakness of an optimiser - amplifying estimate errors - barely touches this answer.

The process itself has not earned adoption. Over 13 reviews it did no better than equal weight. In the year to September 2022 it held 45% IEF, 15% LQD and 30% VT, because its history said bonds cushion stocks; all three fell between 15.6% and 20.9% together and the fund lost **16.4%**, past the limit. The current allocation holds no bonds, so that failure cannot recur this year; even if every fund suffered its own worst 12 months at once (stocks as in 2008, bonds as in 2022), 75/25 would lose 12.0%, inside the limit. A bond-heavy mix would not (30/30/10/30: -21.4%). That is the reason for redesign item 3.

## Material assumptions and how much they matter

| Assumption | Base | If wrong | Effect |
|---|---|---|---|
| BIL expected return = GS2 as known | 4.22% | -1 pt (cash rates fall) | Still 75/25; modeled return 5.29% |
| VT expected return = trailing 60-month average | 11.90% | -3 pts | Still 75/25; 5.29% |
| IEF/LQD expected returns = trailing averages | -1.79% / -0.81% | +6 pts each (4.2% / 5.2%, still below the 10-year Treasury 5.28% and Baa 6.47% yields of early Oct-2026, Lab 17) | Bonds enter: 30/30/10/30 meets 6.5% at a -14.9% worst 12m. **The most consequential open assumption.** |
| Estimation window 60 months | 75/25 | 36 / 120 / all months | 85/15 · 75/25 · 50/0/25/25: 35-point spread > 20-point adopt limit |
| Loss limit -15% (client's answer to my Lab 15 question) | 75/25 | -20% | 65/35 meets 6.5% |
| Costs 10 bp a year + 10 bp per 100% traded | 6.04% | 75 bp a year | 5.39% |

Returns are arithmetic annual estimates (monthly mean x 12). For the 75/25 mix the compounding drag is small (about 0.07 pts); for VT alone it is about 1.1 pts.

## Risks, triggers and what reverses the call (reviewed quarterly)

| Trigger | Threshold | Action |
|---|---|---|
| Cash yield rises | GS2 as known **>= 4.83%** (latest: 4.74% for Oct-2026) | 75/25 meets 6.5% at current estimates; the conflict eases - report it, keep the pilot |
| Cash yield falls | GS2 **< 3.5%** | 75/25 models under about 5.5%; the reserve-heavy mix no longer pays - committee review |
| Fund loss | trailing 12-month return **< -10%** / **< -15%** | review / limit breached: stop and re-decide |
| Bonds re-enter at a re-run | IEF or LQD > 0% | the mix must also pass the all-worst-at-once stress (shown in the app) before trading |
| Data gate | missing GS2 vintage, missing month, unexplained sanity flag | no rebalance until fixed |

**Adopt the process at the 30-Sep-2027 review only if** the committee has resolved the objective/limit conflict, the allocation moves no more than 20 points across the 36/60/120-month and all-history windows, no loss trigger fired during the pilot, and the data gates pass. **Reject it** if, with yield-based bond estimates, it still cannot beat equal weight in the walk-forward test.

Live check, not used in the decision: October 2026 return of 75/25 = -0.14% (VT -1.6%, BIL +0.35%).

*Executed output: [`output/results.md`](../output/results.md) · App: `python -m streamlit run app.py` · Data card: [`data-card.md`](data-card.md) · Tests, AI use and the Locked Changed-Input Record: [`validation-and-ai-use.md`](validation-and-ai-use.md).*
