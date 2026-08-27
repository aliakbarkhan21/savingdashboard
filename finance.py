"""
The money model for Loot Ledger.

Everything the board displays is derived here, so there is exactly one place where
"what is actually left" is defined.

Why the debt maths changed
--------------------------
The previous model counted only *repaid* debt and left the original transfer out
entirely, which invented and destroyed money:

    remaining = income - expenses + lent_repaid - borrowed_repaid

Lending someone Rs. 1,000 moved no cash, yet getting it back added Rs. 1,000 out
of nowhere. Borrowing added nothing, yet repaying subtracted.

Cash actually moves on both legs:

    lend out        -> cash leaves you
    they repay you  -> cash comes back
    you borrow      -> cash comes in
    you repay them  -> cash leaves

A fully settled loan therefore nets to zero, and the model collapses to:

    cash = income - expenses - lent_outstanding + borrowed_outstanding

Money you lent and have not been repaid is money you do not have. Money you
borrowed and have not repaid is money you are holding. Both are cash facts, not
paper ones. What stays on paper is the *obligation*, reported separately as the
receivable and payable balances.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

import db

ALL_TIME = "__ALL__"


# ---------------------------------------------------------------- month keys

def month_key(value) -> str:
    """Normalise anything date-like to a YYYY-MM key."""
    if isinstance(value, str):
        return value[:7]
    return value.strftime("%Y-%m")


def month_label(key: str) -> str:
    if key == ALL_TIME:
        return "All Time"
    try:
        return datetime.strptime(key, "%Y-%m").strftime("%B %Y")
    except ValueError:
        return key


def month_short(key: str) -> str:
    if key == ALL_TIME:
        return "ALL"
    try:
        return datetime.strptime(key, "%Y-%m").strftime("%b").upper()
    except ValueError:
        return key


def month_year(key: str) -> str:
    if key == ALL_TIME:
        return ""
    try:
        return datetime.strptime(key, "%Y-%m").strftime("%Y")
    except ValueError:
        return ""


def shift_month(key: str, delta: int) -> str:
    """Step a YYYY-MM key by whole months."""
    y, m = int(key[:4]), int(key[5:7])
    total = y * 12 + (m - 1) + delta
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def month_span(first: str, last: str) -> list[str]:
    """Every month from `first` to `last` inclusive, gaps filled."""
    out, cur = [], first
    # Guard against a reversed range producing an unbounded walk.
    if first > last:
        return [first]
    while cur <= last:
        out.append(cur)
        cur = shift_month(cur, 1)
    return out


# ---------------------------------------------------------------- data frames

_EMPTY = {
    "expenses": ["id", "date", "description", "category", "amount"],
    "transport": ["id", "date", "amount"],
    "income": ["id", "date", "source", "amount"],
    "lent": ["id", "date", "person", "amount", "paid_back", "settled_date"],
    "borrowed": ["id", "date", "lender", "amount", "paid_back", "settled_date"],
}


def _frame(rows, name):
    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=_EMPTY[name])
    df["_m"] = df["date"].astype(str).str.slice(0, 7) if not df.empty else pd.Series(dtype=str)
    if "settled_date" in df.columns:
        # NaN is truthy, so it must be filtered by type here rather than by
        # truthiness later, or it reaches the month keys and breaks sorting.
        df["_settled_m"] = [
            str(v)[:7] if isinstance(v, str) and v.strip() else None
            for v in df["settled_date"].tolist()
        ]
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    return df


@dataclass
class Frames:
    expenses: pd.DataFrame
    transport: pd.DataFrame
    income: pd.DataFrame
    lent: pd.DataFrame
    borrowed: pd.DataFrame

    @property
    def total_rows(self) -> int:
        return sum(len(f) for f in (self.expenses, self.transport,
                                    self.income, self.lent, self.borrowed))


def load_frames() -> Frames:
    return Frames(
        expenses=_frame(db.get_expenses(), "expenses"),
        transport=_frame(db.get_transport(), "transport"),
        income=_frame(db.get_income(), "income"),
        lent=_frame(db.get_lent(), "lent"),
        borrowed=_frame(db.get_borrowed(), "borrowed"),
    )


def _sum(df, mask=None) -> float:
    if df.empty or "amount" not in df.columns:
        return 0.0
    target = df if mask is None else df[mask]
    if target.empty:
        return 0.0
    return float(target["amount"].sum())


# ---------------------------------------------------------------- the series

@dataclass
class MonthRow:
    key: str
    opening: float = 0.0
    inflow: float = 0.0
    spend: float = 0.0          # expenses only
    transport: float = 0.0      # transport ledger only
    lent_out: float = 0.0       # cash handed to someone this month
    lent_returned: float = 0.0  # cash returned to you this month
    borrowed_in: float = 0.0    # cash you received this month
    borrowed_repaid: float = 0.0
    closing: float = 0.0

    @property
    def outflow(self) -> float:
        """Everything spent. Lending is a transfer, not spending, so it is excluded."""
        return self.spend + self.transport

    @property
    def debt_delta(self) -> float:
        return (self.lent_returned + self.borrowed_in
                - self.lent_out - self.borrowed_repaid)

    @property
    def net(self) -> float:
        """What this month added to, or took from, the pile."""
        return self.inflow - self.outflow + self.debt_delta

    @property
    def savings_rate(self) -> float:
        """Share of this month's income that survived it.

        Debt movement is deliberately excluded: a loan received is not income,
        and letting it inflate the rate would be the old model's mistake in a
        new place.
        """
        if self.inflow <= 0:
            return 0.0
        return (self.inflow - self.outflow) / self.inflow * 100.0


# ---- opening balance -------------------------------------------------
# What was already saved before the tracker started. It is a starting point,
# not a transaction: recording it as income would put a fake entry in a month
# that never had one, and would inflate that month's "earned" figure and every
# ratio built on it. Held here and used to seed the carry-forward walk, so it
# lands in the first month's "brought forward" and rides through untouched.
_OPENING_BALANCE = 0.0


def set_opening_balance(value: float) -> None:
    global _OPENING_BALANCE
    try:
        _OPENING_BALANCE = float(value or 0.0)
    except (TypeError, ValueError):
        _OPENING_BALANCE = 0.0


def opening_balance() -> float:
    return _OPENING_BALANCE


# ---- settled-in-the-same-month debts ---------------------------------
# A debt taken and cleared inside one month moves money out and back within
# that month, so it nets to nothing — but booking both legs still adds its
# value to BOTH the arrivals and departures headlines. Rs. 3,300 borrowed and
# repaid in August made August look like it took in 3,300 more and spent 3,300
# more than it did, which is not what "arrivals" is read as. Hidden by
# default; on_hand is identical either way, since removing both legs of a
# round trip cannot change a balance.
_NET_SAME_MONTH_DEBTS = True


def set_net_same_month_debts(value: bool) -> None:
    global _NET_SAME_MONTH_DEBTS
    _NET_SAME_MONTH_DEBTS = bool(value)


def _roundtrip_mask(df):
    """Rows opened and settled inside the same month."""
    if df.empty or "paid_back" not in df.columns or "_settled_m" not in df.columns:
        return None
    return (df["paid_back"] == 1) & (df["_settled_m"] == df["_m"])


def _without_roundtrips(df):
    if not _NET_SAME_MONTH_DEBTS:
        return df
    mask = _roundtrip_mask(df)
    return df if mask is None else df[~mask]


def month_series(frames: Frames, through: str | None = None) -> dict[str, MonthRow]:
    """Walk every month in order, carrying each closing balance into the next.

    This is the carryover fix: months no longer each start from zero.
    """
    keys: set[str] = set()
    for df in (frames.expenses, frames.transport, frames.income,
               frames.lent, frames.borrowed):
        if not df.empty:
            keys.update(k for k in df["_m"].tolist() if isinstance(k, str) and k)
            if "_settled_m" in df.columns:
                keys.update(k for k in df["_settled_m"].tolist() if isinstance(k, str) and k)

    today = date.today().strftime("%Y-%m")
    keys.add(today)
    if through:
        keys.add(through)

    ordered = month_span(min(keys), max(keys))

    series: dict[str, MonthRow] = {}
    running = _OPENING_BALANCE
    for key in ordered:
        row = MonthRow(key=key, opening=running)
        row.inflow = _sum(frames.income, frames.income["_m"] == key)
        row.spend = _sum(frames.expenses, frames.expenses["_m"] == key)
        row.transport = _sum(frames.transport, frames.transport["_m"] == key)
        # Both legs of a same-month round trip drop out together, so these
        # totals stay consistent with the rows shown on the board.
        lent_v = _without_roundtrips(frames.lent)
        borr_v = _without_roundtrips(frames.borrowed)
        row.lent_out = _sum(lent_v, lent_v["_m"] == key) if not lent_v.empty else 0.0
        row.borrowed_in = _sum(borr_v, borr_v["_m"] == key) if not borr_v.empty else 0.0

        if not lent_v.empty:
            row.lent_returned = _sum(
                lent_v,
                (lent_v["paid_back"] == 1) & (lent_v["_settled_m"] == key),
            )
        if not borr_v.empty:
            row.borrowed_repaid = _sum(
                borr_v,
                (borr_v["paid_back"] == 1) & (borr_v["_settled_m"] == key),
            )

        row.closing = row.opening + row.net
        running = row.closing
        series[key] = row
    return series


# ---------------------------------------------------------------- a snapshot

@dataclass
class Snapshot:
    """Everything the board needs for one period."""
    key: str
    label: str
    row: MonthRow

    receivable_open: float = 0.0   # lent, not yet returned
    payable_open: float = 0.0      # borrowed, not yet repaid
    receivable_count: int = 0
    payable_count: int = 0

    prev_key: str | None = None
    prev_outflow: float | None = None

    by_category: pd.DataFrame = field(default_factory=pd.DataFrame)
    arrivals: pd.DataFrame = field(default_factory=pd.DataFrame)
    departures: pd.DataFrame = field(default_factory=pd.DataFrame)

    # ---- derived ----
    @property
    def opening(self) -> float:
        return self.row.opening

    @property
    def inflow(self) -> float:
        return self.row.inflow

    @property
    def outflow(self) -> float:
        return self.row.outflow

    @property
    def on_hand(self) -> float:
        """Cash you can actually spend right now."""
        return self.row.closing

    @property
    def net_worth(self) -> float:
        """Cash plus what is owed to you, minus what you owe."""
        return self.on_hand + self.receivable_open - self.payable_open

    @property
    def savings_rate(self) -> float:
        return self.row.savings_rate

    @property
    def burn_pct(self) -> float:
        """Outflow against everything available this period, not just income.

        The old version divided by income alone, so a month spending down last
        month's savings reported >100% or, with no income at all, reported 0%.
        """
        available = self.opening + self.inflow
        if available <= 0:
            return 100.0 if self.outflow > 0 else 0.0
        return min(999.0, self.outflow / available * 100.0)

    @property
    def outflow_delta_pct(self) -> float | None:
        if not self.prev_outflow:
            return None
        return (self.outflow - self.prev_outflow) / self.prev_outflow * 100.0

    @property
    def has_activity(self) -> bool:
        return bool(self.inflow or self.outflow or self.opening
                    or self.receivable_open or self.payable_open)

    @property
    def status(self) -> str:
        """quiet / on-time / delayed / cancelled, in the board's own vocabulary.

        A period with nothing in it is reported as quiet rather than on-time:
        calling an empty board healthy is a reading the data does not support.
        """
        if not self.has_activity:
            return "quiet"
        if self.on_hand < 0:
            return "cancelled"
        pct = self.burn_pct
        if pct >= 90:
            return "cancelled"
        if pct >= 70:
            return "delayed"
        return "on-time"

    @property
    def top_category(self) -> tuple[str, float] | None:
        if self.by_category.empty:
            return None
        top = self.by_category.iloc[0]
        return str(top["category"]), float(top["amount"])


def _in_period(df: pd.DataFrame, key: str) -> pd.DataFrame:
    if df.empty:
        return df
    if key == ALL_TIME:
        return df
    return df[df["_m"] == key]


def snapshot(frames: Frames, key: str) -> Snapshot:
    series = month_series(frames, through=None if key == ALL_TIME else key)

    if key == ALL_TIME:
        row = MonthRow(key=ALL_TIME)
        row.opening = _OPENING_BALANCE
        row.inflow = _sum(frames.income)
        row.spend = _sum(frames.expenses)
        row.transport = _sum(frames.transport)
        lent_v = _without_roundtrips(frames.lent)
        borr_v = _without_roundtrips(frames.borrowed)
        row.lent_out = _sum(lent_v)
        row.borrowed_in = _sum(borr_v)
        if not lent_v.empty:
            row.lent_returned = _sum(lent_v, lent_v["paid_back"] == 1)
        if not borr_v.empty:
            row.borrowed_repaid = _sum(borr_v, borr_v["paid_back"] == 1)
        row.closing = row.opening + row.net
        prev_key = None
    else:
        row = series.get(key) or MonthRow(key=key)
        prev_key = shift_month(key, -1)

    snap = Snapshot(key=key, label=month_label(key), row=row)

    # Outstanding obligations are always shown in full: a debt does not belong to
    # the month it was created in, it belongs to right now, until it is settled.
    if not frames.lent.empty:
        open_lent = frames.lent[frames.lent["paid_back"] == 0]
        snap.receivable_open = _sum(open_lent)
        snap.receivable_count = len(open_lent)
    if not frames.borrowed.empty:
        open_borr = frames.borrowed[frames.borrowed["paid_back"] == 0]
        snap.payable_open = _sum(open_borr)
        snap.payable_count = len(open_borr)

    snap.prev_key = prev_key
    if prev_key and prev_key in series:
        snap.prev_outflow = series[prev_key].outflow

    # --- spending by category, transport folded in as its own platform ---
    exp = _in_period(frames.expenses, key)
    records = []
    if not exp.empty:
        grouped = exp.groupby("category", as_index=False)["amount"].sum()
        records = grouped.to_dict("records")
    trans_total = _sum(_in_period(frames.transport, key))
    if trans_total > 0:
        merged = next((r for r in records if r["category"] == "Transportation"), None)
        if merged:
            merged["amount"] += trans_total
        else:
            records.append({"category": "Transportation", "amount": trans_total})
    if records:
        snap.by_category = (pd.DataFrame(records)
                            .sort_values("amount", ascending=False)
                            .reset_index(drop=True))

    snap.arrivals = _arrivals(frames, key)
    snap.departures = _departures(frames, key)
    return snap


def _arrivals(frames: Frames, key: str) -> pd.DataFrame:
    """Every cash movement toward you, as board rows."""
    rows = []
    inc = _in_period(frames.income, key)
    for r in inc.to_dict("records"):
        rows.append({"date": r["date"], "label": r["source"],
                     "platform": "Income", "amount": r["amount"],
                     "kind": "income", "id": r["id"]})

    lent_visible = _without_roundtrips(frames.lent)
    if not lent_visible.empty:
        repaid = lent_visible[lent_visible["paid_back"] == 1]
        if key != ALL_TIME:
            repaid = repaid[repaid["_settled_m"] == key]
        for r in repaid.to_dict("records"):
            rows.append({"date": r.get("settled_date") or r["date"],
                         "label": f"{r['person']} repaid you",
                         "platform": "Returned", "amount": r["amount"],
                         "kind": "lent_returned", "id": r["id"]})

    borr = _in_period(_without_roundtrips(frames.borrowed), key)
    for r in borr.to_dict("records"):
        rows.append({"date": r["date"], "label": f"Borrowed from {r['lender']}",
                     "platform": "Loan", "amount": r["amount"],
                     "kind": "borrowed", "id": r["id"]})

    if not rows:
        return pd.DataFrame(columns=["date", "label", "platform", "amount", "kind", "id"])
    return pd.DataFrame(rows).sort_values("date", ascending=False).reset_index(drop=True)


def _departures(frames: Frames, key: str) -> pd.DataFrame:
    """Every cash movement away from you, as board rows."""
    rows = []
    exp = _in_period(frames.expenses, key)
    for r in exp.to_dict("records"):
        rows.append({"date": r["date"], "label": r["description"],
                     "platform": r["category"], "amount": r["amount"],
                     "kind": "expense", "id": r["id"]})

    trans = _in_period(frames.transport, key)
    for r in trans.to_dict("records"):
        rows.append({"date": r["date"], "label": "Transport",
                     "platform": "Transportation", "amount": r["amount"],
                     "kind": "transport", "id": r["id"]})

    lent = _in_period(_without_roundtrips(frames.lent), key)
    for r in lent.to_dict("records"):
        rows.append({"date": r["date"], "label": f"Lent to {r['person']}",
                     "platform": "Lent", "amount": r["amount"],
                     "kind": "lent", "id": r["id"]})

    borrowed_visible = _without_roundtrips(frames.borrowed)
    if not borrowed_visible.empty:
        repaid = borrowed_visible[borrowed_visible["paid_back"] == 1]
        if key != ALL_TIME:
            repaid = repaid[repaid["_settled_m"] == key]
        for r in repaid.to_dict("records"):
            rows.append({"date": r.get("settled_date") or r["date"],
                         "label": f"Repaid {r['lender']}",
                         "platform": "Settled", "amount": r["amount"],
                         "kind": "borrowed_repaid", "id": r["id"]})

    if not rows:
        return pd.DataFrame(columns=["date", "label", "platform", "amount", "kind", "id"])
    return pd.DataFrame(rows).sort_values("date", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------- formatting

# ---- display currency -------------------------------------------------
# Every stored amount is PKR. These two hold whatever the board is being READ
# in, and are applied at format time only — nothing in the database is ever
# rewritten, so switching currency is a view change and can be undone by
# switching back. app.py sets them once per run from rates.py.
_DISPLAY_CODE = "PKR"
_DISPLAY_SYMBOL = "Rs."
_DISPLAY_RATE = 1.0          # PKR per one unit of the display currency


def set_display_currency(code: str, symbol: str, rate: float) -> None:
    global _DISPLAY_CODE, _DISPLAY_SYMBOL, _DISPLAY_RATE
    _DISPLAY_CODE = code
    _DISPLAY_SYMBOL = symbol
    _DISPLAY_RATE = float(rate) if rate else 1.0


def display_currency() -> tuple[str, str, float]:
    return _DISPLAY_CODE, _DISPLAY_SYMBOL, _DISPLAY_RATE


def to_display(value: float) -> float:
    """A stored PKR amount as a number in the currency being displayed."""
    try:
        return float(value) / _DISPLAY_RATE
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def money(value: float, decimals: int = 2) -> str:
    """The one money format: symbol, grouped thousands, fixed decimals.

    Takes PKR — the unit everything is stored and calculated in — and converts
    on the way out, so callers never have to know which currency is on screen.
    """
    return f"{_DISPLAY_SYMBOL} {to_display(value):,.{decimals}f}"


def money_compact(value: float) -> str:
    """For the board figures, where two decimals of zero are noise.

    Converted like money(). Small foreign amounts keep two decimals — $3.60
    rounded to "4" would be a worse figure than the rupee one it replaced.
    """
    converted = to_display(value)
    av = abs(converted)
    sign = "-" if converted < 0 else ""
    if av >= 1_000_000:
        return f"{sign}{av / 1_000_000:,.2f}M"
    if av < 1000 and _DISPLAY_CODE != "PKR":
        return f"{sign}{av:,.2f}"
    return f"{sign}{av:,.0f}"


def display_date(value) -> str:
    try:
        return pd.to_datetime(value).strftime("%d/%m/%Y")
    except Exception:
        return str(value)


def day_month(value) -> str:
    try:
        return pd.to_datetime(value).strftime("%d/%m")
    except Exception:
        return str(value)[:5]


def try_parse_date(value) -> str | None:
    """Best-effort parse of anything user- or sheet-supplied into ISO.

    Returns None when the value cannot be read as a date at all, so a caller
    that cares (the importer) can warn instead of silently mislabelling a row
    with today's date.
    """
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text:
        return None
    text = text[:10]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y",
                "%d/%m/%y", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    try:
        return pd.to_datetime(text, dayfirst=True).strftime("%Y-%m-%d")
    except Exception:
        return None


def parse_date(value) -> str:
    """Same as try_parse_date, but falls back to today when unparseable —
    for call sites where "today" is genuinely the right default (a blank date
    field in a form, a bot tool call with no date given).
    """
    return try_parse_date(value) or str(date.today())


def clean_amount(value) -> float:
    """Strip currency noise from a sheet cell and return a positive float."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    if isinstance(value, (int, float)):
        return float(abs(value))
    text = (str(value)
            .replace("Rs.", "").replace("Rs", "").replace("PKR", "")
            .replace(",", "").replace("−", "-")
            # Spaces are a thousands separator in plenty of exports
            # ("PKR 2 000"), and spreadsheets emit the non-breaking and narrow
            # no-break variants rather than a plain one. Left in, float() threw
            # and the row was silently dropped as "no readable amount" — real
            # data lost to a space.
            .replace(" ", "").replace(" ", "").replace(" ", "")
            .replace("'", "").replace(" ", "").strip())
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    try:
        return abs(float(text))
    except ValueError:
        return 0.0
