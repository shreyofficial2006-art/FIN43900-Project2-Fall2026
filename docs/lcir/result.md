# Locked Changed-Input Record - machine record

### Locked Changed-Input Record

**Prediction (verbatim from `docs/lcir/prediction.md`, written AI-off):**

**Prediction - Shrey Goyal**

**Date/time:** 23 November 2026, 5:31 p.m. EST.

**Change:** Raise the minimum BIL reserve from 10% to 80%.

**Command:** `python lcir.py --change reserve_min_pct=80`

| Output | Prediction |
|---|---|
| VT weight | Lower: 25% → 20%; BIL rises to 80% |
| Modeled net return | Lower: 6.04% → about 5.66% |
| Worst 12-month loss | Higher (less negative): −13.2% → about −10.4% |
| Meets the 6.50% objective? | No, unchanged |
| Recommendation | PILOT (objective not met), unchanged |

The 80% BIL minimum becomes binding, forcing five percentage points from stocks into cash. Because BIL has a lower expected return than VT, this reduces expected return while making the worst loss smaller.

The committee would still choose PILOT, but approve an 80% BIL / 20% VT allocation and reconsider the return objective.

I used the 80/20 allocation, 5.66% return, and −10.4% worst loss already printed in `output/results.md`, so these figures came from results I had read rather than an independent prediction.

**Lock:** prediction committed at `28a60414ecb8510cc4c1a7b1c243c5335498c3ae` (2026-11-23T18:33:04-05:00); pushed to GitHub: yes. [Commit on GitHub](https://github.com/shreyofficial2006-art/FIN43900-Project2-Fall2026/commit/28a60414ecb8510cc4c1a7b1c243c5335498c3ae)

**Run (AI closed):** `python lcir.py --change reserve_min_pct=80` at 2026-11-23 23:33:07 UTC, review date 2026-09-30, data files unchanged (prices sha256 `d411a2247724`).

**Changed input:** Reserve minimum in BIL 10% -> 80% of the portfolio. Everything else at its base value.

| Measure | Before (base) | After (changed) |
|---|---|---|
| weights | 75 / 0 / 0 / 25 | 80 / 0 / 0 / 20 |
| VT weight | 25% | 20% |
| BIL expected return | 4.22% | 4.22% |
| Modeled net return | 6.04% | 5.66% |
| Volatility | 3.83% | 3.09% |
| Worst 12-month loss | -13.2% | -10.4% |
| All-worst-at-once loss | -12.0% | -9.6% |
| Meets objective | no | no |
| Window spread (pts) | 35 | 5 |
| Recommendation | PILOT (objective not met) | PILOT (objective not met) |


The reconciliation is in docs/validation-and-ai-use.md, section 7.
