"""
NSE trading holidays — the exchange is shut all day on these dates
regardless of it being a weekday, so the engine must not treat them as a
normal session. Source: NSE's own holiday-master API
(https://www.nseindia.com/api/holiday-master?type=trading), Capital Market
(CM) and Futures & Options (FO) segments, which agree — pulled 2026-09-13.
Re-pull each year; NSE sometimes revises this list (state election days,
moved-by-notification festivals) after first publishing it.

08-Nov-2026 (Diwali Laxmi Pujan) carries an asterisk on NSE's own list: it's
a full holiday for normal trading, but there's a separate, brief Muhurat
trading session that evening — not something this engine is built to use,
so it's still treated as closed here.
"""

NSE_HOLIDAYS_2026 = {
    "2026-01-15": "Municipal Corporation Election – Maharashtra",
    "2026-01-26": "Republic Day",
    "2026-02-15": "Mahashivratri",  # falls on a Sunday
    "2026-03-03": "Holi",
    "2026-03-21": "Id-Ul-Fitr (Ramadan Eid)",  # falls on a Saturday
    "2026-03-26": "Shri Ram Navami",
    "2026-03-31": "Shri Mahavir Jayanti",
    "2026-04-03": "Good Friday",
    "2026-04-14": "Dr. Baba Saheb Ambedkar Jayanti",
    "2026-05-01": "Maharashtra Day",
    "2026-05-28": "Bakri Id",
    "2026-06-26": "Muharram",
    "2026-08-15": "Independence Day",  # falls on a Saturday
    "2026-09-14": "Ganesh Chaturthi",
    "2026-10-02": "Mahatma Gandhi Jayanti",
    "2026-10-20": "Dussehra",
    "2026-11-08": "Diwali Laxmi Pujan (Muhurat trading only)",  # falls on a Sunday
    "2026-11-10": "Diwali – Balipratipada",
    "2026-11-24": "Prakash Gurpurb Sri Guru Nanak Dev",
    "2026-12-25": "Christmas",
}


def holiday_name(date):
    """date: a datetime.date, or an object with one (e.g. a tz-aware datetime)."""
    d = getattr(date, "date", lambda: date)()
    return NSE_HOLIDAYS_2026.get(d.isoformat())


def is_holiday(date) -> bool:
    return holiday_name(date) is not None


def next_trading_day(date):
    """The next date that isn't a weekend or an NSE holiday — used to tell
    the user when trading actually resumes."""
    import datetime as _dt
    d = getattr(date, "date", lambda: date)()
    d += _dt.timedelta(days=1)
    while d.weekday() >= 5 or is_holiday(d):
        d += _dt.timedelta(days=1)
    return d
