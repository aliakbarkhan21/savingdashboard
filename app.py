"""
Loot Ledger — personal cash tracker for Ali Akbar.

THESIS: Money in and money out are arrivals and departures on one station board.
  Refuses the fintech KPI-card grid this category always ships.
OWN-WORLD: Dark enamel panel lit from within. Amber signage ink on #0E1116,
  split-flap tiles for the four figures, hairline rules instead of card borders,
  Barlow Condensed signage caps over Barlow UI. Colour is rationed to two jobs:
  the platform rail that names a category, and the status lamp. Nothing else.
STORY: Ali reads what is actually left in one glance, then logs the day from the
  sidebar or by telling the bot. A stranger understands the product in seconds.
FIRST VIEWPORT: Full-width board. Service header names the period and its status
  lamp; four flap figures — brought forward, arrivals, departures, on hand — sit
  across one strip; arrivals and departures run beneath as two opposed columns.
  Primary action (Add / the bot) is the sidebar and the top-left board controls.
FORM: Departure board, candidate 3 of 7, seed key 83a32567.
FINISH: unreviewed and undocumented is unfinished; this build ends with the
  finish review, the verdict, DESIGN.md, and every shipping raster carrying its
  provenance.
"""
import calendar
import hashlib
import io
import json
import pathlib
from datetime import date, datetime
from html import escape as esc

import pandas as pd
import streamlit as st

import bot
import db
import demo
import finance
import icons
import importer
import rates
import theme

st.set_page_config(page_title="Loot Ledger", page_icon="▮",
                   layout="wide", initial_sidebar_state="expanded")

# Installs the PWA manifest and iOS home-screen tags into the page <head> —
# see pwa.html for why this needs a real iframe rather than unsafe_allow_html.
# Lets "Add to Home Screen" launch as a standalone app icon instead of a
# bookmarked browser tab.
st.iframe(pathlib.Path(__file__).parent / "pwa.html", height=1)


@st.cache_resource
def _ensure_db() -> None:
    """init_db() is idempotent but does real I/O (schema checks, migrations) —
    cache_resource runs it once per process instead of on every rerun."""
    db.init_db()


_ensure_db()

# Theme choice is read from the URL query string before anything renders, so a
# full browser reload (not just a Streamlit rerun) keeps the mode the user
# picked — session_state alone would reset to the default on reload since it
# does not survive a fresh page load.
if "theme_mode" not in st.session_state:
    _qp_theme = st.query_params.get("theme")
    st.session_state.theme_mode = _qp_theme if _qp_theme in ("light", "dark") else "dark"
IS_DARK = st.session_state.theme_mode == "dark"

# The direction contract, in the emitted markup so it can be audited at runtime.
st.markdown(
    "<!-- LOOT LEDGER · THE DEPARTURE BOARD · seed 83a32567 · "
    "arrivals/departures on one enamel panel; amber ink, hue only for platform "
    "rail and status lamp; flap settle is the one authored motion -->",
    unsafe_allow_html=True,
)
st.markdown(f"<style>{theme.css(IS_DARK)}</style>", unsafe_allow_html=True)


# ------------------------------------------------------------------ state

# Starter prompts. Three are on screen at a time; clicking one sends it and
# that slot alone refills from further down this list, so the two you did not
# pick stay exactly where they were and the row never empties out.
# Defined above _init_state because the slot state below is sized from it.
STARTER_POOL = [
    "What did I spend most on this period?",
    "How does this month compare with last month?",
    "Who still owes me money?",
    "Where could I realistically cut back?",
    "What is my biggest recurring cost?",
    "Am I on track to close this month positive?",
    "Which category is closest to its budget?",
    "How much did I actually keep this month?",
    "What changed most since last month?",
    "How much have I lent out that is still unpaid?",
    "Summarise this month in three lines.",
    "What was my most expensive single day?",
]
# Two rotating prompts, not three. With the "Explain <month>" button below
# them the rail showed four stacked buttons, which read as a list to work
# through rather than a couple of suggestions. Three is the whole group.
STARTER_SLOTS = 2

# Which prompts the group opens on. Not range(STARTER_SLOTS): the two kept are
# the second and third of the original set, so the one that used to sit at the
# top is gone from the opening view while staying in the rotation pool.
STARTER_OPENING = [1, 2]


def next_starter(shown: list[int]) -> int:
    """Next prompt in the pool that is not already on screen."""
    total = len(STARTER_POOL)
    cursor = st.session_state.starter_cursor
    for step in range(total):
        candidate = (cursor + step) % total
        if candidate not in shown:
            st.session_state.starter_cursor = candidate + 1
            return candidate
    st.session_state.starter_cursor = cursor + 1
    return cursor % total


# ---- since you last looked --------------------------------------------
# The monthly digest only fires on the first load of a new month, so for the
# other thirty days opening the board told you nothing you did not already
# know. This is the everyday version: what has been added since the last time
# this browser session recorded a visit. Stored as a plain row id per ledger —
# ids only ever increase, so "higher than last time" is exactly "new", with no
# clock involved and nothing to go wrong across timezones.
LAST_SEEN_KEY = "last_seen_ids"


def _current_max_ids() -> dict:
    getters = {"expenses": db.get_expenses, "transport": db.get_transport,
               "income": db.get_income, "lent": db.get_lent,
               "borrowed": db.get_borrowed}
    out = {}
    for name, fn in getters.items():
        rows = fn()
        out[name] = max((int(r["id"]) for r in rows), default=0)
    return out


def new_since_last_seen():
    """Rows added since the last recorded visit, as (label, count, total)."""
    try:
        seen = json.loads(db.get_meta(LAST_SEEN_KEY) or "{}")
    except Exception:
        seen = {}
    if not isinstance(seen, dict):
        seen = {}
    getters = {"expenses": ("spent", db.get_expenses),
               "transport": ("transport", db.get_transport),
               "income": ("earned", db.get_income),
               "lent": ("lent out", db.get_lent),
               "borrowed": ("borrowed", db.get_borrowed)}
    fresh, first_visit = [], not seen
    for name, (label, fn) in getters.items():
        mark = int(seen.get(name, 0) or 0)
        rows = [r for r in fn() if int(r["id"]) > mark]
        if rows:
            fresh.append((label, len(rows), sum(float(r["amount"]) for r in rows)))
    return fresh, first_visit


def mark_seen() -> None:
    db.set_meta(LAST_SEEN_KEY, json.dumps(_current_max_ids()))


# ---- chats ----------------------------------------------------------------
# Conversations live in the meta table, not session_state alone: a refresh, or
# Streamlit dropping an idle session, used to throw them away. There are now
# several of them, each with a name, so a question about last month's food
# does not have to share a thread with a question about debts.
#
# Only role and content are stored. Attachment text and image bytes belong to
# the turn that sent them and would bloat the row for nothing.
CHATS_KEY = "chat_sessions"
ACTIVE_CHAT_KEY = "chat_active"
CHAT_LOG_KEY = "chat_log"          # the single log this replaced; migrated below
CHAT_LOG_MAX = 40
CHAT_NAME_MAX = 40


def _clean_messages(raw) -> list:
    if not isinstance(raw, list):
        return []
    return [{"role": m["role"], "content": m["content"]} for m in raw
            if isinstance(m, dict)
            and m.get("role") in ("user", "assistant")
            and isinstance(m.get("content"), str)]


def load_chats() -> list:
    """Every stored conversation, oldest first. Never returns an empty list —
    there is always at least one chat to be looking at."""
    raw = db.get_meta(CHATS_KEY)
    chats = []
    if raw:
        try:
            stored = json.loads(raw)
        except Exception:
            stored = []
        if isinstance(stored, list):
            for c in stored:
                if isinstance(c, dict) and c.get("id"):
                    chats.append({"id": str(c["id"]),
                                  "name": str(c.get("name") or "Chat")[:CHAT_NAME_MAX],
                                  "messages": _clean_messages(c.get("messages"))})
    if not chats:
        # Anything saved before chats existed becomes the first one, rather
        # than being silently dropped on upgrade.
        legacy = []
        old = db.get_meta(CHAT_LOG_KEY)
        if old:
            try:
                legacy = _clean_messages(json.loads(old))
            except Exception:
                legacy = []
        chats = [{"id": "1", "name": "Chat 1", "messages": legacy}]
    return chats


def save_chats(chats, active=None) -> None:
    try:
        trimmed = [{"id": c["id"], "name": c["name"][:CHAT_NAME_MAX],
                    "messages": c["messages"][-CHAT_LOG_MAX:]} for c in chats]
        db.set_meta(CHATS_KEY, json.dumps(trimmed))
        if active is not None:
            db.set_meta(ACTIVE_CHAT_KEY, str(active))
    except Exception:
        # A chat that cannot be saved must not take the board down with it.
        pass


def active_chat_id(chats) -> str:
    wanted = db.get_meta(ACTIVE_CHAT_KEY)
    ids = [c["id"] for c in chats]
    return wanted if wanted in ids else ids[0]


