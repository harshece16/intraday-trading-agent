"""
Multi-source news + sentiment.

Sources, in order of trust:
  1. NSE corporate filings (official, see nse_feed.py)            weight 1.5
  2. Marketaux (optional, needs MARKETAUX_API_KEY; entity sentiment) weight 1.2
  3. Alpha Vantage (optional, needs ALPHAVANTAGE_API_KEY; real       weight 1.2
     sentiment scores, but market-wide discovery only — see
     _alphavantage() for why it can't target one NSE symbol)
  4. Google News RSS, India edition (free, no key, broad coverage)  weight 1.0
  5. Yahoo Finance headlines (fallback only)                        weight 0.6

Headlines are de-duplicated, scored — an LLM read of the actual text
(llm_sentiment.py) when that's configured and its budget allows, the keyword
lexicon otherwise, a source's own sentiment score if it supplies one —
weighted by source trust x relevance (does it actually name the company?)
x recency (12h half-life), and scaled by evidence mass so one stale
headline can't dominate.

get_sentiment(symbol)       -> per-stock view, cached 15 min
market_catalysts(universe)  -> which universe stocks are in the news today, cached 10 min
"""

import email.utils
import logging
import re
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests

import config
import llm_sentiment
import nse_feed
import universe
from sentiment_lexicon import score_text

logger = logging.getLogger("trading_bot")

CACHE_TTL_SECONDS = 900
DISCOVERY_TTL_SECONDS = 600
HALF_LIFE_HOURS = 12
MAX_AGE_HOURS = 72
SOURCE_WEIGHT = {"NSE filing": 1.5, "Marketaux": 1.2, "Alpha Vantage": 1.2, "Google News": 1.0, "Yahoo": 0.6}
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

MARKET_QUERIES = (
    "Nifty stocks to watch when:1d",
    "stocks in news today NSE when:1d",
    "NSE shares surge when:1d",
    "NSE shares fall when:1d",
    "order win shares NSE when:2d",
    "brokerage target price upgrade shares India when:2d",
)

# Headlines often use a name that differs from the NSE symbol or the listed company name.
ALIASES = {
    "TCS": ["tcs"], "INFY": ["infosys"], "HDFCBANK": ["hdfc bank"], "ICICIBANK": ["icici bank"],
    "SBIN": ["sbi", "state bank of india"], "BHARTIARTL": ["airtel", "bharti airtel"], "LT": ["l&t", "larsen"],
    "HINDUNILVR": ["hul", "hindustan unilever"], "M&M": ["mahindra & mahindra", "m&m"],
    "BAJFINANCE": ["bajaj finance"], "KOTAKBANK": ["kotak mahindra bank", "kotak bank"],
    "MARUTI": ["maruti suzuki", "maruti"], "SUNPHARMA": ["sun pharma"], "AXISBANK": ["axis bank"],
    "TATAMOTORS": ["tata motors"], "TATASTEEL": ["tata steel"], "ULTRACEMCO": ["ultratech"],
    "RELIANCE": ["reliance industries", "ril"], "ONGC": ["ongc"], "NTPC": ["ntpc"], "ITC": ["itc"],
    "ETERNAL": ["zomato", "blinkit", "eternal ltd"], "TITAN": ["titan company"], "TRENT": ["trent ltd", "zudio"],
    "DMART": ["avenue supermarts", "dmart"], "BEL": ["bharat electronics"], "HAL": ["hindustan aeronautics"],
}

_cache = {}
_discovery = {"ts": 0.0, "data": {}}
_mx_budget = {"date": None, "used": 0}
_av_budget = {"date": None, "used": 0}
_lock = threading.Lock()


def short_name(name):
    n = re.sub(r"\(.*?\)", "", name or "")
    n = re.sub(r"\b(Ltd|Limited)\.?\s*$", "", n.strip())
    return n.strip(" .,")


_FINANCE_CONTEXT = r"\W+(?:ltd|limited|shares?|stocks?|share price|q[1-4]|results|target|nse|bse)\b"


def name_patterns(symbol, name):
    """Regexes that must match for a headline to count as being about this company.
    Single-word names ("Eternal", "Titan", "Trent") also need finance wording right
    after them, otherwise ordinary English headlines match."""
    plain = set(ALIASES.get(symbol.upper(), []))
    contextual = set()
    if name:
        n = short_name(name).lower()
        (contextual if " " not in n else plain).add(n)
    if len(symbol) >= 3 and symbol.isalpha() and symbol.lower() not in plain:
        contextual.add(symbol.lower())
    pats = [re.compile(r"(?<![\w&])" + re.escape(n) + r"(?![\w&])", re.I) for n in plain if n]
    pats += [re.compile(r"(?<![\w&])" + re.escape(n) + _FINANCE_CONTEXT, re.I) for n in contextual if n]
    return pats


