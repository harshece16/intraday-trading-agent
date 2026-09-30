"""Indian capital-gains tax on listed equity and equity index-fund units, for
research look L53 (docs/research/prereg-after-tax-l53.md, section 4).

Pure functions and two small containers, no data access:

    fy_of, add_months, is_long_term     the financial year and the 12-month line
    ForwardRules, HistoricalRules       FY 2026-27 on every year; the regime of each year
    compute_fy_tax                      one financial year: set-off, carry-forward, exemption, cess
    TaxLedger                           a year's realised items and dividends, the carried losses
    Lots                                FIFO lots per name: buy, sell, corporate-action splits

A gain item is a dict: {"gain", "term" ("st" or "lt"), "acq", "sale"} and,
for a lot bought before 1 February 2018, "gain_gf" (the gain with the
grandfathered cost), which only the historical rules read.

Research only: nothing on the live path imports this.
"""

import calendar
import datetime
import math
from collections import OrderedDict, deque

LOSS_CARRY_YEARS = 8
GRANDFATHER_ACQ_BEFORE = "2018-02-01"
GRANDFATHER_SALE_FROM = "2018-04-01"
BUDGET_2024 = "2024-07-23"          # new short- and long-term rates apply to transfers on or after this date
ADVANCE_TAX_THRESHOLD = 10000.0     # a year's tax at or above this needed advance tax (amendment 2, B2)
LATE_INTEREST = 0.0605              # 234C 1% x (3x15% + 3x45% + 3x75% + 1x100%) = 5.05%, plus 234B 1% for April


# ---- dates ------------------------------------------------------------------------

def _date(d):
    return d if isinstance(d, datetime.date) else datetime.date.fromisoformat(d[:10])


def fy_of(d):
    """The financial year that contains d, named by its first calendar year:
    2015 is 1 April 2015 to 31 March 2016."""
    d = _date(d)
    return d.year if d.month >= 4 else d.year - 1


def add_months(d, n):
    """d plus n calendar months; a day past the end of the target month is
    clamped to its last day (29 February 2020 + 12 months = 28 February 2021)."""
    d = _date(d)
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    return datetime.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def is_long_term(acq, sale):
    """Held for more than 12 months: a sale on the 12-month anniversary is
    short-term, a sale on the day after is long-term."""
    return _date(sale) > add_months(acq, 12)


# ---- the rules ----------------------------------------------------------------------

class ForwardRules:
    """FY 2026-27's rules applied to every year (prereg section 4, primary)."""
    name = "forward_fy2026_27"
    SLAB = 0.30                       # with 4% cess: the assumed 31.2% on dividends

    def st_rate(self, fy, sale):
        return 0.20

    def lt_rate(self, fy, sale):
        """None: long-term gains of this year are exempt."""
        return 0.125

    def lt_exemption(self, fy):
        return 125000.0

    def dividend_rate(self, fy):
        return self.SLAB

    def cess(self, fy):
        return 0.04

    def grandfathered(self, fy, sale, acq):
        return False


class HistoricalRules:
    """The regime of each year (prereg section 4, information only)."""
    name = "historical"
    SLAB = 0.30

    def st_rate(self, fy, sale):
        if fy == 2024:
            return 0.15 if str(sale) < BUDGET_2024 else 0.20
        return 0.20 if fy >= 2025 else 0.15

    def lt_rate(self, fy, sale):
        if fy <= 2017:
            return None                                  # section 10(38)
        if fy == 2024:
            return 0.10 if str(sale) < BUDGET_2024 else 0.125
        return 0.125 if fy >= 2025 else 0.10

    def lt_exemption(self, fy):
        if fy <= 2017:
            return math.inf
        return 125000.0 if fy >= 2024 else 100000.0

    def dividend_rate(self, fy):
        return self.SLAB if fy >= 2020 else 0.0         # DDT regime to 31 March 2020

    def cess(self, fy):
        return 0.04 if fy >= 2018 else 0.03

    def grandfathered(self, fy, sale, acq):
        return str(sale) >= GRANDFATHER_SALE_FROM and str(acq) < GRANDFATHER_ACQ_BEFORE


# ---- one financial year ---------------------------------------------------------------

def _consume(buckets, keys, loss):
    """Set a loss off against buckets[keys...] in that order; returns what is left of the loss."""
    for k in keys:
        if loss <= 0:
            break
        take = min(buckets[k], loss)
        buckets[k] -= take
        loss -= take
    return loss


