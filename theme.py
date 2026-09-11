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

# Streamlit's OWN theme, which is a separate thing from the stylesheet below.
# st.dataframe and st.data_editor paint their cells to a canvas from a
# JavaScript theme Streamlit builds, and CSS cannot reach a canvas — so these
# few values are the only lever on the ledger and debt tables.
#
# This dict is handed to themesync.html at runtime, which used to carry its own
# hardcoded copy. The same values are ALSO in .streamlit/config.toml, which
# Streamlit reads at boot before any of this imports and so cannot be generated
# from here; those two must be kept in step by hand. Two copies is one fewer
# than there were, and the radii below are why that mattered — a sixth field
# duplicated three ways is a drift waiting to happen.
STREAMLIT_THEME = {
    "Dark": {
        "base": "dark", "primaryColor": "#FFB300",
        "backgroundColor": "#07090C", "secondaryBackgroundColor": "#0E1116",
        "textColor": "#E9EDF2", "font": "sans serif",
        "baseRadius": "10px", "buttonRadius": "10px",
    },
    "Light": {
        "base": "light", "primaryColor": "#A85D00",
        "backgroundColor": "#FBF8F0", "secondaryBackgroundColor": "#F3EDE0",
        "textColor": "#1A1712", "font": "sans serif",
        "baseRadius": "10px", "buttonRadius": "10px",
    },
}

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


def _platform_arc(name, _i=0, _n=0) -> str:
    """donut_svg's colour hook for the spending ring."""
    return platform_color(name)


def amber_tints(_name=None, i: int = 0, n: int = 1) -> str:
    """donut_svg's colour hook for the arrivals ring: one hue, stepped by share.

    Income sources are not a taxonomy the way spending categories are — they
    are whoever happened to pay you — so giving them their own categorical
    palette would put hue to a third job, which the Two Jobs Rule forbids and
    which would also make "Dada" and "Salary" look like they belong to some
    scheme they do not. Amber is the board's own light and the arrivals side
    reads in it; the step encodes share, which is the only thing that ranks.
    """
    top, bottom = 0.95, 0.30
    if n <= 1:
        return f"rgba(var(--amber-rgb),{top})"
    step = (top - bottom) / (n - 1)
    return f"rgba(var(--amber-rgb),{top - i * step:.3f})"


def donut_svg(records, total, center_label="", size=184, thickness=24,
              amount_fmt=None, color_for=None, key="category",
              label="Spending by platform", center_sub="spent"):
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
    color_for = color_for or _platform_arc
    radius = (size - thickness) / 2
    circumference = 2 * math.pi * radius
    cx = cy = size / 2
    cursor = 0.0
    seam = max(circumference * 0.006, 1.0)

    arcs = []
    for i, r in enumerate(records):
        amount = float(r["amount"])
        frac = amount / total if total else 0.0
        length = frac * circumference
        seg_len = max(length - seam, 0.0)
        name = str(r[key])
        # The colour goes in `style`, not the `stroke` attribute: a
        # presentation attribute takes a literal colour and will not resolve a
        # var(), and the income ring is drawn in amber tints that are exactly
        # that. The track below has always done it this way for the same reason.
        colour = color_for(name, i, len(records))
        arcs.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius:.2f}" fill="none" '
            f'style="stroke:{colour}" stroke-width="{thickness}" stroke-linecap="butt" '
            f'stroke-dasharray="{seg_len:.2f} {circumference - seg_len:.2f}" '
            f'stroke-dashoffset="{-cursor:.2f}" transform="rotate(-90 {cx} {cy})">'
            f'<title>{esc(name)}: {esc(amount_fmt(amount))} '
            f'({frac * 100:.0f}%)</title></circle>'
        )
        cursor += length

    track = (f'<circle cx="{cx}" cy="{cy}" r="{radius:.2f}" fill="none" '
             f'style="stroke:rgba(var(--ink-rgb),0.09)" stroke-width="{thickness}"/>')
    # Placed off the radius rather than at fixed offsets, so the centre stack
    # stays put if the donut is ever drawn at another size. The old +/-3 and +15
    # were tuned by eye against a 132px ring and drifted the moment it grew.
    center = (
        f'<text x="{cx}" y="{cy + size * 0.005:.2f}" text-anchor="middle" '
        f'class="ll-donut-total">{esc(center_label)}</text>'
        f'<text x="{cx}" y="{cy + size * 0.115:.2f}" text-anchor="middle" '
        f'class="ll-donut-label">{esc(center_sub)}</text>'
    ) if center_label else ""

    return (f'<svg class="ll-donut" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}" role="img" aria-label="{esc(label)}">'
            f'{track}{"".join(arcs)}{center}</svg>')


