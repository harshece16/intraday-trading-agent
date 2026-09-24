# 3f stage 0 — feasibility. 0c source: CONFIRMED. 0b membership: PASS (95.17%). 0c vendor check: **HALT as pre-registered** (38% of stocks ≥ 0.98). No look, no trial.

**2026-09-24.** Pre-registration: `prereg-3f-momentum-delivery.md` with
amendments 1 and 2. Stage 0 reads no forward return; nothing here is a look
or a trial. Every gate below is reported as the pre-registration wrote it,
then diagnosed. **3f stops here for the reviewer.** Stage 1 is not run.

| Gate | Rule (verbatim from the prereg) | Result |
| --- | --- | --- |
| 0c source | "Stage 0 must confirm that from an NSE source and cite it" — hard halt (amendment 1 §A) | **CONFIRMED**, NSE-hosted, §1 |
| 0c regime change | "a mid-window closing-price change truncates the window" (amendment 2) | **No change inside 2010–2025**; the first change is the 2026-08-03 closing auction, §1.3 — no truncation |
| 0b membership | "reconstructed for every month from its start date through Dec 2025" | **Done**, 2009-01 → 2026-09, both chains consistent, §2 |
| 0b start date | "the later of 2010-01-01 and the first month with complete membership" | **2010-01** |
| 0b coverage | "adjusted daily closes exist for ≥ 95% of member-months (delisted and merged names included)" | **95.17%** — PASS by 0.17 points; 92.1% in 2010–17, §3 |
| 0c vendor | "correlation of daily close-to-close returns (yfinance vs the cache's last bar each session) must be ≥ 0.98 for ≥ 95% of stocks. Otherwise stop and report." | **38.0%** — **HALT**. Diagnosed in §4: the cache is dividend-adjusted and its last bar is a last trade, not the close |

## 1 — 0c: the closing price, from NSE's own documents

### 1.1 The rule, for the whole window

NSE's consolidated Capital Market trading circulars carry one paragraph,
"Daily Closing Price", unchanged in wording across the three editions I
could retrieve. Quoted verbatim from NSE/CMTR/61813 (April 29, 2024), §3.4:

> Closing price is calculated only for securities/contracts traded for the
> day. The closing price is last half an hour value weighted average price.
> In case security is not traded in last half an hour, last traded price of
> the day is the close price. In case security is not traded for the day,
> the latest available close price is considered as the close price for
> that day.

The same four sentences appear as §3.4 of NSE/CMTR/67774 (April 30, 2025)
and in NSE/CMTR/40962 (May 9, 2019). Each consolidated circular states that
it replaces the previous one (61813 replaces 57270 of June 26, 2023), so the
chain runs back to 2019 without a change to this paragraph.

For the start of the window, NSE's *Fact Book 2010* (section 6,
`archives.nseindia.com/content/us/fact2010_sec6.pdf`), describing F&O
settlement, says:

> The closing price of the underlying Index/security is currently its last
> half an hour weighted average value in the Capital Market Segment of NSE.

So the same definition is attested at both ends of 2010–2025 and at 2019 in
between. **Hosting caveat:** the 2019, 2024 and 2025 circulars are on
`nsearchives.nseindia.com` as zip files; the 2010 Fact Book is on
`archives.nseindia.com`. Both are NSE domains. Circulars from between 2010
and 2019 (e.g. CMTR/15981, CMTR/22748) return 404 at NSE's current circular
URLs and were **not** retrieved — the continuity claim for 2011–2018 rests on
the two ends plus the unchanged wording, not on a document from every year.

### 1.2 The open — a call auction, so barred by the tradability rule

NSE/CMTR/67774 §1.1: "The pre-open session with call auction mechanism is
applicable to all equity market securities including SME securities, partly
paid-up securities, and InvITs/REITs." SEBI CIR/MRD/DP/21/2010 introduced
the pre-open call auction for Nifty and Sensex stocks from October 18, 2010,
and SEBI CIR/MRD/DP/6/2013 extended it to all non-illiquid scrips from April
1, 2013 — **both read from secondary mirrors, not retrieved from
sebi.gov.in**, whose DNS fails from this machine. This confirms amendment 1
§A's reason for keeping the close: the next-session open is a call-auction
print for the whole window (for Next 50 names only from April 2013).

