"""
CSV import for Loot Ledger.

The previous importer addressed cells by hardcoded position — row 6 onward for
expenses, column 15 for transport, rows 16 to 25 for lent — which meant it read
one specific Google Sheet and silently produced garbage or nothing for any other
shape. It also wiped all five ledgers before parsing, so a failed import
destroyed the existing data.

This version reads headers, guesses a mapping, lets the user correct it, shows
exactly what will be written, and appends by default.
"""
from __future__ import annotations

import csv
import io
from collections import Counter

import pandas as pd

import db
import finance

# What each ledger needs, and which header words hint at it.
SCHEMAS = {
    "expenses": {
        "label": "Expenses",
        "fields": {
            "date": {"required": True, "hints": ["date", "day", "when", "tarikh"]},
            "description": {"required": True, "hints": ["desc", "item", "detail", "note",
                                                        "particular", "narration", "name", "what"]},
            "category": {"required": False, "hints": ["categ", "type", "group", "head", "tag"]},
            "amount": {"required": True, "hints": ["amount", "amt", "value", "price",
                                                   "cost", "debit", "spent", "rs", "pkr"]},
        },
    },
    "income": {
        "label": "Income",
        "fields": {
            "date": {"required": True, "hints": ["date", "day", "when"]},
            "source": {"required": True, "hints": ["source", "from", "desc", "detail",
                                                   "particular", "name", "payer"]},
            "amount": {"required": True, "hints": ["amount", "amt", "value", "credit",
                                                   "received", "rs", "pkr"]},
        },
    },
    "transport": {
        "label": "Transport",
        "fields": {
            "date": {"required": True, "hints": ["date", "day", "when"]},
            "amount": {"required": True, "hints": ["amount", "amt", "fare", "cost", "rs", "pkr"]},
        },
    },
    "lent": {
        "label": "Lent out",
        "fields": {
            "date": {"required": True, "hints": ["date", "day", "when"]},
            # 'desc' sits last on purpose: a wide sheet has both a 'Person /
            # Description' and an expense 'Location / Description', and the
            # earlier hints must win before this one can match either.
            "person": {"required": True, "hints": ["person", "name", "who", "debtor",
                                                   "to", "desc"]},
            "amount": {"required": True, "hints": ["amount", "amt", "value", "rs", "pkr"]},
            "status": {"required": False, "hints": ["status", "settled", "paid", "returned",
                                                    "cleared", "recovered"]},
        },
    },
    "borrowed": {
        "label": "Borrowed",
        "fields": {
            "date": {"required": True, "hints": ["date", "day", "when"]},
            "lender": {"required": True, "hints": ["lender", "name", "who", "creditor",
                                                   "from", "desc"]},
            "amount": {"required": True, "hints": ["amount", "amt", "value", "rs", "pkr"]},
            "status": {"required": False, "hints": ["status", "settled", "paid", "returned",
                                                    "cleared", "repaid"]},
        },
    },
}

NONE_LABEL = "— not in this file —"

# A hand-kept sheet often carries every ledger side by side in one wide file:
# an expense block, then a lent block, then a borrowed block, then income —
# each with its own date/description/amount trio. Those repeated field names
# are what these tokens disambiguate. Without them the bare 'Date' and
# 'Amount' of the expense block score an exact 100 and win the mapping for
# *every* ledger, so importing Income silently writes the expense figures.
# 'expenses' owns no token on purpose: it is the unlabelled default block, and
# claiming words like "spent" would let a 'Total Spent' roll-up column win.
LEDGER_TOKENS = {
    "expenses": ("expense", "debit"),
    "income": ("income", "credit", "salary", "received", "earning"),
    "lent": ("lent", "owed to me", "receivable", "debtor"),
    "borrowed": ("borrowed", "owed by me", "payable", "lender", "creditor"),
    "transport": ("transport", "fare", "travel", "commute"),
}

# A column tagged for its own ledger must outrank a bare generic one even
# though the generic name matches more exactly. Larger than any base score.
_SECTION_BONUS = 200

# Roll-up columns sit beside the real data in exported sheets. Demoted rather
# than rejected: a file whose only amount column is literally called "Total"
# should still map, it just must never beat a real one.
_SUMMARY_HINTS = ("breakdown", "subtotal", "grand total", "running total")
_SUMMARY_PENALTY = 50

