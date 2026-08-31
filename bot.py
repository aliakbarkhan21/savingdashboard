"""
The Finance Bot — Gemini with live write access to the ledger.

Three things changed from the previous version:

1. **It sees the whole board, not one month.** The old context held only the
   selected month's rows, so "how does this compare to last month" was
   unanswerable. It now gets the month series and a `month_summary` read tool.

2. **It streams.** The old version blocked on a non-streaming call while the
   page animated fake "thinking" phrases in a busy loop, then re-typed the
   finished reply character by character. Text now arrives as the model
   produces it.

3. **Reset is guarded.** `reset_ledger` used to be a plain tool the model could
   fire from a loose sentence. It now demands an exact confirmation phrase the
   user has to supply.
"""
# Deliberately NOT `from __future__ import annotations`. That turns every
# annotation into a string at runtime, and google-genai builds each tool's
# schema by INSPECTING these signatures — handed "float" instead of float it
# raises `isinstance() arg 2 must be a type`, every write tool fails, and the
# model reports "an internal system error occurred while calling the tool".
# The board looked fine; only the bot's ability to write was gone. Every
# annotation used below (list[str], X | None) is valid at runtime on its own.

import os
import queue
import re
import threading
import time
from datetime import date

from google import genai
from google.genai import types

import db
import finance

# Overridable without touching this file: set GEMINI_MODEL in
# .streamlit/secrets.toml (app.py forwards it) or LOOT_LEDGER_MODEL in the
# environment. Swapping models is a one-line config change, not a code change.
#
# Default is a *lite* model deliberately. The free tier meters
# GenerateRequestsPerDayPerProjectPerModel, and gemini-3.6-flash — the previous
# default — allows only 20 requests A DAY, which a single afternoon of use
# exhausts. Lite tiers carry a far larger daily allowance and are more than
# enough to read a personal ledger and summarise it.
MODEL = os.environ.get("LOOT_LEDGER_MODEL") or "gemini-3.5-flash-lite"

# That daily quota is counted PER MODEL, so a model that is spent for the day
# says nothing about the next one. When one runs dry the bot moves down this
# list instead of simply failing, which is what makes a day's usage last:
# the allowance is the sum of every model here, not one model's share.
# Verified against this project's key — all of these answer.
FALLBACK_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.1-pro",
]

# Whichever model actually answered last, so the UI can say when it has moved
# off the preferred one.
ACTIVE_MODEL = MODEL

RESET_PHRASE = "RESET LOOT LEDGER"


def model_chain() -> list[str]:
    """Preferred model first, then the rest, with no repeats."""
    chain = [MODEL]
    for name in FALLBACK_MODELS:
        if name not in chain:
            chain.append(name)
    return chain

# How many tool round trips one message may take. Each one is a SEPARATE
# generate_content request against the quota, so the old ceiling of 24 let a
# single question spend more than an entire minute's free-tier allowance
# (observed limit: 20 requests) before the user saw a word. Five covers every
# real question — most need none, since the system prompt already carries six
# months of totals and the current period's rows.
MAX_TOOL_CALLS = 5

# A 429 is a wait, not a failure: Gemini names the delay in the error body.
# Retried quietly, because nothing has been emitted yet and the thinking
# indicator is still up — the turn just takes longer rather than breaking.
_RATE_LIMIT_RETRIES = 2
_MAX_BACKOFF = 30.0

# Counts every generate_content attempt this process makes. The quota that
# actually bites is per minute, so a running total says nothing on its own —
# the timestamps behind requests_last_minute() are what the UI warns from.
REQUEST_COUNT = 0
_REQUEST_TIMES: list[float] = []
_REQUEST_LOCK = threading.Lock()
_QUOTA_WINDOW = 60.0


def _note_request() -> None:
    global REQUEST_COUNT
    now = time.time()
    with _REQUEST_LOCK:
        REQUEST_COUNT += 1
        _REQUEST_TIMES.append(now)
        while _REQUEST_TIMES and _REQUEST_TIMES[0] < now - _QUOTA_WINDOW:
            _REQUEST_TIMES.pop(0)


def requests_last_minute() -> int:
    """Requests in the trailing minute — the window the free tier measures."""
    now = time.time()
    with _REQUEST_LOCK:
        return sum(1 for t in _REQUEST_TIMES if t >= now - _QUOTA_WINDOW)


def _is_rate_limit(message: str) -> bool:
    upper = message.upper()
    return "429" in message or "RESOURCE_EXHAUSTED" in upper or "RATE_LIMIT" in upper