### 1.3 The first change: the closing auction, effective August 3, 2026

SEBI circular SEBI/HO/47/11/11(3)2025-MRD-POD2/I/2765/2026 (January 16,
2026) introduces a Closing Auction Session (CAS); NSE/CMTR/73362 is the
exchange's SOP. From 73362 §1.1: "CAS shall be made applicable in a phased
manner. Initially, the closing […] segment on which derivative contracts are
available" — i.e. the first phase covers stocks with derivatives, and the
old method continues for the rest. Its reference price (§2.1) is "the
trades executed in the stock during the period 3:00 p.m. to 3:15 p.m." This
is outside the selection window (through December 2025), so **amendment 2's
truncation is not triggered**. It does mean that a live 3f from August 2026
would fill into an auction, not the 30-minute VWAP the backtest assumes —
which the prereg's "What 3f cannot establish" already lists.

## 2 — 0b: point-in-time NIFTY 100, rebuilt from NSE Indices' press releases

Code: `backend/research/nifty100_membership.py` (14 tests in
`backend/tests/test_nifty100_membership.py`, each a layout or rule that broke
the real rebuild). Artefacts in `backend/research/data/`:

| File | What |
| --- | --- |
| `nifty100_membership.csv` | the prereg's format — `symbol, from, to, source_in, source_out`: 272 spells over 204 symbols |
| `nifty100_membership_monthly.csv` | the union in force at each month end, 2010-01 → 2026-09 (201 snapshots: 140 of 100 names, 61 of 101 with the Tata Motors DVR) |
| `nifty100_changes.csv` | all 894 inclusion/exclusion events with the release that announced each |
| `nifty100_manual_events.csv` | 20 rows transcribed by hand from the one image-only release (August 23, 2021), source noted per row |
| `nifty100_membership_build.json` | the walk's consistency report, the 23 superseded/voided announcements, the 4 cross-check differences |

**Method.** 547 press releases (`niftyindices.com/Press_Release/ind_prsDDMMYYYY.pdf`,
2009 onward; not committed) → `pdftotext -layout` → parse the "Nifty 50" and
"Nifty Next 50" sections (older names "S&P CNX Nifty", "CNX Nifty Junior")
→ walk each index **backwards** from today's constituent list. Before a
change, the set is (current − inclusions) + exclusions, and at every step
the count must be exactly 50 (51 with the DVR), every inclusion walked back
must already be a member and no exclusion may be. One missed release breaks
the chain, so the chain's length is the proof:

- Nifty 50: consistent at every step back to **2009-01-12**.
- Nifty Next 50: consistent at every step back to **2009-01-12**.
- Nifty 100 = union, plus the DVR when the releases put it in Nifty 100 alone
  (2016-04-01 → 2020-06-25, 2023-09-29 → 2024-08-29). The releases' own
  explicit "Nifty 100 / CNX 100" sections were used only as a cross-check:
  51 sections checked, 4 differ, all four being the DVR overlay dates.

