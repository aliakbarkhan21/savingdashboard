---
name: Loot Ledger
description: A station departure board for money — amber signage ink on dark enamel, one strip of split-flap figures.
colors:
  void: "#07090C"
  panel: "#0E1116"
  panel-2: "#141A23"
  panel-3: "#1B222D"
  rule: "rgba(233,237,242,0.085)"
  rule-2: "rgba(233,237,242,0.17)"
  amber: "#FFB300"
  amber-12: "rgba(255,179,0,0.12)"
  amber-24: "rgba(255,179,0,0.24)"
  ink: "#E9EDF2"
  ink-2: "#9AA6B4"
  ink-3: "#7B8593"
  arrival: "#2DD4A7"
  departure: "#FF6B5B"
  bar-muted: "#5E6E84"
  platform-food: "#F4713B"
  platform-games: "#A78BFA"
  platform-hangouts: "#F472B6"
  platform-shopping: "#FBBF24"
  platform-subscriptions: "#22D3EE"
  platform-transportation: "#60A5FA"
  platform-utilities: "#2DD4BF"
  platform-other: "#94A3B8"
  platform-income: "#2DD4A7"
  platform-returned: "#4ADE80"
  platform-loan: "#FBBF24"
  platform-lent: "#C084FC"
  platform-settled: "#94A3B8"
typography:
  flap-figure:
    fontFamily: "Barlow Condensed, Arial Narrow, system-ui, sans-serif"
    fontSize: "clamp(1.3rem, 4.3cqi, 3.9rem)"
    fontWeight: 700
    lineHeight: 0.9
    letterSpacing: "0.004em"
    fontFeature: "tnum 1, lnum 1"
  masthead:
    fontFamily: "Barlow Condensed, Arial Narrow, system-ui, sans-serif"
    fontSize: "2.05rem"
    fontWeight: 700
    lineHeight: 0.95
    letterSpacing: "0.012em"
  display:
    fontFamily: "Barlow Condensed, Arial Narrow, system-ui, sans-serif"
    fontSize: "1.6rem"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "normal"
  service-period:
    fontFamily: "Barlow Condensed, Arial Narrow, system-ui, sans-serif"
    fontSize: "1.3rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "0.06em"
  column-heading:
    fontFamily: "Barlow Condensed, Arial Narrow, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.13em"
  row-amount:
    fontFamily: "Barlow Condensed, Arial Narrow, system-ui, sans-serif"
    fontSize: "1.16rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.01em"
  body:
    fontFamily: "Barlow, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 500
    lineHeight: 1.6
    letterSpacing: "normal"
  small:
    fontFamily: "Barlow, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 600
    lineHeight: 1.55
    letterSpacing: "0.02em"
  label:
    fontFamily: "Barlow, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.17em"
rounded:
  tile: "2px"
  md: "3px"
  pill: "99px"
spacing:
  s1: "4px"
  s2: "8px"
  s3: "12px"
  s4: "16px"
  s5: "24px"
  s6: "32px"
  s7: "48px"
  s8: "64px"
components:
  button-secondary:
    backgroundColor: "{colors.panel-2}"
    textColor: "{colors.ink}"
    typography: "{typography.small}"
    rounded: "{rounded.md}"
    height: "36px"
  button-secondary-hover:
    backgroundColor: "{colors.panel-3}"
    textColor: "{colors.amber}"
  button-primary:
    backgroundColor: "{colors.amber}"
    textColor: "{colors.void}"
    typography: "{typography.small}"
    rounded: "{rounded.md}"
    height: "36px"
  input-field:
    backgroundColor: "{colors.panel-2}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
  input-label:
    textColor: "{colors.ink-3}"
    typography: "{typography.label}"
  chip-platform:
    backgroundColor: "{colors.platform-food}"
    textColor: "{colors.void}"
    rounded: "{rounded.tile}"
    padding: "3px 0"
    width: "30px"
  status-lamp:
    textColor: "{colors.arrival}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "5px 11px"
  flap-tile:
    textColor: "{colors.amber}"
    typography: "{typography.flap-figure}"
    rounded: "{rounded.tile}"
    padding: "0.07em 0.055em 0.09em"
  board-panel:
    backgroundColor: "{colors.panel-2}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
  side-panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "16px"