def save_chat() -> None:
    """Write the live conversation back into the chat it belongs to."""
    try:
        keep = [{"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
                if m.get("role") and isinstance(m.get("content"), str)]
        # A trailing user message is a question still being answered. Storing
        # it means every later page load sees an unanswered turn and fires the
        # API again to finish it — so a tab left open, or a refresh during a
        # slow reply, quietly spends quota on work already in flight. Only
        # settled exchanges are kept; the live one stays in session_state,
        # where the turn in progress still completes normally.
        while keep and keep[-1]["role"] == "user":
            keep.pop()
        chats = load_chats()
        current = st.session_state.get("chat_id") or active_chat_id(chats)
        for c in chats:
            if c["id"] == current:
                c["messages"] = keep
                break
        save_chats(chats, current)
    except Exception:
        pass


def new_chat_name(chats) -> str:
    used = {c["name"] for c in chats}
    n = len(chats) + 1
    while f"Chat {n}" in used:
        n += 1
    return f"Chat {n}"


def load_chat() -> list:
    """Messages of whichever chat is active — what the bot opens on."""
    chats = load_chats()
    current = active_chat_id(chats)
    for c in chats:
        if c["id"] == current:
            return list(c["messages"])
    return []


def _init_state():
    defaults = {
        "period": date.today().strftime("%Y-%m"),
        "bot_open": False,
        # Whether the rail was already open on the previous run, so the
        # entrance animation fires on the toggle and not on every rerun after.
        "bot_was_open": False,
        "messages": load_chat(),
        "chat_id": None,          # resolved on first render, below
        "partial": "",
        "stop": False,
        "flap_prev": {},
        "data_version": 0,
        "starter_slots": list(STARTER_OPENING),
        "starter_cursor": max(STARTER_OPENING) + 1,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _touch_data() -> None:
    """Call right before rerunning after any write to the ledgers, so the
    cached frames below are reloaded instead of serving stale data on every
    click for the rest of the session."""
    st.session_state.data_version += 1


_init_state()


@st.cache_data
def _load_frames_cached(version: int) -> finance.Frames:
    return finance.load_frames()


frames = _load_frames_cached(st.session_state.data_version)
# Set before a single figure is formatted. The ledger stays in PKR; this only
# decides what the board is read in, and get_rates() answers from a day-old
# cache unless the date has rolled over, so a page load costs no network call.
# What was already saved before this board existed. Seeds the first month's
# brought-forward rather than being logged as income, so it never shows up as
# money earned in a month that did not earn it.
finance.set_opening_balance(db.get_meta("opening_balance") or 0.0)
# Debts opened and cleared inside one month net to nothing, so by default they
# are kept out of the arrivals/departures headlines rather than inflating both.
finance.set_net_same_month_debts(
    (db.get_meta("net_same_month_debts") or "1") == "1")

CURRENCY = rates.get_currency()
FX = rates.get_rates()
CURRENCY_SYMBOL, CURRENCY_LABEL, _ = rates.CURRENCIES[CURRENCY]
finance.set_display_currency(CURRENCY, CURRENCY_SYMBOL,
                             rates.rate_for(CURRENCY, FX["rates"]))

series = finance.month_series(frames)
if st.session_state.period not in series and st.session_state.period != finance.ALL_TIME:
    st.session_state.period = date.today().strftime("%Y-%m")
snap = finance.snapshot(frames, st.session_state.period)
bot.bind_frames(frames)

HAS_DATA = frames.total_rows > 0
DEMO_ON = demo.is_active()


# ------------------------------------------------------------------ helpers

def html(*parts) -> None:
    """Emit raw HTML.

    Joined without newlines on purpose: Streamlit runs the string through a
    markdown pass first, and any line starting with four spaces would become a
    code block instead of layout.
    """
    st.markdown("".join(parts), unsafe_allow_html=True)


def cap(text: str, large: bool = False) -> str:
    """A section heading with its trailing rule.

    `large` is for the bot panel's own title, which heads a whole column
    rather than a group of fields and was sized for the latter. The sidebar
    headings keep the smaller size, so this cannot be a change to .ll-cap
    itself.
    """
    return f'<div class="ll-cap{" is-lg" if large else ""}">{text}</div>'


def to_pkr(amount: float) -> float:
    """A figure typed while the board is being read in another currency, back
    in the rupees everything is stored as. The inverse of finance.to_display —
    without it, "500" typed under a USD board would be banked as 500 rupees."""
    _, _, rate = finance.display_currency()
    return float(amount) * rate


def spacer(px: int) -> None:
    st.markdown(f'<div style="height:{px}px"></div>', unsafe_allow_html=True)


# What the board's four headline figures mean. This used to be a full-width
# panel above the board on first run; it lives in the bot rail now, shown while
# the chat is still empty, which is exactly when someone needs it and is the
# one place it costs no board space.
BOARD_LEGEND = (
    '<div class="ll-insight">'
    '<div class="ll-insight-head">How the board reads</div>'
    '<div class="ll-insight-row"><b>Brought forward</b>'
    '<span>What last month closed at.</span></div>'
    '<div class="ll-insight-row"><b>Arrivals</b>'
    '<span>Every rupee in &mdash; earned, returned to you, or borrowed.</span></div>'
    '<div class="ll-insight-row"><b>Departures</b>'
    '<span>Every rupee out &mdash; spent, lent, or repaid.</span></div>'
    '<div class="ll-insight-row"><b>On hand</b>'
    '<span>What is actually left to spend.</span></div>'
    '</div>')


# ---- chat attachment caps: session_state (and every future turn's prompt)
# holds these for the life of the session, so an uncapped receipt photo or a
# multi-thousand-row CSV paste would sit there at full size indefinitely. ----
_ATTACHMENT_MAX_LINES = 200
_ATTACHMENT_MAX_CHARS = 20_000
_IMAGE_MAX_DIM = 1600
_IMAGE_JPEG_QUALITY = 82


def cap_attachment_text(name: str, raw: bytes) -> str:
    text = raw.decode("utf-8", "ignore")
    lines = text.splitlines()
    truncated = len(lines) > _ATTACHMENT_MAX_LINES
    text = "\n".join(lines[:_ATTACHMENT_MAX_LINES])
    if len(text) > _ATTACHMENT_MAX_CHARS:
        text = text[:_ATTACHMENT_MAX_CHARS]
        truncated = True
    note = (f"\n[...truncated to the first {_ATTACHMENT_MAX_LINES} lines...]"
            if truncated else "")
    return f"\n=== {name} ===\n{text}{note}\n"


def downscale_image(raw: bytes, mime_type: str) -> tuple[bytes, str]:
    """Cap dimensions and re-encode so a full-resolution photo doesn't sit in
    session_state, and get re-sent to Gemini, at its original multi-megabyte
    size. Falls back to the original bytes if Pillow is unavailable or the
    file cannot be decoded as an image.
    """
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(raw))
        img.load()
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.thumbnail((_IMAGE_MAX_DIM, _IMAGE_MAX_DIM))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=_IMAGE_JPEG_QUALITY)
        return out.getvalue(), "image/jpeg"
    except Exception:
        return raw, mime_type or "image/jpeg"


CURRENT_PERIOD = date.today().strftime("%Y-%m")


def due_recurring() -> list:
    """Recurring templates whose day has arrived and that have not already
    been logged (or skipped) for the current calendar month."""
    today_day = date.today().day
    return [r for r in db.get_recurring()
            if r["last_logged"] != CURRENT_PERIOD and today_day >= r["day_of_month"]]


def figure_block(label, value, icon_name, tone="", note="", animate=False):
    note_html = f'<div class="ll-fig-note">{note}</div>' if note else ""
    return (f'<div class="ll-fig {tone}">'
            f'<div class="ll-fig-label">{icons.icon(icon_name, 13)}{label}</div>'
            f'<div class="ll-fig-value"><span class="cur">{esc(CURRENCY_SYMBOL)}</span>'
            f'{theme.flap_chars(finance.money_compact(value), animate)}</div>'
            f'{note_html}</div>')


# ================================================================= sidebar

with st.sidebar:
    html('<div class="ll-mast">',
         '<h1 class="ll-mast-name">LOOT<span class="ll-lamp"></span>LEDGER</h1>',
         '<div class="ll-mast-sub">Departures board</div>',
         '</div>')

    # st.button labels are plain markdown, not HTML — no inline SVG icon here,
    # unlike the rest of the board's controls which go through icons.icon().
    if st.button(f"{'☀ Light mode' if IS_DARK else '☾ Dark mode'}",
                 key="toggle_theme", width="stretch"):
        st.session_state.theme_mode = "light" if IS_DARK else "dark"
        st.query_params["theme"] = st.session_state.theme_mode
        st.rerun()

    # ---- record a movement -------------------------------------------------
    html(cap("Record a movement"))
    kind = st.selectbox("Movement", ["Expense", "Transport", "Income", "Lent out", "Borrowed"],
                        label_visibility="collapsed")

    with st.form("entry", clear_on_submit=True):
        # Inside the form so clear_on_submit resets it to today after every
        # entry — left outside, a backdated date silently kept applying to
        # every entry logged after it until someone noticed.
        when = st.date_input("Date", value=date.today(), format="DD/MM/YYYY")
        if when != date.today():
            st.caption(f"⚠️ Logging to {when.strftime('%d/%m/%Y')}, not today")

        if kind == "Expense":
            what = st.text_input("Description", placeholder="Karahi with the boys")
            where = st.selectbox("Platform", db.CATEGORIES)
            amount = st.number_input(f"Amount ({CURRENCY})", min_value=0.0, step=100.0, format="%.2f")
            if st.form_submit_button("Add departure", width="stretch", type="primary"):
                if what.strip() and amount > 0:
                    db.add_expense(str(when), what.strip(), where, to_pkr(amount))
                    _touch_data()
                    st.rerun()
                else:
                    st.warning("Needs a description and an amount above zero.")

        elif kind == "Transport":
            amount = st.number_input(f"Fare ({CURRENCY})", min_value=0.0, step=50.0, format="%.2f")
            if st.form_submit_button("Add departure", width="stretch", type="primary"):
                if amount > 0:
                    db.add_transport(str(when), to_pkr(amount))
                    _touch_data()
                    st.rerun()
                else:
                    st.warning("Needs an amount above zero.")

        elif kind == "Income":
            src = st.text_input("Source", placeholder="Monthly salary")
            amount = st.number_input(f"Amount ({CURRENCY})", min_value=0.0, step=1000.0, format="%.2f")
            if st.form_submit_button("Add arrival", width="stretch", type="primary"):
                if src.strip() and amount > 0:
                    db.add_income(str(when), src.strip(), to_pkr(amount))
                    _touch_data()
                    st.rerun()
                else:
                    st.warning("Needs a source and an amount above zero.")

        elif kind == "Lent out":
            who = st.text_input("Who took it", placeholder="Sara")
            amount = st.number_input(f"Amount ({CURRENCY})", min_value=0.0, step=500.0, format="%.2f")
            st.caption("Cash leaves you now and returns when they repay.")
            if st.form_submit_button("Record receivable", width="stretch", type="primary"):
                if who.strip() and amount > 0:
                    db.add_lent(str(when), who.strip(), to_pkr(amount))
                    _touch_data()
                    st.rerun()
                else:
                    st.warning("Needs a name and an amount above zero.")

        else:
            who = st.text_input("Who you owe", placeholder="Bhai")
            amount = st.number_input(f"Amount ({CURRENCY})", min_value=0.0, step=500.0, format="%.2f")
            st.caption("Cash arrives now and leaves again when you repay.")
            if st.form_submit_button("Record payable", width="stretch", type="primary"):
                if who.strip() and amount > 0:
                    db.add_borrowed(str(when), who.strip(), to_pkr(amount))
                    _touch_data()
                    st.rerun()
                else:
                    st.warning("Needs a name and an amount above zero.")

    # ---- the month rail: navigation that is already a chart ---------------
    html(cap("Service history"))

    rail_keys = sorted(series, reverse=True)[:10]
    # The active period must always show as selected, even if it has scrolled
    # out of the 10 most recent months — otherwise the board can be showing
    # one period while nothing in the sidebar looks selected at all.
    active_period = st.session_state.period
    if active_period in series and active_period not in rail_keys:
        rail_keys = sorted(set(rail_keys) | {active_period}, reverse=True)
    peak = max((series[k].outflow for k in rail_keys), default=0.0) or 1.0
    # These must out-rank theme.py's sidebar button skin. That rule is
    # !important and equally specific, and Streamlit puts the sidebar BEFORE
    # main in the DOM — so the stylesheet emitted "first" in the script actually
    # lands later in document order and would win a tie. Adding .stButton takes
    # the rail to (0,3,1) and settles it outright.
    SB = '[data-testid="stSidebar"] [class*="st-key-month_"] .stButton button'
    rail_css = [
        # A crisp tick at the end of each bar is what makes two near-equal
        # months readable as near-equal rather than as no encoding at all.
        SB + "{background:linear-gradient(90deg,"
        "rgba(var(--ink-rgb),0.20) 0%,"
        "rgba(var(--ink-rgb),0.20) calc(var(--fill,0%) - 2px),"
        "rgba(var(--ink-rgb),0.62) calc(var(--fill,0%) - 2px),"
        "rgba(var(--ink-rgb),0.62) var(--fill,0%),"
        "rgba(var(--ink-rgb),0.045) var(--fill,0%)) !important;"
        "border:1px solid transparent !important;border-radius:2px !important;"
        "min-height:32px !important;justify-content:flex-start !important;"
        "font-family:var(--font-board) !important;letter-spacing:0.07em !important;"
        "text-transform:uppercase !important;color:var(--ink-2) !important;}",
        SB + ":hover{border-color:var(--rule-2) !important;color:var(--ink) !important;}",
        SB + " p{width:100% !important;text-align:left !important;}",
    ]

    def rail_rule(key, body):
        safe = key.replace("-", "_")
        return (f'[data-testid="stSidebar"] .st-key-month_{safe} '
                f'.stButton button{{{body}}}')

    for key in rail_keys:
        pct = max(3.0, series[key].outflow / peak * 100.0)
        rail_css.append(rail_rule(key, f"--fill:{pct:.1f}%;"))
        if key == st.session_state.period:
            rail_css.append(rail_rule(key,
                "background:linear-gradient(90deg,"
                "rgba(var(--amber-rgb),0.32) 0%,"
                "rgba(var(--amber-rgb),0.32) calc(var(--fill,0%) - 2px),"
                "rgba(var(--amber-rgb),0.95) calc(var(--fill,0%) - 2px),"
                "rgba(var(--amber-rgb),0.95) var(--fill,0%),"
                "rgba(var(--amber-rgb),0.07) var(--fill,0%)) !important;"
                "color:var(--amber) !important;"
                "border-color:rgba(var(--amber-rgb),0.38) !important;"))
    if st.session_state.period == finance.ALL_TIME:
        rail_css.append(rail_rule("all",
            "background:rgba(var(--amber-rgb),0.18) !important;"
            "color:var(--amber) !important;"
            "border-color:rgba(var(--amber-rgb),0.38) !important;"))
    st.markdown(f"<style>{''.join(rail_css)}</style>", unsafe_allow_html=True)

    st.markdown('<div class="ll-railwrap">', unsafe_allow_html=True)
    for key in rail_keys:
        row = series[key]
        # The run of spaces that used to separate these collapsed to one in
        # markdown, so "AUG 26     52,479" rendered as "AUG 26 52,479" and the
        # year ran straight into the amount. An explicit separator survives.
        # Symbol comes from the active display currency — hardcoding "Rs"
        # here left the rail reading "RS 189.23" on a board showing dollars.
        label = (f"{finance.month_short(key)} {key[2:4]}: "
                 f"{CURRENCY_SYMBOL} {finance.money_compact(row.outflow)}")
        if st.button(label, key=f"month_{key.replace('-', '_')}", width="stretch"):
            st.session_state.period = key
            st.rerun()
    if st.button("ALL TIME", key="month_all", width="stretch"):
        st.session_state.period = finance.ALL_TIME
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    html('<div style="flex:1 1 auto;min-height:16px;"></div>',
         '<div style="border-top:1px solid var(--rule);padding-top:14px;',
         'font-size:0.6875rem;color:var(--ink-3);letter-spacing:0.06em;',
         'text-align:center;">',
         'Built by <a href="https://www.linkedin.com/in/muhammad-ali-akbar-khan-7b37b8197" ',
         'target="_blank" rel="noopener">Muhammad Ali Akbar</a></div>')


