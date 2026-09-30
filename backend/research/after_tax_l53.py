"""Research look L53 — what the momentum book (trial 126) is worth to an individual
after Indian costs and taxes, against the funds the owner could buy instead.

Pre-registered: docs/research/prereg-after-tax-l53.md (commit ec7cb12), before this
file was written. Every rule here is a transcription of it.

    1  trial 126's own trade list, replayed with FIFO tax lots (TaxBook, a subclass of
       momentum_width.Book inside momentum_width.simulate, called unchanged)
    2  three funds, taxed and harvested the same way (FundAccount): (a) NIFTY 100 TRI
       less 0.25 pp a year, (b) NIFTY200 Momentum 30 TRI less 0.5 pp, (c) the UTI
       Nifty200 Momentum 30 Index Fund's own NAV
    3  benchmark realism, 2020-09 to 2025-11, and the proposals for the band
    4  turnover diagnostics by name counts (no position valued, no return computed)
    5  correlation of the book's excess with IIMA's WML and HML

The tax engine is research/india_tax.py. Order, as the prereg fixes it:
--prepare-data (inputs cut before 2026) -> stage 0 -> committed and pushed ->
independent review -> ONE measurement pass.

From backend/, reading the main checkout's data read-only:
    SAHAB_RESEARCH_DATA=<main>/backend/data SAHAB_DB_PATH=<scratch>/l53.db \\
        nice -n 15 .venv/bin/python research/after_tax_l53.py --prepare-data --raw-dir <R1's research-r1>
    ... research/after_tax_l53.py --stage0
    ... research/after_tax_l53.py --measure --review-note "<who approved stage 0, when>"   # once

Measurement only: no strategy is selected and no trial is spent (the count stays at
202). Nothing on the live path imports this (tests/test_research_splits.py).
"""
import argparse
import bisect
import csv
import datetime
import hashlib
import io
import json
import math
import os
import platform
import random
import re
import statistics as st
import subprocess
import sys
import time
import zipfile
from collections import Counter, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
for _p in (BACKEND, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import india_tax as tx  # noqa: E402
import momentum_3i as m3  # noqa: E402
import momentum_width as mw  # noqa: E402
import nse_prices  # noqa: E402

# ---- the pre-registration's constants, named once ---------------------------------------

PREREG = "docs/research/prereg-after-tax-l53.md"
PREREG_COMMIT = "ec7cb12"
CUTOFF = "2026-01-01"                       # nothing on or after this date is read
PART = "A"                                   # trial 126's configuration in momentum_width
CAPITALS = (1_000_000.0, 100_000.0)          # primary, second column
TD_A, TD_B = 0.0025, 0.005                   # tracking differences a year, funds (a) and (b)
LAUNCH_B = "2020-08-25"                      # NIFTY200 Momentum 30 launch; before it the TRI is NSE's backtest
LIVE_FROM_LABEL = "2020-09"                  # first return label wholly after the launch
FUND_C_FIRST_NAV = "2021-03-12"
BOOT_N, BOOT_BLOCK, BOOT_SEED = 10000, 12, 53
BOOT_BLOCKS_INFO = (6, 24)
CI_LO, CI_HI = 2.5, 97.5
HALF_FIRST = 94                              # floor(189 / 2)
KEEP_BANDS, REBALANCE_EVERY = (30, 45, 60), (1, 3, 6)
NEAR_MISS_DAYS = 30
BAND_EXPECTED, BAND_SD = 0.0071, 0.0389      # the paper book's band, unchanged by this look
BAND_FLOOR_MONTHS = (6, 12, 24, 36, 60)
FUND_STT_REDEEM, FUND_STAMP_BUY, FUND_STAMP_FROM = 0.00001, 0.00005, "2020-07-01"
EXPECTED_POINTS, EXPECTED_RETURNS = 190, 189
MAX_SUBSTITUTIONS, MAX_STALE_DAYS = 3, 5
MIN_TRI_ROWS_A_YEAR = 240
REL_TOL_REPRO, LOT_TOL, IDENTITY_TOL_RUPEES, HAND_TOL = 1e-12, 1e-9, 1.0, 1e-6
HAND_EVENTS_PER_KIND = 3
HAND_KINDS = ("dividend", "bonus", "split", "rights")
UTI_FIRST_NAV_NEAR, UTI_FIRST_NAV_TOL = 10.0, 0.05
TRI_BASES = {"nifty100_tri.csv": ("2003-01-01", 1000.0), "nifty100_equal_weight_tri.csv": ("2003-01-01", 1000.0),
             "nifty200_momentum30_tri.csv": ("2005-04-01", 1000.0)}
EXPECTED_BOOK_COUNTS = {"buys": 531, "sells": 516, "forced_exits": 2}
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

REPO = os.path.dirname(BACKEND)
DATA_DIR = os.path.join(HERE, "data", "l53")
MANIFEST = os.path.join(DATA_DIR, "manifest.json")
OUT_DIR = os.path.join(REPO, "docs", "research", "data")
STAGE0_OUT = os.path.join(OUT_DIR, "l53_stage0.json")
RESULT_OUT = os.path.join(OUT_DIR, "l53_result.json")
RECORDED_A = os.path.join(OUT_DIR, "momentum_width_A.json")
TESTS = os.path.join(BACKEND, "tests", "test_after_tax_l53.py")

# prepared file -> (path inside R1's research-r1 directory, kind)
RAW = OrderedDict([
    ("nifty100_tri.csv", ("tri/NIFTY_100.json", "tri")),
    ("nifty200_momentum30_tri.csv", ("tri/NIFTY200_MOMENTUM_30.json", "tri")),
    ("nifty200_momentum30_tri_download2.csv", ("tri_test.json", "tri")),
    ("nifty100_equal_weight_tri.csv", ("tri/NIFTY100_EQUAL_WEIGHT.json", "tri")),
    ("uti_nifty200_momentum30_direct_nav.csv", ("nav/148703.json", "nav")),
    ("iima_four_factors_monthly.csv",
     ("iima/2025-12_FourFactors_and_Market_Returns_Monthly_SurvivorshipBiasAdjusted.csv", "iima")),
])
IIMA_COLUMNS = ("SMB", "HML", "WML", "MF", "RF")


def _sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def _sha256(path):
    with open(path, "rb") as f:
        return _sha256_bytes(f.read())


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, default=str)
    os.replace(tmp, path)


def _d(s):
    return datetime.date.fromisoformat(str(s)[:10])


# ---- inputs, cut before 2026 ------------------------------------------------------------

def prepare_data(raw_dir):
    """Copy the downloaded series into research/data/l53/, keeping rows dated before
    2026-01-01. A row's date is parsed first and a 2026 row is dropped before its
    value field is touched; its value is never converted or written."""
    os.makedirs(DATA_DIR, exist_ok=True)
    files = OrderedDict()
    for out, (rel, kind) in RAW.items():
        src = os.path.join(raw_dir, rel)
        with open(src, "rb") as f:
            raw = f.read()
        kept, dropped = [], 0
        if kind in ("tri", "nav"):
            rows = json.loads(raw)
            if kind == "nav":
                rows = rows["data"]
            for r in rows:
                if kind == "tri":
                    d = datetime.datetime.strptime(r["Date"], "%d %b %Y").date().isoformat()
                else:
                    d = datetime.datetime.strptime(r["date"], "%d-%m-%Y").date().isoformat()
                if d >= CUTOFF:
                    dropped += 1
                    continue
                kept.append((d, (r["TotalReturnsIndex"] if kind == "tri" else r["nav"]).replace(",", "")))
            kept.sort()
            header = ["date", "tri" if kind == "tri" else "nav"]
        else:
            reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
            for r in reader:
                label = r["Date"].strip()
                if label >= CUTOFF[:7]:
                    dropped += 1
                    continue
                kept.append(tuple([label] + [r[c].strip() for c in IIMA_COLUMNS]))
            kept.sort()
            header = ["month"] + list(IIMA_COLUMNS)
        dates = [k[0] for k in kept]
        if len(set(dates)) != len(dates):
            raise SystemExit("%s has duplicate dates" % rel)
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(header)
        w.writerows(kept)
        path = os.path.join(DATA_DIR, out)
        with open(path, "w") as f:
            f.write(buf.getvalue())
        files[out] = {"source": rel, "source_sha256": _sha256_bytes(raw), "rows_kept": len(kept),
                      "rows_dropped_on_or_after_2026_01_01": dropped, "first": dates[0], "last": dates[-1],
                      "sha256": _sha256(path)}
        print("%-44s kept %5d rows %s .. %s, dropped %d dated 2026" % (out, len(kept), dates[0], dates[-1], dropped))
    _write(MANIFEST, {"look": "L53", "prepared": datetime.datetime.now(IST).isoformat(), "cutoff": CUTOFF,
                      "files": files})
    return files