def _is_daily_quota(message: str) -> bool:
    """A per-day cap, as opposed to a per-minute burst limit.

    The distinction decides what to do: a minute limit clears if you wait, so
    it is worth sleeping on; a day limit will not clear this session, so the
    only useful move is a different model. Gemini names which one it is in the
    quotaId, and the accompanying "retry in 20s" is a token-bucket hint that
    means nothing for a daily cap — sleeping on it just fails again.
    """
    return "PerDay" in message or "per_day" in message.lower()


def _retry_delay(message: str) -> float:
    """However long Gemini asked us to wait, clamped to something bearable."""
    for pattern in (r"retryDelay['\"]?\s*:\s*['\"]?([0-9.]+)s",
                    r"retry in ([0-9.]+)\s*s"):
        found = re.search(pattern, message, re.IGNORECASE)
        if found:
            try:
                return max(1.0, min(float(found.group(1)), _MAX_BACKOFF))
            except ValueError:
                pass
    return 15.0


def _friendly_error(message: str) -> str:
    """Gemini's raw error bodies are JSON dumps. Say what to actually do."""
    if _is_rate_limit(message) and _is_daily_quota(message):
        return ("**Every model is out of free quota for today.** Gemini's free "
                "tier caps requests per model per day, and this key has spent "
                "all of them. Nothing was lost and your records are untouched — "
                "the allowance resets tomorrow. To carry on now, add another "
                "model to `FALLBACK_MODELS` in `bot.py` or enable billing on "
                "the key.")
    if _is_rate_limit(message):
        return ("**Rate limit reached.** That was a short burst limit, not the "
                "daily one — wait a minute and ask again. Nothing was lost.")
    lowered = message.lower()
    if "api key" in lowered or "unauthenticated" in lowered or "401" in message:
        return ("**That API key was rejected.** Check `GEMINI_API_KEY` in "
                "`.streamlit/secrets.toml` and restart.")
    if "not found" in lowered and "model" in lowered:
        return (f"**No such model: `{MODEL}`.** Set `GEMINI_MODEL` in "
                f"`.streamlit/secrets.toml` to one your key can reach.")
    if "deadline" in lowered or "timeout" in lowered or "connection" in lowered:
        return "**Could not reach Gemini.** Check your connection and try again."
    return f"**The bot could not reach Gemini.** {message}"

# Filled in by app.py before each call so the read tools can answer about any
# period, not just the one on screen.
_FRAMES: finance.Frames | None = None


def bind_frames(frames: finance.Frames) -> None:
    global _FRAMES
    _FRAMES = frames


def _today() -> str:
    return str(date.today())


def _match_category(raw: str) -> str:
    table = {c.lower(): c for c in db.CATEGORIES}
    return table.get((raw or "").strip().lower(), "Other")


# ------------------------------------------------------------------ write tools

def log_expense(description: str, category: str, amount: float, date_str: str = "") -> str:
    """Record a purchase or bill in the expenses ledger.

    Args:
        description: what the money was spent on, e.g. "Pizza" or "Electricity bill".
        category: one of Food, Games, Hangouts, Shopping, Subscriptions,
            Transportation, Utilities, Other. Anything unrecognised becomes Other.
        amount: the amount in rupees, positive.
        date_str: the date it happened. Defaults to today when omitted.
    """
    d = finance.parse_date(date_str) if date_str else _today()
    cat = _match_category(category)
    db.add_expense(d, description.strip(), cat, abs(float(amount)))
    return f"Logged {finance.money(abs(float(amount)))} on {description.strip()} under {cat}, dated {finance.display_date(d)}."


def log_transport(amount: float, date_str: str = "", note: str = "") -> str:
    """Record a travel cost — rickshaw, fuel, bus, ride-hailing.

    Args:
        amount: the fare in rupees, positive.
        date_str: the date it happened. Defaults to today.
        note: optional description; unused by the transport ledger but accepted
            so a natural sentence does not fail.
    """
    d = finance.parse_date(date_str) if date_str else _today()
    db.add_transport(d, abs(float(amount)))
    return f"Logged {finance.money(abs(float(amount)))} of transport on {finance.display_date(d)}."


def log_income(source: str, amount: float, date_str: str = "") -> str:
    """Record money arriving — salary, freelance payment, gift, refund.

    Args:
        source: where it came from, e.g. "Salary" or "Freelance invoice".
        amount: the amount in rupees, positive.
        date_str: the date it arrived. Defaults to today.
    """
    d = finance.parse_date(date_str) if date_str else _today()
    db.add_income(d, source.strip(), abs(float(amount)))
    return f"Logged {finance.money(abs(float(amount)))} of income from {source.strip()} on {finance.display_date(d)}."


