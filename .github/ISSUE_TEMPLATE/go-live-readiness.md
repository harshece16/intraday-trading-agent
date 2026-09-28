---
name: Go-live readiness
about: What must be true before the first real-money order
title: "Go-live readiness: YYYY-MM-DD"
labels: []
---

Going live is the owner's decision alone. This list is what the design says
must hold first. Rule ids point into
[the rules checklist](https://github.com/harshece16/intraday-trading-agent/blob/main/docs/architecture/RULES.md).

## Evidence

- [ ] The strategy that will trade passed its pre-registered test and its confirmations
- [ ] Its paper book has run forward and is inside its band
- [ ] The confidence gate passes on evidence, not because a setting was lowered

## Known gaps that must be closed

- [ ] #155 Live fills are booked at Kite's executed price
- [ ] #156 A live position is watched after a restart
- [ ] #66 Slippage is measured, not assumed
- [ ] #162 The holiday list covers the current year
- [ ] #161 The dashboard key file is mode 0600
- [ ] If options will trade: #154 and #157

## Account and machine

- [ ] A static IP is whitelisted on the Kite app
- [ ] Kite is connected and `GET /api/control/live-readiness` lists no blocker (`EXE-04`)
- [ ] Kite holds no position the engine doesn't track (`RSK-10`)
- [ ] The backend restarts cleanly and the watchdog is installed
- [ ] Telegram alerts arrive on the phone

## Limits, checked in Paper first

- [ ] The kill switch closes everything and returns to Paper (`EXT-07`)
- [ ] The daily loss limit stops new entries (`RSK-06`)
- [ ] The position cap and the sector cap hold (`RSK-07`)
- [ ] The 15:08 square-off leaves nothing open (`EXT-04`)
- [ ] The liquidity check refuses an entry when the order book can't be read (`EXE-01`)
- [ ] Tick stops are live: `GET /api/stops/status` is not stale (`EXT-02`)

## Decision

- [ ] Starting capital and the largest first position are written down
- [ ] The owner has said go, in writing, here