def load_series(name):
    """date -> value from a prepared file; refuses a date on or after the cutoff."""
    out = OrderedDict()
    with open(os.path.join(DATA_DIR, name)) as f:
        for r in csv.reader(f):
            if r[0] in ("date", "month"):
                continue
            if r[0] >= CUTOFF[: len(r[0])]:
                raise SystemExit("refused: %s holds a row dated %s" % (name, r[0]))
            if r[0] in out:
                raise SystemExit("refused: %s has a duplicate date %s" % (name, r[0]))
            out[r[0]] = float(r[1])
    if list(out) != sorted(out):
        raise SystemExit("refused: %s is not in date order" % name)
    return out


def load_iima():
    out = OrderedDict()
    with open(os.path.join(DATA_DIR, "iima_four_factors_monthly.csv")) as f:
        for r in csv.DictReader(f):
            if r["month"] >= CUTOFF[:7]:
                raise SystemExit("refused: the IIMA file holds %s" % r["month"])
            out[r["month"]] = {c: (float(r[c]) if r[c] not in ("", "NA") else None) for c in IIMA_COLUMNS}
    return out


def value_on(series, d):
    """(value, date used): the row of d, or the latest one before it."""
    keys = list(series) if not hasattr(series, "_keys") else series._keys
    i = bisect.bisect_right(keys, d) - 1
    if i < 0:
        return None, None
    return series[keys[i]], keys[i]


class Series(OrderedDict):
    """An OrderedDict with its keys kept as a list, for bisect."""

    def __init__(self, src):
        super().__init__(src)
        self._keys = list(src)


def tri_fund_nav(series, td, start):
    """The NAV of an index fund that trails the TRI by td a year: TRI x (1 - td)^(days/365.25)."""
    def nav(d):
        v, _ = value_on(series, d)
        return v * (1 - td) ** ((_d(d) - _d(start)).days / 365.25)
    return nav


def plain_nav(series):
    def nav(d):
        return value_on(series, d)[0]
    return nav


# ---- the book: trial 126 with FIFO lots and tax paid from the account --------------------

def load_panel():
    cache = nse_prices.cache_file(False, True)
    if not os.path.exists(cache):
        raise SystemExit("refused: the repaired panel's cache %s is missing; building it would write "
                         "into the data directory" % cache)
    sessions, chains, meta, events = nse_prices.load(wide=True)
    if sessions[-1] >= CUTOFF:
        raise SystemExit("refused: the panel holds a session dated %s" % sessions[-1])
    return sessions, chains, meta, events


def events_by_session(chains, events):
    out = {}
    for canon, k, kind, f, ex, purpose in events:
        c = chains.get(canon)
        if c is None or k >= len(c["idx"]):
            continue
        out.setdefault(c["idx"][k], []).append((canon, k, kind, f, ex, purpose))
    return out


class Ctx(object):
    def __init__(self, sessions, chains, by_session, rules, slip):
        self.sessions, self.chains, self.by_session = sessions, chains, by_session
        self.rules, self.slip = rules, slip
        self._fmv = {}
        self.gf_idx = bisect.bisect_right(sessions, "2018-01-31") - 1

    def fmv(self, name):
        """Grandfathering value per adjusted share: the highest price on 31 Jan 2018
        (or the last day traded before it), on the panel's adjusted basis. Historical rules only."""
        if not isinstance(self.rules, tx.HistoricalRules):
            return None
        if name not in self._fmv:
            c = self.chains[name]
            k = m3.rows_before(c, self.gf_idx) - 1
            self._fmv[name] = c["high"][k] * c["close"][k] / c["raw"][k] if k >= 0 and c["raw"][k] > 0 else None
        return self._fmv[name]


def _sell_charges(v, slip, dp):
    """Sell-side charges other than STT (section 48 deductions), and the STT."""
    return v * (m3.NSE_TXN + m3.SEBI + m3.GST * (m3.NSE_TXN + m3.SEBI) + slip) + dp, v * m3.STT


class TaxBook(mw.Book):
    """momentum_width.Book with FIFO tax lots, corporate actions on held lots, the
    year's tax paid at the first fill session of the next financial year, and a
    liquidation value at every month point. rules=None switches tax off (lots are
    still kept, so the replay can be checked against trial 126)."""

    def __init__(self, capital, dp, honest=True, stress=False, ctx=None):
        super().__init__(capital, dp, honest=honest, stress=stress)
        self.ctx, self.capital, self.rules = ctx, capital, ctx.rules
        self.lots = tx.Lots()
        self.ledger = tx.TaxLedger(ctx.rules or tx.ForwardRules())
        self._s, self._events_through, self.open_fy = None, -1, None
        self.paid = OrderedDict()
        self.prorata, self.marks, self.event_log, self.fill_log = [], [], [], []
        self.opened, self.closed = {}, []
        self.stt_paid = self.dividends_total = self.realised_total = 0.0
        self.lot_dev = 0.0

    def _date(self):
        return self.ctx.sessions[self._s]

    # -- hooks --------------------------------------------------------------------------
    def work(self, chains, s, sessions, side=None):
        self._s = s
        if self.open_fy is None:
            self.open_fy = tx.fy_of(sessions[s])
        if s > self._events_through:
            self._apply_events(chains, s)
            self._events_through = s
        super().work(chains, s, sessions, side)
        if side == "sell" and self.rules is not None:
            fy = tx.fy_of(sessions[s])
            while self.open_fy < fy:
                self._pay(chains, s, self.open_fy)
                self.open_fy += 1

    def _bought(self, name, px, amount, slip):
        before = self.pos.get(name, 0.0)
        super()._bought(name, px, amount, slip)
        units = self.pos.get(name, 0.0) - before
        if units > 0:
            d, stt = self._date(), amount * m3.STT
            self.lots.add(name, units, amount - stt, d)
            self.stt_paid += stt
            if before == 0:
                self.opened[name] = d
            self.fill_log.append({"side": "buy", "s": self._s, "date": d, "name": name, "px": px,
                                  "amount": amount, "units": units, "slip": slip})

    def _sold(self, name, px, slip):
        q, d = self.pos[name], self._date()
        v = q * px
        charges, stt = _sell_charges(v, slip, m3.DP_PER_SELL if self.dp else 0.0)
        items = self.lots.sell(name, q, v - charges, d, self.ctx.fmv(name))
        self.ledger.add_items(tx.fy_of(d), items)
        self.realised_total += sum(it["gain"] for it in items)
        self.stt_paid += stt
        net = super()._sold(name, px, slip)
        if abs(net - (v - charges - stt)) > 1e-6 * max(1.0, v):
            raise RuntimeError("sell arithmetic differs from momentum_width.Book for %s on %s" % (name, d))
        self.closed.append({"name": name, "opened": self.opened.pop(name, None), "closed": d})
        self.fill_log.append({"side": "sell", "s": self._s, "date": d, "name": name, "px": px, "value": v})
        return net

    def value(self, chains, idx):
        v = super().value(chains, idx)
        self._mark(chains, idx, v)
        return v

    # -- corporate actions on held lots (prereg section 3) ------------------------------------
    def _apply_events(self, chains, s):
        for name, k, kind, f, ex, purpose in self.ctx.by_session.get(s, ()):
            q = self.pos.get(name)
            if not q:
                continue
            c, d = chains[name], self.ctx.sessions[s]
            prev_adj = c["close"][k - 1]
            amount, new_units = None, 0.0
            if kind == "dividend":
                amount = q * prev_adj * (1 - f)
                new_units = self.lots.split(name, f, amount, d)
                self.ledger.add_dividend(tx.fy_of(d), amount)
                self.dividends_total += amount
            elif kind == "bonus":
                amount = 0.0
                new_units = self.lots.split(name, f, 0.0, d)
            elif kind == "rights":
                amount = q * prev_adj * (1 - f)
                new_units = self.lots.split(name, f, amount, d)
                self.ledger.add_item(tx.fy_of(d), {"gain": amount, "term": "st", "acq": d, "sale": d,
                                                   "units": 0.0, "cost": 0.0, "consideration": amount,
                                                   "kind": "rights_renunciation"})
                self.realised_total += amount
            self.event_log.append({"s": s, "date": d, "name": name, "k": k, "kind": kind, "factor": f,
                                   "units_held": q, "prev_adj_close": prev_adj, "prev_raw_close": c["raw"][k - 1],
                                   "adj_close": c["close"][k], "raw_close": c["raw"][k], "amount": amount,
                                   "new_lot_units": new_units, "purpose": purpose})

    # -- the year's tax, paid from the account ------------------------------------------------
    def _pay(self, chains, s, fy):
        tax = self.ledger.settle(fy)
        self.paid[fy] = tax
        if tax <= 0:
            return
        d = self.ctx.sessions[s]
        if self.cash < tax:
            short = tax - self.cash
            dp = m3.DP_PER_SELL if self.dp else 0.0
            vals = OrderedDict((n, q * (m3.close_on_or_before(chains[n], s) or 0.0)) for n, q in self.pos.items())
            rate = m3.STT + m3.NSE_TXN + m3.SEBI + m3.GST * (m3.NSE_TXN + m3.SEBI) + self.ctx.slip
            gross = sum(vals.values())
            x = min(1.0, (short + dp * len(vals)) / (gross * (1 - rate))) if gross > 0 else 0.0
            raised = 0.0
            for n, v in vals.items():
                q_sold, v_sold = self.pos[n] * x, v * x
                charges, stt = _sell_charges(v_sold, self.ctx.slip, dp)
                items = self.lots.sell(n, q_sold, v_sold - charges, d, self.ctx.fmv(n))
                self.ledger.add_items(tx.fy_of(d), items)
                self.realised_total += sum(it["gain"] for it in items)
                self.stt_paid += stt
                self.pos[n] -= q_sold
                if x >= 1.0 or self.pos[n] <= 0:
                    self.pos.pop(n)
                    self.closed.append({"name": n, "opened": self.opened.pop(n, None), "closed": d})
                self.cash += v_sold - charges - stt
                self.cost += charges + stt
                raised += v_sold - charges - stt
            self.prorata.append({"date": d, "fy_paid": fy, "tax": tax, "shortfall": short, "fraction_sold": x,
                                 "raised": raised})
        self.cash -= tax

    # -- the liquidation value at a month point ----------------------------------------------
    def _mark(self, chains, idx, value):
        d = self.ctx.sessions[idx]
        fy = tx.fy_of(d)
        if self.rules is not None and self.open_fy != fy:
            raise RuntimeError("a month point in FY %d before FY %d's tax was paid" % (fy, self.open_fy))
        dp = m3.DP_PER_SELL if self.dp else 0.0
        net, extra, stt_all = self.cash, [], 0.0
        for n, q in self.pos.items():
            v = q * (m3.close_on_or_before(chains[n], idx) or 0.0)
            charges, stt = _sell_charges(v, self.ctx.slip, dp)
            net += v - charges - stt
            stt_all += stt
            extra += self.lots.preview_sell(n, q, v - charges, d, self.ctx.fmv(n))
            dev = abs(self.lots.units(n) - q) / q if q else 0.0
            self.lot_dev = max(self.lot_dev, dev)
        liability = self.ledger.preview(fy, extra)[0] if self.rules is not None else 0.0
        self.marks.append({"idx": idx, "date": d, "value": value, "liquidation_pre_tax": net,
                           "liability": liability, "liquidation_after_tax": net - liability,
                           "liquidation_gain": sum(it["gain"] for it in extra), "liquidation_stt": stt_all})