def compute_fy_tax(fy, items, dividends, carry, rules):
    """Tax of one financial year.

    items: realised gain items of the year; dividends: rupees of dividend
    income; carry: [{"fy", "term", "amount"}] losses brought forward (not
    mutated); rules: ForwardRules or HistoricalRules.

    Returns (tax, detail, new_carry). new_carry holds what is left of the
    brought-forward losses plus this year's unabsorbed losses, less what lapsed.
    """
    gains = OrderedDict()                    # (term, rate) -> positive gains
    st_loss = lt_loss = 0.0
    exempt_lt = st_gross = lt_gross = 0.0
    for it in items:
        term, sale, acq = it["term"], it["sale"], it["acq"]
        g = it["gain"]
        if term == "lt":
            rate = rules.lt_rate(fy, sale)
            if rate is None:                  # exempt year: neither gain nor loss counts
                exempt_lt += g
                continue
            if rules.grandfathered(fy, sale, acq) and it.get("gain_gf") is not None:
                g = it["gain_gf"]
        else:
            rate = rules.st_rate(fy, sale)
        if g >= 0:
            gains[(term, rate)] = gains.get((term, rate), 0.0) + g
            if term == "st":
                st_gross += g
            else:
                lt_gross += g
        elif term == "st":
            st_loss -= g
        else:
            lt_loss -= g
    by_rate = sorted(gains, key=lambda k: -k[1])                     # highest rate first
    st_keys = [k for k in by_rate if k[0] == "st"]
    lt_keys = [k for k in by_rate if k[0] == "lt"]

    # current-year set-off (section 70), amendment 2's order: ST loss against ST gain,
    # LT loss against LT gain, then what is left of the ST loss against LT gain
    st_loss_left = _consume(gains, st_keys, st_loss)
    lt_loss_left = _consume(gains, lt_keys, lt_loss)
    st_loss_left = _consume(gains, lt_keys, st_loss_left)

    # brought-forward losses (sections 72/74), oldest first within each step; lapse after 8 years
    lapsed, used_bf = 0.0, 0.0
    live = []
    for c in sorted(carry, key=lambda c: (c["fy"], c["term"])):
        if fy - c["fy"] > LOSS_CARRY_YEARS:
            lapsed += c["amount"]
        else:
            live.append(dict(c))
    for term, keys in (("st", st_keys), ("lt", lt_keys), ("st", lt_keys)):
        for c in live:
            if c["term"] == term and c["amount"] > 0:
                left = _consume(gains, keys, c["amount"])
                used_bf += c["amount"] - left
                c["amount"] = left
    new_carry = [c for c in live if c["amount"] > 1e-9]
    if st_loss_left > 1e-9:
        new_carry.append({"fy": fy, "term": "st", "amount": st_loss_left})
    if lt_loss_left > 1e-9:
        new_carry.append({"fy": fy, "term": "lt", "amount": lt_loss_left})

    # the exemption on what long-term gain is left, highest rate first
    lt_after_setoff = sum(gains[k] for k in lt_keys)
    exemption = rules.lt_exemption(fy)
    _consume(gains, lt_keys, exemption)
    cg_tax = sum(amount * k[1] for k, amount in gains.items())
    div_tax = dividends * rules.dividend_rate(fy)
    tax = (cg_tax + div_tax) * (1.0 + rules.cess(fy))
    detail = {
        "fy": fy, "tax": tax, "cg_tax_before_cess": cg_tax, "dividend_tax_before_cess": div_tax,
        "st_gains": st_gross, "st_losses": st_loss, "lt_gains": lt_gross, "lt_losses": lt_loss,
        "exempt_lt_net": exempt_lt,
        "lt_after_setoff": lt_after_setoff, "exemption_used": min(lt_after_setoff, exemption),
        "taxable_by_bucket": {"%s@%g" % k: v for k, v in gains.items()},
        "dividends": dividends, "brought_forward_used": used_bf, "lapsed": lapsed,
        "carry_out": sum(c["amount"] for c in new_carry),
    }
    return tax, detail, new_carry


def interest_on(tax):
    """Interest under sections 234B and 234C on a year's tax paid in April with no
    advance tax (amendment 2, B2): 6.05% of it, if it reached the advance-tax threshold."""
    return tax * LATE_INTEREST if tax >= ADVANCE_TAX_THRESHOLD else 0.0


