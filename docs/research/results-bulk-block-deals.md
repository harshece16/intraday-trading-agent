# Results — bulk and block deal disclosures at the next open (research look L50): VOID at stage 0

**2026-09-30. VOID: too few events to test. Independent review: APPROVED** (see §Review). Pre-registered in `prereg-bulk-block-deals.md` (commit `66c1ed3`, before any code); harness `backend/research/deals_l50.py` (`7e8beb2`); stage 0 record `data/l50_stage0.json` and event list `data/l50_events.csv` (`6d3971d`). Stage 0 ran once, 20:19–20:22 IST, under `nice`, outside the engine's hours. **No price was read**: stage 0's only query on the candle table selects symbol and bar time. No return was computed. The 2026 window was not read. Trials remain 202.

## Stage 0

| Step | Result |
| --- | --- |
| 1. Source | 32 month files (16 months × bulk, block), every one HTTP 200 on the first attempt: **24,176 bulk rows, 2,287 block rows**, deal dates 2024-09-19 to 2025-12-22. Six fixed-seed dates (seed 123) re-queried one day at a time: **12 of 12 identical** to the month files. Rows per day range 4 to 187 (bulk), no sign of a cap. |
| 2. Boundaries | No deal outside 2024-09-19..2025-12-22; last bar loaded 2025-12-23. |
| 3. Symbols | NSE's `symbolchange.csv` applied (ZOMATO → ETERNAL and the like). **277 NIFTY 100 stock-days** on members on the entry session. Lost because the member is not in the Kite cache: bulk 8 (INDUSINDBK 6, SWIGGY 1, BAJAJHFL 1), block 13. Calendar: every one of the 310 regular sessions to 2025-12-22 has bulk rows; the only in-sample deal dates the cache lacks as regular sessions are the two Muhurat sessions (2024-11-01, 2025-10-21). NSE's `symbolchange.csv` includes renames that took effect in 2026; a rename is applied only when effective after the deal date, and the only 2026 rename any NIFTY 100 event used is **LTIM → LTM, on one block stock-day** (2025-07-14), which does not touch the bulk count. |
| 4. Classes | **BULK_BUY 2, BULK_SELL 19, MIXED 5**; BLOCK 251 (2 with buy ≠ sell). Under the information thresholds: 22 directional at 0, 20 at 1/2. |
| 5. Bars | BULK_ALL has **21 directional NIFTY 100 bulk events in the Kite cache** (26 counting members the cache lacks; at most 34 on any side rule), at each of 15, 30 and 60 minutes (20 sessions; 2 in the first half, 19 in the second). BULK_SELL 19, BULK_BUY 2. |
| 6. Void rule | **Every cell is under 60. The family is empty, so L50 is VOID**, as §7 and §8 fix. |
| 7. Adjustment | One Kite fetch run (2026-09-20); no fetch-run boundary between any deal and its entry session. |

## What the events are

**17 of the 21 directional events are strategic stake sales by large holders**: Pastel and Indian Continent Investment selling Bharti Airtel (five), BAT's Tobacco Manufacturers selling ITC, Antfin selling Zomato, Rakesh Gangwal's family trust selling IndiGo (two), SMBC and Oppenheimer selling Kotak Mahindra Bank, the Hamied family selling Cipla, the Bajaj holding companies selling Bajaj Finserv, TotalEnergies selling Adani Green, Invesco selling Lodha, Envestcom selling Adani Energy Solutions, Suneetha Reddy selling Apollo Hospitals. **The other four are BNP Paribas Financial Markets**: both BUY events (Eternal) and the MAXHEALTH and ENRIN SELLs. The five MIXED are Wipro's inter-promoter transfers (three) and Reliance's Siddhant Commercials selling Asian Paints to SBI and ICICI Prudential mutual funds (two): the file names both sides, and the 2:1 rule rightly gives them no direction.

Of the 8 bulk stock-days lost to the cache, 5 are directional under the 2:1 rule (INDUSINDBK 3, SWIGGY 1, BAJAJHFL 1), so the directional count is 26 with them. Counting every MIXED and every lost stock-day as directional, the bulk count is at most 34 (21 + 5 MIXED + 8 lost), far below 60. The result does not depend on the side rule or on the cache gap.

## Reading it

- **In the NIFTY 100 a bulk deal is rare**: 0.5% of a large company's equity in one day is a strategic transaction. Over the 15.1 months of deal dates (2024-09-19 to 2025-12-22): **all NIFTY 100 bulk stock-days, cache-missing members included, 34, about 2.3 a month; directional ones 26, about 1.7 a month** (21, about 1.4 a month, on the members the cache holds). The literature's thousands of bulk-deal events come from small and mid caps, where the project's five-minute bars and liquidity do not reach.
- **Block deals are frequent (251 stock-days) but have no side** in NSE's file, which lists both counterparties. Testing them would need a new, separately pre-registered side rule; §4 considered the premium or discount against a reference price and set it aside, because the file does not say which block window a trade used.
- **What this look cannot say**: whether a stake sale moves the next morning. With 19 SELL events in 15 months, no answer at the project's bar is possible on this cache.

## What would make it testable (not proposed here)

A longer five-minute history of every point-in-time member: at about 1.7 directional events a month, 60 events need roughly **35 months** of NIFTY 100 bars (60 / 1.72 = 34.9), against the 15 months the cache holds before the held-out window (43 months at the in-cache rate of 1.39). That would be a new look with its own pre-registration, and it would still face the literature's expectation that the move happens before the disclosure.

## Review

**APPROVED, 2026-09-30.** The independent reviewer found the void correct and rebuilt all 277 NIFTY 100 events from the raw files independently, with zero differences. Its notes are addressed:

- **N1–N4**: the symbol-change line (§Stage 0, step 3), the event counts with and without the members the cache lacks (step 5), the corrected rates and months needed (§Reading it, §What would make it testable), and the 17-of-21 count (§What the events are).
- **N5**: `deals_l50.canon()` followed each later rename in a chain from the deal date; it now checks each later rename against the previous rename's effective date, so a rename made by an earlier holder of the new symbol is not followed (test `test_a_chain_step_ignores_a_rename_by_an_earlier_holder_of_the_new_symbol`). Stage 0's committed outputs are unchanged: recomputed offline from the cached raw files (no network, bar times only), the event list is byte-identical to `data/l50_events.csv` and the boundaries, symbols, classes, bars, family and sessions sections equal `data/l50_stage0.json`; no row of either file maps differently under the old and new rule.
- **N6**: this results note was committed before the review. Harmless: the void ends the look, and nothing in it depended on the review.

Research look **L50**, VOID at stage 0. No trial. Held-out untouched.
