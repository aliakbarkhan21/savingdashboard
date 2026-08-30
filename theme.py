"""
The Departure Board — design tokens and stylesheet for Loot Ledger.

The world: a station departure board. Money arriving and money leaving are
arrivals and departures, read off one enamel panel lit from within. The reading
field is monochrome (amber ink on dark enamel); hue is rationed to two jobs only
— the platform rail that identifies a category, and the status lamp that reports
a state. Nothing else in the interface is allowed to be colourful.

Type is a real ramp: 4.5rem board figures down to 0.6875rem platform codes, with
nothing crowded in the middle. Every figure is tabular so digits stack in columns
down the page.

Motion is one moment: the flap settle, played only when a figure actually
changed. A board that flips on every rerun is a toy, not an instrument.
"""
import math
from html import escape as esc

# --------------------------------------------------------------- palette

VOID = "#07090C"
PANEL = "#0E1116"
PANEL_2 = "#141A23"
PANEL_3 = "#1B222D"
AMBER = "#FFB300"
INK = "#E9EDF2"
INK_2 = "#9AA6B4"
INK_3 = "#7B8593"
ARRIVAL = "#2DD4A7"
DEPARTURE = "#FF6B5B"
DELAYED = "#FFB300"
# Recessive bars still have to be legible against the panel.
BAR_MUTED = "#5E6E84"

# One hue per platform, in the manner of transit line colours. These are the
# only categorical colours in the product; charts read from this same map so a
# category is the same colour everywhere it appears.
PLATFORM_COLORS = {
    "Food": "#F4713B",
    "Games": "#A78BFA",
    "Hangouts": "#F472B6",
    "Shopping": "#FBBF24",
    "Subscriptions": "#22D3EE",
    "Transportation": "#60A5FA",
    "Utilities": "#2DD4BF",
    "Other": "#94A3B8",
    # non-category platforms used on the arrivals side
    "Income": "#2DD4A7",
    "Returned": "#4ADE80",
    "Loan": "#FBBF24",
    "Lent": "#C084FC",
    "Settled": "#94A3B8",
}

# Two-letter platform codes, the way a board abbreviates a destination.
PLATFORM_CODES = {
    "Food": "FD", "Games": "GM", "Hangouts": "HG", "Shopping": "SH",
    "Subscriptions": "SB", "Transportation": "TR", "Utilities": "UT",
    "Other": "OT", "Income": "IN", "Returned": "RT", "Loan": "LN",
    "Lent": "LT", "Settled": "ST",
}


def platform_color(name: str) -> str:
    return PLATFORM_COLORS.get(name, PLATFORM_COLORS["Other"])


def platform_code(name: str) -> str:
    return PLATFORM_CODES.get(name, (name[:2] or "??").upper())


def chart_sequence(names) -> list:
    return [platform_color(n) for n in names]


def donut_svg(records, total, center_label="", size=132, thickness=18, amount_fmt=None):
    """Inline SVG donut for spending-by-platform.

    Styled to match the board rather than a chart library's default: a
    hairline track, no drop shadows, platform-color arcs with a thin seam
    between them, and a center label. `records` is a list of dicts with
    "category" and "amount" keys — the same shape as Snapshot.by_category
    rows. `amount_fmt` formats a segment's amount for its tooltip; defaults to
    a plain comma-grouped number so this stays independent of finance.py.
    """
    if not records or total <= 0:
        return ""
    amount_fmt = amount_fmt or (lambda v: f"{v:,.0f}")
    radius = (size - thickness) / 2
    circumference = 2 * math.pi * radius
    cx = cy = size / 2
    cursor = 0.0
    seam = max(circumference * 0.006, 1.0)

    arcs = []
    for r in records:
        amount = float(r["amount"])
        frac = amount / total if total else 0.0
        length = frac * circumference
        seg_len = max(length - seam, 0.0)
        colour = platform_color(str(r["category"]))
        arcs.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius:.2f}" fill="none" '
            f'stroke="{colour}" stroke-width="{thickness}" stroke-linecap="butt" '
            f'stroke-dasharray="{seg_len:.2f} {circumference - seg_len:.2f}" '
            f'stroke-dashoffset="{-cursor:.2f}" transform="rotate(-90 {cx} {cy})">'
            f'<title>{esc(str(r["category"]))}: {esc(amount_fmt(amount))} '
            f'({frac * 100:.0f}%)</title></circle>'
        )
        cursor += length

    track = (f'<circle cx="{cx}" cy="{cy}" r="{radius:.2f}" fill="none" '
             f'style="stroke:rgba(var(--ink-rgb),0.09)" stroke-width="{thickness}"/>')
    center = (
        f'<text x="{cx}" y="{cy - 3:.2f}" text-anchor="middle" class="ll-donut-total">'
        f'{esc(center_label)}</text>'
        f'<text x="{cx}" y="{cy + 15:.2f}" text-anchor="middle" class="ll-donut-label">spent</text>'
    ) if center_label else ""

    return (f'<svg class="ll-donut" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}" role="img" aria-label="Spending by platform">'
            f'{track}{"".join(arcs)}{center}</svg>')


# --------------------------------------------------------------- stylesheet
#
# Two palettes share one set of tokens. The dark palette is the product's
# native voice — void darkest, panels stepping lighter off it, ink near-white.
# Light mode is a real inversion of that same relationship (void lightest,
# panels stepping off it, ink near-black), not a reskin: every color below is
# redeclared per mode, including the low-alpha overlay tints (--ink-rgb /
# --void-rgb / --shade-strong / --shade-soft / --board-shadow) that the rest of
# the stylesheet uses for hairlines, hovers and recessed strips. Those overlays
# are the part a simple "swap two accent colors" pass misses: a light tint that
# reads as a subtle highlight on a dark panel goes invisible — or inverts into
# a smudge — on a light one unless the tint itself flips to dark.
#
# The split-flap digit tiles (.ll-flap) follow the mode too: the tile face
# takes the mode's own surface, while the digits keep reading through --amber /
# --departure, which are already redeclared per mode — so the figure stays dark
# ink on a pale flap in light and pale ink on a dark flap in dark. Deliberately
# NOT re-themed: the run-strip's internal bevel, which is a mechanism detail
# rather than a reading surface. Platform colors are also intentionally
# theme-invariant: every platform badge pairs a saturated swatch with a fixed
# always-dark chip ink (not var(--void)), so a category reads the same color
# in both modes and never loses contrast against its own chip.

_FONT_AND_SCALE = """
  --font-board: 'Barlow Condensed', 'Arial Narrow', system-ui, sans-serif;
  --font-ui:    'Barlow', system-ui, -apple-system, 'Segoe UI', sans-serif;

  /* A real ramp, poster down to caption. The flap figure is not a token: it
     scales off its container (cqi), so it is declared where it is used. */
  --t-display: 1.6rem;   /* secondary display figures and the empty-state head */
  --t-h2:    1.3rem;
  --t-h3:    1.0rem;
  --t-body:  0.9375rem;
  --t-small: 0.8125rem;
  --t-micro: 0.6875rem;

  --s1: 4px;  --s2: 8px;  --s3: 12px; --s4: 16px;
  --s5: 24px; --s6: 32px; --s7: 48px; --s8: 64px;

  --ease: cubic-bezier(0.16, 1, 0.3, 1);
  --radius: 3px;

  /* Hairlines and the amber wash both derive from a raw r,g,b triplet rather
     than a fixed rgba(), so a single color swap per mode (below) is enough to
     re-theme every hairline, hover and hairline-adjacent tint at once. */
  --rule:      rgba(var(--ink-rgb),0.085);
  --rule-2:    rgba(var(--ink-rgb),0.17);
  --amber-12:  rgba(var(--amber-rgb),0.12);
  --amber-24:  rgba(var(--amber-rgb),0.24);
"""

_DARK_VARS = """
  --void:      #07090C;
  --panel:     #0E1116;
  --panel-2:   #141A23;
  --panel-3:   #1B222D;
  --amber:     #FFB300;
  --amber-rgb: 255,179,0;
  --amber-muted: rgba(255,179,0,0.46);
  --ink:       #E9EDF2;
  --ink-2:     #9AA6B4;
  --ink-3:     #7B8593;   /* 5.06:1 on panel, 4.68:1 on panel-2 */
  --arrival:   #2DD4A7;
  --departure: #FF6B5B;
  --ink-rgb:      233,237,242;
  --void-rgb:     7,9,12;
  --shade-strong: rgba(7,9,12,0.55);
  --shade-soft:   rgba(7,9,12,0.35);
  --board-shadow: rgba(0,0,0,0.9);
  --blank-tile:      linear-gradient(180deg, #161C25 0 49.6%, #0F141B 50.4% 100%);
  --blank-tile-edge: rgba(233,237,242,0.028);
  --blank-tile-seam: rgba(0,0,0,0.55);
  --flap-face:   linear-gradient(180deg, #232B37 0%, #171D26 49.6%,
                                 #10151C 50.4%, #1B222D 100%);
  --flap-edge:   rgba(233,237,242,0.06);
  --flap-shadow: rgba(0,0,0,0.45);
  --flap-seam:   rgba(0,0,0,0.7);
"""

