"""
Sample data for Loot Ledger.

`tracker.db` ships empty, and an empty board is a bad first impression for
anyone opening this to see what it does. This seeds three months of plausible
records so the interface can be judged with data in it.

It is labelled everywhere it appears. `db.get_meta("demo_data")` is set while
sample rows are present, the board shows a banner, and clearing it is one
button. Nothing here is presented as anyone's real finances.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

import db
import finance

FLAG = "demo_data"


def is_active() -> bool:
    return db.get_meta(FLAG) == "1"


def _day(month_key: str, day: int) -> str:
    year, month = int(month_key[:4]), int(month_key[5:7])
    # Clamp so day 31 never falls off a short month.
    last = (date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)).day
    return date(year, month, min(day, last)).strftime("%Y-%m-%d")


# Description pools per category, so rows read like a real life rather than
# "Expense 1, Expense 2".
_ITEMS = {
    "Food": [("Grocery run", 3200, 6800), ("Lunch at the office", 450, 900),
             ("Karahi with the boys", 1800, 3400), ("Chai and paratha", 180, 420),
             ("Biryani delivery", 700, 1300), ("Fruit and vegetables", 900, 2100)],
    "Hangouts": [("Cinema ticket", 900, 1600), ("Coffee at Chaaye Khana", 650, 1200),
                 ("Cricket ground booking", 1200, 2500), ("Dinner out", 2200, 4500)],
    "Shopping": [("Kurta", 2500, 5200), ("Sneakers", 6500, 12000),
                 ("Phone case", 800, 1800), ("Headphones", 4500, 9000)],
    "Subscriptions": [("Netflix", 1100, 1100), ("Spotify", 599, 599),
                      ("GitHub Copilot", 2800, 2800), ("Domain renewal", 3500, 3500)],
    "Utilities": [("Electricity bill", 6500, 14000), ("Internet bill", 3500, 3500),
                  ("Mobile top-up", 800, 1500), ("Gas bill", 1800, 4200)],
    "Games": [("Steam sale", 1500, 4500), ("Mobile game top-up", 500, 1500)],
    "Other": [("Haircut", 600, 1200), ("Medicine", 700, 2400), ("Gift for Ammi", 3000, 7000)],
}


def seed(months: int = 3) -> dict:
    """Write sample rows for the last `months` months, including this one."""
    rng = random.Random(20260821)  # fixed so the sample is reproducible
    today = date.today()
    current = today.strftime("%Y-%m")
    keys = [finance.shift_month(current, -offset) for offset in range(months - 1, -1, -1)]

    counts = {k: 0 for k in ("income", "expenses", "transport", "lent", "borrowed")}

    for index, key in enumerate(keys):
        is_current = key == current
        cutoff = today.day if is_current else 31

        # --- salary lands on the 1st, freelance shows up sometimes ---
        if cutoff >= 1:
            db.add_income(_day(key, 1), "Monthly salary", 120000)
            counts["income"] += 1
        if index != 1 and cutoff >= 14:
            db.add_income(_day(key, 14), "Freelance project", rng.choice([18000, 25000, 32000]))
            counts["income"] += 1

        # --- day-to-day spending ---
        for category, pool in _ITEMS.items():
            picks = 1 if category in ("Subscriptions", "Games") else rng.randint(2, 4)
            for _ in range(picks):
                day = rng.randint(1, min(28, cutoff))
                if day > cutoff:
                    continue
                name, low, high = rng.choice(pool)
                amount = low if low == high else rng.randrange(low, high, 50)
                db.add_expense(_day(key, day), name, category, float(amount))
                counts["expenses"] += 1

        # --- transport, a few times a week ---
        for _ in range(rng.randint(6, 11)):
            day = rng.randint(1, min(28, cutoff))
            if day > cutoff:
                continue
            db.add_transport(_day(key, day), float(rng.randrange(150, 900, 50)))
            counts["transport"] += 1

    # --- debts, deliberately spread across states so every case is visible ---
    first, last = keys[0], keys[-1]

    settled = db.add_lent(_day(first, 8), "Hamza", 8000.0)
    db.set_paid_back("lent", settled, True, _day(last, 6))     # lent and returned
    counts["lent"] += 1

    db.add_lent(_day(keys[1] if len(keys) > 1 else first, 19), "Sara", 5500.0)
    counts["lent"] += 1                                        # still owed to Ali

    repaid = db.add_borrowed(_day(first, 22), "Usman", 12000.0)
    db.set_paid_back("borrowed", repaid, True, _day(last, 4))  # borrowed and repaid
    counts["borrowed"] += 1

    db.add_borrowed(_day(keys[1] if len(keys) > 1 else first, 11), "Bhai", 20000.0)
    counts["borrowed"] += 1                                    # Ali still owes

    db.set_meta(FLAG, "1")
    return counts


def clear() -> None:
    """Remove everything and drop the sample flag."""
    db.clear_all()
    db.delete_meta(FLAG)