---

# Design System: Loot Ledger

## Overview

**Creative North Star: "The Departure Board"**

Money arriving and money leaving are arrivals and departures read off a single dark enamel panel lit from within. The surface is one board, not a wall of cards: a service header names the period and reports its state, four split-flap figures sit across one strip, and the two ledgers run beneath as opposed columns. The KPI-card grid this category always ships is the thing the world exists to refuse — there is no width at which four figures become four boxes.

Density is high and the reading field is achromatic. Amber is the board's light and carries the four figures; three inks carry everything else. Hue has exactly two jobs and never a third. Depth comes from tonal layering and hairline rules, not from borders drawn around content, and the whole panel is separated from the page by one deep ambient drop plus a single inset top highlight — the enamel catching the room's light.

Motion is one authored moment and it is earned: the flap settle plays only when a figure has actually changed value. Everything else is a 140ms state transition or nothing at all.

**Key Characteristics:**
- Achromatic reading field; colour rationed to platform identity and status
- Barlow Condensed signage caps over Barlow UI, every figure tabular
- Hairline rules instead of card borders
- Container queries, not viewport queries — the board responds to its own width
- One motion moment: the flap settle, gated on a real value change
- Near-square corners throughout (3px panels, 2px tiles)

## Colors

A monochrome enamel field lit by one amber lamp, with a transit-line palette held in reserve for category identity alone.

### Primary
- **Signal Amber** (`{colors.amber}`): the board's light. The four flap figures, the active month on the rail, the selected tab, focus rings, the primary button fill, the caret, links, and the current month's run-strip bar. Nothing decorative is amber.

### Secondary
- **Arrival Green** (`{colors.arrival}`) and **Departure Coral** (`{colors.departure}`): status only. They report the on-time / cancelled lamp, the capacity-meter fill at its thresholds, a negative on-hand figure, and the direction of a period-over-period delta. They never tint the arrivals and departures columns themselves.

### Tertiary
- **The Platform Rail** (the `platform-*` keys): one hue per category in the manner of transit line colours — thirteen fixed assignments across eight spend categories and five non-category platforms used on the arrivals side. This map is the single source: chips, the load bar and any chart read from it, so a category is the same colour everywhere it appears. Chip type is always `{colors.void}` on the hue.

### Neutral
- **Deep Void** (`{colors.void}`): the page behind the board, and the ink used on top of amber and platform hues.
- **Enamel Panel** (`{colors.panel}`) / **Enamel Panel Lit** (`{colors.panel-2}`) / **Enamel Raised** (`{colors.panel-3}`): the three-step tonal ladder — page furniture, the board's lit top edge and input fills, and hover/raised chrome respectively.
- **Board Ink** (`{colors.ink}`, 14.86:1): row labels, primary values, the masthead, and the text of a selection over the 24%-amber selection wash.
- **Secondary Ink** (`{colors.ink-2}`, 7.06:1): column headings, sums, supporting copy.
- **Recessive Ink** (`{colors.ink-3}`, 4.68:1): captions, labels, timestamps, currency marks, the `+`/`−` prefixes.
- **Hairline** (`{colors.rule}`) / **Hairline Strong** (`{colors.rule-2}`): every division in the product. Rules divide; they do not enclose.
- **Muted Bar** (`{colors.bar-muted}`, 3.36:1): non-current run-strip bars, held above the 3:1 non-text floor.

### Named Rules

**The Two Jobs Rule.** Hue has exactly two jobs: the platform rail that names a category, and status. Direction — arrival versus departure — is carried by the word, the icon, the column and the `+`/`−` glyph, never by tint. A third job for colour is a bug.

**The Binding Ground Rule.** Contrast is verified against `{colors.panel-2}`, the lightest surface text sits on, not the darkest. Recessive ink at 4.68:1 is the floor for body-size text; anything dimmer must be large-format or non-text.

**The Shared Threshold Rule.** Status colour is a function of one pair of numbers — 70% and 90% of available cash spent. Below 70 is Arrival Green; 70–89 is Signal Amber; 90+, or a negative on-hand, resolves to Departure Coral; a period with no activity is the quiet grey lamp rather than a healthy one. The service lamp and the capacity meter read the same thresholds, so they can never disagree.

