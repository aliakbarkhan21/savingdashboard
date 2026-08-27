"""
Daily FX rates, so the board can be read in a currency other than the one it
stores.

Nothing here converts stored data. Every amount stays in PKR paisa in SQLite
exactly as before; a rate is applied at format time only. That keeps the
ledger's arithmetic exact and reversible — a rate that moves overnight must
never silently restate what last month cost.

Sources, in the order they are tried:

1. TradingView's scanner endpoint. It carries the pairs directly and is what
   was asked for. It is also undocumented and browser-facing, not a published
   API — it can change shape or start refusing requests without notice, so it
   is never the only way to get a number.
2. open.er-api.com, a free keyless daily feed, as the automatic fallback.
3. The last rates fetched, cached in the meta table.
4. A built-in table, so a first run with no network still shows something
   plausible rather than crashing or silently pretending amounts are dollars.
"""
import json
import time
import urllib.error
import urllib.request
from datetime import date

import db

# code -> (symbol, label, decimals shown by default)
CURRENCIES = {
    "PKR": ("Rs.", "Pakistani Rupee", 2),
    "USD": ("$", "US Dollar", 2),
    "GBP": ("£", "Pound Sterling", 2),
    "EUR": ("€", "Euro", 2),
    "AED": ("AED", "UAE Dirham", 2),
}
BASE = "PKR"

_META_RATES = "fx_rates"
_META_FETCHED = "fx_fetched_on"
_META_SOURCE = "fx_source"
_META_TRIED = "fx_tried_at"
_CURRENCY_KEY = "display_currency"

# Only used when there has never been a successful fetch. Deliberately stale
# and labelled as such wherever it is shown.
_FALLBACK = {"USD": 277.0, "GBP": 378.0, "EUR": 323.0, "AED": 75.5}

# Per source. Two sources are tried in turn, so this is half the worst-case
# wait before the board gives up and renders from cache.
_TIMEOUT = 4

# After a failed attempt, don't try again for this long. Without it a machine
# that is simply offline retries on EVERY rerun — and since a rerun happens on
# every click, each one paid the full timeout before anything drew. Rates that
# are a few minutes staler than they could be cost nothing; a board that takes
# 16 seconds to answer a click costs a great deal.
_RETRY_AFTER = 900.0
_TV_URL = "https://scanner.tradingview.com/forex/scan"
_ER_URL = "https://open.er-api.com/v6/latest/PKR"


def _sane(rate) -> bool:
    """A rate is PKR per unit of foreign currency, so it is comfortably > 1.

    Guards against a source that starts returning 0, null, or an inverted
    quote — any of which would silently divide every figure on the board by
    the wrong thing.
    """
    try:
        value = float(rate)
    except (TypeError, ValueError):
        return False
    return 1.0 < value < 100_000.0


def _from_tradingview() -> dict:
    wanted = ("USD", "GBP", "EUR", "AED")
    payload = {
        "symbols": {"tickers": [f"FX_IDC:{c}{BASE}" for c in wanted],
                    "query": {"types": []}},
        "columns": ["close"],
    }
    request = urllib.request.Request(
        _TV_URL, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
        body = json.loads(response.read().decode())
    out = {}
    for row in body.get("data", []):
        code = str(row.get("s", "")).split(":")[-1].replace(BASE, "")
        values = row.get("d") or []
        if code in wanted and values and _sane(values[0]):
            out[code] = float(values[0])
    if len(out) < len(wanted):
        raise ValueError(f"TradingView returned {len(out)} of {len(wanted)} pairs")
    return out


def _from_er_api() -> dict:
    request = urllib.request.Request(_ER_URL, headers={"User-Agent": "loot-ledger"})
    with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
        body = json.loads(response.read().decode())
    quoted = body.get("rates") or {}
    out = {}
    for code in ("USD", "GBP", "EUR", "AED"):
        per_pkr = quoted.get(code)
        # The feed quotes foreign-per-PKR; the board wants PKR-per-foreign.
        if per_pkr:
            inverted = 1.0 / float(per_pkr)
            if _sane(inverted):
                out[code] = inverted
    if len(out) < 4:
        raise ValueError("er-api did not return all four rates")
    return out


def fetch_rates() -> tuple[dict, str]:
    """Live rates and the name of whichever source actually answered."""
    errors = []
    for name, getter in (("TradingView", _from_tradingview),
                         ("open.er-api.com", _from_er_api)):
        try:
            return getter(), name
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}")
    raise RuntimeError("; ".join(errors))


def get_rates(force: bool = False) -> dict:
    """Today's rates, fetched at most once a day.

    Returns {"rates": {...}, "source": str, "fetched_on": "YYYY-MM-DD",
             "stale": bool}. Never raises: a board that cannot reach the
    internet still has to render.
    """
    today = str(date.today())
    cached_raw = db.get_meta(_META_RATES)
    cached = {}
    if cached_raw:
        try:
            parsed = json.loads(cached_raw)
            cached = {k: v for k, v in parsed.items() if _sane(v)}
        except Exception:
            cached = {}
    fetched_on = db.get_meta(_META_FETCHED)

    if not force and cached and fetched_on == today:
        return {"rates": cached, "source": db.get_meta(_META_SOURCE) or "cache",
                "fetched_on": fetched_on, "stale": False}

    # Held off after a recent failure, provided there is something to show.
    if not force and cached:
        try:
            last_try = float(db.get_meta(_META_TRIED) or 0)
        except (TypeError, ValueError):
            last_try = 0.0
        if time.time() - last_try < _RETRY_AFTER:
            return {"rates": cached,
                    "source": db.get_meta(_META_SOURCE) or "cache",
                    "fetched_on": fetched_on or "unknown", "stale": True}

    try:
        fresh, source = fetch_rates()
        db.set_meta(_META_RATES, json.dumps(fresh))
        db.set_meta(_META_FETCHED, today)
        db.set_meta(_META_SOURCE, source)
        db.delete_meta(_META_TRIED)
        return {"rates": fresh, "source": source, "fetched_on": today,
                "stale": False}
    except Exception:
        db.set_meta(_META_TRIED, str(time.time()))
        if cached:
            return {"rates": cached, "source": db.get_meta(_META_SOURCE) or "cache",
                    "fetched_on": fetched_on or "unknown", "stale": True}
        return {"rates": dict(_FALLBACK), "source": "built-in estimate",
                "fetched_on": "never", "stale": True}


def get_currency() -> str:
    code = db.get_meta(_CURRENCY_KEY)
    return code if code in CURRENCIES else BASE


def set_currency(code: str) -> None:
    if code not in CURRENCIES:
        raise ValueError(f"unknown currency {code!r}")
    db.set_meta(_CURRENCY_KEY, code)


def rate_for(code: str, rates: dict | None = None) -> float:
    """PKR per one unit of `code`. The base is 1 by definition."""
    if code == BASE:
        return 1.0
    table = rates if rates is not None else get_rates()["rates"]
    value = table.get(code)
    return float(value) if _sane(value) else float(_FALLBACK.get(code, 1.0))