def search_query(symbol, name):
    names = [short_name(name)] if name else [symbol]
    names += [a for a in ALIASES.get(symbol.upper(), []) if len(a) > 3][:2]
    quoted = " OR ".join(f'"{n}"' for n in dict.fromkeys(names))
    return f"({quoted}) (share OR shares OR stock) when:2d"


def _google_news(query):
    url = "https://news.google.com/rss/search?q=" + quote(query) + "&hl=en-IN&gl=IN&ceid=IN:en"
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=12)
    resp.raise_for_status()
    out = []
    for item in ET.fromstring(resp.content).iter("item"):
        title = item.findtext("title") or ""
        publisher = item.findtext("source") or ""
        if publisher and title.endswith(" - " + publisher):
            title = title[: -len(publisher) - 3]
        try:
            published = email.utils.parsedate_to_datetime(item.findtext("pubDate"))
        except (TypeError, ValueError):
            published = None
        out.append({"title": title.strip(), "summary": "", "published": published, "source": "Google News",
                    "publisher": publisher, "url": item.findtext("link")})
    return out


def _yahoo(symbol):
    import yfinance as yf
    out = []
    for item in yf.Ticker(f"{symbol}.NS").news or []:
        content = item.get("content", item)
        published = None
        if content.get("pubDate"):
            try:
                published = datetime.fromisoformat(content["pubDate"].replace("Z", "+00:00"))
            except ValueError:
                pass
        url = (content.get("canonicalUrl") or {}).get("url") if isinstance(content.get("canonicalUrl"), dict) else None
        out.append({"title": content.get("title") or "", "summary": content.get("summary") or "",
                    "published": published, "source": "Yahoo",
                    "publisher": (content.get("provider") or {}).get("displayName"), "url": url})
    return out


def _marketaux_allowed():
    if not config.NEWS.get("marketaux_api_key"):
        return False
    today = datetime.now(timezone.utc).date()
    with _lock:
        if _mx_budget["date"] != today:
            _mx_budget.update(date=today, used=0)
        if _mx_budget["used"] >= config.NEWS.get("marketaux_daily_limit", 90):
            return False
        _mx_budget["used"] += 1
        return True


