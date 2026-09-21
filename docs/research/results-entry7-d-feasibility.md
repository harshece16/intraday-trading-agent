# Entry 7 §D — feasibility facts: the index-level split, and the cost sheet

**Directed by:** reviewer Entry 7 §D.1 and §D.2. **Measurements only, no
trials.** Trial count stays at **34**. Research look **L29**.
**Run:** 2026-09-21. Selection dates only.

---

## Verdict: the intraday drag is real. The overnight gain is 40% survivorship.

> **§D.1 was designed to find out how much of 3c's split survives without
> survivorship bias. The answer splits cleanly in two:**
>
> | | Universe A (today's members) | **NIFTY 100 index (point-in-time)** | Inflation |
> | --- | --- | --- | --- |
> | Overnight | +16.78 bp | **+12.01 bp** | **+40%** |
> | Intraday | −6.94 bp | **−6.42 bp** | **+8%** |
> | Total/day | +9.84 bp | **+5.59 bp** | **+76%** |
>
> **The intraday drag is essentially untouched by survivorship — it is a real
> property of the market. The overnight gain, which carries all of the
> return, is inflated by 40%.**

That is exactly the asymmetry one should expect: survivorship bias flatters
long-run *returns*, and the overnight leg is where all the return lives. The
intraday leg is a *drag*, and a drag is not flattered by dropping the losers.

**Consequence: 3c's finding that matters to an intraday agent survives the
check. The finding I was careful not to propose is the one that was partly an
artefact.**

---

## §D.1 — index-level overnight vs intraday (L29)

Index series are point-in-time by construction: they already contain their
own constituent changes, so no survivorship correction is needed.

| Series | Sessions | Span | Overnight | Intraday | Total/day |
| --- | --- | --- | --- | --- | --- |
| **NIFTY 100** (`^CNX100`) | 4,941 | 2005-12 → 2025-12 | **+12.01 bp** (t = +12.20) | **−6.42 bp** (t = −4.02) | +5.59 bp |
| **NIFTY 50** (`^NSEI`) | 4,487 | 2007-09 → 2026-01 | **+9.77 bp** (t = +11.45) | **−4.97 bp** (t = −2.81) | +4.79 bp |
| **NIFTY BANK** (`^NSEBANK`) | 4,502 | 2007-09 → 2026-01 | +10.44 bp (t = +7.92) | −4.15 bp (t = −1.87) | +6.30 bp |

**On every series the whole daily return, and more, is earned overnight** —
166% to 215% of it, because the intraday component is negative. Holding an
Indian equity index from open to close has lost money on average for two
decades.

**The intraday drag is significant on the two broad indices** (t = −2.81 and
−4.02) and **not quite** on BANKNIFTY (t = −1.87), which is stated rather
than rounded up.

### Year by year — and the effect is decaying

| Split holds (overnight > 0 **and** intraday < 0) | |
| --- | --- |
| NIFTY 100 | **16 of 20 years** |
| NIFTY 50 | **13 of 19 years** |
| NIFTY BANK | **11 of 19 years** |

**It is not a constant of nature.** And the recent years are the weakest:

| Year | NIFTY 50 | NIFTY 100 | NIFTY BANK |
| --- | --- | --- | --- |
| 2020 | +18.44 / −10.81 | +18.27 / −10.74 | +20.46 / −17.64 |
| 2021 | +18.66 / −9.46 | +19.89 / −10.37 | +15.48 / −9.35 |
| 2022 | +3.15 / −0.83 | +5.75 / −3.68 | +1.93 / **+6.75** ✗ |
| 2023 | +12.78 / −5.14 | +13.62 / −5.97 | +12.88 / −7.79 |
| 2024 | +9.74 / −5.91 | +13.19 / −8.19 | +5.51 / −2.78 |
| **2025** | **+3.64 / +0.68** ✗ | **+5.24 / −1.41** | **+1.35 / +5.36** ✗ |

**2025 is the weakest year in the series on all three indices**, and the
split fails outright on two of them. Whatever the mechanism is, it is
weaker now than over the sample that measured it.

---

## §D.2 — the cost sheet

### Verified this session

**Lot sizes** — official NSE F&O market-lots file,
`https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv`, retrieved
**2026-09-21**. **Prices** — yfinance last close, same date.

| Instrument | Lot | Last close | **Contract notional** |
| --- | --- | --- | --- |
| NIFTY | 65 | 23,366.75 | **₹15,18,839** |
| BANKNIFTY | 30 | 56,372.15 | **₹16,91,164** |
| SBIN | 750 | 991.80 | ₹7,43,850 |
| RELIANCE | 500 | 1,234.20 | ₹6,17,100 |
| TATASTEEL | 2,750 | 184.63 | ₹5,07,733 |
| HDFCBANK | 650 | 734.30 | ₹4,77,295 |
| ITC | 1,725 | 266.05 | ₹4,58,936 |
| **INFY** (smallest here) | 400 | 1,035.60 | **₹4,14,240** |

### Cash costs, from the project's own model (`costs.py`)

Round trip, both legs, including the modelled slippage.

| Notional | **Intraday (MIS)** | **Delivery (CNC, held overnight)** |
| --- | --- | --- |
| ₹5,000 | **16.60 bp** | **60.08 bp** |
| ₹33,000 | **16.60 bp** | **33.05 bp** |
| ₹1,00,000 | 14.24 bp | 29.81 bp |
| ₹3,00,000 | 11.09 bp | 28.75 bp |

**Delivery costs roughly double intraday**, and at ₹5,000 it is nearly four
times. The ₹20 flat brokerage plus the ₹15.93 depository charge per sell
dominate small positions — which is why the intraday column is flat at
16.60 bp until ₹33,000 (the ₹20 cap binds) and the delivery column falls
steeply with size.

### The comparison that settles the overnight question

**To harvest the overnight leg you must buy near the close and sell at the
open — a delivery round trip, every day.**

| | |
| --- | --- |
| Index overnight return, survivorship-free | **+12.01 bp/day** |
| Delivery round trip at ₹33,000 | **33.05 bp** |
| **Ratio** | **0.36× — it does not pay** |
| At ₹5,000 | 12.01 vs 60.08 = **0.20×** |
| At ₹3,00,000 | 12.01 vs 28.75 = **0.42×** |

**The only way to avoid the daily round trip is to hold continuously — which
means eating the −6.42 bp intraday too, netting +5.59 bp/day. That is not a
strategy; that is being long the index.**

> **The overnight effect is real, survivorship-corrected, and costs three
> times what it yields to capture. It is not a lead.**

### Not verified — stated rather than estimated

Entry 7 §D.2 says to say so rather than estimate silently. **I did not verify
these and have not guessed them:**

- **Futures brokerage, STT, exchange and SEBI charges, stamp duty and GST.**
  The project has no futures cost model, and I did not confirm current rates
  against a published broker tariff in this session. **Any futures cost
  figure would have been invented.**
- **SPAN + exposure margin per lot.** Not fetched. NSE publishes SPAN files
  and brokers publish margin calculators; neither was consulted.
- **The cash rates in `costs.py` themselves** were not re-verified against
  `zerodha.com/charges` today. The code already carries that caveat, and it
  still stands.

**This does not affect the capital answer below**, because that turns on
contract notional, which is verified.

---

## Which instruments are reachable

| Capital | Cash intraday | Cash delivery | Index futures | Stock futures |
| --- | --- | --- | --- | --- |
| **₹5,500** | Yes, but **16.60 bp** cost and ~₹5k positions | Yes, at **60.08 bp** — punitive | **No** | **No** |
| **₹1,00,000** | Yes, 14.24 bp | Yes, 29.81 bp | **No** | **No** |
| **₹3,00,000** | Yes, 11.09 bp | Yes, 28.75 bp | **Marginal at best** | **Marginal at best** |

**Futures are out of reach at all three levels**, and this follows from the
verified notional alone, without needing the margin figures:

- The **smallest** stock future in the liquid set is **INFY at ₹4.14 lakh**
  notional; NIFTY is **₹15.19 lakh**.
- Even at a permissive 15–20% margin, one NIFTY lot needs roughly **₹2.3–3.0
  lakh** — the entire ₹3,00,000 account on a single position, with no room
  for a second and a margin call on a small adverse move. That range is an
  **illustrative bracket, not a verified figure.**
- At ₹5,500 and ₹1,00,000 the question does not arise.

**So the instrument set actually available is cash intraday and cash
delivery.** Intraday costs 16.60 bp and faces a −6.42 bp drift; delivery
costs 33.05 bp and the effect it would harvest is 12.01 bp.

---

## What this means for the next design

1. **The intraday drag is real and survivorship-free.** Any long-biased
   intraday design starts behind by roughly 5–6 bp per day, on top of
   16.60 bp of cost. Entry 7 §A's requirement that 3a/3b be
   direction-symmetric or explicitly short-capable is well founded.
2. **The overnight route is closed at this capital.** Not because the effect
   is fake — it survives the survivorship check — but because harvesting it
   costs 0.36× what it returns, and the alternative to harvesting is buy-and-hold.
3. **Futures are closed at this capital**, on verified notional alone.
4. **The effect is decaying.** 2025 is the weakest year on all three indices
   and the split fails outright on two. Any design motivated by this should
   be judged on recent data, not on a twenty-year average dominated by
   2017–2021.

---

## Caveats

- **Index series are survivorship-free but not cost-free**: they are not
  investable without a tracking product, and the bp figures above are
  index-level, not the return of any tradable instrument.
- **yfinance index data** is the source for §D.1; it was not cross-checked
  against NSE's own published index history.
- **The 2026 sessions are excluded** — selection dates only, so the held-out
  window is untouched.
- **`^CNX100` spans 2005–2025 and `^NSEI` 2007–2026.** The two are not over
  identical windows, so the small differences between them are partly period,
  not construction.
