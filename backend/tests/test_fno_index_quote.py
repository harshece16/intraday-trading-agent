"""#189: a paper option is repriced from its underlying's price (#154), read
with data_provider.get_ltp(underlying). For an index underlying that asked
Kite for "NSE:NIFTY" and yfinance for "NIFTY.NS", and neither is an
instrument: Kite's quote key for the index is "NSE:NIFTY 50" ("NSE:NIFTY
BANK" for BANKNIFTY), yfinance's ticker "^NSEI" ("^NSEBANK"). Kite leaves an
unknown key out of its answer, so the lookup failed and a paper index option
never repriced: no stop, no target, squared off at the entry premium."""
from datetime import datetime, timedelta

import pandas as pd
import pytest

import config
import data_provider
import kite_broker
import options_pricing
import trading_engine
from state import AppState


class FakeKite:
    """kiteconnect's ltp(): an unknown instrument is simply missing from the answer."""

    def __init__(self, quotes):
        self.quotes, self.asked = quotes, []

    def ltp(self, keys):
        self.asked.extend(keys)
        return {k: {"last_price": self.quotes[k]} for k in keys if k in self.quotes}


QUOTES = {"NSE:NIFTY 50": 24500.0, "NSE:NIFTY BANK": 51000.0, "NSE:RELIANCE": 1400.0}


@pytest.fixture
def kite(monkeypatch):
    fake = FakeKite(QUOTES)
    monkeypatch.setattr(data_provider, "kite_data_active", lambda: True)
    monkeypatch.setattr(data_provider, "_get_kite", lambda: fake)
    monkeypatch.setattr(data_provider, "_get_intraday_candles_yfinance",
                        lambda *a, **k: pytest.fail("fell back to the delayed feed"))
    return fake


def test_kite_is_asked_for_an_index_under_its_quote_name(kite):
    assert data_provider.get_ltp("NIFTY") == 24500.0
    assert data_provider.get_ltp("BANKNIFTY") == 51000.0
    assert data_provider.get_ltp("RELIANCE") == 1400.0                   # a stock is unchanged
    assert kite.asked == ["NSE:NIFTY 50", "NSE:NIFTY BANK", "NSE:RELIANCE"]


def test_one_mapping_for_the_order_path_and_the_data_path():
    # kite_broker.get_index_spot (the PCR read) and data_provider.get_ltp use the same table
    for name in config.FNO["index_underlyings"]:
        assert data_provider.kite_quote_key(name) == kite_broker.INDEX_QUOTE_SYMBOLS[name]
    assert data_provider.kite_quote_key("M&M") == "NSE:M&M"


def test_the_delayed_feed_is_asked_for_the_yahoo_index_ticker(monkeypatch):
    asked = []
    bar = pd.DataFrame({"Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [24480.0], "Volume": [0]},
                       index=pd.DatetimeIndex([pd.Timestamp("2026-09-30 10:00", tz="Asia/Kolkata")]))
    monkeypatch.setattr(data_provider, "kite_data_active", lambda: False)
    monkeypatch.setattr(data_provider, "yf_download", lambda **kw: asked.append(kw["tickers"]) or bar)
    assert data_provider.get_ltp("NIFTY") == 24480.0
    data_provider.get_ltp("BANKNIFTY")
    data_provider.get_ltp("RELIANCE")
    assert asked == ["^NSEI", "^NSEBANK", "RELIANCE.NS"]


def test_a_paper_nifty_option_reprices_from_the_index(kite):
    e = trading_engine.TradingEngine(AppState(watchlist=[], paper_mode=True))
    days, r = 20, config.FNO["risk_free_rate_pct"] / 100
    entry = round(options_pricing.price(24400.0, 24500.0, days / 365, 0.20, r, True), 2)
    e.state.fno_positions["NIFTY"] = {
        "tradingsymbol": "NIFTY26OCT24500CE", "underlying": "NIFTY", "is_call": True, "strike": 24500.0,
        "expiry": (datetime.now(trading_engine.IST).date() + timedelta(days=days)).isoformat(),
        "entry_iv": 0.20, "lots": 1, "lot_size": 65, "entry_premium": entry, "ltp": entry,
        "stop_premium": round(entry * 0.6, 2), "target_premium": round(entry * 1.8, 2), "position_id": "P-N",
    }
    assert e._check_fno_stop_take("NIFTY") is False
    now = e.state.fno_positions["NIFTY"]["ltp"]
    assert now == round(options_pricing.price(24500.0, 24500.0, days / 365, 0.20, r, True), 2) != entry
    assert not [a for a in e.state.activity if "can't reprice" in a["message"]]