## Typography

**Display Font:** Barlow Condensed (500/600/700), with Arial Narrow fallback
**Body Font:** Barlow (400/500/600/700), with system-ui fallback

Both load from Google Fonts via a single `@import` at the head of the stylesheet; the committed Streamlit theme sets a dark base so the first paint does not fight it.

**Character:** Condensed signage caps do the naming — masthead, period, column headings, figures, tab labels, table headers — and the humanist UI face does the reading. The condensed face is always uppercase and always letterspaced; the UI face is never uppercased above label size.

### Hierarchy
- **Flap figure** (Condensed 700, `clamp(1.3rem, 4.3cqi, 3.9rem)`, line-height 0.9): the four board figures only. Steps down to `clamp(1.1rem, 3.45cqi, 2.5rem)` under a 1150px container.
- **Masthead** (Condensed 700, 2.05rem, 0.95): the product name in the sidebar, with a 9px amber lamp set on the baseline row.
- **Display** (Condensed 700, 1.6rem, line-height 1): the secondary-display step, one rung below the flap figure. It carries the figures that matter but are not board figures — the obligation values and the capacity percentage — plus the first-run head, which is set in caps at 0.06em. Before this token those three sites sat at 1.7, 1.55 and 1.5rem: three sizes doing one job.
- **Service period** (Condensed 700, 1.3rem, tracking 0.06em, caps): the period name in the service header.
- **Column heading** (Condensed 700, 1rem, tracking 0.13em, caps): Arrivals / Departures, panel titles, empty-state titles.
- **Row amount** (Condensed 600, 1.16rem): ledger row values, the one fixed size below the display step.
- **Body** (Barlow 500, 0.9375rem, 1.6): row labels, inputs, chat. Explanatory prose caps at 68ch; empty-state copy at 34ch.
- **Small** (Barlow 600, 0.8125rem, 1.55): sums, buttons, list values, legends.
- **Label** (Barlow 700, 0.6875rem, tracking 0.17em, caps): figure labels, section captions, widget labels, platform codes, table headers. Tracking runs 0.10em–0.18em by context; caps at this size are never below 0.10em.

### Named Rules

**The Tabular Rule.** Tabular, lining figures are set globally on the app and on its inputs, buttons and tables. Every digit in this product stacks in a column down the page. Never opt a figure out.

**The One Money Format Rule.** `Rs.` prefix, grouped thousands. Two forms only on the surface: compact on the flap figures (`1,240`, `1.24M`) and whole-rupee `Rs. N` on every sum and note. Two decimals appear only inside the ledger tables. Dates display DD/MM/YYYY on records and DD/MM on board rows; storage is always ISO.

**The Closed Ramp Rule.** The ramp is six tokens — display, h2, h3, body, small, micro — and a new size joins it or reuses one; it never lands as a literal. The flap figure is the single deliberate exception and is not a token: it scales off its container in `cqi`, so it is declared where it is used, and its 1150px step-down (`clamp(1.1rem, 3.45cqi, 2.5rem)`, with a 0.625rem label) stays inline for the same reason.

**The Signage Caps Rule.** Uppercase belongs to Barlow Condensed and to the 0.6875rem label role. Sentence-case body copy is never set in the condensed face, and body-size Barlow is never uppercased.

## Layout

The page is a full-width board inside a 1680px container with 24px side padding and 32px below. The sidebar is a fixed enamel column at `{colors.panel}` with a strong hairline on its right edge, holding the masthead, the month rail and the entry forms; the board owns the main column.

The board declares itself a named inline-size container, and every responsive step is a container query. This is load-bearing: opening the bot panel narrows the board while the window does not change width, so viewport queries would read the wrong number. The flap figures size in `cqi` for the same reason.

Breakpoints are container widths. At 1150px the figure steps down and the cells tighten; at 720px the four figures fold to 2×2; at 520px the figures stack to one column and the two ledger columns become one. The four figures stay on one strip everywhere above 720px. A single viewport media query survives, on the first-run teaching panel, which sits outside the board container.

