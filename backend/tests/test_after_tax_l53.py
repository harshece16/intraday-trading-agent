"""Research look L53 (docs/research/prereg-after-tax-l53.md): the Indian tax engine on
hand-worked cases, the book's lots inside momentum_width.simulate, the funds' harvest,
and the guard that keeps every 2026 row out."""
import datetime
import json
import math
import os
import sys

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(BACKEND, "research"))

import after_tax_l53 as l53  # noqa: E402
import india_tax as tx  # noqa: E402
import momentum_3i as m3  # noqa: E402
import momentum_width as mw  # noqa: E402

FWD, HIST = tx.ForwardRules(), tx.HistoricalRules()


def _item(gain, term, sale="2021-06-01", acq="2020-01-01", **kw):
    it = {"gain": float(gain), "term": term, "sale": sale, "acq": acq}
    it.update(kw)
    return it


def _tax(fy, items, dividends=0.0, carry=(), rules=FWD):
    return tx.compute_fy_tax(fy, items, dividends, list(carry), rules)


# --- dates: the financial year and the 12-month line ----------------------------------------

def test_financial_year():
    assert tx.fy_of("2015-04-01") == 2015
    assert tx.fy_of("2016-03-31") == 2015
    assert tx.fy_of("2016-01-15") == 2015


@pytest.mark.parametrize("acq,sale,long_term", [
    ("2020-03-02", "2021-03-02", False),     # on the anniversary: not more than 12 months
    ("2020-03-02", "2021-03-03", True),      # the day after
    ("2020-02-29", "2021-02-28", False),     # a leap day reaches its anniversary on 28 February
    ("2020-02-29", "2021-03-01", True),
    ("2020-01-31", "2021-01-31", False),
    ("2020-01-31", "2021-02-01", True),
    ("2020-06-01", "2020-12-01", False),
])
def test_twelve_month_boundary(acq, sale, long_term):
    assert tx.is_long_term(acq, sale) is long_term


# --- FIFO lots ---------------------------------------------------------------------------------

def test_fifo_sells_the_oldest_lot_first_and_splits_a_lot_pro_rata():
    lots = tx.Lots()
    lots.add("X", 10, 1000.0, "2020-01-01")
    lots.add("X", 10, 2000.0, "2020-06-01")
    items = lots.sell("X", 15, 3000.0, "2021-03-01")          # 200 a unit
    assert [(it["units"], it["cost"], it["gain"], it["term"]) for it in items] == [
        (10, 1000.0, 1000.0, "lt"), (5, 1000.0, 0.0, "st")]
    assert lots.by_name["X"][0] == [5, 1000.0, "2020-06-01"]
    with pytest.raises(ValueError):
        lots.sell("X", 6, 100.0, "2021-03-02")


def test_preview_sell_changes_nothing():
    lots = tx.Lots()
    lots.add("X", 10, 1000.0, "2020-01-01")
    a = lots.preview_sell("X", 10, 1500.0, "2020-06-01")
    assert a[0]["gain"] == 500.0 and lots.units("X") == 10


def test_a_dividend_or_bonus_turns_part_of_each_lot_into_a_new_lot():
    lots = tx.Lots()
    lots.add("X", 100, 10000.0, "2020-01-01")
    moved = lots.split("X", 0.98, 200.0, "2020-06-01")        # a dividend of 2% of the price, reinvested
    assert moved == pytest.approx(2.0)
    assert lots.by_name["X"][0][:2] == [pytest.approx(98.0), 10000.0]
    assert lots.by_name["X"][1] == [pytest.approx(2.0), 200.0, "2020-06-01"]
    items = lots.sell("X", 100, 15000.0, "2021-03-01")
    assert [(round(it["gain"], 6), it["term"]) for it in items] == [(4700.0, "lt"), (100.0, "st")]
    lots.add("Y", 10, 1000.0, "2020-01-01")
    lots.split("Y", 0.5, 0.0, "2020-02-01")                   # bonus 1:1: half the (adjusted) units at nil cost, dated the allotment
    assert lots.units("Y") == pytest.approx(10.0)
    items = lots.sell("Y", 10, 1000.0, "2021-01-15")
    assert [(it["gain"], it["term"]) for it in items] == [(-500.0, "lt"), (500.0, "st")]