# ================================================================== layout

# Both columns are created every run, open or closed. Swapping between a bare
# st.container() and st.columns() — which is what used to happen here — hands
# React two structurally different trees, so the entire board was unmounted and
# rebuilt on every toggle: the screen recording shows three frames of blank
# page mid-flip. Keeping one shape means the board's DOM survives the toggle
# and only the rail's width changes, which CSS can animate instead of jumping.
# The rail is left empty when closed, so nothing renders that cannot be seen.
stage, rail_column = st.columns([2.55, 1], gap="medium")
# The rail always gets a child, even shut. Streamlit collapses a column with no
# content to display:none, and an element on its way to display:none cannot
# transition — which is exactly why closing snapped shut while opening eased.
with rail_column:
    st.markdown('<div class="ll-rail-anchor"></div>', unsafe_allow_html=True)
rail = rail_column if st.session_state.bot_open else None
if not st.session_state.bot_open:
    st.markdown(f"<style>{theme.BOT_CLOSED_CSS}</style>", unsafe_allow_html=True)
_was_open = st.session_state.bot_was_open
st.session_state.bot_was_open = st.session_state.bot_open

with stage:
    # Anchors the width rules above onto this specific row: the page has other
    # horizontal blocks (the toolbar, the figure strip) that must not collapse.
    st.markdown('<div class="ll-stage-marker"></div>', unsafe_allow_html=True)
    # The full-width "board is empty" explainer that used to sit here has moved
    # into the bot rail as an insight card (BOARD_LEGEND above). The board's own
    # empty columns already say the board is empty, so repeating it in a large
    # panel above them pushed the real board below the fold on first run and
    # read as filler. The one action worth offering moved into the toolbar row
    # below, so nothing floats above the controls.
    # ---- what changed since the last visit ------------------------------
    fresh_rows, first_visit = new_since_last_seen()
    if fresh_rows and not first_visit:
        summary = " &middot; ".join(
            f"{count} {label} {finance.money(total, 0)}"
            for label, count, total in fresh_rows)
        html('<div class="ll-since">',
             f'<div class="ll-since-title">{icons.icon("clock", 14)}'
             'Since you last looked</div>',
             f'<div class="ll-since-body">{summary}</div></div>')
        sc_a, _ = st.columns([1.5, 8.5])
        with sc_a:
            if st.button("Mark as seen", key="mark_seen", width="stretch"):
                mark_seen()
                st.rerun()
    elif first_visit:
        # Nothing to compare against yet; record the starting point quietly so
        # the first real visit has a baseline instead of announcing the whole
        # ledger as new.
        mark_seen()

    if DEMO_ON:
        html('<div class="ll-demo">', icons.icon("info", 15),
             'Sample data &mdash; <span>these figures are generated for demonstration, '
             'not real records. Clear them from Settings.</span></div>')

    # ---- monthly digest: one bot call on the first load of a new month -----
    # Set to last month's period key when a digest still needs generating; the
    # actual call runs at the very bottom of this script so it cannot delay the
    # board. None means there is nothing to generate this run.
    digest_job = None
    if db.get_meta("digest_dismissed_for") != CURRENT_PERIOD:
        last_month_key = finance.shift_month(CURRENT_PERIOD, -1)
        last_month_row = series.get(last_month_key)
        if last_month_row and (last_month_row.inflow or last_month_row.outflow):
            # Generating the digest calls Gemini. Doing that here, inline, held
            # the whole script on a spinner: Streamlit paints elements in the
            # order they are created, so on the first load of a new month the
            # entire board stayed blank for as long as the API took to answer.
            # The work is deferred to the end of the script and dropped into
            # this reserved slot on the rerun after, which leaves the board
            # rendering at its normal speed on every load.
            if db.get_meta("digest_period") != CURRENT_PERIOD:
                digest_job = last_month_key

            digest_text = db.get_meta("digest_text")
            if digest_text and not digest_job:
                # The digest is bot-generated, not typed by the user, but it can
                # still echo ledger text (descriptions, names) verbatim — same
                # unescaped-HTML risk as the board rows, so it gets the same fix.
                digest_html = esc(digest_text).replace("\n", "<br>")
                html('<div class="ll-panel ll-digest"><div class="ll-panel-head">',
                     f'<div class="ll-panel-title">{icons.icon("sheet", 15)}'
                     f'{finance.month_label(last_month_key)} digest</div></div>',
                     f'<div class="ll-panel-body">{digest_html}</div></div>')
                dc1, _ = st.columns([1.4, 8.6])
                with dc1:
                    if st.button("Dismiss", key="dismiss_digest", width="stretch"):
                        db.set_meta("digest_dismissed_for", CURRENT_PERIOD)
                        st.rerun()
                spacer(16)

    due = due_recurring()
    if due:
        total_due = sum(r["amount"] for r in due)
        rows_html = "".join(
            f'<div class="ll-recur-item">{esc(r["label"])}'
            f'<span class="sub">{esc(r["category"] or r["kind"].title())}</span>'
            f'<span class="amt">{finance.money(r["amount"], 0)}</span></div>'
            for r in due
        )
        html('<div class="ll-panel ll-recur"><div class="ll-panel-head">',
             f'<div class="ll-panel-title">{icons.icon("refresh", 15)}'
             f'{len(due)} recurring due this month</div>',
             f'<div class="ll-col-sum">{finance.money(total_due, 0)}</div></div>',
             f'<div class="ll-panel-body">{rows_html}</div></div>')
        rc1, rc2, _ = st.columns([1.4, 1.6, 6.0])
        with rc1:
            if st.button("Log all", key="recur_log_all", type="primary", width="stretch"):
                for r in due:
                    if r["kind"] == "income":
                        db.add_income(str(date.today()), r["label"], r["amount"])
                    else:
                        db.add_expense(str(date.today()), r["label"],
                                       r["category"] or "Other", r["amount"])
                    db.mark_recurring_logged(r["id"], CURRENT_PERIOD)
                _touch_data()
                st.rerun()
        with rc2:
            if st.button("Not this month", key="recur_skip", width="stretch"):
                for r in due:
                    db.mark_recurring_logged(r["id"], CURRENT_PERIOD)
                st.rerun()
        spacer(16)

    # Built here so it renders in the empty band above the controls, which
    # was carrying nothing but page padding. Its 400-line body still lives
    # further down and simply fills this object, so nothing had to be
    # re-indented to move it up.
    ledgers_menu = st.expander("Ledgers, debts and import")

    ctl_a, ctl_b, ctl_c, _ = st.columns([1.5, 1.2, 1.7, 5.6])
    with ctl_a:
        if st.button("Close bot" if st.session_state.bot_open else "Finance bot",
                     key="toggle_bot", width="stretch"):
            st.session_state.bot_open = not st.session_state.bot_open
            st.rerun()
    with ctl_b:
        settings_open = st.button("Settings", key="open_settings", width="stretch")
    with ctl_c:
        # Only offered while there is nothing to lose: seeding refuses to mix
        # sample rows into real ones anyway. Sitting in the toolbar keeps the
        # empty board's one call to action on the same line as the controls.
        if not HAS_DATA and st.button("Load sample data", key="firstrun_demo",
                                      type="primary", width="stretch"):
            demo.seed()
            _touch_data()
            st.rerun()

    # ================================================================ board
    status_word = {"on-time": "On track", "delayed": "Running warm",
                   "cancelled": "Over budget", "quiet": "No service"}[snap.status]

    # The four figures are one equation: brought forward + arrivals - departures
    # = on hand. That only holds if "arrivals" means every rupee that came in,
    # settlements included - which is also what the Arrivals column lists. The
    # earlier version showed income here and all-cash-in below, so the same word
    # carried two different numbers 40px apart.
    arrivals_total = snap.inflow + snap.row.lent_returned + snap.row.borrowed_in
    departures_total = snap.outflow + snap.row.lent_out + snap.row.borrowed_repaid

    figures = {
        "opening": finance.money_compact(snap.opening),
        "in": finance.money_compact(arrivals_total),
        "out": finance.money_compact(departures_total),
        "hand": finance.money_compact(snap.on_hand),
    }
    changed = st.session_state.flap_prev != figures
    st.session_state.flap_prev = figures

    delta = snap.outflow_delta_pct
    if not snap.has_activity:
        out_note = "nothing recorded yet"
    elif delta is None:
        out_note = f'<b>{finance.money(snap.outflow, 0)}</b> of it spending'
    elif abs(delta) < 1:
        out_note = f'level with {finance.month_label(snap.prev_key)}'
    else:
        arrow = "up" if delta >= 0 else "down"
        sign = "+" if delta >= 0 else "&minus;"
        out_note = (f'spending <span class="{arrow}">{sign}{abs(delta):.0f}%</span> '
                    f'vs {finance.month_label(snap.prev_key)}')

    settled_in = snap.row.lent_returned + snap.row.borrowed_in
    if settled_in > 0:
        in_note = (f'<b>{finance.money(snap.inflow, 0)}</b> earned + '
                   f'{finance.money(settled_in, 0)} settled')
    else:
        in_note = f'{len(snap.arrivals)} movement(s) inward'

    brought_note = (f"closing balance of {finance.month_label(snap.prev_key)}"
                    if snap.prev_key else "no earlier month on record")
    hand_note = (f"<b>{snap.savings_rate:.0f}%</b> of income kept"
                 if snap.inflow > 0 else "nothing arrived this period")

    parts = [
        '<div class="ll-board">',
        '<div class="ll-service"><div class="ll-service-left">',
        f'<div class="ll-service-period">{snap.label}</div>',
        f'<div class="ll-service-meta">{len(snap.arrivals)} arrivals &middot; '
        f'{len(snap.departures)} departures</div></div>',
        f'<div class="ll-status {snap.status}"><span class="dot"></span>{status_word}</div>',
        '</div>',
        f'<div class="ll-figures{" is-flipping" if changed else ""}">',
        figure_block("Brought forward", snap.opening, "history", "is-muted",
                     brought_note, changed),
        figure_block("Arrivals", arrivals_total, "arrival", "", in_note, changed),
        figure_block("Departures", departures_total, "departure", "", out_note, changed),
        figure_block("On hand", snap.on_hand, "wallet",
                     "is-neg" if snap.on_hand < 0 else "", hand_note, changed),
        '</div>',
        '<div class="ll-cols">',
    ]

    # ---- remove an entry -------------------------------------------------
    # Two kinds of row live on this board. Five are records in their own right
    # and are deleted. The other two — a repayment on a debt you lent or
    # borrowed — are not records at all; they are the settled half of an
    # existing debt. Deleting the debt to undo its repayment would throw away
    # the loan as well, so those are un-settled instead, which is what
    # "remove this repayment" actually means.
    SETTLEMENT_KINDS = {"lent_returned": "lent", "borrowed_repaid": "borrowed"}
    RECORD_KINDS = {"expense": "expenses", "transport": "transport",
                    "income": "income", "lent": "lent", "borrowed": "borrowed"}

    pending_removal = st.session_state.get("pending_remove")
    if pending_removal:
        kind, _, raw_id = str(pending_removal).rpartition("_")
        target = None
        if raw_id.isdigit() and (kind in RECORD_KINDS or kind in SETTLEMENT_KINDS):
            wanted = int(raw_id)
            for frame in (snap.arrivals, snap.departures):
                for row in frame.to_dict("records"):
                    if row["kind"] == kind and int(row["id"]) == wanted:
                        target = row
                        break
        if target is None:
            st.session_state.pop("pending_remove", None)
        else:
            undo = kind in SETTLEMENT_KINDS
            verb = ("Mark this repayment as not settled?" if undo
                    else "Remove this entry for good?")
            html('<div class="ll-confirm">',
                 f'<div class="ll-confirm-title">{icons.icon("alert", 14)}{verb}</div>',
                 f'<div class="ll-confirm-body">{esc(str(target["label"]))} '
                 f'&mdash; {finance.money(float(target["amount"]))} on '
                 f'{finance.display_date(target["date"])}'
                 + ('. The debt itself is kept; only the repayment is undone.'
                    if undo else '. This cannot be undone.')
                 + '</div></div>')
            rm1, rm2, _ = st.columns([1.5, 1.2, 7.3])
            with rm1:
                if st.button("Remove" if not undo else "Un-settle",
                             type="primary", width="stretch", key="confirm_remove"):
                    if undo:
                        db.set_paid_back(SETTLEMENT_KINDS[kind], int(target["id"]),
                                         False, None)
                    else:
                        db.delete_row(RECORD_KINDS[kind], int(target["id"]))
                    st.session_state.pop("pending_remove", None)
                    _touch_data()
                    st.rerun()
            with rm2:
                if st.button("Cancel", width="stretch", key="cancel_remove"):
                    st.session_state.pop("pending_remove", None)
                    st.rerun()

    # ---- search ---------------------------------------------------------
    # A month of entries is only ever read by scrolling, so finding one
    # remembered purchase means scanning every row. Matches detail and
    # platform, and reports what it did: a search returning nothing must not
    # look the same as a month with nothing in it.
    sc1, sc2 = st.columns([3, 7])
    with sc1:
        query = st.text_input(
            "Search entries", key="board_search", placeholder="Search entries…",
            label_visibility="collapsed").strip()

    board_arrivals, board_departures = snap.arrivals, snap.departures
    if query:
        def matching(frame):
            if frame.empty:
                return frame
            needle = query.lower()
            hit = (frame["label"].astype(str).str.lower().str.contains(needle, regex=False)
                   | frame["platform"].astype(str).str.lower().str.contains(needle, regex=False))
            return frame[hit]
        board_arrivals = matching(snap.arrivals)
        board_departures = matching(snap.departures)
        found = len(board_arrivals) + len(board_departures)
        shown = finance.money(
            board_arrivals["amount"].sum() + board_departures["amount"].sum(), 0)
        with sc2:
            if found:
                st.caption(f"{found} entr{'y' if found == 1 else 'ies'} matching "
                           f"“{query}” — {shown} in total. Clear the box to see "
                           f"the whole month.")
            else:
                st.caption(f"Nothing in {finance.month_label(snap.key)} matches "
                           f"“{query}”. The month is not empty — the search is.")

    # Both columns always render exactly pad_to row-slots — real rows, then an
    # overflow marker if the column has more than fit, then blank flaps to
    # fill the rest. Padding the short side up to a cap while leaving the long
    # side unbounded (the previous behaviour) broke parity the moment one side
    # had more than pad_to rows: the long column just kept growing past it.
    pad_to = min(max(len(board_arrivals), len(board_departures)), 7)

    def board_column(title, icon_name, css_class, rows, total):
        out = [f'<div class="ll-col {css_class}"><div class="ll-col-head">',
               f'<div class="ll-col-title">{icons.icon(icon_name, 15)}{title}</div>',
               f'<div class="ll-col-sum">{finance.money(total, 0)}</div></div>']
        if rows.empty:
            verb = "arrived" if css_class == "arrivals" else "departed"
            out += ['<div class="ll-empty">', icons.icon("board", 26),
                    f'<div class="ll-empty-title">Nothing {verb}</div>',
                    '<div class="ll-empty-body">Record a movement from the sidebar, '
                    'or tell the bot what happened in plain words.</div></div>']
        else:
            # Every row, always. The list is a scroll container (max-height
            # plus overflow-y in .ll-rows), so a long month is read by
            # scrolling it rather than being cut off at seven and handed a
            # button. `is-short` only suppresses the fade mask, so it goes on
            # when the rows genuinely fit and there is nothing to scroll to.
            visible = rows
            short = len(rows) <= pad_to
            # A hidden checkbox and its label make the list expand in place,
            # in the browser, with no rerun and no navigation. A Streamlit
            # button cannot be nested in this HTML block, and the anchor that
            # replaced it reloaded the whole dashboard just to show rows that
            # were already on the page. It must come BEFORE the list so the
            # sibling selectors in the stylesheet can reach it.
            if not short:
                out.append(f'<input type="checkbox" class="ll-expand" '
                           f'id="ll-expand-{css_class}">')
            out.append(f'<div class="ll-rows{" is-short" if short else ""}">')
            for r in visible.to_dict("records"):
                colour = theme.platform_color(r["platform"])
                # No href. An anchor navigates, and navigating reloads the
                # whole dashboard just to select a row that is already on the
                # page. This carries its identity in a data attribute instead;
                # the bridge below forwards the click to a real (off-screen)
                # Streamlit button, which reruns the script the same way any
                # other widget does — fast, and with no page load.
                out.append(
                    f'<div class="ll-row is-clickable" role="button" tabindex="0" '
                    f'data-rm="{r["kind"]}_{r["id"]}" '
                    f'title="Click to remove this entry">'
                    f'<div class="ll-row-time">{finance.day_month(r["date"])}</div>'
                    f'<div class="ll-plat" style="background:{colour}">'
                    f'{theme.platform_code(r["platform"])}</div>'
                    f'<div class="ll-row-label">{esc(str(r["label"]))}'
                    f'<span class="sub">{esc(str(r["platform"]))}</span></div>'
                    f'<div class="ll-row-amt">{finance.money(float(r["amount"]), 0)}</div>'
                    f'</div>')
            # Padding still keeps a short column from collapsing next to a
            # long one; it just never has to stand in for hidden rows now.
            for _ in range(max(0, pad_to - len(visible))):
                out.append('<div class="ll-row is-blank" aria-hidden="true">'
                           '<div class="ll-blank-tile"></div></div>')
            out.append('</div>')
            # Sits below the list but inside the panel: at full contrast, in
            # view without scrolling, and it opens the rest of THIS column
            # rather than sending you to another table.
            if not short:
                out.append(
                    f'<label class="ll-row-more" for="ll-expand-{css_class}">'
                    f'<span class="ll-row-more-label more-open">'
                    f'Show all {len(rows)} {title.lower()}</span>'
                    f'<span class="ll-row-more-label more-close">'
                    f'Show fewer</span></label>')
        out.append('</div>')
        return "".join(out)

    parts.append(board_column("Arrivals", "arrival", "arrivals",
                              board_arrivals, arrivals_total))
    parts.append(board_column("Departures", "departure", "departures",
                              board_departures, departures_total))
    parts += ['</div>', '</div>']
    html(*parts)

    # ---- click bridge ----------------------------------------------------
    # One real Streamlit button per visible row, parked off-screen, plus a
    # small script that forwards a click on the row to its button. That turns
    # selecting a row into an ordinary widget interaction — a rerun, not the
    # full page load an <a href> was causing.
    #
    # Off-screen rather than display:none: a button that is not rendered
    # cannot be clicked programmatically. The script lives in a components
    # iframe because Streamlit strips <script> from markdown; the iframe is
    # same-origin, so it can reach the board in the parent document.
    for r in pd.concat([board_arrivals, board_departures]).to_dict("records"):
        token = f'{r["kind"]}_{r["id"]}'
        if st.button("remove", key=f"rm_{token}"):
            st.session_state.pending_remove = token
            st.rerun()

    # st.components.v1.html is deprecated (removal was scheduled for
    # 2026-06-01), so the bridge lives in bridge.html and is loaded with
    # st.iframe. It is served from the app's own origin, which is what lets it
    # reach the board in the parent document — verified, not assumed.
    # height=1, not 0: st.iframe rejects zero, where components.html allowed
    # it. The container is collapsed in the stylesheet instead, so the bridge
    # takes no space on the page.
    st.iframe(pathlib.Path(__file__).parent / "bridge.html", height=1)

    # ============================================================== panels
    spacer(4)
    p1, p2 = st.columns([1.35, 1], gap="medium")

    with p1:
        load = ['<div class="ll-panel"><div class="ll-panel-head">',
                f'<div class="ll-panel-title">{icons.icon("platform", 15)}Platform load</div>',
                f'<div class="ll-col-sum">{finance.money(snap.outflow, 0)}</div>',
                '</div><div class="ll-panel-body">']
        if snap.by_category.empty:
            load += ['<div class="ll-empty">', icons.icon("platform", 26),
                     '<div class="ll-empty-title">No departures yet</div>',
                     '<div class="ll-empty-body">Spending splits by platform here '
                     'once the board has something on it.</div></div>']
        else:
            total = float(snap.by_category["amount"].sum()) or 1.0
            donut = theme.donut_svg(
                snap.by_category.to_dict("records"), total,
                center_label=finance.money_compact(total),
                amount_fmt=lambda v: finance.money(v, 0),
            )
            # A monthly cap only makes sense against a monthly total, not an
            # all-time one, so budgets only ever show up on a real month.
            budgets = db.get_budgets() if snap.key != finance.ALL_TIME else {}
            load.append('<div class="ll-load">'
                        f'<div class="ll-donut-wrap">{donut}</div>'
                        '<div class="ll-load-list">')
            for r in snap.by_category.to_dict("records"):
                category = str(r["category"])
                spent = float(r["amount"])
                share = spent / total * 100
                colour = theme.platform_color(category)
                load.append('<div class="ll-load-row">')
                load.append(
                    f'<div class="ll-load-item">'
                    f'<div class="ll-plat" style="background:{colour}">'
                    f'{theme.platform_code(category)}</div>'
                    f'<div class="ll-load-name">{esc(category)}</div>'
                    f'<div class="ll-load-pct">{share:.0f}%</div>'
                    f'<div class="ll-load-amt">{finance.money(spent, 0)}</div>'
                    f'</div>')
                # Named budget_cap, not cap: this script runs top to bottom in
                # one namespace, and `cap` is the section-heading helper defined
                # above. Binding it here replaced that function for every line
                # that followed, so the bot panel's own cap() call further down
                # raised TypeError and the whole rail rendered empty.
                budget_cap = budgets.get(category)
                if budget_cap:
                    used = spent / budget_cap
                    tone = ("var(--departure)" if used >= 0.9 else
                            "var(--amber)" if used >= 0.7 else "var(--arrival)")
                    load.append(
                        '<div class="ll-load-cap">'
                        f'<div class="ll-load-cap-track"><div class="ll-load-cap-fill" '
                        f'style="width:{min(used * 100, 100):.1f}%;background:{tone}">'
                        f'</div></div>'
                        f'<div class="ll-load-cap-label">{finance.money(spent, 0)} / '
                        f'{finance.money(budget_cap, 0)} cap</div></div>')
                load.append('</div>')
            load.append('</div></div>')
        load += ['</div></div>']
        html(*load)

    with p2:
        pct = snap.burn_pct
        meter_colour = ("var(--departure)" if pct >= 90 else
                        "var(--amber)" if pct >= 70 else "var(--arrival)")
        available = snap.opening + snap.inflow

        # Only meaningful for the month actually in progress — a past month
        # has no "days remaining" left to pace out, and All Time has no close.
        projection_html = ""
        if snap.key == CURRENT_PERIOD:
            today = date.today()
            days_elapsed = today.day
            days_in_month = calendar.monthrange(today.year, today.month)[1]
            days_remaining = days_in_month - days_elapsed
            daily_burn = snap.outflow / days_elapsed if days_elapsed else 0.0
            projected_close = snap.on_hand - daily_burn * days_remaining
            close_tone = "var(--departure)" if projected_close < 0 else "var(--ink-2)"
            projection_html = (
                '<div class="ll-meter-foot">Pacing at '
                f'<b>{finance.money(daily_burn, 0)}</b>/day &mdash; projected to close the '
                f'month at <b style="color:{close_tone}">'
                f'{finance.money(projected_close, 0)}</b> with {days_remaining} '
                f'day{"s" if days_remaining != 1 else ""} left.</div>'
            )

        html('<div class="ll-panel"><div class="ll-panel-head">',
             f'<div class="ll-panel-title">{icons.icon("coins", 15)}Capacity</div>',
             '</div><div class="ll-panel-body"><div class="ll-meter-top">',
             f'<div class="ll-meter-pct">{pct:.0f}%</div>',
             '<div class="ll-meter-cap">of available cash spent</div></div>',
             '<div class="ll-meter-track">',
             f'<div class="ll-meter-fill" style="width:{min(pct, 100):.1f}%;'
             f'background:{meter_colour}"></div>',
             '<div class="ll-meter-mark" style="left:70%"></div>',
             '<div class="ll-meter-mark" style="left:90%"></div></div>',
             f'<div class="ll-meter-foot"><b>{finance.money(snap.outflow, 0)}</b> spent of '
             f'<b>{finance.money(available, 0)}</b> available '
             f'({finance.money(snap.opening, 0)} carried in + '
             f'{finance.money(snap.inflow, 0)} arrived)</div>',
             projection_html,
             '</div></div>')

        spacer(16)
        html('<div class="ll-panel"><div class="ll-oblig">',
             '<div class="ll-oblig-cell owed-to-me">',
             f'<div class="ll-oblig-label">{icons.icon("receivable", 13)}Owed to you</div>',
             f'<div class="ll-oblig-value">{finance.money(snap.receivable_open, 0)}</div>',
             f'<div class="ll-oblig-note">{snap.receivable_count} unsettled</div></div>',
             '<div class="ll-oblig-cell owed-by-me">',
             f'<div class="ll-oblig-label">{icons.icon("payable", 13)}You owe</div>',
             f'<div class="ll-oblig-value">{finance.money(snap.payable_open, 0)}</div>',
             f'<div class="ll-oblig-note">{snap.payable_count} unsettled</div></div>',
             '</div></div>')

    # ---- the run strip -----------------------------------------------------
    if HAS_DATA and len(series) > 1:
        spacer(20)
        SLOTS = 12
        keys = sorted(series)[-SLOTS:]
        span = len(keys)
        title = "Last 12 months" if span >= SLOTS else f"Last {span} months"
        peak_out = max((series[k].outflow for k in keys), default=0.0) or 1.0

        strip = ['<div class="ll-panel"><div class="ll-panel-head">',
                 f'<div class="ll-panel-title">{icons.icon("clock", 15)}{title}</div>',
                 f'<div class="ll-col-sum">on hand '
                 f'{finance.money(series[keys[-1]].closing, 0)}</div>',
                 '</div><div class="ll-run">']
        # The track always holds twelve slots. A three-month history then reads
        # as three of twelve on a board with room to fill, which is what the
        # empty slots on a real board mean — capping the column width instead
        # left the columns adrift in a half-empty panel.
        for _ in range(SLOTS - span):
            strip.append('<div class="ll-run-col is-vacant" aria-hidden="true">'
                         '<div class="ll-run-track"></div>'
                         '<div class="ll-run-foot">&middot;</div></div>')
        for key in keys:
            row = series[key]
            height = max(2.0, row.outflow / peak_out * 100.0)
            current = " is-current" if key == snap.key else ""
            strip.append(
                f'<div class="ll-run-col{current}">'
                f'<div class="ll-run-track">'
                f'<div class="ll-run-fill" style="height:{height:.1f}%"></div>'
                f'</div>'
                f'<div class="ll-run-foot">{finance.month_short(key)} {key[2:4]}'
                f'<span>{finance.money_compact(row.closing)}</span></div>'
                f'</div>')
        strip.append('</div>')
        # One quantity, one scale. The closing balance rides as a figure under
        # each column rather than a second line on a second axis, so nothing on
        # this strip invites a comparison the scale does not support.
        strip.append('<div class="ll-run-key">'
                     '<span><i class="k-out"></i>Column height &mdash; departures</span>'
                     '<span><i class="k-now"></i>This period</span>'
                     '<span>Figure beneath &mdash; cash on hand at close</span>'
                     '</div>')
        strip.append('</div>')
        html(*strip)

    # ============================================== ledgers / debts / import
    spacer(12)
    with ledgers_menu:
        t_led, t_edit, t_debt, t_imp = st.tabs(["Ledgers", "Edit", "Debts", "Import"])

        with t_led:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Departures**")
                if snap.departures.empty:
                    st.caption("Nothing recorded for this period.")
                else:
                    out = snap.departures[["date", "label", "platform", "amount"]].copy()
                    out["date"] = out["date"].map(finance.display_date)
                    # Converted here too, and the column says which currency —
                    # an exported file that just says "Amount" is ambiguous the
                    # moment the board is read in anything but rupees.
                    out["amount"] = out["amount"].map(finance.to_display)
                    out = out.rename(columns={"date": "Date", "label": "Detail",
                                              "platform": "Platform",
                                              "amount": f"Amount ({CURRENCY})"})
                    st.dataframe(out, column_config={f"Amount ({CURRENCY})":
                        st.column_config.NumberColumn(f"Amount ({CURRENCY})",
                        format=f"{CURRENCY_SYMBOL} %.2f")}, width="stretch", hide_index=True)
                    st.download_button("Export departures", out.to_csv(index=False).encode(),
                                       f"loot_ledger_departures_{snap.key}.csv", "text/csv",
                                       width="stretch", key="dl_out")
            with c2:
                st.markdown("**Arrivals**")
                if snap.arrivals.empty:
                    st.caption("Nothing recorded for this period.")
                else:
                    inn = snap.arrivals[["date", "label", "platform", "amount"]].copy()
                    inn["date"] = inn["date"].map(finance.display_date)
                    # Converted here too, and the column says which currency —
                    # an exported file that just says "Amount" is ambiguous the
                    # moment the board is read in anything but rupees.
                    inn["amount"] = inn["amount"].map(finance.to_display)
                    inn = inn.rename(columns={"date": "Date", "label": "Detail",
                                              "platform": "Platform",
                                              "amount": f"Amount ({CURRENCY})"})
                    st.dataframe(inn, column_config={f"Amount ({CURRENCY})":
                        st.column_config.NumberColumn(f"Amount ({CURRENCY})",
                        format=f"{CURRENCY_SYMBOL} %.2f")}, width="stretch", hide_index=True)
                    st.download_button("Export arrivals", inn.to_csv(index=False).encode(),
                                       f"loot_ledger_arrivals_{snap.key}.csv", "text/csv",
                                       width="stretch", key="dl_in")

        with t_edit:
            st.caption("Fix a typo, correct an amount, or drop a row entirely. "
                       "Entries could only be added and deleted before, so a "
                       "mistyped figure meant deleting the row and typing it "
                       "again. Edits are written when you press Save.")
            ledger_labels = {"expenses": "Expenses", "transport": "Transport",
                             "income": "Income", "lent": "Lent out",
                             "borrowed": "Borrowed"}
            which = st.selectbox("Ledger", list(ledger_labels),
                                 format_func=lambda k: ledger_labels[k],
                                 key="edit_ledger")
            getter = {"expenses": db.get_expenses, "transport": db.get_transport,
                      "income": db.get_income, "lent": db.get_lent,
                      "borrowed": db.get_borrowed}[which]
            records = getter()
            if not records:
                st.caption(f"Nothing in {ledger_labels[which].lower()} yet.")
            else:
                frame = pd.DataFrame(records)
                editable_cols = list(db.EDITABLE[which])
                view = frame[["id"] + editable_cols].copy()
                # Shown and typed in whatever the board is being read in; the
                # save below converts back, so a figure edited under a USD
                # board is not banked as rupees.
                view["amount"] = view["amount"].map(finance.to_display)
                config = {
                    "id": st.column_config.NumberColumn("id", disabled=True, width="small"),
                    "date": st.column_config.TextColumn("Date (YYYY-MM-DD)"),
                    "amount": st.column_config.NumberColumn(
                        f"Amount ({CURRENCY})", format="%.2f", min_value=0.0),
                }
                if "category" in editable_cols:
                    config["category"] = st.column_config.SelectboxColumn(
                        "Category", options=db.CATEGORIES)
                if "paid_back" in editable_cols:
                    config["paid_back"] = st.column_config.CheckboxColumn("Settled")
                edited = st.data_editor(
                    view, column_config=config, hide_index=True, width="stretch",
                    num_rows="dynamic", key=f"edit_{which}_{st.session_state.data_version}")

                if st.button("Save changes", type="primary", width="stretch",
                             key=f"save_edit_{which}"):
                    before = {r["id"]: r for r in records}
                    kept, changed, removed = set(), 0, 0
                    for row in edited.to_dict("records"):
                        rid = row.get("id")
                        if rid is None or pd.isna(rid):
                            continue          # a blank row typed into the grid
                        rid = int(rid)
                        kept.add(rid)
                        original = before.get(rid)
                        if original is None:
                            continue
                        updates = {}
                        for col in editable_cols:
                            new_value = row.get(col)
                            if col == "amount":
                                new_value = to_pkr(float(new_value or 0))
                                if abs(new_value - float(original["amount"])) > 0.005:
                                    updates[col] = new_value
                            elif col == "paid_back":
                                new_value = 1 if new_value else 0
                                if new_value != int(original.get("paid_back") or 0):
                                    updates[col] = new_value
                            else:
                                new_value = "" if new_value is None else str(new_value)
                                if new_value != str(original.get(col) or ""):
                                    updates[col] = new_value
                        if updates:
                            db.update_row(which, rid, **updates)
                            changed += 1
                    # A row deleted in the grid simply stops appearing in it.
                    for rid in before:
                        if rid not in kept:
                            db.delete_row(which, rid)
                            removed += 1
                    if changed or removed:
                        _touch_data()
                        st.success(f"{changed} row(s) updated, {removed} deleted.")
                        st.rerun()
                    else:
                        st.caption("Nothing changed.")

        with t_debt:
            st.caption("Ticking Settled records the repayment as today's cash movement, "
                       "so it lands in this month's figures.")
            d1, d2 = st.columns(2)
            for column, table, name_col, heading in (
                (d1, "lent", "person", "Owed to you"),
                (d2, "borrowed", "lender", "You owe"),
            ):
                with column:
                    st.markdown(f"**{heading}**")
                    source = frames.lent if table == "lent" else frames.borrowed
                    if source.empty:
                        st.caption("Nothing on the books.")
                        continue
                    view = source[["id", "date", name_col, "amount", "paid_back"]].copy()
                    view["days"] = view["date"].map(
                        lambda d: (date.today()
                                  - datetime.strptime(str(d)[:10], "%Y-%m-%d").date()).days)

                    # st.data_editor does not support pandas Styler (that's
                    # read-only-dataframe only), so aging past the threshold
                    # surfaces here instead — the same departure tone used for
                    # is-neg elsewhere — with the numeric column still living
                    # in the editable grid below for anyone who wants the raw count.
                    overdue = view[(view["paid_back"] == 0) & (view["days"] > 30)]
                    if not overdue.empty:
                        html(f'<div class="ll-aging-head">{icons.icon("alert", 13)}'
                             f'{len(overdue)} unsettled over 30 days</div>')
                        for r in overdue.sort_values("days", ascending=False).to_dict("records"):
                            ov1, ov2 = st.columns([2.6, 1.4])
                            with ov1:
                                html(f'<div class="ll-aging-row">{esc(str(r[name_col]))}'
                                    f'<span class="amt">{finance.money(float(r["amount"]), 0)}</span>'
                                    f'<span class="days">{r["days"]}d</span></div>')
                            with ov2:
                                verb = "owes you" if table == "lent" else "you owe them"
                                if st.button("Draft reminder", key=f"remind_{table}_{r['id']}",
                                            width="stretch"):
                                    st.session_state.bot_open = True
                                    st.session_state.messages.append({
                                        "role": "user",
                                        "content": (
                                            f"Draft a short, polite reminder message to "
                                            f"{r[name_col]} about the "
                                            f"{finance.money(float(r['amount']), 0)} that "
                                            f"{verb}, outstanding for {r['days']} days."),
                                    })
                                    st.rerun()

                    view["date"] = view["date"].map(finance.display_date)
                    view["paid_back"] = view["paid_back"].astype(bool)
                    # Safe to convert: "amount" is listed in disabled= below and
                    # the write-back loop only ever reads the id and the
                    # checkbox, so a displayed figure never travels back to the
                    # database.
                    view["amount"] = view["amount"].map(finance.to_display)
                    edited = st.data_editor(
                        view, key=f"edit_{table}", hide_index=True, width="stretch",
                        disabled=["id", "date", name_col, "amount", "days"],
                        column_config={
                            "id": None,
                            "date": "Since",
                            name_col: "Name",
                            "amount": st.column_config.NumberColumn(
                                f"Amount ({CURRENCY})", format=f"{CURRENCY_SYMBOL} %.2f"),
                            "days": st.column_config.NumberColumn(
                                "Days", help="Days since this debt was recorded"),
                            "paid_back": st.column_config.CheckboxColumn("Settled"),
                        },
                    )
                    touched = False
                    for before, after in zip(view.to_dict("records"), edited.to_dict("records")):
                        if bool(before["paid_back"]) != bool(after["paid_back"]):
                            db.set_paid_back(table, int(before["id"]),
                                             bool(after["paid_back"]), str(date.today()))
                            touched = True
                    if touched:
                        _touch_data()
                        st.rerun()

        with t_imp:
            # Auto sits first and is the default. A hand-kept sheet usually
            # carries every ledger side by side, so choosing a single one read
            # a quarter of the file while looking like it had read all of it —
            # spending landed but income, lent and borrowed silently did not.
            AUTO_TARGET = "__auto__"
            targets = [AUTO_TARGET] + list(importer.SCHEMAS)
            picked = st.selectbox(
                "Import into", targets,
                format_func=lambda k: ("Auto — send each section to its own ledger"
                                       if k == AUTO_TARGET
                                       else importer.SCHEMAS[k]["label"]),
                key="import_ledger")
            auto = picked == AUTO_TARGET
            target = "expenses" if auto else picked
            st.caption(
                "Each block of columns goes to the ledger it belongs to — spending, "
                "income, lent and borrowed all land in the right place from one file. "
                "Nothing is written until you press import."
                if auto else
                f"Only {importer.SCHEMAS[target]['label']} is touched. Nothing is "
                f"written until you press import.")
            upload = st.file_uploader("CSV or Excel file",
                                      type=importer.UPLOAD_TYPES,
                                      key="import_file")
            if upload is not None:
                # A workbook can hold several sheets and only one of them is
                # the ledger, so ask which — but only when there is actually a
                # choice to make.
                sheet = None
                if importer._is_excel(upload.name):
                    names = importer.excel_sheets(upload)
                    if len(names) > 1:
                        sheet = st.selectbox(
                            "Sheet", names,
                            key=f"import_sheet_{upload.name}_{upload.size}")
                    elif names:
                        sheet = names[0]
                raw = None
                try:
                    raw = importer.read_table(upload, sheet)
                except Exception as exc:
                    st.error(str(exc))
                if raw is not None and not raw.empty:
                    st.caption(f"{len(raw)} rows, {len(raw.columns)} columns detected.")

                    sections = importer.detect_sections(raw, None if auto else target)

                    if auto:
                        if not sections:
                            st.warning("No ledger section could be read from this file. "
                                       "Pick a ledger above and map the columns by hand.")
                        else:
                            st.dataframe(
                                [{"Section": importer.SCHEMAS[k]["label"],
                                  "Rows": len(v["rows"]),
                                  "Total": finance.money(
                                      sum(r["amount"] for r in v["rows"]), 0)}
                                 for k, v in sections.items()],
                                width="stretch", hide_index=True)
                            # The same padding/summary rows are skipped in
                            # every section, so warnings would otherwise repeat
                            # once per ledger. Blank-row notices are dropped
                            # outright here: in a sheet with several blocks
                            # side by side, every block is padded out to the
                            # longest one, so blank rows are the file's shape
                            # rather than anything lost. They also differ by a
                            # row or two per section, which defeated the
                            # de-duplication and produced two near-identical
                            # lines with no clue which block each described.
                            told = set()
                            for detail in sections.values():
                                for problem in detail["problems"]:
                                    if "empty row" in problem:
                                        continue
                                    if problem not in told:
                                        told.add(problem)
                                        st.warning(problem)
                            ready = sum(len(v["rows"]) for v in sections.values())
                            replace_auto = st.checkbox(
                                "Replace everything already in these ledgers",
                                key="import_replace_auto")
                            if st.button(f"Import {ready} rows into "
                                         f"{len(sections)} ledgers", type="primary",
                                         key="do_import_auto", width="stretch"):
                                done = {}
                                for led, detail in sections.items():
                                    done[led] = importer.commit(
                                        led, detail["rows"], replace_auto)
                                db.delete_meta(demo.FLAG)
                                _touch_data()
                                st.success(" · ".join(
                                    f"{n} {importer.SCHEMAS[k]['label'].lower()}"
                                    for k, n in done.items()))
                                st.rerun()

                    if not auto:
                        extras = {k: v for k, v in sections.items() if k != target}
                        if extras:
                            st.info("This file also holds "
                                    + ", ".join(f"{len(v['rows'])} "
                                                f"{importer.SCHEMAS[k]['label'].lower()}"
                                                for k, v in extras.items())
                                    + " — switch to Auto above to bring those in too.")

                        guess = importer.suggest_mapping(raw, target)
                        options = [importer.NONE_LABEL] + list(raw.columns)
                        mapping = {}
                        fields = importer.SCHEMAS[target]["fields"]
                        holders = st.columns(len(fields))
                        for (field, spec), holder in zip(fields.items(), holders):
                            with holder:
                                label = field.title() + ("" if spec["required"] else " (optional)")
                                guessed = guess.get(field, importer.NONE_LABEL)
                                mapping[field] = st.selectbox(
                                    label, options,
                                    index=options.index(guessed) if guessed in options else 0,
                                    key=f"map_{target}_{field}_{upload.name}_{upload.size}_{sheet}")
                        rows, problems = importer.build_rows(raw, target, mapping)
                        for problem in problems:
                            st.warning(problem)
                        if rows:
                            st.markdown(f"**{len(rows)} rows ready.** First few:")
                            st.dataframe(importer.preview(rows), width="stretch", hide_index=True)
                            replace = st.checkbox(
                                f"Replace everything already in "
                                f"{importer.SCHEMAS[target]['label']}", key="import_replace")
                            if st.button(f"Import {len(rows)} rows", type="primary",
                                         key="do_import", width="stretch"):
                                written = importer.commit(target, rows, replace)
                                db.delete_meta(demo.FLAG)
                                _touch_data()
                                st.success(f"Imported {written} rows.")
                                st.rerun()