Rhythm is an 8px-derived scale (4 / 8 / 12 / 16 / 24 / 32 / 48 / 64). Section headers pad 12px vertical by 24px horizontal, figure cells 24px, ledger rows 9px by 24px. The ledger scroll region caps at 336px with a 52px mask fade at its foot, removed when the list is short enough not to scroll.

### Named Rules

**The Container Rule.** Responsive behaviour keys off the board's own inline size, never the viewport. A board-resident component uses `@container board` and `cqi`, or neither.

**The One Strip Rule.** A narrower board buys room by stepping the figure down and tightening the cell. It never folds four figures into a 2×2 of cards above a 720px container — that grid is the thing this design refuses.

## Elevation & Depth

Tonal layering, not shadow. Depth is a three-step surface ladder (void → panel → panel-2 → panel-3) plus hairline rules; content is divided, never boxed. Shadows appear in exactly three places, all describing physical objects: the board's ambient drop, the inset highlight that makes the enamel catch light, and the flap tile's small cast. The lamp glow is the only emissive effect.

### Shadow Vocabulary
- **Board lift** (`box-shadow: 0 24px 60px -28px rgba(0,0,0,0.9), inset 0 1px 0 rgba(233,237,242,0.05)`): the board panel only. One object floats in this product.
- **Flap cast** (`box-shadow: inset 0 0 0 1px rgba(233,237,242,0.06), 0 2px 5px rgba(0,0,0,0.45)`): the split-flap tile.
- **Lamp glow** (`box-shadow: 0 0 10px 1px rgba(255,179,0,0.65)`): the 9px masthead lamp.

### Named Rules

**The Rules-Not-Borders Rule.** Sections are divided by 1px hairlines that run edge to edge. Only the board, the side panels and form controls carry a full border, and it is always the single strong hairline at 3px radius.

## Shapes

Near-square. Panels, buttons, inputs and dropzones take a 3px radius; tiles, chips, meter tracks and run-strip bars take 2px; only the status lamp, the month-rail bars and the scrollbar thumb are pills. Nothing here is soft.

Two radii and a pill are the whole vocabulary: 3px for panels, buttons, inputs and dropzones; 2px for tiles, chips, meter tracks, run-strip bars and the run-key swatches; pill for the status lamp, the month-rail bars and the scrollbar thumb.

The recurring silhouette is the flap: a tile with a hard centre seam, drawn as a four-stop vertical gradient that breaks at 49.6%/50.4% with a 1px black hinge line across the middle. It appears at three scales — the character tile inside a figure, the full-row blank tile, and the vacant run-strip slot. Icons are one authored set on a 24 grid at 1.6 stroke, round caps and joins, `currentColor` throughout, inline SVG. No raster images ship in this build.

The flap's own material stays literal on purpose, and it is material rather than palette drift: the four-stop face gradient (`#232B37 / #171D26 / #10151C / #1B222D`) is what makes the hinge read, and the two black hinge seams (`rgba(0,0,0,0.7)` on the character tile, `rgba(0,0,0,0.55)` on the blank row tile), the run-fill inset (`rgba(0,0,0,0.32)`) and the `#000` inside the ledger mask — an alpha channel, not a colour — belong to the object, not to the palette.

## Components

### Buttons
- **Shape:** near-square (3px radius), minimum height 36px, Barlow 600 at 0.8125rem with 0.03em tracking.
- **Secondary (default):** raised enamel fill (`{colors.panel-2}`) with a strong hairline border and board ink.
- **Hover / Focus:** lifts to `{colors.panel-3}` with border and label both going amber over 140ms on `cubic-bezier(0.16, 1, 0.3, 1)`; focus adds the global 2px amber outline at 2px offset.
- **Primary:** solid amber with void-coloured type; hover brightens 1.09 rather than shifting hue. Match it with `button[kind^="primary"]` — Streamlit tags form submits as `primaryFormSubmit`, so an exact-value selector silently misses every form.
- **Disabled:** 42% opacity, not-allowed cursor.

### Chips
- **Style:** the two-letter platform code in condensed 700 at 0.6875rem, void-coloured type on the category's own hue, 2px radius, 30px wide, centred.
- **State:** chips are identity, not selection. There is no selected/unselected variant — code and hue are both fixed per category by the platform map.