def log_lent(person: str, amount: float, date_str: str = "") -> str:
    """Record money handed to someone that you expect back — a receivable.

    This is cash leaving your hands now, so it reduces cash on hand until repaid.

    Args:
        person: who took the money.
        amount: the amount in rupees, positive.
        date_str: the date it was handed over. Defaults to today.
    """
    d = finance.parse_date(date_str) if date_str else _today()
    db.add_lent(d, person.strip(), abs(float(amount)))
    return f"Recorded {finance.money(abs(float(amount)))} lent to {person.strip()} on {finance.display_date(d)}."


def log_borrowed(lender: str, amount: float, date_str: str = "") -> str:
    """Record money you took from someone and owe back — a payable.

    This is cash arriving now, so it raises cash on hand until you repay it.

    Args:
        lender: who you borrowed from.
        amount: the amount in rupees, positive.
        date_str: the date you received it. Defaults to today.
    """
    d = finance.parse_date(date_str) if date_str else _today()
    db.add_borrowed(d, lender.strip(), abs(float(amount)))
    return f"Recorded {finance.money(abs(float(amount)))} borrowed from {lender.strip()} on {finance.display_date(d)}."


def settle_debt(direction: str, person: str, date_str: str = "") -> str:
    """Mark an outstanding debt as settled.

    Args:
        direction: "lent" when someone has repaid you, "borrowed" when you have
            repaid someone.
        person: the name on the debt.
        date_str: the date it was settled. Defaults to today. This date decides
            which month the cash movement lands in.
    """
    table = "lent" if direction.strip().lower().startswith("lent") else "borrowed"
    name_col = "person" if table == "lent" else "lender"
    rows = db.get_lent() if table == "lent" else db.get_borrowed()
    target = (person or "").strip().lower()
    open_rows = [r for r in rows if r["paid_back"] == 0 and target in str(r[name_col]).lower()]
    if not open_rows:
        return f"No outstanding {table} entry found for {person!r}. Nothing changed."
    d = finance.parse_date(date_str) if date_str else _today()
    row = open_rows[0]
    db.set_paid_back(table, int(row["id"]), True, d)
    verb = "repaid you" if table == "lent" else "was repaid"
    return (f"Marked {finance.money(float(row['amount']))} from {row[name_col]} as settled "
            f"({verb}) on {finance.display_date(d)}.")


# ------------------------------------------------------------------- read tools

def month_summary(month: str = "") -> str:
    """Report the figures for one month, including months not currently on screen.

    Args:
        month: the month as YYYY-MM, e.g. "2026-07". Omit for the current month.
            Pass "all" for the all-time totals.
    """
    if _FRAMES is None:
        return "Ledger data is not loaded right now."
    key = (month or "").strip()
    if key.lower() in ("all", "all time", "alltime"):
        key = finance.ALL_TIME
    elif not key:
        key = date.today().strftime("%Y-%m")
    snap = finance.snapshot(_FRAMES, key)
    top = snap.top_category
    return "\n".join([
        f"{snap.label}:",
        f"  brought forward: {finance.money(snap.opening)}",
        f"  arrivals (money in): {finance.money(snap.inflow)}",
        f"  departures (money out): {finance.money(snap.outflow)}",
        f"  cash on hand at close: {finance.money(snap.on_hand)}",
        f"  savings rate: {snap.savings_rate:.1f}%",
        f"  budget used: {snap.burn_pct:.1f}% of everything available",
        f"  owed to you: {finance.money(snap.receivable_open)}",
        f"  you owe: {finance.money(snap.payable_open)}",
        f"  net worth: {finance.money(snap.net_worth)}",
        f"  top spending: {top[0]} at {finance.money(top[1])}" if top else "  top spending: nothing logged",
    ])


def list_open_debts() -> str:
    """List every unsettled receivable and payable with names and amounts."""
    lent = [r for r in db.get_lent() if r["paid_back"] == 0]
    borrowed = [r for r in db.get_borrowed() if r["paid_back"] == 0]
    if not lent and not borrowed:
        return "Nothing outstanding in either direction."
    lines = []
    if lent:
        lines.append("Owed to you:")
        lines += [f"  {r['person']}: {finance.money(float(r['amount']))} since {finance.display_date(r['date'])}"
                  for r in lent]
    if borrowed:
        lines.append("You owe:")
        lines += [f"  {r['lender']}: {finance.money(float(r['amount']))} since {finance.display_date(r['date'])}"
                  for r in borrowed]
    return "\n".join(lines)


