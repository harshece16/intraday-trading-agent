# Gemini research prompt: Indian intraday equity trading evidence

Copy everything below the line into Gemini (Deep Research mode works best).
Save its JSON answer as `research/findings.json` in this repo.

---

You are a quantitative research assistant. I am building a rules-based trading agent and I need **evidence I can backtest**, not general trading education. Treat every claim as a hypothesis that I will test on data, so accuracy and sourcing matter far more than coverage.

## The system you are researching for

- Market: NSE cash equities, NIFTY 100 universe. Intraday only (MIS product), long and short, all positions closed by 15:15 IST.
- Data: 5-minute and 15-minute OHLCV bars (Zerodha Kite Connect or yfinance, which is about 15 minutes delayed), daily bars, NIFTY 50, India VIX.
- Costs: Zerodha intraday equity charges plus about 0.03% slippage per side. Round-trip cost is roughly ₹35 on a ₹33,000 position.
- Current logic:
  - A scanner ranks stocks on daily trend, 10-day relative strength vs NIFTY, gap, time-of-day relative volume, VWAP, opening range, sector strength, news, and results-day risk.
  - A confluence score across trend, structure, momentum, S/R levels, candlestick patterns, volume and news decides entry timing.
  - Exits are an ATR stop (1.5× ATR) and target (3× ATR), with at most one entry per stock per day.
- Current results: net-negative over 55 days of 5-minute data. Losses are negative even before costs, so the entries have no edge yet.

## Rules for your answer