def run_book(panel, unis, capital, rules, by_session=None):
    """momentum_width.simulate, unchanged, with TaxBook as the strategy's book.
    Returns (series, the TaxBook, the benchmark book, holdings)."""
    sessions, chains, meta, events = panel
    cfg = mw.PARTS[PART]
    ctx = Ctx(sessions, chains, by_session if by_session is not None else events_by_session(chains, events),
              rules, cfg["flat"])
    original, held = mw.Book, {}

    def factory(capital, dp=True, honest=True, stress=False):
        if dp:
            held["book"] = TaxBook(capital, dp, honest=honest, stress=stress, ctx=ctx)
            return held["book"]
        return original(capital, dp=dp, honest=honest, stress=stress)

    mw.Book = factory
    try:
        series, strat, bench, holdings = mw.simulate(sessions, chains, unis, cfg, capital, m3.SELECTION_START)
    finally:
        mw.Book = original
    return series, strat, bench, holdings


def liquidation_path(book, capital, key="liquidation_after_tax"):
    """The account's value path for the headline: the capital at the first point,
    the liquidation value at every later point."""
    return [capital] + [m[key] for m in book.marks[1:]]


# ---- the funds ---------------------------------------------------------------------------

class FundAccount(object):
    """An index fund bought with all the capital at the first point, held, and
    (with rules) harvested every March point and taxed like the book."""
    NAME = "F"

    def __init__(self, nav, rules, capital, fmv_date="2018-01-31"):
        self.nav, self.rules, self.capital = nav, rules, capital
        self.lots = tx.Lots()
        self.ledger = tx.TaxLedger(rules or tx.ForwardRules())
        self.cash, self.units, self.open_fy = capital, 0.0, None
        self.marks, self.paid, self.harvests = [], OrderedDict(), []
        self.fmv_date = fmv_date

    def _fmv(self):
        return self.nav(self.fmv_date) if isinstance(self.rules, tx.HistoricalRules) else None

    def _buy(self, d, amount):
        if amount <= 0:
            return
        stamp = amount * FUND_STAMP_BUY if d >= FUND_STAMP_FROM else 0.0
        u = (amount - stamp) / self.nav(d)
        self.lots.add(self.NAME, u, amount, d)
        self.units += u
        self.cash -= amount

    def _redeem(self, d, units):
        value = units * self.nav(d)
        items = self.lots.sell(self.NAME, units, value, d, self._fmv())
        self.ledger.add_items(tx.fy_of(d), items)
        self.units -= units
        self.cash += value * (1 - FUND_STT_REDEEM)
        return items

    def step(self, d, first=False, harvest=False):
        if first:
            self.open_fy = tx.fy_of(d)
            self._buy(d, self.cash)
        elif self.rules is not None:
            fy = tx.fy_of(d)
            while self.open_fy < fy:
                self._pay(d, self.open_fy)
                self.open_fy += 1
            if harvest:
                self._harvest(d)
        self._mark(d)

    def _pay(self, d, fy):
        tax = self.ledger.settle(fy)
        self.paid[fy] = tax
        if tax > self.cash:
            need = tax - self.cash
            self._redeem(d, min(self.units, need / (self.nav(d) * (1 - FUND_STT_REDEEM))))
        self.cash -= tax

    def _harvest(self, d):
        """Sell long-term units oldest first until the year's long-term gain after
        set-off reaches the exemption; reinvest the proceeds at once."""
        fy = tx.fy_of(d)
        ex = self.rules.lt_exemption(fy)
        nav, sold = self.nav(d), 0.0
        while self.lots.by_name.get(self.NAME):
            lot = self.lots.by_name[self.NAME][0]
            if not tx.is_long_term(lot[2], d):
                break
            whole = lot[0]
            if ex == math.inf or whole * nav - lot[1] <= 0:
                self._redeem(d, whole)
                sold += whole
                continue
            if self.ledger.preview(fy)[1]["lt_after_setoff"] >= ex - 1e-6:
                break
            trial = self.lots.preview_sell(self.NAME, whole, whole * nav, d, self._fmv())
            if self.ledger.preview(fy, trial)[1]["lt_after_setoff"] <= ex:
                self._redeem(d, whole)
                sold += whole
                continue
            lo, hi = 0.0, whole
            for _ in range(200):
                mid = (lo + hi) / 2
                trial = self.lots.preview_sell(self.NAME, mid, mid * nav, d, self._fmv())
                if self.ledger.preview(fy, trial)[1]["lt_after_setoff"] <= ex:
                    lo = mid
                else:
                    hi = mid
            if lo > 0:
                self._redeem(d, lo)
                sold += lo
            break
        if sold > 0:
            self.harvests.append({"date": d, "units_sold": sold, "value": sold * nav,
                                  "lt_after_setoff": self.ledger.preview(fy)[1]["lt_after_setoff"]})
            self._buy(d, self.cash)

    def _mark(self, d):
        nav = self.nav(d)
        value = self.units * nav
        extra = self.lots.preview_sell(self.NAME, self.units, value, d, self._fmv()) if self.units > 0 else []
        liability = self.ledger.preview(tx.fy_of(d), extra)[0] if self.rules is not None else 0.0
        pre = self.cash + value * (1 - FUND_STT_REDEEM)
        self.marks.append({"date": d, "nav": nav, "liquidation_pre_tax": pre, "liability": liability,
                           "liquidation_after_tax": pre - liability})


def run_fund(nav, dates, capital, rules):
    acct = FundAccount(nav, rules, capital)
    for i, d in enumerate(dates):
        acct.step(d, first=(i == 0), harvest=(i > 0 and d[5:7] == "03"))
    return acct


def fund_path(acct, key="liquidation_after_tax"):
    return [acct.capital] + [m[key] for m in acct.marks[1:]]


# ---- statistics ---------------------------------------------------------------------------

def mrets(vals):
    return [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals))]


def cagr(a, b, months):
    return (b / a) ** (12.0 / months) - 1 if months > 0 and a > 0 and b > 0 else None


def t_of(xs):
    if len(xs) < 2:
        return None
    sd = st.stdev(xs)
    return st.mean(xs) / sd * math.sqrt(len(xs)) if sd > 0 else None


