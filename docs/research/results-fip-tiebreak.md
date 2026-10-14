# Frog-in-the-pan tie-break — results. **FAIL (trial 204). In the top 200 the tie-break did worse than filling by rank: −0.39% a month, paired t −2.15. In ranks 201–400 it was −0.15% a month, t −0.72. No change to the paper book.**

**2026-10-14.** Pre-registration `prereg-fip-tiebreak.md` (`52e8977`), then
the code (`cde4947`), then stage 0, run once at 09:17 and committed
(`2c7d25e`), then the trial, run once at 09:19 from the same code. There is
no amendment. Nothing dated 2026 was read, and no live or Kite data.

**No reviewer read the pre-registration or the code before the run.** The
owner asked for the result directly. It is in `reviewer-outbox.md` for a
read after the fact, and until that read these figures are unreviewed.

## Verdict, in the pre-registration's terms

| Part | Rule | Result | |
| --- | --- | --- | --- |
| **Stage 0** (L56) | parity, coverage ≥ 97%, ≥ 2.0 of 15 holdings differ | parity exact; 100% and 99.98%; 5.8 and 5.5 | pass, trial not withdrawn |
| **Item 1**, paired, top 200 (trial 204) | mean > 0, t ≥ 1.65 | **−0.39% a month, t −2.15** | **fail** |
| **Item 2**, paired, ranks 201–400 (L57) | mean > 0, t ≥ 1.65 | **−0.15% a month, t −0.72** | **fail** |
| **Item 3**, family bar at N = 11, top 200 | six criteria | meets three; t 1.26 against 2.838 | **fail** |

The falsification table has a row for this: "Either paired t ≤ −1.65: FAIL.
Continuous-information winners did worse here. The sign is not flipped and
re-tested." The top 200 hit it.

**This is not the outcome the pre-registration expected.** It expected both
paired t-values inside ±1.65, a fail for lack of power. The direction was
not predicted.

## What it means, plainly

**1. In the running book's own universe the tie-break cost money.** The top
200 book made 15.6% a year with it and 20.6% without, against a benchmark of
11.9%. The paired difference is −0.39% a month. It was negative in both
halves (−0.35% and −0.44%).

**2. It is not mainly a cost effect.** With every cost at zero the difference
is still −0.37% a month (t −2.03). The rule does trade more: turnover rose
from 211% to 281% a year and costs from 0.69% to 0.92% of the book. That
accounts for about 0.02% a month of the gap.

**3. Ranks 201–400 do not confirm a loss, or a gain.** The difference there
is −0.15% a month, well inside noise. In that sample the rule had lower
volatility (23.1% against 26.6%) and a shallower worst drawdown (−29.2%
against −37.1%), with a lower return (25.8% against 26.9% a year).

**4. It does not show that the published effect is absent in India.** The
rule changes two things at once. It prefers low information discreteness,
and it stops filling vacancies from the best-ranked names. This test cannot
separate the two. Stage 0 found that rank and ID are already mildly related
inside the top 30 (rank correlation +0.20 and +0.27): the best-ranked names
tend to be the more continuous ones. A plausible reading is that the loss
comes from giving up rank, not from continuity itself. That reading is
untested, and testing it would be a new trial.

**5. How strong the evidence is.** One sample of two reached t −2.15, about
3 in 100 two-sided on its own. The test was built to find a gain, and the
other sample is inside noise. So it is evidence that this tie-break hurts
this book, and no evidence at all for adopting it.

## The two arms

| | Top 200, base | Top 200, this rule | Ranks 201–400, base | Ranks 201–400, this rule |
| --- | --- | --- | --- | --- |
| Net excess a month (t) | +0.71% (2.51) | **+0.32% (1.26)** | +0.91% (3.00) | **+0.75% (2.79)** |
| First half, second half | +0.65%, +0.77% | +0.30%, +0.33% | +0.57%, +1.24% | +0.56%, +0.94% |
| Last three years (t) | +0.78% (1.13) | −0.30% (−0.53) | +1.08% (1.63) | +1.04% (1.60) |
| Net CAGR; benchmark | 20.6%; 11.9% | 15.6%; 11.9% | 26.9%; 15.2% | 25.8%; 15.2% |
| Annual volatility | 23.4% | 21.5% | 26.6% | 23.1% |
| Deepest drawdown | −33.1% | −39.8% | −37.1% | −29.2% |
| Longest spell below a peak | 24 months | 42 months | 31 months | 30 months |
| CAGR ÷ volatility | 0.88 | 0.72 | 1.01 | 1.11 |
| One-sided turnover a year | 211% | 281% | 269% | 379% |
| All costs, share of the book a year | 0.69% | 0.92% | 1.14% | 1.61% |
| Buys; round trips | 531; 516 | 720; 705 | 665; 650 | 867; 852 |
| Mean ID of the names held | −0.070 | −0.100 | −0.045 | −0.074 |
| Added slippage a side that zeroes the excess | 2.2% | 0.73% | 3.4% | 1.7% |

