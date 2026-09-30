# The momentum book after Indian tax ties the funds an individual could buy instead — research look L53: TIES against both

**2026-10-01.** Pre-registration `prereg-after-tax-l53.md` (`ec7cb12`), amendment 1 (`2550a00`, the harvest day) and amendment 2 (`e0b2e98`: set-off order, interest, the tax paid by one fraction of the whole book, check 9). Harness `after_tax_l53.py` and tax engine `india_tax.py` at `635d911`. Inputs cut before 2026 (`8b834d8`). Stage 0 run 3 (`2f39ce5`) passed all nine checks. Runs 1 and 2 are kept, and the first review was NOT APPROVED on three findings that amendment 2 fixed. A second independent review approved it. The one measurement pass ran from 01:49:47 to 01:51:38 IST on 2026-10-01 on the main session's instruction. Record: `data/l53_result.json` (`288ef4a`). Nothing dated 2026 was read.

**This is a measurement for the owner's decision, not investment advice.**

## Verdict, in the pre-registration's terms

Primary block: ₹10 lakh, FY 2026-27 rules applied to every year, 189 months (2010-03-02 to 2025-12-01). Every account is sold at the close of 2025-12-01 and the tax settled. The difference is the book's after-tax CAGR minus the fund's. The interval is a 12-month block bootstrap, 95%.

| Book minus | After-tax CAGR, book / fund | Difference | 95% interval | First half (2010-03 to 2017-12) | Second half (2018-01 to 2025-11) | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| **(b) Nifty200 Momentum 30 index fund** (TRI less 0.5 pp a year) | 17.67% / 17.28% | **+0.39 pp a year** | −5.99 to +7.33 | −2.86 (16.83% / 19.69%) | +3.56 (18.51% / 14.95%) | **TIES** |
| **(a) NIFTY 100 index fund** (TRI less 0.25 pp a year) | 17.67% / 11.86% | **+5.82 pp a year** | −2.05 to +15.36 | +5.58 | +6.06 | **TIES** |

In the pre-registration's words, "ties" means the record cannot tell the two apart. For (b), the interval spans zero and the two halves have opposite signs. For (a), both halves are positive, but the interval includes zero, so "beats" is not met. **No trial is spent: the count stays at 202.** Research look L53 is closed.

The expectation written in §0 was that the book would be behind (b) or tied with it, and ahead of (a), perhaps distinguishably. The point estimates are +0.4 and +5.8; neither comparison is distinguishable.

## What tax does

| ₹10 lakh, FY 2026-27 rules | Book | (b) momentum fund | (a) NIFTY 100 fund |
| --- | --- | --- | --- |
| CAGR before tax, sold at the end | 20.55% | 18.10% | 12.39% |
| CAGR after tax, sold at the end | 17.67% | 17.28% | 11.86% |
| **Tax drag** | **2.87 pp a year** | 0.81 | 0.54 |
| Terminal wealth after tax, from ₹10 lakh | ₹1.298 crore | ₹1.232 crore | ₹58.4 lakh |
| Tax paid year by year, plus interest | ₹20.40 lakh + ₹1.23 lakh | nil (15 harvests) | nil (15 harvests) |
| Tax owed on the final sale | ₹4.07 lakh | ₹14.13 lakh | ₹4.55 lakh |

- **Break-even.** Before tax the book led (b) by 2.45 pp a year and (a) by 8.15 pp. Tax takes 2.06 pp a year more from the book than from (b), and 2.34 pp more than from (a). So the book must beat the momentum fund by about **2.1 pp a year before tax** just to tie after tax, and the NIFTY 100 fund by about 2.3. The research sweep's stylised estimate was +2.3 to +2.8.
- **Where the book's tax came from.** Its sales realised ₹1.48 crore of short-term gains against ₹1.03 crore of short-term losses. They realised ₹76 lakh of long-term gains, of which ₹10.6 lakh fell inside the exemptions, and ₹6.4 lakh of dividends taxed at 31.2% in the settled years. 6.4% of its sales were long-term.
- **Interest.** Twelve of the sixteen settled years owed at least ₹10,000 and paid 6.05% interest under sections 234B/234C: ₹1.23 lakh in all.
- **The funds.** They paid nothing until the end. Every year's harvest realised gains inside the ₹1.25 lakh exemption and reinvested them.