def block(xs):
    return {"n": len(xs), "mean": st.mean(xs) if xs else None, "sd": st.stdev(xs) if len(xs) > 1 else None,
            "t": t_of(xs), "share_positive": (sum(x > 0 for x in xs) / len(xs)) if xs else None}


def halves(xs):
    h = len(xs) // 2
    return xs[:h], xs[h:]


def bootstrap_cagr_difference(r1, r2, block_len=BOOT_BLOCK, n=BOOT_N, seed=BOOT_SEED):
    """Circular moving-block bootstrap of paired monthly returns: the CAGR difference
    of each resample (numpy)."""
    import numpy as np
    a, b = np.asarray(r1, float), np.asarray(r2, float)
    T = len(a)
    rng = np.random.default_rng(seed)
    k = int(math.ceil(T / float(block_len)))
    starts = rng.integers(0, T, size=(n, k))
    idx = (starts[:, :, None] + np.arange(block_len)[None, None, :]).reshape(n, -1)[:, :T] % T
    ga = np.exp(np.log1p(a[idx]).sum(axis=1) * 12.0 / T) - 1
    gb = np.exp(np.log1p(b[idx]).sum(axis=1) * 12.0 / T) - 1
    return ga - gb


def compare(path_book, path_fund, first_half=HALF_FIRST, info_blocks=BOOT_BLOCKS_INFO, verdict=True):
    """Book minus fund: CAGR difference (pp a year), bootstrap interval, both halves."""
    import numpy as np
    n = len(path_book) - 1
    cb, cf = cagr(path_book[0], path_book[-1], n), cagr(path_fund[0], path_fund[-1], n)
    rb, rf = mrets(path_book), mrets(path_fund)
    diffs = bootstrap_cagr_difference(rb, rf)
    lo, hi = (float(np.percentile(diffs, q)) * 100 for q in (CI_LO, CI_HI))
    out = {"months": n, "cagr_book": cb, "cagr_fund": cf, "difference_pp": (cb - cf) * 100,
           "ci95_pp": [lo, hi], "bootstrap": {"block": BOOT_BLOCK, "resamples": BOOT_N, "seed": BOOT_SEED},
           "monthly_difference": block([x - y for x, y in zip(rb, rf)])}
    out["ci95_pp_other_blocks"] = {}
    for bl in info_blocks:
        dd = bootstrap_cagr_difference(rb, rf, block_len=bl)
        out["ci95_pp_other_blocks"][str(bl)] = [float(np.percentile(dd, q)) * 100 for q in (CI_LO, CI_HI)]
    if first_half:
        h = {}
        for label, a, b in (("half1", 0, first_half), ("half2", first_half, n)):
            m = b - a
            h[label] = {"months": m, "cagr_book": cagr(path_book[a], path_book[b], m),
                        "cagr_fund": cagr(path_fund[a], path_fund[b], m)}
            h[label]["difference_pp"] = (h[label]["cagr_book"] - h[label]["cagr_fund"]) * 100
        out["halves"] = h
        if verdict:
            D, d1, d2 = out["difference_pp"], h["half1"]["difference_pp"], h["half2"]["difference_pp"]
            if D > 0 and lo > 0 and d1 > 0 and d2 > 0:
                v = "BEATS"
            elif D < 0 and hi < 0 and d1 < 0 and d2 < 0:
                v = "LOSES"
            else:
                v = "TIES"
            out["verdict"] = v
    return out


def pearson(x, y):
    mx, my = st.mean(x), st.mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx, syy = sum((a - mx) ** 2 for a in x), sum((b - my) ** 2 for b in y)
    r = sxy / math.sqrt(sxx * syy)
    n = len(x)
    z, se = math.atanh(r), 1 / math.sqrt(n - 3)
    return {"n": n, "r": r, "ci95": [math.tanh(z - 1.959964 * se), math.tanh(z + 1.959964 * se)]}


def ols(y, cols, names):
    import numpy as np
    X = np.column_stack([np.ones(len(y))] + [np.asarray(c, float) for c in cols])
    Y = np.asarray(y, float)
    beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
    resid = Y - X @ beta
    dof = len(Y) - X.shape[1]
    s2 = float(resid @ resid) / dof
    cov = s2 * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    ss_tot = float(((Y - Y.mean()) ** 2).sum())
    return {"n": len(Y), "r2": 1 - float(resid @ resid) / ss_tot,
            "coef": {nm: {"b": float(b), "t": float(b / s)} for nm, b, s in zip(["const"] + names, beta, se)}}


# ---- section 9: turnover by name counts, no position valued ---------------------------------

def decisions(sessions, chains, unis):
    """Trial 126's decision months with each month's ranking (signal only)."""
    mes = m3.month_ends(sessions)
    me_idx = {m: i for m, i in mes}
    months = [m for m, _ in mes]
    lo, hi = mw.PARTS[PART]["ranks"]
    out = []
    for month, idx in mes:
        if month < m3.SELECTION_START:
            continue
        f = idx + 1
        if f >= len(sessions) or sessions[f] >= mw.HELD_OUT_FIRST_SESSION:
            break
        names = unis[month]["e3i"][lo - 1:hi]
        sc = m3.scores(chains, names, me_idx, months, month, idx)
        if not sc:
            continue
        order = sorted(sc, key=sc.get, reverse=True)
        out.append({"month": month, "idx": idx, "f": f, "order": order,
                    "rank": {n: i + 1 for i, n in enumerate(order)}, "uset": set(names)})
    return out


def holding_stats(closed, open_ages, years):
    days = [(_d(c) - _d(o)).days for o, c in closed]
    lt = [tx.is_long_term(o, c) for o, c in closed]
    near = [(not l) and _d(c) > tx.add_months(o, 12) - datetime.timedelta(days=NEAR_MISS_DAYS)
            for (o, c), l in zip(closed, lt)]
    n = len(closed)
    return {"sells": n, "sells_a_year": n / years, "one_sided_turnover_by_names": n / years / m3.N_HOLD,
            "holding_days_mean": st.mean(days) if days else None,
            "holding_days_median": st.median(days) if days else None,
            "share_long_term": sum(lt) / n if n else None,
            "share_within_30_days_before_the_12_month_line": sum(near) / n if n else None,
            "open_at_end": len(open_ages), "open_age_days": sorted(open_ages)}


def turnover_run(decs, sessions, chains, keep, every, phase):
    held, closed = {}, []
    for i, dc in enumerate(decs):
        idx, f = dc["idx"], dc["f"]
        for n in list(held):
            if chains[n]["idx"][-1] < idx:
                closed.append((held.pop(n), sessions[idx]))
        if i < phase or (i - phase) % every:
            continue
        for n in list(held):
            if n not in dc["uset"] or dc["rank"].get(n, 10 ** 9) > keep:
                closed.append((held.pop(n), sessions[f]))
        vac = m3.N_HOLD - len(held)
        for n in dc["order"]:
            if vac <= 0:
                break
            if n not in held:
                held[n] = sessions[f]
                vac -= 1
    end = sessions[decs[-1]["f"]]
    return closed, [(_d(end) - _d(o)).days for o in held.values()]


def turnover_diagnostics(decs, sessions, chains, trial126_closed, trial126_open):
    years = (len(decs) - 1) / 12.0
    grid = OrderedDict()
    for keep in KEEP_BANDS:
        for every in REBALANCE_EVERY:
            runs = [holding_stats(*turnover_run(decs, sessions, chains, keep, every, p), years=years)
                    for p in range(every)]
            row = {"phase0": runs[0]}
            if every > 1:
                keys = [k for k in runs[0] if k not in ("open_age_days",)]
                row["mean_over_phases"] = {k: st.mean([r[k] for r in runs]) for k in keys
                                           if all(r[k] is not None for r in runs)}
            grid["keep%d_every%d" % (keep, every)] = row
    return {"years": years, "grid": grid,
            "trial126_with_fill_rules": holding_stats(trial126_closed, trial126_open, years)}


# ---- stage 0 --------------------------------------------------------------------------------

def _git(*args):
    return subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True).stdout.strip()


def environment():
    return {"python": platform.python_version(), "platform": platform.platform(), "commit": _git("rev-parse", "HEAD"),
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "sahab_research_data": os.environ.get("SAHAB_RESEARCH_DATA"),
            "sahab_db_path": os.environ.get("SAHAB_DB_PATH")}


class Halt(Exception):
    pass


def _check(rec, key, ok, why):
    rec[key]["passes"] = bool(ok)
    if not ok:
        raise Halt("%s: %s" % (key, why))


def _rel(a, b):
    return abs(a - b) / max(abs(b), 1e-300)


