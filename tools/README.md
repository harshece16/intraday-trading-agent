# tools/

Developer utilities that are **not part of the trading agent**. Nothing here
is imported by `backend/` or `frontend/`, and nothing here runs in the live
path.

## `token-usage.py`

Reports what each Claude Code session actually cost, read from the JSONL
transcripts under `~/.claude/projects/<project>/`. Nothing is estimated from
message lengths — it sums the `usage` each API call reported.

```bash
python3 tools/token-usage.py               # all sessions, largest first
python3 tools/token-usage.py --top 5
python3 tools/token-usage.py --detail 2d14 # per-model, by session-id prefix
```

### Read `fresh`, not `raw`

Three numbers, because they differ by orders of magnitude:

| | meaning |
| --- | --- |
| **raw** | every token counted, cache reads included |
| **fresh** | input + output only — genuinely new work |
| **cost** | cost-weighted; cache reads ~0.1x, cache writes ~1.25x |

On the session that built this repo's phase-2 research: **raw 1.65 B, fresh
2.60 M** — cache reads were **98.5%** of raw. Quoting `raw` overstates the
work by roughly 600x.

### Caveats

- **Prices are hardcoded in the script and will go stale.** They are list
  prices; a subscription or a different tier makes the cost figure wrong.
  Edit `PRICING` at the top. Calls / raw / fresh are hard data; **cost is the
  least reliable line.**
- It only reads transcripts. It writes nothing, sends nothing, and needs no
  credentials.

### Why it lives here

`~/.claude/` is not a git repository and should not become one — it holds
credentials and the full text of every session. This repo is simply the
version-controlled home closest to hand. A copy also sits at
`~/.claude/tools/token-usage.py`, which is where it is normally run from.
