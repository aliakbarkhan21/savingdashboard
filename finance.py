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

Debts where no cash moved
-------------------------
The model above assumes a debt begins with a transfer. Often it does not. A
friend buys your concert ticket: you owe him 3,000, but nobody handed you
3,000, and treating it as a borrowing would inflate your cash on hand by money
you never held. The mirror case is covering someone's bill on a card — the
expense is already logged, so booking the receivable as a second departure
would take the same 3,000 out twice.

So a debt carries a `kind` (see `db.CASH` / `db.COVERED`) and only the opening
leg is conditional:

    kind     opening leg                 settlement leg
    cash     moves cash (as above)       reverses it
    covered  nothing — no cash moved     moves cash

Both kinds owe and are owed identically; `receivable_open`, `payable_open` and
net worth do not look at `kind` at all. Only cash on hand does.
"""
from __future__ import annotations

import calendar
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
    "lent": ["id", "date", "person", "amount", "paid_back", "settled_date", "kind"],
    "borrowed": ["id", "date", "lender", "amount", "paid_back", "settled_date", "kind"],
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
    if name in ("lent", "borrowed"):
        # A file migrated mid-session, or a hand-edited row, can leave this
        # missing or blank. Absent means the old schema, and the old schema
        # only ever held cash transfers.
        if "kind" not in df.columns:
            df["kind"] = db.CASH
        df["kind"] = df["kind"].where(df["kind"].isin(list(db.KINDS)), db.CASH)
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


def _cash_leg(df):
    """Rows whose *opening* leg actually moved cash.

    A COVERED debt has no opening leg — nobody handed anything over — so it
    must not be counted as cash out when lent, or cash in when borrowed. Its
    settlement still counts, and is taken from the unfiltered frame.
    """
    if df.empty or "kind" not in df.columns:
        return df
    return df[df["kind"] == db.CASH]


def debt_cash_contribution(table: str, amount: float, kind: str,
                           settled: bool) -> float:
    """What one debt row currently contributes to cash on hand.

    Deleting the row reverses exactly this, which is what the confirmation in
    the debts table quotes before anything is removed. It lives here rather
    than in the UI so the figure shown and the figure the model produces come
    from one definition and cannot drift apart.
    """
    moved = (kind == db.CASH)
    if table == "lent":
        # Cash out when handed over, back in when repaid.
        return (-amount if moved else 0.0) + (amount if settled else 0.0)
    # borrowed: cash in when received, out again when repaid.
    return (amount if moved else 0.0) + (-amount if settled else 0.0)


def _roundtrip_mask(df):
    """Rows opened and settled inside the same month, where both legs cancel."""
    if df.empty or "paid_back" not in df.columns or "_settled_m" not in df.columns:
        return None
    same = (df["paid_back"] == 1) & (df["_settled_m"] == df["_m"])
    if "kind" in df.columns:
        # Only a CASH debt is a true round trip. A COVERED one has nothing on
        # the opening leg for the settlement to cancel against, so netting it
        # away would delete a payment that really did leave the account.
        same = same & (df["kind"] == db.CASH)
    return same


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
        # The opening leg counts only for debts where cash changed hands.
        lent_c = _cash_leg(lent_v)
        borr_c = _cash_leg(borr_v)
        row.lent_out = _sum(lent_c, lent_c["_m"] == key) if not lent_c.empty else 0.0
        row.borrowed_in = _sum(borr_c, borr_c["_m"] == key) if not borr_c.empty else 0.0

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
        row.lent_out = _sum(_cash_leg(lent_v))
        row.borrowed_in = _sum(_cash_leg(borr_v))
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

    records = _category_totals(frames, key)
    if records:
        snap.by_category = (pd.DataFrame(records)
                            .sort_values("amount", ascending=False)
                            .reset_index(drop=True))

    snap.arrivals = _arrivals(frames, key)
    snap.departures = _departures(frames, key)
    return snap


def _category_totals(frames: Frames, key: str) -> list[dict]:
    """Spending by category for one period, transport folded into its platform.

    Transport is its own ledger AND a spending category, which is a known
    duplication in the model. Wherever a category total is reported the two must
    be summed the same way, so both the donut and the trend read this — a second
    implementation is how they would come to disagree by a few hundred rupees
    and neither would look wrong on its own.
    """
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
    return records


def category_series(frames: Frames, keys: list[str]) -> dict[str, list[float]]:
    """Spend per category across `keys`, in the order given.

    Every category that appears in any of those months gets a full-length list,
    zero-filled where it had no spending — so the caller can draw them against a
    shared axis without having to reconcile ragged rows.
    """
    per_month = [{r["category"]: float(r["amount"])
                  for r in _category_totals(frames, k)} for k in keys]
    names = sorted({c for month in per_month for c in month})
    return {name: [month.get(name, 0.0) for month in per_month] for name in names}


def days_in_period(key: str) -> int:
    """How many days the month `key` holds. 0 for All Time, which has no shape."""
    if key == ALL_TIME:
        return 0
    year, month = int(key[:4]), int(key[5:7])
    return calendar.monthrange(year, month)[1]


def _daily_rows(frames: Frames, key: str):
    """Every spending row inside one month, paired with its day of the month.

    Transport is folded into Transportation here for the same reason
    `_category_totals` does it: two ledgers, one category, and a single place
    that decides how they add up.
    """
    days = days_in_period(key)
    if not days:
        return []
    out = []
    exp = _in_period(frames.expenses, key)
    if not exp.empty:
        for row in exp.to_dict("records"):
            out.append((str(row["date"])[8:10], str(row["category"]),
                        float(row["amount"])))
    trans = _in_period(frames.transport, key)
    if not trans.empty:
        for row in trans.to_dict("records"):
            out.append((str(row["date"])[8:10], "Transportation",
                        float(row["amount"])))
    return [(int(d), c, a) for d, c, a in out if d.isdigit() and 1 <= int(d) <= days]


def category_by_day(frames: Frames, key: str) -> dict[int, list[tuple[str, float]]]:
    """What one day of a month spent, split by category, heaviest first.

    The calendar square already knows a day's total. This is what the back of
    it needs: the same day broken out, so a dark square can say what made it
    dark instead of only that something did.

    Built from `_daily_rows`, which is also where the day totals and the
    sparklines come from — a day cannot add up to one figure on the face of
    the card and a different one on the back of it.

    Days with nothing spent are simply absent; the caller decides what an empty
    day should say, and it is not the same sentence as "no data".
    """
    out: dict[int, dict[str, float]] = {}
    for day, category, amount in _daily_rows(frames, key):
        bucket = out.setdefault(day, {})
        bucket[category] = bucket.get(category, 0.0) + amount
    return {day: sorted(cats.items(), key=lambda kv: (-kv[1], kv[0]))
            for day, cats in out.items()}


def category_daily(frames: Frames, key: str) -> dict[str, list[float]]:
    """Cumulative spend per category through one month, day by day.

    Cumulative rather than per-day, and the choice is about what a 104x26px
    line can actually say. Per-day, a category with four purchases in it is
    four spikes on an empty floor — noise at that size, and indistinguishable
    from a different category with four purchases somewhere else. Cumulative,
    the same row reads as a shape: a step early and then flat is one big buy at
    the start of the month, a steady climb is a habit, a late kick is a month
    that got away at the end.

    A category with nothing in this month gets a list of zeros, which draws as
    the flat line that says exactly that. Every category is given a full-length
    list so the rows share an axis.

    Days beyond today in the month in progress are still included: the line
    running flat to the right edge IS the month having not happened yet, and
    truncating it would make a half-finished month look like a completed one.
    """
    days = days_in_period(key)
    if not days:
        return {}
    rows = _daily_rows(frames, key)
    names = sorted({c for _, c, _ in rows})
    per_day = {name: [0.0] * days for name in names}
    for day, category, amount in rows:
        per_day[category][day - 1] += amount
    out = {}
    for name, values in per_day.items():
        running = 0.0
        cumulative = []
        for value in values:
            running += value
            cumulative.append(running)
        out[name] = cumulative
    return out


def daily_outflow(frames: Frames, key: str) -> list[float]:
    """What left on each day of one month, in day order. [] for All Time.

    The whole month across every category, which is the other half of the
    question `category_daily` answers per row: not "how did this category
    accumulate" but "which days were expensive".
    """
    days = days_in_period(key)
    if not days:
        return []
    totals = [0.0] * days
    for day, _, amount in _daily_rows(frames, key):
        totals[day - 1] += amount
    return totals


def income_by_source(frames: Frames, key: str) -> pd.DataFrame:
    """Arrivals grouped by the source they were logged under.

    The mirror of `_category_totals`. Every income row has carried a `source`
    since the first version and nothing has ever grouped them, so "where does
    my money actually come from" was a question the board held the data for and
    could not answer.
    """
    inc = _in_period(frames.income, key)
    if inc.empty:
        return pd.DataFrame()
    return (inc.groupby("source", as_index=False)["amount"].sum()
               .sort_values("amount", ascending=False)
               .reset_index(drop=True))


def source_series(frames: Frames, keys: list[str]) -> dict[str, list[float]]:
    """Income per source across `keys`, in the order given. Zero-filled.

    The mirror of `category_series`, and deliberately month-stepped even
    though the category trend beside it steps by day within a month. Spending
    happens most days, so a month of days has a shape worth drawing; income
    lands on one or two dates and a cumulative day line for it would be a
    single step and a flat run — a picture of the pay date, not of the pay.
    Whether an income is steady or lumpy is a question about months, so months
    are what this returns.
    """
    per_month = [{str(r["source"]): float(r["amount"])
                  for r in income_by_source(frames, k).to_dict("records")}
                 for k in keys]
    names = sorted({s for month in per_month for s in month})
    return {name: [month.get(name, 0.0) for month in per_month]
            for name in names}


def _days_outstanding(value) -> int:
    try:
        started = datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return 0
    return max(0, (date.today() - started).days)


def people_ledger(frames: Frames) -> list[dict]:
    """Open debts rolled up per person, with both directions netted.

    One person can sit on both sides at once — you covered their taxi in March,
    they bought your router in August — and the board showed that as rows in two
    separate tables with the net position nowhere. Netting is the whole point:
    what you actually settle with someone is the difference.

    Only unsettled rows count. A settled debt is a closed conversation, and
    including it would make a person who has always paid you back on time look
    identical to one who never has.
    """
    people: dict[str, dict] = {}

    def bucket(name: str) -> dict:
        return people.setdefault(name, {
            "name": name, "owed_to_you": 0.0, "you_owe": 0.0,
            "rows": 0, "oldest_days": 0,
        })

    for table, who, field in (("lent", "person", "owed_to_you"),
                              ("borrowed", "lender", "you_owe")):
        df = getattr(frames, table)
        if df.empty:
            continue
        for r in df[df["paid_back"] == 0].to_dict("records"):
            name = str(r.get(who) or "").strip() or "Unnamed"
            b = bucket(name)
            b[field] += float(r["amount"])
            b["rows"] += 1
            b["oldest_days"] = max(b["oldest_days"], _days_outstanding(r["date"]))

    for b in people.values():
        b["net"] = b["owed_to_you"] - b["you_owe"]
        b["both_ways"] = b["owed_to_you"] > 0 and b["you_owe"] > 0
    # Largest obligation first, either direction — the biggest number is the one
    # worth acting on whichever way it points.
    return sorted(people.values(), key=lambda b: -abs(b["net"]))


def usual_daily_outflow(series: dict, key: str) -> float | None:
    """Spend per day across the completed months before `key`.

    The Capacity panel already projects where the month closes from the current
    burn, but a rate with nothing to compare it against says very little: only
    someone who already knows their own habits can read "Rs. 400 a day" as fast
    or slow. This is the baseline that makes it legible.

    Returns None when there is no completed month to average — one month of
    history is not a habit, and inventing a baseline from it would be worse
    than saying nothing.
    """
    earlier = [k for k in sorted(series) if k < key and series[k].outflow > 0]
    if not earlier:
        return None
    days = 0
    spent = 0.0
    for k in earlier:
        year, month = int(k[:4]), int(k[5:7])
        days += calendar.monthrange(year, month)[1]
        spent += series[k].outflow
    return (spent / days) if days else None


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

    # Only cash borrowings arrive. A debt someone covered on your behalf put
    # nothing in your hand, so listing it here would show an arrival that never
    # happened — and would not match the arrivals headline, which excludes it.
    borr = _in_period(_cash_leg(_without_roundtrips(frames.borrowed)), key)
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

    # Same rule on this side: covering someone's bill on a card already logged
    # as an expense is not a second departure.
    lent = _in_period(_cash_leg(_without_roundtrips(frames.lent)), key)
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