_LIGHT_VARS = """
  --void:      #EDE7D9;
  --panel:     #FBF8F0;
  --panel-2:   #F3EDE0;
  --panel-3:   #EAE2D0;
  --amber:     #A85D00;
  --amber-rgb: 168,93,0;
  --amber-muted: rgba(168,93,0,0.55);
  --ink:       #1A1712;
  --ink-2:     #5B5449;
  --ink-3:     #7D7568;   /* kept close to dark mode's ~4.7:1 target on panel */
  --arrival:   #0A7A57;
  --departure: #C7392A;
  --ink-rgb:      26,23,18;
  --void-rgb:     26,23,18;
  --shade-strong: rgba(26,23,18,0.045);
  --shade-soft:   rgba(26,23,18,0.028);
  --board-shadow: rgba(20,18,14,0.16);
  --blank-tile:      linear-gradient(180deg, rgba(26,23,18,0.10) 0 49.6%,
                                             rgba(26,23,18,0.145) 50.4% 100%);
  --blank-tile-edge: rgba(26,23,18,0.06);
  --blank-tile-seam: rgba(26,23,18,0.14);
  --flap-face:   linear-gradient(180deg, #FFFFFF 0%, #F6F1E5 49.6%,
                                 #EDE5D3 50.4%, #FAF6EC 100%);
  --flap-edge:   rgba(26,23,18,0.10);
  --flap-shadow: rgba(20,18,14,0.14);
  --flap-seam:   rgba(26,23,18,0.16);
"""

_CSS_HEAD = """
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Barlow:wght@400;500;600;700&display=swap');

:root {"""

_CSS_ROOT_CLOSE = "\n}\n"

