# Trader Sahab — System design

Start here. These documents describe `main` as of 2026-09-28.

| Document | Read it for | Length |
| --- | --- | --- |
| [High-Level Design](HLD.md) | What the system is, its parts, a trading day, where entries stop, how it fails | 10 minutes |
| [Low-Level Design](LLD.md) | Every module, the tick sequence, formulas, the API, the database, the settings | Reference |
| [Rules checklist](RULES.md) | All 227 rules: what each says, the code that enforces it, how to check it | Reference |
| [Knowledge graph](KNOWLEDGE_GRAPH.md) | How the code and the research connect, and how to query it | 5 minutes |

## Interactive rulebook

[Open the rulebook](https://claude.ai/artifact/5VxZ5bHM8b79u2sSUUtWrK). It
has search, filters by area and status, a tick for each rule you have
checked, and the design diagrams. Ticks are saved to the page. The link is
private to the owner.

The same page is in this folder as [`rules.html`](rules.html). GitHub shows
its source; download it and open it in a browser to use it. There, ticks are
kept in that browser.

## Checklists you can tick on GitHub

Open a [new issue](https://github.com/harshece16/intraday-trading-agent/issues/new/choose)
and pick a template. Checkboxes in an issue can be ticked and are saved.

| Template | Use it |
| --- | --- |
| Pre-market checklist | Each trading morning |
| New strategy checklist | Before testing any new idea |
| Go-live readiness | Before the first real-money order |

## Keeping these documents true

| File | How it is maintained |
| --- | --- |
| `rules.json` | The one source for the rules. Edit it by hand |
| `RULES.md`, `rules.html` | Generated. Run `python3 tools/build_rules_docs.py` |
| `HLD.md` | Written by hand. Its diagrams and its trading-day table also feed `rules.html` |
| `LLD.md`, `KNOWLEDGE_GRAPH.md` | Written by hand |

`backend/tests/test_rules_catalogue.py` runs in CI. It fails when a rule
names a file, function or test that no longer exists, when a generated page
is stale, or when one of these documents links to a file that isn't there.
