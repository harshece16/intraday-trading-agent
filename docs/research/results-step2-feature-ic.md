# Step 2 results — per-feature scanner IC

**Pre-registered:** `prereg-step2-feature-ic.md` — `bc704e5`, amended
`d165699` / `535a082`, all committed before this measurement was written.
**Run:** 2026-09-21. Selection split only, **2023-09-25 → 2026-01-01**.
**Trial count:** unchanged at **34**. Ten research looks, not strategy trials.

> **Three of ten features survive both Benjamini–Hochberg and Bonferroni.**
> That is the first positive result this project has produced — and **two of
> the three cannot be interpreted as registered**, for reasons below. **Do not
> act on this table before reading the problems section.**

---

## Sample

| | |
| --- | --- |
| Selection sessions available | 813 |
| **Usable sessions** (≥20 eligible stocks) | **561** |
| Stock-sessions built | 51,962 |
| **Dropped for 252-bar warm-up** (§D3) | **27,626** |
| Span | 2023-09-25 → 2026-01-01 |

The warm-up requirement removed 35% of candidate stock-sessions. Four years of
daily history was downloaded so the requirement holds from the first selection
session, as §D3 directs.

---

## Data-quality gate (§D4) — and a process failure

| | |
| --- | --- |
| Overlapping stock-sessions (yfinance ∩ Kite) | 29,949 |
| **Correlation** (yf open→close vs Kite first-open→last-close) | **0.9832** |
| **Share differing by more than 25 bp** | **18.55%** |

**My judgement: agreement is good enough to proceed, with one caveat that
matters.** A correlation of 0.983 across ~30k stock-sessions is strong. The
18.55% tail is material but not disqualifying: classical errors-in-variables
attenuates ICs **toward zero**, so target noise makes survivors *understated*
rather than spurious.

**The caveat:** that reasoning holds only when the measurement error is
independent of the feature. **`atr_pct` is precisely the feature where it may
not be** — more volatile stocks plausibly have larger vendor discrepancies, so
error and feature could be correlated, which *can* manufacture association.
This is not tested here and is a live concern about the strongest result in
the table.

### Process failure: the gate was computed but not enforced

The pre-registration says *"If agreement is poor, stop and report instead of
running the ICs."* **I implemented the gate as a report, not a halt.** The
script printed the numbers and ran the ten tests unconditionally.

So the judgement above is being made **after** seeing the ICs, which is
exactly the contamination the gate existed to prevent. I believe I would have
passed a 0.983 correlation either way, but I cannot demonstrate that, and the
claim is worth less because of the order in which it happened. Recorded as a
failure rather than smoothed over.

---

## The ten tests

Family size **10**. BH at q = 0.10; Bonferroni threshold p < 0.0050.
Selection split only — **no held-out look has been taken** (see Problems).

| Feature | Test | Sessions | Mean | t | p | % pos | BH | Bonf |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `atr_pct` [^band] | rank IC | 561 | **−0.0558** | **−6.13** | <0.0001 | 39.4 | **Y** | **Y** |
| `from_low` [^sign] | rank IC | 561 | **−0.0415** | **−5.23** | <0.0001 | 41.0 | **Y** | **Y** |
| `from_high` | rank IC | 561 | **+0.0258** | **+3.33** | 0.0009 | 55.6 | **Y** | **Y** |
| `nr7` | session diff | 509 | +0.0346 | +1.54 | 0.1229 | 51.7 | . | . |
| `rs10` | rank IC | 561 | −0.0090 | −1.24 | 0.2167 | 49.2 | . | . |
| `pattern` | session diff | 556 | −0.0221 | −1.01 | 0.3118 | 47.7 | . | . |
| `rsi` [^band] | rank IC | 561 | −0.0060 | −0.82 | 0.4115 | 49.6 | . | . |
| `reversal` | session diff | 372 | −0.0286 | −0.76 | 0.4486 | 48.7 | . | . |
| `inside` | session diff | 537 | +0.0211 | +0.71 | 0.4752 | 48.2 | . | . |
| `trend` | session diff | 521 | −0.0062 | −0.18 | 0.8595 | 52.6 | . | . |

Mean is in the sign convention registered: positive = "the scanner's use of
this feature is correct".

[^sign]: **Corrected sign.** The run printed **+0.0415, t = +5.23, 59.0%
positive**, because the code applied sign −1 where the scanner's +10 sits on
the SHORT side. The table above carries the corrected **−0.0415, t = −5.23,
41.0%**. The statistic is unchanged — p depends on |t|, so BH and Bonferroni
outcomes are identical — and **no rerun was done**. Only the meaning flips,
and it flips to "the scanner's 52-week-low short signal is backwards". Both
figures are kept visible so the history is auditable. See Problem 1.

[^band]: **Monotonic association measured; the scanner's banded use of this
feature is not tested.** `atr_pct` (band 1.5–4.0%) and `rsi` (side-dependent
bands) are not monotonic preferences, so a fixed-sign rank IC cannot test
"the direction the scanner uses it". Per reviewer Entry 4 §D, no band test is
added: the composite is already dead, so validating its bands is no longer
the question, and each extra test would enlarge the family for no gain. See
Problem 2.

### Detectable effect sizes (amendment 1)

Computed from each test's own spread, so nulls read as "no effect larger
than X" rather than "nothing found".