# A trailing roll-up line ("Total Expenses,,,24060") is not a transaction.
_SUMMARY_ROW_PREFIXES = ("total", "grand total", "subtotal", "sum", "net", "balance")

_TRUE_WORDS = {"true", "yes", "y", "1", "paid", "settled", "returned",
               "cleared", "done", "repaid", "recovered"}

# Real exports show up in more than one delimiter. Comma first since it is by
# far the common case and the tie-break default.
_DELIMS = [",", ";", "\t", "|"]

# How many leading lines a title/metadata banner might occupy before the real
# header row — bank and wallet exports commonly carry one.
_HEADER_SCAN_LINES = 20


def _decode(raw: bytes) -> str:
    """Decode raw bytes to text, tolerating the encodings real exports use."""
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except Exception as exc:  # try the next encoding
            last_error = exc
    raise ValueError(f"Could not read this file as text: {last_error}")


def _detect_delimiter(sample_lines: list[str]) -> str:
    """Sniff the field delimiter instead of assuming comma."""
    sample = "\n".join(sample_lines)
    try:
        return csv.Sniffer().sniff(sample, delimiters="".join(_DELIMS)).delimiter
    except Exception:
        pass
    # Sniffer gives up on short or irregular samples. Fall back to whichever
    # candidate splits the sample into the most consistent multi-column shape.
    best, best_score = ",", -1
    for d in _DELIMS:
        counts = [line.count(d) for line in sample_lines if line.strip()]
        if not counts or max(counts) == 0:
            continue
        common_count, frequency = Counter(counts).most_common(1)[0]
        if common_count == 0:
            continue
        score = frequency * common_count
        if score > best_score:
            best, best_score = d, score
    return best


def _header_score(cells: list[str]) -> int:
    """How much a row of cells looks like a header rather than data."""
    all_hints = {hint for schema in SCHEMAS.values()
                 for spec in schema["fields"].values() for hint in spec["hints"]}
    return sum(1 for c in cells if c and any(
        c == hint or c.startswith(hint) or hint in c for hint in all_hints))


def _best_header_row(rows: list[list[str]]) -> int:
    """Index of the most header-like row. Shared by CSV and spreadsheets, both
    of which commonly carry a title or metadata banner above the real one."""
    best_idx, best_score = 0, 0
    for i, cells in enumerate(rows[:_HEADER_SCAN_LINES]):
        if len(cells) < 2 or not any(c for c in cells):
            continue
        score = _header_score(cells)
        if score > best_score:
            best_idx, best_score = i, score
    return best_idx


def _find_header_row(lines: list[str], delimiter: str) -> int:
    """Some exports carry a title/metadata banner above the real header row."""
    return _best_header_row([[c.strip().lower() for c in line.split(delimiter)]
                             for line in lines])


def read_csv(uploaded) -> pd.DataFrame:
    """Read an upload into a DataFrame, tolerating messy real-world exports:

    BOM/non-UTF-8 encodings, a comma/semicolon/tab/pipe delimiter, and a
    title or metadata banner sitting above the real header row.
    """
    raw = uploaded.getvalue() if hasattr(uploaded, "getvalue") else uploaded.read()
    if not raw or not raw.strip():
        raise ValueError("This file is empty.")

    text = _decode(raw)
    lines = text.splitlines()
    sample = [line for line in lines if line.strip()][:_HEADER_SCAN_LINES]
    if not sample:
        raise ValueError("This file is empty.")

    delimiter = _detect_delimiter(sample)
    header_row = _find_header_row(lines, delimiter)

    try:
        df = pd.read_csv(io.StringIO(text), sep=delimiter, skiprows=header_row,
                         skip_blank_lines=True, dtype=str, engine="python")
    except Exception as exc:
        raise ValueError(f"Could not read this file as CSV: {exc}")

    df.columns = [str(c).strip() for c in df.columns]
    # Drop columns and rows that are entirely empty — exported sheets are full
    # of both.
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    if df.empty or len(df.columns) < 2:
        raise ValueError("No usable rows or columns found — check the file has a "
                         "header row with at least two columns.")
    return df