### Cards / Containers
- **Board:** vertical gradient from `{colors.panel-2}` to `{colors.panel}`, one strong hairline, 3px radius, clipped, board lift shadow. One board per screen.
- **Side panel:** flat `{colors.panel}`, strong hairline, 3px radius, header padded 12/16 with a hairline beneath, body padded 16.
- **Internal padding:** 24px at board-level cells, 16px in panels, 9px in rows.

### Inputs / Fields
- **Style:** `{colors.panel-2}` fill, strong hairline, 3px radius, Barlow at body size, placeholder in recessive ink at full opacity.
- **Label:** the uppercase label role in recessive ink, 5px above the field.
- **Focus:** border goes amber, plus the global amber focus ring. Every interactive surface keeps that ring.

### Navigation
The month rail is navigation that is already a chart: one row per month laid out `46px | 1fr | auto`, month in condensed caps, a 5px pill bar whose fill is that month's outflow, amount in micro type. The active row takes a 12%-amber wash and a 2px amber left edge, and its month, bar fill and amount each step up one level of emphasis. Tabs use condensed caps in recessive ink with an amber label and amber highlight when selected; Streamlit's own tab border is removed.

### The Split-Flap Figure
Each character of a figure is its own tile; separators (commas, the compact `M`) get no tile, because boxing punctuation makes a number harder to read, not more thematic. The currency mark sits at 0.36em in recessive ink, aligned to the bottom of the digits. The value carries `perspective: 460px`, and when the figure has changed, `flapSettle` runs a 560ms `rotateX` hinge with a 34ms per-tile stagger and a brightness dip through the swing. The arming class is emitted only when this run's figures differ from the last, and the animation is disabled entirely under `prefers-reduced-motion`.

### Unused Capacity
Two idioms speak one language. An empty arrival slot is a recessed full-row flap with its own hinge seam at 55% opacity; a vacant run-strip month is a fainter track with a dimmed mark. Neither uses content-shaped grey bars, which read as a loading skeleton and say the opposite of "nothing is here".

## Do's and Don'ts

### Do:
- **Do** ration hue to the platform rail and to status; everything else reads in ink and amber.
- **Do** verify new text colours against `{colors.panel-2}` and hold the floor: 4.68:1 for body-size text, 3:1 for non-text marks.
- **Do** use `@container board` and `cqi` for anything living inside the board.
- **Do** divide with hairlines and tonal steps, and reserve the board lift shadow for the board itself.
- **Do** set condensed caps with at least 0.06em tracking, and keep every figure tabular.
- **Do** gate any new motion on a real state change and give it a `prefers-reduced-motion` exit.
- **Do** leave the flap's material literals alone — the face gradient, the two hinge seams, the run-fill inset and the mask's `#000` are object material, not tokens waiting to be extracted.
- **Do** draw new icons on the 24 grid at 1.6 stroke, round caps and joins, `currentColor`.
- **Do** format money as `Rs. N` with grouped thousands — compact only on flap figures, two decimals only in tables.
- **Do** match Streamlit primaries with `button[kind^="primary"]`, and remember the sidebar is emitted before main in the DOM, so a stylesheet injected early in the script lands later in document order.

### Don't:
- **Don't** tint a column, a label or a figure to show direction; the word, the icon and the `+`/`−` carry it.
- **Don't** fold the four figures into a card grid above a 720px container.
- **Don't** introduce a fourth surface tone, or a radius outside 2px / 3px / pill.
- **Don't** set a new type size as a literal. Use the six-token ramp or add a step to it; only the container-scaled flap figure is declared inline.
- **Don't** animate on rerun. A board that flips when nothing changed is a toy, not an instrument.
- **Don't** use content-shaped grey bars for empty states; use the blank flap.
- **Don't** expect `st.dataframe`'s body to take CSS — it is a canvas grid, and only its header row responds.
- **Don't** carry a hue below recessive ink's contrast onto body-size text: the dimmed-figure amber (~3.0:1 on `{colors.panel-2}`) is licensed for the large-format figure alone and is not a text colour.
