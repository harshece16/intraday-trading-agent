# Shadow check of the scanner's live feed, 2026-09-29

Run between 13:53 and 14:15 IST with the market open, from the branch of PR #195, in a process of its own on a throwaway journal (`SAHAB_DB_PATH`). Nothing was written to the engine's journal and no order was placed. The results are summed up in README §101.

| File | What it measures |
| --- | --- |
| `check_1` | A live scan and a delayed scan from the same code, against Kite's quotes read before and after |
| `check_2` | Time spent in each part of a scan. The running engine's rows and a live scan's rows, each against a quote read right after |
| `check_3` | How far prices move in the seconds a scan takes, and how old the delayed feed's newest price is |
| `check_4` | The rows whose live price sits furthest from Kite's quotes |
| `check_5` | The same comparison after the fix for #196 |
| `check_6` | A scan and a tick's bar fetch at the same moment in one process: the spacing of requests to Kite |

Each script takes the output path as its first argument. `check_2` and `check_5` take the main backend folder as the second, to read the running engine over its API.

Two limits of these files. `check_1`'s `list_equal` compares two scanners that read the same fixed list from the same throwaway journal, so it says nothing. Its `delayed_price_off_by_bp` compares a scan with a quote read before it, not after; `check_3` is the fair measure.