def _is_summary_column(name: str) -> bool:
    return any(h in name for h in _SUMMARY_HINTS) or name.startswith("total")


# Spreadsheets people actually keep their money in. .xls needs a different
# engine and is not installed by default, so it is offered but reported
# clearly if the reader is missing rather than failing as a mystery.
EXCEL_SUFFIXES = (".xlsx", ".xlsm", ".xltx", ".xltm", ".xls")
UPLOAD_TYPES = ["csv", "xlsx", "xlsm", "xls"]


def _is_excel(name: str) -> bool:
    return str(name or "").lower().endswith(EXCEL_SUFFIXES)


def excel_sheets(uploaded) -> list[str]:
    """Sheet names in a workbook, so a multi-sheet file can be chosen from."""
    raw = uploaded.getvalue() if hasattr(uploaded, "getvalue") else uploaded.read()
    try:
        return list(pd.ExcelFile(io.BytesIO(raw)).sheet_names)
    except Exception:
        return []


def read_excel(uploaded, sheet: str | None = None) -> pd.DataFrame:
    """Read one sheet of a workbook into the same shape read_csv returns.

    Read with no header first, then the header row is located by the same
    scoring the CSV path uses — a spreadsheet is at least as likely as an
    export to open with a title row, merged banner, or blank line above the
    real column names.
    """
    raw = uploaded.getvalue() if hasattr(uploaded, "getvalue") else uploaded.read()
    if not raw:
        raise ValueError("This file is empty.")
    try:
        book = pd.ExcelFile(io.BytesIO(raw))
    except ImportError as exc:
        raise ValueError(
            "This workbook needs an extra reader that is not installed "
            f"({exc}). Save the sheet as .xlsx or .csv and try again.")
    except Exception as exc:
        raise ValueError(f"Could not read this file as a spreadsheet: {exc}")

    names = list(book.sheet_names)
    if not names:
        raise ValueError("This workbook has no sheets.")
    chosen = sheet if sheet in names else names[0]

    try:
        blank = book.parse(chosen, header=None, dtype=str)
    except Exception as exc:
        raise ValueError(f"Could not read sheet {chosen!r}: {exc}")
    if blank.empty:
        raise ValueError(f"Sheet {chosen!r} is empty.")

    cells = [[("" if pd.isna(v) else str(v).strip().lower()) for v in row]
             for row in blank.values.tolist()]
    header_at = _best_header_row(cells)

    frame = blank.iloc[header_at + 1:].copy()
    frame.columns = [("" if pd.isna(c) else str(c).strip())
                     for c in blank.iloc[header_at].tolist()]
    # Excel columns with no header come through as Unnamed/blank; drop them
    # rather than offering them in the mapping dropdowns.
    frame = frame.loc[:, [bool(c) and not c.lower().startswith("unnamed")
                          for c in frame.columns]]
    frame = frame.dropna(axis=1, how="all").dropna(axis=0, how="all")
    if frame.empty or len(frame.columns) < 2:
        raise ValueError(f"No usable rows or columns found in sheet {chosen!r} — "
                         f"check it has a header row with at least two columns.")
    return frame.reset_index(drop=True)


def read_table(uploaded, sheet: str | None = None) -> pd.DataFrame:
    """Read an upload, whichever of the two shapes it happens to be."""
    name = getattr(uploaded, "name", "") or ""
    if _is_excel(name):
        return read_excel(uploaded, sheet)
    return read_csv(uploaded)


def _score(column: str, hints: list[str], ledger: str | None = None) -> int:
    name = column.strip().lower()
    if not name:
        return 0

    owned = any(token in name for token in LEDGER_TOKENS.get(ledger or "", ()))
    if ledger is not None and not owned:
        # A column belonging to a different block must never feed this ledger.
        # 'Amount Lent' is not this sheet's income, however well 'amount' reads.
        foreign = (token for other, tokens in LEDGER_TOKENS.items()
                   if other != ledger for token in tokens)
        if any(token in name for token in foreign):
            return 0

    base = 0
    for i, hint in enumerate(hints):
        if name == hint:
            base = 100 - i
            break
        if name.startswith(hint) or hint in name:
            base = 70 - i
            break
    if base <= 0:
        return 0

    if owned:
        base += _SECTION_BONUS
    if _is_summary_column(name):
        base -= _SUMMARY_PENALTY
    return max(base, 1)