The base columns match trial 126 and L42, as the parity gate required. The mean ID rows show the rule did what it was written to do: it
held more continuous names in both samples.

## The paired test (this rule minus the base, 189 months)

| | Top 200 | Ranks 201–400 |
| --- | --- | --- |
| Mean difference a month | **−0.39%** | **−0.15%** |
| Standard deviation | 2.50% | 2.94% |
| t | **−2.15** | **−0.72** |
| First half (t) | −0.35% (−1.34) | −0.01% (−0.02) |
| Second half (t) | −0.44% (−1.69) | −0.30% (−1.02) |
| Difference with every cost at zero (t) | −0.37% (−2.03) | −0.12% (−0.58) |
| Smallest difference detectable at 80% power | 0.45% | 0.53% |
| Holdings in common, of 15 | 9.2 | 9.5 |

## The family bar, top 200 (item 3)

| Criterion | This rule | Met |
| --- | --- | --- |
| t ≥ 2.838 (Bonferroni across 11) | 1.26 | no |
| Deflated Sharpe ≥ 0.95 at N = 11 | 0.357 | no |
| Positive in both halves | +0.30%, +0.33% | yes |
| Positive over the last three years | −0.30% | no |
| CAGR at least 2.0 points over the benchmark | 3.7 points | yes |
| At least 100 round trips | 705 | yes |

Project-wide Deflated Sharpe at 204 trials, for information: 0.066.

## Stage 0 (L56), as run

| | Top 200 | Ranks 201–400 |
| --- | --- | --- |
| Base arm reproduces the recorded holdings, all 190 months | yes | yes |
| Top-30 name-months with an ID | 100% | 99.98% |
| Holdings that differ, mean of 15 (median, most) | 5.8 (6, 9) | 5.5 (5, 9) |
| Months in which the two books are identical | 0 | 0 |
| Buys a year: base, this rule | 33.7, 45.7 | 42.2, 55.0 |
| Rank correlation of ID with score rank, top 30 | +0.20 | +0.27 |

## What was predicted, and what was wrong

- **Power.** The pre-registration guessed the difference's standard
  deviation at √*d* × 1% a month. With 5.8 holdings differing that is 2.4%;
  the measured figure is 2.50%. The guess for ranks 201–400 would be 2.3%
  against a measured 2.94%.
- **Turnover.** Stage 0's buy counts warned of it, and it came through: about
  a third more trading in both samples.
- **Direction.** Wrong. The file assumed the tie-break could only help a
  little or do nothing measurable. It did not consider that leaving rank
  order could cost more than continuity adds.
- **The trial count.** The script uses 204 for the project-wide Deflated
  Sharpe. Trials actually spent are 203, because trial 203 (Jev 2) is
  registered and not yet spent. The figure is overstated by one, on the
  conservative side.
- **One shortcut.** The script builds its stock lists without the wide-book
  screens, which neither sample uses. The parity gate shows the holdings are
  identical to the recorded runs.
- **No review before the run**, as stated at the top.

## What happens now

- **No change to the paper book, and no shadow sleeve.** A sleeve needed a
  pass.
- **The candidate is closed.** No variant may be run under this file: not a
  cut at 15 or 45, not another window, not the opposite sign.
- **The momentum family now counts eleven.** The next momentum trial faces
  t ≥ 2.865 at N = 12. That includes the tax-aware hold rule if the owner
  puts it in this family.
- The order in `profitability-sweep-2026-10-01.md` §4 stands: the L53
  after-tax measurements, then the tax-aware hold rule.

Data: `data/momentum_fip_stage0.json`, `data/momentum_fip_trial.json`.