## Momentum fund (b), before and after its launch

| Window | Book after tax | (b) after tax | Difference | 95% interval |
| --- | --- | --- | --- | --- |
| 2010-03 to 2020-08, the index is NSE's backtest (126 months) | 12.86% | 15.73% | −2.87 pp | −10.58 to +4.82 |
| 2020-09 to 2025-11, the index is live (63 months) | 27.92% | 20.44% | +7.48 pp | +0.56 to +16.41 |

As the pre-registration read it in advance, after 2020-08-25 the index is a live product and the book is still a backtest of a rule chosen with these years in view. A book advantage in that window is overstated, not understated. Before the launch, when both are backtests, the fund was ahead.

## The actual UTI fund (c), beside a fresh fund (b), from 2021-04-01 (56 months)

| After tax, ₹10 lakh | CAGR | Minus UTI (c) | 95% interval |
| --- | --- | --- | --- |
| UTI Nifty200 Momentum 30 Index Fund, Direct (c) | 16.88% | — | — |
| Fresh fund (b), TRI less 0.5 pp, started 2021-04-01 | 16.76% | −0.13 pp | −0.45 to +0.30 |
| The book, its liquidation values over the same months | 21.39% | +4.51 pp | −2.65 to +15.44 |

The real fund did slightly better than the TRI less 0.5 pp a year, so the assumed tracking difference is, if anything, a little harsh on the fund. With a tracking difference of −0.3 pp a year (information), (b)'s after-tax CAGR is 17.51% and the book leads it by +0.16 pp a year (−6.02 to +6.97).

## Information only: ₹1 lakh, and the regime of each year

| Block | Book after tax | Book minus (b) | 95% interval | Halves | Book minus (a) | 95% interval |
| --- | --- | --- | --- | --- | --- | --- |
| ₹1 lakh, FY 2026-27 rules | 18.21% | +0.33 pp | −6.24 to +7.77 | −3.14 / +3.74 | +5.83 pp | −2.29 to +15.77 |
| ₹10 lakh, each year's regime | 18.61% | +1.16 pp | −5.38 to +8.64 | −2.08 / +4.30 | +6.70 pp | −1.46 to +16.82 |
| ₹1 lakh, each year's regime | 18.80% | +0.93 pp | −5.78 to +8.55 | −2.40 / +4.18 | +6.46 pp | −1.83 to +16.70 |

- At ₹1 lakh the book's tax drag is 2.12 pp a year, and its break-even over (b) is 1.90 pp. The ₹1.25 lakh exemption covers a larger share of a small account, and fund (a) pays almost nothing.
- Under each year's regime the book pays less: long-term gains were exempt until March 2018, short-term gains were taxed at 15% until July 2024, and dividends were untaxed until March 2020.

No verdict is read from these blocks.

## Benchmark realism: the book against the indices an investor can buy

Pre-tax, the book net of its trading costs, indices gross of any fee. Monthly means.

| 2020-09 to 2025-11 (63 months) | Mean excess | t | Months positive | Halves (31 / 32) |
| --- | --- | --- | --- | --- |
| Book minus N200M30 TRI | +0.78% | 1.63 | 54% | +0.63 (t 0.90) / +0.93 (t 1.39) |
| Book minus NIFTY100 EW TRI | +0.85% | 1.48 | 49% | +0.73 / +0.98 |
| Book minus its own EW-200 benchmark | +0.85% | 1.63 | 49% | +0.75 / +0.95 |
| *All 189 months, information:* book minus N200M30 TRI | +0.23% | 0.83 | 50% | −0.04 / +0.49 |
| *All 189 months:* book minus NIFTY100 EW TRI | +0.65% | 1.98 | 53% | +0.54 / +0.75 |

- Over the whole sample the book's edge over the momentum index is 0.23% a month, about 2.8% a year, with t 0.83. That is on the right side of the ~2.1 pp break-even, but it is not measured.
- Against its own equal-weighted benchmark the book's edge is 0.71% a month (trial 126). Against the NIFTY100 EW TRI it is 0.65%. So most of that edge does not depend on the choice of benchmark, but it is largely the momentum index's own edge.

## A proposal for the paper book's band, not applied