# --- one financial year: set-off, exemption, carry-forward, cess --------------------------------

def test_short_term_loss_goes_to_short_term_gains_first_then_long_term():
    tax, d, carry = _tax(2021, [_item(100e3, "st"), _item(200e3, "lt"), _item(-50e3, "st"), _item(-30e3, "lt")])
    # ST 100k - 50k = 50k at 20%; LT 200k - 30k = 170k, less the 1.25 lakh exemption = 45k at 12.5%
    assert tax == pytest.approx((50e3 * 0.20 + 45e3 * 0.125) * 1.04)
    assert d["lt_after_setoff"] == pytest.approx(170e3) and carry == []
    tax, d, carry = _tax(2021, [_item(100e3, "st"), _item(200e3, "lt"), _item(-150e3, "st"), _item(-30e3, "lt")])
    assert d["lt_after_setoff"] == pytest.approx(120e3) and tax == 0.0 and carry == []


def test_a_long_term_loss_cannot_touch_a_short_term_gain():
    tax, d, carry = _tax(2021, [_item(100e3, "st"), _item(-80e3, "lt")])
    assert tax == pytest.approx(100e3 * 0.20 * 1.04)
    assert carry == [{"fy": 2021, "term": "lt", "amount": pytest.approx(80e3)}]


def test_brought_forward_losses_are_used_even_inside_the_exemption():
    tax, d, carry = _tax(2020, [_item(100e3, "lt")], carry=[{"fy": 2019, "term": "st", "amount": 50e3}])
    assert tax == 0.0 and carry == [] and d["brought_forward_used"] == pytest.approx(50e3)
    assert d["lt_after_setoff"] == pytest.approx(50e3)


def test_a_brought_forward_long_term_loss_only_meets_long_term_gains():
    tax, d, carry = _tax(2020, [_item(100e3, "st"), _item(150e3, "lt")],
                         carry=[{"fy": 2019, "term": "lt", "amount": 200e3}])
    assert tax == pytest.approx(100e3 * 0.20 * 1.04)
    assert carry == [{"fy": 2019, "term": "lt", "amount": pytest.approx(50e3)}]


def test_losses_carry_for_eight_years_then_lapse():
    loss = [{"fy": 2010, "term": "st", "amount": 10e3}]
    tax, d, carry = _tax(2018, [_item(10e3, "st", sale="2018-06-01")], carry=loss)
    assert tax == 0.0 and d["lapsed"] == 0.0
    tax, d, carry = _tax(2019, [_item(10e3, "st", sale="2019-06-01")], carry=loss)
    assert tax == pytest.approx(10e3 * 0.20 * 1.04) and d["lapsed"] == pytest.approx(10e3) and carry == []


def test_carried_losses_are_used_oldest_first():
    carry = [{"fy": 2015, "term": "st", "amount": 30e3}, {"fy": 2012, "term": "st", "amount": 30e3}]
    _, _, left = _tax(2016, [_item(40e3, "st", sale="2016-06-01")], carry=carry)
    assert left == [{"fy": 2015, "term": "st", "amount": pytest.approx(20e3)}]


def test_the_ledger_settles_a_year_and_carries_its_losses():
    led = tx.TaxLedger(FWD)
    led.add_item(2020, _item(-40e3, "st", sale="2020-06-01"))
    assert led.settle(2020) == 0.0
    led.add_item(2021, _item(100e3, "st", sale="2021-06-01"))
    assert led.preview(2021)[0] == pytest.approx(60e3 * 0.2 * 1.04)
    assert led.carry == [{"fy": 2020, "term": "st", "amount": pytest.approx(40e3)}]   # preview changed nothing
    assert led.settle(2021) == pytest.approx(60e3 * 0.2 * 1.04) and led.carry == []


def test_dividends_at_the_slab_with_cess():
    assert _tax(2012, [], dividends=10e3)[0] == pytest.approx(3120.0)
    assert _tax(2019, [], dividends=10e3, rules=HIST)[0] == 0.0          # DDT regime
    assert _tax(2020, [], dividends=10e3, rules=HIST)[0] == pytest.approx(3120.0)


# --- the historical regime (information only) ------------------------------------------------