1. **Never invent statistics.** Every number must come from a source you actually found. If you find no evidence for a question, say "no evidence found". An empty answer is useful to me; a fabricated one is harmful.
2. **Prefer primary sources**, in this order: NSE/BSE publications and circulars, SEBI circulars and studies, NISM workbooks, peer-reviewed papers and SSRN/arXiv working papers, exchange-published data, then broker research. Use blogs and forums only when nothing else exists, and label them as such.
3. **Separate Indian evidence from foreign evidence.** Many famous statistics (for example Bulkowski's pattern success rates) come from US stocks on daily charts. Mark whether each result was measured on Indian data, and on what timeframe.
4. **Date-stamp everything regulatory or structural** (charges, expiry days, margin rules, algo rules). These changed often in 2024–2026. Give the effective date and the circular number.
5. **Do not use or link pirated book PDFs** (Scribd uploads, dokumen.pub, pdfcoffee and similar). Summarise books from publisher or author pages, or cite them by title and chapter.
6. Give every rule an **exact, codeable definition** using only OHLCV bars, VWAP, daily data, NIFTY, India VIX, or NSE filings. Write "trend bar: close within the top 25% of the bar's range and body ≥ 60% of range", not "a strong bar".
7. State the **failure conditions**: when the rule stops working (regime, volatility, period, liquidity).

## Questions to research

### A. NSE market structure and calendar (2026)
1. Current session timings: pre-open call auction, normal market, closing session, and how the official closing price is calculated.
2. Current weekly and monthly expiry days for NIFTY, BANKNIFTY and single-stock F&O. Are there documented intraday effects on expiry days for cash-market NIFTY 100 stocks (volatility, reversals, pinning)?
3. Price band and circuit rules for NIFTY 100 stocks in F&O vs outside F&O, including dynamic price bands. What happens to an intraday short when a stock locks at a circuit?
4. Intraday short-selling rules in the cash market: what happens if an MIS short isn't covered (auction, penalties), and any restrictions tied to the F&O ban list (MWPL above 95%).
5. The SEBI retail algorithmic trading framework as of 2026: static IP, order-per-second thresholds, algo registration or IDs, broker obligations, and what applies to one person trading their own account through the API.
6. Current intraday equity charges (STT, exchange transaction charges, SEBI fee, stamp duty, GST), with effective dates.

### B. Intraday return patterns measured on Indian equities
7. Volume and volatility profile across the NSE session (U-shape or not), and whether the first 15 or 30 minutes predict the rest of the day.
8. Opening range breakout studies on NSE stocks or NIFTY: range length, filters, reported win rate, average return, costs included or not.
9. Gap behaviour: how often gaps of various sizes fill on the same day for NIFTY 100 stocks, split by gap direction and by NIFTY's direction.
10. VWAP: evidence of mean reversion toward VWAP vs momentum away from it on NSE intraday data.
11. Intraday momentum vs reversal: does the first-half-hour return predict the last-half-hour return in Indian markets? Is there time-series momentum for single stocks within the day?
12. Does GIFT Nifty (formerly SGX Nifty), the US session or Asian markets predict NIFTY's open or first hour?
13. Do FII/DII flow data, India VIX level or VIX change help predict intraday direction or volatility?
14. Day-of-week, pre-holiday, month-end, budget-day and RBI-policy-day effects on Indian stocks, with recent evidence (after 2018).

### C. Candlestick, chart pattern and price-action reliability
15. Studies measuring candlestick pattern profitability on Indian stocks (any timeframe). Give the patterns tested, sample size, period, holding period and results, including negative results.
16. Evidence on classical chart patterns (double bottom, head and shoulders, flags, triangles) on Indian data. Where only US evidence exists, say so and give Bulkowski's definitions and reported failure rates as foreign evidence.
17. Failed or "busted" breakouts: any measured evidence that fading failed breakouts is profitable, on any market, preferably intraday. Give a codeable definition of a failed breakout.
18. Al Brooks price-action concepts turned into codeable rules: trend bar, always-in direction, two-legged pullback, micro channel, climax and trading-range detection. Cite whether anyone has backtested them.
19. Which of these reliably add value **after costs** at 5-minute and 15-minute horizons on liquid large caps, and which only work gross of costs?

### D. News, filings and events in India
20. How fast NSE stock prices react to results, order-win filings, rating changes, block and bulk deals, and promoter pledge disclosures (minutes, hours, days). Can a trader using 15-minute-delayed data still capture any of it?
21. Is there post-announcement drift in Indian stocks after earnings surprises or large order wins (intraday and next-day)?
22. Behaviour on results day: volatility, gap and reversal statistics for NIFTY 100 stocks.

### E. Risk, exits and position sizing
23. Evidence on stop and target placement for intraday trades: ATR-multiple stops vs structure-based stops vs time exits, preferably on Indian or other liquid equity data.
24. Realistic expectancy (in R-multiples) and win rates reported for professional intraday strategies, and what SEBI's studies say about retail intraday and F&O trader outcomes (include the figures and study dates).
25. Whether volatility-scaled sizing, a daily loss limit, or reducing size after losses improves risk-adjusted results, with evidence.

### F. Statistical arbitrage and machine learning on Indian equities
26. Published cointegration or pairs-trading studies on NSE stocks (for example within banking or IT). Report half-life, profitability after costs, and whether intraday execution in the cash market is practical vs using futures.
27. Machine learning studies predicting intraday or next-day direction for Indian stocks: the features used, the validation method (was there look-ahead or leakage?), reported accuracy, and whether results survived costs. Flag studies that used random K-fold cross-validation on time series.
28. Practical use of meta-labeling, triple-barrier labeling, purged cross-validation and the deflated Sharpe ratio (López de Prado) on small datasets like mine (a few months to a few years of 5-minute bars for 100 stocks). What minimum sample sizes are recommended?

## Output format

Answer in two parts.

**Part 1: a short summary (at most 400 words).** The 5 findings most likely to improve a net-negative intraday NIFTY 100 strategy, plus the 5 popular ideas the evidence says to avoid.

**Part 2: one JSON code block** holding an array of findings with exactly this shape. Use `null` where something is unknown.

```json
[
  {
    "id": "B8-orb-15min",
    "question": "B8",
    "category": "session_timing | intraday_pattern | candlestick | chart_pattern | price_action | news_event | risk_exit | sizing | regulation | costs | stat_arb | machine_learning",
    "claim": "One-sentence plain-English finding.",
    "india_specific": true,
    "timeframe": "5m | 15m | 1h | daily | n/a",
    "side": "long | short | both | n/a",
    "rule": {
      "definition": "Exact codeable definition using OHLCV, VWAP, daily bars, NIFTY, India VIX or filings.",
      "parameters": {"range_minutes": {"value": 15, "tested_range": [5, 30]}},
      "entry": "When to enter, or null",
      "exit": "Stop, target or time exit, or null",
      "filters": ["Conditions under which it applies"]
    },
    "evidence": [
      {
        "title": "Source title",
        "url": "https://…",
        "source_type": "regulator | exchange | peer_reviewed | working_paper | book | broker_research | blog | forum",
        "published": "YYYY-MM",
        "market": "NSE | BSE | US | global | other",
        "sample_period": "YYYY-MM to YYYY-MM",
        "sample_size": "e.g. 12,400 trades or 80 stocks",
        "reported_results": "Exact numbers as reported, including whether costs were deducted",
        "quote": "One short quote under 25 words supporting the claim"
      }
    ],
    "confidence": "high | medium | low",
    "confidence_reason": "Why, e.g. single blog, small sample, US-only, pre-2015 data",
    "effective_date": "For rules, charges and regulation: YYYY-MM-DD, else null",
    "how_to_test": "Exact backtest: universe, period, entry/exit, baseline to compare against, costs, and the metric that would confirm or reject it",
    "failure_conditions": "When it stops working",
    "conflicts_with": ["ids of findings that disagree"]
  }
]
```

Aim for 40–80 findings. Quality beats quantity: 30 well-sourced findings are better than 100 weak ones. Include negative findings (for example "pattern X shows no edge on NSE after costs") with the same structure, and set the claim accordingly.
