# Results — 3h, market breadth and intermarket moves as new information (L35)

**2026-09-25. NO PASS: 0 of 8 predictors survive Benjamini-Hochberg at 5%, and
none has an extreme tercile that could pay the 16.63 bp round trip.**
Pre-registered in `prereg-3h-breadth-intermarket.md` (commit `db82c9a`); code
and tests in `1ea0ab5`, both before the run. One run. **Research look L35, not a
trial.** The held-out window was not loaded. It ran at the owner's direction
without external reviewer review.

Selection sample: 316 sessions, 2024-09-25 → 2026-01-01. **313** had a usable
target (at least 50 NIFTY 100 stocks with both the 09:15 and 15:05 bars).

## Data gate: PASS

| | |
| --- | --- |
| Bhavcopies fetched | 414 weekdays from 2024-06-01, 403 files and 11 holidays |
| Selection sessions with a bhavcopy of ≥ 1,500 EQ rows | **99.7%** (gate ≥ 95%) |
| yfinance coverage, P4–P8 | every predictor ≥ 90%; none dropped |

## The target

The equal-weighted NIFTY 100 return from 09:20 to 15:10 averaged **−2.65 bp**,
with a session-to-session spread of **73.1 bp**. That is the familiar negative
intraday drift, and a noisy one.

## All 8 predictors

Tercile means are the target in bp. "Tradable" is pre-registered rule 2: the
tercile the spread points to must reach 16.63 bp with the right sign.

| Predictor | Bottom | Middle | Top | **Spread** | t | p | BH 5% | Tradable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 breadth ratio, D−1 | −2.73 | −12.94 | +7.83 | +10.56 | +0.98 | 0.33 | no | no |
| P2 McClellan Oscillator, D−1 | −1.12 | −10.25 | +3.50 | +4.62 | +0.44 | 0.66 | no | no |
| P3 TRIN, D−1 | −0.38 | −4.76 | −2.78 | −2.40 | −0.24 | 0.81 | no | no |
| P4 India VIX change | −0.15 | −3.90 | −3.88 | −3.73 | −0.36 | 0.72 | no | no |
| P5 S&P 500 overnight | +3.01 | −3.17 | −7.78 | −10.79 | −1.04 | 0.30 | no | no |
| P6 USD/INR change | **+10.82** | −12.75 | −5.92 | −16.75 | −1.79 | **0.073** | no | no |
| P7 crude return | −5.95 | +2.32 | −4.37 | +1.58 | +0.15 | 0.88 | no | no |
| P8 US 10-year yield change | −0.28 | −5.70 | −1.94 | −1.65 | −0.16 | 0.87 | no | no |

**The closest is USD/INR.** On sessions after the rupee strengthened most, the
day averaged +10.8 bp, and the spread's p is 0.073 before correction. It does not
survive BH (its threshold is 0.00625 as the smallest of 8), and even at face
value its best tercile covers **0.65×** the round trip. Per the pre-registration,
it is reported as a ratio of cost, and **no filter is proposed from it**.

## What this can and cannot rule out

With 104 sessions per tercile and a 73 bp spread, the standard error of a
tercile spread is about 10 bp, so **a spread of about 20 bp is the smallest this
sample detects reliably**. A tradable effect needs one tercile at 16.63 bp or
more, which with a −3 bp base is a spread of about 20 bp. **The test had the
power to see a tradable effect, and none is there.** Smaller effects may exist.
They would not pay for a round trip.

## The rest of the "not yet built" list

These were not tested, for reasons fixed in the pre-registration:

- **Elliott Wave**: counts are judgement calls that, as Murphy says, trained
  analysts disagree on. There is no fixed rule to test.
- **Point & Figure and time cycles**: both are built from price alone, the class
  the 76-configuration search found carries nothing before costs.
- **ML models** (Jansen ch 9–24): the data now exists (two years of 5-minute
  bars), but a model trained on the same price inputs has the same information.
  They are worth a trial once a genuinely new input exists, such as the
  order-book samples now recorded (README §71).

## Conclusion

**Whole-market breadth and the overnight moves of the dollar, crude, US equities
and US yields do not predict the NSE intraday session by enough to pay for a
round trip.** That closes the last two unbuilt items on the methods page that
brought new information. Breadth stays on the dashboard as context, and no rule
is built from it. The remaining untested new input is the order book.