_CSS_BODY = """
/* ============================================================ base shell */

html, body, [data-testid="stAppViewContainer"] {
  background: var(--void) !important;
  overflow-x: hidden !important;
}
.stApp {
  font-family: var(--font-ui) !important;
  color: var(--ink) !important;
  background:
    radial-gradient(1200px 520px at 50% -8%, rgba(255,179,0,0.055), transparent 65%),
    var(--void) !important;
}
.block-container {
  /* Top padding trimmed to pay for the ledgers menu that now sits in this
     band. The menu is 42px plus a 16px gap, and this reclaims most of it, so
     the board below stays where it was rather than being pushed down. */
  padding: 0 var(--s5) var(--s6) !important;
  max-width: 1680px !important;
}
/* On a phone, --s5's 24px on each edge is real board width, not spare
   margin — the same trim the board's own container queries above already
   assume once it gets this narrow. */
@media (max-width: 480px) {
  .block-container { padding-left: var(--s3) !important; padding-right: var(--s3) !important; }
}

/* every number in this product stacks in a column */
.stApp, .stApp input, .stApp button, .stApp table {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1, "lnum" 1;
}

/* ---- browser surfaces: these ship with defaults belonging to no design ---- */
::selection { background: var(--amber-24); color: var(--ink); }
* { scrollbar-width: thin; scrollbar-color: rgba(var(--ink-rgb),0.18) transparent; }
*::-webkit-scrollbar { width: 9px; height: 9px; }
*::-webkit-scrollbar-track { background: transparent; }
*::-webkit-scrollbar-thumb {
  background: rgba(var(--ink-rgb),0.16);
  border-radius: 99px;
  border: 2px solid transparent;
  background-clip: content-box;
}
*::-webkit-scrollbar-thumb:hover { background: rgba(255,179,0,0.5); background-clip: content-box; }
input, textarea { caret-color: var(--amber) !important; }
a { color: var(--amber); text-underline-offset: 3px; text-decoration-thickness: 1px; }
:focus-visible,
.stApp button:focus-visible,
.stApp input:focus-visible,
.stApp textarea:focus-visible,
.stApp [role="combobox"]:focus-visible {
  outline: 2px solid var(--amber) !important;
  outline-offset: 2px !important;
  border-radius: 2px;
}

.ll-icon { display: block; flex: 0 0 auto; }

/* ============================================ streamlit chrome removal */

/* The header bar itself stays transparent and empty — its menu/toolbar/status
   children are individually hidden below — but it must keep its natural
   height. That height is what the collapsed-sidebar expand arrow
   (stExpandSidebarButton) renders inside; zeroing it clips the arrow away
   along with the chrome nobody wants.

   stExpandSidebarButton lives INSIDE stToolbar (verified by inspecting the
   rendered DOM, not assumed from the name) — hiding stToolbar wholesale, as
   the previous rule did, took the expand arrow down with the deploy button
   and menu it was actually meant to hide. Those get targeted individually
   instead so the toolbar shell itself can stay visible. */
/* Reserves 60px for a single 28px button. Trimmed to just clear it — the
   surplus was the other half of the space the ledgers menu now occupies. Not
   zeroed: this band is what the collapsed-sidebar expand arrow renders in,
   and collapsing it clips that control away. */
[data-testid="stHeader"] {
  background: transparent !important;
  height: 34px !important; min-height: 34px !important;
}
[data-testid="stToolbar"] { background: transparent !important; }
[data-testid="stStatusWidget"], [data-testid="stHeaderActionElements"],
[data-testid="stDecoration"], [data-testid="stMainMenu"],
[data-testid="stAppDeployButton"], [data-testid="stToolbarActions"] { display: none !important; }
#MainMenu, footer { display: none !important; }
.stMarkdown a.anchor-link,
h1 a[href^="#"], h2 a[href^="#"], h3 a[href^="#"],
h4 a[href^="#"], h5 a[href^="#"], h6 a[href^="#"] { display: none !important; }
[data-testid="stElementContainer"]:has(> [data-testid="stIFrame"]) { display: none; }
[data-testid="stElementToolbar"] { display: none !important; }

/* ================================================================ sidebar */

[data-testid="stSidebar"] {
  background: var(--panel) !important;
  border-right: 1px solid var(--rule-2) !important;
  position: relative !important;   /* anchors the floated collapse control */
}
[data-testid="stSidebar"] > div { background: transparent !important; }
[data-testid="stSidebarUserContent"] {
  padding: 10px var(--s4) var(--s4) !important;
  display: flex !important; flex-direction: column !important;
  min-height: calc(100vh - 40px) !important;
}
[data-testid="stSidebarUserContent"] > div:first-child {
  display: flex !important; flex-direction: column !important; flex: 1 1 auto !important;
}
/* Trimming this band's height still left it occupying a row above the
   masthead. Taking it out of flow entirely and floating it into the sidebar's
   top-right corner reclaims that space outright — the title rises to the top
   of the panel and the arrow sits clear of it, in the corner, rather than on
   the line the title wants. Height must stay auto (not zero): the control is
   this element's child, and collapsing the box clips the arrow away. */
[data-testid="stSidebarHeader"] {
  background: transparent !important;
  position: absolute !important; top: 0 !important; right: 0 !important;
  left: auto !important; width: auto !important;
  height: auto !important; min-height: 0 !important;
  padding: 6px 8px 0 0 !important;
  z-index: 6 !important;
}
/* Chrome, not content: no fill or border at rest, so it never reads as a
   stray empty widget. It is drawn in ink rather than the faint --ink-3 it
   used to carry, which was legible enough on a dark panel but disappeared
   against light mode's cream. Full contrast arrives on hover. */
/* Streamlit keeps this wrapper at visibility:hidden until the sidebar is
   hovered, which is the actual reason the arrow read as missing — no amount of
   colour or opacity on the button shows an ancestor that is hidden outright.
   Forced visible so the control can be found without knowing it is there. */
[data-testid="stSidebarCollapseButton"] {
  visibility: visible !important; opacity: 1 !important;
  color: var(--ink-2) !important;
}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stExpandSidebarButton"] {
  background: transparent !important;
  border: 1px solid transparent !important;
  color: var(--ink-2) !important;
  border-radius: var(--radius) !important;
  opacity: 1 !important;
  visibility: visible !important;
  transition: color 120ms ease, background 120ms ease, border-color 120ms ease !important;
}
[data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stSidebarCollapseButton"] button span,
[data-testid="stExpandSidebarButton"] svg,
[data-testid="stExpandSidebarButton"] span { color: inherit !important; }
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stExpandSidebarButton"]:hover {
  background: var(--panel-2) !important;
  border-color: var(--rule-2) !important;
  color: var(--amber) !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: var(--s3) !important; }
[data-testid="stSidebar"] hr { border-color: var(--rule) !important; margin: var(--s3) 0 !important; }

/* ------------------------------------------------------- masthead */
.ll-mast { margin-bottom: var(--s5); }
.ll-mast-name {
  font-family: var(--font-board) !important;
  font-size: 2.05rem !important; font-weight: 700 !important; line-height: 0.95 !important;
  letter-spacing: 0.012em; text-transform: uppercase;
  /* !important because this is a real <h1> — Streamlit applies its own
     heading color from .streamlit/config.toml's static textColor, which
     otherwise wins over an unqualified color here. That hardcoded value
     happens to equal dark mode's --ink exactly, which is why this was
     invisible until light mode gave the two values something to disagree on. */
  color: var(--ink) !important; margin: 0; display: flex; align-items: baseline; gap: 0.42rem;
}
.ll-mast-name .ll-lamp {
  width: 9px; height: 9px; border-radius: 50%;
  background: var(--amber); box-shadow: 0 0 10px 1px rgba(255,179,0,0.65);
  align-self: center;
}
.ll-mast-sub {
  font-size: var(--t-micro); letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--ink-3); margin-top: 7px; font-weight: 600;
}

/* ------------------------------------------------- section captions */
.ll-cap {
  font-size: var(--t-micro); font-weight: 700; letter-spacing: 0.17em;
  text-transform: uppercase; color: var(--ink-3);
  display: flex; align-items: center; gap: 7px;
  margin: var(--s5) 0 var(--s2);
}
/* The bot panel's title heads an entire column, not a group of fields, so it
   carries more weight than the sidebar's section labels. 65% larger than
   --t-micro, with the letter-spacing eased back: tracking that reads as
   deliberate at small sizes turns into a gap at larger ones. */
.ll-cap.is-lg {
  font-size: calc(var(--t-micro) * 1.65);
  letter-spacing: 0.12em;
  color: var(--ink-2);
  /* No top margin. .ll-cap carries one so consecutive sections breathe, but
     this is the first thing in its column and had nothing above it to be
     separated from — just 24px of empty panel. The sidebar already zeroes its
     own first heading for the same reason; the rail had no equivalent. */
  margin-top: 0;
  margin-bottom: var(--s3);
}

.ll-cap::after {
  content: ""; flex: 1 1 auto; height: 1px; background: var(--rule);
}
[data-testid="stSidebar"] .ll-cap:first-child { margin-top: 0; }

/* ---------------------------------------------------- the month rail */
/* Navigation that is already a chart: each month's bar is its outflow. */
.ll-rail { display: flex; flex-direction: column; gap: 1px; margin-bottom: var(--s2); }
.ll-rail-row {
  display: grid; grid-template-columns: 46px 1fr auto; align-items: center;
  gap: var(--s2); padding: 7px var(--s2); border-radius: var(--radius);
  border-left: 2px solid transparent; background: transparent;
}
.ll-rail-row.is-active { background: var(--amber-12); border-left-color: var(--amber); }
.ll-rail-mon {
  font-family: var(--font-board); font-size: var(--t-small); font-weight: 600;
  letter-spacing: 0.09em; color: var(--ink-2);
}
.ll-rail-row.is-active .ll-rail-mon { color: var(--amber); }
.ll-rail-bar { height: 5px; background: rgba(var(--ink-rgb),0.08); border-radius: 99px; overflow: hidden; }
.ll-rail-fill { height: 100%; background: var(--ink-3); border-radius: 99px; }
.ll-rail-row.is-active .ll-rail-fill { background: var(--amber); }
.ll-rail-amt {
  font-size: var(--t-micro); color: var(--ink-3); font-weight: 600; min-width: 46px; text-align: right;
}
.ll-rail-row.is-active .ll-rail-amt { color: var(--ink-2); }

/* ============================================================ the board */

.ll-board {
  container-type: inline-size;
  container-name: board;
  background: linear-gradient(180deg, var(--panel-2) 0%, var(--panel) 100%);
  border: 1px solid var(--rule-2);
  border-radius: var(--radius);
  box-shadow: 0 24px 60px -28px var(--board-shadow), inset 0 1px 0 rgba(var(--ink-rgb),0.05);
  overflow: hidden;
}

/* ---- service header: the strip that names the period and its state ----
   flex-wrap is unconditional, not tied to a breakpoint: period+meta and the
   status pill carry white-space:nowrap and nothing clips their overflow, so
   whenever the row is too narrow for both — a board width no single
   threshold can predict, since it depends on the period label's own length —
   the pill needs to be free to drop to its own line. Wrapping is a no-op
   whenever there is room, so this costs nothing at any width that fits. */
.ll-service {
  display: flex; align-items: center; justify-content: space-between; gap: var(--s4);
  flex-wrap: wrap; row-gap: 6px;
  padding: var(--s3) var(--s5);
  border-bottom: 1px solid var(--rule-2);
  background: var(--shade-strong);
}
.ll-service-left {
  display: flex; align-items: baseline; gap: var(--s3); min-width: 0;
  flex-wrap: wrap; row-gap: 2px;
}
.ll-service-period {
  font-family: var(--font-board); font-size: var(--t-h2); font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.06em; color: var(--ink); white-space: nowrap;
}
.ll-service-meta {
  font-size: var(--t-micro); letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--ink-3); font-weight: 600; white-space: nowrap;
}
.ll-status {
  display: inline-flex; align-items: center; gap: 7px;
  font-size: var(--t-micro); font-weight: 700; letter-spacing: 0.15em;
  text-transform: uppercase; padding: 5px 11px; border-radius: 99px;
  border: 1px solid currentColor; white-space: nowrap;
}
.ll-status .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.ll-status.on-time   { color: var(--arrival); }
.ll-status.delayed   { color: var(--amber); }
.ll-status.cancelled { color: var(--departure); }
.ll-status.quiet     { color: var(--ink-3); }

/* ---------------------------------------------- the four flap figures ---- */
.ll-figures {
  display: grid; grid-template-columns: repeat(4, 1fr);
  border-bottom: 1px solid var(--rule-2);
}
.ll-fig {
  padding: var(--s5) var(--s5) var(--s4);
  border-right: 1px solid var(--rule);
  display: flex; flex-direction: column; gap: var(--s2); min-width: 0;
}
.ll-fig:last-child { border-right: none; }
.ll-fig-label {
  font-size: var(--t-micro); font-weight: 700; letter-spacing: 0.17em;
  text-transform: uppercase; color: var(--ink-3);
  display: flex; align-items: center; gap: 6px;
}
.ll-fig-label .ll-icon { opacity: 0.75; }
.ll-fig-value {
  font-family: var(--font-board);
  /* cqi, not vw: opening the bot panel narrows the board while the window
     stays the same width, and a vw-based figure would overrun its cell. */
  font-size: clamp(1.3rem, 4.3cqi, 3.9rem);
  font-weight: 700;
  line-height: 0.9; letter-spacing: 0.004em; color: var(--amber);
  display: flex; align-items: flex-end; gap: 2px; flex-wrap: nowrap;
}
.ll-fig-value .cur {
  font-size: 0.36em; font-weight: 600; color: var(--ink-3);
  letter-spacing: 0.1em; margin-right: 5px; padding-bottom: 0.42em;
}
/* One board, one light. Direction is carried by the label, the icon and the
   +/- prefixes on the rows below — not by giving each figure its own hue.
   The only exception is a negative balance, which is a state, not a category. */
.ll-fig.is-muted .ll-fig-value { color: var(--amber-muted); }
.ll-fig.is-neg   .ll-fig-value { color: var(--departure); }
.ll-fig-note {
  font-size: var(--t-micro); color: var(--ink-3); font-weight: 500;
  letter-spacing: 0.02em; display: flex; align-items: center; gap: 5px;
}
.ll-fig-note b { color: var(--ink-2); font-weight: 600; }
.ll-fig-note .up   { color: var(--departure); font-weight: 700; }
.ll-fig-note .down { color: var(--arrival); font-weight: 700; }

/* ---- the flap tile: one character, hinged on its centre seam ---- */
.ll-flap {
  position: relative; display: inline-block;
  background: var(--flap-face);
  border-radius: 2px; padding: 0.07em 0.055em 0.09em;
  box-shadow: inset 0 0 0 1px var(--flap-edge), 0 2px 5px var(--flap-shadow);
  min-width: 0.62em; text-align: center;
}
.ll-flap::after {
  content: ""; position: absolute; left: 0; right: 0; top: 50%;
  height: 1px; background: var(--flap-seam);
}
.ll-flap.sep { background: none; box-shadow: none; min-width: 0.26em; padding-left: 0; padding-right: 0; }
.ll-flap.sep::after { display: none; }

/* THE authored moment — played only when the figure actually changed */
.ll-figures.is-flipping .ll-flap {
  animation: flapSettle 560ms var(--ease) both;
  animation-delay: calc(var(--i, 0) * 34ms);
}
@keyframes flapSettle {
  0%   { transform: rotateX(-88deg); filter: brightness(0.45); }
  52%  { transform: rotateX(9deg);   filter: brightness(1.06); }
  76%  { transform: rotateX(-4deg);  filter: brightness(1); }
  100% { transform: rotateX(0deg);   filter: brightness(1); }
}
.ll-fig-value { perspective: 460px; }

/* ================================================= arrivals / departures */

.ll-cols { display: grid; grid-template-columns: 1fr 1fr; }
.ll-col { min-width: 0; border-right: 1px solid var(--rule); }
.ll-col:last-child { border-right: none; }
.ll-col-head {
  display: flex; align-items: center; justify-content: space-between; gap: var(--s3);
  padding: var(--s3) var(--s5); border-bottom: 1px solid var(--rule);
  background: var(--shade-soft);
}
.ll-col-title {
  display: flex; align-items: center; gap: 8px;
  font-family: var(--font-board); font-size: var(--t-h3); font-weight: 700;
  letter-spacing: 0.13em; text-transform: uppercase;
}
/* The reading field is achromatic. Direction is carried by the word, the icon
   and the column it sits in - not by tinting the type. Hue stays reserved for
   the platform rail and the status lamp. */
.ll-col-title { color: var(--ink-2); }
.ll-col-sum {
  font-size: var(--t-small); font-weight: 700; color: var(--ink-2); letter-spacing: 0.02em;
}
.ll-rows {
  max-height: 336px; overflow-y: auto;
  scroll-snap-type: y proximity;
  -webkit-mask-image: linear-gradient(180deg, #000 calc(100% - 52px), transparent 100%);
  mask-image: linear-gradient(180deg, #000 calc(100% - 52px), transparent 100%);
}
.ll-rows.is-short { -webkit-mask-image: none; mask-image: none; }
.ll-row {
  display: grid; grid-template-columns: 46px 30px 1fr auto;
  align-items: center; gap: var(--s3);
  padding: 9px var(--s5); border-bottom: 1px solid var(--rule);
}
.ll-row:last-child { border-bottom: none; }
.ll-row { scroll-snap-align: start; }
/* A clickable row says so on hover without turning the board into a page of
   hyperlinks: a faint amber edge on the leading side, and the amount picking
   up the accent. Every row still reads as a row. */
.ll-row.is-clickable { cursor: pointer; }
.ll-row.is-clickable:hover {
  background: rgba(var(--amber-rgb),0.07) !important;
  box-shadow: inset 2px 0 0 var(--amber);
}
.ll-row.is-clickable:hover .ll-row-amt { color: var(--amber); }
.ll-row.is-clickable:focus-visible {
  outline: 2px solid var(--amber); outline-offset: -2px;
}

/* The per-row buttons the bridge clicks. Kept in the layout but out of sight:
   display:none would stop them being clickable at all. */
/* The click bridge is an iframe with no visible content. st.iframe will not
   accept a height of 0, so it is collapsed here instead of taking a row. */
/* Taken out of the column's flow entirely, not merely shrunk. A zero-height
   flex item is still an item, and the gap either side of it is real space —
   four of these between the board and the panels added up to a visible band.
   position:absolute keeps the frame rendered (a display:none iframe is not
   guaranteed to run its script) while costing no layout. */
[data-testid="stElementContainer"]:has(> [data-testid="stIFrame"]) {
  position: absolute !important; left: -9999px !important; top: 0 !important;
  width: 1px !important; height: 1px !important; overflow: hidden !important;
}
div[class*="st-key-rm_"] { position: absolute !important; left: -9999px !important;
  width: 1px !important; height: 1px !important; overflow: hidden !important; }

/* ---- confirm bar for removing an entry ---- */
.ll-confirm {
  border: 1px solid var(--rule-2); border-left: 2px solid var(--departure);
  border-radius: var(--radius); background: var(--shade-strong);
  padding: var(--s3) var(--s4); margin-bottom: var(--s2);
}
.ll-confirm-title {
  font-family: var(--font-board); font-size: var(--t-small); font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink);
  display: flex; align-items: center; gap: 8px; margin-bottom: 4px;
}
.ll-confirm-title .ll-icon { color: var(--departure); }
.ll-confirm-body { font-size: var(--t-small); color: var(--ink-2); line-height: 1.5; }
.ll-row:hover { background: rgba(var(--ink-rgb),0.028); }

/* ---- expand the list in place ----
   A hidden checkbox and its label. The board is one HTML block, so a
   Streamlit button cannot live inside it, and an anchor could only work by
   navigating — which reloaded the whole dashboard to reveal rows that were
   already in the page. This is pure CSS: the browser toggles it instantly,
   with no rerun, no reload and no scroll position lost. */
.ll-expand { display: none !important; }
.ll-expand:checked ~ .ll-rows {
  max-height: none !important;
  -webkit-mask-image: none !important; mask-image: none !important;
}
label.ll-row-more {
  display: flex; align-items: center; justify-content: center;
  padding: 11px var(--s5); cursor: pointer; user-select: none;
  border-top: 1px solid var(--rule);
  background: var(--shade-soft);
  transition: background 120ms ease, color 120ms ease;
}
label.ll-row-more:hover { background: var(--shade-strong); }
.ll-row-more-label {
  font-family: var(--font-board); font-size: var(--t-micro); font-weight: 700;
  letter-spacing: 0.13em; text-transform: uppercase; color: var(--ink-3);
}
label.ll-row-more:hover .ll-row-more-label { color: var(--amber); }
/* the label says what the next click will do, so it swaps once expanded */
.more-close { display: none; }
.ll-expand:checked ~ label.ll-row-more .more-open { display: none; }
.ll-expand:checked ~ label.ll-row-more .more-close { display: inline; }
.ll-row-time {
  font-family: var(--font-board); font-size: var(--t-small); font-weight: 600;
  color: var(--ink-3); letter-spacing: 0.05em;
}
.ll-plat {
  font-family: var(--font-board); font-size: var(--t-micro); font-weight: 700;
  letter-spacing: 0.06em; text-align: center; padding: 3px 0; border-radius: 2px;
  color: var(--void);
}
.ll-row-label {
  font-size: var(--t-body); color: var(--ink); font-weight: 500;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ll-row-label .sub {
  display: block; font-size: var(--t-micro); color: var(--ink-3);
  letter-spacing: 0.08em; text-transform: uppercase; font-weight: 600; margin-top: 1px;
}
.ll-row-amt {
  font-family: var(--font-board); font-size: 1.16rem; font-weight: 600;
  color: var(--ink); letter-spacing: 0.01em; white-space: nowrap;
}
.ll-col.arrivals   .ll-row-amt::before { content: "+"; color: var(--ink-3); margin-right: 3px; }
.ll-col.departures .ll-row-amt::before { content: "−"; color: var(--ink-3); margin-right: 3px; }

/* --------------------------------------------------------- empty states */
/* An empty slot is one blank flap across the row. Content-shaped grey bars
   read as a loading skeleton, which says the opposite of "nothing is here". */
.ll-row.is-blank { pointer-events: none; display: block; padding: 6px var(--s5); }
/* Unlike the digit flaps, a blank tile is themed. The flaps show a figure and
   read as the board's physical mechanism in either mode, but these are empty
   slots: the hardcoded dark gradient sat on light mode's cream panel as a row
   of solid mid-grey bars — precisely the loading-skeleton look the note above
   says to avoid. Tokenised so each mode gets a faint recess in its own ink. */
.ll-row.is-blank .ll-blank-tile {
  position: relative; height: 26px; border-radius: 2px;
  background: var(--blank-tile);
  box-shadow: inset 0 0 0 1px var(--blank-tile-edge);
  opacity: 0.55;
}
.ll-row.is-blank .ll-blank-tile::after {
  content: ""; position: absolute; left: 0; right: 0; top: 50%;
  height: 1px; background: var(--blank-tile-seam);
}

.ll-empty {
  padding: var(--s7) var(--s5); text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: var(--s3);
}
.ll-empty .ll-icon { color: var(--ink-3); opacity: 0.5; }
.ll-empty-title {
  font-family: var(--font-board); font-size: var(--t-h3); font-weight: 700;
  letter-spacing: 0.11em; text-transform: uppercase; color: var(--ink-2);
}
.ll-empty-body { font-size: var(--t-small); color: var(--ink-3); max-width: 34ch; line-height: 1.55; }

/* ============================================================ panels */

.ll-panel {
  background: var(--panel); border: 1px solid var(--rule-2);
  border-radius: var(--radius); overflow: hidden;
}
.ll-panel-head {
  display: flex; align-items: center; justify-content: space-between; gap: var(--s3);
  padding: var(--s3) var(--s4); border-bottom: 1px solid var(--rule);
}
.ll-panel-title {
  display: flex; align-items: center; gap: 8px;
  font-family: var(--font-board); font-size: var(--t-h3); font-weight: 700;
  letter-spacing: 0.13em; text-transform: uppercase; color: var(--ink-2);
}
.ll-panel-body { padding: var(--s4); }

/* ---- platform load: spending by category as a stacked rail ---- */
.ll-load { display: flex; align-items: center; gap: var(--s5); }
.ll-donut-wrap { flex: 0 0 auto; }
.ll-donut circle { transition: opacity 140ms var(--ease); }
.ll-donut:hover circle:not(:hover) { opacity: 0.55; }
.ll-donut-total {
  font-family: var(--font-board); font-size: 1.05rem; font-weight: 700;
  fill: var(--ink); letter-spacing: 0.01em;
}
.ll-donut-label {
  font-family: var(--font-ui); font-size: 0.5625rem; font-weight: 600;
  letter-spacing: 0.14em; text-transform: uppercase; fill: var(--ink-3);
}
.ll-load-list { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 0; }
.ll-load-item {
  display: grid; grid-template-columns: 30px 1fr auto auto; align-items: center;
  gap: var(--s3); padding: 7px 0; border-bottom: 1px solid var(--rule);
}
.ll-load-row:last-child .ll-load-item { border-bottom: none; }
.ll-load-name { font-size: var(--t-small); color: var(--ink); font-weight: 500; }
.ll-load-pct { font-size: var(--t-micro); color: var(--ink-3); font-weight: 600; min-width: 38px; text-align: right; }
.ll-load-amt { font-size: var(--t-small); color: var(--ink-2); font-weight: 600; min-width: 78px; text-align: right; }

/* ---- per-category budget cap: a thin meter under any category that has one
   set, reusing the Capacity panel's own tone thresholds ---- */
.ll-load-cap {
  display: flex; align-items: center; gap: var(--s3);
  padding: 0 0 8px 42px; margin-top: -2px;
}
.ll-load-cap-track {
  flex: 1 1 auto; height: 4px; background: rgba(var(--ink-rgb),0.09);
  border-radius: 99px; overflow: hidden;
}
.ll-load-cap-fill { height: 100%; border-radius: 99px; }
.ll-load-cap-label {
  font-size: var(--t-micro); color: var(--ink-3); font-weight: 600; white-space: nowrap;
}
@media (max-width: 900px) {
  .ll-load { flex-direction: column; align-items: flex-start; }
  .ll-load-list { width: 100%; }
}

/* ---- obligations ---- */
.ll-oblig { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background: var(--rule); }
.ll-oblig-cell { background: var(--panel); padding: var(--s4); display: flex; flex-direction: column; gap: 5px; }
.ll-oblig-label {
  font-size: var(--t-micro); font-weight: 700; letter-spacing: 0.15em;
  text-transform: uppercase; color: var(--ink-3);
  display: flex; align-items: center; gap: 6px;
}
.ll-oblig-value {
  font-family: var(--font-board); font-size: var(--t-display);
  font-weight: 700; line-height: 1; color: var(--ink);
}
.ll-oblig-value { color: var(--ink); }
.ll-oblig-note { font-size: var(--t-micro); color: var(--ink-3); }

/* ---- utilisation meter ---- */
.ll-meter-top {
  display: flex; align-items: baseline; justify-content: space-between;
  margin-bottom: 9px;
}
.ll-meter-pct {
  font-family: var(--font-board); font-size: var(--t-display); font-weight: 700;
  line-height: 1; color: var(--ink);
}
.ll-meter-cap { font-size: var(--t-micro); color: var(--ink-3); font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; }
.ll-meter-track {
  height: 8px; background: rgba(var(--ink-rgb),0.07); border-radius: 2px;
  overflow: hidden; position: relative;
}
.ll-meter-fill { height: 100%; border-radius: 2px; }
.ll-meter-mark { position: absolute; top: -2px; bottom: -2px; width: 1px; background: var(--rule-2); }
.ll-meter-foot { margin-top: 9px; font-size: var(--t-micro); color: var(--ink-3); }
.ll-meter-foot b { color: var(--ink-2); font-weight: 600; }

/* ---- the run strip: months as flap columns, not a stock chart ---- */
.ll-run {
  display: flex; align-items: stretch; gap: 8px;
  padding: var(--s5) var(--s5) 0; height: 196px;
}
/* Twelve equal slots. Months fill from the right; the rest stay vacant, the
   way unused rows sit on a real board. */
.ll-run-col {
  flex: 1 1 0; display: flex; flex-direction: column;
  height: 100%; min-width: 0;
}
.ll-run-col.is-vacant .ll-run-track { background: rgba(var(--ink-rgb),0.016); }
.ll-run-col.is-vacant .ll-run-foot { color: var(--ink-3); opacity: 0.3; }
.ll-run-track {
  position: relative; flex: 1 1 auto; display: flex; flex-direction: column;
  justify-content: flex-end; background: rgba(var(--ink-rgb),0.035);
  border-radius: 2px; overflow: hidden;
}
.ll-run-fill {
  min-height: 3px; border-radius: 2px 2px 0 0;
  background:
    repeating-linear-gradient(180deg,
      rgba(255,255,255,0.055) 0 1px,
      rgba(0,0,0,0) 1px 13px,
      rgba(0,0,0,0.40) 13px 14px),
    var(--run-colour, #5E6E84);
  box-shadow: inset 0 0 0 1px rgba(0,0,0,0.32);
}
.ll-run-col.is-current .ll-run-fill { --run-colour: #FFB300; }
.ll-run-hand {
  position: absolute; left: 0; right: 0; height: 2px;
  background: var(--ink); opacity: 0.9;
}
.ll-run-hand::after {
  content: ""; position: absolute; right: 0; top: -3px;
  width: 7px; height: 7px; border-radius: 50%; background: var(--ink);
}
.ll-run-foot {
  padding-top: 10px; text-align: center; font-family: var(--font-board);
  font-size: var(--t-micro); letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--ink-3);
}
.ll-run-col.is-current .ll-run-foot { color: var(--amber); }
.ll-run-foot span { display: block; color: var(--ink-3); opacity: 0.8; margin-top: 3px; }
.ll-run-key {
  display: flex; gap: var(--s5); padding: var(--s3) var(--s5) var(--s4);
  font-size: var(--t-micro); color: var(--ink-3); letter-spacing: 0.06em;
}
.ll-run-key i {
  display: inline-block; width: 18px; height: 9px; border-radius: 2px;
  margin-right: 8px; vertical-align: middle; font-style: normal;
}
.ll-run-key .k-out { background: #5E6E84; }
.ll-run-key .k-now { background: #FFB300; }

/* ---- data tables inherit the board's rules, not Streamlit's default chrome */
[data-testid="stDataFrame"] thead th, [data-testid="stDataEditor"] thead th {
  background: var(--panel-2) !important;
  font-size: var(--t-micro) !important; font-weight: 700 !important;
  letter-spacing: 0.12em !important; text-transform: uppercase !important;
  color: var(--ink-3) !important;
}

/* ---- board legend, shown in the bot rail while the chat is empty ----
   Replaces the old .ll-firstrun panel, which taught the same four terms from
   a full-width block above the board. Laid out for the narrow rail: the term
   sits on its own line above its definition rather than in a label column,
   which would wrap badly at this width. */
.ll-insight {
  border-top: 1px solid var(--rule);
  /* A little air at the foot: without it the last definition sat flush
     against the first prompt button and the two groups read as one list. */
  margin: var(--s2) var(--s2) 0; padding: var(--s3) var(--s2) var(--s2);
  display: flex; flex-direction: column; gap: 8px; text-align: left;
}
.ll-insight-head {
  font-family: var(--font-board); font-size: var(--t-micro); font-weight: 700;
  letter-spacing: 0.15em; text-transform: uppercase; color: var(--amber-muted);
  margin-bottom: 1px;
}
.ll-insight-row { display: flex; flex-direction: column; gap: 2px; }
.ll-insight-row b {
  font-family: var(--font-board); font-weight: 700; font-size: var(--t-micro);
  letter-spacing: 0.12em; text-transform: uppercase; color: var(--ink-2);
}
.ll-insight-row span {
  font-size: var(--t-small); color: var(--ink-3); line-height: 1.5;
}

/* ---- the bot rail opening and closing --------------------------------
   Both columns exist in every render (see app.py), so these widths are the
   only thing that changes between open and closed — and a width the browser
   can transition is what turns the old unmount-and-rebuild jump into a slide.
   The row is pinned by .ll-stage-marker so the toolbar and figure strip,
   which are also horizontal blocks, keep their own widths. */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ll-stage-marker) {
  transition: gap 300ms cubic-bezier(0.22, 0.61, 0.36, 1);
}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ll-stage-marker)
  > [data-testid="stColumn"] {
  /* max-width is the property that actually opens and closes this column.
     Streamlit sets flex-basis from a stylesheet rule that outranks anything
     declared here, so the width is driven by clamping instead — and a
     max-width jumping straight from a length to 0 snaps shut no matter what
     else is transitioning, which is why closing had no in-between frames.
     Given a length in BOTH states it animates like any other property. */
  max-width: 100%;
  transition: max-width 300ms cubic-bezier(0.22, 0.61, 0.36, 1),
              flex-basis 300ms cubic-bezier(0.22, 0.61, 0.36, 1),
              width 300ms cubic-bezier(0.22, 0.61, 0.36, 1),
              opacity 220ms ease;
  will-change: max-width;
}
/* On a phone there is no room for the sidebar (left) AND a side-by-side
   board+rail split, so below this width Streamlit's own column stacking
   would otherwise drop the rail beneath the board instead of beside it. The
   rail is pulled out of that flow and pinned as a right-edge overlay instead
   — the same drawer behaviour the sidebar already has, mirrored to the other
   edge — so it still reads as sliding in from the side, not appearing at the
   bottom of a scroll. position:fixed removes it from flow entirely, so this
   applies regardless of whether the row itself is row- or column-flex. */
@media (max-width: 680px) {
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ll-stage-marker)
    > [data-testid="stColumn"]:last-child {
    position: fixed !important;
    top: 0 !important; right: 0 !important; bottom: 0 !important;
    height: 100dvh !important;
    width: min(88vw, 380px) !important;
    max-width: min(88vw, 380px) !important;
    z-index: 1000 !important;
    background: var(--panel) !important;
    border-left: 1px solid var(--rule-2) !important;
    box-shadow: -12px 0 32px var(--board-shadow) !important;
    padding: var(--s4) var(--s4) var(--s3) !important;
    overflow-y: auto !important;
    transition: transform 260ms cubic-bezier(0.22, 0.61, 0.36, 1) !important;
  }
  /* A dimmed scrim so the board reads as backgrounded behind the panel — not
     interactive (no tap-to-close) since forwarding that tap into a Streamlit
     rerun needs the same click-bridge trickery as the board rows use, which
     isn't worth it when the panel's own close button already does the job. */
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ll-stage-marker)::before {
    content: ""; position: fixed; inset: 0;
    background: rgba(var(--void-rgb), 0.55);
    z-index: 999; pointer-events: none;
  }
  .st-key-close_bot_mobile { display: block !important; position: absolute !important;
    top: var(--s3) !important; right: var(--s3) !important; width: 32px !important; z-index: 2; }
}
/* Hidden outside the breakpoint above: the toolbar's own "Close bot" button
   already covers desktop, where the rail is a normal in-flow column and this
   corner control would be redundant clutter. */
.st-key-close_bot_mobile { display: none; }
.ll-stage-marker { display: none; }
/* The marker is hidden, but Streamlit still gives its element container a
   slot in the column's flex gap — 16px of nothing above the board. Removed
   from the layout entirely; the :has() rules above match on the marker being
   in the DOM, which display:none does not affect. */
[data-testid="stElementContainer"]:has(.ll-stage-marker) { display: none !important; }
.ll-rail-anchor { height: 0; margin: 0; padding: 0; }

/* The rail runs on a tighter rhythm than the board. Streamlit's default
   element gap left the empty state, the legend, the prompts and the composer
   floating as four unrelated islands down a tall column; pulling the gap in
   groups them into one panel that reads as a single tool. */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ll-stage-marker)
  > [data-testid="stColumn"]:last-child [data-testid="stVerticalBlock"] {
  gap: var(--s2) !important;
}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ll-stage-marker)
  > [data-testid="stColumn"]:last-child [data-testid="stElementContainer"] {
  margin-bottom: 0 !important;
}

/* The rail's contents, on the way in. The column is already sliding open, so
   this only has to keep the panel from appearing fully-formed in a gap that is
   still growing — it drifts in behind the edge. */
.ll-rail-in { animation: llRailIn 340ms cubic-bezier(0.22, 0.61, 0.36, 1) both; }
@keyframes llRailIn {
  from { opacity: 0; transform: translateX(16px); }
  to   { opacity: 1; transform: none; }
}
@media (prefers-reduced-motion: reduce) {
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ll-stage-marker),
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ll-stage-marker)
    > [data-testid="stColumn"] { transition: none !important; }
  .ll-rail-in { animation: none !important; }
}


/* ---- what changed since the last visit ---- */
.ll-since {
  border: 1px solid var(--rule-2); border-left: 2px solid var(--amber);
  border-radius: var(--radius); background: var(--shade-soft);
  padding: var(--s3) var(--s4); margin-bottom: var(--s3);
}
.ll-since-title {
  font-family: var(--font-board); font-size: var(--t-micro); font-weight: 700;
  letter-spacing: 0.14em; text-transform: uppercase; color: var(--ink-3);
  display: flex; align-items: center; gap: 7px; margin-bottom: 4px;
}
.ll-since-title .ll-icon { color: var(--amber); }
.ll-since-body { font-size: var(--t-small); color: var(--ink); line-height: 1.5; }

/* ---- bot with no API key: a stated condition, not a dead panel ---- */
.ll-nokey {
  border: 1px solid var(--rule-2); border-left: 2px solid var(--amber);
  border-radius: var(--radius);
  background: var(--shade-strong);
  padding: var(--s3) var(--s4); margin-bottom: var(--s3);
}
.ll-nokey-title {
  font-family: var(--font-board); font-size: var(--t-small); font-weight: 700;
  letter-spacing: 0.12em; text-transform: uppercase; color: var(--ink-2);
  display: flex; align-items: center; gap: 8px; margin-bottom: 5px;
}
.ll-nokey-title .ll-icon { color: var(--amber); }
.ll-nokey-body { font-size: var(--t-small); color: var(--ink-3); line-height: 1.55; }
.ll-nokey-body code {
  background: var(--shade-soft); color: var(--ink-2);
  padding: 1px 5px; border-radius: 3px; font-size: 0.92em;
}

/* ---- debt aging: same departure tone used for is-neg elsewhere, applied to
   an unsettled receivable/payable once it has aged past the threshold ---- */
.ll-aging-head {
  display: flex; align-items: center; gap: 6px;
  font-size: var(--t-micro); font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; color: var(--departure); margin: var(--s2) 0 6px;
}
.ll-aging-row {
  display: flex; align-items: baseline; gap: 8px;
  font-size: var(--t-small); color: var(--ink); padding: 4px 0;
}
.ll-aging-row .amt { color: var(--ink-2); font-weight: 600; }
.ll-aging-row .days {
  margin-left: auto; font-family: var(--font-board); font-weight: 700;
  color: var(--departure);
}

/* ---- monthly digest: one bot-written card on the first load of a new month */
.ll-digest .ll-panel-body { font-size: var(--t-body); color: var(--ink-2); line-height: 1.6; }

/* ---- recurring-due banner: shown above the board once a template's day
   has arrived and it has not been logged (or skipped) yet this month ---- */
.ll-recur { margin-bottom: var(--s3); }
.ll-recur-item {
  display: flex; align-items: baseline; gap: var(--s3);
  padding: 6px 0; border-bottom: 1px solid var(--rule);
  font-size: var(--t-small); color: var(--ink);
}
.ll-recur-item:last-child { border-bottom: none; }
.ll-recur-item .sub {
  color: var(--ink-3); font-size: var(--t-micro); font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.08em;
}
.ll-recur-item .amt {
  margin-left: auto; font-family: var(--font-board); font-weight: 600;
  color: var(--ink-2); white-space: nowrap;
}

/* ---- demo banner: sample data must never pass as real ---- */
.ll-demo {
  display: flex; align-items: center; gap: 9px;
  padding: 9px var(--s4); border: 1px dashed var(--amber-24);
  background: var(--amber-12); border-radius: var(--radius);
  color: var(--amber); font-size: var(--t-small); font-weight: 600;
  margin-bottom: var(--s3);
}
.ll-demo span { color: var(--ink-2); font-weight: 500; }

/* ============================================== streamlit widget skins */

[data-testid="stSidebar"] .stButton button,
[data-testid="stSidebar"] .stFormSubmitButton button,
[data-testid="stSidebar"] [data-testid="stPopover"] > div > button,
.stButton button, .stFormSubmitButton button, [data-testid="stPopover"] > div > button,
[data-testid="stDownloadButton"] button {
  font-family: var(--font-ui) !important;
  font-size: var(--t-small) !important; font-weight: 600 !important;
  letter-spacing: 0.03em !important;
  background: var(--panel-2) !important;
  color: var(--ink) !important;
  border: 1px solid var(--rule-2) !important;
  border-radius: var(--radius) !important;
  min-height: 36px !important;
  transition: background 140ms var(--ease), border-color 140ms var(--ease), color 140ms var(--ease) !important;
}
.stButton button:hover, .stFormSubmitButton button:hover,
[data-testid="stDownloadButton"] button:hover,
[data-testid="stPopover"] > div > button:hover {
  background: var(--panel-3) !important;
  border-color: var(--amber) !important;
  color: var(--amber) !important;
}
.stButton button p, .stFormSubmitButton button p, [data-testid="stDownloadButton"] button p {
  font-weight: 600 !important; -webkit-text-fill-color: currentColor !important;
}
/* Streamlit tags form submits as kind="primaryFormSubmit", not "primary",
   so match the prefix rather than the exact value. */
.stApp button[kind^="primary"] {
  background: var(--amber) !important; color: var(--void) !important;
  border-color: var(--amber) !important;
}
.stApp button[kind^="primary"] p { color: var(--void) !important; }
.stApp button[kind^="primary"]:hover {
  filter: brightness(1.09); color: var(--void) !important;
  border-color: var(--amber) !important;
}
.stButton button:disabled, .stFormSubmitButton button:disabled {
  opacity: 0.42 !important; cursor: not-allowed !important;
}

[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label {
  font-size: var(--t-micro) !important; font-weight: 700 !important;
  letter-spacing: 0.14em !important; text-transform: uppercase !important;
  color: var(--ink-3) !important; margin-bottom: 5px !important;
}
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input, [data-baseweb="select"] > div,
[data-testid="stTextArea"] textarea {
  background: var(--panel-2) !important;
  border: 1px solid var(--rule-2) !important;
  border-radius: var(--radius) !important;
  color: var(--ink) !important;
  font-family: var(--font-ui) !important; font-size: var(--t-body) !important;
}
/* Selectbox and date-input shells.
   These are the boxes that stayed black in light mode. The rule above styles
   the <input> and [data-baseweb="select"] — but this Streamlit build paints
   the *shell around* them instead, and that shell carries no data-baseweb
   attribute at all, so nothing above ever matched it. It fills itself from
   config.toml's static backgroundColor (#07090C), which is why it stayed dark
   no matter which token set was active: it was never reading a token.
   Selected structurally via role="group" / the field testid rather than the
   st-emotion-cache-* class beside it, which is a build hash and would break
   on any Streamlit upgrade. */
[data-testid="stSelectbox"] > div > div[role="group"],
[data-testid="stMultiSelect"] > div > div[role="group"],
[data-testid="stDateInputField"],
[data-testid="stTextInputRootElement"],
[data-testid="stNumberInputContainer"] {
  background: var(--panel-2) !important;
  border: 1px solid var(--rule-2) !important;
  border-radius: var(--radius) !important;
  color: var(--ink) !important;
}
[data-testid="stSelectbox"] > div > div[role="group"]:hover,
[data-testid="stMultiSelect"] > div > div[role="group"]:hover,
[data-testid="stDateInputField"]:hover { border-color: var(--amber) !important; }
[data-testid="stSelectbox"] div[role="group"] *,
[data-testid="stDateInputField"] * { color: var(--ink) !important; }
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder { color: var(--ink-3) !important; opacity: 1 !important; }
[data-testid="stTextInput"] input:focus, [data-testid="stNumberInput"] input:focus,
[data-testid="stTextArea"] textarea:focus { border-color: var(--amber) !important; }
[data-baseweb="select"] svg { color: var(--ink-3) !important; }
[data-baseweb="popover"] [role="listbox"], [data-baseweb="menu"] {
  background: var(--panel-2) !important; border: 1px solid var(--rule-2) !important;
}
[data-baseweb="menu"] li:hover { background: var(--panel-3) !important; }
[data-testid="stNumberInput"] button { background: var(--panel-3) !important; border-color: var(--rule-2) !important; }
[data-testid="stForm"] { border: none !important; padding: 0 !important; }
[data-testid="stCheckbox"] p { font-size: var(--t-small) !important; color: var(--ink-2) !important; }
[data-testid="stCaptionContainer"] p { font-size: var(--t-micro) !important; color: var(--ink-3) !important; }
/* Plain st.markdown text (section headers like "**Budgets**", the records
   count line, ledger/debt column headings) has no custom class of its own,
   so nothing here was overriding Streamlit's own paragraph color — which
   comes from .streamlit/config.toml's static textColor and, like the h1
   masthead above, only ever matched dark mode's ink by coincidence. */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] strong,
[data-testid="stMarkdownContainer"] em { color: var(--ink) !important; }
/* The bot answers comparison questions with a markdown table, and a table is
   none of the tags above — its cells kept Streamlit's static light-grey ink,
   which is invisible on a cream panel. Headings, quotes, code and links had
   the same gap. Tables also get real rules, since a borderless one on a plain
   panel is unreadable regardless of colour. */
[data-testid="stMarkdownContainer"] h1, [data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3, [data-testid="stMarkdownContainer"] h4,
[data-testid="stMarkdownContainer"] h5, [data-testid="stMarkdownContainer"] h6,
[data-testid="stMarkdownContainer"] td, [data-testid="stMarkdownContainer"] th,
[data-testid="stMarkdownContainer"] blockquote,
[data-testid="stMarkdownContainer"] code { color: var(--ink) !important; }
[data-testid="stMarkdownContainer"] a { color: var(--amber) !important; }
[data-testid="stMarkdownContainer"] table {
  border-collapse: collapse !important; width: 100% !important;
  font-size: var(--t-small) !important; margin: var(--s2) 0 !important;
  background: transparent !important;
}
[data-testid="stMarkdownContainer"] th {
  font-family: var(--font-board) !important; font-weight: 700 !important;
  letter-spacing: 0.08em !important; text-transform: uppercase !important;
  font-size: var(--t-micro) !important; color: var(--ink-2) !important;
  text-align: left !important; background: var(--shade-strong) !important;
}
[data-testid="stMarkdownContainer"] th,
[data-testid="stMarkdownContainer"] td {
  border: 1px solid var(--rule) !important; padding: 6px 9px !important;
}
[data-testid="stMarkdownContainer"] tbody tr:nth-child(even) td {
  background: var(--shade-soft) !important;
}
[data-testid="stMarkdownContainer"] code {
  background: var(--shade-strong) !important; padding: 1px 5px !important;
  border-radius: 3px !important; font-size: 0.92em !important;
}
/* A table wider than the rail must scroll inside its own message, not push
   the chat column sideways. */
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] { overflow-x: auto !important; }

[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: 2px !important; background: transparent !important;
  border-bottom: 1px solid var(--rule) !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  font-family: var(--font-board) !important; font-size: var(--t-small) !important;
  font-weight: 600 !important; letter-spacing: 0.12em !important;
  text-transform: uppercase !important; color: var(--ink-3) !important;
  background: transparent !important; padding: 9px 15px !important;
}
[data-testid="stTabs"] [aria-selected="true"] { color: var(--amber) !important; }
[data-testid="stTabs"] [data-baseweb="tab-highlight"] { background: var(--amber) !important; }
[data-testid="stTabs"] [data-baseweb="tab-border"] { display: none !important; }

[data-testid="stExpander"] {
  background: var(--panel) !important; border: 1px solid var(--rule-2) !important;
  border-radius: var(--radius) !important;
}
/* The background here is the fix for the black header bar: Streamlit leaves
   this summary transparent while the expander is shut, then paints it from
   config.toml's static dark palette the moment it is opened — so the bar only
   turned black once you expanded it, which is why a closed-state check missed
   it. Pinned transparent in both states, with the hover tint drawn from the
   active token set instead of Streamlit's fixed blue-grey. */
[data-testid="stExpander"] summary {
  font-family: var(--font-board) !important; font-size: var(--t-small) !important;
  font-weight: 700 !important; letter-spacing: 0.13em !important;
  text-transform: uppercase !important; color: var(--ink-2) !important;
  background: transparent !important; border-radius: var(--radius) !important;
}
[data-testid="stExpander"] summary:hover {
  color: var(--amber) !important; background: var(--shade-strong) !important;
}
[data-testid="stExpander"] summary * { color: inherit !important; }

[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
  border: 1px solid var(--rule) !important; border-radius: var(--radius) !important;
}
[data-testid="stAlert"] { border-radius: var(--radius) !important; }
[data-testid="stFileUploaderDropzone"] {
  background: var(--panel-2) !important; border: 1px dashed var(--rule-2) !important;
  border-radius: var(--radius) !important;
}
/* The "Browse files" button inside the dropzone. Streamlit fills it from
   config.toml's static dark secondaryBackgroundColor while the label colour
   comes from the active token set — so in light mode it rendered dark ink on
   a near-black fill and the text was unreadable. Both halves are pinned to
   tokens here so the pair can never disagree again. */
/* Popovers, tooltips and their buttons. These carry their own test ids that
   none of the button rules above match, so they kept filling from
   config.toml's static dark palette — the "..." chat menu rendered near-black
   on a cream panel, and its tooltip with it. */
[data-testid="stPopoverButton"] {
  background: var(--panel-2) !important;
  border: 1px solid var(--rule-2) !important;
  color: var(--ink) !important;
  border-radius: var(--radius) !important;
}
[data-testid="stPopoverButton"]:hover {
  border-color: var(--amber) !important; color: var(--amber) !important;
}
[data-testid="stPopoverButton"] * { color: inherit !important; }
[data-testid="stPopoverBody"], [data-testid="stPopover"] > div {
  background: var(--panel) !important;
  border: 1px solid var(--rule-2) !important;
  border-radius: var(--radius) !important;
}
[data-testid="stTooltipContent"] {
  background: var(--panel-3) !important;
  border: 1px solid var(--rule-2) !important;
  color: var(--ink) !important;
  border-radius: var(--radius) !important;
}
[data-testid="stTooltipContent"] * { color: var(--ink) !important; }

[data-testid="stFileUploaderDropzone"] button {
  background: var(--panel-3) !important;
  border: 1px solid var(--rule-2) !important;
  color: var(--ink) !important;
  border-radius: var(--radius) !important;
}
[data-testid="stFileUploaderDropzone"] button:hover {
  border-color: var(--amber) !important; color: var(--amber) !important;
}
[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploaderDropzoneInstructions"] * { color: var(--ink-2) !important; }
[data-testid="stFileUploaderFile"],
[data-testid="stFileUploaderFile"] * { color: var(--ink) !important; }
[data-testid="stToast"] { background: var(--panel-3) !important; border: 1px solid var(--rule-2) !important; }
[data-testid="stDialog"] > div { background: var(--panel) !important; border: 1px solid var(--rule-2) !important; }

/* --------------------------------------------------------- the bot */
.ll-bot-log { max-height: 460px; overflow-y: auto; padding-right: 5px; }
[data-testid="stChatMessage"] {
  background: transparent !important; padding: var(--s2) 0 !important;
  border-bottom: 1px solid var(--rule) !important;
}
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li {
  font-size: var(--t-body) !important; line-height: 1.6 !important; color: var(--ink) !important;
}
[data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] {
  background: var(--panel-3) !important; color: var(--amber) !important;
}
/* One ring, not three. Streamlit draws a focus border on an inner wrapper AND
   an outline on the textarea itself; with this panel border that stacked into
   the box-inside-a-box seen on click. The outer element is the only ring now.
   It also fills from config.toml's static dark secondaryBackgroundColor, so
   the child is cleared to transparent. */
[data-testid="stChatInput"] {
  background: var(--panel-2) !important;
  border: 1px solid var(--rule-2) !important;
  border-radius: var(--radius) !important;
  transition: border-color 140ms ease;
  /* The composer sits last in a tall column, and as a stretchy flex item it
     absorbed all the leftover height — which is what stretched an empty
     one-row field to 189px. Fixed basis: it takes only what it needs. */
  flex: 0 0 auto !important;
  height: auto !important;
  min-height: 0 !important;
}
[data-testid="stChatInput"]:focus-within { border-color: var(--amber) !important; }
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] > div > div {
  background: transparent !important;
  border: none !important; box-shadow: none !important;
  border-radius: var(--radius) !important;
  height: auto !important; min-height: 0 !important;
}
[data-testid="stChatInput"] textarea {
  font-family: var(--font-ui) !important; font-size: var(--t-body) !important;
  color: var(--ink) !important; background: transparent !important;
  outline: none !important; box-shadow: none !important;
  resize: none !important;
}
[data-testid="stChatInput"] textarea:focus {
  outline: none !important; box-shadow: none !important;
}
/* The wrapper immediately around the field is a flex item in a column, so it
   grew to swallow every spare pixel of that column — an empty one-row field
   was being stretched to 177px. A fixed basis makes it take only the row it
   needs, and Streamlit's own auto-grow (which already works correctly once
   text exists) still drives the height from there. */
[data-testid="stChatInput"] > div > div > div:first-child {
  flex: 0 0 auto !important;
  height: auto !important;
  min-height: 0 !important;
}
[data-testid="stChatInput"] textarea { max-height: 7.5em !important; }
[data-testid="stChatInput"] textarea::placeholder { color: var(--ink-3) !important; opacity: 1 !important; }
[data-testid="stChatInput"] button { background: var(--amber) !important; border-radius: 2px !important; }
[data-testid="stChatInput"] button svg { color: var(--void) !important; }


/* ---- bot thinking state: shown from the moment a reply starts generating,
   cleared the instant the first streamed token arrives ---- */
.ll-thinking {
  display: flex; align-items: center; gap: 7px;
  font-size: var(--t-body); color: var(--ink-3); padding: var(--s2) 0;
}
.ll-thinking .dot {
  width: 5px; height: 5px; border-radius: 50%; background: var(--amber);
  animation: llThinkPulse 1.1s ease-in-out infinite;
}
.ll-thinking .dot:nth-child(2) { animation-delay: 0.15s; }
.ll-thinking .dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes llThinkPulse {
  0%, 80%, 100% { opacity: 0.25; transform: translateY(0); }
  40%           { opacity: 1;    transform: translateY(-2px); }
}

/* --------------------------------------------------------- reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ll-figures.is-flipping .ll-flap { animation: none !important; }
  .ll-thinking .dot { animation: none !important; opacity: 0.7 !important; }
  * { transition-duration: 0.01ms !important; }
}

/* --------------------------------------------------------- narrower desks */
/* One strip is the thesis. A narrower board buys room by stepping the figure
   down and tightening the cell, never by folding into a 2x2 of cards - that is
   the KPI grid this design exists to refuse. */
@container board (max-width: 1150px) {
  .ll-fig { padding: var(--s4) var(--s3) var(--s3); }
  .ll-fig-value { font-size: clamp(1.1rem, 3.45cqi, 2.5rem); }
  .ll-fig-value .cur { font-size: 0.32em; margin-right: 3px; padding-bottom: 0.45em; }
  .ll-fig-label { font-size: 0.625rem; letter-spacing: 0.12em; }
  .ll-fig-note { font-size: 0.625rem; }
}
@container board (max-width: 720px) {
  .ll-figures { grid-template-columns: repeat(2, 1fr); }
  .ll-fig:nth-child(2) { border-right: none; }
  .ll-fig:nth-child(1), .ll-fig:nth-child(2) { border-bottom: 1px solid var(--rule); }
}
@container board (max-width: 520px) {
  .ll-cols { grid-template-columns: 1fr; }
  .ll-col { border-right: none; border-bottom: 1px solid var(--rule); }
  .ll-figures { grid-template-columns: 1fr; }
  .ll-fig { border-right: none; border-bottom: 1px solid var(--rule); }
}
/* Twelve equal columns is the run strip's whole idea (see .ll-run above), and
   that stays true even here — squeezing them to fit would make every month
   unreadable at once. Scrolling instead keeps each column full-size; only the
   current one has to be on screen without swiping. direction:rtl on the strip
   (undone per-column so labels still read left-to-right) means the browser's
   unscrolled resting position is already the right edge — i.e. the current
   month — with no script needed to scroll there on load. */
@container board (max-width: 620px) {
  .ll-run {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scroll-snap-type: x proximity;
    direction: rtl;
  }
  .ll-run-col {
    direction: ltr;
    flex: 0 0 52px;
    min-width: 52px;
    scroll-snap-align: end;
  }
  .ll-run-key { flex-wrap: wrap; row-gap: 4px; }
}

/* board controls must never wrap to two lines */
.st-key-toggle_bot button, .st-key-open_settings button { white-space: nowrap !important; }

/* Clear chat is the one destructive control in the rail, and it holds one
   colour in both modes on purpose: a wipe should not read as an ordinary
   action just because the lights changed. Fixed red rather than --departure,
   which is a different red per mode. Declared last and with a heavier
   selector than the generic button skin, which is also !important and would
   otherwise win the tie on source order. */
div.st-key-clear_chat .stButton button,
div.st-key-clear_chat button {
  background: #C0392B !important;
  border: 1px solid #C0392B !important;
  color: #FFFFFF !important;
}
div.st-key-clear_chat .stButton button:hover,
div.st-key-clear_chat button:hover {
  background: #A93226 !important;
  border-color: #A93226 !important;
  color: #FFFFFF !important;
}
div.st-key-clear_chat button * { color: #FFFFFF !important; }
"""