def trend_svg(values, colour, width=104, height=26, label=""):
    """Inline sparkline for one category, over whatever steps it is handed.

    Two callers, two axes: a month view passes that month's days (cumulative,
    so the line only ever climbs), and All Time passes one step per month.
    Nothing here needs to know which — it draws the numbers it is given.

    Scaled to its OWN peak, not to a scale shared with the other categories.
    The question this answers is "what shape is this category", which is about
    a category against its own past; a shared scale would answer a different
    question and would flatten every small category into a straight line while
    it did so. The amount beside each row is what makes them comparable.
    """
    values = [float(v) for v in values]
    if len(values) < 2:
        return ""
    top = max(values)
    inset = 1.5
    floor_y = height - inset
    span_x = width - inset * 2
    span_y = height - inset * 2

    if top <= 0:
        # A run of flat zero is a real answer. Drawing nothing would look like
        # missing data, which is a different and wrong statement.
        line = (f'<line x1="{inset}" y1="{floor_y:.2f}" x2="{width - inset}" '
                f'y2="{floor_y:.2f}" stroke="{colour}" stroke-width="1.6" '
                f'stroke-linecap="round" opacity="0.35"/>')
        pts_last = None
        body = line
    elif min(values) == top:
        # Every reading identical — a salary that is the same number every
        # month. On an axis scaled to its own peak that puts every point at
        # the ceiling, and with the area fill under it the row came out as a
        # solid block: it read as "enormous" when it means "unvarying". Drawn
        # flat through the middle instead, with no fill, which is the same
        # thing the zero case says one floor down.
        mid = height / 2
        line = (f'<line x1="{inset}" y1="{mid:.2f}" x2="{width - inset}" '
                f'y2="{mid:.2f}" stroke="{colour}" stroke-width="1.6" '
                f'stroke-linecap="round"/>')
        pts_last = (width - inset, mid)
        body = line
    else:
        step = span_x / (len(values) - 1)
        pts = [(inset + i * step, floor_y - (v / top) * span_y)
               for i, v in enumerate(values)]
        poly = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
        area = (f'<polygon points="{inset},{floor_y:.2f} {poly} '
                f'{width - inset},{floor_y:.2f}" fill="{colour}" '
                f'fill-opacity="0.15" stroke="none"/>')
        line = (f'<polyline points="{poly}" fill="none" stroke="{colour}" '
                f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>')
        pts_last = pts[-1]
        body = area + line

    tip = (f'<circle cx="{pts_last[0]:.2f}" cy="{pts_last[1]:.2f}" r="2.1" '
           f'fill="{colour}" stroke="none"/>') if pts_last else ""
    title = f"<title>{esc(label)}</title>" if label else ""

    return (f'<svg class="ll-spark" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="{esc(label or "trend")}">{title}{body}{tip}</svg>')


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

  /* Two kinds of object live on this screen and they want different corners.
     The MECHANISM — flap tiles, platform chips, meter tracks, the run strip —
     stays hard, because square is what makes a flap read as a physical thing
     rather than a number in a box. The CHROME around it — buttons, inputs,
     dialogs, banners — is furniture, not mechanism, and at 3px it read like a
     framework default. Softening only the chrome makes the board a housing
     with a hard mechanism inside it, which is a truer story than the uniform
     near-square this file used to enforce. */
  --radius-tile: 2px;   /* flaps, chips, meters, run strip */
  --radius-sm:   6px;   /* inline code, the composer's send key */
  --radius:      10px;  /* buttons, inputs, banners, popovers, tooltips */
  --radius-lg:   14px;  /* housings: the board, side panels, the dialog */

  /* Chip ink is deliberately mode-invariant. It was var(--void), which is
     near-black in dark mode but CREAM in light — so a light-mode Shopping chip
     put #EDE7D9 text on #FBBF24. Both the note above and DESIGN.md already
     claimed a fixed always-dark ink; only the code disagreed. */
  --chip-ink: #07090C;

  /* Hairlines and the amber wash both derive from a raw r,g,b triplet rather
     than a fixed rgba(), so a single color swap per mode (below) is enough to
     re-theme every hairline, hover and hairline-adjacent tint at once. */
  --rule:      rgba(var(--ink-rgb),var(--rule-a));
  --rule-2:    rgba(var(--ink-rgb),var(--rule-2-a));
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
  --rule-a:       0.085;
  --rule-2-a:     0.17;
  /* Chrome elevation. Content is still divided by hairlines, never boxed —
     these are for things you press or that float above the page. */
  --lift-1: 0 1px 2px rgba(0,0,0,0.35);
  --lift-2: 0 4px 12px -2px rgba(0,0,0,0.5);
  --lift-3: 0 24px 60px -16px rgba(0,0,0,0.72);
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
  --shade-strong: rgba(26,23,18,0.070);
  --shade-soft:   rgba(26,23,18,0.040);
  --board-shadow: rgba(20,18,14,0.22);
  /* Dark ink on cream reads fainter than pale ink on near-black at the same
     alpha, so light mode runs its hairlines higher to land in the same place.
     Held per mode rather than in the shared derivation so dark is untouched. */
  --rule-a:       0.12;
  --rule-2-a:     0.22;
  --lift-1: 0 1px 2px rgba(20,18,14,0.10);
  --lift-2: 0 4px 12px -2px rgba(20,18,14,0.15);
  --lift-3: 0 24px 60px -16px rgba(20,18,14,0.24);
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

# The type is served from the app's own /app/static/fonts, not fetched from
# Google at runtime. An @import is a blocking request to a third party on
# every load: when it is slow, blocked, or unreachable — a restrictive
# network, a region that filters it, a cold origin — every rule below still
# applies but the whole product silently falls back to Arial Narrow, which
# reads as a cheap imitation of itself rather than as a broken stylesheet.
# Self-hosting makes the signage type as reliable as the layout it sits in,
# and the latin subset costs 152KB served from the same origin.
_CSS_HEAD = """
@font-face {
  font-family: 'Barlow';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('/app/static/fonts/barlow-400.woff2') format('woff2');
}
@font-face {
  font-family: 'Barlow';
  font-style: normal;
  font-weight: 500;
  font-display: swap;
  src: url('/app/static/fonts/barlow-500.woff2') format('woff2');
}
@font-face {
  font-family: 'Barlow';
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url('/app/static/fonts/barlow-600.woff2') format('woff2');
}
@font-face {
  font-family: 'Barlow';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url('/app/static/fonts/barlow-700.woff2') format('woff2');
}
@font-face {
  font-family: 'Barlow Condensed';
  font-style: normal;
  font-weight: 500;
  font-display: swap;
  src: url('/app/static/fonts/barlow-condensed-500.woff2') format('woff2');
}
@font-face {
  font-family: 'Barlow Condensed';
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url('/app/static/fonts/barlow-condensed-600.woff2') format('woff2');
}
@font-face {
  font-family: 'Barlow Condensed';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url('/app/static/fonts/barlow-condensed-700.woff2') format('woff2');
}

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
    radial-gradient(1200px 520px at 50% -8%, rgba(var(--amber-rgb),0.055), transparent 65%),
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
  border-radius: var(--radius);
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
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 10px !important; }
/* Section captions carry a full 24px above them on the board, where they
   separate whole regions. In the sidebar they separate two short groups in a
   panel that has to fit a laptop window, and 24px twice over was most of a row. */
[data-testid="stSidebar"] .ll-cap { margin-top: var(--s4); }
/* The credit rides to the bottom of the sidebar column. margin-top:auto in a
   flex column consumes free space only — it adds no height of its own, so it
   cannot push the credit past the fold on a short window the way the old
   spacer div was meant to and a real spacer would.
   
   It goes on the LAYOUT WRAPPER, not on .st-key-ll_credit itself. Streamlit
   inserts a stLayoutWrapper between a keyed container and the block above it,
   so the keyed element is a grandchild of the flex column and not a flex item
   of it — `auto` there has no free space to consume and resolves to 0, which is
   exactly what it did: the rule applied, computed to 0px, and nothing moved. */
[data-testid="stSidebar"] [data-testid="stLayoutWrapper"]:has(> .st-key-ll_credit) {
  margin-top: auto !important;
}
[data-testid="stSidebar"] hr { border-color: var(--rule) !important; margin: var(--s3) 0 !important; }

/* ------------------------------------------------------- masthead */
/* The wordmark is the one thing in this panel that should be large; it was set
   smaller than the board's own service period, which read as timid.
   
   It starts below the collapse arrow rather than beside it. The arrow is 32x28
   in the top-right corner and its bottom edge is at y=36; the title needs the
   full 207px of content width to hold "LOOT · LEDGER" on one line at this size,
   so there is no room to sit alongside it — reserving the arrow's column drops
   the largest fitting size to 2.1rem, smaller than this was before it grew.
   Passing underneath keeps the size and removes the collision outright. The
   bottom margin is trimmed to pay most of the height back. */
.ll-mast { margin-top: 28px; margin-bottom: var(--s2); }
.ll-mast-name {
  font-family: var(--font-board) !important;
  font-size: 2.4rem !important; font-weight: 700 !important; line-height: 0.92 !important;
  /* Streamlit pads every <h1> by 20px above and 16px below. On a page that is
     36px of nothing; in a sidebar that has to fit a laptop window it was the
     gap above the wordmark and a third of the space the wordmark itself takes.
     Zeroed, the type gets bigger AND the title sits higher than before. */
  padding: 0 !important;
  letter-spacing: 0.012em; text-transform: uppercase;
  /* !important because this is a real <h1> — Streamlit applies its own
     heading color from .streamlit/config.toml's static textColor, which
     otherwise wins over an unqualified color here. That hardcoded value
     happens to equal dark mode's --ink exactly, which is why this was
     invisible until light mode gave the two values something to disagree on. */
  color: var(--ink) !important; margin: 0; display: flex; align-items: baseline; gap: 0.42rem;
}
.ll-mast-name .ll-lamp {
  /* Sized in em, not pixels. It was a fixed 9px against a 2.05rem wordmark —
     0.27 of the cap height — and when the wordmark grew the lamp stayed put and
     quietly shrank against it. Tied to the type, it holds the proportion it was
     drawn at whatever size the title is set to. The glow scales with it. */
  width: 0.27em; height: 0.27em; border-radius: 50%;
  background: var(--amber);
  box-shadow: 0 0 0.3em 0.03em rgba(255,179,0,0.65);
  align-self: center;
  /* Never shrink. The two words are text nodes and cannot compress below their
     own glyphs, so this was the only item in the flex row with any give — and
     when the title ran wide, the browser took every pixel it needed out of the
     lamp. It did not disappear; it was crushed to a sliver. */
  flex: 0 0 auto;
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

/* The month rail is gone: it is a dropdown now, because a stack of buttons had
   to be capped at ten to fit the sidebar and that cap left older months with no
   route from here. Its stylesheet went with it — .ll-rail / -row / -mon / -bar /
   -fill / -amt described markup app.py had already stopped emitting long before
   that, and had been matching nothing for some time. (.ll-rail-anchor and
   .ll-rail-in below are unrelated and still live: they belong to the bot rail.) */

/* ============================================================ the board */

.ll-board {
  container-type: inline-size;
  container-name: board;
  background: linear-gradient(180deg, var(--panel-2) 0%, var(--panel) 100%);
  border: 1px solid var(--rule-2);
  border-radius: var(--radius-lg);
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
  border-radius: var(--radius-tile); padding: 0.07em 0.055em 0.09em;
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
/* Perspective only while the flap is actually turning. On .ll-fig-value
   unconditionally it gave all four figures a 3D rendering context that
   outlived the one 560ms it exists for — a permanent compositing promotion on
   the four largest pieces of type on the board, re-rasterised on every scroll
   frame for nothing. The keyframes are already gated on .is-flipping; the
   perspective they need is now gated with them, and a figure that is not
   moving is plain 2D text again. */
.ll-figures.is-flipping .ll-fig-value { perspective: 460px; }

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
/* No scroll snapping here, and it is not a matter of taste.
   The list carried `scroll-snap-type: y proximity` with `scroll-snap-align:
   start` on every row, so the browser pulled each scroll to the nearest row
   edge. Measured with 40px wheel deltas over the departures list, the list
   advanced 54, 60, 61, 61, 62, 61, 58, 25, 45, 55, 63, 62, 62, 43 — every
   notch a different distance, none of them the distance asked for. That is
   the shifting people report when they scroll the board: not a layout bug,
   a scroll position the page keeps overriding.

   Snapping earns its keep on a pager, where every stop is a destination. A
   ledger is a continuous list of rows people read past, and the rows are
   61px, so the snap was never more than a rounding error away from where the
   scroll already was — all of the jerk, none of the use. */
.ll-rows {
  max-height: 336px; overflow-y: auto;
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
div[class*="st-key-rm_"], div[class*="st-key-jump_"] {
  position: absolute !important; left: -9999px !important;
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
  letter-spacing: 0.06em; text-align: center; padding: 3px 0;
  border-radius: var(--radius-tile);
  color: var(--chip-ink);
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
  position: relative; height: 26px; border-radius: var(--radius-tile);
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
  border-radius: var(--radius-lg); overflow: hidden;
}
/* Cards lift under the cursor. This is a state transition on direct
   interaction, which is the one kind of motion this product allows besides the
   flap settle — nothing here animates on load or on rerun, and nothing scales.
   The board itself is deliberately NOT in this list: it is the object the whole
   page is about, it already carries the one ambient drop, and a page that
   shrugs when the pointer crosses it reads as loose rather than responsive. */
.ll-panel, .ll-person {
  transition: transform 160ms var(--ease), box-shadow 160ms var(--ease),
              border-color 160ms var(--ease);
  will-change: transform;
}
.ll-panel:hover, .ll-person:hover {
  transform: translateY(-3px);
  box-shadow: var(--lift-2);
  border-color: rgba(var(--ink-rgb), calc(var(--rule-2-a) + 0.10));
}
@media (prefers-reduced-motion: reduce) {
  /* The global rule only collapses the duration; the displacement itself has
     to go, or the card still jumps 3px the instant it is pointed at. */
  .ll-panel:hover, .ll-person:hover { transform: none !important; }
}
.ll-panel-head {
  display: flex; align-items: center; justify-content: space-between; gap: var(--s3);
  padding: var(--s3) var(--s4); border-bottom: 1px solid var(--rule);
}
/* A panel title names a piece of furniture, not a platform. It reads; it does
   not announce. Column titles (ARRIVALS / DEPARTURES) are the board itself and
   keep the signage treatment - the two rules split here deliberately. */
.ll-panel-title {
  display: flex; align-items: center; gap: 8px;
  font-family: var(--font-ui); font-size: var(--t-h3); font-weight: 600;
  letter-spacing: normal; text-transform: none; color: var(--ink);
}
.ll-panel-body { padding: var(--s4); }

/* ---- platform load: spending by category as a stacked rail ---- */
/* The ring is the panel's headline and the list is its detail, so the ring
   gets the room. align-items:center keeps them optically related when the list
   is short — two categories should not leave a tall ring stranded at the top.
   
   The list is capped rather than left to take every pixel to the panel edge.
   Uncapped, a two-category month opened a hand's width of dead space between a
   name and its percentage — inside the row, where it reads as a broken layout
   rather than as margin. The cap moves that slack out of the rows.
   
   It goes to the right of the list, not between the ring and the list: pushing
   the list to the panel edge with space-between only trades a hole inside the
   rows for a 105px hole beside the ring, which is worse because it separates
   the two halves of one reading. Slack against the panel's outer edge is quiet;
   slack in the middle of a composition is not. */
.ll-load { display: flex; align-items: center; gap: var(--s4);
           justify-content: flex-start; }
.ll-donut-wrap { flex: 0 0 auto; }
.ll-donut circle { transition: opacity 140ms var(--ease); }
.ll-donut:hover circle:not(:hover) { opacity: 0.55; }
.ll-donut-total {
  font-family: var(--font-board); font-size: var(--t-h2); font-weight: 700;
  fill: var(--ink); letter-spacing: 0.01em;
}
.ll-donut-label {
  font-family: var(--font-ui); font-size: var(--t-micro); font-weight: 600;
  letter-spacing: 0.14em; text-transform: uppercase; fill: var(--ink-3);
}
.ll-load-list { flex: 0 1 auto; min-width: 0; max-width: 380px; width: 100%;
                display: flex; flex-direction: column; gap: 0; }
/* Arrivals rows carry a swatch, not a two-letter chip: a source is whoever
   paid you, not a platform with a fixed code in the map. Otherwise this is the
   trend row's grid: swatch, name, line, amount, change. The share each source
   holds moved off the row and onto its hover and its arc — the ring is already
   drawing it, and five columns in ~330px is all the row will take. */
.ll-src-item {
  display: grid;
  grid-template-columns: 22px minmax(0,1fr) auto auto auto;
  align-items: center; gap: var(--s2);
  padding: 7px 0; border-bottom: 1px solid var(--rule);
}
.ll-src-item .ll-load-name {
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ll-src-item .ll-load-amt { min-width: 0; }
/* Rising income is good news, so an arrival's change reads in the opposite
   tones to a departure's: up is the arrival colour, down is the departure
   one. Same figures, same class, inverted meaning — which is exactly what a
   modifier is for. */
.ll-trend-delta.is-in.up { color: var(--arrival); }
.ll-trend-delta.is-in.down { color: var(--departure); }
.ll-src-item:last-child { border-bottom: none; }
.ll-src-dot {
  width: 12px; height: 12px; border-radius: var(--radius-tile);
  display: inline-block; justify-self: center;
}
/* Do NOT add flex-wrap here. It was added when this panel went half-width, on
   the theory that a ring plus a list would not fit side by side — and it is
   the wrong tool, because the list can already shrink: `flex: 0 1 auto`
   against a 380px max-width. With wrapping on, the browser breaks the line at
   the basis rather than shrinking to fit, so at 496px of room the list
   dropped underneath a 184px ring and left the whole right half of the panel
   empty. Without it the list narrows to ~288px, sits beside the ring, and the
   row is full. */

/* ---- the spending calendar --------------------------------------------
   Days are mechanism, so they take --radius-tile like every other cell on
   the board: flaps, chips, meter tracks. A month is a grid of hard little
   squares, not a row of pills.
   
   aspect-ratio rather than a height, so the grid keeps its shape at any panel
   width without a media query per breakpoint. */
/* Seven day columns and a margin for the week's own total. The day columns
   share the room equally and the margin takes only what its figures need, so
   a wider panel grows the squares rather than the numbers. */
.ll-cal {
  display: grid; grid-template-columns: repeat(7, 1fr) auto;
  gap: 4px; max-width: 460px;
  /* The depth a lifted day comes forward into. On the grid rather than on each
     square, so every day shares one vanishing point — per-square, a day in the
     corner would swing around a pivot in the corner and read as toppling over
     rather than rising. */
  perspective: 1200px;
}
/* A day that can be opened is a CELL, not just a square, and the cell is the
   frame of reference for everything its card does. Because the cell is square,
   `100%` inside it is one day wide AND one day tall — which is what lets the
   open card be written entirely in day-units with no measuring at run time.
   The card is absolutely positioned, so it never contributes to the cell's
   size and the grid lays out exactly as it did before. */
.ll-cal-cell { position: relative; aspect-ratio: 1; transform-style: preserve-3d; }
.ll-cal-cell > .ll-cal-day { position: absolute; inset: 0; aspect-ratio: auto; }
/* The lifted day has to paint over the squares that come after it in the DOM.
   z-index on the card alone is not enough: preserve-3d makes each cell its own
   stacking context, so the card's z-index only orders it within its own cell
   and later cells still paint on top. The CELL is the thing that has to rise. */
.ll-cal-cell:has(.ll-vr:checked) { z-index: 6; }
/* The margin needs a gutter, not the 4px the day cells sit on: at the grid's
   own gap the totals read as an eighth column of the calendar rather than as
   an annotation beside it. Margin, NOT padding — these cells are right-aligned,
   so left padding moves the figure inside its box and leaves the column
   exactly where it was. */
.ll-cal-dow.is-sum { margin-left: var(--s4); }
/* The row total sits in the margin, not in the grid: no fill, no border, and
   the board's tabular figure face, so it reads as an annotation of the week
   rather than as an eighth day. */
.ll-cal-sum {
  display: flex; align-items: center; justify-content: flex-end;
  margin-left: var(--s4);
  font-family: var(--font-board); font-size: var(--t-micro);
  font-weight: 600; color: var(--ink-2); white-space: nowrap;
}
.ll-cal-sum.is-none { color: var(--ink-3); opacity: 0.5; }
.ll-cal-dow {
  font-family: var(--font-board); font-size: var(--t-micro);
  letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink-3);
  text-align: center; padding-bottom: 2px;
}
.ll-cal-pad { aspect-ratio: 1; }
.ll-cal-day {
  aspect-ratio: 1; display: flex; align-items: center; justify-content: center;
  border-radius: var(--radius-tile);
  background: rgba(var(--ink-rgb), 0.035);
  font-family: var(--font-board); font-size: var(--t-micro);
  font-weight: 600; color: var(--ink);
  transition: transform 140ms var(--ease), box-shadow 140ms var(--ease);
}
/* The theme's own ink, NOT the fixed chip ink a platform badge uses. A chip is
   a solid saturated swatch, so it needs an ink that ignores the theme; a day
   here is the panel and the amber mixed at an alpha that is usually low, which
   keeps it near the panel's own surface in both modes. That is exactly the
   ground --ink is for, and it is why the alpha ramp is capped — see
   spending_calendar() in app.py for the measurements. */
/* --ink-2, not the --ink-3 a caption would take. A quiet day is still a date
   somebody reads, and measured on the light panel --ink-3 came out at 4.0:1 —
   under the line, and the only cell in the grid that was. */
.ll-cal-day.is-quiet, .ll-cal-day.is-future {
  color: var(--ink-2); background: rgba(var(--ink-rgb), 0.035);
}
.ll-cal-day.is-future {
  background: transparent;
  box-shadow: inset 0 0 0 1px var(--rule);
  opacity: 0.55;
}
.ll-cal-day.is-today { box-shadow: inset 0 0 0 1.5px var(--ink); }
/* Only the days that turn over lift under the pointer. A future day is not
   clickable, and a cell that rises when you brush past it is promising
   something it cannot do. */
.ll-cal-day.is-live { cursor: pointer; }
.ll-cal-day.is-live:hover { transform: translateY(-2px); box-shadow: var(--lift-1); }
.ll-cal-day.is-live.is-today:hover {
  box-shadow: inset 0 0 0 1.5px var(--ink), var(--lift-1);
}
.ll-cal-foot {
  padding-top: var(--s3); font-size: var(--t-micro); color: var(--ink-3);
  line-height: 1.5;
}
.ll-cal-foot b { color: var(--ink-2); font-weight: 600; }
@media (prefers-reduced-motion: reduce) {
  .ll-cal-day { transition: none; }
  .ll-cal-day.is-live:hover { transform: none; }
}

/* ---- a day lifts out of the month --------------------------------------
   The first version of this turned the whole panel over like a page. It
   answered the question and lost where the answer came from — so now the
   square you pressed is the thing that moves: it rises off the grid, grows to
   cover the weeks, and only then turns onto its own figures. The month stays
   where it is behind it, and coming back is the same motion in reverse.

   Two stages, one per element, ordered with transition DELAYS rather than
   keyframes so that each direction can order itself. The outer .ll-day-card
   carries the lift (position, size, translateZ); the inner .ll-day-flip
   carries the turn. A transition takes its timing from the state it is moving
   TO, so the delays simply swap between the two rules — going out the card
   travels first and the turn waits 260ms, coming back the turn goes first and
   the shrink waits. Without that the card folds up while it is still moving,
   which is the seam this is built to avoid. */
.ll-day-card {
  position: absolute;
  left: 0; top: 0; width: 100%; height: 100%;
  transform-style: preserve-3d;
  pointer-events: none;
  transition: left 300ms var(--ease) 250ms,
              top 300ms var(--ease) 250ms,
              width 300ms var(--ease) 250ms,
              height 300ms var(--ease) 250ms,
              transform 300ms var(--ease) 250ms;
}
/* Day-units, all of them. Inside the square cell 100% is one day, so -col of
   them to the left is the first column, seven across is the whole week, and
   `rows` down is every week of the month. Nothing is measured, nothing breaks
   when the panel changes width, and the weekday header stays above the card
   with the week totals beside it — the month stays readable around the day
   that came out of it. */
.ll-vr:checked ~ .ll-day-card {
  left: calc(-1 * var(--col) * (100% + 4px));
  top: calc(-1 * var(--row) * (100% + 4px));
  width: calc(7 * (100% + 4px) - 4px);
  height: calc(var(--rows) * (100% + 4px) - 4px);
  transform: translateZ(48px);
  pointer-events: auto;
  transition: left 300ms var(--ease) 0ms,
              top 300ms var(--ease) 0ms,
              width 300ms var(--ease) 0ms,
              height 300ms var(--ease) 0ms,
              transform 300ms var(--ease) 0ms;
}
.ll-day-flip {
  position: absolute; inset: 0;
  transform-style: preserve-3d;
  transition: transform 300ms var(--ease) 0ms;
}
.ll-vr:checked ~ .ll-day-card .ll-day-flip {
  transform: rotateY(180deg);
  transition: transform 340ms var(--ease) 260ms;
}
.ll-day-face {
  position: absolute; inset: 0;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
}
/* The front face IS the square, and it takes over from the real one at the
   instant of the press: both swap on a 0s transition, so what you see is one
   square lifting rather than a copy peeling off a duplicate. Coming back, the
   swap waits 550ms for the card to land. The day's tint is written inline, so
   this face carries the same colour its square had. */
.ll-day-tile {
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--radius-tile);
  background: rgba(var(--ink-rgb), 0.035);
  font-family: var(--font-board); font-size: var(--t-micro);
  font-weight: 600; color: var(--ink);
  opacity: 0;
  transition: border-radius 300ms var(--ease) 250ms,
              font-size 300ms var(--ease) 250ms,
              box-shadow 300ms var(--ease) 250ms,
              opacity 0s linear 550ms;
}
.ll-vr:checked ~ .ll-day-card .ll-day-tile {
  opacity: 1;
  border-radius: var(--radius);
  font-size: 2rem;
  box-shadow: var(--lift-2);
  transition: border-radius 300ms var(--ease) 0ms,
              font-size 300ms var(--ease) 0ms,
              box-shadow 300ms var(--ease) 0ms,
              opacity 0s linear 0s;
}
.ll-cal-cell > .ll-cal-day {
  transition: transform 140ms var(--ease), box-shadow 140ms var(--ease),
              opacity 0s linear 550ms;
}
.ll-cal-cell:has(.ll-vr:checked) > .ll-cal-day {
  opacity: 0; transition: opacity 0s linear 0s;
}
/* Opaque, and it clips: the month is directly behind this face, and a
   translucent one would let the squares read straight through the figures. */
.ll-day-back {
  transform: rotateY(180deg);
  display: flex; flex-direction: column; gap: var(--s3);
  padding: var(--s4);
  border-radius: var(--radius);
  background: var(--panel-3);
  border: 1px solid var(--rule-2);
  box-shadow: var(--lift-3);
  overflow: hidden;
}
/* One day out at a time. An open card already covers every square in the grid,
   so this only states the rule rather than leaving the geometry to enforce it. */
.ll-cal:has(.ll-vr:checked) .ll-cal-day.is-live { pointer-events: none; }
/* The month recedes while a day is out of it. Only what is still visible needs
   it — the squares themselves are underneath the card. */
.ll-cal-dow, .ll-cal-sum { transition: opacity 240ms var(--ease); }
.ll-cal:has(.ll-vr:checked) .ll-cal-dow,
.ll-cal:has(.ll-vr:checked) .ll-cal-sum { opacity: 0.35; }
@media (prefers-reduced-motion: reduce) {
  .ll-day-card, .ll-day-flip, .ll-day-tile,
  .ll-cal-cell > .ll-cal-day { transition: none !important; }
}
.ll-day-head {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: var(--s3); padding-bottom: var(--s3);
  border-bottom: 1px solid var(--rule-2);
}
.ll-day-when { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.ll-day-when b {
  font-family: var(--font-board); font-size: var(--t-small); font-weight: 700;
  letter-spacing: 0.04em; color: var(--ink); white-space: nowrap;
}
.ll-day-when span { font-size: var(--t-micro); color: var(--ink-3); }
.ll-day-total {
  font-family: var(--font-board); font-size: var(--t-body); font-weight: 700;
  color: var(--amber); white-space: nowrap; line-height: 1.2;
}
.ll-day-total.is-none { color: var(--ink-3); opacity: 0.5; }
.ll-day-list { flex: 1 1 auto; min-height: 0; overflow-y: auto; }
/* Same five-cell rhythm as a Platform load row, so a category reads the same
   on the back of this card as it does in the panel beside it. */
.ll-day-row {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr) 46px auto auto;
  align-items: center; gap: var(--s3);
  padding: 7px 0; border-bottom: 1px solid var(--rule);
}
.ll-day-row:last-child { border-bottom: none; }
.ll-day-bar {
  height: 4px; border-radius: 99px; overflow: hidden;
  background: rgba(var(--ink-rgb), 0.09);
}
.ll-day-bar i { display: block; height: 100%; border-radius: 99px; }
.ll-day-none {
  flex: 1 1 auto; display: flex; align-items: center; justify-content: center;
  font-size: var(--t-small); color: var(--ink-3);
}
.ll-day-close {
  align-self: flex-start;
  display: inline-flex; align-items: center; gap: 7px;
  font-size: var(--t-micro); font-weight: 700; letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--ink-3);
  cursor: pointer; padding: 2px 0;
  transition: color 140ms var(--ease);
}
.ll-day-close:hover { color: var(--ink); }
@media (prefers-reduced-motion: reduce) {
  .ll-flip { transition: none; }
  .ll-day-close { transition: none; }
}
.ll-load-item {
  display: grid; grid-template-columns: 30px 1fr auto auto; align-items: center;
  gap: var(--s3); padding: 7px 0; border-bottom: 1px solid var(--rule);
}
.ll-load-row:last-child .ll-load-item { border-bottom: none; }
.ll-load-name { font-size: var(--t-small); color: var(--ink); font-weight: 500; }
.ll-load-pct { font-size: var(--t-micro); color: var(--ink-3); font-weight: 600; min-width: 32px; text-align: right; }
.ll-load-amt { font-size: var(--t-small); color: var(--ink-2); font-weight: 600; min-width: 68px; text-align: right; }

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
  /* Stacked, the list has the full width to itself and the cap would only
     strand the amounts mid-panel. */
  .ll-load-list { width: 100%; max-width: none; }
}

/* ---- obligations ---- */
/* Three cells: the two components and the figure they add up to. Net worth was
   computed in finance.py from the day the obligations panel shipped, but only
   the bot could see it — the two numbers it is made of sat side by side here
   and the total was nowhere on screen. */
.ll-oblig { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1px; background: var(--rule); }
@container board (max-width: 620px) {
  .ll-oblig { grid-template-columns: 1fr; }
}
/* The total is the point of the panel, so it reads in the board's own ink
   rather than the neutral the two components use. */
.ll-oblig-cell.is-total .ll-oblig-value { color: var(--amber); }
.ll-oblig-cell.is-total.is-neg .ll-oblig-value { color: var(--departure); }
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

/* ---- share / trend, switched without a round trip ----------------------
   One checkbox, the same pure-CSS idea as .ll-expand on the ledger columns: the
   browser swaps the view instantly, with no rerun, no reload and no scroll
   position lost. The input is the first child of .ll-panel so a general sibling
   combinator can reach both the head (to light the active segment) and the body
   (to swap the views).

   This was written with two radios first, because a lone checkbox re-clicked on
   the segment already showing would toggle back and fight the user. That does
   not work: a radio hidden with display:none is never activated by a click on
   its label — measured in Chromium, where flipping the very same element's type
   to checkbox and clicking the same label checked it. Association was fine
   either way (label.control resolved), so this is about how a radio group is
   activated, not about the markup.

   The segmented behaviour is recovered by making the ACTIVE label inert:
   pointer-events:none on the option you are already on, so clicking it does
   nothing, which is what a segmented control does. */
.ll-vr { display: none !important; }
.ll-panel-tools { display: flex; align-items: center; gap: var(--s3); }
/* One thumb that MOVES, not two backgrounds that swap.
   
   Cross-fading a fill on one label while fading it out on the other is the
   cheap version of this control, and it reads as two lamps rather than one
   switch: nothing travels, so nothing connects the state you left to the one
   you arrived at. A single pseudo-element sliding the width of one segment
   says "these are two positions of the same control" without a word.
   
   The thumb is sized off the track, not off the labels, which is why the
   labels are forced to equal widths: at `flex: 1 1 0` with a shared
   min-width, "Share" and "Trend" occupy exactly half each and a 50% thumb
   lands true whatever the two words are. The container's 2px padding is the
   track inset, so the thumb is `50% - 2px` wide and travels 100% of itself. */
.ll-seg {
  position: relative;
  display: inline-flex; gap: 0; padding: 2px;
  background: var(--shade-soft); border-radius: var(--radius-sm);
}
.ll-seg::before {
  content: ""; position: absolute; z-index: 0;
  top: 2px; bottom: 2px; left: 2px; width: calc(50% - 2px);
  background: var(--panel-3); box-shadow: var(--lift-1);
  border-radius: calc(var(--radius-sm) - 2px);
  transition: transform 240ms var(--ease);
}
#ll-view:checked ~ .ll-panel-head .ll-seg::before {
  transform: translateX(100%);
}
.ll-seg label {
  position: relative; z-index: 1;
  flex: 1 1 0; min-width: 52px; text-align: center;
  font-size: var(--t-micro); font-weight: 600; letter-spacing: 0.02em;
  padding: 4px 10px; border-radius: calc(var(--radius-sm) - 2px);
  color: var(--ink-3); cursor: pointer; user-select: none;
  transition: color 240ms var(--ease);
}
.ll-seg label:hover { color: var(--ink); }
/* The active label is inert: clicking the segment you are already on would
   toggle the checkbox and throw you to the other view. */
.ll-seg .seg-share,
#ll-view:checked ~ .ll-panel-head .ll-seg .seg-trend {
  color: var(--ink); pointer-events: none;
}
#ll-view:checked ~ .ll-panel-head .ll-seg .seg-share {
  color: var(--ink-3); pointer-events: auto;
}
@media (prefers-reduced-motion: reduce) {
  .ll-seg::before, .ll-seg label { transition: none; }
}
.ll-trend { display: none; }
#ll-view:checked ~ .ll-panel-body .ll-load { display: none; }
#ll-view:checked ~ .ll-panel-body .ll-trend { display: block; }

.ll-trend-row {
  display: grid; grid-template-columns: 30px minmax(0,1fr) auto auto auto;
  align-items: center; gap: var(--s3);
  padding: 8px 0; border-bottom: 1px solid var(--rule);
}
.ll-trend-row:last-child { border-bottom: none; }
.ll-trend-name {
  font-size: var(--t-small); color: var(--ink); font-weight: 500;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ll-spark { display: block; overflow: visible; }
.ll-trend-amt {
  font-family: var(--font-board); font-size: var(--t-small); font-weight: 600;
  color: var(--ink-2); white-space: nowrap;
}
/* Rising spend is the departure tone and falling spend is the arrival tone,
   which is the same reading the board's own "+15% vs August" note uses. This
   is status, not a third job for hue. */
.ll-trend-delta {
  font-size: var(--t-micro); font-weight: 700; letter-spacing: 0.04em;
  white-space: nowrap; min-width: 46px; text-align: right;
}
.ll-trend-delta.up { color: var(--departure); }
.ll-trend-delta.down { color: var(--arrival); }
.ll-trend-delta.flat, .ll-trend-delta.new { color: var(--ink-3); }
.ll-trend-foot {
  padding-top: var(--s3); font-size: var(--t-micro); color: var(--ink-3);
  line-height: 1.5;
}
@container board (max-width: 720px) {
  .ll-trend-row { grid-template-columns: 30px minmax(0,1fr) auto auto; }
  .ll-trend-row .ll-spark { display: none; }
}

/* ---- a panel that fills its column ------------------------------------
   Streamlit columns already stretch to the tallest of them; what does not
   stretch is the chain between the column and the panel, which is five divs of
   auto height. So the Platform load panel sat at its content height and left a
   dead band under it whenever the column beside it ran taller — which is any
   month with only two or three categories in it.

   Keyed off .ll-panel-fill rather than a positional selector, because a chain
   of :has(> div > div) anchored on nothing is exactly the kind of rule that
   silently stops matching on a Streamlit upgrade. One class, one anchor.

   The emotion wrapper in the middle centres its child, which would float the
   panel in the space instead of filling it; that one is put back to stretch. */
[data-testid="stElementContainer"]:has(.ll-panel-fill) {
  flex: 1 1 auto !important;
  min-height: 0 !important;
}
[data-testid="stElementContainer"]:has(.ll-panel-fill) [data-testid="stMarkdown"],
[data-testid="stElementContainer"]:has(.ll-panel-fill) [data-testid="stMarkdown"] > div,
[data-testid="stElementContainer"]:has(.ll-panel-fill) [data-testid="stMarkdownContainer"] {
  height: 100% !important;
  align-items: stretch !important;
}
.ll-panel-fill {
  height: 100%;
  display: flex;
  flex-direction: column;
}
/* The body takes the slack, so the ring and its list sit in the middle of the
   space rather than clinging to the header. */
.ll-panel-fill .ll-panel-body {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

/* ---- debts, rolled up per person ---------------------------------------
   Direction is carried by the word ("owes you" / "you owe") and by which edge
   is lit, never by tinting the card — the Two Jobs Rule holds here as much as
   on the board. The edge is the status hue doing its one job. */
.ll-people {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: var(--s2); margin-bottom: var(--s2);
}
.ll-person {
  background: var(--panel-2); border: 1px solid var(--rule-2);
  border-left: 2px solid var(--ink-3);
  border-radius: var(--radius); padding: 10px var(--s3);
}
.ll-person.is-in { border-left-color: var(--arrival); }
.ll-person.is-out { border-left-color: var(--departure); }
.ll-person.is-square { border-left-color: var(--ink-3); }
.ll-person-name {
  font-size: var(--t-small); font-weight: 600; color: var(--ink);
  display: flex; align-items: center; gap: 7px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ll-person-both {
  font-size: var(--t-micro); font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--amber);
  border: 1px solid var(--amber-24); border-radius: var(--radius-tile);
  padding: 1px 5px; flex: 0 0 auto;
}
.ll-person-net {
  font-family: var(--font-board); font-size: var(--t-h3); font-weight: 700;
  color: var(--ink); margin-top: 3px;
}
.ll-person-sub {
  font-size: var(--t-micro); color: var(--ink-3); margin-top: 2px;
}

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
  height: 8px; background: rgba(var(--ink-rgb),0.07); border-radius: var(--radius-tile);
  overflow: hidden; position: relative;
}
.ll-meter-fill { height: 100%; border-radius: var(--radius-tile); }
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
  border-radius: var(--radius-tile); overflow: hidden;
}
.ll-run-fill {
  min-height: 3px; border-radius: var(--radius-tile) var(--radius-tile) 0 0;
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
  display: inline-block; width: 18px; height: 9px; border-radius: var(--radius-tile);
  margin-right: 8px; vertical-align: middle; font-style: normal;
}
.ll-run-key .k-out { background: #5E6E84; }
.ll-run-key .k-now { background: #FFB300; }

/* ---- data tables inherit the board's rules, not Streamlit's default chrome */
[data-testid="stDataFrame"] thead th, [data-testid="stDataEditor"] thead th {
  background: var(--panel-2) !important;
  font-family: var(--font-ui) !important;
  font-size: var(--t-small) !important; font-weight: 600 !important;
  letter-spacing: normal !important; text-transform: none !important;
  color: var(--ink-2) !important;
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
     Given a length in BOTH states it animates like any other property.

     The width has to be a real layout change: the board beside it has to
     reflow into the room, and no transform can do that. What a transform CAN
     do is carry the panel's contents, and that is where the closing motion
     actually lives — see BOT_CLOSED_CSS at the foot of this file.

     Easing is per direction, not per element. Opening runs on the decelerating
     curve below; closing declares its own accelerating one in the closed-state
     sheet, because a transition takes its timing from the state it is moving
     TO. A panel that leaves on an ease-out darts off and then crawls the last
     few pixels; ease-in lets go of it instead.

     No will-change. It was set to max-width, which is a layout property the
     compositor cannot take over anyway, so the hint bought nothing and left
     both of the page's largest columns permanently promoted. */
  max-width: 100%;
  transition: max-width 300ms cubic-bezier(0.22, 0.61, 0.36, 1),
              flex-basis 300ms cubic-bezier(0.22, 0.61, 0.36, 1),
              width 300ms cubic-bezier(0.22, 0.61, 0.36, 1),
              opacity 220ms ease;
}
/* The rail's stack, in its resting place. It is the closed state that moves
   this (transform + opacity, nothing the layout has to think about); coming
   back it snaps home at 0s and lets llRailIn own the entrance, so the panel
   does not slide twice over itself on the way in. */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ll-stage-marker)
  > [data-testid="stColumn"]:last-child > [data-testid="stVerticalBlock"] {
  transform: none;
  opacity: 1;
  transition: transform 0s, opacity 140ms ease;
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
    padding: var(--s4) var(--s4) var(--s5) !important;
    overflow-y: auto !important;
    /* Open: sitting on its own edge, visible, and able to slide. The closed
       state moves it off with translateX rather than squeezing its width to
       zero — this is a fixed drawer, so there is no column to collapse and
       collapsing it anyway crushed the panel in place instead of sending it
       away. visibility rides along at 0s so it can be flipped at the END of
       the close (see the closed sheet) without fading the panel out early. */
    transform: none !important;
    visibility: visible !important;
    transition: transform 260ms cubic-bezier(0.22, 0.61, 0.36, 1),
                visibility 0s !important;
  }
  /* The prompts and composer sit at the foot of the panel rather than
     halfway up it: the rail is a fixed-height drawer here, so whatever the
     log does not use was 218px of dead panel measured under the composer.
     An auto top margin on the first prompt carries everything after it down
     with it, and the panel's own bottom padding keeps it off the edge.

     The desktop half of this is below: the same auto margin, but only once
     that rail has been given a bounded height to distribute. */
  .st-key-starter_0 { margin-top: auto !important; }
  /* A dimmed scrim so the board reads as backgrounded behind the panel — not
     interactive (no tap-to-close) since forwarding that tap into a Streamlit
     rerun needs the same click-bridge trickery as the board rows use, which
     isn't worth it when the panel's own close button already does the job. */
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ll-stage-marker)::before {
    content: ""; position: fixed; inset: 0;
    background: rgba(var(--void-rgb), 0.55);
    z-index: 999; pointer-events: none;
    /* It used to be switched off with display:none, which is not a thing that
       can be transitioned: the board behind the drawer went from dimmed to
       bright in one frame while the drawer was still on screen. Opacity can,
       and it is composited. */
    opacity: 1;
    transition: opacity 260ms cubic-bezier(0.22, 0.61, 0.36, 1);
  }
}
/* The close button's column is sized for the control, not the other way
   round — without this it keeps the column's full width and the icon drifts
   left of the panel edge. Its skin is declared at the end of this sheet, for
   the same source-order reason as .st-key-clear_chat. */
.st-key-close_rail { display: flex !important; justify-content: flex-end !important; }
/* Heading and close button are a pair, not a stack. Streamlit's own column
   stacking breaks them onto two rows once the rail is phone-width, which put
   the × on its own line under the title — the exact layout this row exists
   to avoid. Held on one line, with the button column sized to the control.

   The full child chain is deliberate. A plain :has(.st-key-close_rail) also
   matches the outer stage/rail row, because that row contains this one — it
   was measured matching two blocks, and the column rules below would then
   have resized the rail column itself. Spelling out
   > stColumn > stVerticalBlock > the keyed element pins it to this row
   alone. Same reasoning for the switcher row and the log wrapper below. */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > .st-key-close_rail) {
  flex-wrap: nowrap !important;
  gap: var(--s2) !important;
}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > .st-key-close_rail) > [data-testid="stColumn"] {
  min-width: 0 !important;
}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > .st-key-close_rail) > [data-testid="stColumn"]:last-child {
  flex: 0 0 auto !important;
  width: auto !important;
}
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
/* The board naming what it has not been told. Same idiom as .ll-since, in the
   departure tone rather than amber, because this is not news — it is a figure
   on screen being reported as more certain than it is. */
.ll-setup {
  border: 1px solid var(--rule-2); border-left: 2px solid var(--departure);
  border-radius: var(--radius); background: var(--shade-soft);
  padding: var(--s3) var(--s4); margin-bottom: var(--s2);
}
.ll-setup .ll-since-title .ll-icon { color: var(--departure); }
.ll-setup-item {
  font-size: var(--t-small); color: var(--ink-2); line-height: 1.55;
  padding: 4px 0;
}
.ll-setup-item + .ll-setup-item { border-top: 1px solid var(--rule); margin-top: 4px; }
.ll-setup-item b { color: var(--ink); font-weight: 600; }
.st-key-setup_open, .st-key-setup_hide { margin-bottom: var(--s3); }

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
  padding: 1px 5px; border-radius: var(--radius-sm); font-size: 0.92em;
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
  box-shadow: var(--lift-1) !important;
  transition: background 140ms var(--ease), border-color 140ms var(--ease),
              color 140ms var(--ease), box-shadow 140ms var(--ease),
              transform 90ms var(--ease) !important;
}
.stButton button:hover, .stFormSubmitButton button:hover,
[data-testid="stDownloadButton"] button:hover,
[data-testid="stPopover"] > div > button:hover {
  background: var(--panel-3) !important;
  border-color: var(--amber) !important;
  color: var(--amber) !important;
  box-shadow: var(--lift-2) !important;
  transform: translateY(-2px) !important;
}
/* Up on approach, down on press. The pair is what makes a button feel like an
   object rather than a picture of one, and it is the same two pixels the cards
   move — a control and a card should not disagree about how far "raised" is.
   :active is written after :hover deliberately: it matches while hovering too,
   and equal specificity means source order is what settles the press. */
.stButton button:active, .stFormSubmitButton button:active,
[data-testid="stDownloadButton"] button:active,
[data-testid="stPopover"] > div > button:active {
  transform: translateY(1px) !important;
  box-shadow: none !important;
}
@media (prefers-reduced-motion: reduce) {
  .stButton button:hover, .stFormSubmitButton button:hover,
  [data-testid="stDownloadButton"] button:hover,
  [data-testid="stPopover"] > div > button:hover,
  .stButton button:active, .stFormSubmitButton button:active,
  [data-testid="stDownloadButton"] button:active,
  [data-testid="stPopover"] > div > button:active {
    transform: none !important;
  }
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
  font-family: var(--font-ui) !important;
  font-size: var(--t-small) !important; font-weight: 600 !important;
  letter-spacing: normal !important; text-transform: none !important;
  color: var(--ink-2) !important; margin-bottom: 5px !important;
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
/* One border, not two.
   The two rules above draw a border on the <input> itself, and the shell rule
   between them draws another on the wrapper Streamlit puts around it — so
   every text, number and date field was painting two rings 1px apart. Then the
   shell's own overflow:hidden clipped the inner ring's bottom edge off, which
   is the "one uncoloured edge" the search box shows: measured on it, the
   shell's content box is 351x38 and the input sitting in it is 351x39, so
   three sides carried a doubled line and the fourth carried none.

   The shell keeps the border — it is what the radius and the hover state are
   already hung on, and it is the box the eye reads as the field. The input
   inside goes borderless and transparent, and focus moves up to the shell with
   it, or the amber ring would have nothing left to draw on. :focus-within,
   not :focus, because the thing taking focus is the input and the thing
   wearing the border is now its parent. */
[data-testid="stTextInputRootElement"] > input,
[data-testid="stNumberInputContainer"] input,
[data-testid="stDateInputField"] input {
  border: none !important;
  background: transparent !important;
  border-radius: 0 !important;
}
[data-testid="stTextInputRootElement"]:focus-within,
[data-testid="stNumberInputContainer"]:focus-within,
[data-testid="stDateInputField"]:focus-within {
  border-color: var(--amber) !important;
}
[data-testid="stTextInputRootElement"]:hover,
[data-testid="stNumberInputContainer"]:hover { border-color: var(--amber) !important; }
[data-baseweb="select"] svg { color: var(--ink-3) !important; }
[data-baseweb="popover"] [role="listbox"], [data-baseweb="menu"] {
  background: var(--panel-2) !important; border: 1px solid var(--rule-2) !important;
}
[data-baseweb="menu"] li:hover { background: var(--panel-3) !important; }
[data-testid="stNumberInput"] button { background: var(--panel-3) !important; border-color: var(--rule-2) !important; }
[data-testid="stForm"] { border: none !important; padding: 0 !important; }
/* Streamlit's "Press Enter to submit form" hint. It is positioned absolutely
   inside the field it belongs to, so it prints straight over the placeholder
   rather than sitting under the input — and it appears on every text and
   number field in the sidebar at once. Every form here already carries a
   labelled submit button ("Add departure"), so the hint states something the
   button says better, and removing it is the same call as toolbarMode
   "viewer" in config.toml: this is a finished product being used, not a
   scaffold being demonstrated. */
[data-testid="InputInstructions"] { display: none !important; }
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
  font-family: var(--font-ui) !important; font-weight: 600 !important;
  letter-spacing: normal !important; text-transform: none !important;
  font-size: var(--t-small) !important; color: var(--ink-2) !important;
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
  border-radius: var(--radius-sm) !important; font-size: 0.92em !important;
}
/* A table wider than the rail must scroll inside its own message, not push
   the chat column sideways. */
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] { overflow-x: auto !important; }

/* Tabs are addressed by data-testid and ARIA role, NOT by data-baseweb.
   Streamlit moved this widget off BaseWeb onto react-aria, and the four
   [data-baseweb="tab*"] rules that used to live here matched nothing at all
   afterwards — measured, not guessed: with the ledgers expander open and four
   tabs on screen, every one of those selectors returned zero elements while
   [data-testid="stTab"] returned four. Nothing announced the change, because
   dead CSS fails silently; the tabs had simply been rendering in Streamlit's
   own Source Sans at its own size, and the selected tab was the same ink as
   the others. The amber selection bar was all that still worked, and only
   because react-aria draws it from primaryColor in config.toml.

   The label lives in a nested markdown container, so the type rules go on the
   <p> and only the box rules go on the tab. */
[data-testid="stTabs"] [role="tablist"] {
  gap: 2px !important; background: transparent !important;
  border-bottom: 1px solid var(--rule) !important;
}
[data-testid="stTabs"] [data-testid="stTab"] {
  background: transparent !important; padding: 9px 15px !important;
}
[data-testid="stTabs"] [data-testid="stTab"] p {
  font-family: var(--font-ui) !important; font-size: var(--t-small) !important;
  font-weight: 600 !important; letter-spacing: normal !important;
  text-transform: none !important; color: var(--ink-2) !important;
}
[data-testid="stTabs"] [data-testid="stTab"]:hover p { color: var(--ink) !important; }
[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] p {
  color: var(--amber) !important;
}
[data-testid="stTabs"] .react-aria-SelectionIndicator {
  background: var(--amber) !important;
}

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
  font-family: var(--font-ui) !important; font-size: var(--t-small) !important;
  font-weight: 600 !important; letter-spacing: normal !important;
  text-transform: none !important; color: var(--ink-2) !important;
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
  box-shadow: var(--lift-2) !important;
}
[data-testid="stTooltipContent"] {
  background: var(--panel-3) !important;
  border: 1px solid var(--rule-2) !important;
  color: var(--ink) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--lift-2) !important;
}
[data-testid="stTooltipContent"] * { color: var(--ink) !important; }
/* A tooltip should describe what you are pointing at, not what you last
   pressed. Streamlit shows it on focus as well as hover, and a mouse click
   leaves the button focused — so every icon button kept its label floating
   over the board after it had been used, describing an action already taken.
   
   The condition is "nothing is being hovered AND nothing has keyboard focus".
   :focus-visible is the load-bearing half: a mouse click sets :focus but not
   :focus-visible, while Tab sets both — so this drops the tooltip after a click
   and keeps it for anyone driving the board from the keyboard, who has no
   other way to know what an unlabelled icon does. Verified both ways. */
body:not(:has([data-testid="stTooltipHoverTarget"]:hover)):not(:has(:focus-visible))
  [data-testid="stTooltipContent"] { display: none !important; }

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
  box-shadow: var(--lift-1) !important;
  transition: border-color 140ms ease, box-shadow 140ms ease;
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
/* An empty composer must be one row tall, and the thing that kept inflating it
   is the placeholder.
   
   The textarea's row sizes to the textarea's content height, and for an empty
   field the content IS the placeholder — so as soon as "Message the bot" wraps,
   the empty box grows to two or three rows. It wrapped for two reasons, and
   both had to go:
   
     - a genuinely narrow rail, where 106px of field cannot hold the phrase;
     - the font swap, which is why the same window width gave 42px on one load
       and 97px on the next. Barlow loads with font-display:swap, so the first
       layout is measured in the wider fallback face; the placeholder wraps,
       the row takes that height, and when Barlow arrives nothing re-measures.
       Typing a character and deleting it snapped the box back to one row,
       which is what gave the race away.
   
   Stopping the placeholder from wrapping fixes both at once, and touches only
   the empty state: typed text still wraps and still auto-grows to the 7.5em
   cap. Verified 640px-1600px, empty and with four lines in it.
   
   Note what does NOT work here: out-specifying the row's flex. Streamlit ships
   its own `> div > div > div:first-child:has(> [data-testid="stChatInputTextArea"])
   { flex: 1 1 auto }`, which beats any plainer version of that chain — and it
   is right to, because the row growing with content is the behaviour we want.
   The bug was never the flex; it was what the row was measuring. */
[data-testid="stChatInputTextArea"]::placeholder {
  white-space: nowrap !important;
  text-overflow: ellipsis !important;
  overflow: hidden !important;
}
[data-testid="stChatInput"] textarea { max-height: 7.5em !important; }
[data-testid="stChatInput"] textarea::placeholder { color: var(--ink-3) !important; opacity: 1 !important; }
[data-testid="stChatInput"] button { background: var(--amber) !important; border-radius: var(--radius-sm) !important; }
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

/* ---- the desktop rail is a panel, not a column ----
   Left to itself it is a flex item stretched to the tallest thing in the row,
   which is the board: 1444px of column against a 900px viewport, with the
   composer ending at 751px and roughly 700px of empty panel beneath it. That
   dead run is the gap under the composer, and no auto margin can close it
   while the box being distributed is itself taller than the screen.

   Bounding it to the viewport turns it into what it already reads as — a
   panel beside the board — and gives the auto margin a box worth
   distributing, so the composer sits at its foot exactly as it does in the
   mobile drawer. Sticky rather than fixed so it holds position while the
   board scrolls without leaving the row's layout, and align-self stops the
   flex row stretching it back to the board's full height. */
@media (min-width: 681px) {
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ll-stage-marker)
    > [data-testid="stColumn"]:last-child {
    position: sticky !important;
    top: var(--s4) !important;
    align-self: flex-start !important;
    height: calc(100vh - var(--s7)) !important;
    overflow-y: auto !important;
    padding-bottom: var(--s5) !important;
  }
  /* The stack has to fill the panel before anything in it can be pushed to
     the foot of it. */
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ll-stage-marker)
    > [data-testid="stColumn"]:last-child > [data-testid="stVerticalBlock"] {
    min-height: 100% !important;
  }
  .st-key-starter_0 { margin-top: auto !important; }
}

/* The rail's close control. Chrome, not content — the same treatment the
   sidebar's collapse arrow gets: no fill or border at rest so it reads as a
   dismiss affordance rather than an action, full contrast on hover. Declared
   here, last and with a heavier selector than the generic button skin, for
   exactly the reason given above clear_chat: that skin is !important too and
   ties on specificity, so source order would otherwise hand it the win — and
   it is what was keeping this button at a chunky 36px filled panel box. */
div.st-key-close_rail button {
  width: 26px !important; height: 26px !important;
  min-height: 26px !important; padding: 0 !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  color: var(--ink-3) !important;
  border-radius: var(--radius) !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
}
div.st-key-close_rail button:hover {
  background: var(--panel-2) !important;
  border-color: var(--rule-2) !important;
  color: var(--amber) !important;
}
div.st-key-close_rail button * { color: inherit !important; }
div.st-key-close_rail button span[class*="material"] { font-size: 17px !important; }

/* ---- attachments must stay inside the composer ----
   Streamlit already sets flex-wrap:wrap on the chip tray, but wrapping never
   engaged: a flex item's default min-width is auto, so the tray was free to
   size itself to its contents (461px measured) inside a 275px composer and
   simply overhang it. Three pasted images were enough to see it. Letting the
   tray and its two flex ancestors shrink below their content width is what
   makes the existing wrap rule do its job. */
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] > div > div {
  min-width: 0 !important;
  max-width: 100% !important;
}
[data-testid="stChatInput"] [data-testid="stFileChips"] {
  flex-wrap: wrap !important;
  min-width: 0 !important;
  max-width: 100% !important;
  row-gap: 4px !important;
  /* Wrapping alone only moves the problem from sideways to downwards: enough
     attachments and the tray pushes the composer off screen again. Capped and
     scrolled, the composer costs the same height whether it is carrying one
     image or ten. */
  max-height: 96px !important;
  overflow-y: auto !important;
}
/* Two chips to a row, then wrap. The tray is 275px wide and each chip sizes
   itself to a fixed 148px, so two of them plus the 8px column gap came to
   304px and only one ever fit per line. Halving them fits the pair the tray
   was always wide enough for.

   The chips are grandchildren, not children: Streamlit wraps them in a
   display:contents element, which is why an earlier rule aimed at
   `stFileChips > *` did nothing at all — it was styling a box that generates
   no box. The 4px is half the column gap. */
[data-testid="stChatInput"] [data-testid="stFileChips"] > *,
[data-testid="stChatInput"] [data-testid="stFileChips"] > * > * {
  min-width: 0 !important;
}
[data-testid="stChatInput"] [data-testid="stFileChips"] > * > * {
  flex: 0 0 calc(50% - 4px) !important;
  max-width: calc(50% - 4px) !important;
}
/* The chip inside that slot carries its own intrinsic width (144px measured)
   and simply overhung it. Clipping the slot hid the overflow but took the
   chip's remove button with it, which is the one control on a chip that has
   to stay reachable — so the chip is made to fit instead, and its contents
   are allowed to shrink so the filename gives way rather than the ×. */
[data-testid="stChatInput"] [data-testid="stFileChip"] {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
}
[data-testid="stChatInput"] [data-testid="stFileChip"] > * { min-width: 0 !important; }

/* The caret starts where the field starts, and the field starts next to the
   attach button. Measured: a 299px row carrying 206px of controls was
   dealing its 93px of slack out *between* the three of them — ~46px either
   side of the text field — so typing began a third of the way across the
   composer with dead space to its left. Giving the field the slack instead
   puts the caret back beside the + and lets it grow with the panel.

   Two things had to change together. The row is justify-content:
   space-between, which is what deals the slack outward in the first place;
   and the field's own wrapper is pinned to flex:0 0 auto by the composer
   height rule further up, whose selector outscores a plain descendant one —
   so the :first-child chain is repeated here, plus :has(), to land above it
   rather than merely after it. */
[data-testid="stChatInput"] > div > div:has(> div > [data-testid="stChatInputTextArea"]) {
  justify-content: flex-start !important;
}
[data-testid="stChatInput"] > div > div > div:first-child:has(> [data-testid="stChatInputTextArea"]) {
  flex: 1 1 auto !important;
  min-width: 0 !important;
}
[data-testid="stChatInput"] [data-testid="stChatInputTextArea"] {
  width: 100% !important;
}
/* Send holds the right edge in both states. Once the typed text is long
   enough the row wraps and the two buttons drop to a line of their own —
   with the row now packed to flex-start they both sat at the left, which
   space-between used to prevent as a side effect. An auto left margin does
   it deliberately instead, and costs nothing on the single-line layout where
   the field has already taken the slack. */
[data-testid="stChatInput"] > div > div > div:has(> [data-testid="stChatInputSubmitButton"]) {
  margin-left: auto !important;
}

/* ---- the log takes the room, the composer keeps its place ----
   The composer must stay on screen: it is not inside a scroll box, so being
   pushed past the fold makes the panel look broken. The prompts and composer
   are held at the foot of the rail by `margin-top: auto` on .st-key-starter_0
   (twice, once per breakpoint) — and that is what used to eat the slack. An
   auto margin absorbs free space, so with the log capped at a fixed 300px a
   tall window put ~300px of dead panel BETWEEN the last reply and the first
   prompt: a gap you could see, inside a box you could not fill.

   Letting the log take that space instead fixes it without moving anything.
   Flex resolves flexible lengths BEFORE it distributes free space to auto
   margins, so a growing log leaves the margin nothing to take and everything
   below stays exactly where it was. Shrinking works the same way in reverse:
   on a short window the log gives room back rather than pushing the composer
   down.

   Three declarations, and all three are load-bearing:
     flex: 1 1 auto   grow into the slack, shrink when there is none. The
                      basis stays `auto` rather than 0 so the box is still
                      content-sized if it ever lands in an unbounded parent,
                      where a 0 basis would collapse it to nothing.
     height: auto     st.container(height=) writes a pixel height here; left
                      alone it pins the basis and nothing flexes.
     min-height       a floor, so a very short viewport scrolls the rail —
                      which its own overflow-y already handles — rather than
                      squeezing the log out of existence. */
/* The keyed element IS the log's own stVerticalBlock, so it is the only
   thing that may carry this. An earlier version also listed
   `.st-key-bot_log [data-testid="stVerticalBlock"]`, which matched every
   block *inside* the log — every individual chat message — and handed each
   one its own clamp and scrollbar: a stack of nested scroll tracks with the
   replies clipped and printing over each other. */
div.st-key-bot_log {
  height: 100% !important;
  max-height: none !important;
  min-height: 0 !important;
  /* Paired with the fill, never without it: a box that grows past its
     content is fine, but one whose content outgrows IT has to scroll or the
     replies print over whatever comes next. */
  overflow-y: auto !important;
}
/* st.container(height=) puts the pixel height on a wrapper *around* the
   keyed element, so sizing the keyed element alone left the wrapper at its
   full height and the change never reached the layout. Direct child only —
   an unscoped :has() also matches the rail's outer wrapper. */
[data-testid="stLayoutWrapper"]:has(> .st-key-bot_log) {
  flex: 1 1 auto !important;
  height: auto !important;
  max-height: none !important;
  min-height: 140px !important;
}

/* The chat switcher is three small controls that Streamlit's own column
   stacking breaks onto three rows once the rail is phone-width — 150px of
   height for one selectbox and two icon buttons. They fit side by side at
   any width this panel actually reaches, provided the columns are allowed
   to shrink below their content. */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > .st-key-chat_new) {
  flex-wrap: nowrap !important;
  gap: var(--s2) !important;
}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > .st-key-chat_new) > [data-testid="stColumn"] {
  min-width: 0 !important;
  flex: 1 1 0 !important;
}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > .st-key-chat_new) > [data-testid="stColumn"]:nth-child(2),
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > .st-key-chat_new) > [data-testid="stColumn"]:nth-child(3) {
  flex: 0 0 auto !important;
  width: auto !important;
}

/* The prompts are a menu, not the main event. Trimmed so the four buttons
   under the log cost roughly one button's worth of height less between them
   — which is what buys the composer its place on a short screen. */
div.st-key-starter_0 button,
div.st-key-starter_1 button,
div.st-key-explain_period button,
div.st-key-clear_chat button {
  min-height: 30px !important;
  height: auto !important;
  padding: 5px 10px !important;
  font-size: var(--t-micro) !important;
  line-height: 1.3 !important;
  letter-spacing: 0.02em !important;
}

/* ---- Streamlit's own dialogs, including the connection error ----
   Not one of ours and never themed: the card paints itself near-white from
   Streamlit's own palette while the text inside inherits config.toml's
   static textColor (#E9EDF2), so "Connection error" and its body came out
   near-white on cream — legible only if you already knew what it said. Same
   class of bug as the expander header and the file-uploader button noted
   above: one Streamlit surface filling from two palettes at once.

   Targeted through BaseWeb's own modal attribute rather than an emotion
   class hash, which changes on every Streamlit build. The popover and menu
   rules further up deliberately are not touched — this is scoped to modals
   so those keep their own panel-2 surface. */
[data-baseweb="modal"] [role="dialog"],
[data-testid="stDialog"] [role="dialog"] {
  background: var(--panel) !important;
  border: 1px solid var(--rule-2) !important;
  border-radius: var(--radius-lg) !important;
  box-shadow: var(--lift-3) !important;
  color: var(--ink) !important;
}
[data-baseweb="modal"] [role="dialog"] *,
[data-testid="stDialog"] [role="dialog"] * {
  color: var(--ink) !important;
}
/* The dialog's code block is the one thing in it that should read as a
   terminal line, so it keeps the void ground and amber ink used elsewhere. */
[data-baseweb="modal"] [role="dialog"] code,
[data-baseweb="modal"] [role="dialog"] pre,
[data-testid="stDialog"] [role="dialog"] code,
[data-testid="stDialog"] [role="dialog"] pre {
  background: var(--void) !important;
  color: var(--amber) !important;
  border: 1px solid var(--rule) !important;
  border-radius: var(--radius-sm) !important;
}
[data-baseweb="modal"] [role="dialog"] code *,
[data-testid="stDialog"] [role="dialog"] code * { color: var(--amber) !important; }

/* ================================================ data grids follow the mode */
/* st.dataframe and st.data_editor render through glide-data-grid, which paints
   every cell from its own --gdg-* custom properties and reads nothing else in
   this stylesheet. Streamlit fills those from config.toml's [theme] block,
   which is pinned dark so the first paint never flashes light — so the ledger
   and debt tables stayed black slabs on light mode's cream however the tokens
   were set. Re-pointing them at the same tokens the rest of the board reads
   makes the grid follow the mode from one rule, rather than needing a second
   palette kept in sync by hand. */
.stDataFrameGlideDataEditor {
  --gdg-bg-cell: var(--panel) !important;
  --gdg-bg-cell-medium: var(--panel-2) !important;
  --gdg-bg-header: var(--panel-2) !important;
  --gdg-bg-header-hovered: var(--panel-3) !important;
  --gdg-bg-header-has-focus: var(--panel-3) !important;
  --gdg-bg-group-header: var(--panel-2) !important;
  --gdg-bg-group-header-hovered: var(--panel-3) !important;
  --gdg-text-dark: var(--ink) !important;
  --gdg-text-medium: var(--ink-2) !important;
  --gdg-text-light: var(--ink-3) !important;
  --gdg-text-header: var(--ink-2) !important;
  --gdg-text-group-header: var(--ink-2) !important;
  --gdg-text-header-selected: var(--ink) !important;
  --gdg-text-bubble: var(--ink-2) !important;
  --gdg-bg-bubble: var(--panel-2) !important;
  --gdg-bg-bubble-selected: var(--panel-3) !important;
  --gdg-border-color: var(--rule-2) !important;
  --gdg-horizontal-border-color: var(--rule) !important;
  --gdg-drilldown-border: var(--rule-2) !important;
  --gdg-accent-color: var(--amber) !important;
  --gdg-accent-light: var(--amber-12) !important;
  /* Ink ON the accent fill, not beside it. --void is the mode's own background:
     dark beneath dark mode's bright amber, pale beneath light mode's brown one,
     so a single token gives the right contrast in both directions. */
  --gdg-accent-fg: var(--void) !important;
  --gdg-bg-search-result: var(--amber-24) !important;
  --gdg-bg-icon-header: var(--ink-3) !important;
  --gdg-fg-icon-header: var(--panel) !important;
  --gdg-link-color: var(--amber) !important;
  --gdg-resize-indicator-color: var(--amber) !important;
  --gdg-font-family: var(--font-ui) !important;
}
/* The grid's own frame, which is DOM rather than canvas and so kept the
   static config background behind the painted cells. */
[data-testid="stDataFrame"] > div,
[data-testid="stDataFrameResizable"] {
  background: var(--panel) !important;
  border-color: var(--rule-2) !important;
}

/* ============================================ the open dropdown, both modes */
/* A closed selectbox was already themed. The OPEN list is a different element
   in a different place: this build portals it to <body> as
   stSelectboxVirtualDropdown, so it is outside every container selector above,
   and it carries neither [data-baseweb="menu"] nor a [role="listbox"] wrapper
   that the older rules were written against. Nothing matched it, so it fell
   back to config.toml's pinned #07090C and hung as a black card off a cream
   page. Tokens are declared on :root, so a portalled element still inherits
   them — only the selector was missing. */
[data-testid="stSelectboxVirtualDropdown"],
[data-testid="stSelectboxVirtualDropdown"] > div,
[data-testid="stSelectboxVirtualDropdown"] [role="listbox"] {
  background: var(--panel-2) !important;
  border-color: var(--rule-2) !important;
  color: var(--ink) !important;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"] {
  background: transparent !important;
  color: var(--ink) !important;
  font-family: var(--font-ui) !important;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover,
[data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"] {
  background: var(--panel-3) !important;
  color: var(--ink) !important;
}

/* ==================================================== settings dialog rhythm */
/* Every section in Settings is a heading, a caption and a control, and the
   default vertical block gap treated all three as peers — so a label sat as
   far from the thing it named as from the next section entirely, and the
   dialog scrolled far longer than it had content for. Tightening the gap and
   the rules pulls each group together and lets the dividers do the separating
   they were already there to do. */
[data-testid="stDialog"] [data-testid="stVerticalBlock"] {
  gap: var(--s2) !important;
}
[data-testid="stDialog"] hr {
  margin-top: var(--s3) !important;
  margin-bottom: var(--s3) !important;
}
/* Deliberately NOT zeroing the paragraph margins inside these blocks. Doing
   that collapsed each caption's element container to a single line's height
   while the caption itself still wrapped to two — the container does not clip,
   so the overflow printed straight over the widget underneath. The gap above
   is the whole adjustment; the text keeps the box it needs. */

/* ================================================ a composer that starts small */
/* The field opened at the height of the buttons flanking it rather than the
   height of one line of text, which is a lot of empty box to look at before
   anything has been typed. The textarea already grows with its own content —
   Streamlit drives that from scrollHeight — so the fix is only to stop the
   row around it setting a floor: trim the shell's padding, shrink the two
   controls to the line they sit on, and let the cap in the rule further up
   decide when it starts scrolling instead. */
/* Two wrappers deep, and the height came from the OUTER one: it carries 12px
   top and bottom, which is 24px of the 58 an empty composer used to occupy
   before a single character had been typed. The inner row only holds the two
   26px controls. */
[data-testid="stChatInput"] > div {
  padding-top: 5px !important;
  padding-bottom: 5px !important;
}
[data-testid="stChatInput"] > div > div {
  padding-top: 2px !important;
  padding-bottom: 2px !important;
  align-items: flex-end !important;
}
[data-testid="stChatInput"] textarea {
  min-height: 21px !important;
  padding-top: 2px !important;
  padding-bottom: 2px !important;
}
[data-testid="stChatInput"] button {
  width: 26px !important; height: 26px !important;
  min-width: 26px !important; min-height: 26px !important;
  padding: 0 !important;
}
[data-testid="stChatInput"] button svg { width: 15px !important; height: 15px !important; }

/* ============================================== the two chrome controls */
/* Icon-only, so the button should be the size of its glyph rather than the
   width of a column that no longer has a label to hold. margin-left:auto pins
   each to the right edge of its own slot, which keeps the pair tight against
   the board's right margin at any container width instead of drifting apart as
   the column grows. */
/* The pair sits on its side and hard right, tight to each other. As two
   separate columns the space between them was the row's gap plus each
   column's leftover width — 30px, which read as two unrelated buttons
   rather than one control cluster. */
.st-key-ll_toolbar {
  flex-direction: row !important;
  justify-content: flex-end !important;
  align-items: center !important;
  gap: var(--s2) !important;
}
.st-key-ll_toolbar [data-testid="stElementContainer"] {
  width: auto !important;
  flex: 0 0 auto !important;
}
/* Square, and the same height as the search field beside them so the row
   reads as one line rather than three things that happen to be near each
   other. */
.st-key-toggle_theme button,
.st-key-toggle_bot button,
.st-key-open_settings button {
  width: 39px !important;
  min-width: 39px !important;
  height: 39px !important;
  min-height: 39px !important;
  padding: 0 !important;
}
.st-key-toggle_theme button > div,
.st-key-toggle_bot button > div,
.st-key-open_settings button > div { gap: 0 !important; }
/* The row these sit in used to carry two labelled buttons and was spaced like
   a section of its own. As a pair of marks in the corner it is chrome, so the
   band above and below it closes up and the board starts higher — which is the
   whole point of moving them out of the top-left. Selector spelled out to the
   exact child chain: a looser :has() also matches the outer stage/rail row,
   which would drag the entire board up by the same amount. */
/* No margin override on the row itself. It needed one when it held two
   floating buttons and nothing else — the band read as empty page and had to
   be pulled shut. Now that the search box shares the line it is a real row and
   Streamlit's own rhythm already lands it evenly: measured 16px above and 17px
   below. A rule was written for it and deleted rather than left in, because
   the chain it guessed (column > block > container) omits the stLayoutWrapper
   Streamlit puts in between, so it matched nothing — and the obvious loose
   rewrite matches two rows, the second being the outer stage/rail, which would
   have moved the whole board instead. */
"""


# Injected only while the bot is shut. Everything it does is reversible by
# simply not emitting it, which is what lets the transition in _CSS_BODY run in
# both directions: closing adds these widths, opening removes them, and the
# same elements animate between the two.
#
# A transition reads its timing from the state it is moving TO, so declaring
# the timing here — and only here — is what gives closing a curve of its own
# without touching opening. It accelerates: the panel is let go of rather than
# flung, which is what the old shared ease-out made it look like.
_ROW = ('[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] '
        '.ll-stage-marker)')
# ease-in. Opening decelerates into place; closing gathers speed as it leaves.
_SHUT = "cubic-bezier(0.4, 0, 1, 1)"
BOT_CLOSED_CSS = f"""
{_ROW} {{ gap: 0 !important; }}
{_ROW} > [data-testid="stColumn"]:first-child {{
  flex: 1 1 100% !important; width: 100% !important;
  max-width: 100% !important; min-width: 0 !important;
}}
{_ROW} > [data-testid="stColumn"]:last-child {{
  flex: 0 0 0 !important; width: 0 !important;
  min-width: 0 !important; max-width: 0 !important;
  overflow: hidden !important;
  pointer-events: none !important;
  transition: max-width 280ms {_SHUT}, flex-basis 280ms {_SHUT},
              width 280ms {_SHUT} !important;
}}
/* The part the compositor can actually carry. The stack inside the column
   leaves on transform and opacity — no layout, no paint of its own — and it
   leaves FIRST, so the panel is already gone by the time the edge finishes
   closing behind it rather than being squeezed flat on the way out. */
{_ROW} > [data-testid="stColumn"]:last-child > [data-testid="stVerticalBlock"] {{
  transform: translateX(20px) !important;
  opacity: 0 !important;
  transition: transform 200ms {_SHUT}, opacity 150ms {_SHUT} !important;
}}
/* On a phone there is no column to collapse — the rail is a fixed drawer — so
   it keeps its width and slides off its own edge instead. Pure transform, and
   the scrim fades with it. visibility flips only once the slide is over, which
   is what the 0s-with-a-delay is for: it keeps the drawer hit-testable and
   painted for the whole 260ms and then takes it out of the tree. */
@media (max-width: 680px) {{
  {_ROW} > [data-testid="stColumn"]:last-child {{
    flex: 0 0 auto !important;
    width: min(88vw, 380px) !important;
    max-width: min(88vw, 380px) !important;
    overflow: hidden !important;
    transform: translateX(100%) !important;
    visibility: hidden !important;
    transition: transform 260ms {_SHUT},
                visibility 0s linear 260ms !important;
  }}
  {_ROW} > [data-testid="stColumn"]:last-child > [data-testid="stVerticalBlock"] {{
    transform: none !important; opacity: 1 !important;
    transition: none !important;
  }}
  {_ROW}::before {{ opacity: 0 !important; }}
}}
@media (prefers-reduced-motion: reduce) {{
  {_ROW} > [data-testid="stColumn"]:last-child,
  {_ROW} > [data-testid="stColumn"]:last-child > [data-testid="stVerticalBlock"],
  {_ROW}::before {{ transition: none !important; }}
}}
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
/* On mobile the panel is a fixed overlay whose entire subtree — chat log,
   composer, the click-bridge iframe — mounts for the first time on this same
   run. The slide keyframe is compositor-only in isolation, but competing with
   all of that mounting on a phone's single main thread is what read as lag;
   dropping it here trades the drift-in for an instant, un-janky appearance. */
@media (max-width: 680px) {{
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