def suggest_mapping(df: pd.DataFrame, ledger: str) -> dict[str, str]:
    """Best guess at which column feeds which field. Never reuses a column."""
    fields = SCHEMAS[ledger]["fields"]
    taken: set[str] = set()
    mapping: dict[str, str] = {}
    # Resolve the most distinctive fields first so 'amount' does not steal a
    # column that 'date' needed.
    order = sorted(fields, key=lambda f: 0 if fields[f]["required"] else 1)
    for field in order:
        best, best_score = NONE_LABEL, 0
        for col in df.columns:
            if col in taken:
                continue
            s = _score(col, fields[field]["hints"], ledger)
            if s > best_score:
                best, best_score = col, s
        mapping[field] = best
        if best != NONE_LABEL:
            taken.add(best)
    return mapping


def build_rows(df: pd.DataFrame, ledger: str, mapping: dict[str, str],
               default_category: str = "Other") -> tuple[list[dict], list[str]]:
    """Turn the mapped frame into insertable rows plus a list of skip reasons."""
    fields = SCHEMAS[ledger]["fields"]
    problems: list[str] = []

    for field, spec in fields.items():
        if spec["required"] and mapping.get(field, NONE_LABEL) == NONE_LABEL:
            problems.append(f"{field} is required but no column is mapped to it")
    if problems:
        return [], problems

    mapped_cols = [c for c in mapping.values() if c != NONE_LABEL]

    def cell(record, col):
        """The trimmed text of a mapped cell, '' for blank/NaN."""
        if col == NONE_LABEL:
            return ""
        value = record.get(col)
        if value is None or pd.isna(value):
            return ""
        return str(value).strip()

    # A file this app exported carries a 'ledger' column naming which ledger
    # each row came from. Without honouring it, restoring a backup into
    # Expenses would file the income and debt rows as expenses too. Only
    # trusted when the column actually holds ledger names, so an unrelated
    # sheet that happens to have a 'ledger' header is left alone.
    ledger_col = next((c for c in df.columns if c.strip().lower() == "ledger"), None)
    if ledger_col is not None:
        seen = {str(v).strip().lower() for v in df[ledger_col].dropna()}
        if not seen or not seen <= set(SCHEMAS):
            ledger_col = None

    rows: list[dict] = []
    skipped_amount = 0
    skipped_date = 0
    blank_rows = 0
    summary_rows = 0
    other_ledger_rows = 0
    for record in df.to_dict("records"):
        row: dict = {}

        if ledger_col is not None:
            value = record.get(ledger_col)
            name = "" if value is None or pd.isna(value) else str(value).strip().lower()
            if name and name != ledger:
                other_ledger_rows += 1
                continue

        # A wide sheet pads every block out to the longest one, so most rows
        # are genuinely empty for this ledger. That is the file's shape, not
        # lost data — counted quietly rather than reported as a failure.
        if not any(cell(record, c) for c in mapped_cols):
            blank_rows += 1
            continue

        # A trailing roll-up line carries a real number under a label instead
        # of a date. Recognised explicitly so it is never banked as a
        # transaction and never reported as an unreadable date.
        date_text = cell(record, mapping["date"]).lower()
        if any(date_text.startswith(p) for p in _SUMMARY_ROW_PREFIXES):
            summary_rows += 1
            continue

        amount = finance.clean_amount(record.get(mapping["amount"]))
        if amount <= 0:
            skipped_amount += 1
            continue

        parsed_date = finance.try_parse_date(record.get(mapping["date"]))
        if parsed_date is None:
            skipped_date += 1
            continue

        row["amount"] = amount
        row["date"] = parsed_date

        for field in fields:
            if field in ("amount", "date"):
                continue
            text = cell(record, mapping.get(field, NONE_LABEL))

            if field == "category":
                match = {c.lower(): c for c in db.CATEGORIES}.get(text.lower())
                row["category"] = match or default_category
            elif field == "description":
                row["description"] = text or "Imported expense"
            elif field == "source":
                row["source"] = text or "Imported income"
            elif field == "person":
                row["person"] = text or "Unknown"
            elif field == "lender":
                row["lender"] = text or "Unknown"
            elif field == "status":
                # Every row needs the key whether or not a status column was
                # mapped — add_many takes its column list from the first row.
                row["paid_back"] = 1 if text.lower() in _TRUE_WORDS else 0

        rows.append(row)

    if other_ledger_rows:
        problems.append(f"{other_ledger_rows} row(s) belong to another ledger in this "
                        f"file and were left for that import")
    if summary_rows:
        problems.append(f"{summary_rows} total/summary row(s) ignored — not transactions")
    if skipped_amount:
        problems.append(f"{skipped_amount} row(s) skipped — no readable positive amount")
    if skipped_date:
        problems.append(f"{skipped_date} row(s) skipped — date could not be read, "
                        f"not guessed as today")
    if blank_rows:
        problems.append(f"{blank_rows} empty row(s) ignored — no data in the mapped columns")
    return rows, problems


