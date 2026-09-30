"""3h's formulas and date alignment, checked before L35 runs."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from research import breadth_intermarket as bi

BHAV = """SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER
AAA, EQ, 24-Sep-2026, 100, 0, 0, 0, 0, 101, 0, 500, 0, 0, 0, 0
BBB, EQ, 24-Sep-2026, 100, 0, 0, 0, 0, 99, 0, 200, 0, 0, 0, 0
CCC, EQ, 24-Sep-2026, 100, 0, 0, 0, 0, 98, 0, 300, 0, 0, 0, 0
DDD, EQ, 24-Sep-2026, 100, 0, 0, 0, 0, 100, 0, 50, 0, 0, 0, 0
GSX, GS, 24-Sep-2026, 100, 0, 0, 0, 0, 120, 0, 9, 0, 0, 0, 0
"""


def test_breadth_counts_eq_series_only():
    b = bi.breadth_from_bhav(BHAV)
    assert (b["adv"], b["dec"], b["unch"], b["n_eq"]) == (1, 2, 1, 4)
    assert (b["up_vol"], b["down_vol"]) == (500, 500)


def test_trin_is_arms_index():
    assert abs(bi.trin(1, 2, 500, 500) - 0.5) < 1e-12
    assert bi.trin(5, 0, 1, 1) is None


def test_mcclellan_is_ema19_minus_ema39():
    xs = [10, -5, 3, 8, -2] * 20
    m = bi.mcclellan(xs)
    assert abs(m[0]) < 1e-12                                   # both seeded with the first value
    e19, e39 = bi.ema(xs, 19), bi.ema(xs, 39)
    assert all(abs(a - (b - c)) < 1e-9 for a, b, c in zip(m, e19, e39))
    assert abs(bi.ema([0, 10], 19)[1] - 1.0) < 1e-12           # alpha = 2/20


def test_predictors_only_read_dates_strictly_before_the_session():
    dates, vals = ["2025-03-03", "2025-03-04", "2025-03-05"], [100.0, 110.0, 99.0]
    assert abs(bi.yf_predictor("P5_sp500_ret_pct", dates, vals, "2025-03-05") - 10.0) < 1e-9
    assert abs(bi.yf_predictor("P5_sp500_ret_pct", dates, vals, "2025-03-06") - (-10.0)) < 1e-9
    assert bi.yf_predictor("P5_sp500_ret_pct", dates, vals, "2025-03-04") is None
    assert abs(bi.yf_predictor("P8_us10y_chg_bp", ["a", "b"], [3.70, 3.75], "c") - 5.0) < 1e-9


def test_intraday_target_uses_0920_and_1510_closes():
    def bars(o, c):
        return [{"time": "2025-03-05T09:15:00", "close": o}, {"time": "2025-03-05T12:00:00", "close": 1.0},
                {"time": "2025-03-05T15:05:00", "close": c}, {"time": "2025-03-05T15:25:00", "close": 9.0}]
    data = {f"S{i}": bars(100.0, 101.0) for i in range(50)}
    assert abs(bi.intraday_target(data, "2025-03-05") - 100.0) < 1e-9
    assert bi.intraday_target({"S": bars(100.0, 101.0)}, "2025-03-05") is None


def test_bh_and_tradability():
    assert bi.bh({"a": 0.001, "b": 0.02, "c": 0.5}) == {"a", "b"}
    base = {"bottom": {"mean_bp": -3.0}, "top": {"mean_bp": 20.0}}
    assert bi.tradable({**base, "spread_bp": 23.0})
    assert not bi.tradable({"spread_bp": 10.0, "bottom": {"mean_bp": -3.0}, "top": {"mean_bp": 7.0}})
    assert bi.tradable({"spread_bp": -30.0, "bottom": {"mean_bp": 5.0}, "top": {"mean_bp": -25.0}})