**Rules taken from the releases themselves** (in the module docstring): a
change announced twice for one stock is one change and the later release
holds (Yes Bank's removal brought forward to March 19, 2020); the Feb 18,
2020 review was deferred by the May 13, 2020 release and re-announced on
June 10, 2020 with a different list, so the Feb 18 announcement is voided;
corporate-adjustment dummies (a spun-off entity at a notional price for a
few sessions) are ignored. Symbol changes use NSE's `symbolchange.csv`;
names NSE's files no longer resolve (Sesa Goa → VEDL, Satyam, Ranbaxy …) are
a short hand map in the module.

**Start date: 2010-01** — membership is complete from 2009-01, so the rule's
"later of" is January 2010.

## 3 — 0b coverage: 95.17% — a pass, but read the first half

Adjusted closes: yfinance daily, `auto_adjust=False`, `<SYMBOL>.NS`, 219
symbols requested, 195 returned data, 24 returned nothing. Signal date = the
last session of the month.

| | member-months | with a close | |
| --- | --- | --- | --- |
| 2010-01 → 2025-12 | 19,261 | 18,330 | **95.17%** — gate ≥ 95% **PASS** |
| 2010 → 2017 | 9,621 | 8,860 | 92.1% |
| 2018 → 2025 | 9,640 | 9,470 | 98.2% |
| 2010 alone | 1,200 | 1,035 | 86.2% |

Every missing member-month belongs to a name yfinance has **no history at
all** for — 20 symbols, all delisted, merged or renamed before yfinance's
coverage: HDFC (162 months, the largest weight in the index for the whole
period until its July 2023 merger), Cairn India (82), Reliance Capital (75),
GSK Consumer (72), Piramal Enterprises (71), Aditya Birla Nuvo (69), IDFC
(64), the Tata Motors DVR (61), Ranbaxy (58), Jaiprakash Associates (50),
Andhra Bank and Sterlite (32 each), Patni and Syndicate Bank (21), Punj
Lloyd (18), Corporation Bank (14), ING Vysya (11), RNRL (9), Mindtree (6),
Moser Baer (3). No member with data starts late.

**What the pass means.** The gate is met, by 0.17 points. But the 4.83% that
is missing is not random: it is exactly the set of names that left the
index by failure or absorption, so the residual survivorship the prereg
accepts ("at most 5%, by stage 0b's gate") is concentrated in the **first
half of the sample (7.9% there, 13.8% in 2010)** — the half the stage-1 gate
needs to clear on its own. This is reported, not decided: the reviewer may
want either (a) the gate applied per half, which 2010–17 would fail, or (b)
the 20 names filled from NSE's own bhavcopy archive (unadjusted closes are
there for every one of them; splits and bonuses would need NSE's
corporate-action file), which is a bounded piece of work and would remove
the residual entirely.

## 4 — 0c vendor check: HALT as written; the pre-registered comparator is the wrong instrument

Code: `backend/research/step3f_stage0_checks.py` (reads no forward return;
its inputs are local sqlite files built outside the repo and are not
committed). Window 2024-09-20 → 2025-12-31, 318 sessions.

### 4.1 As pre-registered

yfinance Close vs the Kite 5-minute cache's last bar each session, 100
stocks in the cache: **38 of 100 stocks ≥ 0.98; median correlation 0.977.
Gate ≥ 95% — FAIL → HALT.** Restricting to sessions whose last cached bar is
the 15:25 bar (30,853 stock-sessions) does not change it.

### 4.2 Why — two properties of the cache, neither a vendor disagreement

1. **The Kite cache is dividend-adjusted.** COALINDIA on 2024-11-04:
   yfinance Close 443.30, NSE bhavcopy official close **443.30**, Kite last bar
   **416.40**. The Kite/yfinance ratio steps on exactly the ex-dividend dates
   (0.939 → 0.974 on 2024-11-05, → 1.001 on 2025-11-04) and each step
   equals yfinance's own adjustment-factor step (1.0366 vs 1.0367). So the
   cache's history is back-adjusted for dividends as of the day it was
   fetched, which is why the level gap shrinks to nothing by late 2025.
   Comparing Kite against yfinance's Adj Close instead does not lift the
   correlation (38 → 38), because the steps are only a few days a year.
2. **The last 5-minute bar is a last trade, not the official close.** The
   official close is the last-30-minute VWAP (§1.1). The two differ by a
   typical 0.10–0.15% each day, and a 0.14% daily noise against a 1.3%
   daily volatility is enough on its own to hold a return correlation near
   0.977 — which is where the median sits. The names below 0.98 with a
   near-zero level gap (ICICIBANK 0.953, SBILIFE 0.940, SHREECEM 0.943 …)
   are this effect and nothing else.

Two demergers add outliers the prereg did not anticipate: ITC (0.798 —
ITC Hotels, January 2025; yfinance does not adjust the Close for a demerger,
Kite does) and Siemens (0.845 — Siemens Energy, April 2025).

