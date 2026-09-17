# Development workflow

Trader Sahab is a solo project, but it's real-money-adjacent code, so it
gets a real workflow — branch, PR, review, merge — not commits straight to
`main`. This document is that workflow, and why each piece is here rather
than assumed.

## Branching model: GitHub Flow

Not trunk-based development (Google/DORA's "elite performer" practice) —
that assumes CI/CD mature enough to merge to `main` several times a day
and catch problems that fast; without that maturity it destabilizes `main`
quickly, and this project isn't there. **GitHub Flow** — one short-lived
branch per change, off `main`, merged back via PR, branch deleted — is the
right size for a project this scale. (Toptal, Mergify, and
codewithmukesh's comparisons of the three models all converge on this for
solo/small projects; see the project's own research trail in `research/`
for the fuller writeups this repo already does for its trading logic.)

Branch naming: `type/short-description`, matching the commit-type prefixes
below — `fix/slippage-not-applied-live`, `feat/market-breadth`,
`docs/workflow`.

## Commits: Conventional Commits prefix, existing prose style kept

This repo's commit messages have always been long, well-explained
prose bodies explaining the *why* — that's a real strength, not something
to lose. What's missing is a scannable `type:` prefix. [Conventional
Commits](https://www.conventionalcommits.org/) is close to the default now
(a 2025 sample found 360 of 381 popular JS repos using it) and costs
nothing to adopt: `fix:`, `feat:`, `docs:`, `test:`, `refactor:` before the
same kind of subject line already in use. Enables changelog/semver tooling
later if ever wanted; doesn't require rewriting the existing history.

```
fix: apply slippage to live/paper fills, not just backtests

costs.apply_slippage() was already used by backtester.py for every fill
but never wired into trading_engine._execute()...
```

## Bugs

Every bug gets a GitHub issue as soon as it's confirmed, whether or not
it's fixed right away:

- **Label:** `bug`, or `documentation` for a wrong doc.
- **Contents:** what's wrong, the evidence (real data, logs or code, not a
  hunch), the impact, and a fix direction.

It also gets a row in [`BUG_LOG.md`](BUG_LOG.md). When the fix merges, move
the row to "Fixed" with the PR. Note when the backend was restarted, since
that's when the fix is actually live.

## Pull requests

Every change — a bug fix found watching the live log, a new feature, a
README update — goes through a PR, even solo. `.github/PULL_REQUEST_TEMPLATE.md`
covers what to fill in: what changed and why, evidence it was actually
verified (this project's core discipline — a real check against live data
or the journal DB, not just "the code looks right"), a self-review
checklist, and a one-line rollback plan.

**Squash merge** into `main` — keeps `main`'s history one commit per
logical change, matching the PR title, rather than every intermediate
"wip" commit from the branch.

## Review, without a second person

No co-founder to open a second pair of eyes on this repo, so the
substitute is deliberate, not skipped:

1. **An AI review pass on every PR** — `/code-review` (this repo already
   has Claude Code available) or GitHub Copilot's PR review. GitHub's own
   data on Copilot suggestions: roughly 30% get accepted — real signal,
   not noise, but also proof it isn't sufficient alone.
2. **Read the diff on the PR page, not just in the editor** — the diff
   view surfaces things a normal editing session doesn't (an accidental
   debug print, a stray file, a change that touches more than the PR
   description claims).
3. **CI must be green** (`.github/workflows/tests.yml` — runs the full
   pytest suite on every PR). Tests passing is table stakes, not proof of
   correctness, but the discipline of not merging on red is worth keeping.

## Branch protection: honestly, partial

GitHub's branch protection rules (and the newer Repository Rulesets) both
require GitHub Pro **or a public repo** to use on a private repository —
checked directly against this repo (`gh api repos/.../branches/main/protection`
and `.../rulesets`, both 403 "Upgrade to GitHub Pro or make this
repository public"), not assumed. This repo stays private, so nothing here
is platform-*enforced* — no red X blocking a direct push to `main`. The
PR → review → merge flow above is a personal discipline, not a guardrail
GitHub is holding shut. If that stops being good enough, the honest fix is
GitHub Pro (~$4/mo, unlocks branch protection on private repos), not
making the repo public just to get free enforcement.

What *is* real, not just documented: `require pull request before
merging` + `require status checks to pass` are independent settings from
`require approvals` — GitHub won't let you approve your own PR anyway, so
a solo repo (once on a plan that allows protection) should turn on the
first two and leave approvals off, with "do not allow bypassing" checked
so it isn't just decorative for the one admin account.

## Project board

[Project #1](https://github.com/users/harshece16/projects/1) tracks open
work. Its built-in automations — item added → Todo, item closed → Done,
PR merged → Done, PR linked to its issue — are **on by default**, verified
directly via the API against this project, not assumed from the docs.
Nothing to configure. The one workflow type that isn't auto-created
("auto-add items from this repo matching a filter") has no `gh` CLI path
— `gh project --help` has no `workflow` subcommand — so it'd need the
Project's own ⚙️ Workflows tab in the browser; skippable, since new
issues linked to a PR already flow through the automations that do exist.

Every PR that closes an issue should say `Closes #N` in its description
(already in the PR template) — that's what drives the "PR merged → issue
Done" automation.