def test_before_april_2018_long_term_is_exempt_and_its_losses_vanish():
    tax, d, carry = _tax(2016, [_item(500e3, "lt", sale="2016-06-01"), _item(100e3, "st", sale="2016-06-01"),
                                _item(-70e3, "lt", sale="2016-07-01")], rules=HIST)
    assert tax == pytest.approx(100e3 * 0.15 * 1.03) and carry == []


def test_2018_to_2024_ten_percent_above_one_lakh():
    tax, _, _ = _tax(2019, [_item(150e3, "lt", sale="2020-03-01", acq="2019-01-01")], rules=HIST)
    assert tax == pytest.approx(50e3 * 0.10 * 1.04)


def test_2024_25_rates_change_on_23_july_and_losses_go_to_the_higher_rate():
    items = [_item(100e3, "st", sale="2024-07-01"), _item(100e3, "st", sale="2024-08-01"),
             _item(-100e3, "st", sale="2024-09-01")]
    assert _tax(2024, items, rules=HIST)[0] == pytest.approx(100e3 * 0.15 * 1.04)
    items = [_item(100e3, "lt", sale="2024-06-01"), _item(100e3, "lt", sale="2024-09-01")]
    # the 1.25 lakh exemption goes to the 12.5% gains first: 75k left at 10%
    assert _tax(2024, items, rules=HIST)[0] == pytest.approx(75e3 * 0.10 * 1.04)


@pytest.mark.parametrize("cost,fmv,sale,expected", [
    (100.0, 200.0, 150.0, 0.0),       # the sale is between cost and the 31 Jan 2018 value
    (100.0, 200.0, 250.0, 50.0),      # the 31 Jan 2018 value becomes the cost
    (100.0, 50.0, 150.0, 50.0),       # cost above the value: the actual cost stands
    (100.0, 200.0, 80.0, -20.0),      # grandfathering creates no loss and hides none
])
def test_grandfathering(cost, fmv, sale, expected):
    lots = tx.Lots()
    lots.add("X", 1, cost, "2017-06-01")
    it = lots.sell("X", 1, sale, "2018-06-15", fmv_per_unit=fmv)[0]
    assert it["gain_gf"] == pytest.approx(expected) and it["gain"] == pytest.approx(sale - cost)
    tax, d, _ = _tax(2018, [it], rules=HIST)
    assert d["lt_after_setoff"] == pytest.approx(max(expected, 0.0))
    assert _tax(2018, [it], rules=FWD)[1]["lt_after_setoff"] == pytest.approx(max(sale - cost, 0.0))


# --- the book: TaxBook inside momentum_width.simulate -------------------------------------------

def _sessions(start="2020-01-01", n=700):
    d, out = datetime.date.fromisoformat(start), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out


def _panel(n_stocks=40, n=700):
    """Prices whose leaders rotate, so the book trades (as test_momentum_width)."""
    sessions, chains = _sessions(n=n), {}
    for k in range(n_stocks):
        px, closes = 100.0, []
        for i in range(n):
            px *= 1 + 0.002 * math.sin(2 * math.pi * (i / 180.0 + k / n_stocks)) \
                + 0.01 * (((i * 7 + k * 13) % 11) - 5) / 5
            closes.append(px)
        chains["S%02d" % k] = {"idx": list(range(n)), "close": closes[:], "raw": closes[:], "open": closes[:],
                               "val": [1e8 + k * 1e6] * n, "isins": set(), "high": [x * 1.01 for x in closes],
                               "low": [x * 0.99 for x in closes], "prev": [closes[0]] + closes[:-1],
                               "ser": [0] * n}
    return sessions, chains