def check_inputs():
    with open(MANIFEST) as f:
        man = json.load(f)
    out = {"files": {}, "passes": True}
    bad = []
    for name, info in man["files"].items():
        path = os.path.join(DATA_DIR, name)
        ok = _sha256(path) == info["sha256"]
        with open(path) as f:
            dates = [r[0] for r in csv.reader(f)][1:]
        last_ok = max(dates) < (CUTOFF if len(dates[0]) == 10 else CUTOFF[:7])
        out["files"][name] = {"sha256_matches_manifest": ok, "first": min(dates), "last": max(dates),
                              "rows": len(dates), "rows_dropped_on_or_after_2026_01_01_in_source":
                                  info["rows_dropped_on_or_after_2026_01_01"]}
        if not (ok and last_ok):
            bad.append(name)
    out["bad"] = bad
    return out


def coverage(series, dates):
    subs = []
    for d in dates:
        v, used = value_on(series, d)
        if used != d:
            subs.append({"date": d, "used": used, "stale_days": None if used is None else (_d(d) - _d(used)).days})
    return subs


def hand_path_rows(date, aliases):
    """The printed row of a symbol on a date, read from the bhavcopy zip directly."""
    d = _d(date)
    names = [d.strftime("%d%b%Y").upper() + ".zip", d.strftime("%Y%m%d") + ".zip"]
    for nm in names:
        path = os.path.join(nse_prices.BHAV_DIR, nm)
        if not os.path.exists(path):
            continue
        with zipfile.ZipFile(path) as z, z.open(z.namelist()[0]) as fh:
            for r in csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="ignore")):
                r = {k.strip(): (v or "").strip() for k, v in r.items() if k}
                sym = r.get("TckrSymb") or r.get("SYMBOL")
                ser = r.get("SctySrs") or r.get("SERIES")
                if sym in aliases and ser in ("EQ", "BE", "BZ"):
                    close = float(r.get("ClsPric") or r.get("CLOSE"))
                    prev = float(r.get("PrvsClsgPric") or r.get("PREVCLOSE"))
                    return {"file": nm, "symbol": sym, "series": ser, "close": close, "prev_close": prev}
    return None


def hand_path_action(ex_date, aliases):
    """NSE's corporate-action rows for a symbol on an ex-date, read from the CSV directly."""
    path = os.path.join(nse_prices.CA_DIR, "ca_%s.csv" % ex_date[:4])
    want = _d(ex_date).strftime("%d-%b-%Y")
    rows = []
    with open(path, encoding="utf-8-sig", errors="ignore") as fh:
        for r in csv.DictReader(fh):
            r = {k.strip().strip('"'): (v or "").strip() for k, v in r.items() if k}
            if r.get("SYMBOL") in aliases and r.get("EX-DATE", "").lower() == want.lower():
                rows.append({"purpose": r.get("PURPOSE", ""), "face_value": r.get("FACE VALUE", "")})
    return rows


RX_HAND = {
    "dividend": re.compile(r"^(?:interim |final |special )?dividend\s*-\s*r[se]\.?\s*([\d.]+)\s*per\s*share$", re.I),
    "bonus": re.compile(r"^bonus\s*(\d+)\s*:\s*(\d+)$", re.I),
    "split": re.compile(r"^face value split \(sub-division\)\s*-\s*from\s*r[se]\.?\s*([\d.]+)/?-?\s*per share to\s*r[se]\.?\s*([\d.]+)/?-?\s*per share$", re.I),
    "rights": re.compile(r"^rights\s*(\d+)\s*:\s*(\d+)\s*@\s*premium\s*r[se]\.?\s*([\d.]+)/?-?$", re.I),
}


def hand_check_events(book, panel):
    """Stage 0 check 6: seeded corporate actions on held positions, recomputed from the
    bhavcopy zip and NSE's CSV. Only events whose purpose has one simple form, on a
    position with no other action between its buy and the event, are candidates."""
    sessions, chains, meta, events = panel
    aliases = meta.get("aliases", {})
    by_name = {}
    for e in book.event_log:
        by_name.setdefault(e["name"], []).append(e)
    buys = {}
    for fl in book.fill_log:
        if fl["side"] == "buy":
            buys.setdefault(fl["name"], []).append(fl)
    rng = random.Random(BOOT_SEED)
    out, candidates = [], {k: [] for k in HAND_KINDS}
    for e in book.event_log:
        if e["kind"] not in HAND_KINDS:
            continue
        before = [b for b in buys.get(e["name"], []) if b["s"] < e["s"]]
        if not before:
            continue
        buy = before[-1]
        between = [x for x in by_name[e["name"]] if buy["s"] < x["s"] < e["s"]]
        same = [x for x in by_name[e["name"]] if x["s"] == e["s"] and x is not e]
        if between or same:
            continue
        candidates[e["kind"]].append((e, buy))
    for kind in HAND_KINDS:
        pool = candidates[kind]
        rng.shuffle(pool)
        taken = 0
        for e, buy in pool:
            if taken >= HAND_EVENTS_PER_KIND:
                break
            al = set(aliases.get(e["name"], [e["name"]])) | {e["name"]}
            acts = hand_path_action(e["date"], al)
            m = None
            for a in acts:
                m = RX_HAND[kind].match(a["purpose"].strip())
                if m:
                    act = a
                    break
            row_buy = hand_path_rows(buy["date"], al)
            if not m or len(acts) != 1 or row_buy is None:
                continue
            rate = m3.STT + m3.STAMP_BUY + m3.NSE_TXN + m3.SEBI + m3.GST * (m3.NSE_TXN + m3.SEBI) + buy["slip"]
            shares_hand = buy["amount"] * (1 - rate) / row_buy["close"]
            shares_engine = e["units_held"] * e["prev_adj_close"] / e["prev_raw_close"]
            rec = {"kind": kind, "name": e["name"], "ex_date": e["date"], "purpose": act["purpose"],
                   "buy_date": buy["date"], "buy_file": row_buy["file"], "printed_buy_close": row_buy["close"],
                   "shares_hand": shares_hand, "shares_engine": shares_engine}
            if kind == "dividend":
                rec["hand"] = shares_hand * float(m.group(1))
                rec["engine"] = e["amount"]
            elif kind == "bonus":
                a, b = float(m.group(1)), float(m.group(2))
                rec["hand"] = shares_hand * a / b
                rec["engine"] = e["new_lot_units"] * e["adj_close"] / e["raw_close"]
            elif kind == "split":
                a, b = float(m.group(1)), float(m.group(2))
                rec["hand"] = shares_hand * a / b
                rec["engine"] = e["units_held"] * e["adj_close"] / e["raw_close"]
            else:
                a, b, prem = float(m.group(1)), float(m.group(2)), float(m.group(3))
                row_prev = hand_path_rows(sessions[chains[e["name"]]["idx"][e["k"] - 1]], al)
                fv = float(act["face_value"] or 0)
                if row_prev is None:
                    continue
                P = row_prev["close"]
                terp = (b * P + a * (fv + prem)) / (a + b)
                rec["hand"] = shares_hand * (P - terp)
                rec["engine"] = e["amount"]
            rec["relative_difference"] = _rel(rec["engine"], rec["hand"]) if rec["hand"] else None
            rec["shares_relative_difference"] = _rel(shares_engine, shares_hand)
            rec["ok"] = (rec["relative_difference"] is not None and rec["relative_difference"] <= HAND_TOL
                         and rec["shares_relative_difference"] <= HAND_TOL)
            out.append(rec)
            taken += 1
    return {"checked": out, "candidates_by_kind": {k: len(v) for k, v in candidates.items()},
            "checked_by_kind": dict(Counter(r["kind"] for r in out))}


