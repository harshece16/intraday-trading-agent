# Architectural review of the real-money pivot (2026-11-01)

Scope: the momentum book's move from paper to real money, the 13 open `[live]` gaps (#292–#304), Jev2's design, and the next 30 days. Grounded in `kite_broker.py`, `momentum_book.py`, `trading_engine.py`, `jev2_book.py`, `docs/research/live-momentum-gaps-2026-10-18.md`, the pivot brief and the paper-book state files as of 2026-10-30. A note for the owner; it changes no code.

## Verdict

The HFT framing is the wrong lens. The product is a 15-name delivery book that places about 15–30 orders in one ten-minute window a month. Its risks are exactly-once order placement, reconciliation to the broker's truth, and a human who must log in on the right day. The repo has none of the three for the momentum book, and the third is already failing in paper: **Jev and Jev2 have had 10 consecutive void sessions since 16 Oct (`no_live_prices`), the watchdog nag included.** No real-money code exists (no CNC path, no `prereg-live-momentum.md`, no `momentum_live.py`), so the 2 Nov rebalance is paper regardless. Earliest defensible real rebalance: **1 Dec**, and only after a tiny rehearsal book.

## 1. Global bottlenecks mapped to this repo

**Execution determinism.** Nanosecond latency is irrelevant here; FastAPI, Python and a Mac are three orders of magnitude faster than a monthly rebalance needs. The determinism that matters is *state* determinism, the weakest area:

- Order intent is never written before an order is sent. `_unconfirmed_orders` is in-memory; the momentum state is saved once at the end of the job. A crash or lost HTTP response between send and save makes the next run double-order (G7, G8). This is the one gap that loses real money in seconds.
- Nothing reconciles to the broker. The engine's reconcile reads Kite's *day* book only, so CNC holdings are invisible to every safety path, the kill switch included.
- The decision is computed after the session from the bhavcopy. A live book must decide before the close, with a token that dies at 06:00 and an owner who has not logged in for 10 sessions.

**Unmeasured slippage.** Paper fills at the close with 5 bp. Live cannot get the close: Kite has no retail closing-auction order, so the fill is a 15:20–15:29 market-protected order in a mid-cap, or an AMO filled at the next open. Both differ from the tested rule and the gap is unknown. Two slippage constants exist (5 bp in the book config, 3 bp in `DELIVERY_COSTS`; G11). The only honest fix is to measure with real one-share orders before the book goes in.

**Overfitting and drift.** Momentum is not an overfit signal, but the parameters were chosen inside an 11-trial family, trial 126 sits at t 2.51, the README says it would not pass at the project-wide trial count, and it lost 13% against its universe in 2025. Momentum's known failure is a crash on a sharp reversal, which the band from month 6 does nothing about. Microstructure drift that already bit the code: mandatory market protection (April 2026), T+1 settlement and same-day reuse of sale proceeds, trade-for-trade names in the universe. Treat the live phase as an execution experiment with expected return near zero after costs, not an alpha deployment.

**Policy enforcement outside the brain.** Every limit lives in the caller. `KiteExecutor.place_order` has no notional cap, no daily order cap, no product whitelist and no halt check. The cheapest, highest-value change: a guard inside the broker layer that no caller, job or model can bypass.

## 2. The go-live minefield, ranked by systemic risk

| Rank | Gap | Why |
| --- | --- | --- |
| 1 | G7 + G8 idempotency, restart | Double-order on retry compounds; everything else loses a month or some bp |
| 2 | G9 kill switch | `stop_and_flatten` iterates intraday positions; would not see a single CNC holding |
| 3 | G5 token on rebalance day | Already failing: 10 of the last 10 paper sessions void |
| 4 | G6 + G14 fills, rejections, sell authorisation | Each rejection reason needs its own branch; CDSL authorisation cannot be dry-run |
| 5 | G3 + G13 sizing, band on real NAV | At 1–2 L it is not trial 126; months 1–5 have no stop at all |
| 6 | G4, G10, G15, G1, G2 | Necessary and mechanical |
| 7 | G11, G12 | Cost truth and tax lots; blockers for filing, not for order one |

Edge cases underestimated:

