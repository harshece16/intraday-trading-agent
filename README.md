# Trader Sahab: a research-driven trading agent for NSE (Zerodha)

Trader Sahab is a paper-mode trading system for Indian equities: a FastAPI backend (`backend/`), a React dashboard (`frontend/`) and Zerodha Kite Connect as the broker. Its one rule is that **nothing trades until it passes a test written down before its data was read.**

It began as an intraday agent built on Zerodha Varsity's checklist. Measured over 495 sessions, that approach loses 0.36R a trade (t −3.59), and so did every intraday rule tried after it. More than 200 recorded trials have produced one pass: a **monthly momentum book held in delivery**, and the pass is narrow. **No real-money order has ever been placed**, and going live is the owner's decision alone.

## Where it stands (2026-10-26)

| Book | What it is | Record so far | Next |
| --- | --- | --- | --- |
| **Momentum book** (the product) | Holds the 15 of NSE's 200 most-traded stocks with the strongest volatility-adjusted 6- and 12-month returns, in delivery, on ₹10 L of paper capital. Rebalances at the close of each month's first session. Trial 126: +0.71% a month over its universe after costs, 2010–2025 (t 2.51) | Since 1 Oct: ₹9,38,476 against its benchmark's ₹9,53,962 on 23 Oct (−1.6%). One month says nothing, and the switch-off band only applies from month 6 | Rebalance on 2 Nov. Go-live gaps G1–G15 (#292–#304) must close before any real money |
| Jev2 (a blind, decomposed LLM judge on the intraday shortlist) | Pre-registered forward test | 42 trades (of 100 decisions) over 4 sessions, +46.6 bp a trade, session-clustered t 1.19 against the pass line of 2.39 (as of 7 Nov). One day, 8 Oct at +158 bp, carries most of it. Every session since 14 Oct has been void: Kite was not connected by 09:45 | Verdict at 300 trades or 60 sessions. Needs Kite connected by 09:45 |
| Jev book (an LLM shown the scanner's side) | Pre-registered forward test (trial 123) | Agreed with the scanner on 101 of 120 decisions, so it cannot be told apart from the scanner. 114 trades over 8 sessions, +11.2 bp a trade, session-clustered t 0.74 (as of 7 Nov) | Verdict at 300 trades or 60 sessions |
| Intraday engine | Paper record of the original checklist strategy | 48 closed legs, −₹1,731, 3 winners (as of 18 Oct) | Closed as a money-maker. Kept running as a record |
| Rule lab | 107 single rules, each its own shadow paper book | Historical search: no survivor among 104,655 combinations | One forward read after 40 lab sessions |

The [pivot brief of 2026-10-18](docs/research/pivot-brief-2026-10-18.md) set the order of work. First, no void paper days. Then the momentum book moves to real money. Then come delivery-horizon trials, pre-registered one at a time.

## Read this first

- **Nothing here guarantees profit.** The momentum book's evidence is one backtest, 200 unseen stocks and eight unseen months. It lost 13% against its universe in 2025, and at the project-wide trial count it would not pass.
- **Costs decide everything.** A cash intraday round trip costs about 16.6 bp. A delivery round trip costs about 22 bp, plus 10 bp of slippage and a ₹15.34 DP charge per stock sold. Every intraday entry family tested makes about zero before costs, so the costs are the whole loss.
- **These lines are closed. Don't retry them blind:** the Varsity checklist, the 76-configuration intraday rule search, filings and results days, post-earnings drift, the 14-signal ranker, the overnight ETF premium, Kronos and other forecasting models, and frog-in-the-pan. The evidence is in [docs/history.md](docs/history.md) and [docs/research/trials.md](docs/research/trials.md).
- **Every trading day:** Kite logs out at 06:00, so click **Reconnect** on the dashboard before 09:15. The watchdog sends a reminder at 09:00 and 09:30, and logs a VOID DAY at 09:46 if Kite is still not connected.
- **Most retail intraday traders lose.** SEBI found that 71% of individual intraday cash traders lost money in FY23, and that 93% of individual F&O traders lost money over FY22–FY24.
- **F&O means buying calls and puts only**, never writing them. The confidence gate keeps it off until an edge is proven, and it has never traded.

## Run it

```bash
cd backend && source .venv/bin/activate && uvicorn app:app --port 8000   # API
cd frontend && npm run dev                                               # dashboard, http://localhost:5500
cd backend && .venv/bin/python -m pytest tests/ -q                       # tests
```

Every API route except `/kite/callback` needs the dashboard key in the `X-Api-Key` header (`backend/.dashboard_key.json`). Paper mode is the default. Details are under [Setup](#setup).

## Documents

- [High-level design](docs/architecture/HLD.md) · [Low-level design](docs/architecture/LLD.md) · [Rules](docs/architecture/RULES.md) · [Knowledge graph](docs/architecture/KNOWLEDGE_GRAPH.md) · [Interactive rulebook](https://claude.ai/artifact/5VxZ5bHM8b79u2sSUUtWrK)
- **[docs/history.md](docs/history.md)** has every numbered section, §1–§129: what was built, measured and decided, in order. It also holds the dashboard tour, the requirements, the backtest results and the known limitations. Code comments that cite "README §N" point there.
- [docs/research/](docs/research/) holds the pre-registrations, results files, trial ledger and reviewer inbox.
- [BUG_LOG.md](BUG_LOG.md) · [WORKFLOW.md](WORKFLOW.md)

## Setup

```bash
cd webapp/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MARKETAUX_API_KEY=...        # optional
export ALPHAVANTAGE_API_KEY=...     # optional — market-wide news discovery only
export ANTHROPIC_API_KEY=...        # optional — LLM-read news sentiment, see below
uvicorn app:app --port 8000
```

On first run, the backend auto-generates a **dashboard API key**
(`backend/.dashboard_key.json`, gitignored). It logs the key in full on that
run only; later starts log a masked reference. Every route except
`/kite/callback` requires it in the **`X-Api-Key` header**. A `?key=` query
string is refused with 401, because uvicorn logs every request line (#87).
The WebSocket takes the key as its first message, and the Connect Kite
button fetches the login URL with the header instead of opening a keyed
link. Never put the key in a URL.

In another terminal:

```bash
cd webapp/frontend
npm install
npm run dev          # http://localhost:5500
```

It prompts for the dashboard API key once and keeps it in the browser's
`localStorage`. The key requirement exists
because the backend sometimes needs to be reachable from the public
internet (see "Connecting Kite locally" below) and has real control
surface — without it, anyone with the URL could flip the dashboard to live
trading or turn on F&O. `npm run build` produces a static `dist/` you can
serve any other way if you don't want the dev server running.

The first scan runs within a minute, even when the market is closed (it
shows the last session). To point the dashboard at a backend on another
local port, add `?api=http://localhost:8765` to the URL.

Main settings in `config.py`: `SCANNER` (universe filters, active count,
pinned symbols), `MARKET_FILTER` (risk-off / VIX behaviour), `NEWS`
(sources), `STRATEGY_PARAMS["trader_brain"]`, `RISK`, and `FNO` (capital
allocation, confidence bar, expiry window — disabled by default).

### Connecting Kite locally

Kite Connect's app registration requires an **HTTPS** Redirect URL, even for
local testing — `http://127.0.0.1:8000/kite/callback` will be rejected by
the form. Two ways around it:

1. **CLI script, no exposure needed** — `python generate_access_token.py`
   opens the login in your browser; after you log in, the `request_token` is
   in the browser's address bar even if the redirect page fails to load. You
   paste it into the terminal; nothing on the internet ever needs to receive
   the redirect. Register *any* real, resolving `https://` URL as the
   Redirect URL just to satisfy the form — it never needs to actually
   respond. This is the recommended daily routine (see below).
2. **In-app "Connect Kite" button (the backend runs the tunnel for you)**.
   One-time setup:
   - `brew install ngrok`.
   - Get a free authtoken from [dashboard.ngrok.com](https://dashboard.ngrok.com), then run `ngrok config add-authtoken <token>`.
   - Claim the one free static domain (Gateway → Domains).
   - Register `https://<your-static-domain>/kite/callback` as the Redirect URL at developers.kite.trade.
   - Set `config.KITE_TUNNEL["domain"]`, or the `NGROK_DOMAIN` env var. This repo defaults to `ambiguity-patchy-untold.ngrok-free.dev`.

   After that, **don't start ngrok yourself.** Clicking Reconnect makes the backend start ngrok on that domain and wait until the tunnel is up. Then it sends you to Kite, and **stops the tunnel a few seconds after the callback**. It also stops after 10 minutes if the login is abandoned, and when the backend shuts down. The backend is reachable from the internet only for the minute or so a login takes, and every route except `/kite/callback` still needs the dashboard key. An ngrok you started by hand is reused and left running.

**If the tunnel is down when you log in**, Kite still redirects to it and the page fails to load. The address bar keeps the whole redirect, though. Replace the tunnel host with `http://127.0.0.1:8000` and keep the rest of the URL unchanged (`/kite/callback?...&request_token=...`), then open it. The running backend completes the login the same way. The request token can only be used once and expires within minutes, so do this straight away. (Verified 2026-09-23 with ngrok stopped.)

**Kite sessions expire daily, at 06:00.** Whichever method you used, redo
it each trading morning before 09:15, even in paper mode. The order-book
test needs a live Kite feed for every session it counts, and without one
the engine falls back to yfinance prices about 15 minutes behind.
`python generate_access_token.py` doesn't depend on any tunnel still being
up, which is why it's the more durable daily habit.

### Getting an Anthropic API key (for LLM-read news sentiment)

Optional — only needed if you want `llm_sentiment.py` reading headlines
instead of the keyword lexicon. `pip install -r requirements.txt` already
pulls in the `anthropic` SDK, so no separate install once you have a key.

1. Go to [console.anthropic.com](https://console.anthropic.com) and sign
   up or log in.
2. Anthropic's API is prepaid — under **Billing**, add a payment method
   and purchase credits before any call will succeed. This is a real (if
   small — see the cost tracking on the Technical Analysis page) ongoing
   cost, not a one-time setup fee.
3. Under **API Keys**, create a new key and copy it — it's shown once.
4. `export ANTHROPIC_API_KEY="sk-ant-..."` and restart the backend.
   Setting the key alone doesn't turn the feature on: flip the toggle on
   the Technical Analysis page (or `POST /api/llm-sentiment/enable`) once
   you're ready — it stays off by default even with a valid key, and you
   can turn it off again any time without restarting anything.

### Storing the TypeSafe API key (for the Jev book)

The Jev book ([§86](docs/history.md#86-the-jev-book-an-llm-judge-on-the-daily-shortlist-tested-in-paper)) calls TypeSafe's official API and needs a key;
without one, each day is recorded as "Jev unavailable" and nothing is
traded. TypeSafe is prepaid: add credits, then create a key at
[console.typesafe.ai/keys](https://console.typesafe.ai/keys). At about
34,000 input tokens a trading day it costs roughly $0.03 a month.

Copy the key to the clipboard and run, from the repo root:

```bash
pbpaste | backend/.venv/bin/python backend/typesafe_key.py set
backend/.venv/bin/python backend/typesafe_key.py test     # one tiny request
backend/.venv/bin/python backend/typesafe_key.py status   # never prints the key
```

`set` with nothing piped in asks for the key at a hidden prompt. Never pass
the key as a command-line argument: it lands in shell history. The key is
written to `backend/.typesafe_key.json` with mode 0600 (gitignored), and the
`TYPESAFE_API_KEY` environment variable overrides it. The engine reads the
key on each call, so no restart is needed.

### Going live (only once backtests and paper results justify it)

1. Create an app at https://developers.kite.trade and subscribe to the
   **Connect** tier (needed for historical data + live market quotes —
   Personal tier explicitly excludes both, and F&O has no other data source).
2. Whitelist a **static IPv4** on the app. Use a VPS in India, and run the
   backend there, if your home connection doesn't have one.
3. `export KITE_API_KEY=... KITE_API_SECRET=...`, then log in each morning
   (`python generate_access_token.py` or **Connect Kite**). The token is
   saved to the gitignored `.kite_session.json`.
4. Click **LIVE** and confirm.
5. **Separately**, if you also want F&O: open the Portfolio page and turn
   F&O on (its own confirmation dialog). It stays off by default even once
   cash equity is live — an order only reaches Kite when both are on.

## Development workflow

Every change — a fix, a feature, a README update — goes through a branch
and a PR, not a direct commit to `main`. See **[WORKFLOW.md](WORKFLOW.md)**
for the full picture: branch naming, commit conventions, how solo code
review actually works without a second person, CI (`.github/workflows/tests.yml`
runs the full pytest suite on every PR), and an honest note on why branch
protection isn't platform-enforced here (private repo, free tier — a real,
checked-not-assumed limitation, not an oversight). Open work is tracked on
[Project #1](https://github.com/users/harshece16/projects/1). Every confirmed
bug gets a GitHub issue labeled `bug` and a row in
**[BUG_LOG.md](BUG_LOG.md)**, which lists open bugs and everything fixed so
far with its PR.