### 4.3 Against the primary source instead — reported, not substituted

NSE's daily bhavcopy (`BhavCopy_NSE_CM_0_0_0_<date>_F_0000.csv.zip`, 318
files, EQ rows, downloaded for this check) gives the official close for 193
of the 219 symbols in the window.

| Comparison | stocks ≥ 0.98 | median corr |
| --- | --- | --- |
| yfinance Close vs bhavcopy close, raw | 163 / 193 (84.5%) | 0.9959 |
| same, excluding the one split/bonus day per affected stock (19 days, unadjusted on the NSE side, adjusted on yfinance's) | **181 / 193 (93.8%)** | 0.9959 |
| Kite last bar vs bhavcopy close | 56 / 193 (29.0%) | 0.9819 |

On **99.4% of stock-days yfinance's Close equals NSE's official close to
within 0.5%** (58,802 compared; 334 differ by 0.5–20%). The 334 are
concentrated: ITC 72 days (post-demerger), CONCOR 67 (a bonus yfinance
applied late), and **one bad row across many stocks on 2025-03-18**
(ICICIBANK 1,269.00 vs NSE 1,309.85; M&M, HAVELLS, UPL likewise) — a
yfinance data fault on a single non-month-end date. yfinance also carries
1,148 stock-days NSE's EQ series does not (renamed or relisted symbols such
as TMPV, ETERNAL), and no NSE day is missing from yfinance.

The twelve names below 0.98 even against the primary source: IDFC and PEL
(no yfinance data — merged), CONCOR 0.838 (two bonus events), RAYMOND
0.956 (demergers), and eight large caps at 0.971–0.979 (ICICIBANK, ETERNAL,
CASTROLIND, M&M, PAYTM, BOSCHLTD, HAVELLS, UPL) each pulled down by the
2025-03-18 row or a handful of days like it.

**So yfinance's daily close is the official NSE close, with isolated bad
rows.** The pre-registered check fails because its comparator — the intraday
cache — is neither the official close nor unadjusted, which the prereg did
not know when it chose it. That is a reason to amend the check, not to
proceed as if it had passed: **3f halts here as written.**

### 4.4 A finding outside 3f, for the live engine

The 5-minute cache the backtester reads (`backend/data/kite_history.db`)
holds dividend-adjusted history: bars fetched in bulk are scaled by every
dividend between the bar and the fetch date, while bars cached live on the
day are not. Price *levels* in the cache are therefore up to ~6% below what
traded (COALINDIA, Sep 2024) and inconsistent across fetch dates. Returns
within a fetched span are unaffected; anything using rupee levels from the
cache (₹ per-share P&L, charges as a fraction of price, an eligibility
price test) is off by the accumulated dividend yield. Not investigated
further here — offered as an issue.

## 5 — What the reviewer decides

1. **0c vendor check.** Options: (a) hold the halt — 3f ends; (b) amend the
   check to the primary source: yfinance Close vs NSE bhavcopy close, with
   split/bonus days excluded by rule, at the same 0.98/95% bar — which
   **also fails at 93.8%** unless the two merged no-data names are excluded
   as coverage cases (then 181/191 = 94.8%, still short) or the bar is set
   before the comparison is rerun; (c) replace the correlation with a
   level test — "official close matched to within 0.5% on ≥ 99% of
   stock-days" — which is what actually matters for a monthly close-to-close
   strategy and passes at 99.4%. I do not run any of these as a gate
   without a pre-registered amendment.
2. **0b coverage.** Accept the 95.17% overall pass with the first-half
   residual on record, or require the delisted names be filled from NSE's
   archive before stage 1.
3. The 2025-03-18 yfinance row: stage 1 should treat any signal-date close
   that differs from the bhavcopy by > 0.5% as missing (case §B of
   amendment 1), which needs the bhavcopy for every signal date, not just
   the 2024–25 window — a further ~190 downloads.

Nothing in stage 1 has been written. Looks spent: none. Trials spent: none.