def stage0():
    t0 = time.time()
    rec = OrderedDict([("look", "L53"), ("prereg", PREREG), ("prereg_commit", PREREG_COMMIT),
                       ("started", datetime.datetime.now(IST).isoformat()), ("environment", environment())])
    status = "HALTED"
    try:
        # 1. inputs cut before 2026
        rec["1_inputs_cut_before_2026"] = check_inputs()
        panel = load_panel()
        sessions, chains, meta, events = panel
        iima = load_iima()
        c1 = rec["1_inputs_cut_before_2026"]
        c1.update({"panel_first_session": sessions[0], "panel_last_session": sessions[-1],
                   "panel_sessions_on_or_after_cutoff": sum(1 for s in sessions if s >= CUTOFF),
                   "iima_last_month": list(iima)[-1]})
        _check(rec, "1_inputs_cut_before_2026",
               not c1["bad"] and c1["panel_sessions_on_or_after_cutoff"] == 0 and c1["iima_last_month"] == "2025-12",
               "a prepared file differs from its manifest or holds 2026, or the panel does")
        print("stage 0: 1 inputs cut before 2026 - ok (%.0f s)" % (time.time() - t0), flush=True)

        # 2. trial 126 reproduced by momentum_width.simulate, unchanged
        with open(RECORDED_A) as f:
            recd = json.load(f)
        base = recd["base"]
        unis = mw.universes(sessions, chains)
        cfg = mw.PARTS[PART]
        series, strat, bench, holdings = mw.simulate(sessions, chains, unis, cfg, CAPITALS[0], m3.SELECTION_START)
        sv, bv = [s[2] for s in series], [s[3] for s in series]
        dev_s = max(_rel(a, b) for a, b in zip(sv, base["values"]["strategy"])) if len(sv) == len(base["values"]["strategy"]) else None
        dev_b = max(_rel(a, b) for a, b in zip(bv, base["values"]["benchmark"])) if len(bv) == len(base["values"]["benchmark"]) else None
        counts = {"buys": strat.buys, "sells": strat.sells, "forced_exits": strat.forced}
        s1, _, _, _ = mw.simulate(sessions, chains, unis, cfg, CAPITALS[1], m3.SELECTION_START)
        sv1, bv1 = [s[2] for s in s1], [s[3] for s in s1]
        col = recd["capital_columns"]["100000"]
        ex1 = [a - b for a, b in zip(m3.mrets(sv1), m3.mrets(bv1))]
        rec["2_trial126_reproduced"] = {
            "points": len(sv), "recorded_points": len(base["values"]["strategy"]),
            "first_point": series[0][1], "last_point": series[-1][1],
            "months": [series[0][0], series[-1][0]],
            "strategy_max_relative_difference": dev_s, "benchmark_max_relative_difference": dev_b,
            "holdings_identical": holdings == base["holdings"],
            "months_identical": [s[0] for s in series] == base["months"],
            "book_counts": counts, "fills": dict(strat.count), "recorded_fills": base["strategy_book"]["fills"],
            "capital_100000": {"cagr": m3.describe(sv1)["cagr"], "recorded_cagr": col["cagr"],
                               "excess_mean": st.mean(ex1), "recorded_excess_mean": col["excess_mean"]}}
        c2 = rec["2_trial126_reproduced"]
        ok2 = (len(sv) == EXPECTED_POINTS and dev_s is not None and dev_s <= REL_TOL_REPRO and dev_b <= REL_TOL_REPRO
               and c2["holdings_identical"] and c2["months_identical"] and counts == EXPECTED_BOOK_COUNTS
               and dict(strat.count) == base["strategy_book"]["fills"]
               and _rel(c2["capital_100000"]["cagr"], col["cagr"]) <= REL_TOL_REPRO
               and _rel(c2["capital_100000"]["excess_mean"], col["excess_mean"]) <= REL_TOL_REPRO)
        _check(rec, "2_trial126_reproduced", ok2, "momentum_width.simulate does not give trial 126's record")
        print("stage 0: 2 trial 126 reproduced - ok (%.0f s)" % (time.time() - t0), flush=True)
        dates = [s[1] for s in series]

        # 3. the replay with tax switched off
        by_session = events_by_session(chains, events)
        c3 = {}
        book10 = None
        for cap, ref in ((CAPITALS[0], sv), (CAPITALS[1], sv1)):
            ser, book, _, _ = run_book(panel, unis, cap, None, by_session)
            vals = [s[2] for s in ser]
            dev = max(_rel(a, b) for a, b in zip(vals, ref)) if len(vals) == len(ref) else None
            last = book.marks[-1]
            lhs = last["liquidation_pre_tax"] - cap
            rhs = (book.realised_total + last["liquidation_gain"] + book.dividends_total
                   - (book.stt_paid + last["liquidation_stt"]))
            c3[str(int(cap))] = {"points": len(vals), "max_relative_difference": dev,
                                 "largest_lot_deviation": book.lot_dev, "identity_residual_rupees": lhs - rhs,
                                 "marks": len(book.marks), "tax_paid": sum(book.paid.values()),
                                 "prorata_sales": len(book.prorata)}
            if cap == CAPITALS[0]:
                book10 = book
        rec["3_replay_tax_off"] = c3
        ok3 = all(v["points"] == EXPECTED_POINTS and v["max_relative_difference"] is not None
                  and v["max_relative_difference"] <= REL_TOL_REPRO and v["largest_lot_deviation"] <= LOT_TOL
                  and abs(v["identity_residual_rupees"]) <= IDENTITY_TOL_RUPEES and v["marks"] == EXPECTED_POINTS
                  and v["tax_paid"] == 0 and v["prorata_sales"] == 0 for v in c3.values())
        _check(rec, "3_replay_tax_off", ok3, "the replay with tax off differs from trial 126 or its lots do not add up")
        print("stage 0: 3 replay with tax off - ok (%.0f s)" % (time.time() - t0), flush=True)

        # 4. coverage on the point dates
        series_names = ("nifty100_tri.csv", "nifty200_momentum30_tri.csv", "nifty100_equal_weight_tri.csv")
        loaded = {n: Series(load_series(n)) for n in series_names + ("uti_nifty200_momentum30_direct_nav.csv",
                                                                   "nifty200_momentum30_tri_download2.csv")}
        c_start = next(i for i, d in enumerate(dates) if d >= FUND_C_FIRST_NAV)
        c4 = {"fund_c_first_point": dates[c_start], "fund_c_points": len(dates) - c_start, "series": {}}
        bad4 = []
        for n in series_names:
            subs = coverage(loaded[n], dates)
            years = Counter(d[:4] for d in loaded[n])
            thin = {y: years.get(str(y), 0) for y in range(2009, 2026) if years.get(str(y), 0) < MIN_TRI_ROWS_A_YEAR}
            vals_ok = all(v > 0 and math.isfinite(v) for v in loaded[n].values())
            c4["series"][n] = {"substitutions": subs, "thin_years": thin, "values_positive_finite": vals_ok}
            if len(subs) > MAX_SUBSTITUTIONS or any(s["stale_days"] is None or s["stale_days"] > MAX_STALE_DAYS for s in subs) \
                    or thin or not vals_ok:
                bad4.append(n)
        nav = loaded["uti_nifty200_momentum30_direct_nav.csv"]
        subs = coverage(nav, dates[c_start:])
        vals_ok = all(v > 0 and math.isfinite(v) for v in nav.values())
        c4["series"]["uti_nifty200_momentum30_direct_nav.csv"] = {"substitutions": subs, "values_positive_finite": vals_ok}
        if len(subs) > MAX_SUBSTITUTIONS or any(s["stale_days"] is None or s["stale_days"] > MAX_STALE_DAYS for s in subs) \
                or not vals_ok:
            bad4.append("uti_nifty200_momentum30_direct_nav.csv")
        ret_labels = [_label_of_return(series, i) for i in range(1, len(series))]
        missing = [m for m in ret_labels if m not in iima or any(iima[m][c] is None for c in IIMA_COLUMNS)]
        c4["iima"] = {"labels_needed": [ret_labels[0], ret_labels[-1]], "missing_or_na": missing}
        if missing:
            bad4.append("iima")
        c4["bad"] = bad4
        rec["4_coverage"] = c4
        _check(rec, "4_coverage", not bad4, "coverage fails for %s" % bad4)
        print("stage 0: 4 coverage - ok (%.0f s)" % (time.time() - t0), flush=True)

        # 5. hand checks of the data
        c5 = {"tri_base_values": {}, "download_agreement": {}, "uti_first_nav": {}}
        ok5 = True
        for n, (d0, v0) in TRI_BASES.items():
            v = loaded[n].get(d0)
            c5["tri_base_values"][n] = {"date": d0, "value": v, "expected": v0}
            ok5 &= v is not None and abs(v - v0) < 1e-9
        a, b = loaded["nifty200_momentum30_tri.csv"], loaded["nifty200_momentum30_tri_download2.csv"]
        common = set(a) & set(b)
        mism = sorted(d for d in common if a[d] != b[d])
        c5["download_agreement"] = {"dates_first": len(a), "dates_second": len(b), "common": len(common),
                                    "only_first": len(set(a) - set(b)), "only_second": len(set(b) - set(a)),
                                    "mismatched_values": len(mism)}
        ok5 &= len(set(a) ^ set(b)) == 0 and not mism
        first_d = next(iter(nav))
        c5["uti_first_nav"] = {"date": first_d, "nav": nav[first_d], "near": UTI_FIRST_NAV_NEAR}
        ok5 &= abs(nav[first_d] / UTI_FIRST_NAV_NEAR - 1) <= UTI_FIRST_NAV_TOL
        rec["5_hand_checks_data"] = c5
        _check(rec, "5_hand_checks_data", ok5, "a TRI base value, the two downloads or the fund's first NAV disagree")
        print("stage 0: 5 hand checks of the data - ok", flush=True)

        # 6. hand checks of the lots
        c6 = hand_check_events(book10, panel)
        rec["6_hand_checks_lots"] = c6
        ok6 = all(r["ok"] for r in c6["checked"]) and c6["checked_by_kind"].get("dividend", 0) >= 1
        _check(rec, "6_hand_checks_lots", ok6, "a corporate action on a held lot differs from its hand calculation")
        print("stage 0: 6 hand checks of the lots - ok: %s" % c6["checked_by_kind"], flush=True)

        # 7. the tax engine's hand-worked cases
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", TESTS], cwd=BACKEND, capture_output=True, text=True)
        tail = [ln for ln in p.stdout.strip().splitlines() if ln.strip()][-1:] if p.stdout else []
        rec["7_tax_engine_tests"] = {"returncode": p.returncode, "summary": tail, "file_sha256": _sha256(TESTS)}
        _check(rec, "7_tax_engine_tests", p.returncode == 0, "the hand-worked cases fail: %s" % tail)
        print("stage 0: 7 tests - ok: %s" % tail, flush=True)

        # 8. information, not a check
        fys = Counter(tx.fy_of(d) for d in dates)
        rec["8_information"] = {
            "events_on_held_positions_by_kind": dict(Counter(e["kind"] for e in book10.event_log)),
            "tax_payment_dates": [d for d in dates if d[5:7] == "04"],
            "harvest_dates": [d for d in dates[1:] if d[5:7] == "03"],
            "points_per_financial_year": {str(k): v for k, v in sorted(fys.items())},
            "windows": {"returns": len(dates) - 1, "half1": HALF_FIRST, "half2": len(dates) - 1 - HALF_FIRST,
                        "fund_b_backtest_returns": sum(1 for m in ret_labels if m < LIVE_FROM_LABEL),
                        "fund_b_live_returns": sum(1 for m in ret_labels if m >= LIVE_FROM_LABEL),
                        "fund_c_returns": len(dates) - 1 - c_start},
            "positions_closed": len(book10.closed), "lots_open_at_end": sum(len(v) for v in book10.lots.by_name.values())}
        status = "STAGE0_DONE"
    except Halt as h:
        rec["halted_at"] = str(h)
        print("stage 0 HALTED: %s" % h, flush=True)
    rec["seconds"] = round(time.time() - t0)
    rec["finished"] = datetime.datetime.now(IST).isoformat()
    _write(STAGE0_OUT, {"stage0": rec, "status": status})
    print("stage 0 %s; written to %s" % (status, STAGE0_OUT), flush=True)
    if status != "STAGE0_DONE":
        raise SystemExit(1)
    return rec


