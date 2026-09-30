"""
NSE trading holidays — the exchange is shut all day on these dates
regardless of it being a weekday, so the engine must not treat them as a
normal session. Source: NSE's own holiday-master API
(https://www.nseindia.com/api/holiday-master?type=trading), Capital Market
(CM) and Futures & Options (FO) segments, which agree — pulled 2026-09-13,
re-checked 2026-09-30 (unchanged).
Re-pull each year; NSE sometimes revises this list (state election days,
moved-by-notification festivals) after first publishing it.

08-Nov-2026 (Diwali Laxmi Pujan) carries an asterisk on NSE's own list: it's
a full holiday for normal trading, but there's a separate, brief Muhurat
trading session that evening — not something this engine is built to use,
so it's still treated as closed here.

Lists are held per year (NSE_HOLIDAYS). A date in a year with no list is
treated as a trading day on every weekday, so calendar_missing() makes that
loud: the engine logs an error at start-up and on every pre-market read, and
/api/state carries `holiday_calendar_missing` (#162). Weekends stay closed.
The 2026 list was NSE circular CMTR71775 of 2025-12-12 (Capital Market
segment), so the 2027 list is likely in December 2026. Checked on 2026-09-30: no
2027 list in NSE's circulars from June to September 2026, and the
holiday-master API above still returns 2026 only.
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


# Year -> {ISO date: name}. Add a year here, with its source above, once NSE
# publishes it.
NSE_HOLIDAYS = {
    2026: NSE_HOLIDAYS_2026,
}


def _day(date):
    """A datetime.date from a date or a datetime (tz-aware or not)."""
    return getattr(date, "date", lambda: date)()


def holiday_name(date):
    """date: a datetime.date, or an object with one (e.g. a tz-aware datetime).
    None for a day that isn't a listed holiday, including every day of a year
    with no list; see calendar_missing()."""
    d = _day(date)
    return NSE_HOLIDAYS.get(d.year, {}).get(d.isoformat())


def calendar_missing(date):
    """The year, when `date` falls in a year with no holiday list, else None.
    In such a year every weekday counts as a session, holidays included."""
    year = _day(date).year
    return None if year in NSE_HOLIDAYS else year


def missing_calendar_message(year):
    return (f"There is no NSE holiday list for {year} in backend/holidays.py, so every weekday of {year} "
            f"is treated as a trading day, holidays included. Add NSE's {year} list (its circular \"Trading "
            f"holidays for the calendar year {year}\", or nseindia.com/api/holiday-master?type=trading).")


def is_holiday(date) -> bool:
    return holiday_name(date) is not None


def next_trading_day(date):
    """The next date that isn't a weekend or an NSE holiday — used to tell
    the user when trading actually resumes."""
    import datetime as _dt
    d = _day(date)
    d += _dt.timedelta(days=1)
    while d.weekday() >= 5 or is_holiday(d):
        d += _dt.timedelta(days=1)
    return d
