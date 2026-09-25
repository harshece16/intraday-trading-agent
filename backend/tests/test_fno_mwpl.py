"""NSE's F&O ban list (Market Wide Position Limit): the parser, the
fail-closed block rule, and that the engine consults it before any F&O
order (NISM Series VIII)."""
import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import fno_risk
import nse_feed

SAMPLE = "Securities in Ban For Trade Date 25-SEP-2026:\n1,KAYNES\n2,LICHSGFIN\n3,MANAPPURAM\n4,SAIL\n"


def test_parse_real_format():
    b = nse_feed.parse_fno_ban(SAMPLE)
    assert b == {"trade_date": "2026-09-25", "symbols": {"KAYNES", "LICHSGFIN", "MANAPPURAM", "SAIL"}}


def test_parse_clear_day_is_empty_not_unknown():
    assert nse_feed.parse_fno_ban("Securities in Ban For Trade Date 26-SEP-2026:\n") == \
        {"trade_date": "2026-09-26", "symbols": set()}


def test_parse_unrecognised_format_is_unknown():
    assert nse_feed.parse_fno_ban("<html>Access Denied</html>") is None
    assert nse_feed.parse_fno_ban("") is None
    assert nse_feed.parse_fno_ban("Securities in Ban For Trade Date garbage:\n1,SAIL") is None


def test_block_rule():
    ban = nse_feed.parse_fno_ban(SAMPLE)
    today = "2026-09-25"
    assert "ban period" in fno_risk.mwpl_block_reason("SAIL", ban, today)
    assert fno_risk.mwpl_block_reason("RELIANCE", ban, today) is None
    assert fno_risk.mwpl_block_reason("sail", ban, today)          # case-insensitive


def test_fails_closed_when_unknown_or_stale():
    assert "unknown" in fno_risk.mwpl_block_reason("RELIANCE", None, "2026-09-25")
    stale = nse_feed.parse_fno_ban(SAMPLE)
    assert "unknown" in fno_risk.mwpl_block_reason("RELIANCE", stale, "2026-09-28")


def test_index_options_are_exempt_even_when_status_unknown():
    assert fno_risk.mwpl_block_reason("NIFTY", None, "2026-09-25", ["NIFTY", "BANKNIFTY"]) is None


def test_engine_checks_the_ban_before_pricing_or_ordering():
    """The ban check sits in _try_enter_fno before the contract lookup, so
    no F&O order path can skip it."""
    src = (Path(__file__).parent.parent / "trading_engine.py").read_text()
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "_try_enter_fno")
    body = ast.get_source_segment(src, fn)
    assert "fno_risk.mwpl_block_reason(" in body and "nse_feed.fno_ban_list()" in body
    assert body.index("mwpl_block_reason(") < body.index("find_contract(")
