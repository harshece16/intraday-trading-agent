# Pre-registration — results direction from the filed numbers (research look L36, no trial)

**Written and committed before the script runs.** L35 found results days move NIFTY 100 stocks about 3× normal (121 bp in 30 minutes) but could not align direction: the filing text carries no numbers. This measures whether the **filed numbers themselves** give a direction that predicts the tradable move. Runs at the user's direction without external reviewer review.

## Data
- **Results index:** NSE `/api/corporates-financial-results?index=equities&symbol=S&period=Quarterly`, per NIFTY 100 symbol. Event time = `broadCastDate` (IST, to the second). **Consolidated** filing preferred; standalone only if no consolidated filing exists for that quarter.
- **Numbers:** each filing's `xbrl` file; `ProfitLossForPeriod` with context `OneD` (the quarter). The comparison quarter is the same company's filing whose quarter ends one year earlier.
- **Prices:** Kite 5m cache, **selection sample only** (events broadcast between 2024-09-25 and 2026-01-01). Held-out not loaded.

## Direction, fixed now
`dir = sign(PAT_q − PAT_{q−4})`, year on year. An event with no prior-year filing, or a zero change, is dropped. **No consensus estimates are used; this is growth, not surprise.** That is a known weakness and is stated up front.

## Windows (as L35)
After-hours broadcast (the usual case): next session's 09:20 bar open; +30 min, +60 min, to the 15:08 close. In-hours (09:15 ≤ t < 14:30): first 5m bar after the broadcast; same windows. **The overnight gap is reported for information** (it says whether the direction is right at all) and is **not tradable**.

## Gate for a step-2 rule, fixed now
> Direction-aligned mean return **> 16.63 bp with t > 2 on ≥ 50 events** in at least one of the three windows, after Benjamini–Hochberg across the 3 windows. Otherwise: **"the filed numbers' direction does not predict a tradable results-day move"**, and no rule is written.

Research look **L36**. No trial. One run; a fetch failure is recorded as missing, not retried for a better sample.
