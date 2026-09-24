"""
research/nifty100_membership.py — the 3f stage-0b membership rebuild.

Each test is a layout or rule that broke the real rebuild once and was fixed
with a real release in hand; the synthetic texts below mirror those releases.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from research import nifty100_membership as nm

SYM = nm.SymbolMap()
SYM.symchange = {"ZOMATO": "ETERNAL", "LTI": "LTIM", "LTIM": "LTM"}


def ev(events, index=None):
    return sorted((e["index"], e["effective"], e["action"], e["symbol"]) for e in events if not index or e["index"] == index)


# ---- layouts --------------------------------------------------------------

def test_2010_layout_names_only_resolve_through_the_symbol_map():
    text = """PRESS RELEASE
The Index Maintenance Sub-Committee has decided to make the following changes in various indices
during its periodic review. These changes shall become effective from April 8, 2010.

(1)     S&P CNX Nifty Index
The following company is being excluded:
  Sr. No.     Company Name
  1           Titan Industries Ltd.

The following company is being included:
  Sr. No.     Company Name
  1           Sesa Goa Ltd.

(2)     CNX Nifty Junior Index
The following companies are being excluded:
  Sr. No.     Company Name
  1           Sesa Goa Ltd.
"""
    assert ev(nm.parse_release(text, "ind_prs24022010.txt", SYM)) == [
        ("N50", "2010-04-08", "EXCL", "TITAN"), ("N50", "2010-04-08", "INCL", "VEDL"),
        ("NN50", "2010-04-08", "EXCL", "VEDL"),
    ]


def test_2025_layout_with_symbols_and_scrips_wording_and_renames():
    text = """These changes shall become effective from March 28, 2025 (close of March 27, 2025).
a) Nifty 50

The following scrips are being excluded:

   Sr. No.   Company Name          Symbol
     1       Britannia Ltd.        BRITANNIA

The following scrips are being included:

   Sr. No.   Company Name          Symbol
     1       Zomato Ltd.           ZOMATO
b) Nifty 500
The following companies are being excluded:
   Sr. No.   Company Name          Symbol
     1       Akums Ltd.            AKUMS
"""
    out = ev(nm.parse_release(text, "ind_prs21022025.txt", SYM))
    assert out == [("N50", "2025-03-28", "EXCL", "BRITANNIA"), ("N50", "2025-03-28", "INCL", "ETERNAL")]


def test_a_wrapped_note_ending_in_the_index_name_is_not_a_heading():
    """The Feb 2025 release wraps a note onto a line that is exactly 'Nifty 50 index';
    treating it as a heading attributed the Next 50 tables to Nifty 50."""
    text = """These changes shall become effective from March 28, 2025.
a) Nifty 50

The following companies are being included:
   Sr. No.   Company Name          Symbol
     1       Jio Financial Ltd.    JIOFIN

Note: Adani Total Gas has been removed on account of its inclusion in
Nifty 50 index

d) Nifty Next 50

The following companies are being included:
   Sr. No.   Company Name          Symbol
     1       Hyundai Motor Ltd.    HYUNDAI
"""
    out = nm.parse_release(text, "ind_prs21022025.txt", SYM)
    assert ev(out, "N50") == [("N50", "2025-03-28", "INCL", "JIOFIN")]
    assert ev(out, "NN50") == [("NN50", "2025-03-28", "INCL", "HYUNDAI")]


def test_a_heading_after_a_page_break_still_ends_the_previous_block():
    text = "effective from September 30, 2025.\n1) Nifty 50\n\nThe following companies are being included:\n" \
           "   Sr. No.   Company Name   Symbol\n     1       Max Health Ltd.   MAXHEALTH\n" \
           "\x0c2) Nifty 500\n\nThe following companies are being included:\n" \
           "   Sr. No.   Company Name   Symbol\n     1       Some Small Ltd.   SMALL\n"
    assert ev(nm.parse_release(text, "ind_prs22082025.txt", SYM)) == [("N50", "2025-09-30", "INCL", "MAXHEALTH")]


def test_prose_layout_lists_indices_by_name():
    text = """These changes shall become effective from August 30, 2024 (close of August 29, 2024).
Tata Motors Ltd., 'A' Ordinary Shares - DVR (Symbol: TATAMTRDVR) shall be excluded from the following indices:
   Sr. No.     Index Name
      1      Nifty 100
      2      Nifty 200
      3      Nifty Auto

Consequently, the equity shares of Tata Motors Ltd. shall be adjusted.
"""
    assert ev(nm.parse_release(text, "ind_prs23082024_1.txt", SYM)) == [("N100", "2024-08-30", "EXCL", "TATAMTRDVR")]


def test_a_count_sentence_wrapped_onto_a_numbered_line_is_not_a_row():
    """Feb 2016: 'the Nifty 100 index shall have\n101 securities.' parsed as row 101 'securities.'"""
    text = """effective from April 1, 2016.
1) Nifty 100

The following companies are being included:
   Sr. No.   Company Name          Symbol
     1       Tata Motors Ltd. (DVR)   TATAMTRDVR

On account of inclusion of Tata Motors Ltd. (DVR), the Nifty 100 index shall have
101 securities.
"""
    assert ev(nm.parse_release(text, "ind_prs22022016_2.txt", SYM)) == [("N100", "2016-04-01", "INCL", "TATAMTRDVR")]


def test_corporate_adjustment_dummies_are_ignored():
    text = """In accordance with the index methodology, demerged entity ITC Hotels Ltd. (with a dummy Symbol
"DUMMYITC") shall be included at zero price in following indices effective from January 06, 2025.
   Sr. No.     Index Name
      1      Nifty 50
      2      Nifty 100
