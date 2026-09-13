# Gemini follow-up prompt

Send this in the same Gemini conversation. Paste back each section's answer
separately. Answers are checked against `research/findings_verified.json`.

---

Thank you. I checked your four findings against the primary sources, and I need a stricter second pass:

- **Wrong source.** The "28% of net losses went to transaction costs" figure is not in SEBI PR 22/2024, which you cited.
- **Wrong date.** The algo framework was not effective on 2025-04-01. It came from SEBI's circular of 4 Feb 2025, rolled out through NSE circulars in May, July and September 2025.
- **Unverifiable source.** The ORB finding cites a Scribd upload with no readable content, no dataset and no sample period.
- **Invented quote.** The F&O machine learning finding names the wrong book, and its "quote" comes from text I wrote, not from the source.
- **Unsourced claims.** "Averaging down drives the 93% loss rate" and "genuine strategies cluster at 40–60% win rates" had no sources.
- **Missed study.** You missed SEBI's July 2024 study of intraday cash traders (71% lost money in FY23), which is the most relevant one for my system.

Please redo the research **one section at a time**, starting with Section B, then C, D, E, F and A. For each section, return 10–15 findings in the same JSON format as before, with these extra rules:

1. **Every finding must include at least one URL and an exact quote under 25 words that appears on that page.** If you cannot quote the page, drop the finding or set `"confidence": "low"` and say why.
2. **Do not use Scribd, dokumen.pub, pdfcoffee, Telegram, YouTube or forum posts as the only source.** Broker blogs are allowed only if they describe their own backtest with a sample period and sample size; otherwise mark the finding `low`.
3. **Negative results count.** If the best available evidence says an idea doesn't work after costs on Indian stocks, report that as a finding.
4. For every number, state whether it is **before or after costs**, and which **market, timeframe and period** it was measured on.
5. If you find nothing for a question, return a finding with `"claim": "No evidence found"` and list the searches you tried.
6. Add a field `"verification_status": "quoted_from_source" | "paraphrased" | "not_verified"`.

Start with **Section B (intraday return patterns on Indian equities)**. I especially need:
- opening range breakout studies on NSE with sample sizes
- how often NIFTY 100 gaps fill on the same day
- VWAP reversion vs momentum
- whether the first half hour predicts the last half hour in Indian markets
- whether GIFT Nifty predicts the open
