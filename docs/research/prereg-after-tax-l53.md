# Pre-registration — what is the momentum book worth to an individual after Indian costs and taxes, against the funds the owner could buy instead? (research look L53, no trial)

**Written 2026-10-01, after midnight IST, before any L53 code exists and before any after-tax figure, fund comparison or turnover split of the book has been computed on project data.** Asked for by the main session the same night, from the research sweep of 2026-09-30/10-01 (R1 to R4, section 0). The owner made the monthly momentum book (trial 126) the core of the product on 2026-09-30 (PR #228). Its first rebalance is at the close of 2026-10-01.

**What it is.** A measurement. It replays trial 126's own trade list through an Indian tax engine, puts it beside three index funds treated the same way, and reports what each leaves an individual after tax. It also measures the book against two public indices, some turnover facts of the rule, and its correlation with two published Indian factors.

**What it is not.** Not a strategy, not a new configuration, not a trial. It selects nothing: the book's rules, its trades and its benchmark are trial 126's, fixed before this was written. No order path, no config, no band and no rule of the paper book changes. Nothing here reaches the engine. **It is a measurement for the owner's decision, not investment advice.**

## 0. What had been seen when this was written

**Trial 126 (repaired panel, honest fills; `results-universe-width.md`, `data/momentum_width_A.json`).** Net excess over the equal-weighted 200 +0.71% a month (sd 3.89%, t 2.51, 189 months), CAGR 20.6% against 11.9%, 516 round trips, one-sided turnover 211% a year, costs 0.69% of the book a year. Halves +0.65% / +0.77% a month. At ₹1 lakh: CAGR 20.4%, excess +0.69% a month. The month-by-month values and holdings are published in that file. Its disclosure 8: "Tax is not modelled."

**The research sweep, 2026-09-30/10-01** (reports in the session's scratchpad, `research-synthesis/R1…R4`; raw work in `research-r1…r4/`). What it computed that touches this look:

| Source | What it read or computed | Figures |
| --- | --- | --- |
| R1 | NSE daily TRI of 16 indices **to 2026-09-30**, including NIFTY 100, NIFTY100 Equal Weight and NIFTY200 Momentum 30 (the files this look uses, cut before 2026) | N200M30 backtest excess over NIFTY 200 +6.1 pp a year (monthly +0.44%, t 1.95) against live +1.7 pp (+0.21%, t 0.64, 73 months to 2026-09); **N200M30 minus NIFTY100 EW TRI: −0.01% a month (t −0.02) over 2020-09 to 2026-09, and +0.41% a month (t 2.02) over trial 126's window 2010-02 to 2025-11**; drawdown episodes 2024–26; calendar-year returns 2021–2026 year to date |
| R1 | AMFI NAVs (mfapi) of 43 direct funds **to 2026-09-29**, including UTI Nifty200 Momentum 30 Index Fund (scheme 148703, used here, cut before 2026) | Tracking difference against the TRI 1y/3y/5y −0.53 / −0.34 / −0.30 pp; UTI fund 5y 9.0% against NIFTY 100 TRI 7.1%; Nifty 100 funds −0.18 to −0.29 pp |
| R1 | IIMA four-factor library, release 2025-12 (the file used here) | WML +1.09% a month 1994–2025; big-stock WML post-2013 +0.35% (t 0.71), 2020-09 to 2025 +0.20%; 2025 WML −5.5%, HML +11.4% |
| R1 | A stylised after-tax model (`taxmodel2.py`: 10 years, 90% of gains realised a year, 0.9% dividend yield at 31.2%) | The book needs +2.4 to +2.7 pp a year more pre-tax than a harvested fund to tie |
| R4 | The same kind of stylised arithmetic; a rounded index series from a third-party repository | Break-even +1.64 to +2.76 pp by account size and harvesting; "N200M30 ~21.8% a year 2010-02 to 2024-05, mostly NSE backtest, against the book's 20.6% 2010–25"; IIMA corr(HML, WML) −0.47 over 2010-02 to 2025-11 |
| R2 (F5) | Arithmetic only | Average holding ~5.6 months, so gains mostly short-term; 20.6% pre-tax → ~16–17% after tax; tax 4–6× the modelled trading cost |
| R3 | Arithmetic only | Tax drag 1.5–3 pp a year against a held index fund |

No research agent read `momentum_width_A.json`'s trade list or holdings, computed the book's return against any index, or replayed any trade through a tax engine (a search of their working directories for the file finds only the R1 summary's mention of it).

**Held-out exposure that touches this look** (to be added to the held-out log of `trials.md` with this look): R1 read the three TRI series and the UTI fund's NAV through September 2026 and computed live-period statistics that include 2026 (above); R1, R2 and R4 read NSE factsheets dated 2026-09-30 (1-year and year-to-date returns). **This look reads no 2026 row** (section 2), but a later 2026 check of the book against these indices or funds is partly seen.

**What the author of this text saw of the data**, none of it a result: the date fields of the three TRI files and the NAV file (rows per year, first dates: NIFTY 100 and NIFTY100 EW from 2003-01-01, N200M30 from 2005-04-01, the UTI fund from 2021-03-12; 185 TRI rows and 184 NAV rows dated 2026); the IIMA file's header, its first rows (1993–94) and its last date labels (to 2025-12). **While checking the file formats, the first 600 bytes of the N200M30 TRI file and of the UTI NAV file were printed. They show the TRI on 25–30 September 2026 (37,144.93 to 38,030.13) and the NAV on 18–29 September 2026 (20.49 to 21.28).** No statistic was computed from them. This is logged as held-out exposure. The code of `momentum_width.py`, `momentum_3i.py` and `nse_prices.py`, and the paper book's definition, were read.

**The expectation, written now.** From R1 and R4: after tax the book is behind the Nifty200 Momentum 30 fund or not distinguishable from it, and ahead of the Nifty 100 fund, perhaps distinguishably. The book pays short-term tax most years; the funds pay almost nothing until they are sold.

## 1. The question

Over trial 126's own months, for an individual with ₹10 lakh (and, as a second column, ₹1 lakh):

1. What after-tax compound return did the book leave, on its own trades, under the tax rules of FY 2026-27?
2. What would the same money have left in (a) a NIFTY 100 index fund, (b) a Nifty200 Momentum 30 index fund, and (c) the actual UTI Nifty200 Momentum 30 Index Fund over its life, each held and harvested every year?
3. Against the two public indices a realistic investor could buy, how large was the book's pre-tax edge in 2020-09 to 2025-11, next to its edge over its own equal-weighted benchmark?
4. How much would a wider keep band or a slower rebalance cut turnover and lengthen holdings (no return read)?
5. Does the book's excess move with the published Indian momentum and value factors?

## 2. Data, fixed

Every series is cut before **2026-01-01**. Nothing dated 2026 is read.

| Series | Source | Use |
| --- | --- | --- |
| Price panel | `nse_prices.load(wide=True)`, the repaired panel of trial 126 (cached `nse_prices_wide.pkl` in the main checkout's `backend/data/bhav_daily/`, read-only; the harness refuses to run if the cache is missing, so the loader never writes) | The book's replay |
| Corporate actions | The panel's own `events` list (NSE's files to 2025) | Dividends, bonuses, splits, rights, demergers on held lots |
| NIFTY 100 TRI | NSE (niftyindices `getTotalReturnIndexString`), R1's download `research-r1/tri/NIFTY_100.json` | Fund (a) |
| NIFTY200 Momentum 30 TRI | R1's download `tri/NIFTY200_MOMENTUM_30.json`; a second download `tri_test.json` for a hand check | Fund (b), section 8 |
| NIFTY100 Equal Weight TRI | R1's download `tri/NIFTY100_EQUAL_WEIGHT.json` | Section 8 |
| UTI Nifty200 Momentum 30 Index Fund, Direct, Growth (AMFI scheme 148703, ISIN INF789F1AUT5) | AMFI NAVs via mfapi.in, R1's download `nav/148703.json` | Fund (c) |
| IIMA four factors, monthly, survivorship-bias adjusted, release 2025-12 | R1's download `iima/2025-12_FourFactors_and_Market_Returns_Monthly_SurvivorshipBiasAdjusted.csv` | Section 10 |

**The cut, and how it is proven.** A `--prepare-data` step reads each downloaded file, parses **only the date field** of each row, drops every row dated 2026-01-01 or later **before its value field is parsed**, and writes the kept rows (2009-01-01 to 2025-12-31; IIMA 2009-01 to 2025-12) to `backend/research/data/l53/` with a manifest: each source file's sha256, rows kept, and the count of rows dropped (a count, nothing else). Those files are committed before stage 0. Every later step reads only them. The loaders assert that no date is on or after 2026-01-01. Stage 0 proves it again (section 11) and a test proves that a 2026 row is refused.

**Dates.** Trial 126's month points are the fill sessions of its rebalances: 190 points, from the first session of March 2010 (the 2010-02 rebalance) to the first session of December 2025 (the 2025-11 rebalance). Its 189 monthly returns are labelled by the rebalance month that ends them, 2010-03 to 2025-11 (`momentum_width.py`). Every other series is read **on those same session dates**: the TRI or NAV of that date, or, if that date is missing, the latest one before it (stage 0 lists every substitution). A return labelled 2020-09 runs from the close of 2020-09-01 to the close of 2020-10-01, which is calendar September 2020 shifted by one session. That is how the IIMA months are matched (section 10).

## 3. The book, replayed

**The trade list is trial 126's.** The harness calls `momentum_width.simulate` unchanged, with trial 126's configuration (`PARTS["A"]`, E-3i ranks 1–200, 0.05% slippage a side, base fills H1–H5, start `2010-01`, the repaired panel and its universes). For the strategy book only, `simulate`'s `Book` is replaced by a subclass, `TaxBook`, which keeps FIFO tax lots beside the positions and pays tax from the account. The benchmark book is the original class. With tax switched off, `TaxBook` must give trial 126's values exactly (stage 0).

**What tax changes, and what it does not.** The names, dates and order of every trade are trial 126's: which stocks are sold and bought depends only on ranks and holdings, and the fill rules depend only on the price rows. What changes is the rupee size: tax paid out of the account leaves less cash for the buys that follow. The book's buy amount is still cash after the session's filled sells divided by the vacancies, as trial 126 fixes it.

**Lots, in the panel's adjusted share units.** The panel's `close` is a total-return price: dividends are reinvested in the paying stock on the ex-date, as trial 126 assumes. The replay keeps that assumption and accounts for it:

| On a held position | What happens to its lots | Tax |
| --- | --- | --- |
| Buy | a new lot: the adjusted shares bought, cost = amount paid **less STT** (stamp, exchange and SEBI charges, GST and slippage are part of the cost; STT is not deductible, section 48), dated the fill session | none |
| Sell (whole position; also an ended chain, rule H5, dated the month-end the book recognises it) | lots sold oldest first; each lot's consideration is its share of the sale value **less the sell-side charges and the DP charge, with STT added back** | a gain or loss per lot, short- or long-term by that lot's date |
| Dividend with factor f = 1 − D / previous close | each lot splits: a fraction f keeps its cost and date; a fraction 1 − f becomes a new lot, cost = its share of the dividend, dated the ex-date. The dividend is q × adjusted close(ex − 1) × (1 − f) rupees | the dividend is income of the financial year of its ex-date |
| Bonus a:b (factor b / (a + b)) | a fraction b/(a+b) keeps cost and date; a fraction a/(a+b) becomes a new lot at **nil cost, dated the ex-date** (section 55(2)(aa)(iiia); holding period from allotment) | none until sold |
| Rights (factor TERP / P) | treated as renouncing the entitlement at its theoretical value and reinvesting it: a fraction 1 − f becomes a new lot at cost equal to that value, dated the ex-date | the value is a short-term gain at nil cost on the ex-date (section 55(2)(aa)(A)) |
| Split, consolidation | none: adjusted units already carry cost and date | none |
| Demerger | none: the series puts the demerged value back into the parent; cost and date stay with the parent's lots | none |

The adjusted closes used are the panel's, so a lot's rupee cost and its rupee value are on the same basis.

**Tax is paid from the account once a year.** The tax of a financial year (1 April to 31 March) is paid on **the book's first fill session of the next financial year**, the fill of the March rebalance, which is the first session of April. It is paid after that session's filled sells and before its buys, out of cash. If cash is short, every holding is sold pro rata at that session's close to raise the rest, with every sell charge and one DP charge per scrip, and the gains realised fall in the new year. The payment is later than the advance-tax dates (15 June to 15 March); interest under sections 234B/234C is not charged. The number and size of pro-rata sales are reported.

**Two accounts.** ₹10,00,000 (primary) and ₹1,00,000, each simulated separately (trial 126's ₹1 lakh column is a separate run; DP is a fixed charge).

## 4. The tax engine, fixed

**Primary: the rules of FY 2026-27, applied to every year** (the forward question):

- Held for **more than 12 months** is long-term: a sale on the 12-month anniversary of the acquisition date is short-term, a sale the day after is long-term (12 calendar months; a 29 February acquisition reaches its anniversary on 28 February).
- **Short-term gains 20%, long-term gains 12.5% above ₹1.25 lakh a financial year, 4% cess** on the tax.
- **Set-off, in the most favourable order the law allows.** Within a year, short-term losses are set off against short-term gains first, then long-term gains; long-term losses only against long-term gains. Then brought-forward losses, oldest first, the same way (short-term against either, long-term against long-term only). Set-off is compulsory, including against long-term gains inside the ₹1.25 lakh exemption. The exemption applies to the long-term gain left after set-off.
- **Carry-forward** of unabsorbed short- and long-term losses for **8 financial years** after the year of the loss, then they lapse (reported).
- **Dividends** at an assumed slab rate of **31.2%** (30% plus 4% cess), as income of the year of the ex-date.
- Grandfathering (the 31 January 2018 value) is a transition rule of the real law and is **not** applied in the counterfactual where these rules always held.
- Costs as trial 126 charges them (Zerodha delivery, 2026): STT 0.1% each side, stamp 0.015% on buys, NSE 0.00307%, SEBI, 18% GST on those, slippage 0.05% a side, **DP ₹15.34 per scrip per sell**.
- Assumed: the book is the owner's only source of capital gains, so it uses the whole ₹1.25 lakh; total income stays at or below ₹50 lakh (no surcharge); the owner's other income already fills the lower slabs; returns are filed on time, so losses carry forward.

**Information only: the regime of each year**, applied to the same trades (the three accounts and both sizes):

| Financial years | Short-term | Long-term | Dividends | Cess |
| --- | --- | --- | --- | --- |
| to 2017-18 | 15% | exempt (section 10(38)); long-term losses neither set off nor carried | exempt (DDT regime) | 3% |
| 2018-19 to 2019-20 | 15% | 10% above ₹1 lakh; grandfathering: cost = max(cost, min(value on 31 Jan 2018, sale value)), the value being that day's highest price (NAV for a fund) | exempt | 4% |
| 2020-21 to 2023-24 | 15% | as above | 31.2% | 4% |
| 2024-25 | 15% to 22 July 2024, 20% from 23 July 2024, by sale date | 10% / 12.5% by the same date; ₹1.25 lakh for the whole year | 31.2% | 4% |
| 2025-26 | 20% | 12.5% above ₹1.25 lakh | 31.2% | 4% |

With two rates in 2024-25, losses and the exemption go to the higher-rate gains first.

The engine is a module of its own (`backend/research/india_tax.py`), with tests on hand-worked cases before any run (section 11, check 7).

## 5. The alternatives

Each is an account of the same size, started with cash at the book's first point (the first session of March 2010), valued on the book's point dates, and taxed by the same engine and the same payment date.

- **(a) NIFTY 100 index fund.** NAV = NIFTY 100 TRI × (1 − 0.25%) ^ (days since the start / 365.25): a tracking difference of −0.25 pp a year.
- **(b) Nifty200 Momentum 30 index fund.** The N200M30 TRI with a tracking difference of −0.5 pp a year. **Before the index's launch on 2020-08-25 the TRI is NSE's backtest.** The windows before and after launch are reported separately: returns labelled 2010-03 to 2020-08 (126 months, the backtest; the month that straddles the launch counts here) and 2020-09 to 2025-11 (63 months, live).
- **(c) The actual UTI Nifty200 Momentum 30 Index Fund**, Direct, Growth: its published NAV, no adjustment. Its first NAV is on 2021-03-12, so its account starts at the first book point on or after that date, the first session of April 2021 (the 2021-03 rebalance), and runs to the first session of December 2025: 56 monthly returns.

**Treatment, the same for all three.** Growth option, no dividends. Units are bought on the start date. **Every financial year the ₹1.25 lakh exemption is harvested** on the book's last point in that year (the first session of March): units held more than 12 months are sold oldest first until the year's long-term gain, after set-off, reaches the exemption, and the proceeds are reinvested at once in a new lot. A lot at a loss that is reached in that order is sold too, and its loss is set off or carried. Units held 12 months or less are not harvested. Redemptions pay STT of 0.001%; purchases pay stamp duty of 0.005% from 2020-07-01. No exit load, no DP charge. Under the historical regime a year whose long-term gains are exempt harvests every long-term lot.

## 6. Marking, and the headline

**Liquidation value.** At every point, each account is also valued as if it were sold that day: holdings at the close less every sell charge (one DP charge per scrip for the book), less the tax the current financial year would then owe on its realised gains, its dividends and the gains of that sale, after set-off, carry-forward and the exemption. At the first point it is the starting capital. At the last point it is the account's **after-tax terminal wealth**: everything sold at the close of the first session of December 2025 and the tax of FY 2025-26 settled.

From the 190 liquidation values of each account come 189 monthly after-tax returns. Deferred tax is counted as it builds up, so the fund's advantage (paying at the end) is valued at the end, not ignored.

**The headline, for (b) and for (a):** after-tax CAGR of the book minus after-tax CAGR of the fund, in percentage points a year, from the terminal liquidation values over 189 months (years = months / 12).

- **Interval:** a circular moving-block bootstrap of the paired monthly after-tax returns (book, fund), block length **12 months**, **10,000** resamples, seed **53**; each resample's two CAGRs and their difference; the **95% percentile interval**. The bootstrap resamples the returns, not the trades, so it does not re-run the tax engine; it describes how much the difference moves with the months that happen to be in the sample. Block lengths 6 and 24 are reported as information.
- **Both halves:** the first 94 returns (2010-03 to 2017-12) and the last 95 (2018-01 to 2025-11), each as the CAGR difference over its own months, from the same liquidation values.
- **Also reported:** pre-tax CAGRs (liquidated, no tax) and after-tax CAGRs of each account; **the tax drag** of each (pre-tax minus after-tax CAGR); **the break-even pre-tax margin**, the book's drag minus the fund's, which is how much more a year the book must earn before tax to tie after tax; tax paid by year and by kind (short-term, long-term, dividends); the terminal deferred liability; losses carried and lapsed; pro-rata sales; the ₹1 lakh columns; the historical regime; for (b), both windows around launch.
- **Fund (c)** is reported against the book's liquidation values over its 56 months (the book's value at the first session of April 2021 as the start), and beside fund (b) over the same months, which shows how the actual fund compares with the TRI less 0.5 pp. Its interval is computed the same way; no verdict is read from it.

## 7. The reading rule

For each of (b) and (a), at ₹10 lakh under the forward rules, with D the headline difference, [L, U] its 95% interval, and D₁, D₂ the two halves:

| Verdict | Condition |
| --- | --- |
| **The DIY book beats the fund after tax** | D > 0, **L > 0**, and D₁ > 0 and D₂ > 0 |
| **The DIY book loses to the fund after tax** | D < 0, **U < 0**, and D₁ < 0 and D₂ < 0 |
| **Ties: the record cannot tell them apart** | anything else. Reported with the sign of D, the interval, and which half disagrees if one does |

The two comparisons are read separately and are not corrected for each other: neither selects anything. The ₹1 lakh account, the historical regime, the windows around launch and fund (c) are reported the same way and are information: no verdict is read from them.

**How to read "ties".** The interval is expected to be wide: a monthly difference with a standard deviation near 3% gives roughly ±5 pp a year over 15.75 years. "Ties" then says the sample cannot separate the two by less than about that much. It does not say they are equal. Nothing in this look measures what a tie leaves to decide: the work and the execution risk of running the book, how far slippage differs from 0.05% (#66), and how much a backtest shrinks when it goes live. Those remain for the owner.

**The windows around launch, read in advance.** After 2020-08-25 the index is a live product and the book is still a backtest of a rule written in 2026 and tested on these years. A book advantage in that window is therefore overstated, not understated. Before the launch both are backtests.

## 8. Benchmark realism, and a proposal for the band

**Measured, pre-tax, net of the book's trading costs:** the book's monthly return minus (i) the N200M30 TRI, (ii) the NIFTY100 EW TRI, and (iii) its own equal-weighted-200 benchmark (trial 126's excess), over the 63 returns labelled **2020-09 to 2025-11**: mean, standard deviation, t, share of months positive, and both halves (31 and 32 months). The same over the full 189 months as information, and against the funds (TRI less the tracking difference) as information. Indices are gross of any fee; the book is net of its costs.

**How it feeds the paper book's band, fixed now. These are proposals for the owner. This look does not change the band** (`n × 0.71% − 2 × 3.89% × √n` against the equal-weighted 200).

- **P1, the band's expected figure.** Trial 126's 0.71% a month is a backtest mean over the years it was designed on. The nearest public implementation of the same signal, the N200M30 index, has a backtest (to 2020-08) and a live record (from 2020-09). Its shrinkage is measured against the book's own benchmark: s = mean(N200M30 TRI − EW-200, 2020-09 to 2025-11) / mean(N200M30 TRI − EW-200, 2010-03 to 2020-08), using trial 126's benchmark series for EW-200. **If the backtest mean is positive, the proposal is an expected figure of 0.71% × s, with s clipped to [0, 1]**, and the same 3.89% standard deviation. If the backtest mean is zero or negative, no P1 proposal is made. Both means and their t are reported, and so is the book's own mean over 2020-09 to 2025-11 (which is in-sample for the book and is not used).
- **P2, a second line against the fund.** An informational line of the book's cumulative pre-tax excess over the N200M30 TRI less 0.5 pp, with an **expected figure equal to the break-even margin of section 6** (forward rules, ₹10 lakh, (b); converted to a monthly rate), the standard deviation of the book's monthly excess over the N200M30 TRI over 189 months, and a floor at 2 standard errors below it. Falling below that floor would say the book is doing worse after tax than the fund would have. If the break-even margin is zero or negative, P2's expected figure is 0.
- **P3, information.** The book's excess over the NIFTY100 EW TRI says how much of its edge over the equal-weighted 200 depends on that benchmark. R1 suggested showing the N200M30 and NIFTY100 EW TRIs on the paper book's page; that is a product decision for the owner.

## 9. Turnover diagnostics (no return is read)

For keep bands **30, 45 and 60** and rebalancing **every 1, 3 and 6 months**, over the rebalances 2010-02 to 2025-11: the rule's own decisions (E-3i ranks 1–200, trial 126's signal, 15 names, sell a holding that leaves the 200 or whose rank passes the band, buy from the top). Every order is assumed to fill at the next session (no fill rules), and a chain that ends is sold at the month-end it is found. **No price is used except inside the signal, no position is valued, and no return is computed.** Counted by names:

- one-sided turnover: names sold a year / 15;
- holding period of each closed position (fill session to fill session): mean and median in days;
- **share of sales that would be long-term** (more than 12 months, section 4's date rule), and the share sold in the 30 days before the 12-month line;
- positions still open at the end, and their ages.

Rebalancing every 3 or 6 months counts from 2010-02 (phase 0); the mean over all phases is reported beside it. Trial 126's own trade list (with its fill rules) is reported in the same terms, and beside it the band-30, monthly row, to show what the fill rules change.

## 10. Correlation with the IIMA factors

The book's monthly net excess over its benchmark (trial 126's series, labels 2010-03 to 2025-11) against IIMA's WML and HML of the same calendar months: Pearson correlation with a 95% interval (Fisher z), for the full 189 months and both halves. As information: a least-squares fit of the excess on MF − RF, SMB, HML and WML, with plain t statistics. **Nothing is decided from this.** A positive correlation with WML says the book's excess moves with the published momentum factor; the sign against HML says whether a value sleeve would diversify it (R4's note).

## 11. Stage 0 — before any after-tax figure, fund comparison, turnover split or correlation; each check a halt

1. **Inputs cut before 2026.** The prepared files match their manifest (sha256); every date in them, and every panel session, is before 2026-01-01; the IIMA series ends at 2025-12. The count of rows each source had on or after 2026-01-01 is reported (from the date field only).
2. **Trial 126 reproduced.** `momentum_width.simulate`, called unchanged, gives the 190 strategy and benchmark values of `momentum_width_A.json` to within 1e-12 relative, the same holdings every month and the same book counts (531 buys, 516 sells, 2 ended chains, 7 buys and 9 sells carried at a band, 14 sells filled from a trade-for-trade row). The ₹1 lakh run gives the recorded ₹1 lakh CAGR and mean excess to 1e-12.
3. **The replay with tax switched off.** `TaxBook` without a tax rule gives the same 190 strategy values as check 2 to within 1e-12 relative, at ₹10 lakh and at ₹1 lakh. At every point, each position's lots add up to its shares (1e-9 relative). Over the whole run, the pre-tax liquidation value equals the starting capital plus every realised and liquidation gain plus the dividends less the STT paid, to within ₹1. **Only the residual of that identity is written, not its parts.**
4. **Coverage.** Each TRI has a row on each of the 190 point dates, and the UTI NAV on each of fund (c)'s 57; halt if more than 3 dates of a series need the latest earlier row, or if any such row is more than 5 calendar days old. Every substitution is listed. At least 240 TRI rows in each year 2009–2025; no duplicate dates; every value positive and finite. IIMA has numeric WML, HML, SMB, MF and RF for every label 2010-03 to 2025-11.
5. **Hand checks of the data.** The TRI base values (NIFTY 100 and NIFTY100 EW = 1,000 on 2003-01-01; N200M30 = 1,000 on 2005-04-01). The two downloads of the N200M30 TRI agree on every date before 2026-01-01. The UTI fund's first NAV is within 5% of ₹10.
6. **Hand checks of the lots.** On seeded corporate-action events on held positions (up to three of each kind: dividend, bonus, split, rights), a separate path reads the printed prices from the bhavcopy zip and the event row from NSE's corporate-actions CSV, and recomputes the actual shares held and the dividend in rupees (or the bonus shares). It must equal the replay's figure to 1e-6 relative. No gain is computed.
7. **The tax engine's hand-worked cases** (`tests/test_after_tax_l53.py`: FIFO, the 12-month boundary, set-off order, the exemption after set-off, carry-forward and lapse, dividends, the historical regime and grandfathering, the pro-rata tax sale, the fund harvest) pass; the record keeps the test run's summary.
8. **Information, not a check:** events on held positions by kind; the tax payment dates; the points in each financial year.

Stage 0 is written to `docs/research/data/l53_stage0.json`, committed and pushed. **The run then stops for an independent review** of this text, the code and the stage 0 record. The measurement pass starts only after that review, on the main session's instruction. A finding is fixed by a dated amendment before any L53 figure exists.

## 12. One run

One measurement pass computes sections 6 to 10 together. It writes `docs/research/data/l53_result.json` with status STARTED before it replays any tax, and refuses to start if that file exists, or if the stage 0 record or the harness is missing, not committed or changed since its commit. A re-run only for a crash before any figure was printed, or a declared bug with both runs recorded. Nothing in sections 2 to 10 changes after the first number is seen. The results note is written after the pass.

## 13. Compute

On the Mac, from the worktree, reading the main checkout's panel cache read-only through `SAHAB_RESEARCH_DATA`, at `nice 15`, with a throwaway `SAHAB_DB_PATH`. The Mac runs the trading engine from 08:30 to 15:45 IST; heavy work runs outside those hours. No Kite call; no key or token read; nothing imports `app`.

## 14. Trial accounting

Research look **L53**. It selects nothing, so it spends **no trial: the count stays at 202.** Nothing here can pass or fail a strategy. If the owner later wants a rule that uses tax (for example the "tax-aware hold" R2 proposes), that is a new configuration with its own pre-registration and trial number, and this look's turnover facts will have been seen.

## 15. Choices this text makes that its sources left open

Listed for the reviewer, so each can be challenged before any number exists:

1. **DP charge.** The request said "₹15.34 + GST". ₹15.34 already includes GST (₹13 + 18%; `momentum_3i.DP_PER_SELL`, Zerodha's tariff read by R1), and trial 126 charges it. No further GST is added.
2. **Dividends stay reinvested**, as trial 126's total-return prices assume; they are taxed as income, and the reinvested part is a new lot at the ex-date. The alternative (dividends paid out and held as cash) would change trial 126's pre-tax series.
3. **Bonus shares at nil cost from the ex-date, rights as a renunciation, demergers and splits carried.** The legal treatment of bonus shares is applied; the other two are simplifications (both are rare on held names; counted in stage 0).
4. **Tax paid at the first April fill, from cash, with a pro-rata sale if short**, rather than in advance-tax instalments.
5. **Liquidation value as the headline**, so the funds' deferral is valued at the end and not ignored; the halves are slices of the same liquidation values, so they compound to the headline. A fresh investor starting in the second half would carry no losses from the first; that is not modelled.
6. **The funds are harvested on the book's March point every year**, oldest units first, including lots at a loss that come first in that order.
7. **Fund (c) starts at the first session of April 2021**, the first book point after its first NAV, and is compared with the book's liquidation values over the same months.
8. **No grandfathering under the forward rules**; grandfathering only in the historical regime.
9. **The bootstrap resamples months, not trades**, block 12, percentile interval at 95%.
10. **P1's shrinkage uses the index's backtest-to-live ratio against the book's own benchmark**, not the book's own recent mean, because the book's recent months are in-sample for it.
11. **Turnover diagnostics ignore the fill rules** and count names, not rupees, so that no position is valued; the fill rules' effect is shown on trial 126's own configuration.