- **Same-day reuse of sale proceeds.** The rebalance sells first and sizes buys as cash / vacancies, assuming all proceeds are usable at once. Zerodha releases only ~80% of same-day sale credit for new buys, the rest the next day. Buys sized on full cash get rejected for margin. Verify the exact rule with Zerodha; size buys on what is actually available.
- **A lost response after a sent order.** Only a pre-written intent plus a per-rebalance `tag` lets you find it. Kite's tag is short alphanumeric; design the format now.
- **`orders()` lists only today's orders.** Reconcile-by-tag works for a same-day restart. A crash at 15:28 followed by a restart next morning must reconcile from `holdings()` including `t1_quantity`.
- **`wait_for_fill` cancels after 5 s.** Right for intraday, wrong for a rebalance: the residual is lost, not carried. At 15:29 the exchange cancels open orders itself; the leg state machine must treat exchange cancel and own cancel the same and re-place the residual next session within the 5-session buy rule.
- **Partial fills are the normal case.** 1% market protection turns a market order into a limit; in a thin name at 15:25 a partial is likely.
- **Rejection reasons needing distinct handling:** insufficient funds, price band/circuit, trade-for-trade series, ASM/GSM stage, quantity freeze, unknown instrument after a symbol change, unauthorised sell. The last needs DDPI (Demat Debit and Pledge Instruction) signed with Zerodha: an owner step, takes days, no buy-and-cancel dry run proves it. Start this week.
- **Holdings drift without a trade.** Bonus, split, pledge, a manual sale from the Kite app. Daily reconciliation, not monthly.
- **The window is short.** Sequential sell → wait 5 s → cancel → re-read → buy with the 80% rule and residual loops can exceed nine minutes for 15 names. Fire all sells, then all buys; poll in bulk.
- **Capital.** The brief says 10 L; the pivot brief says 1–2 L. At 1–2 L three names floor to zero shares and 14–29% of the book sits in cash, so the band compares a part-cash book to a fully invested benchmark. The gaps doc's own answer is 3–4 L or 10 names. Write down which before any code. If 10 L is meant, say so in the prereg and size the hard stop accordingly: a 20% stop is 2 L of real loss.

## 3. Jev2

Right shape, quarantined. The LLM returns 14 bounded probabilities; a frozen equal-weight rule in code turns them into buy/short/skip; no size; model ID pinned and logged per decision; own thread with try/except; nothing in the module can place an order. That bypasses hallucinated execution by construction. Hidden risks:

- **Starved, not broken.** Verdict at 300 decisions or 60 sessions; nothing produced since 16 Oct. Operations, not architecture.
- **Fill convention must match what would be traded.** Paper fill is Kite LTP after up to four 90-second attempts across 25 names. Confirm in the prereg that +19.6 bp/decision is net of the 16.6 bp round trip and half a spread; if gross, it is break-even.
- **Vendor drift.** A third-party endpoint can retire or quietly change a pinned model; a headline-source change changes the state. Log a hash of the state template; refuse to decide on a model-ID mismatch.
- **If it ever passes**, its live path is the intraday MIS path and the intraday cost wall already closed. Plan no live path now. Never let any LLM output touch the momentum book.

## 4. The next 30 days, in order

1. **2–8 Nov.** Let the 2 Nov paper rebalance run; check the evening job's trades. Fix void days at the root: Kite's terms forbid automated login, so the fix is operational: one-tap login link on the phone at 09:00 with escalation, and a written rule that rebalance day is the one day a month that matters. Write `docs/research/prereg-live-momentum.md` before any code: capital or name count; order mechanics (15:20 window vs AMO at the open, and which the slippage is measured against); dead-token rule (roll to the next session, up to N, then skip the month); residual rule; band + hard −20% stop + halt file; per-fill logging of Kite's price and model price; success criterion = non-inferiority to paper.
2. **Week 2.** Broker-layer guards inside `KiteExecutor`: halt file, per-order notional cap, per-day order count, product whitelist, tag required. `MOMENTUM_LIVE` flag off by default. The ₹500 limit-buy-and-cancel dry run. Owner signs DDPI.
3. **Week 3.** Order ledger: intent written before send, order ID recorded, per-leg state machine (NEW → SENT → PARTIAL → FILLED / CANCELLED / REJECTED(reason)), residual carry, same-day reconcile by tag, next-day reconcile from holdings. Sells before buys with the proceeds rule. Stand-in Kite tests: lost response, partial at the close, insufficient funds, unauthorised sell, restart mid-rebalance.
4. **Week 4.** Daily holdings reconciliation; real NAV from holdings + margins; band and hard stop on that NAV; Slack alert on any mismatch. Then a **rehearsal book**: one real share of five liquid names through the full live path on a non-rebalance day. About ₹100 in charges, and the first real slippage, DDPI, T1 and DP-charge readings the repo has ever had.
5. **1 Dec.** First real rebalance only if the rehearsal passed and every gap above G11 is closed. Otherwise January, recorded in the ledger.

Nothing here touches the intraday engine or reopens a closed line.