"""
    assert nm.parse_release(text, "ind_prs30122024.txt", SYM) == []


# ---- announcement rules --------------------------------------------------------

def mk(index, eff, action, sym, file):
    return {"index": index, "effective": eff, "action": action, "symbol": sym, "name": sym, "file": file, "layout": "table"}


def test_later_dated_release_wins_a_repeated_announcement():
    # Yes Bank: announced Feb 18 for Mar 27, brought forward by the Mar 16 release to Mar 19.
    events = [mk("N50", "2020-03-27", "EXCL", "YESBANK", "ind_prs18022020.txt"),
              mk("N50", "2020-03-19", "EXCL", "YESBANK", "ind_prs16032020.txt")]
    kept, log = nm.dedupe([dict(e, file="ind_prs16032020.txt") if e["effective"] == "2020-03-19" else e for e in events])
    assert [e["effective"] for e in kept] == ["2020-03-19"]
    assert any(x[0] in ("superseded", "voided") for x in log)


def test_alternating_actions_are_all_kept():
    events = [mk("NN50", "2015-05-29", "INCL", "MRF", "ind_prs29042015.txt"),
              mk("NN50", "2016-04-01", "EXCL", "MRF", "ind_prs22022016.txt"),
              mk("NN50", "2017-09-29", "INCL", "MRF", "ind_prs28082017.txt")]
    kept, _ = nm.dedupe(events)
    assert len(kept) == 3


def test_the_voided_february_2020_announcement_is_dropped():
    kept, log = nm.dedupe([mk("NN50", "2020-03-27", "INCL", "IDBI", "ind_prs18022020.txt")])
    assert kept == [] and log[0][0] == "voided"


# ---- the walk ------------------------------------------------------------------

def test_walk_reconstructs_and_a_missing_release_breaks_the_chain():
    cur = {f"S{i:02d}" for i in range(50)}
    events = [mk("N50", "2025-03-28", "INCL", "S00", "ind_prs21022025.txt"),
              mk("N50", "2025-03-28", "EXCL", "OLD1", "ind_prs21022025.txt"),
              mk("N50", "2024-09-30", "INCL", "S01", "ind_prs23082024.txt"),
              mk("N50", "2024-09-30", "EXCL", "OLD2", "ind_prs23082024.txt")]
    snaps, steps = nm.walk(events, "N50", cur, "2026-09-24")
    assert all(s["ok"] for s in steps) and len(snaps) == 3
    assert "OLD1" in nm.set_asof(snaps, "2025-03-27") and "OLD1" not in nm.set_asof(snaps, "2025-03-28")
    assert {"OLD1", "OLD2"} <= nm.set_asof(snaps, "2024-01-01")
    # drop the 2024 release: S01 is then "included" without being a member before -> inconsistent
    snaps, steps = nm.walk(events[:2] + [mk("N50", "2023-09-29", "INCL", "S01", "ind_prs17082023.txt")], "N50", cur, "2026-09-24")
    assert steps[-1]["ok"] is False and steps[-1]["bad_inc"] == []  # S01 still a member; the count is what breaks
    assert steps[-1]["n"] == 49


def test_the_dvr_counts_as_an_additional_security():
    cur = {f"S{i:02d}" for i in range(50)}
    events = [mk("N50", "2017-09-29", "EXCL", "TATAMTRDVR", "ind_prs28082017.txt")]
    _, steps = nm.walk(events, "N50", cur, "2026-09-24")
    assert steps[0]["n"] == 51 and steps[0]["ok"]


def test_overlay_and_monthly_union():
    events = [mk("N100", "2023-09-29", "INCL", "TATAMTRDVR", "ind_prs17082023.txt"),
              mk("N100", "2024-08-30", "EXCL", "TATAMTRDVR", "ind_prs23082024_1.txt")]
    n50 = [("2026-09-24", {"A"})]
    nn50 = [("2026-09-24", {"B"})]
    rows = nm.monthly_series(events, n50, nn50, "2023-08", "2024-09-30")
    by = {mo: mem for mo, _, mem in rows}
    assert by["2023-08"] == ["A", "B"] and by["2023-09"] == ["A", "B", "TATAMTRDVR"]
    assert by["2024-07"] == ["A", "B", "TATAMTRDVR"]
    assert by["2024-08"] == ["A", "B"] and by["2024-09"] == ["A", "B"]  # excluded Aug 30, before the Aug 31 signal date


def test_intervals_give_each_spell_with_its_source():
    inc = mk("N50", "2025-03-28", "INCL", "S00", "ind_prs21022025.txt")
    exc = mk("N50", "2025-03-28", "EXCL", "OLD1", "ind_prs21022025.txt")
    snaps, _ = nm.walk([inc, exc], "N50", {"S00", "X"}, "2026-09-24")
    rows = nm.intervals([inc, exc], snaps, [("2026-09-24", {"Y"})], "2026-09-24")
    assert rows == [("OLD1", "", "2025-03-27", "", "ind_prs21022025.txt"),
                    ("S00", "2025-03-28", "", "ind_prs21022025.txt", ""),
                    ("X", "", "", "", ""), ("Y", "", "", "", "")]
