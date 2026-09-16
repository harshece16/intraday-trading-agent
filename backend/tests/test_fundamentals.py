"""
fundamentals.py: real-data scoring logic and caching, without ever hitting
the network — yfinance.Ticker is patched with real-shaped values (the exact
numbers verified live against TCS.NS: returnOnEquity/operatingMargins as
plain 0-1 ratios, debtToEquity in Yahoo's percent-scaled convention).
"""
from unittest.mock import MagicMock, patch

import fundamentals


def _mock_ticker(info):
    m = MagicMock()
    m.get_info.return_value = info
    return m


def test_strong_fundamentals_score_like_real_tcs():
    # Real TCS.NS values fetched live from Yahoo Finance during development.
    info = {"returnOnEquity": 0.47743, "operatingMargins": 0.23963, "debtToEquity": 10.211,
            "trailingPegRatio": 2.8759}
    with patch("yfinance.Ticker", return_value=_mock_ticker(info)):
        fundamentals._cache.clear()
        result = fundamentals.get_fundamentals("TCS")
    assert result["label"] == "Strong"
    assert result["score"] == 3.0  # +1 ROE, +1 margin, +1 debt/equity, 0 PEG (mixed zone)
    by_key = {m["key"]: m for m in result["metrics"]}
    assert by_key["debt_to_equity"]["value"] == 10.211 / 100
    assert by_key["peg_ratio"]["points"] == 0.0


def test_weak_fundamentals_score():
    info = {"returnOnEquity": 0.03, "operatingMargins": 0.02, "debtToEquity": 350.0, "pegRatio": 5.0}
    with patch("yfinance.Ticker", return_value=_mock_ticker(info)):
        fundamentals._cache.clear()
        result = fundamentals.get_fundamentals("WEAKCO")
    assert result["label"] == "Weak"
    assert result["score"] == -4.0


def test_missing_data_never_guessed():
    with patch("yfinance.Ticker", return_value=_mock_ticker({})):
        fundamentals._cache.clear()
        result = fundamentals.get_fundamentals("NODATA")
    assert result["score"] is None
    assert result["label"] == "Not enough data"
    assert result["metrics"] == []


def test_negative_peg_skipped_not_scored():
    # A negative PEG (negative earnings growth) isn't a valuation signal in
    # the usual sense — skipped rather than scored as "cheap".
    info = {"returnOnEquity": 0.20, "trailingPegRatio": -1.5}
    with patch("yfinance.Ticker", return_value=_mock_ticker(info)):
        fundamentals._cache.clear()
        result = fundamentals.get_fundamentals("NEGPEG")
    keys = {m["key"] for m in result["metrics"]}
    assert "peg_ratio" not in keys
    assert "roe" in keys


def test_yahoo_failure_returns_not_enough_data_not_a_crash():
    with patch("yfinance.Ticker", side_effect=RuntimeError("rate limited")):
        fundamentals._cache.clear()
        result = fundamentals.get_fundamentals("FAILCO")
    assert result["score"] is None
    assert result["label"] == "Not enough data"


def test_result_is_cached():
    info = {"returnOnEquity": 0.20}
    with patch("yfinance.Ticker", return_value=_mock_ticker(info)) as ticker:
        fundamentals._cache.clear()
        fundamentals.get_fundamentals("CACHECO")
        fundamentals.get_fundamentals("CACHECO")
    ticker.assert_called_once()
