# International markets via IBKR or Alpaca, and Hermes Agent: a first look (2026-10-26)

The owner asked on 2026-10-26: "think about integrating with IBKR or Alpaca and trading in international markets", and "see the Hermes flow". This note is a desk review. It spends no trial and no look. Facts were checked on the web the same day. Where a source could not be confirmed, the claim is marked **unverified**.

## 1. What a new market changes, and what it doesn't

- **It doesn't create an intraday edge.** Every intraday entry family tested here made about zero *before* costs (history §51, §69). Cheaper US costs shrink the loss but cannot turn a zero into a profit. US large caps are the most competed intraday market in the world. Day trading stays closed, in any market.
- **The pattern-day-trader barrier is gone.** FINRA's $25,000 minimum was replaced by intraday margin standards. The SEC approved the change on 14 April 2026, it took effect on 4 June 2026, and brokers can phase it in until 20 October 2027 ([FINRA RN 26-10](https://www.finra.org/rules-guidance/notices/26-10)). That doesn't help, because the blocker is the missing edge, not the rule. And under LRS an Indian resident can't use margin anyway.
- **It could help the momentum book.** Cross-sectional momentum is the most replicated anomaly in US data. US delivery costs are far below India's (about 22 bp plus 10 bp slippage plus ₹15.34 DP per sale here). Fractional shares also remove the whole-share sizing gap (G3, #294) at ₹1–2 L of capital.
- **The session runs at night in IST:** 19:00–01:30 now, and 20:00–02:30 from 1 November 2026, when US clocks change. A monthly rebalance runs unattended, so this matters little for the book. It rules out any human-in-the-loop intraday design.

## 2. The Indian-resident frictions

| Item | What applies | Source |
| --- | --- | --- |
| Remittance | LRS allows USD 250,000 per person per financial year. No margin, leveraged or derivative trading abroad, so a cash account only | Secondary sources; IBKR states that Indian residents can't trade on margin |
| TCS | 20% on LRS investment remittances above ₹10 lakh a year (threshold raised from ₹7 L in Budget 2025). It is adjustable against tax, but cash is locked up until then. Budget 2026 cuts for other purposes may not apply to investment: **check the Finance Act 2026** | [tdsman, Sep 2026](https://blog.tdsman.com/2026/09/tcs-on-foreign-remittances-and-overseas-tour-packages-section-3941-206c1g/) |
| Capital gains | Foreign shares are taxed as **unlisted**: long-term only after 24 months (12.5%, no indexation), short-term at the **slab rate**. A monthly-rebalanced book is nearly all short-term, so its gains are taxed at up to ~30%+, against 20% STCG on Indian listed equity. **This tax drag is the biggest structural cost** | [Zerodha, Budget 2024](https://zerodha.com/z-connect/business-updates/what-changes-for-investors-after-budget-2024) |
| Dividends | 25% US withholding under the DTAA with a W-8BEN (30% without one). Credit is claimed in India | Secondary |
| Disclosure | Schedule FA in ITR-2/3 every year; a return is required even with no other income | [Business Today, Dec 2025](https://www.businesstoday.in/amp/personal-finance/tax/story/foreign-assets-disclosure-what-taxpayers-must-report-in-schedule-fa-in-revised-itr-before-dec-31-508023-2025-12-24) |
| Estate | US estate tax on US-situs assets of a nonresident alien above USD 60,000 (IRS Form 706-NA). Irrelevant at ₹1–2 L. **Not verified this session** | — |

## 3. The two brokers

| | Alpaca | Interactive Brokers |
| --- | --- | --- |
| Live account for an Indian resident | **Unverified.** India isn't on the country page, which says to email support ([countries](https://alpaca.markets/support/countries-alpaca-is-available)). Alpaca bought GIFT City broker Zincmoney IFSC (closed April 2026), and Upstox sells US stocks through Alpaca under LRS, so the live route may be through an Indian intermediary rather than a direct API account | **Yes.** There is an "Indian Individual Residents (trading overseas only)" account covering 90+ markets but not NSE, opened with a PAN and a signed paper form ([IBKR India](https://www.interactivebrokers.co.in/en/accounts/individual-account-india.php)). NSE needs a separate IB India account |
| Paper trading | Anyone worldwide, email sign-up ([docs](https://docs.alpaca.markets/docs/trading-api)) | Yes, with an account |
| Commission | $0 for self-directed US equities through the API, plus regulatory fees | Pro Tiered: $0.0005–0.0035 a share, $0.35 minimum an order ([pricing](https://investors.interactivebrokers.com/en/pricing/commissions-home.php)) |
| Fractional shares | Yes, from $1 | Yes for US stocks |
| Market data | Free IEX-only feed (30 websocket symbols); full SIP is $99/month | Paid subscriptions; delayed data is free |
| API | REST plus websockets, the easiest to build against | TWS API, IB Gateway or Client Portal Web API. A gateway process has to run, and re-authentication is believed to be daily (**unverified**), the same operational problem as Kite's 06:00 logout |

At 15 names and about 3 replacements a month, IBKR's minimum commission works out to about $2 a month, so commission does not decide between them. Eligibility and API ergonomics do.

## 4. Recommendation

1. **Do not build US day trading.** Nothing above changes the intraday verdict.
2. **Gate the broker work behind a cheap measurement** (protocol item 5). The first step is a pre-registered US replication of trial 126's rule. It needs survivorship-free US prices, because free sources drop delisted names, and it must model slab-rate STCG and the 25% dividend withholding. It is a new trial in the momentum family, so the bar is t ≥ 2.865. Use `trial-check`. If it fails, no broker code is needed.
3. **If it passes:** add an `alpaca_broker.py` beside `paper_broker.py` and `kite_broker.py`, against **Alpaca paper** first (no money, no LRS, no approval needed). Run the US book in paper beside the Indian one.
4. **Real money, if ever:** IBKR is the confirmed route for an Indian resident. Use Alpaca only if support confirms a direct account. Keep remittances under ₹10 L a year to avoid locking up cash in TCS. The Indian book's go-live list (G1–G15) comes first either way.

## 5. Hermes Agent ("the Hermes flow")

[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) (MIT, very widely starred, active) is a Python agent with a CLI, a TUI and a messaging gateway (Telegram, Slack, Discord and others). It has file memory plus SQLite search, skills in the same SKILL.md format Claude Code uses, and a cron scheduler that runs natural-language jobs and posts the results to chat. That scheduler is its "flow".

- **For prediction, no.** Nobody publishes net-of-cost results from it. One integration guide itself advises monitoring only.
- **As a runtime here, no.** It needs at least a 64k-token context. On the RTX 3060 Ti (8 GB), a 7–8B model at that context would likely spill to CPU (estimated, not tested). It would also add a second agent stack on a GPU shared with the studio, against the no-jobs-while-gaming rule. launchd plus Chotu plus Claude Code already cover the 09:00 nag, the watchdog and the reports.
- **The ideas are worth borrowing.** [tradermonty/hermes-trading-research-agent-work-package](https://github.com/tradermonty/hermes-trading-research-agent-work-package) has a pre-market, after-close and weekly review routine with "no orders, human decides" controls. Its sister repo [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills) (MIT) is Claude-native. Its pre-trade discipline gate and signal post-mortem were adapted into `.claude/skills/rebalance-check` (#307).