def reset_ledger(confirm_phrase: str) -> str:
    """Erase every record in every ledger. Irreversible.

    Never call this on a loose request. Ask the user to type the exact phrase
    first, quote the phrase to them, and only call this once they have sent it
    back verbatim.

    Args:
        confirm_phrase: must be exactly "RESET LOOT LEDGER".
    """
    if (confirm_phrase or "").strip() != RESET_PHRASE:
        return (f"Not reset — the confirmation phrase did not match. "
                f"Ask the user to send exactly: {RESET_PHRASE}")
    db.clear_all()
    return "Every ledger has been cleared."


TOOLS = [
    log_expense, log_transport, log_income, log_lent, log_borrowed,
    settle_debt, month_summary, list_open_debts, reset_ledger,
]


# ------------------------------------------------------------------- context

def system_context(snap: finance.Snapshot, frames: finance.Frames, series: dict) -> str:
    display_code, _, display_rate = finance.display_currency()
    recent = []
    for key in sorted(series, reverse=True)[:6]:
        row = series[key]
        recent.append(
            f"  {finance.month_label(key)}: in {finance.money(row.inflow)}, "
            f"out {finance.money(row.outflow)}, closed at {finance.money(row.closing)}"
        )

    cats = [f"  {r['category']}: {finance.money(float(r['amount']))}"
            for r in snap.by_category.to_dict("records")] or ["  nothing logged"]

    departures = []
    for r in snap.departures.head(25).to_dict("records"):
        departures.append(f"  {finance.display_date(r['date'])} | {r['platform']} | "
                          f"{r['label']}: {finance.money(float(r['amount']))}")

    return f"""You are the Finance Bot inside Loot Ledger, a personal cash tracker
belonging to Ali Akbar. You speak with Ali directly. Currency is Pakistani
Rupees, written as "Rs. 1,234.56". Dates are DD/MM/YYYY. Today is {finance.display_date(_today())}.

You hold live write access to his ledgers. When he tells you something happened
("pizza 1500, shirt 5000 shopping", "got paid 60k", "lent Sara 2000"), call the
matching tool for each item rather than describing what he could do. When he
attaches a receipt photo or a CSV, read it and log each row you find.

How the money model works, so your answers match the board:
- Cash on hand = money in - money out - unpaid money you lent + unpaid money you borrowed.
- Lending is cash leaving now. Being repaid is cash coming back. A fully settled
  loan nets to zero.
- Each month opens with the previous month's closing balance carried forward.
- Savings rate measures only income against spending; debt movement is excluded.

Be concise and concrete. Quote real figures from below. Never invent a number.
If something is not in the data, say so plainly.

=== ON SCREEN: {snap.label} ===
Brought forward: {finance.money(snap.opening)}
Arrivals (money in): {finance.money(snap.inflow)}
Departures (money out): {finance.money(snap.outflow)}
Cash on hand: {finance.money(snap.on_hand)}
Savings rate: {snap.savings_rate:.1f}%
Budget used: {snap.burn_pct:.1f}% of everything available
Owed to Ali (unpaid): {finance.money(snap.receivable_open)} across {snap.receivable_count} people
Ali owes (unpaid): {finance.money(snap.payable_open)} across {snap.payable_count} people
Net worth: {finance.money(snap.net_worth)}

=== SPENDING BY PLATFORM ({snap.label}) ===
{chr(10).join(cats)}

=== RECENT MONTHS ===
{chr(10).join(recent) if recent else "  no history yet"}

=== DEPARTURES THIS PERIOD (most recent 25) ===
{chr(10).join(departures) if departures else "  nothing logged"}

For any month not listed above, call month_summary. For debt detail, call
list_open_debts.

=== SHOWING YOUR WORKING ===
Every figure you state must be traceable to the data above or to a tool result.
When you give a number that you worked out rather than read off directly, say
in the same breath where it came from — which months, which categories, or how
many rows it covers. "Rs. 5,010 on Food, across 7 entries" or "Rs. 19,360 out
in August against Rs. 50,730 in July" can be checked against the board;
"you spent a lot on food" cannot. Keep it to a clause, not a footnote.

If the data above does not cover what was asked, say so plainly and name what
is missing. Never estimate a number that is not there, and never carry a
figure over from an earlier answer without re-reading it.

=== CURRENCY ===
Every figure above is already written in {display_code}, which is what the user
is reading the board in. Quote figures in {display_code} and never restate them
in another currency unless asked.

The ledger itself stores Pakistani Rupees, and the log_* tools take PKR. One
{display_code} is {display_rate:,.4f} PKR. So when the user asks you to record
an amount, read it as {display_code} unless they name a currency, and pass
amount * {display_rate:,.4f} to the tool. If {display_code} is PKR the two are
the same and no conversion is needed."""