def _label_of_return(series, i):
    """A return is labelled by the rebalance month that ends it (momentum_width)."""
    return series[i][0]


# ---- the one measurement pass -------------------------------------------------------------

def refusals(rerun_reason=None):
    why = []
    if not os.path.exists(STAGE0_OUT):
        why.append("no stage 0 record at %s" % STAGE0_OUT)
    else:
        with open(STAGE0_OUT) as f:
            if json.load(f).get("status") != "STAGE0_DONE":
                why.append("stage 0 did not finish with every check passing")
    for rel in ("docs/research/data/l53_stage0.json", "backend/research/after_tax_l53.py",
                "backend/research/india_tax.py", "backend/research/data/l53/manifest.json"):
        if subprocess.run(["git", "-C", REPO, "ls-files", "--error-unmatch", rel], capture_output=True).returncode:
            why.append("%s is not committed" % rel)
        elif _git("status", "--porcelain", rel):
            why.append("%s differs from its commit" % rel)
    if os.path.exists(RESULT_OUT) and not rerun_reason:
        why.append("%s exists: one run only (prereg section 12)" % RESULT_OUT)
    return why


def book_summary(book, capital, pre_path):
    path = liquidation_path(book, capital)
    n = len(path) - 1
    return {"cagr_after_tax": cagr(path[0], path[-1], n), "cagr_pre_tax_liquidated": cagr(pre_path[0], pre_path[-1], n),
            "terminal_after_tax": path[-1], "terminal_pre_tax_liquidated": pre_path[-1],
            "terminal_liability": book.marks[-1]["liability"],
            "tax_paid_by_fy": {str(k): v for k, v in book.paid.items()}, "tax_paid_total": sum(book.paid.values()),
            "settled_by_fy": {str(k): v for k, v in book.ledger.settled.items()},
            "carry_at_end": book.ledger.carry, "prorata_sales": book.prorata,
            "dividends_total": book.dividends_total,
            "events_on_held_positions": dict(Counter(e["kind"] for e in book.event_log)),
            "going_concern_value_at_end": book.marks[-1]["value"]}


def fund_summary(acct, pre_acct):
    path, pre = fund_path(acct), fund_path(pre_acct, "liquidation_pre_tax")
    n = len(path) - 1
    return {"cagr_after_tax": cagr(path[0], path[-1], n), "cagr_pre_tax_liquidated": cagr(pre[0], pre[-1], n),
            "terminal_after_tax": path[-1], "terminal_pre_tax_liquidated": pre[-1],
            "terminal_liability": acct.marks[-1]["liability"],
            "tax_paid_by_fy": {str(k): v for k, v in acct.paid.items()}, "tax_paid_total": sum(acct.paid.values()),
            "harvests": acct.harvests, "carry_at_end": acct.ledger.carry}