def _held_event(sessions, chains, unis, kind, factor):
    """An event on a name the book holds, on a session inside its holding."""
    _, _, _, holdings = mw.simulate(sessions, chains, unis, mw.PARTS["A"], 1e6, m3.SELECTION_START)
    h = holdings[len(holdings) // 2]
    name = h["holdings"][0]
    month_end = [i for m, i in m3.month_ends(sessions) if m == h["month"]][0]
    k = month_end + 5                                         # a few sessions after the fill
    return (name, k, kind, factor, sessions[k], "synthetic")


def test_with_tax_off_the_replay_is_trial_126s_simulator_and_its_lots_add_up():
    sessions, chains = _panel()
    unis = mw.universes(sessions, chains)
    ref, _, _, _ = mw.simulate(sessions, chains, unis, mw.PARTS["A"], 1e6, m3.SELECTION_START)
    events = [_held_event(sessions, chains, unis, "dividend", 0.97),
              _held_event(sessions, chains, unis, "bonus", 0.5)]
    panel = (sessions, chains, {}, events)
    ser, book, _, _ = l53.run_book(panel, unis, 1e6, None)
    assert [s[2] for s in ser] == [s[2] for s in ref]          # bit for bit
    assert book.lot_dev < 1e-9 and len(book.marks) == len(ser)
    assert {e["kind"] for e in book.event_log} == {"dividend", "bonus"}
    last = book.marks[-1]
    rhs = book.realised_total + last["liquidation_gain"] + book.dividends_total - book.stt_paid - last["liquidation_stt"]
    assert last["liquidation_pre_tax"] - 1e6 == pytest.approx(rhs, abs=1e-4)
    assert book.paid == {} and book.prorata == []


def test_with_tax_on_the_year_is_paid_at_the_first_april_fill_and_trades_keep_their_names():
    sessions, chains = _panel()
    unis = mw.universes(sessions, chains)
    panel = (sessions, chains, {}, [])
    off, book_off, _, h_off = l53.run_book(panel, unis, 1e6, None)
    on, book, _, h_on = l53.run_book(panel, unis, 1e6, FWD)
    assert h_on == h_off                                        # the same names, month by month
    assert list(book.paid) == sorted(book.paid) and len(book.paid) >= 1
    april = [m for m in book.marks if m["date"][5:7] == "04"]
    assert april and all(tx.fy_of(m["date"]) - 1 in book.paid for m in april)
    total_tax = sum(book.paid.values())
    assert on[-1][2] < off[-1][2] or total_tax == 0
    assert all(m["liquidation_after_tax"] <= m["liquidation_pre_tax"] + 1e-6 for m in book.marks)


def test_a_tax_bill_larger_than_cash_is_paid_by_a_pro_rata_sale():
    sessions, chains = _panel()
    ctx = l53.Ctx(sessions, chains, {}, FWD, 0.0005)
    book = l53.TaxBook(1e6, True, ctx=ctx)
    book.work(chains, 300, sessions, "buy")                    # sets the session and the open year
    for n in ("S01", "S02"):
        book._bought(n, chains[n]["close"][300], 400000.0, 0.0005)
    book.open_fy = tx.fy_of(sessions[300])
    book.ledger.add_item(book.open_fy, _item(2e6, "st", sale=sessions[300]))
    tax_due = book.ledger.preview(book.open_fy)[0]
    cash_before = book.cash
    s = next(i for i in range(301, 700) if tx.fy_of(sessions[i]) > book.open_fy)
    units_before = {n: book.pos[n] for n in book.pos}
    book.work(chains, s, sessions, "sell")
    assert book.paid[tx.fy_of(sessions[300])] == pytest.approx(tax_due)
    assert book.cash == pytest.approx(0.0, abs=1e-6)
    p = book.prorata[0]
    assert p["shortfall"] == pytest.approx(tax_due - cash_before)
    for n in units_before:
        assert book.pos[n] == pytest.approx(units_before[n] * (1 - p["fraction_sold"]))
        assert book.lots.units(n) == pytest.approx(book.pos[n])
    assert tx.fy_of(sessions[s]) in book.ledger.items          # the sale's gains fall in the new year


# --- the funds -----------------------------------------------------------------------------------

def _dates(first="2015-03-02", n=60):
    out = []
    d = datetime.date.fromisoformat(first)
    for i in range(n):
        out.append(tx.add_months(d, i).isoformat())
    return out


def _growing(rate=0.01, first="2015-03-02"):
    d0 = datetime.date.fromisoformat(first)

    def nav(d):
        return 100.0 * (1 + rate) ** ((datetime.date.fromisoformat(d) - d0).days / 30.4375)
    return nav


def test_a_fund_with_tax_off_is_its_nav_less_the_redemption_stt():
    dates = _dates()
    nav = _growing()
    acct = l53.run_fund(nav, dates, 1e6, None)
    for m in acct.marks:
        assert m["liquidation_pre_tax"] == pytest.approx(1e6 * nav(m["date"]) / nav(dates[0]) * (1 - l53.FUND_STT_REDEEM))


def test_the_harvest_realises_the_exemption_exactly_and_the_fund_pays_no_tax():
    dates = _dates(n=61)
    acct = l53.run_fund(_growing(0.015), dates, 1e6, FWD)
    assert len(acct.harvests) >= 3
    for h in acct.harvests:
        assert h["lt_after_setoff"] == pytest.approx(125000.0, abs=0.01)
    assert sum(acct.paid.values()) == 0.0
    assert acct.marks[-1]["liability"] > 0                      # the deferred tax is counted at the end
    no = l53.run_fund(_growing(0.015), dates, 1e6, None)
    assert acct.marks[-1]["liquidation_after_tax"] < no.marks[-1]["liquidation_pre_tax"]


def test_a_losing_old_lot_is_sold_in_the_harvest_and_its_loss_carried():
    dates = _dates(n=40)
    d0 = datetime.date.fromisoformat(dates[0])

    def nav(d):
        t = (datetime.date.fromisoformat(d) - d0).days
        return 100.0 if t < 400 else 60.0                       # a 40% fall after 13 months
    acct = l53.run_fund(nav, dates, 1e6, FWD)
    assert acct.harvests and acct.ledger.carry and acct.ledger.carry[0]["term"] == "lt"


def test_a_harvest_waits_for_the_first_long_term_day_in_the_same_year():
    """Amendment 1: bought on 2010-03-02, the lot is not long-term on the 2011-03-01 point;
    the harvest runs on 2011-03-03, the first day after the anniversary."""
    dates = ["2010-03-02", "2010-04-01", "2011-03-01", "2011-04-01"]
    d, cal = datetime.date(2010, 3, 1), []
    while d <= datetime.date(2011, 4, 30):
        if d.weekday() < 5:
            cal.append(d.isoformat())
        d += datetime.timedelta(days=1)
    nav = _growing(0.03, first="2010-03-02")
    acct = l53.run_fund(nav, dates, 1e6, FWD, cal)
    assert [h["date"] for h in acct.harvests] == ["2011-03-03"]
    assert acct.harvests[0]["lt_after_setoff"] == pytest.approx(125000.0, abs=0.01)
    assert len(acct.marks) == len(dates) and 2010 in acct.ledger.items
    assert l53.run_fund(nav, dates, 1e6, FWD).harvests == []                  # without the day rule, lost
    late = ["2010-03-31", "2010-04-30", "2011-03-01", "2011-04-01"]         # anniversary after 31 March: none
    assert l53.run_fund(_growing(0.03, first="2010-03-31"), late, 1e6, FWD, cal).harvests == []


def test_stamp_duty_only_from_july_2020():
    a = l53.FundAccount(lambda d: 10.0, None, 1e6)
    a._buy("2020-06-30", 1000.0)
    a._buy("2020-07-01", 1000.0)
    assert [lot[0] for lot in a.lots.by_name["F"]] == [pytest.approx(100.0), pytest.approx(99.995)]


# --- statistics ----------------------------------------------------------------------------------

def test_the_bootstrap_of_identical_series_is_zero_and_of_constant_series_exact():
    r = [0.01 * ((i % 7) - 3) for i in range(189)]
    assert max(abs(x) for x in l53.bootstrap_cagr_difference(r, r, n=200)) == 0.0
    d = l53.bootstrap_cagr_difference([0.01] * 189, [0.0] * 189, n=50)
    assert d.min() == pytest.approx(1.01 ** 12 - 1) and d.max() == pytest.approx(1.01 ** 12 - 1)
    a = l53.bootstrap_cagr_difference(r, [0.0] * 189, n=100)
    b = l53.bootstrap_cagr_difference(r, [0.0] * 189, n=100)
    assert (a == b).all()                                       # seeded


def test_the_reading_rule():
    up = [100.0 * 1.02 ** i for i in range(190)]
    flat = [100.0] * 190
    wiggle = [100.0 * (1 + 0.05 * math.sin(i)) for i in range(190)]
    assert l53.compare(up, flat)["verdict"] == "BEATS"
    assert l53.compare(flat, up)["verdict"] == "LOSES"
    assert l53.compare(wiggle, flat)["verdict"] == "TIES"
    c = l53.compare(up, flat)
    assert c["halves"]["half1"]["months"] == 94 and c["halves"]["half2"]["months"] == 95


def test_turnover_counts_names_and_the_long_term_share():
    sessions = _sessions(start="2015-01-01", n=1200)
    names = ["N%02d" % i for i in range(40)]
    chains = {n: {"idx": [len(sessions) - 1]} for n in names}
    mes = m3.month_ends(sessions)
    decs = []
    for j, (month, idx) in enumerate(mes[:-1]):
        order = names if j % 2 == 0 else names[5:20] + names[:5] + names[20:]   # five holdings slip to ranks 16-20
        decs.append({"month": month, "idx": idx, "f": idx + 1, "order": order,
                     "rank": {n: i + 1 for i, n in enumerate(order)}, "uset": set(names)})
    closed, open_ages = l53.turnover_run(decs, sessions, chains, 30, 1, 0)
    assert closed == [] and len(open_ages) == 15                # nothing leaves the band
    closed, _ = l53.turnover_run(decs, sessions, chains, 15, 1, 0)
    stats = l53.holding_stats(closed, [], 4.0)
    assert stats["sells"] == len(closed) > 0 and stats["share_long_term"] == 0.0


# --- 2026 stays out ------------------------------------------------------------------------------

def test_prepare_drops_2026_rows_and_the_loader_refuses_them(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    (raw / "tri").mkdir(parents=True)
    (raw / "nav").mkdir()
    (raw / "iima").mkdir()
    tri = [{"Date": "02 Jan 2026", "TotalReturnsIndex": "999"}, {"Date": "31 Dec 2025", "TotalReturnsIndex": "1,001.5"},
           {"Date": "01 Jan 2003", "TotalReturnsIndex": "1000"}]
    for rel, _ in l53.RAW.values():
        p = raw / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".json") and "nav" in rel:
            p.write_text(json.dumps({"meta": {}, "data": [{"date": "05-01-2026", "nav": "9"},
                                                          {"date": "31-12-2025", "nav": "20.1"}]}))
        elif rel.endswith(".json"):
            p.write_text(json.dumps(tri))
        else:
            p.write_text("Date,SMB,HML,WML,MF,RF\n2025-12,1,2,3,4,0.5\n2026-01,9,9,9,9,9\n")
    monkeypatch.setattr(l53, "DATA_DIR", str(tmp_path / "out"))
    monkeypatch.setattr(l53, "MANIFEST", str(tmp_path / "out" / "manifest.json"))
    files = l53.prepare_data(str(raw))
    assert files["nifty100_tri.csv"]["rows_dropped_on_or_after_2026_01_01"] == 1
    assert files["iima_four_factors_monthly.csv"]["rows_dropped_on_or_after_2026_01_01"] == 1
    s = l53.load_series("nifty100_tri.csv")
    assert list(s.items()) == [("2003-01-01", 1000.0), ("2025-12-31", 1001.5)]
    assert list(l53.load_iima()) == ["2025-12"]
    with open(os.path.join(l53.DATA_DIR, "nifty100_tri.csv"), "a") as f:
        f.write("2026-01-02,999\n")
    with pytest.raises(SystemExit):
        l53.load_series("nifty100_tri.csv")


def test_the_constants_are_the_written_ones():
    assert (l53.TD_A, l53.TD_B) == (0.0025, 0.005)
    assert (l53.BOOT_N, l53.BOOT_BLOCK, l53.BOOT_SEED) == (10000, 12, 53)
    assert l53.CAPITALS == (1_000_000.0, 100_000.0) and l53.CUTOFF == "2026-01-01"
    assert (FWD.st_rate(2030, "x"), FWD.lt_rate(2030, "x"), FWD.lt_exemption(2030), FWD.cess(2030)) == \
        (0.20, 0.125, 125000.0, 0.04)
    assert m3.DP_PER_SELL == pytest.approx(15.34)               # GST included; no further GST