The band, `n × 0.71% − 2 × 3.89% × √n` against the equal-weighted 200, is unchanged by this look. These are proposals for the owner.

- **P1, the expected figure.** Against the book's own benchmark, the N200M30 index earned +0.685% a month in its backtest years (2010-03 to 2020-08, t 2.80) and +0.066% a month live (2020-09 to 2025-11, t 0.21). The shrinkage is **s = 0.096**, which gives a proposed expected figure of **0.07% a month** in place of 0.71%. Its 95% interval is **−1.00 to +1.23**. As written in advance, **s is close to uninformative**: the live window is too short to say whether a momentum edge shrank by 90% or not at all. If adopted, the floor would loosen from −14.8% to −18.6% at 6 months and from −18.4% to −26.1% at 12 months.
- **P2, a line against the fund.** An informational line of the book's cumulative pre-tax excess over the N200M30 TRI less 0.5 pp, expecting **+0.17% a month** (the 2.06 pp break-even), with a standard deviation of 3.80% a month. Its floor is −17.6% at 6 months and −24.3% at 12. Falling below it would mean the book is doing worse after tax than the fund would have.
- **P3, information.** The book's excess over the NIFTY100 EW TRI is in the table above.

## Turnover, counted by names (no position valued, no return read)

| Keep band / rebalance | One-sided turnover a year | Mean holding (median), days | Sales long-term | Sold in the 30 days before the 12-month line |
| --- | --- | --- | --- | --- |
| **Trial 126's own trades** (30, monthly, with its fill rules) | 2.18 | 165 (123) | 6.4% | 2.9% |
| 30, monthly | 2.18 | 165 (123) | 6.4% | 2.9% |
| 30, every 3 months (mean over phases) | 1.68 | 212 (183) | 10.1% | 8.9% |
| 30, every 6 months | 1.28 | 276 (184) | 15.2% | 23.8% |
| 45, monthly | 1.77 | 203 (154) | 10.3% | 4.1% |
| 45, every 3 months | 1.38 | 256 (184) | 16.2% | 11.2% |
| 45, every 6 months | 1.11 | 312 (188) | 20.5% | 27.8% |
| 60, monthly | 1.48 | 242 (212) | 17.2% | 4.9% |
| 60, every 3 months | 1.20 | 294 (273) | 22.2% | 14.3% |
| 60, every 6 months | 0.98 | 352 (364) | 26.8% | 28.7% |

- Even the slowest variant sells only about a quarter of its positions long-term.
- A six-monthly rebalance puts a quarter of its sales just short of the 12-month line. That is where a "tax-aware hold" rule (R2) would act.
- These are facts about turnover, not returns. A rule built on them would be a new configuration with its own pre-registration and trial number, and these figures will have been seen.

## Correlation with the IIMA factors

| Book's monthly excess over its benchmark with | All 189 months | First half | Second half |
| --- | --- | --- | --- |
| WML (momentum) | **+0.40** (+0.27 to +0.51) | +0.50 | +0.28 |
| HML (value) | −0.02 (−0.16 to +0.13) | −0.26 | +0.23 |

As information, a four-factor fit explains 30% of the excess: WML 0.45 (t 7.7), SMB 0.26 (t 4.1), market 0.14 (t 2.1), HML 0.10 (t 1.6), and an intercept of +0.06% a month (t 0.25). The book's excess moves with the published Indian momentum factor and tilts to smaller stocks; little is left once those are counted. Value's relation to it changed sign between the halves, so a value sleeve's diversifying power is not established here.

## Disclosures — read before relying on any number

1. **Lapsed losses.** None lapsed in any block, so a lapse-aware set-off order would have saved nothing. The book ends with no losses carried; they would have been valued at zero.
2. **The April tax sale (amendment 2, B3) costs the book, and more so at ₹1 lakh.**
   - At ₹10 lakh: 15 sales of between 0.3% and 5.8% of the book, costing ₹6,768 (₹3,436 of DP charges and ₹3,332 of sell charges), or 0.31% of the ₹21.6 lakh of tax and interest they raised.
   - At ₹1 lakh: ₹3,675, of which ₹3,436 is DP, or 2.4% of the ₹1.52 lakh raised.
   - The sales also realise gains a year earlier than the book's own trades would; that cost is not counted. It is a bias against the book.