def preview(rows: list[dict], limit: int = 6) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows[:limit]).copy()
    frame["date"] = frame["date"].map(finance.display_date)
    frame["amount"] = frame["amount"].map(lambda v: finance.money(v))
    return frame


def detect_sections(df: pd.DataFrame, prefer: str | None = None) -> dict:
    """Every ledger this file carries its own block of columns for.

    A hand-kept monthly sheet usually holds expenses, income, lent and borrowed
    side by side, each with its own date/name/amount trio. Importing into one
    ledger reads only that block and silently leaves the rest of the file
    behind, so this finds them all at once.

    One block belongs to exactly one ledger. Schemas that need only a date and
    an amount have no distinguishing columns of their own, so they match the
    expense block's plain 'Date'/'Amount' and would file a second copy of it
    under another name — 'transport' picking up all 24 expenses on a sheet with
    no transport in it. Each date+amount pair is therefore claimed once, with
    `prefer` first in line so the ledger the user actually chose wins ties.

    Returns {ledger: {"rows": [...], "mapping": {...}, "problems": [...]}}.
    """
    order = list(SCHEMAS)
    if prefer in SCHEMAS:
        order = [prefer] + [k for k in order if k != prefer]

    found: dict = {}
    claimed: set = set()
    for ledger in order:
        mapping = suggest_mapping(df, ledger)
        signature = (mapping.get("date"), mapping.get("amount"))
        if signature in claimed:
            continue
        rows, problems = build_rows(df, ledger, mapping)
        if rows:
            claimed.add(signature)
            found[ledger] = {"rows": rows, "mapping": mapping, "problems": problems}
    # Report in the schema's own order, not the order they were claimed in.
    return {k: found[k] for k in SCHEMAS if k in found}


def export_csv() -> str:
    """Every record in every ledger as one long-format CSV.

    The app could import but never export, which left the SQLite file as the
    only copy of the data. One flat sheet with a `ledger` column keeps that
    backup readable in any spreadsheet and re-importable section by section,
    rather than a per-ledger zip that needs unpacking to inspect.
    """
    getters = {
        "expenses": db.get_expenses,
        "transport": db.get_transport,
        "income": db.get_income,
        "lent": db.get_lent,
        "borrowed": db.get_borrowed,
    }
    columns = ["ledger", "date", "description", "category", "amount",
               "paid_back", "settled_date"]
    # 'who' folds person/lender/source into the description column so one sheet
    # can carry all five ledgers without four near-empty name columns.
    name_keys = ("description", "source", "person", "lender")

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for ledger, getter in getters.items():
        for record in getter():
            row = dict(record)
            writer.writerow({
                "ledger": ledger,
                "date": row.get("date", ""),
                "description": next((row[k] for k in name_keys if row.get(k)), ""),
                "category": row.get("category", ""),
                "amount": f"{float(row.get('amount') or 0):.2f}",
                "paid_back": row.get("paid_back", ""),
                "settled_date": row.get("settled_date") or "",
            })
    return buffer.getvalue()


def commit(ledger: str, rows: list[dict], replace: bool = False) -> int:
    """Write the rows. Only clears the target ledger, never all five."""
    if replace:
        conn = db.get_connection()
        conn.execute(f"DELETE FROM {ledger}")
        conn.commit()
        conn.close()
    return db.add_many(ledger, rows)