# ==================================================================== bot

if rail is not None:
    with rail:
        # Only on the run that opens the panel. Replaying the entrance on every
        # later rerun would make the whole rail flicker each time a message is
        # sent, which is worse than no animation at all. Applied as CSS to the
        # column rather than a wrapper div, because Streamlit gives every
        # element its own container and a stray <div> cannot wrap its siblings.
        if not _was_open:
            st.markdown(f"<style>{theme.RAIL_OPEN_CSS}</style>",
                        unsafe_allow_html=True)
        # Heading and its close control share one row, aligned on their
        # centres. An absolutely-positioned button was tried first and had to
        # guess an offset that only held at one breakpoint — a real column
        # pair lines them up at every width, and the heading's trailing rule
        # simply stops before the button instead of running underneath it.
        # The toolbar's own toggle can scroll out of view (and sits behind the
        # overlay on mobile), so this is the close that is always reachable.
        head_l, head_r = st.columns([6, 1], vertical_alignment="center")
        with head_l:
            html(cap("Finance bot", large=True))
        with head_r:
            if st.button("", icon=":material/close:", key="close_rail",
                         help="Close"):
                st.session_state.bot_open = False
                st.rerun()

        # ---- chat switcher ---------------------------------------------
        # A selectbox rather than the heading itself: Streamlit cannot turn
        # custom HTML into a native menu, and a real widget is keyboard
        # reachable and obviously a control. Sat directly under the heading so
        # the two read as one block.
        chats = load_chats()
        if st.session_state.chat_id not in {c["id"] for c in chats}:
            st.session_state.chat_id = active_chat_id(chats)
        names = {c["id"]: c["name"] for c in chats}
        ids = list(names)

        # The selectbox's key carries a digest of the chat names. Renaming
        # changes only the label a format_func produces, not the option value,
        # so Streamlit had no reason to redraw and the old name stayed on
        # screen until a full reload — the rename had actually saved. A key
        # that moves with the names remounts the widget exactly when its
        # labels change, and never otherwise.
        signature = hashlib.md5(
            "|".join(f"{i}:{names[i]}" for i in ids).encode()).hexdigest()[:8]
        pick_key = f"chat_pick_{signature}"
        # Seeded before the widget exists; Streamlit refuses writes to a
        # widget's key once it has been instantiated.
        if pick_key not in st.session_state:
            st.session_state[pick_key] = st.session_state.chat_id

        def _switch_chat():
            picked = st.session_state[pick_key]
            if picked == st.session_state.chat_id:
                return
            save_chat()                        # keep the one being left
            st.session_state.chat_id = picked
            db.set_meta(ACTIVE_CHAT_KEY, picked)
            st.session_state.messages = next(
                (list(c["messages"]) for c in load_chats() if c["id"] == picked), [])

        cs1, cs2, cs3 = st.columns([2.2, 0.9, 0.9])
        with cs1:
            st.selectbox("Chat", ids, format_func=lambda i: names[i],
                         key=pick_key, label_visibility="collapsed",
                         on_change=_switch_chat)
        with cs2:
            if st.button("", icon=":material/add:", key="chat_new",
                         width="stretch", help="Start a new chat"):
                save_chat()
                # One past the highest numeric id in use. Ids that are not
                # numbers (hand-edited, or from a future format) are simply
                # skipped rather than crashing the expression.
                numeric = [int(c["id"]) for c in chats if str(c["id"]).isdigit()]
                fresh = {"id": str(max(numeric, default=0) + 1),
                         "name": new_chat_name(chats), "messages": []}
                chats.append(fresh)
                save_chats(chats, fresh["id"])
                st.session_state.chat_id = fresh["id"]
                st.session_state.messages = []
                st.rerun()
        with cs3:
            with st.popover("", icon=":material/more_horiz:", key="chat_menu",
                            width="stretch", help="Rename or delete this chat"):
                current = next(c for c in chats if c["id"] == st.session_state.chat_id)
                # A form, not a bare text_input plus button. text_input only
                # sends its value on blur or Enter, so typing a name and
                # clicking Rename straight away — the natural motion — would
                # submit the OLD name and look like nothing happened. A form
                # posts every field with the click, whatever the focus did.
                with st.form("chat_rename_form", clear_on_submit=False):
                    renamed = st.text_input("Name", value=current["name"],
                                            max_chars=CHAT_NAME_MAX,
                                            key="chat_rename")
                    if st.form_submit_button("Rename", width="stretch"):
                        label = renamed.strip()
                        if label:
                            current["name"] = label
                            save_chats(chats, st.session_state.chat_id)
                            st.rerun()
                        else:
                            st.caption("A chat needs a name.")
                # The last chat is never deleted — the panel would have
                # nothing to show and no way back.
                if st.button("Delete this chat", key="chat_delete",
                             width="stretch", disabled=len(chats) == 1):
                    remaining = [c for c in chats
                                 if c["id"] != st.session_state.chat_id]
                    save_chats(remaining, remaining[0]["id"])
                    st.session_state.chat_id = remaining[0]["id"]
                    st.session_state.messages = list(remaining[0]["messages"])
                    st.rerun()
                if len(chats) == 1:
                    st.caption("This is your only chat, so it cannot be deleted. "
                               "Clear chat empties it instead.")
        # hasattr() alone does not guard this: st.secrets can still raise on
        # first access when no secrets.toml exists at all, depending on the
        # Streamlit version.
        try:
            api_key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            api_key = None

        # Swapping models is config, not code: set GEMINI_MODEL in
        # .streamlit/secrets.toml and the bot uses it from the next message.
        try:
            chosen_model = st.secrets.get("GEMINI_MODEL")
            if chosen_model:
                bot.MODEL = chosen_model
        except Exception:
            pass

        # The free tier's ceiling is per minute, and hitting it reads as the
        # bot breaking. Warned about while there is still room to slow down,
        # and only then — a permanent counter would just be noise.
        # Falling back is invisible otherwise, and it is the one early warning
        # that the day's free allowance is running out.
        if bot.ACTIVE_MODEL != bot.MODEL:
            st.caption(f"Using {bot.ACTIVE_MODEL} — {bot.MODEL} is out of free "
                       f"quota for today.")

        # Previously this only surfaced as a chat reply, so the panel looked
        # fully working until you sent a message and got told it was not. Said
        # up front instead, with the fix and the reassurance that the board
        # itself does not depend on it.
        if not api_key:
            html('<div class="ll-nokey">',
                 f'<div class="ll-nokey-title">{icons.icon("info", 15)}'
                 'Bot not connected</div>',
                 '<div class="ll-nokey-body">Add <code>GEMINI_API_KEY</code> to '
                 '<code>.streamlit/secrets.toml</code> and restart to turn the '
                 'chat on. Every other panel on this board works without it and '
                 'none of your records are affected.</div></div>')

        # Sized to what is in it. A fixed tall box left a dead void between
        # the last message and the composer whenever the conversation was
        # short, which is most of the time; a long one still needs the room so
        # a table-shaped reply is not born already scrolled out of view.
        turns = len(st.session_state.messages)
        # No fixed height while the chat is empty. A height= container is a
        # scroll box, so the opening state sat in one and the composer was
        # parked below the fold behind a scrollbar. Unbounded, the panel is
        # simply as tall as its contents and the input is the first thing in
        # reach. A real conversation still gets the scroll box, or it would
        # push the whole page down as it grew.
        # Keyed so the stylesheet can clamp it against the viewport: a pixel
        # height is all st.container takes, and a fixed 400 was taller than
        # the room left on a phone once the heading, switcher, prompts and
        # composer had taken theirs — the composer ended up below the fold.
        # CSS finishes the job in vh; these numbers are just the ceiling.
        log = (st.container(key="bot_log") if turns == 0
               else st.container(height=min(200 + turns * 60, 320), key="bot_log"))
        with log:
            if not st.session_state.messages:
                # No example line here. It cost four lines of height on the
                # one screen where height matters most, and pushed the
                # composer below the fold — the prompt buttons underneath
                # already show what can be asked, and better, because they
                # are clickable.
                html('<div class="ll-empty" style="padding:10px 8px 2px;gap:6px">',
                     icons.icon("chat", 24),
                     '<div class="ll-empty-title">Tell it what happened</div>',
                     '</div>',
                     BOARD_LEGEND)
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # Only while the chat is empty. This exists to sit the prompts and
        # composer down into the room the privacy note used to occupy on the
        # opening screen — but once there is a conversation, the log has
        # already filled that room, and the spacer becomes a bare gap between
        # the last reply and the buttons.
        if not st.session_state.messages:
            spacer(64)

        pending = bool(st.session_state.messages
                       and st.session_state.messages[-1]["role"] == "user")

        if pending:
            if st.button("Stop generating", key="stop_gen", width="stretch"):
                st.session_state.stop = True
                st.rerun()
        else:
            # The three stay up for the whole conversation. Only the slot that
            # was clicked refills, from the next prompt in the pool that is not
            # already on screen, so the other two do not move under the cursor.
            # No wrapper div around these. Streamlit gives every element its
            # own container, so the <div> never actually wrapped the buttons —
            # it just added two more elements to the column, and the gap either
            # side of them is what made the space above "Explain" wider than
            # the gaps between the prompts. Without it all four are siblings on
            # one rhythm.
            # A session that started before the count changed still carries
            # the old number of slots in its state, and would keep rendering
            # four buttons until it was restarted.
            if len(st.session_state.starter_slots) != STARTER_SLOTS:
                st.session_state.starter_slots = list(STARTER_OPENING)
            shown = st.session_state.starter_slots
            for slot, pool_index in enumerate(list(shown)):
                if st.button(STARTER_POOL[pool_index], key=f"starter_{slot}",
                             width="stretch"):
                    st.session_state.messages.append(
                        {"role": "user", "content": STARTER_POOL[pool_index]})
                    st.session_state.starter_slots[slot] = next_starter(shown)
                    save_chat()
                    st.rerun()
            # The month digest only fires once, on the first load of a new
            # month, so the one genuinely useful thing the bot does was
            # unreachable for the other thirty days. This asks for the same
            # read-out on demand, for whichever period the board is showing.
            if st.button(f"Explain {finance.month_label(snap.key)}"
                         if snap.key != finance.ALL_TIME else "Explain all time",
                         key="explain_period", width="stretch"):
                st.session_state.messages.append({
                    "role": "user",
                    "content": (
                        f"Give me a plain-language read-out of "
                        f"{finance.month_label(snap.key) if snap.key != finance.ALL_TIME else 'my whole history'}: "
                        f"what came in, what went out, where most of it went, "
                        f"what changed against the month before, and the one "
                        f"thing most worth acting on. Use the real figures."),
                })
                save_chat()
                st.rerun()
            if st.session_state.messages:
                if st.button("Clear chat", key="clear_chat", width="stretch"):
                    st.session_state.messages = []
                    save_chat()
                    st.rerun()

        try:
            typed = st.chat_input("Message the bot", disabled=pending,
                                  accept_file="multiple",
                                  file_type=["csv", "png", "jpg", "jpeg"])
        except TypeError:
            typed = st.chat_input("Message the bot", disabled=pending)


        if typed:
            text = getattr(typed, "text", None)
            files = getattr(typed, "files", None)
            if text is None and isinstance(typed, dict):
                text, files = typed.get("text", ""), typed.get("files", [])
            elif text is None:
                text, files = str(typed), []
            text = (text or "").strip()
            files = files or []

            attachment_text, images, names = "", [], []
            for handle in files:
                names.append(handle.name)
                try:
                    handle.seek(0)
                    if handle.name.lower().endswith(".csv"):
                        attachment_text += cap_attachment_text(handle.name, handle.read())
                    else:
                        data, mime = downscale_image(handle.read(), handle.type)
                        images.append({"mime_type": mime, "data": data})
                except Exception:
                    pass

            shown = text
            if names:
                shown = (shown + "\n\n" if shown else "") + f"*Attached: {', '.join(names)}*"
            if shown:
                st.session_state.messages.append({
                    "role": "user", "content": shown,
                    "attachment_text": attachment_text, "images": images,
                })
                save_chat()
                st.rerun()

        # ---- generate the pending reply ------------------------------------
        if pending:
            last = st.session_state.messages[-1]
            with log:
                with st.chat_message("assistant"):
                    if not api_key:
                        reply = ("**No API key.** Add `GEMINI_API_KEY` to "
                                 "`.streamlit/secrets.toml` and I can read and write "
                                 "your ledgers.")
                        st.markdown(reply)
                    elif st.session_state.stop:
                        reply = "_Stopped._"
                        st.markdown(reply)
                    else:
                        st.session_state.partial = ""

                        # Shown immediately; the first streamed piece clears it, so the
                        # gap between hitting send and the first token never reads blank.
                        thinking = st.empty()
                        thinking.markdown(
                            '<div class="ll-thinking"><span class="dot"></span>'
                            '<span class="dot"></span><span class="dot"></span>'
                            'Thinking…</div>', unsafe_allow_html=True)

                        def show_status(note: str) -> None:
                            """Progress shown in place of 'Thinking…' — a
                            rate-limit backoff can run half a minute, and an
                            unexplained pause reads as a hang."""
                            thinking.markdown(
                                '<div class="ll-thinking"><span class="dot"></span>'
                                '<span class="dot"></span><span class="dot"></span>'
                                f'{esc(note)}</div>', unsafe_allow_html=True)

                        def collect():
                            first_piece = True
                            prompt = last["content"]
                            if last.get("attachment_text"):
                                prompt += (f"\n\n[attached file contents]"
                                           f"\n{last['attachment_text']}")
                            stream = bot.stream_reply(
                                api_key,
                                bot.system_context(snap, frames, series),
                                bot.build_history(st.session_state.messages[:-1]),
                                bot.build_parts(prompt, last.get("images")),
                                should_stop=lambda: st.session_state.get("stop", False),
                                on_status=show_status,
                            )
                            for piece in stream:
                                if first_piece:
                                    thinking.empty()
                                    first_piece = False
                                st.session_state.partial += piece
                                yield piece

                        # Belt-and-suspenders: bot.stream_reply already turns a
                        # Gemini-side failure into yielded text, but anything that
                        # raises while building the prompt/context (a malformed
                        # attachment, a bad history entry) would otherwise escape as
                        # a raw traceback and leave `pending` stuck true forever,
                        # since the message-append below would never run.
                        try:
                            # Rendered by re-parsing the whole reply so far on
                            # every chunk, rather than handing st.write_stream
                            # one fragment at a time. Gemini splits mid-syntax:
                            # a table arrives row by row and a bold span can be
                            # cut between its asterisks, and a fragment parsed
                            # alone is not valid markdown — which is why long
                            # answers flashed raw pipes and stars while they
                            # streamed and only settled once finished.
                            slot = st.empty()
                            streamed = ""
                            for piece in collect():
                                streamed += piece
                                slot.markdown(streamed + "▌")
                            slot.markdown(streamed)
                            reply = streamed or st.session_state.partial
                        except Exception as exc:
                            thinking.empty()
                            reply = f"_Something went wrong talking to the bot: {exc}_"
                            st.markdown(reply)

            st.session_state.messages.append({"role": "assistant",
                                              "content": reply or "_No reply._"})
            save_chat()
            st.session_state.partial = ""
            st.session_state.stop = False
            # The bot may have written to the ledgers via its tools — there is
            # no cheap way to know from here whether it actually did, so treat
            # every turn as data-changing. Reruns here are already infrequent
            # (one per message), so the extra reload is not worth avoiding.
            _touch_data()
            st.rerun()


