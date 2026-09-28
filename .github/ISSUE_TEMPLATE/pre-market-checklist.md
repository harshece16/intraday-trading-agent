---
name: Pre-market checklist
about: The daily checks before 09:15 and after the close
title: "Pre-market checklist: YYYY-MM-DD"
labels: []
---

Rule ids point into [the rules checklist](https://github.com/harshece16/intraday-trading-agent/blob/main/docs/architecture/RULES.md).

## Before 09:15

- [ ] Kite is reconnected. The header shows it connected, and no pre-open alert fired at 08:45 (`OPS-07`, `DAT-06`)
- [ ] The backend is up and the dashboard loads (`OPS-02`)
- [ ] The mode is Paper, unless going live was decided (`EXE-04`)
- [ ] Entries are paused or not, as intended (`OPS-01`)
- [ ] Last evening's momentum job ran: the Momentum Book page shows yesterday's session (`MOM-12`)
- [ ] It is a trading day: no holiday banner

## During the session

- [ ] 09:45: the Jev Book page shows today's round, not "No live prices" or "Jev unavailable" (`JEV-07`, `JEV-08`)
- [ ] The order-book sampler is writing: `GET /api/journal/depth-samples` shows today's session (`OBK-01`, `OBK-03`)
- [ ] Any review card was decided inside its 5 minutes, or left to expire

## After 15:30

- [ ] No position is open (`EXT-04`)
- [ ] The Jev round is closed and scored
- [ ] The session summary line is in the activity feed
- [ ] Anything that looked wrong has an issue and a `BUG_LOG.md` row (`WFL-07`)

## First session of a month

- [ ] After 19:30: the Momentum Book page shows the rebalance and 15 holdings (`MOM-06`)
- [ ] Cumulative excess is above the band's floor (`MOM-09`)

## Notes

