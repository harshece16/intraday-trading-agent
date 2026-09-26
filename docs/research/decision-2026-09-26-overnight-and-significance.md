# Owner decisions, 2026-09-26 — overnight ETF holds are in scope; the significance bar is family-level

**Recorded before any pre-registration they affect.** The owner's words:
"go ahead with overnight holds and significance bar", in reply to the two
open questions in `prediction-engine-sweep-2026-09-26.md` §5.

## 1. Overnight holds

**Decision:** Trader Sahab may hold a **Nifty index ETF overnight in
delivery (CNC)**, in **paper mode**, once a strategy doing so has passed its
pre-registered gates and its held-out confirmation.

Bounds, fixed now:
- Instrument: liquid Nifty 50 ETFs only (NIFTYBEES; SETFNIF50 as the
  replication). No single stocks overnight, no futures, no options, no
  leverage, no short positions.
- Size: never more than the capital allocated to the book; order size
  capped by the ETF's measured depth at the entry and exit times.
- Nothing changes in the live engine until a test passes. Real money
  remains a separate owner decision.

## 2. The significance bar

The owner was asked whether a new idea is judged against the project's
full trial count (119 tries, needing roughly t ≥ 4.3) or against its own
family's tries. "Go ahead with the significance bar" is read as choosing the
**family-level bar**, since the project-wide bar is the status quo. If that
reading is wrong, reverse it before trial 120 runs.

**Rule, prospective only.** It applies to hypotheses pre-registered from
2026-09-26. **It does not re-grade any past trial** — trial 119 (3h) stays
a FAIL; re-grading it after its result was seen is exactly the forking
path this rule must not open.

- **Family.** A family is one economic mechanism (for example "the Nifty
  overnight premium"), named in the pre-registration before any data is
  read.
- **N.** N_family = every pre-registered configuration in that family,
  including earlier trials of the same mechanism, plus every research look
  that tested the same mechanism against a pass rule. **Floor: N_family ≥ 2.**
  A family cannot be re-opened under a new name to reset N; the reviewer, or
  failing one the main session, rules on whether two mechanisms are the same
  family.
- **Gate.** Net-of-cost |t| above the two-sided Bonferroni bound at 5%
  across N_family (N = 2 → t ≥ 2.24; N = 3 → 2.39; N = 5 → 2.58), **and** the
  corrected Deflated Sharpe ≥ 0.95 at N_family. The project-wide Deflated
  Sharpe is still reported, for information.

**Safeguards that come with the easier bar (all mandatory):**
1. Net result positive in **both halves** of the selection sample.
2. Net result positive in the **most recent three years** of the selection
   sample. A decayed edge fails.
3. **Held-out confirmation** before any paper deployment: same sign, and
   inside a band written in the pre-registration.
4. **Forward paper run** with its own pre-registered band, switched off
   automatically on a breach.
5. A result that passes the economic gates but fails the multiple-testing
   gate **has failed**: no held-out window is spent on it and nothing goes
   to paper.

**Why this is not a loosening in disguise.** The project-wide count (119)
was dominated by intraday price-rule searches that share nothing with a new
mechanism; charging a new idea for them makes every new idea unpassable. The
cost of the easier multiple-testing bar is paid in the safeguards: the
held-out and forward confirmations become mandatory rather than optional,
and a recent-years condition catches decayed effects.

## What follows

1. Stage 0 for the overnight ETF test — facts only, no strategy returns:
   the ETF's data coverage and splits, the tradable exit window (NIFTYBEES
   is not in the 09:00–09:08 pre-open auction; the exit is the continuous
   market from 09:15), Zerodha's rules for selling an ETF bought the
   previous day, the overnight interest rate series, and forward order-book
   samples at the entry and exit times.
2. Then one pre-registration covering the family "Nifty overnight
   premium": H1 (always hold, net of costs and interest) and H2 (a nightly
   gate beats always-hold), N_family = 2.