# =============================================================== settings

@st.dialog("Settings")
def settings_dialog():
    counts = db.row_counts()
    present = ", ".join(f"{v} {k}" for k, v in counts.items() if v) or "nothing yet"
    st.markdown(f"**{sum(counts.values())} records** &mdash; {present}")

    st.divider()
    st.markdown("**Debts settled the same month**")
    net_on = (db.get_meta("net_same_month_debts") or "1") == "1"
    picked_net = st.checkbox(
        "Keep them out of arrivals and departures",
        value=net_on, key="net_debts_toggle",
        help="A debt borrowed and repaid inside one month moves money out and "
             "back again, so it changes nothing. Leaving both legs in adds its "
             "value to your arrivals AND departures totals. Either way your "
             "on-hand balance is identical.")
    if picked_net != net_on:
        db.set_meta("net_same_month_debts", "1" if picked_net else "0")
        _touch_data()
        st.rerun()
    st.caption("Debts still outstanding, or settled in a later month, always "
               "show — only same-month round trips are hidden.")

    st.divider()
    st.markdown("**Opening balance**")
    st.caption("What you had saved before this board started. It seeds the "
               "earliest month's brought-forward instead of being logged as "
               "income, so it never counts as money earned.")
    ob_current = float(db.get_meta("opening_balance") or 0.0)
    ob_c1, ob_c2 = st.columns([1.4, 1])
    with ob_c1:
        ob_new = st.number_input(
            f"Opening balance ({CURRENCY})", min_value=0.0, step=500.0,
            format="%.2f", value=float(finance.to_display(ob_current)),
            key="opening_balance_input", label_visibility="collapsed")
    with ob_c2:
        if st.button("Save balance", key="save_opening", width="stretch"):
            db.set_meta("opening_balance", str(to_pkr(ob_new)))
            _touch_data()
            st.rerun()
    if ob_current:
        st.caption(f"Currently {finance.money(ob_current)} — carried into "
                   f"the first month on the board.")

    st.divider()
    st.markdown("**Finance bot**")
    st.caption("Messages, receipts and CSVs you send to the bot, plus the "
               "ledger figures needed to answer them, go to Google's Gemini "
               "API to generate a reply. Nothing else on this board leaves "
               "your machine.")

    st.divider()
    st.markdown("**Currency**")
    st.caption("Changes what the board is read in. Your records stay stored in "
               "rupees exactly as entered — this converts on display only, so "
               "switching back restores the original figures precisely.")
    codes = list(rates.CURRENCIES)
    cur_c1, cur_c2 = st.columns([1.2, 1])
    with cur_c1:
        picked = st.selectbox(
            "Display currency", codes,
            index=codes.index(CURRENCY),
            format_func=lambda c: f"{c} — {rates.CURRENCIES[c][1]}",
            key="currency_pick", label_visibility="collapsed")
    with cur_c2:
        if st.button("Refresh rates", key="fx_refresh", width="stretch"):
            rates.get_rates(force=True)
            st.rerun()
    if picked != CURRENCY:
        rates.set_currency(picked)
        st.rerun()

    if CURRENCY == rates.BASE:
        st.caption(f"Rates on file: " + " · ".join(
            f"1 {c} = {rates.rate_for(c, FX['rates']):,.2f} PKR"
            for c in codes if c != rates.BASE))
    else:
        st.caption(f"1 {CURRENCY} = {rates.rate_for(CURRENCY, FX['rates']):,.4f} PKR")
    if FX["stale"]:
        st.warning(f"Showing rates from {FX['fetched_on']} — could not reach a "
                   f"live source just now ({FX['source']}). Figures are "
                   f"converted with the last good rates.")
    else:
        st.caption(f"Source: {FX['source']} · updated {FX['fetched_on']}")

    st.divider()
    st.markdown("**Budgets**")
    st.caption("A monthly cap per category. Platform load shows spent-vs-cap once one is set.")
    budgets = db.get_budgets()
    bc1, bc2, bc3 = st.columns([1.3, 1, 0.7])
    with bc1:
        budget_cat = st.selectbox("Category", db.CATEGORIES, key="budget_cat",
                                  label_visibility="collapsed")
    with bc2:
        # Keyed on the chosen category so switching categories shows that
        # category's own cap instead of carrying over whatever was last typed —
        # the same stale-widget-state trap as the import column mapping above.
        budget_amt = st.number_input(
            f"Monthly cap ({CURRENCY})", min_value=0.0, step=500.0, format="%.2f",
            value=float(finance.to_display(budgets.get(budget_cat, 0.0))),
            key=f"budget_amt_{budget_cat}", label_visibility="collapsed")
    with bc3:
        if st.button("Save", key="save_budget", width="stretch"):
            if budget_amt > 0:
                db.set_budget(budget_cat, to_pkr(budget_amt))
            else:
                db.delete_budget(budget_cat)
            st.rerun()
    if budgets:
        st.caption(" · ".join(f"{c}: {finance.money(v, 0)}/mo" for c, v in sorted(budgets.items())))

    st.divider()
    st.markdown("**Merge a category**")
    st.caption("Moves every expense from one category into another. Imports "
               "bring in near-duplicates — a “Transport” beside the "
               "“Transportation” that already exists — and until now "
               "the only fix was deleting the rows and typing them again. The "
               "rows keep their dates and amounts; only the label moves.")
    used = sorted({r["category"] for r in db.get_expenses() if r.get("category")})
    if not used:
        st.caption("No expenses to merge yet.")
    else:
        mc1, mc2, mc3 = st.columns([1.2, 1.2, 0.9])
        with mc1:
            merge_from = st.selectbox("From", used, key="merge_from",
                                      label_visibility="collapsed")
        with mc2:
            targets = [c for c in db.CATEGORIES if c != merge_from]
            merge_to = st.selectbox("Into", targets, key="merge_to",
                                    label_visibility="collapsed")
        with mc3:
            movable = sum(1 for r in db.get_expenses()
                          if r.get("category") == merge_from)
            if st.button("Merge", key="do_merge", width="stretch",
                         disabled=not movable):
                moved = db.rename_category(merge_from, merge_to)
                # A cap set against the old name would otherwise sit there
                # budgeting a category that no longer has anything in it.
                caps = db.get_budgets()
                if merge_from in caps:
                    db.delete_budget(merge_from)
                _touch_data()
                st.success(f"Moved {moved} entr"
                           f"{'y' if moved == 1 else 'ies'} into {merge_to}.")
                st.rerun()
        st.caption(f"{movable} entr{'y' if movable == 1 else 'ies'} currently "
                   f"in {merge_from}.")

    st.divider()
    st.markdown("**Recurring**")
    st.caption("Rent, subscriptions, salary — the same entry every month. A due "
               "template shows as a banner above the board once its day arrives.")
    existing_recurring = db.get_recurring()
    for r in existing_recurring:
        rr1, rr2 = st.columns([5, 1])
        with rr1:
            kind_label = "Income" if r["kind"] == "income" else (r["category"] or "Expense")
            st.caption(f"{r['label']} — {finance.money(r['amount'], 0)} "
                       f"on day {r['day_of_month']} ({kind_label})")
        with rr2:
            if st.button("✕", key=f"del_recur_{r['id']}", width="stretch"):
                db.delete_recurring(r["id"])
                st.rerun()
    nr1, nr2 = st.columns(2)
    with nr1:
        new_label = st.text_input("Label", placeholder="Rent", key="recur_label")
        new_kind = st.selectbox("Kind", ["Expense", "Income"], key="recur_kind")
    with nr2:
        new_amount = st.number_input(f"Amount ({CURRENCY})", min_value=0.0,
                                     step=500.0, format="%.2f", key="recur_amount")
        new_day = st.number_input("Day of month", min_value=1, max_value=28,
                                  value=1, step=1, key="recur_day")
    new_category = None
    if new_kind == "Expense":
        new_category = st.selectbox("Category", db.CATEGORIES, key="recur_category")
    if st.button("Add recurring", width="stretch", key="add_recurring"):
        if new_label.strip() and new_amount > 0:
            db.add_recurring(new_label.strip(), new_kind.lower(), new_category,
                             to_pkr(new_amount), int(new_day))
            st.rerun()
        else:
            st.warning("Needs a label and an amount above zero.")

    st.divider()
    st.markdown("**Sample data**")
    if demo.is_active():
        st.caption("The board is showing generated sample records right now.")
        if st.button("Clear sample data", width="stretch", key="clear_demo"):
            demo.clear()
            st.session_state.messages = []
            _touch_data()
            st.rerun()
    else:
        st.caption("Fills three months with plausible generated records so the board "
                   "can be judged with data in it. Labelled while active.")
        blocked = frames.total_rows > 0
        if blocked:
            st.caption("Clear your real records first — sample rows are never mixed "
                       "into data you entered.")
        if st.button("Load sample data", width="stretch", key="load_demo", disabled=blocked):
            demo.seed()
            _touch_data()
            st.rerun()

    st.divider()
    st.markdown("**Backup**")
    st.caption("Every record in every ledger as one CSV — readable in any "
               "spreadsheet, and the only copy of this data that is not the "
               "app's own database file.")
    total_rows = sum(counts.values())
    st.download_button(
        "Download all records (CSV)",
        data=importer.export_csv(),
        file_name=f"loot-ledger-{date.today().isoformat()}.csv",
        mime="text/csv", width="stretch", key="export_csv",
        disabled=total_rows == 0)

    st.divider()
    st.markdown("**Reset**")
    st.caption("Deletes every record in every ledger. This cannot be undone.")
    # Two clicks, not a typed phrase. The phrase was removed by request, but a
    # single click on a primary button sitting a few pixels below "Load sample
    # data" is one slip away from destroying the whole ledger with nothing to
    # undo it. Arming is a separate, explicit act and costs one extra click.
    # A nested st.dialog is not an option — this already runs inside one.
    # Arming deliberately does NOT call st.rerun(): a rerun dismisses the
    # surrounding st.dialog, which closed Settings the instant you armed it and
    # left the confirm buttons unreachable. The click already triggers its own
    # rerun, so setting the flag and testing it just below renders the confirm
    # step in the same pass, with the dialog still open.
    if not st.session_state.get("erase_armed"):
        if st.button("Erase everything", type="primary", width="stretch",
                     key="erase_all"):
            st.session_state.erase_armed = True
    if st.session_state.get("erase_armed"):
        st.error(f"This deletes all {sum(counts.values())} records permanently.")
        ec1, ec2 = st.columns(2)
        with ec1:
            if st.button("Yes, erase everything", type="primary",
                         width="stretch", key="erase_confirm"):
                db.erase_all()
                st.session_state.messages = []
                st.session_state.erase_armed = False
                _touch_data()
                st.rerun()
        with ec2:
            if st.button("Cancel", width="stretch", key="erase_cancel"):
                st.session_state.erase_armed = False
                st.rerun()


if settings_open:
    settings_dialog()


# ---- deferred digest generation -------------------------------------------
# Runs last, after every panel above has already been sent to the browser, so
# the Gemini round trip costs nothing on the board's first paint. The rerun at
# the end draws the finished digest into the slot reserved for it at the top.
if digest_job:
    api_key_for_digest = None
    try:
        api_key_for_digest = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        pass
    # One attempt per month, success or failure — marking the period up front
    # means a Gemini failure doesn't retry on every rerun for the rest of it.
    db.set_meta("digest_period", CURRENT_PERIOD)
    if api_key_for_digest:
        try:
            last_snap = finance.snapshot(frames, digest_job)
            digest_text = "".join(bot.stream_reply(
                api_key_for_digest,
                bot.system_context(last_snap, frames, series),
                [],
                bot.build_parts(
                    "Summarize last month's finances in 3-4 short, concrete "
                    "sentences for a quick glance: total spent, total earned, "
                    "where most money went, and whether it was a good month "
                    "financially. Use the real figures already given to you "
                    "above — never invent a number."),
            ))
            db.set_meta("digest_text", digest_text.strip())
        except Exception:
            db.delete_meta("digest_text")
    else:
        db.delete_meta("digest_text")
    st.rerun()