class TaxLedger:
    """Realised items and dividends by financial year, and the losses carried."""

    def __init__(self, rules):
        self.rules = rules
        self.items, self.dividends = {}, {}
        self.carry = []
        self.settled = OrderedDict()           # fy -> detail

    def add_item(self, fy, item):
        self.items.setdefault(fy, []).append(item)

    def add_items(self, fy, items):
        for it in items:
            self.add_item(fy, it)

    def add_dividend(self, fy, amount):
        self.dividends[fy] = self.dividends.get(fy, 0.0) + amount

    def income(self, fy, extra_items=()):
        """A year's realised income for the surcharge flag (amendment 2, N8): net
        short- and long-term gains (not below zero) and dividends."""
        items = self.items.get(fy, []) + list(extra_items)
        st_net = sum(i["gain"] for i in items if i["term"] == "st")
        lt_net = sum(i["gain"] for i in items if i["term"] == "lt")
        return max(0.0, st_net) + max(0.0, lt_net) + self.dividends.get(fy, 0.0)

    def preview(self, fy, extra_items=()):
        """(tax, detail) of fy as if extra_items were also realised; changes nothing."""
        tax, detail, _ = compute_fy_tax(fy, self.items.get(fy, []) + list(extra_items),
                                        self.dividends.get(fy, 0.0), self.carry, self.rules)
        return tax, detail

    def settle(self, fy):
        """Close fy: its tax, and the losses it carries forward."""
        tax, detail, self.carry = compute_fy_tax(fy, self.items.get(fy, []), self.dividends.get(fy, 0.0),
                                                 self.carry, self.rules)
        self.settled[fy] = detail
        return tax


# ---- lots -----------------------------------------------------------------------------

class Lots:
    """FIFO lots per name: [units, cost in rupees, acquisition date]. Units are
    whatever the caller counts in (the panel's adjusted shares, fund units)."""

    def __init__(self):
        self.by_name = {}

    def add(self, name, units, cost, date):
        if units > 0:
            self.by_name.setdefault(name, deque()).append([units, cost, str(date)[:10]])

    def units(self, name):
        return sum(l[0] for l in self.by_name.get(name, ()))

    def _take(self, name, units, consideration, sale, fmv_per_unit=None, mutate=True):
        """Gain items for selling `units` of name, oldest lots first, for a
        total consideration (rupees, net of deductible charges)."""
        lots = self.by_name.get(name, deque())
        total = sum(l[0] for l in lots)
        if units > total * (1 + 1e-9) + 1e-12:
            raise ValueError("selling %.6f units of %s, %.6f held" % (units, name, total))
        units = min(units, total)
        per_unit = consideration / units if units > 0 else 0.0
        items, left = [], units
        work = lots if mutate else deque([list(l) for l in lots])
        while left > 1e-12 and work:
            lot = work[0]
            q = min(lot[0], left)
            share = q / lot[0]
            cost = lot[1] * share
            cons = per_unit * q
            it = {"gain": cons - cost, "term": "lt" if is_long_term(lot[2], sale) else "st",
                  "acq": lot[2], "sale": str(sale)[:10], "units": q, "cost": cost, "consideration": cons}
            if fmv_per_unit is not None and lot[2] < GRANDFATHER_ACQ_BEFORE:
                cu, su = cost / q, cons / q
                it["gain_gf"] = (su - max(cu, min(fmv_per_unit, su))) * q
            items.append(it)
            if q >= lot[0] - 1e-12 * max(1.0, lot[0]):
                work.popleft()
            else:
                lot[0] -= q
                lot[1] -= cost
            left -= q
        if mutate and not lots:
            self.by_name.pop(name, None)
        return items

    def sell(self, name, units, consideration, sale, fmv_per_unit=None):
        return self._take(name, units, consideration, sale, fmv_per_unit, mutate=True)

    def preview_sell(self, name, units, consideration, sale, fmv_per_unit=None):
        return self._take(name, units, consideration, sale, fmv_per_unit, mutate=False)

    def split(self, name, keep_fraction, new_cost, date):
        """A corporate action that turns part of a holding into a new lot: every
        lot keeps keep_fraction of its units with all its cost and its date;
        the rest become one new lot of cost new_cost, dated `date`, after the
        others. Returns the new lot's units."""
        lots = self.by_name.get(name)
        if not lots or not 0 < keep_fraction < 1:
            return 0.0
        moved = 0.0
        for lot in lots:
            m = lot[0] * (1 - keep_fraction)
            lot[0] -= m
            moved += m
        lots.append([moved, new_cost, str(date)[:10]])
        return moved
