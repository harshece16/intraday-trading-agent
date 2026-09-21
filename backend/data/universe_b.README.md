# Universe B — NSE F&O-eligible minus NIFTY 100

**Retrieved:** 2026-09-21
**Source:** https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv
(the official NSE F&O market-lots file; the `archives.` host 301-redirects to
`nsearchives.`)

**Construction:** the "Derivatives on Individual Securities" block of that
file (210 symbols), minus the 100 NIFTY 100 names in
`nifty100.csv`, leaving **113**.

**Why F&O-eligible:** liquid, shortable intraday, and stock futures exist —
which matters for any later cost model. Reviewer Entry 6 §B.

## Caveats, recorded at creation

- **This is TODAY'S membership applied to history**, exactly as with the
  NIFTY 100. Names that were F&O-eligible earlier and were dropped are
  absent.
- **Survivorship distortion is likely LARGER here than in the NIFTY 100**,
  because mid-caps enter and leave F&O eligibility more often and the ones
  that leave usually do so after falling.
- **Costs differ.** Entry 6 §D fixes double the configured slippage per leg
  for any universe B figure expressed in money or R, unless a measured figure
  from this project's own fills exists. It does not.
- **Not in the live path.** Entry 6 §F: universe B is not added to the
  running engine's watchlist or scanner.
