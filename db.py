"""
Storage layer for Loot Ledger.

SQLite, one local file, zero setup. Every write goes through a helper here so the
rest of the app never builds SQL by hand.

Schema note: `lent` and `borrowed` carry a `settled_date` alongside `paid_back`.
Without it a repayment has no date, so it cannot be attributed to a month, and any
month-by-month cash figure that involves debt is guesswork. `init_db` migrates
older files in place.

Money note: `amount` is stored as integer paisa (rupees * 100), not a rupee
float. SQLite's REAL affinity happens to round-trip whole-rupee floats exactly,
but repeated float arithmetic on fractional-rupee amounts drifts over many
entries, and an integer column can't drift at all. This is a storage-layer
detail only — every add_*/get_* function converts at the boundary, so the rest
of the app (finance.py, importer.py, bot.py, app.py) works in rupee floats
throughout and never sees paisa. `init_db` migrates older files in place.
"""
import os
import sqlite3
from pathlib import Path

# Overridable so a second instance can run against a scratch file — useful for
# checking the empty state without disturbing real records.
DB_PATH = Path(os.environ.get("LOOT_LEDGER_DB") or (Path(__file__).parent / "tracker.db"))

CATEGORIES = [
    "Food", "Games", "Hangouts", "Shopping",
    "Subscriptions", "Transportation", "Utilities", "Other",
]

# Every ledger the app knows about, in board order.
LEDGERS = ("expenses", "transport", "income", "lent", "borrowed")

_UNIT_FLAG = "amount_unit"

# ---------- how a debt was actually incurred ----------
# A debt has two separate facts in it: the obligation, and whether cash moved
# when it started. They are usually the same event, but not always.
#
#   CASH     someone handed over money. Borrowing puts cash in your pocket now;
#            lending takes it out now. Both reverse on settlement.
#   COVERED  nobody handed over money. A friend paid for your ticket, or you
#            paid for theirs on a card already logged as an expense. The
#            obligation is real, but your cash on hand did not move — and it
#            must not, or the ledger invents money that was never in your hand.
#            Only settling it moves cash.
#
# Every row written before this column existed was a real cash transfer, so
# CASH is the default and the migration backfills it.
CASH = "cash"
COVERED = "covered"
KINDS = (CASH, COVERED)


def clean_kind(value):
    """Anything unrecognised falls back to CASH — the historic behaviour."""
    return value if value in KINDS else CASH


def _to_paisa(amount) -> int:
    return int(round(float(amount) * 100))


def _from_paisa(value) -> float:
    return round(value / 100.0, 2)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _columns(cur, table):
    return {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}