3. **The April sale is modelled as delivery; in law some of it is intraday.** Part of it sells shares bought at the same session's close. In law that part nets intraday: speculative income at the slab rate, sell-side STT of 0.025%, no DP charge. It is a small slice of a small sale, with effects of mixed sign, and it is not corrected.
4. **The funds are harvested and the book is not.** The harvest is worth at most ₹16,250 a year to a fund. The book uses the exemption only through its own long-term sales: ₹10.6 lakh of exemption over 16 years at ₹10 lakh, against up to ₹20 lakh available.
5. **Surcharge.** At ₹10 lakh, fund (b)'s final sale realises ₹1.10 crore in one year, which triggers a 15% surcharge that the model does not charge (about ₹2.1 lakh). With it, (b)'s after-tax CAGR is about 17.15% and the book's lead about +0.52 pp a year. That figure is derived by hand and is not the registered one. Under each year's regime the same sale is ₹88 lakh (10%, about ₹1.1 lakh). The book's largest year is ₹40 lakh (FY 2023-24). The owner's other income could take that year past ₹50 lakh.
6. **Interest is approximated.** Instalments are not modelled; 6.05% is charged on each settled year's tax of ₹10,000 or more. The final sale's tax carries no interest. The book's gains realised from April to November 2025 would in fact have missed two instalments: at most about 1.8% of that year's tax, a small favour to the book.
7. **Corporate actions.** Bonus lots are dated the ex-date, not the allotment a day or two later. The two rights renunciations on held names are taxed at 20%. Dividends stay reinvested as trial 126's prices assume and are taxed at an assumed 31.2%.
8. **The book is a backtest; the funds after 2020 are not.** Trial 126's rule was chosen on these years and passed its own bar narrowly (t 2.51 against 2.394; at a family of 10 it would not clear). Its slippage of 0.05% a side is a judgement (#66); at 0.07% the pass would have failed. Live momentum indices in India kept a fraction of their backtest edge (R1: a median of about 20% across six indices; this look's P1: s = 0.10 with an uninformative interval).
9. **Section numbers.** The Income-tax Act, 2025, in force from 1 April 2026, renumbers the sections cited here. The sweep read the 2026 budget as leaving these rates and rules unchanged; that was not checked independently.
10. **Held-out exposure.** R1 to R4, this look's author and the reviewer have seen 2026 levels of these indices and of the UTI fund (see `trials.md`). A 2026 check of the book against these funds is partly seen.

## What this means for an individual choosing between the book and the fund

- **Against a Nifty200 Momentum 30 index fund, running the book would have left about the same money after tax.** Over these 15¾ years it is +0.4 pp a year, with the fund ahead in the first half and the book in the second. Tax and interest took 2.9 pp a year from the book and 0.8 pp from the fund, which used up most of the book's 2.45 pp lead before tax.
- **For the book to be worth running instead of that fund, it has to beat the momentum index by about 2 pp a year before tax, live.** Its backtest edge over the index was about 2.8% a year, not distinguishable from zero (t 0.83). The window in which the book looks clearly better is the one in which the book is a backtest and the index is live.
- **Against a plain NIFTY 100 index fund the book was ahead by 5.8 pp a year after tax, in both halves.** That is still not distinguishable at 95%, and most of it is what the momentum index itself earned over the NIFTY 100.
- **On after-tax return alone this measurement gives no reason to prefer the DIY book to the momentum index fund, and none to prefer the fund.** What it does not measure sits on the fund's side: the book's trading work, execution and slippage risk, about 33 sales a year to report as capital gains, nearly all short-term, and a backtest that has not yet run live. The book's own forward record against the momentum index, a line like P2, is what would change this reading.

This is a measurement of past data under stated assumptions, for the owner's decision. It is not investment advice.

## Files

| File | What |
| --- | --- |
| `data/l53_result.json` | The one pass: every block, comparison, window, proposal, turnover row and correlation |
| `data/l53_stage0.json`, `_run1.json`, `_run2.json` | Stage 0 runs 3, 1 and 2 |
| `backend/research/after_tax_l53.py`, `india_tax.py` | Harness and tax engine |
| `backend/research/data/l53/` | The input series cut before 2026, with the manifest |
| `backend/tests/test_after_tax_l53.py` | 44 tests, including the hand-worked tax cases |