def measure(review_note, rerun_reason=None):
    why = refusals(rerun_reason)
    if why:
        raise SystemExit("refused: " + "; ".join(why))
    t0 = time.time()
    started = {"look": "L53", "status": "STARTED", "started": datetime.datetime.now(IST).isoformat(),
               "review_note": review_note, "rerun_reason": rerun_reason, "stage0_sha256": _sha256(STAGE0_OUT),
               "prereg_commit": PREREG_COMMIT, "environment": environment()}
    _write(RESULT_OUT, started)                    # before any tax is replayed
    c1 = check_inputs()
    if c1["bad"]:
        raise SystemExit("prepared inputs differ from the manifest: %s" % c1["bad"])
    panel = load_panel()
    sessions, chains, meta, events = panel
    with open(RECORDED_A) as f:
        recd = json.load(f)["base"]
    unis = mw.universes(sessions, chains)
    by_session = events_by_session(chains, events)
    tri = {k: Series(load_series(v)) for k, v in (("n100", "nifty100_tri.csv"), ("m30", "nifty200_momentum30_tri.csv"),
                                                   ("n100ew", "nifty100_equal_weight_tri.csv"))}
    uti = Series(load_series("uti_nifty200_momentum30_direct_nav.csv"))
    iima = load_iima()
    rules = OrderedDict([("forward", tx.ForwardRules()), ("historical", tx.HistoricalRules())])

    # 1. the book, tax off (pre-tax liquidation) and under each rule set, both sizes
    books, pre_books, series_by_cap = {}, {}, {}
    for cap in CAPITALS:
        ser, book, _, _ = run_book(panel, unis, cap, None, by_session)
        if cap == CAPITALS[0] and (len(ser) != len(recd["values"]["strategy"]) or max(
                _rel(s[2], r) for s, r in zip(ser, recd["values"]["strategy"])) > REL_TOL_REPRO):
            raise SystemExit("the tax-off replay no longer reproduces trial 126")
        pre_books[cap], series_by_cap[cap] = book, ser
        for rn, r in rules.items():
            _, bk, _, _ = run_book(panel, unis, cap, r, by_session)
            books[(cap, rn)] = bk
        print("book replayed at %d (%.0f s)" % (cap, time.time() - t0), flush=True)
    series = series_by_cap[CAPITALS[0]]
    dates = [s[1] for s in series]
    labels = [s[0] for s in series][1:]
    c_start = next(i for i, d in enumerate(dates) if d >= FUND_C_FIRST_NAV)

    # 2. the funds
    navs = {"a_nifty100": tri_fund_nav(tri["n100"], TD_A, dates[0]),
            "b_nifty200_momentum30": tri_fund_nav(tri["m30"], TD_B, dates[0])}
    funds, pre_funds = {}, {}
    for cap in CAPITALS:
        for fn, nav in navs.items():
            pre_funds[(cap, fn)] = run_fund(nav, dates, cap, None)
            for rn, r in rules.items():
                funds[(cap, fn, rn)] = run_fund(nav, dates, cap, r)
        pre_funds[(cap, "c_uti")] = run_fund(plain_nav(uti), dates[c_start:], cap, None)
        for rn, r in rules.items():
            funds[(cap, "c_uti", rn)] = run_fund(plain_nav(uti), dates[c_start:], cap, r)

    after_tax = OrderedDict()
    for cap in CAPITALS:
        for rn in rules:
            book = books[(cap, rn)]
            pre_path = liquidation_path(pre_books[cap], cap, "liquidation_pre_tax")
            bpath = liquidation_path(book, cap)
            block_out = {"book": book_summary(book, cap, pre_path), "funds": OrderedDict(),
                         "comparisons": OrderedDict()}
            b_drag = (block_out["book"]["cagr_pre_tax_liquidated"] - block_out["book"]["cagr_after_tax"]) * 100
            block_out["book"]["tax_drag_pp"] = b_drag
            for fn in navs:
                acct = funds[(cap, fn, rn)]
                fs = fund_summary(acct, pre_funds[(cap, fn)])
                fs["tax_drag_pp"] = (fs["cagr_pre_tax_liquidated"] - fs["cagr_after_tax"]) * 100
                block_out["funds"][fn] = fs
                cmpd = compare(bpath, fund_path(acct))
                cmpd["break_even_pre_tax_margin_pp"] = b_drag - fs["tax_drag_pp"]
                cmpd["pre_tax_liquidated_difference_pp"] = (block_out["book"]["cagr_pre_tax_liquidated"]
                                                            - fs["cagr_pre_tax_liquidated"]) * 100
                if fn.startswith("b_"):
                    fpath = fund_path(acct)
                    k = sum(1 for m in labels if m < LIVE_FROM_LABEL)
                    cmpd["windows"] = {
                        "backtest_2010_03_to_2020_08": compare(bpath[:k + 1], fpath[:k + 1], first_half=0),
                        "live_2020_09_to_2025_11": compare(bpath[k:], fpath[k:], first_half=0)}
                block_out["comparisons"][fn] = cmpd
            acct_c = funds[(cap, "c_uti", rn)]
            fs = fund_summary(acct_c, pre_funds[(cap, "c_uti")])
            fs["tax_drag_pp"] = (fs["cagr_pre_tax_liquidated"] - fs["cagr_after_tax"]) * 100
            block_out["funds"]["c_uti"] = fs
            cpath = fund_path(acct_c)
            bslice = bpath[c_start:]
            fb = fund_path(funds[(cap, "b_nifty200_momentum30", rn)])[c_start:]
            block_out["comparisons"]["c_uti"] = {
                "window": [dates[c_start], dates[-1]],
                "book_minus_c": compare(bslice, cpath, first_half=0),
                "b_slice_minus_c": compare(fb, cpath, first_half=0)}
            after_tax["%d_%s" % (cap, rn)] = block_out
    print("after-tax replay done (%.0f s)" % (time.time() - t0), flush=True)

    # 3. benchmark realism and the band proposals (pre-tax, net of the book's costs)
    sv, bv = [s[2] for s in series], [s[3] for s in series]
    r_book, r_ew = mrets(sv), mrets(bv)
    r_m30 = mrets([value_on(tri["m30"], d)[0] for d in dates])
    r_ew100 = mrets([value_on(tri["n100ew"], d)[0] for d in dates])
    r_fa = mrets([navs["a_nifty100"](d) for d in dates])
    r_fb = mrets([navs["b_nifty200_momentum30"](d) for d in dates])
    live = [i for i, m in enumerate(labels) if m >= LIVE_FROM_LABEL]
    back = [i for i, m in enumerate(labels) if m < LIVE_FROM_LABEL]

    def ex(a, b, idx):
        xs = [a[i] - b[i] for i in idx]
        h1, h2 = halves(xs)
        return dict(block(xs), half1=block(h1), half2=block(h2))

    everything = list(range(len(labels)))
    realism = {"window": [labels[live[0]], labels[live[-1]]],
               "book_minus_n200m30_tri": ex(r_book, r_m30, live),
               "book_minus_n100ew_tri": ex(r_book, r_ew100, live),
               "book_minus_own_ew200": ex(r_book, r_ew, live),
               "information": {"full_189": {"book_minus_n200m30_tri": ex(r_book, r_m30, everything),
                                            "book_minus_n100ew_tri": ex(r_book, r_ew100, everything),
                                            "book_minus_own_ew200": ex(r_book, r_ew, everything)},
                               "live_window_against_funds": {"book_minus_fund_b": ex(r_book, r_fb, live),
                                                             "book_minus_fund_a": ex(r_book, r_fa, live)}}}
    m30_ew_back, m30_ew_live = ex(r_m30, r_ew, back), ex(r_m30, r_ew, live)
    p1 = {"n200m30_minus_ew200_backtest_2010_03_to_2020_08": m30_ew_back,
          "n200m30_minus_ew200_live_2020_09_to_2025_11": m30_ew_live}
    if m30_ew_back["mean"] > 0:
        s = max(0.0, min(1.0, m30_ew_live["mean"] / m30_ew_back["mean"]))
        p1.update({"s": s, "s_unclipped": m30_ew_live["mean"] / m30_ew_back["mean"],
                   "proposed_expected_monthly": BAND_EXPECTED * s, "sd": BAND_SD,
                   "floors": {str(n): n * BAND_EXPECTED * s - 2 * BAND_SD * math.sqrt(n) for n in BAND_FLOOR_MONTHS},
                   "current_floors": {str(n): n * BAND_EXPECTED - 2 * BAND_SD * math.sqrt(n) for n in BAND_FLOOR_MONTHS}})
    else:
        p1["proposal"] = None
    margin = after_tax["%d_forward" % CAPITALS[0]]["comparisons"]["b_nifty200_momentum30"]["break_even_pre_tax_margin_pp"]
    e2 = (1 + max(0.0, margin) / 100.0) ** (1 / 12.0) - 1
    sd2 = st.stdev([r_book[i] - r_m30[i] for i in everything])
    p2 = {"break_even_margin_pp_a_year": margin, "expected_monthly": e2, "sd": sd2,
          "floors": {str(n): n * e2 - 2 * sd2 * math.sqrt(n) for n in BAND_FLOOR_MONTHS}}
    band = {"P1_expected_figure": p1, "P2_line_against_the_fund": p2,
            "P3_book_minus_n100ew": realism["book_minus_n100ew_tri"],
            "note": "Proposals for the owner only. This look does not change the band."}

    # 4. turnover diagnostics (names only)
    decs = decisions(sessions, chains, unis)
    pb = pre_books[CAPITALS[0]]
    t126_closed = [(c["opened"], c["closed"]) for c in pb.closed if c["opened"]]
    t126_open = [(_d(dates[-1]) - _d(o)).days for o in pb.opened.values()]
    turnover = turnover_diagnostics(decs, sessions, chains, t126_closed, t126_open)

    # 5. IIMA
    excess = [a - b for a, b in zip(r_book, r_ew)]
    fac = {c: [iima[m][c] / 100.0 for m in labels] for c in IIMA_COLUMNS}
    corr = {}
    for c in ("WML", "HML"):
        h1x, h2x = halves(excess)
        h1y, h2y = halves(fac[c])
        corr[c] = {"full": pearson(excess, fac[c]), "half1": pearson(h1x, h1y), "half2": pearson(h2x, h2y)}
    mkt = [a - b for a, b in zip(fac["MF"], fac["RF"])]
    regression = ols(excess, [mkt, fac["SMB"], fac["HML"], fac["WML"]], ["MF_minus_RF", "SMB", "HML", "WML"])

    result = dict(started, status="DONE", finished=datetime.datetime.now(IST).isoformat(),
                  seconds=round(time.time() - t0), dates={"first": dates[0], "last": dates[-1], "points": len(dates),
                                                          "fund_c_first": dates[c_start]},
                  after_tax=after_tax, benchmark_realism=realism, band_proposals=band, turnover=turnover,
                  iima={"correlations": corr, "regression_information": regression})
    _write(RESULT_OUT, result)
    head = after_tax["%d_forward" % CAPITALS[0]]["comparisons"]
    for fn in ("b_nifty200_momentum30", "a_nifty100"):
        c = head[fn]
        print("book minus %-22s %+6.2f pp a year, 95%% [%+.2f, %+.2f], halves %+.2f / %+.2f -> %s"
              % (fn, c["difference_pp"], c["ci95_pp"][0], c["ci95_pp"][1], c["halves"]["half1"]["difference_pp"],
                 c["halves"]["half2"]["difference_pp"], c["verdict"]), flush=True)
    print("wrote", RESULT_OUT, flush=True)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-data", action="store_true", help="copy the downloads, cut before 2026")
    mode.add_argument("--stage0", action="store_true", help="the eight checks; computes no after-tax figure")
    mode.add_argument("--measure", action="store_true", help="the ONE measurement pass, after the review of stage 0")
    ap.add_argument("--raw-dir", default=None, help="R1's research-r1 directory (with --prepare-data)")
    ap.add_argument("--review-note", default=None, help="who approved stage 0, and when (required with --measure)")
    ap.add_argument("--owner-approved-rerun", default=None, help="a recorded reason; only for prereg section 12's cases")
    args = ap.parse_args(argv)
    if args.prepare_data:
        if not args.raw_dir:
            raise SystemExit("--prepare-data needs --raw-dir")
        prepare_data(args.raw_dir)
    elif args.stage0:
        stage0()
    else:
        if not args.review_note:
            raise SystemExit("--measure needs --review-note: the pass runs only after the independent review")
        measure(args.review_note, args.owner_approved_rerun)


if __name__ == "__main__":
    main()
