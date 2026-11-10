# Link triage, 2026-11-07 → 2026-11-08: 19 Instagram reels

The owner sent 19 trending trading-agent and AI-tooling reels. A separate research agent took each reel: the caption, the comments that could be fetched, any slides, the transcript, and key frames. Each reel was then checked against the closed lines in `pivot-brief-2026-10-18.md` §1 and `trials.md`.

- **One reel became a trial:** OI build-up became trial 207. It **FAILED** (`results-oi-buildup.md`).
- **One became a method note** on a live-readiness issue (#302).
- **The rest are not trading strategies,** or cannot be tested with this repo's data.

Nothing from this batch goes to paper or live.

## Outcome by reel

| Reel | What it is | Verdict | Outcome |
| --- | --- | --- | --- |
| DfFrvCWTijy | Futures OI build-up: price up and OI up means fresh longs | Testable and not a closed line | **Trial 207.** Prereg #321, code #322, holiday-expiry fix #323/#324, result #325. **FAIL**: −56.9 bp a session, t −19.7, every year 2009–2025 negative, mechanism backwards. Line closed. |
| DfPJm5FB754 | "3 tests that break a backtest" | Method only, no edge claim | A comment on #302 proposes setting the hard drawdown stop from a block bootstrap of the book's monthly returns. |
| DfFDtGpOBHy | Trading coach and website | Authenticity not shown | None |
| DdY55d0tPOL | Open-source market-making engine that replays the order book with queue and latency (crypto) | HFT on tick-level order-book data we cannot get | None |
| DfL3TotRdV1 | "AlgoFactory": genetic search over NQ 4H strategies, in-sample curves only | Data mining with no out-of-sample test. This is the overfitting our protocol exists to stop. | None |
| DfacvOIBCQ9 | NQ backtest behind a paywall | Nothing to check | None |
| Debex7eiZZu | Hypothesis-testing explainer (t = mean / SE, p-values) | Already our protocol, which adds Newey–West t and deflated Sharpe at the family count | None |
| DfUsvACMSgj | Black–Scholes and Monte Carlo explainer | Numbers check out (10.45 at 1 y, 2.51 at 1 m); no strategy | None. The repo has no option prices. |
| Dern6eUT_Tk | ML explainer | Not a strategy | None |
| DfbwJGFMSqQ | Trading course ad | Ad | None |
| DfcWc7Az1T0 | F&O data website ad | Ad | None |
| De-ubnLp9ZV | Screen recorder | Not trading | None |
| DdO1UioAHAS | "40 Claude repos" list | Tooling, not trading | Optional: a context7 MCP trial for the workflow (not taken) |
| DfBiOnLMcSP | "5 MCPs" list (Perplexity, Playwright, Firecrawl, Hyperframes, Chrome) | Tooling, not trading | Optional: Hyperframes for the studio channels (not taken) |
| DfTRiosCq6u | claude-obsidian | Tooling | None |
| DfCRr86jGEK | Orbit Agents SaaS ad | Ad | None |
| DfEJ10mtZdx | Skills auto-install | Tooling | None |
| De4oK2PNPvB | OmniRoute model router | Supply-chain risk | Audit before any use; not adopted |
| DfPXTVtxG7X | Hugging Face model-name jargon (abliterated, distilled, LoRA, MTP) | Not trading | None. Don't use abliterated models for Slack agents. |

## Notes

- **Comment-for-link funnels.** About half the reels are lead funnels ("comment X and I'll DM the link"). The research agents did not comment, so anything behind those funnels was not fetched.
- **Ad-heavy F&O content.** The F&O-themed reels were mostly ads or coaching. The only falsifiable claim among them (OI build-up) failed by a wide margin, with no gross edge for any vehicle to collect. It is no basis for live F&O trading.
- **Second slot in the futures-positioning family.** It is still unspent. The prereg names its likely use: the short-side OI states as put buys. That needs historical option prices first.