# Injected only while the bot is shut. Everything it does is reversible by
# simply not emitting it, which is what lets the transition in _CSS_BODY run in
# both directions: closing adds these widths, opening removes them, and the
# same elements animate between the two.
_ROW = ('[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] '
        '.ll-stage-marker)')
BOT_CLOSED_CSS = f"""
{_ROW} {{ gap: 0 !important; }}
{_ROW} > [data-testid="stColumn"]:first-child {{
  flex: 1 1 100% !important; width: 100% !important;
  max-width: 100% !important; min-width: 0 !important;
}}
{_ROW} > [data-testid="stColumn"]:last-child {{
  flex: 0 0 0 !important; width: 0 !important;
  min-width: 0 !important; max-width: 0 !important;
  opacity: 0 !important; overflow: hidden !important;
  pointer-events: none !important;
}}
{_ROW}::before {{ content: none !important; display: none !important; }}
"""


# Emitted once, on the run that opens the panel, so the contents drift in
# behind the widening edge instead of appearing fully formed in a gap that is
# still growing.
RAIL_OPEN_CSS = f"""
{_ROW} > [data-testid="stColumn"]:last-child {{
  animation: llRailIn 340ms cubic-bezier(0.22, 0.61, 0.36, 1) both;
}}
@media (prefers-reduced-motion: reduce) {{
  {_ROW} > [data-testid="stColumn"]:last-child {{ animation: none !important; }}
}}
"""


def css(dark: bool = True) -> str:
    """The full stylesheet for the given mode.

    Only the root token block differs between modes; every other rule in
    _CSS_BODY reads its colors exclusively through var(...), so redeclaring
    the tokens is enough to re-theme the whole board.
    """
    root_vars = _DARK_VARS if dark else _LIGHT_VARS
    return _CSS_HEAD + root_vars + _FONT_AND_SCALE + _CSS_ROOT_CLOSE + _CSS_BODY


def flap_chars(text: str, animate: bool = False) -> str:
    """Render a figure as split-flap tiles, one per character.

    Separators (commas, dots, the compact-notation M) get no tile — a board's
    flaps carry digits, and boxing the punctuation makes the number harder to
    read, not more thematic.
    """
    out = []
    for i, ch in enumerate(text):
        sep = "" if ch.isdigit() else " sep"
        style = f' style="--i:{i}"' if animate else ""
        out.append(f'<span class="ll-flap{sep}"{style}>{ch}</span>')
    return "".join(out)
