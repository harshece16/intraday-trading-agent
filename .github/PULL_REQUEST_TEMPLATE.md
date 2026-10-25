## What changed and why

<!-- The "why" matters more than the "what" — the diff already shows what changed.
     What real problem, finding, or request prompted this? Link the issue if there is one. -->

Closes #

## Evidence

<!-- This project's whole discipline: never fabricate, always verify.
     What did you actually check, not just write? -->

- [ ] Ran the real thing (a live/paper check, a backtest, a direct query against `data/sahab_journal.db`) — not just read the code
- [ ] `cd backend && python -m pytest tests/ -q` — all passing
- [ ] Added/updated a regression test for the specific bug or behavior this PR addresses
- [ ] If this touches a risk/confidence/entry threshold: called out as a real tradeoff, not silently changed

## Self-review checklist

<!-- No second reviewer on a solo project — this is the substitute.
     Read your own diff top to bottom before requesting the merge, as if it were someone else's. -->

- [ ] Read the full diff, not just the files I expected to change
- [ ] No debug prints, commented-out code, or leftover scratch scripts
- [ ] `docs/history.md` section added if this changes documented behavior, and the README status table if what runs changed
- [ ] If deploying live: backend restarted and the change verified against a real request, not just "tests pass"

## Rollback plan

<!-- One sentence: if this turns out wrong once it's live, how does it get undone? -->