| Feature | Detectable at t=2 | Observed |
| --- | --- | --- |
| `rs10` | 0.0145 | −0.0090 |
| `rsi` | 0.0145 | −0.0060 |
| `from_high` | 0.0155 | +0.0258 |
| `from_low` | 0.0159 | −0.0415 |
| `atr_pct` | 0.0182 | −0.0558 |
| `nr7` | 0.0449 | +0.0346 |
| `pattern` | 0.0438 | −0.0221 |
| `inside` | 0.0590 | +0.0211 |
| `trend` | 0.0695 | −0.0062 |
| `reversal` | 0.0754 | −0.0286 |

The seven failures are genuine nulls only at these resolutions. `trend` and
`reversal` in particular could hide an IC of ~0.07 — larger than any survivor
— and this design would not see it. **"No effect" for the sparse features
means "no effect larger than roughly 0.05–0.08".**

---

## Problems — read before using the table

### Problem 1: `from_low`'s sign convention is implemented backwards

The scanner awards `pct_from_low <= 3` **+10 on the SHORT side** (`s < 0`):
near a 52-week low is read as bearish. So "the scanner is correct" means low
`from_low` predicts a **negative** return.

My code applied sign = −1, which reports positive when low `from_low` predicts
a **positive** return — the opposite. **The sign should have been +1.**

**Correctly signed, the result is −0.0415 with t = −5.23**: the scanner's
52-week-low short signal is **significantly backwards** over this sample.
Stocks near their 52-week low went *up* intraday, not down.

**No rerun is needed and none was done.** p is a function of |t|, so the
p-value, BH and Bonferroni outcomes are identical; only the interpretation
flips. Rerunning would produce the same table with one sign changed, and the
standing rule's rerun allowance is not needed for a relabelling.

`from_high` was coded correctly (+10 on the long side for low `from_high`;
sign −1 gives positive when the scanner is right). **Its +0.0258 means the
52-week-high long signal does work**, weakly.

### Problem 2: `atr_pct` and `rsi` are band-shaped, so a rank IC cannot test "the scanner's direction"

The scanner scores `1.5 <= atr_pct <= 4.0` → +5 — a band, with **both** ends
penalised by omission. RSI is worse: the bands are **side-dependent**. On the
long side RSI 45–70 → +5 and RSI > 75 → −8; on the short side RSI 30–55 → +5
and RSI < 25 → −8. **Neither is a monotonic preference.**

A rank IC with a single fixed sign tests "higher is better", which is not what
either feature does. So:

- **`atr_pct`'s −0.0558 (t = −6.13) is a real measurement** — higher daily ATR
  predicts lower open-to-close return, strongly — **but it is not a test of the
  scanner's use of ATR**, and it should not be reported as one.
- **`rsi`'s null is likewise not a test of the scanner's RSI bands.** A
  band-shaped effect can easily show zero monotonic rank IC, and a
  side-dependent one can do so even when both sides are individually strong.

The pre-registration's sign-convention paragraph assumed every feature was
monotonic. It is not. **This is a specification gap, not a coding bug**, and I
have not chosen a replacement test unilaterally.

**Reviewer ruling (Entry 4 §D):** no band tests are added, and both features
are recorded as *"monotonic association measured; scanner's banded use not
tested"*. `atr_pct`'s result stands as a measurement, **not** as support for
the scanner.

### Problem 3: the held-out look has NOT been taken

The pre-registration allows the survivors **one** held-out look, with
Bonferroni across survivors (3 survivors → α = 0.0167).

**I have not run it**, deliberately. Two of the three survivors have
interpretation problems above. Spending the single irreversible held-out look
on a set that includes a mis-signed feature and a feature whose test does not
match its registered purpose would waste it. The look is still available.

---

## What this does and does not say

**It does not revive the strategy.** The largest effect is an IC of 0.056.
Step 1 established friction of ~0.25R per trade (likely more, pending §B).
An IC of that size does not translate into anything close to that hurdle, and
nothing here is a reason to re-tune the old system.

**The most interesting line is not a survivor.** `trend` — the scanner's
single heaviest weight at +20/−15 points — returns **t = −0.18**, the flattest
result in the table. The feature the composite leans on hardest carries no
measurable information about the coming session's return at a resolution of
~0.07.

**And `from_low`, correctly signed, is significantly backwards.** A component
the scanner adds points for is, over 561 sessions, associated with the
opposite outcome.

**Survivorship bias is worst exactly here.** The universe is today's NIFTY 100
applied to history, and a volatility sort is where that distorts most: the
volatile names that fell out of the index are precisely the ones missing.
Carried into every later statement about this factor.

---

## Next — reviewed, and the rule is now stricter

Entry 4 ruled on all three problems and added a fourth consideration I had
not raised: **the three survivors are probably one factor, not three.**
`from_high` and `from_low` are both distances across a 52-week range, and a
volatile stock has a wide range — so all three plausibly measure the same
thing, and promoting them as three discoveries would triple-count one
association.

The held-out look now requires **all three** of: BH survival on selection
(already true), passing a **tradable Kite target** (09:20 open → 15:10 close,
same sign and |t| > 2), and — for `from_high`/`from_low` — a **partial IC
controlling for `atr_pct` with |t| > 2**. Bonferroni across whatever
qualifies. Committed in `prereg-step2-feature-ic.md` amendments 7–9 and
`prereg-step2-followups.md`, **before any of those measurements ran.**

Runs A, B and C follow, on selection data only. **The held-out look does not
happen until the reviewer has seen them.** The Entry 3 items — null
diagnostic, friction decomposition, README §51/§52 diff for the user, the
ten-section report — follow after.
