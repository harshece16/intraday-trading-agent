# Pivot brief, 2026-10-18: what the trades say, and the prompt for the next phase

Read-only review of the journal, the three paper books and the research ledger. No trial or look spent.

## 1. What has actually traded

| Book | Record | Verdict so far |
| --- | --- | --- |
| Intraday engine (paper, candlestick + Varsity checklist) | 48 closed legs since Sept; net −₹1,731 (gross −₹1,211); 3 winners of 48; mean −1.29R; 19 stop-outs cost −₹2,001, 4 targets made +₹327; longs −₹1,400, shorts −₹332 | Dead. Matches the 495-session backtest (−0.356R/trade, entries = random). Friction 16.6 bp a round trip is the whole loss. |
| Momentum book (paper, ₹10 L, trial 126 rule, monthly) | Live since 2026-10-01; NAV ₹10,09,460 vs benchmark ₹10,09,306 on 10-16 (+1.5 bp excess in 11 sessions) | Only passing strategy (+0.71%/mo, t 2.51, 2010–25; held-out 2026 +1.28%/mo). Family N = 11; next trial needs t ≥ 2.865. Needs 6 months before the band says anything. |
| Jev book (LLM shown the scanner's side) | 8 scored days, 120 decisions, agreed with the scanner 101/120, skipped 6; +10.6 bp/decision, t 1.18 | Indistinguishable from the scanner. 6 of 14 days lost to "no live prices" (Kite not logged in by 09:45). |
| Jev2 book (blind, decomposed) | 4 scored days, 100 decisions, 58 skips; +19.6 bp/decision, t 2.78 | Too early (verdict rule: 300 trades / 60 sessions) and within-day correlated. The only intraday line still alive. 5 of 10 days lost to no Kite login. |
| Rule lab (L54/L55) | 104,655 rule combinations, 53,210 lab trades | 0 survivors; test was vacuous (Romano–Wolf bar 7e7). Forward screen 40 sessions away. |
| F&O | 0 trades | Never used. |

Count of record: 204 trials. Lines closed and not to be reopened: intraday entries (76-config sweep, confluence, universe width), overnight ETF, PEAD, Sahab Ranker, Kronos/TSFM family, frog-in-the-pan.

## 2. The honest read

1. The intraday product is finished as a money-maker. Every entry family sits at pre-friction R ≈ 0; the loss is the 16.6 bp round trip. No entry research can fix a cost problem.
2. The one edge found is slow momentum in delivery. It is worth ~+0.7%/mo over the index, which is ~₹7,000/month on ₹10 L. That is real but small, and 2025 was −13%.
3. Operational leakage is now the biggest measured loss: 11 of 24 Jev/Jev2 days were void because nobody logged into Kite by 09:45. A strategy that does not run is the worst strategy.
4. No real-money order has ever been placed. All must-fix-before-live bugs (#155, #156) are closed; #66 (per-symbol slippage) is open but only matters intraday.

## 3. Three ways to pivot (pick one)

| Pivot | What it is | Cost / time | Why it might work |
| --- | --- | --- | --- |
| A. Go live, small, on the momentum book | ₹1–2 L real money on the trial-126 rule (or its ETF form, NIFTY200 Momentum 30 fund, if DP charges eat the stock version). Monthly rebalance, delivery, no leverage. | 1–2 weeks of engineering; zero new research | It is the only pre-registered pass; delivery costs are ~1/4 of intraday; live fills are the data the project lacks (slippage, DP, tax). |
| B. New strategy families, delivery horizon only | Pre-registered search over families not yet tried: cross-sectional low-vol/quality overlays on the momentum book, turn-of-month, buyback/promoter-buy events, sector rotation, gold/debt dual momentum. | 1 trial each; momentum-family bar now t ≥ 2.865 | Literature says net-positive evidence exists only at ≥ 1-month horizons; these are the untested ones. Expected hit rate: low. |
| C. Keep Jev2 as the only intraday line, fix uptime first | Automate the Kite login/alert so 0 days are void; run Jev2 to its 300-trade verdict (~3 months). Build nothing else intraday. | Mostly ops | t 2.78 at n = 100 is the strongest intraday number ever seen here, but 4 days is not evidence. Cheap to let it finish. |

Owner decision 2026-10-18: **do all three.** Order: C (uptime, days) → A (live momentum, weeks) → B (one pre-registered trial at a time, ongoing). B has consumed 200 trials for one pass; expect that rate to continue.

## 4. Reframed prompt (paste this into a new session)

> You are continuing Trader Sahab (`~/Projects/webapp`, read CLAUDE.md, then `docs/research/pivot-brief-2026-10-18.md`, then the newest `reviewer-inbox.md` entry). The intraday search is closed: 204 trials, one pass (trial 126, monthly momentum in delivery, +0.71%/mo, t 2.51). Do not re-run any closed line or spend the 2026 held-out window.
>
> Goal for this phase, all three in this order: **(C) zero void paper-book days, (A) the momentum book from paper to real money at ₹[1–2] L, (B) a steady pipeline of pre-registered delivery-horizon trials, one at a time.**
>
> Deliver, in order:
> 1. **Go-live gap list.** Read `momentum_book.py`, `kite_broker.py`, `trading_engine.py` and BUG_LOG.md. List every gap between the paper book and a real delivery order on Kite: order type (CNC), lot-aware sizing, partial fills, the 06:00 token expiry versus a 15:20 rebalance window, failed-order retry, restart safety, kill switch, tax lots (STCG/LTCG) in the journal, and the self switch-off band enforced on real NAV. File each as a GitHub issue (label `live`).
> 2. **Live-mode design, pre-registered.** One doc, `docs/research/prereg-live-momentum.md`: capital, first rebalance date, the exact rule (trial 126 unchanged), the stop-the-book rule (band from month 6, plus a hard −20% drawdown stop), what is logged per fill (Kite executed price, not the model price), and the success criterion at 6 and 12 months (non-inferiority to paper within slippage, not a new alpha claim). Commit it before any live code.
> 3. **Implement** behind a `MOMENTUM_LIVE=1` flag that is off by default, with a dry-run that places and cancels one ₹500 order outside a rebalance to prove the broker path. Tests for sizing, fills, restart and the band. Nothing touches the intraday engine.
> 4. **Uptime fix for Jev/Jev2:** 11 of 24 days were void because Kite was not logged in by 09:45. Add a 09:00 IST alert (Chotu/Slack/notification) and a page banner; record every void day as a bug-log row. Target 0 void days in the next 20 sessions.
> 5. **Research pipeline (one pre-registered trial at a time, each only after the previous one's results file is committed; start after 1–4 are merged):** pick from the untested delivery families (low-vol/quality overlay as a non-inferiority rule, turn-of-month, promoter open-market buys, dual momentum with gold). Family-level bar, both halves, forward band, no held-out read.
>
> Rules: pre-registration before code, one run per hypothesis, bp against round-trip cost, file every bug, no Claude attribution in commits, never print tokens. Report plainly; if a step blocks on the owner (money transfer, Kite login, capital), finish every other step first and list the exact `! <cmd>` or click needed.

## 5. Local models (Hermes agent, Qwen on sahab-pc), asked 2026-10-18

Not for prediction. The project's own evidence (profitability sweep §1, Sahab Ranker, Kronos/TSFM family, Jev book = scanner) and the outside tests all say an LLM or foundation model adds no net return. A bigger or local model does not change that.

Where a local model on the PC could pay for itself:
- **Replace the paid Jev judge in Jev2 with a local Qwen** as a *new, pre-registered arm* (same prompts, same blind decomposition). Saves API spend, gives a second judge to compare, raises N_family by one. Only worth doing if Jev2 is still alive at its 300-trade read.
- **Ops agent (Hermes-style)**: the 09:00 Kite-login nag, watchdog triage, bug-log drafting, Chaywanaprash self-review at zero marginal cost. Gains are convenience, not P&L.
- **News/filing classification** for the research pipeline (B), locally, so a trial over thousands of filings costs nothing per call.

Blockers before any of it: the PC is mid Ubuntu→WSL migration (owner steps open) and is gaming-blocked for background jobs; Python 3.9 in the backend; nothing local may touch the engine's decision path without a prereg, a trial and the family bar. Decision: **no new engine, no model in the live path.** Add a local Qwen judge as a Jev2 arm only if Jev2 survives its first interim read.