# ------------------------------------------------------------------- streaming

_SENTINEL = object()


class _Status:
    """An out-of-band progress note — shown while waiting, never kept in the
    reply text, so a backoff message cannot end up saved in the transcript."""

    def __init__(self, text: str) -> None:
        self.text = text


def stream_reply(api_key: str, system_prompt: str, history: list, parts: list,
                 should_stop=None, on_status=None):
    """Yield reply text as it arrives.

    The API call runs on a worker thread and pushes chunks onto a queue; this
    generator drains that queue on the main thread so Streamlit can render each
    piece and so `should_stop` is checked against live session state.
    """
    q: queue.Queue = queue.Queue()

    def worker():
        global ACTIVE_MODEL
        attempt = 0
        chain = model_chain()
        index = 0
        try:
            while True:
                emitted = False
                model = chain[index]
                try:
                    _note_request()
                    client = genai.Client(api_key=api_key)
                    chat = client.chats.create(
                        model=model,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            tools=TOOLS,
                            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                                maximum_remote_calls=MAX_TOOL_CALLS
                            ),
                        ),
                        history=history,
                    )
                    for chunk in chat.send_message_stream(parts):
                        text = getattr(chunk, "text", None)
                        if text:
                            if not emitted:
                                ACTIVE_MODEL = model
                            emitted = True
                            q.put(text)
                    ACTIVE_MODEL = model
                    return
                except Exception as exc:
                    message = str(exc)
                    stopping = should_stop is not None and should_stop()
                    # A model out of quota for the day, or one this key cannot
                    # reach at all, is not worth waiting on — move to the next
                    # and try again immediately. Only ever before any text has
                    # been shown, so a reply can never restart mid-sentence.
                    if (not emitted and not stopping and index + 1 < len(chain)
                            and (_is_daily_quota(message)
                                 or "404" in message
                                 or "not found" in message.lower())):
                        index += 1
                        attempt = 0
                        q.put(_Status(f"{model} is out of free quota for today — "
                                      f"switching to {chain[index]}…"))
                        continue
                    # Only worth retrying before any text has been shown —
                    # re-running the call after a partial answer would print
                    # the beginning of the reply twice.
                    if (_is_rate_limit(message) and not emitted and not stopping
                            and not _is_daily_quota(message)
                            and attempt < _RATE_LIMIT_RETRIES):
                        attempt += 1
                        wait = _retry_delay(message)  # per-minute burst: waiting works
                        # Said out loud: a silent backoff looks identical to
                        # the bot having hung, and the wait can run to half a
                        # minute.
                        q.put(_Status(f"Rate limited — waiting {wait:.0f}s "
                                      f"then retrying ({attempt} of "
                                      f"{_RATE_LIMIT_RETRIES})…"))
                        deadline = time.time() + wait
                        while time.time() < deadline:
                            if should_stop is not None and should_stop():
                                break
                            time.sleep(0.2)
                        continue
                    q.put(RuntimeError(_friendly_error(message)))
                    return
        finally:
            q.put(_SENTINEL)

    threading.Thread(target=worker, daemon=True).start()

    while True:
        if should_stop is not None and should_stop():
            yield "\n\n_Stopped._"
            return
        try:
            item = q.get(timeout=0.1)
        except queue.Empty:
            continue
        if item is _SENTINEL:
            return
        if isinstance(item, _Status):
            if on_status is not None:
                on_status(item.text)
            continue
        if isinstance(item, Exception):
            # Already phrased for a human by _friendly_error.
            yield str(item)
            return
        yield item


def build_parts(text: str, images: list | None = None) -> list:
    """Message text plus any attached image bytes, as google-genai Parts."""
    parts = []
    if text and text.strip():
        parts.append(types.Part.from_text(text=text))
    for img in (images or []):
        parts.append(types.Part.from_bytes(
            data=img["data"], mime_type=img.get("mime_type") or "image/jpeg"
        ))
    return parts or [types.Part.from_text(text=" ")]


def build_history(messages: list, limit: int = 8) -> list:
    """Recent turns as Content objects.

    Images are deliberately dropped from history: re-uploading every receipt on
    every turn cost tokens for no benefit once the model had already read it.
    """
    out = []
    for msg in messages[-limit:]:
        text = msg.get("content", "")
        if msg.get("attachment_text"):
            text += f"\n\n[attached file contents]\n{msg['attachment_text']}"
        if not text.strip():
            continue
        out.append(types.Content(
            role="model" if msg["role"] == "assistant" else "user",
            parts=[types.Part.from_text(text=text)],
        ))
    return out