def init_db():
    """Create tables if absent and migrate older files. Safe to call every run."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transport (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            source TEXT NOT NULL,
            amount REAL NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            person TEXT NOT NULL,
            amount REAL NOT NULL,
            paid_back INTEGER NOT NULL DEFAULT 0,
            settled_date TEXT,
            kind TEXT NOT NULL DEFAULT 'cash'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS borrowed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            lender TEXT NOT NULL,
            amount REAL NOT NULL,
            paid_back INTEGER NOT NULL DEFAULT 0,
            settled_date TEXT,
            kind TEXT NOT NULL DEFAULT 'cash'
        )
    """)

    # --- migrate files created before `kind` existed ---
    # NOT NULL DEFAULT on ADD COLUMN backfills every existing row with 'cash',
    # which is the correct reading of them: before this column there was no way
    # to record a debt where cash had not moved, so every one of them had.
    for table in ("lent", "borrowed"):
        if "kind" not in _columns(cur, table):
            cur.execute(
                f"ALTER TABLE {table} ADD COLUMN kind TEXT NOT NULL DEFAULT '{CASH}'")

    # --- migrate files created before settled_date existed ---
    for table in ("lent", "borrowed"):
        if "settled_date" not in _columns(cur, table):
            cur.execute(f"ALTER TABLE {table} ADD COLUMN settled_date TEXT")
            # Rows already marked paid have no recorded settle date. Fall back to
            # the origination date so they at least land in a real month rather
            # than vanishing from every period.
            cur.execute(
                f"UPDATE {table} SET settled_date = date "
                f"WHERE paid_back = 1 AND settled_date IS NULL"
            )

    cur.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            category TEXT PRIMARY KEY,
            monthly_cap REAL NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recurring (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            kind TEXT NOT NULL,
            category TEXT,
            amount REAL NOT NULL,
            day_of_month INTEGER NOT NULL,
            last_logged TEXT
        )
    """)

    # --- migrate amounts from rupee floats to integer paisa, once ---
    unit_row = cur.execute("SELECT value FROM meta WHERE key = ?", (_UNIT_FLAG,)).fetchone()
    if unit_row is None:
        # Belt as well as braces. A missing marker is meant to mean "this file
        # predates paisa", but it can also mean the marker was lost — and
        # scaling live rows on a guess is not recoverable. With every ledger
        # empty there is nothing that could need converting either way, so the
        # marker is simply restored and no arithmetic is done.
        rows = sum(cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                   for t in LEDGERS)
        if rows:
            for table in LEDGERS:
                cur.execute(
                    f"UPDATE {table} SET amount = CAST(ROUND(amount * 100) AS INTEGER)")
        cur.execute("INSERT INTO meta (key, value) VALUES (?, ?)", (_UNIT_FLAG, "paisa"))

    for table in LEDGERS:
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_date ON {table}(date)")

    conn.commit()
    conn.close()


# ---------- Inserts ----------

def add_expense(entry_date, description, category, amount):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO expenses (date, description, category, amount) VALUES (?,?,?,?)",
        (entry_date, description, category, _to_paisa(amount)),
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def add_transport(entry_date, amount):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO transport (date, amount) VALUES (?,?)",
        (entry_date, _to_paisa(amount)),
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def add_income(entry_date, source, amount):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO income (date, source, amount) VALUES (?,?,?)",
        (entry_date, source, _to_paisa(amount)),
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def add_lent(entry_date, person, amount, kind=CASH):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO lent (date, person, amount, kind) VALUES (?,?,?,?)",
        (entry_date, person, _to_paisa(amount), clean_kind(kind)),
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def add_borrowed(entry_date, lender, amount, kind=CASH):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO borrowed (date, lender, amount, kind) VALUES (?,?,?,?)",
        (entry_date, lender, _to_paisa(amount), clean_kind(kind)),
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def add_many(table, rows):
    """Bulk insert for the importer. `rows` is a list of dicts keyed by column."""
    if not rows:
        return 0
    cols = list(rows[0].keys())
    placeholders = ",".join("?" for _ in cols)
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
    conn = get_connection()
    conn.executemany(sql, [
        tuple(_to_paisa(r[c]) if c == "amount" else r[c] for c in cols)
        for r in rows
    ])
    conn.commit()
    conn.close()
    return len(rows)


# ---------- Updates and deletes ----------

def set_paid_back(table, row_id, paid_back, settled_date=None):
    """`table` must be 'lent' or 'borrowed'. Clearing the flag clears the date."""
    if table not in ("lent", "borrowed"):
        raise ValueError(f"set_paid_back: unknown table {table!r}")
    conn = get_connection()
    if paid_back:
        conn.execute(
            f"UPDATE {table} SET paid_back = 1, settled_date = ? WHERE id = ?",
            (settled_date, row_id),
        )
    else:
        conn.execute(
            f"UPDATE {table} SET paid_back = 0, settled_date = NULL WHERE id = ?",
            (row_id,),
        )
    conn.commit()
    conn.close()


# Columns a row may legitimately carry, per ledger. Anything not on this list
# is refused rather than interpolated into SQL — the table name and every
# column name below reach a query as identifiers, which cannot be
# parameterised, so they are checked against a fixed set instead.
EDITABLE = {
    "expenses":  ("date", "description", "category", "amount"),
    "transport": ("date", "amount"),
    "income":    ("date", "source", "amount"),
    "lent":      ("date", "person", "amount", "paid_back", "settled_date", "kind"),
    "borrowed":  ("date", "lender", "amount", "paid_back", "settled_date", "kind"),
}


def update_row(table, row_id, **fields):
    """Change one existing row. Amounts convert to paisa like every other
    write, so an edited figure is stored the same way an added one is."""
    if table not in LEDGERS:
        raise ValueError(f"update_row: unknown table {table!r}")
    allowed = EDITABLE[table]
    sets, values = [], []
    for column, value in fields.items():
        if column not in allowed:
            raise ValueError(f"update_row: {column!r} is not editable on {table}")
        sets.append(f"{column} = ?")
        values.append(_to_paisa(value) if column == "amount" else value)
    if not sets:
        return 0
    values.append(row_id)
    conn = get_connection()
    cur = conn.execute(f"UPDATE {table} SET {','.join(sets)} WHERE id = ?", values)
    conn.commit()
    changed = cur.rowcount
    conn.close()
    return changed


def rename_category(old, new):
    """Move every expense from one category to another.

    Used to merge duplicates that crept in from imports — 'Transport' and
    'Transportation' meaning the same thing, split across two slices of the
    donut and two budget lines. Renaming beats deleting and re-entering: the
    rows keep their dates and amounts, only the label moves.
    """
    conn = get_connection()
    cur = conn.execute("UPDATE expenses SET category = ? WHERE category = ?",
                       (new, old))
    conn.commit()
    moved = cur.rowcount
    conn.close()
    return moved


def delete_row(table, row_id):
    if table not in LEDGERS:
        raise ValueError(f"delete_row: unknown table {table!r}")
    conn = get_connection()
    conn.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()


def safety_backup(tag="wipe"):
    """Copy the whole database file before something irreversible touches it.

    This exists because a wipe once went through with no way back. Restoring
    from one of these is a file copy; the alternative is retyping a month of
    records from memory, which is not an alternative. Cheap insurance: the file
    is well under a megabyte, and a failure here must never block the caller —
    if the copy cannot be made, the caller still proceeds, it just proceeds
    unprotected rather than not at all.

    Returns the backup path, or None if it could not be written.
    """
    import shutil
    from datetime import datetime
    if not Path(DB_PATH).exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = Path(f"{DB_PATH}.autobackup-{tag}-{stamp}")
    try:
        # Checkpoint anything sitting in a journal so the copy is complete.
        conn = get_connection()
        conn.execute("PRAGMA wal_checkpoint(FULL)")
        conn.close()
        shutil.copy2(DB_PATH, target)
        _prune_autobackups()
        return target
    except Exception:
        return None


def _prune_autobackups(keep=10):
    """Keep the most recent few. Unbounded backups would quietly fill a disk."""
    try:
        found = sorted(Path(DB_PATH).parent.glob(f"{Path(DB_PATH).name}.autobackup-*"))
        for old in found[:-keep]:
            old.unlink()
    except Exception:
        pass


def list_backups():
    """Every snapshot sitting beside the database, newest first.

    Covers both the automatic ones taken before a wipe and any hand-made
    `tracker.db.backup-*` copies. Each entry carries its row counts, because
    "restore a backup" is not a decision anyone can make from a filename — the
    only question that matters is how much is in it.
    """
    base = Path(DB_PATH)
    out = []
    for path in list(base.parent.glob(base.name + ".autobackup-*")) + \
                list(base.parent.glob(base.name + ".backup*")):
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            counts = {}
            for table in LEDGERS:
                try:
                    counts[table] = conn.execute(
                        f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                except sqlite3.Error:
                    counts[table] = 0
            conn.close()
        except sqlite3.Error:
            continue                      # not a readable database; skip it
        stat = path.stat()
        out.append({"path": path, "name": path.name, "taken": stat.st_mtime,
                    "size": stat.st_size, "counts": counts,
                    "total": sum(counts.values()),
                    "automatic": ".autobackup-" in path.name})
    out.sort(key=lambda b: b["taken"], reverse=True)
    return out


def restore_backup(path):
    """Replace the live database with a snapshot.

    Takes a backup of what is being replaced first, so choosing the wrong
    snapshot is itself recoverable — a restore that could destroy the thing you
    were trying to protect would be a strange kind of safety feature.
    """
    import shutil
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    # Prove it is a usable ledger before overwriting anything with it.
    conn = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    try:
        for table in LEDGERS:
            conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    finally:
        conn.close()
    safety_backup("pre-restore")
    shutil.copy2(source, DB_PATH)
    init_db()                             # migrate an older snapshot in place
    return True


def clear_all():
    """Wipe every ledger. Used by demo.clear() only — no bot tool reaches this."""
    safety_backup("clear_all")
    conn = get_connection()
    for table in LEDGERS:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()


def erase_all():
    """True full wipe: every row in every ledger, plus every meta flag.

    Used by the settings "Erase everything" reset. Deliberately does not go
    through demo.clear() — that function exists to undo demo.seed() and only
    ever runs while demo rows are the only thing present, so a future change to
    what it considers "demo data" should never be able to leave real records
    behind on a full reset.
    """
    safety_backup("erase_all")
    conn = get_connection()
    for table in LEDGERS:
        conn.execute(f"DELETE FROM {table}")
    # Every meta key EXCEPT the schema markers. _UNIT_FLAG records that this
    # file already stores paisa; deleting it made init_db believe the file was
    # a pre-migration one and multiply every amount by 100 again on the next
    # start. That is how a reset, followed by fresh entries and a restart, came
    # back showing figures a hundred times too large.
    conn.execute("DELETE FROM meta WHERE key NOT IN (?)", (_UNIT_FLAG,))
    conn.commit()
    conn.close()


# ---------- Queries ----------

def _fetch_all(query):
    conn = get_connection()
    rows = conn.execute(query).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        if d.get("amount") is not None:
            d["amount"] = _from_paisa(d["amount"])
        out.append(d)
    return out


def get_expenses():
    return _fetch_all("SELECT * FROM expenses ORDER BY date DESC, id DESC")


def get_transport():
    return _fetch_all("SELECT * FROM transport ORDER BY date DESC, id DESC")


def get_income():
    return _fetch_all("SELECT * FROM income ORDER BY date DESC, id DESC")


def get_lent():
    return _fetch_all("SELECT * FROM lent ORDER BY date DESC, id DESC")


def get_borrowed():
    return _fetch_all("SELECT * FROM borrowed ORDER BY date DESC, id DESC")


# ---------- Budgets ----------

def set_budget(category, monthly_cap):
    conn = get_connection()
    conn.execute(
        "INSERT INTO budgets (category, monthly_cap) VALUES (?,?) "
        "ON CONFLICT(category) DO UPDATE SET monthly_cap = excluded.monthly_cap",
        (category, float(monthly_cap)),
    )
    conn.commit()
    conn.close()


def get_budgets() -> dict:
    """{category: monthly_cap} for every category with a cap set."""
    conn = get_connection()
    rows = conn.execute("SELECT category, monthly_cap FROM budgets").fetchall()
    conn.close()
    return {r["category"]: float(r["monthly_cap"]) for r in rows}


def delete_budget(category):
    conn = get_connection()
    conn.execute("DELETE FROM budgets WHERE category = ?", (category,))
    conn.commit()
    conn.close()


# ---------- Recurring transactions ----------

def add_recurring(label, kind, category, amount, day_of_month):
    """`kind` is 'expense' or 'income'; `category` is only meaningful for
    'expense' (None for income). Amount is stored in paisa like the ledgers —
    get_recurring() goes through _fetch_all, which converts every "amount"
    column back to rupees, so this must match that convention."""
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO recurring (label, kind, category, amount, day_of_month) "
        "VALUES (?,?,?,?,?)",
        (label, kind, category, _to_paisa(amount), int(day_of_month)),
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def get_recurring() -> list:
    return _fetch_all("SELECT * FROM recurring ORDER BY day_of_month, id")


def delete_recurring(row_id):
    conn = get_connection()
    conn.execute("DELETE FROM recurring WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()


def mark_recurring_logged(row_id, period_key):
    conn = get_connection()
    conn.execute("UPDATE recurring SET last_logged = ? WHERE id = ?", (period_key, row_id))
    conn.commit()
    conn.close()


def set_meta(key, value):
    conn = get_connection()
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?,?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, None if value is None else str(value)),
    )
    conn.commit()
    conn.close()


def get_meta(key, default=None):
    conn = get_connection()
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row[0] if row else default


def delete_meta(key):
    conn = get_connection()
    conn.execute("DELETE FROM meta WHERE key = ?", (key,))
    conn.commit()
    conn.close()


def row_counts():
    conn = get_connection()
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in LEDGERS}
    conn.close()
    return counts


def is_empty():
    return sum(row_counts().values()) == 0


if __name__ == "__main__":
    init_db()
    print(f"Database ready at {DB_PATH}")
    print(row_counts())