def _marketaux(extra_params):
    """Marketaux /v1/news/all filtered to Indian-listed entities. Its per-entity
    sentiment_score is used directly instead of the lexicon."""
    if not _marketaux_allowed():
        return []
    params = {
        "api_token": config.NEWS["marketaux_api_key"], "language": "en", "countries": "in",
        "filter_entities": "true",
        "published_after": (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M"),
        **extra_params,
    }
    resp = requests.get("https://api.marketaux.com/v1/news/all", params=params, timeout=12)
    resp.raise_for_status()
    out = []
    for art in resp.json().get("data", []):
        try:
            published = datetime.fromisoformat((art.get("published_at") or "").replace("Z", "+00:00"))
        except ValueError:
            published = None
        base = {"title": art.get("title") or "", "summary": art.get("description") or "", "published": published,
                "source": "Marketaux", "publisher": art.get("source"), "url": art.get("url")}
        entities = art.get("entities") or []
        for ent in entities:
            out.append({**base, "symbol": (ent.get("symbol") or "").split(".")[0].upper(),
                        "score": ent.get("sentiment_score")})
        if not entities:
            out.append(base)
    return out


def _alphavantage_allowed():
    if not config.NEWS.get("alphavantage_api_key"):
        return False
    today = datetime.now(timezone.utc).date()
    with _lock:
        if _av_budget["date"] != today:
            _av_budget.update(date=today, used=0)
        if _av_budget["used"] >= config.NEWS.get("alphavantage_daily_limit", 20):
            return False
        _av_budget["used"] += 1
        return True


def _alphavantage(extra_params):
    """Alpha Vantage NEWS_SENTIMENT: a broad market feed with real per-article
    sentiment (overall_sentiment_score), used only for market-wide discovery
    and filtered locally by company name — its `tickers` filter is built
    around US-listed symbols (it can't reliably target an NSE symbol like
    RELIANCE or SBIN), so we don't use it as a per-symbol source."""
    if not _alphavantage_allowed():
        return []
    params = {"function": "NEWS_SENTIMENT", "apikey": config.NEWS["alphavantage_api_key"], **extra_params}
    resp = requests.get("https://www.alphavantage.co/query", params=params, timeout=12)
    resp.raise_for_status()
    data = resp.json()
    out = []
    for art in data.get("feed", []) or []:
        try:
            published = datetime.strptime(art["time_published"], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
        except (KeyError, ValueError):
            published = None
        out.append({"title": art.get("title") or "", "summary": art.get("summary") or "", "published": published,
                    "source": "Alpha Vantage", "publisher": art.get("source"), "url": art.get("url"),
                    "score": art.get("overall_sentiment_score")})
    return out


def _aggregate(items, patterns=None):
    now = datetime.now(timezone.utc)
    seen, scored = set(), []
    weighted = weight_sum = 0.0
    for it in items:
        key = re.sub(r"\W+", "", it["title"].lower())[:80]
        if not key or key in seen:
            continue
        seen.add(key)
        age_h = (now - it["published"]).total_seconds() / 3600 if it.get("published") else 24.0
        if age_h > MAX_AGE_HOURS:
            continue
        age_h = max(age_h, 0.0)
        text = f"{it['title']}. {it.get('summary', '')}"
        trusted = it["source"] in ("NSE filing", "Marketaux")
        if not (patterns is None or trusted or any(p.search(text) for p in patterns)):
            continue  # search results that never name the company are noise, not evidence — don't even score them
        llm_scored = False
        if it.get("score") is not None:
            s = it["score"]
        else:
            llm = llm_sentiment.score_headline(it["title"], it.get("summary"))
            if llm is not None:
                s, llm_scored = llm, True
            else:
                s = score_text(text)
        w = SOURCE_WEIGHT.get(it["source"], 1.0) * 0.5 ** (age_h / HALF_LIFE_HOURS)
        weighted += w * s
        weight_sum += w
        scored.append((w * (abs(s) + 0.1), {
            "title": it["title"], "score": round(s, 2), "age_h": round(age_h, 1), "source": it["source"],
            "publisher": it.get("publisher"), "url": it.get("url"), "llm_scored": llm_scored,
        }))
    score = max(-1.0, min(1.0, weighted / weight_sum * min(1.0, weight_sum / 2.0))) if weight_sum else 0.0
    scored.sort(key=lambda x: -x[0])
    return round(score, 3), [h for _, h in scored]


def get_sentiment(symbol, company_name=None):
    key = symbol.upper()
    cached = _cache.get(key)
    if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    if company_name is None:
        company_name = universe.by_symbol().get(key, {}).get("name")
    patterns = name_patterns(key, company_name)
    cfg = config.NEWS
    items, sources, errors = [], {}, []

    def collect(label, fn):
        try:
            got = fn()
            items.extend(got)
            sources[label] = len(got)
        except Exception as exc:
            errors.append(f"{label}: {exc}")

    if cfg.get("use_nse_filings", True):
        collect("NSE filing", lambda: nse_feed.announcements_by_symbol().get(key, []))
    if cfg.get("use_google_news", True):
        collect("Google News", lambda: _google_news(search_query(key, company_name)))
    if cfg.get("marketaux_api_key"):
        name = short_name(company_name) if company_name else key
        collect("Marketaux", lambda: [i for i in _marketaux({"search": name, "limit": 3})
                                      if i.get("symbol") in (None, key)])
    if cfg.get("use_yahoo", True) and not sources.get("Google News"):
        collect("Yahoo", lambda: _yahoo(key))

    score, headlines = _aggregate(items, patterns)
    result = {"score": score, "count": len(headlines), "headlines": headlines[:8], "sources": sources}
    if errors:
        result["errors"] = errors
        logger.warning(f"News for {key}: {'; '.join(errors)}")
    _cache[key] = (time.time(), result)
    return result


def market_catalysts(universe_rows):
    """Which universe stocks are in today's market news / filings, with a catalyst score each."""
    if time.time() - _discovery["ts"] < DISCOVERY_TTL_SECONDS:
        return _discovery["data"]
    cfg = config.NEWS
    headlines = []
    if cfg.get("use_google_news", True):
        for q in MARKET_QUERIES:
            try:
                headlines.extend(_google_news(q))
            except Exception as exc:
                logger.warning(f"Google News query failed ({q}): {exc}")
    if cfg.get("marketaux_api_key"):
        try:
            headlines.extend(_marketaux({"limit": 3}))
        except Exception as exc:
            logger.warning(f"Marketaux discovery failed: {exc}")
    if cfg.get("alphavantage_api_key"):
        try:
            headlines.extend(_alphavantage({"topics": "financial_markets", "limit": 200}))
        except Exception as exc:
            logger.warning(f"Alpha Vantage discovery failed: {exc}")
    filings = nse_feed.announcements_by_symbol() if cfg.get("use_nse_filings", True) else {}

    by_symbol = {}
    for row in universe_rows:
        sym = row["symbol"]
        pats = name_patterns(sym, row["name"])
        matched = [h for h in headlines if h.get("symbol") == sym or any(p.search(h["title"]) for p in pats)]
        matched += filings.get(sym, [])
        if not matched:
            continue
        score, scored = _aggregate(matched)
        if scored and abs(score) >= 0.05:
            by_symbol[sym] = {"score": score, "count": len(scored), "top": scored[0]["title"], "headlines": scored[:3]}

    _discovery.update(ts=time.time(), data=by_symbol)
    return by_symbol
