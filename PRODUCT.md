# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary and only user: **Muhammad Ali Akbar** ("Ali Akbar" in-app), tracking his own
personal money. Single-tenant by design — there are no accounts, no auth, no per-user
data separation, and the app addresses him by name.

Secondary audience, confirmed as the driving reason for this redesign: **recruiters and
peers viewing this as a portfolio piece.** They arrive cold, look for under a minute, and
judge whether the maker can build a real product. They are viewers, not operators — they
will never log a transaction, but the interface must survive their first impression.

This dual audience is the central design tension: the surface must impress a stranger on
first look while staying fast for the one person who uses it every day.

## Product Purpose

Loot Ledger records personal cash flow — income, expenses, transport costs, money lent
out, and money borrowed — and reports what is actually left. Success is Ali knowing his
real cash position for any given month without touching a spreadsheet, and a recruiter
understanding what the project is within seconds of opening it.

It replaces a Google Sheets workflow, which the CSV import path still exists to migrate
from.

## Positioning

Two things a generic expense tracker does not do:

1. **Debt is modeled as cash movement, not just a balance.** Receivables and payables are
   tracked separately from expenses, and only *paid-back* debt moves the savings figure —
   unpaid balances are owed on paper and deliberately do not touch cash on hand.
2. **The ledger is writable in natural language.** A Gemini-backed Finance Bot holds live
   tool access to the database and can log expenses, transport, income, and debts from a
   sentence, a pasted CSV, or a photo of a receipt.

## Operating Context

- **Wide screen is the primary design target; the phone is a supported second one.**
  Superseded the previous "desktop only, never used on a phone" position — the app is now
  used on a phone regularly. The board keeps its one-strip thesis and reflows through
  container queries rather than a separate mobile layout; the Finance Bot opens as a
  right-edge overlay drawer under 680px instead of stacking beneath the board.
- Installable to a phone home screen: a web app manifest and iOS meta tags are injected
  into `<head>` from `pwa.html`, so "Add to Home Screen" launches it standalone.
- Runs two ways: locally via `streamlit run app.py`, and deployed on Streamlit Community
  Cloud from the `main` branch of `aliakbarkhan21/savingdashboard`. **No base path** —
  `server.baseUrlPath` was removed because Community Cloud does its own routing and the
  mismatch broke frontend asset loading outright.
- Currency is Pakistani Rupees, displayed as `Rs.` with thousands separators and two
  decimals. Dates are entered and displayed as DD/MM/YYYY; stored as ISO `YYYY-MM-DD`.
- Data is a local SQLite file (`tracker.db`), which is gitignored. **Local and deployed
  therefore hold two entirely separate databases, and neither syncs to the other.** The
  Cloud copy is also ephemeral: a reboot re-clones the repo, and since the file is not in
  it, the deployed ledger starts empty again. Treat the local file as the real one.
- Typefaces are self-hosted from `static/fonts` (Barlow and Barlow Condensed, latin
  subset). Previously fetched from Google Fonts at runtime; when that request was slow or
  filtered the whole product silently fell back to Arial Narrow and looked like a cheap
  imitation of itself.
- The Gemini API key lives in `.streamlit/secrets.toml` as `GEMINI_API_KEY`. The bot
  degrades to an explicit warning when the key is absent.

## Capabilities and Constraints

**Stack (fixed, confirmed):** Streamlit + SQLite + `google-genai`, with pandas, Pillow and
openpyxl for the import path. Confirmed decision to stay in Streamlit rather than move to
a custom frontend, accepting its design ceiling. Custom CSS injection and same-origin
`st.iframe` scripts are established, working techniques in this codebase and remain
available.

**No charting library.** Plotly was listed here but is imported nowhere; every graphic is
hand-drawn — the category donut is inline SVG generated in `theme.donut_svg`, and the
month run strip, budget meters and rail bars are CSS. This is deliberate: a chart library
brings its own visual defaults, and the point of the board is that nothing on it looks
like a default.

**Five ledgers:** `expenses` (date, description, category, amount), `transport`
(date, amount), `income` (date, source, amount), `lent` (date, person, amount,
paid_back), `borrowed` (date, lender, amount, paid_back).

**Eight fixed categories:** Food, Games, Hangouts, Shopping, Subscriptions,
Transportation, Utilities, Other. Transport is a separate ledger *and* appears as a
spending category in charts — a known duplication in the current model.

**Monthly dashboards:** every view is scoped to a `YYYY-MM` key, plus an All Time
rollup. Debts can optionally ignore the month filter, since they carry across months.

**Confirmed logic to repair in this cycle** (all four named by the user):
- Savings and debt math, including how paid-back loans move cash and how opening
  balances behave.
- Month handling and carryover — months currently start from zero and leftover savings
  do not roll into the next month's opening balance.
- The AI Finance Bot — tool-calling reliability, chat history handling, stop and
  regenerate controls, and how much ledger context the model actually receives.
- CSV import — currently keyed to hardcoded row/column offsets (row 6, column 15,
  rows 16–25) that fail silently on any differently shaped sheet.

**Known undecided:** whether transport should stay a separate ledger or collapse into
the Transportation category. Not resolved; do not silently merge them.

## Brand Commitments

- Name: **Loot Ledger**. The playful name is deliberate and stays.
- The app greets its user by name ("Hello, Ali Akbar").
- The sidebar credits "Built by Muhammad Ali Akbar" and links to
  `https://www.linkedin.com/in/muhammad-ali-akbar-khan-7b37b8197`. This attribution is
  load-bearing for the portfolio purpose and must survive any redesign.
- The assistant is called the **Finance Bot**.

## Evidence on Hand

- Working code: `app.py`, `db.py`, `.streamlit/config.toml`, `.streamlit/secrets.toml`.
- A live, working Gemini API key and confirmed access to `gemini-3.6-flash`, verified
  this session including end-to-end tool-calling.
- `finance_data.csv` (83 bytes) — a near-empty stub, not real historical data.
- **`tracker.db` now holds demo data, not real history** — 32 expenses, 3 income rows and
  1 transport row, loaded through the in-app "Load sample data" control. It was empty when
  this document was written. There is still no real transaction history, no user
  testimonials and no usage metrics. The rule is unchanged and now load-bearing: nothing
  in this project may present invented balances as Ali's real finances, and any sample
  figures must stay visibly labeled as demo data.

## Product Principles

1. **The first screen must be legible to a stranger and useful to Ali.** Neither audience
   gets a degraded version.
2. **Cash on hand is the truth being reported.** Every number traces to a real ledger row;
   paper obligations never masquerade as spendable cash.
3. **Never show an empty dashboard as the finished product.** With zero rows the interface
   must teach and invite, not display a wall of `Rs. 0.00`.
4. **The bot is a writer, not a chatbot.** Its value is mutating the ledger from plain
   language; conversation is the interface, not the point.
5. **Money formatting is invariant.** `Rs.` prefix, grouped thousands, two decimals,
   DD/MM/YYYY dates — everywhere, without exception.

## Accessibility & Inclusion

No user-specific accessibility requirement was established. Baseline still applies: text
contrast must hold in both light and dark themes (Streamlit exposes both and the current
code branches on theme), and color must never be the only carrier of meaning — over-budget,
on-track, receivable, and payable states each need a label or icon alongside their hue.
