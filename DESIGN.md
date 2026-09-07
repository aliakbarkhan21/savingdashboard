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
  chip-ink: "#07090C"
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
  signage-label:
    fontFamily: "Barlow, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.17em"
  ui-label:
    fontFamily: "Barlow, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "normal"
rounded:
  tile: "2px"
  sm: "6px"
  md: "10px"
  lg: "14px"
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
    textColor: "{colors.ink-2}"
    typography: "{typography.ui-label}"
  chip-platform:
    backgroundColor: "{colors.platform-food}"
    textColor: "{colors.chip-ink}"
    rounded: "{rounded.tile}"
    padding: "3px 0"
    width: "30px"
  status-lamp:
    textColor: "{colors.arrival}"
    typography: "{typography.signage-label}"
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
    rounded: "{rounded.lg}"
  side-panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
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
- A hard mechanism in a soft housing: 2px tiles and chips inside 10px chrome
  and 14px panels

## Colors

A monochrome enamel field lit by one amber lamp, with a transit-line palette held in reserve for category identity alone.

### Primary
- **Signal Amber** (`{colors.amber}`): the board's light. The four flap figures, the selected tab, focus rings, the primary button fill, the caret, links, and the current month's run-strip bar. Nothing decorative is amber.

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

Both are **self-hosted** from `/app/static/fonts` as seven woff2 faces, latin subset, 152KB. They are not fetched from Google — this doc said they were, and it was wrong. An `@import` is a blocking request to a third party on every load, and when it is slow, filtered or unreachable every rule below still applies while the product silently falls back to Arial Narrow, which reads as a cheap imitation of itself rather than as a broken stylesheet. The committed Streamlit theme sets a dark base so the first paint does not fight the rest.

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
- **Signage label** (Barlow 700, 0.6875rem, tracking 0.17em, caps): figure labels, section captions, platform codes, obligation labels, the run-strip footer. Tracking runs 0.10em–0.18em by context; caps at this size are never below 0.10em.
- **UI label** (Barlow 600, 0.8125rem, sentence case, no tracking, `{colors.ink-2}`): widget labels, panel titles, tab labels, expander summaries, table headers. Adopting it needed no source-string changes — every one of these was already written in sentence case and uppercased by CSS.

### Named Rules

**The Tabular Rule.** Tabular, lining figures are set globally on the app and on its inputs, buttons and tables. Every digit in this product stacks in a column down the page. Never opt a figure out.

**The One Money Format Rule.** `Rs.` prefix, grouped thousands. Two forms only on the surface: compact on the flap figures (`1,240`, `1.24M`) and whole-rupee `Rs. N` on every sum and note. Two decimals appear only inside the ledger tables. Dates display DD/MM/YYYY on records and DD/MM on board rows; storage is always ISO.

**The Closed Ramp Rule.** The ramp is six tokens — display, h2, h3, body, small, micro — and a new size joins it or reuses one; it never lands as a literal. The flap figure is the single deliberate exception and is not a token: it scales off its container in `cqi`, so it is declared where it is used, and its 1150px step-down (`clamp(1.1rem, 3.45cqi, 2.5rem)`, with a 0.625rem label) stays inline for the same reason.

**The Signage Caps Rule.** Uppercase belongs to Barlow Condensed and to the 0.6875rem *signage* label role, and signage means the board: figure labels, section captions, column headings, the status lamp, platform codes, the run-strip footer. Sentence-case body copy is never set in the condensed face, and body-size Barlow is never uppercased.

**The Furniture Is Not Signage Rule.** A form label, a panel title, a tab and a table header name a piece of interface, not a platform. They take the *UI label* role — Barlow 600 at 0.8125rem, sentence case, no tracking, secondary ink. This split is the single largest thing separating the current surface from the one before it: one label role was doing both jobs, and uppercase micro-type at 0.14em tracking on a settings form shouts a word that does not need shouting. If a new label sits inside the board, it is signage; if it sits inside a form, a dialog or a panel header, it is furniture.

## Layout

The page is a full-width board inside a 1680px container with 24px side padding and 32px below. The sidebar is a fixed enamel column at `{colors.panel}` with a strong hairline on its right edge, holding the masthead, the entry form and the period picker; the board owns the main column.

**The sidebar has to fit a laptop window without scrolling.** It ran to 689px, so anything under about 695px of viewport scrolled — and what it was spending that height on was mostly not content. Streamlit pads every `<h1>` by 20px above and 16px below; in a sidebar that was the gap above the wordmark and a third of the wordmark's own box, so it is zeroed and the type is *larger* than before while sitting *higher*. The "Departures board" subtitle went with it — six-point caps restating what the board says at full size two hundred pixels to the right. The credit no longer rides a flex spacer to the floor, which on a short window put it below the fold. 689px → 596px.

The board declares itself a named inline-size container, and every responsive step is a container query. This is load-bearing: opening the bot panel narrows the board while the window does not change width, so viewport queries would read the wrong number. The flap figures size in `cqi` for the same reason.

Breakpoints are container widths. At 1150px the figure steps down and the cells tighten; at 720px the four figures fold to 2×2; at 520px the figures stack to one column and the two ledger columns become one. The four figures stay on one strip everywhere above 720px. A single viewport media query survives, on the first-run teaching panel, which sits outside the board container.

Rhythm is an 8px-derived scale (4 / 8 / 12 / 16 / 24 / 32 / 48 / 64). Section headers pad 12px vertical by 24px horizontal, figure cells 24px, ledger rows 9px by 24px. The ledger scroll region caps at 336px with a 52px mask fade at its foot, removed when the list is short enough not to scroll.

### Named Rules

**The Container Rule.** Responsive behaviour keys off the board's own inline size, never the viewport. A board-resident component uses `@container board` and `cqi`, or neither.

**The One Strip Rule.** A narrower board buys room by stepping the figure down and tightening the cell. It never folds four figures into a 2×2 of cards above a 720px container — that grid is the thing this design refuses.

## Elevation & Depth

Tonal layering for content, weight for chrome. **Content** is still divided by hairlines and a three-step surface ladder (void → panel → panel-2 → panel-3), never boxed — that part of the law is unchanged and is what keeps the board dense rather than card-strewn. What was missing is that **things you press had no weight at all**: every button, input and dialog sat perfectly flat, which is most of what made the surface read as older than it is.

So chrome now carries a three-step elevation scale, and content still does not.

### Shadow Vocabulary

Object shadows, which describe physical things and are declared where they are used:
- **Board lift** (`0 24px 60px -28px var(--board-shadow), inset 0 1px 0 rgba(var(--ink-rgb),0.05)`): the board panel only. One object floats in this product.
- **Flap cast** (`inset 0 0 0 1px var(--flap-edge), 0 2px 5px var(--flap-shadow)`): the split-flap tile.
- **Lamp glow** (`0 0 10px 1px rgba(255,179,0,0.65)`): the 9px masthead lamp.

Chrome elevation, tokenised per mode so light mode can run heavier than dark:
- **`--lift-1`**: resting weight on buttons and the bot composer.
- **`--lift-2`**: button hover, popovers, tooltips, the active segment of a segmented control.
- **`--lift-3`**: the Settings dialog and the command palette.

Light mode's values are deliberately stronger than a naive inversion. Dark ink on cream reads fainter than pale ink on near-black at the same alpha, and the previous light palette carried its shades at 4.5% and its board drop at 16% — which separated nothing. The same reasoning moved `--rule-a` / `--rule-2-a` to per-mode tokens so light mode's hairlines land where dark mode's do.

### Named Rules

**The Press Rule.** Things you can point at move. A card lifts 3px and a button 2px on hover, taking `--lift-2` with them; a button then drops to +1px on press with its shadow collapsed. Up on approach, down on press — that pair is what makes a control feel like an object rather than a picture of one, and card and button agree on how far "raised" is. Nothing scales, and nothing animates on load or on rerun.

The board is deliberately exempt: it is the object the page is about, it already carries the one ambient drop, and a whole page that shrugs when the pointer crosses it reads as loose rather than responsive. Every hover displacement has an explicit `prefers-reduced-motion` exit — the global rule only collapses the duration, so without one the card still jumps the instant it is pointed at.

**The Rules-Not-Borders Rule.** Sections are divided by 1px hairlines that run edge to edge. Only the board, the side panels and form controls carry a full border, and it is always the single strong hairline.

## Shapes

**A hard mechanism inside a soft housing.** Two kinds of object live on this screen and they take different corners, and the seam between them is the whole rule.

The **mechanism** is square: the split-flap tile, the platform chip, the meter track and fill, the run-strip track and bars, the run-key swatch. All 2px, all unchanged. Square is what makes a flap read as a physical thing rather than a number in a box, and softening it would cost the product its one real idea.

The **chrome** is not mechanism. Buttons, inputs, selects, banners, popovers, tooltips, dropzones and the bot composer are furniture standing around the board, and at 2–3px they read as a framework default rather than as anything authored. They take 10px. **Housings** — the board itself, the side panels, the Settings dialog — take 14px, because a large surface needs proportionally more radius than a small one to read as equally rounded. Inline code and the composer's send key take 6px.

This replaces an earlier law that read *"Near-square. Nothing here is soft"* and set one 3px radius across everything. That law was applied to two different kinds of object at once; splitting it along the mechanism/chrome seam does not dilute the concept, it states it more precisely — the board is now a housing with a hard mechanism inside it.

Four radii and a pill are the whole vocabulary: **14px** housings, **10px** chrome, **6px** inline code and small keys, **2px** mechanism, pill for the status lamp, the capacity bars and the scrollbar thumb. `baseRadius` and `buttonRadius` in `.streamlit/config.toml` carry the 10px into the canvas-painted grids and the few surfaces Streamlit paints before the stylesheet reaches them.

The recurring silhouette is the flap: a tile with a hard centre seam, drawn as a four-stop vertical gradient that breaks at 49.6%/50.4% with a 1px black hinge line across the middle. It appears at three scales — the character tile inside a figure, the full-row blank tile, and the vacant run-strip slot. Icons are one authored set on a 24 grid at 1.6 stroke, round caps and joins, `currentColor` throughout, inline SVG. No raster images ship in this build.

The flap's own material stays literal on purpose, and it is material rather than palette drift: the four-stop face gradient (`#232B37 / #171D26 / #10151C / #1B222D`) is what makes the hinge read, and the two black hinge seams (`rgba(0,0,0,0.7)` on the character tile, `rgba(0,0,0,0.55)` on the blank row tile), the run-fill inset (`rgba(0,0,0,0.32)`) and the `#000` inside the ledger mask — an alpha channel, not a colour — belong to the object, not to the palette.

## Components

### Buttons
- **Shape:** 10px radius, minimum height 36px, Barlow 600 at 0.8125rem with 0.03em tracking, resting on `--lift-1`.
- **Secondary (default):** raised enamel fill (`{colors.panel-2}`) with a strong hairline border and board ink.
- **Hover / Focus:** lifts to `{colors.panel-3}` and `--lift-2`, with border and label both going amber over 140ms on `cubic-bezier(0.16, 1, 0.3, 1)`; focus adds the global 2px amber outline at 2px offset.
- **Active:** `translateY(1px)` with the shadow removed. See The Press Rule.
- **Primary:** solid amber with void-coloured type; hover brightens 1.09 rather than shifting hue. Match it with `button[kind^="primary"]` — Streamlit tags form submits as `primaryFormSubmit`, so an exact-value selector silently misses every form.
- **Disabled:** 42% opacity, not-allowed cursor.

### Chips
- **Style:** the two-letter platform code in condensed 700 at 0.6875rem on the category's own hue, 2px radius, 30px wide, centred.
- **Ink:** `{colors.chip-ink}`, a fixed near-black in *both* modes. It was `{colors.void}`, which is near-black in dark mode and **cream** in light — so a light-mode Shopping chip put #EDE7D9 on #FBBF24 at about 1.5:1. This document and the code comment both already claimed a fixed always-dark ink; only the code disagreed. Now measured at 11.4:1 on the lightest chip in the map.
- **State:** chips are identity, not selection. There is no selected/unselected variant — code and hue are both fixed per category by the platform map.

### Cards / Containers
- **Board:** vertical gradient from `{colors.panel-2}` to `{colors.panel}`, one strong hairline, 14px radius, clipped, board lift shadow. One board per screen.
- **Side panel:** flat `{colors.panel}`, strong hairline, 14px radius, header padded 12/16 with a hairline beneath, body padded 16.
- **Dialog:** `{colors.panel}`, strong hairline, 14px radius, `--lift-3`.
- **Internal padding:** 24px at board-level cells, 16px in panels, 9px in rows.

### Inputs / Fields
- **Style:** `{colors.panel-2}` fill, strong hairline, 10px radius, Barlow at body size, placeholder in recessive ink at full opacity.
- **Label:** the *UI label* role — Barlow 600 at 0.8125rem, sentence case, secondary ink, 5px above the field.
- **Focus:** border goes amber, plus the global amber focus ring. Every interactive surface keeps that ring.

### Navigation
Periods are chosen from a **dropdown** in the sidebar, one option per month plus All Time, each carrying that month's outflow in the display currency. Streamlit's selectbox is type-to-filter, so reaching a month two years back is three keystrokes.

This replaced a month rail that was *navigation and a chart at once*: a stack of buttons whose background gradients encoded each month's outflow against the period peak. It read well and it did not scale — a stack that tall had to be capped at ten, and that cap was the real cost, because the eleventh month back then had no route from the sidebar at all.

Losing the bars costs less than it looks. The run strip at the foot of the board already draws the same twelve months at a size you can actually compare them at, so the rail was a second, smaller copy of a chart that was already on screen; the amount survives on every option. The rule this leaves behind: **when a navigation control has to be truncated to fit, it is the wrong control** — reach beats encoding, and the encoding usually already lives somewhere with room for it.

The picker holds its own widget state, so anything that moves the board without touching it — the command palette, an off-screen jump button — must write that state back *before* the widget is created on the next run. Streamlit refuses a write to a widget's key once the widget exists, and a picker left holding a stale value drags the board back to it.

**Tabs** are addressed by `[data-testid="stTab"]` and `[aria-selected]`, never by `data-baseweb`. Streamlit moved tabs off BaseWeb onto react-aria and every `[data-baseweb="tab*"]` rule here silently stopped matching — with four tabs on screen those selectors returned zero elements while `[data-testid="stTab"]` returned four. The label sits in a nested markdown container, so type rules go on its `<p>`. This is worth remembering beyond tabs: **dead CSS fails silently**, and the only honest check is to count what a selector matches in a live page.

### Tooltips
A tooltip describes what you are pointing at, not what you last pressed. Streamlit shows it on focus as well as hover and a mouse click leaves a button focused, so every icon button kept its label floating over the board after being used — describing an action already taken.

Hidden when nothing is hovered *and* nothing holds keyboard focus. `:focus-visible` is the load-bearing half: a mouse click sets `:focus` but not `:focus-visible`, while Tab sets both. So the tooltip drops after a click and survives for anyone driving the board from the keyboard, who has no other way to learn what an unlabelled icon does.

### Dropdowns
A dropdown must not behave like a text field. Streamlit renders every `st.selectbox` as a react-aria combobox — a real `<input type="text">` — so clicking one puts a caret in it and typing filters the list; type anything the list does not hold and it says "No results", which reads as broken rather than as a filter that found nothing. Every one of them is therefore `readOnly`, which leaves the dropdown intact (it still focuses, still opens on click, arrow keys and Enter still choose) and removes only the keystrokes.

It is set by a MutationObserver in the parent document, not a one-off pass: Streamlit rebuilds these inputs on rerun, and several never exist at first paint at all — the Settings dialog and the Import tab mount their own later. The cost is that reaching a distant option is now scrolling rather than typing; the command palette is the keyboard route, and it is why losing type-to-filter on the period picker is affordable.

### The Corner Cluster
Three 39px squares, hard right on the toolbar row, icon-only and unlabelled: theme, Finance Bot, Settings. Light/dark leads, because it changes how everything else looks while the other two open things. They live in one keyed container rather than three columns — as separate columns the space between them was the row's gap plus each column's leftover width, which read as unrelated marks rather than one cluster.

### Segmented Control
Two labels over one hidden checkbox, used for the Platform Load panel's Share / Trend switch. Pure CSS, so the swap costs no rerun and no scroll position — the same bargain `.ll-expand` strikes on the ledger columns. The active segment is lit *and* `pointer-events: none`, so clicking the option already showing does nothing.

Radios would be the obvious way to get that and they do not work: a radio hidden with `display: none` is never activated by a click on its label. Measured — flipping the very same element's `type` to `checkbox` and clicking the same label checked it, with the label/control association identical either way.

### The Composer
An empty chat input must be one row tall. Its row sizes to the textarea's content, and for an empty field the content is the **placeholder** — so the moment "Message the bot" wraps, the empty box grows to two or three rows. The placeholder is therefore held to one line (`::placeholder { white-space: nowrap; text-overflow: ellipsis }`), which touches only the empty state; typed text still wraps and auto-grows to the 7.5em cap.

Two things made it wrap: a genuinely narrow rail, and the font swap. Barlow loads with `font-display: swap`, so the first layout is measured in the wider fallback face — which is why the same window width gave 42px on one load and 97px on the next, and why typing a character and deleting it snapped it back. Do not try to fix this by out-specifying the row's flex: Streamlit ships its own `:has(> [data-testid="stChatInputTextArea"]) { flex: 1 1 auto }`, and that rule is correct — growing with content is wanted. The bug was what the row was measuring.

### Panel Fill
Streamlit columns stretch to the tallest of them; the five divs between a column and a panel do not. A panel that should fill its column takes `.ll-panel-fill`, and the stretch rules hang off that class rather than off a positional `:has(> div > div)` chain — a chain anchored on nothing is what silently stops matching on an upgrade. The emotion wrapper in the middle of that chain centres its child, so it is put back to `stretch`.

### Person Cards
Open debts rolled up per person, in the Debts tab above the two ledger tables. The two tables are organised the way the data is stored; what you actually settle with someone is one number, the difference between the two directions. Someone can sit on both sides at once, and split across two tables that nets to nothing visible — the card says it, and marks that person "both ways".

Direction is carried by the words ("owes you" / "you owe") and by which edge is lit, never by tinting the card: status hue doing its one job, not a third. Settled debts are excluded — counting them would make someone who always pays you back look identical to someone who never has.

### Arrivals Ring
The mirror of Platform load, full width beneath the two-column row. Drawn in **amber tints stepped by share**, not in categorical hues: income sources are whoever happened to pay you, not a taxonomy, so giving them their own palette would put hue to a third job and imply a scheme that does not exist. Amber is the board's own light and the arrivals side reads in it.

The colour is emitted in `style`, not the `stroke` attribute — a presentation attribute takes a literal colour and will not resolve a `var()`, which is what a tint is.

### The Setup Strip
When a setting that changes the reported numbers is missing, the board says so, in the departure tone. This is not onboarding and not a checklist: an unset opening balance does not read as "unset" on screen, it reads as "you have less money than you do", and the figure looks exactly as confident as any other. Each notice clears itself the moment the thing is set, so the strip describes the current state rather than tracking progress.

### Sparkline
`theme.trend_svg` — a polyline over a 15%-opacity area fill in the category's own hue, last point marked, 104×26. Each line is scaled to **its own peak**, not a shared one: the question is whether a category is rising against its own past, and a shared scale would answer a different question while flattening every small category into a straight line. The amount beside each row is what makes categories comparable.

### Command Palette
Ctrl/Cmd+K. An overlay in the parent document at `--radius-lg` on `--lift-3`, themed from the board's own custom properties. Choosing an item clicks an off-screen Streamlit button — the same bridge idea the board rows use — or, for a filter, drives the toolbar's existing search box rather than introducing a second filter with its own rules. It does not intercept Ctrl+K while focus is in the bot composer, where that chord belongs to the text field.

### The Split-Flap Figure
Each character of a figure is its own tile; separators (commas, the compact `M`) get no tile, because boxing punctuation makes a number harder to read, not more thematic. The currency mark sits at 0.36em in recessive ink, aligned to the bottom of the digits. The value carries `perspective: 460px`, and when the figure has changed, `flapSettle` runs a 560ms `rotateX` hinge with a 34ms per-tile stagger and a brightness dip through the swing. The arming class is emitted only when this run's figures differ from the last, and the animation is disabled entirely under `prefers-reduced-motion`.

### Unused Capacity
Two idioms speak one language. An empty arrival slot is a recessed full-row flap with its own hinge seam at 55% opacity; a vacant run-strip month is a fainter track with a dimmed mark. Neither uses content-shaped grey bars, which read as a loading skeleton and say the opposite of "nothing is here".

## Do's and Don'ts

### Do:
- **Do** ration hue to the platform rail and to status; everything else reads in ink and amber.
- **Do** verify new text colours against `{colors.panel-2}` and hold the floor: 4.68:1 for body-size text, 3:1 for non-text marks.
- **Do** use `@container board` and `cqi` for anything living inside the board.
- **Do** divide *content* with hairlines and tonal steps, and give *chrome* weight from `--lift-1/2/3`. The board lift shadow stays reserved for the board itself.
- **Do** count what a new selector actually matches in a live page before trusting it. Dead CSS fails silently, and this file has shipped rules that matched nothing for a whole Streamlit release.
- **Do** address Streamlit widgets by `data-testid` or ARIA role. `data-baseweb` is gone from tabs, selects, menus, popovers and modals in 1.62.
- **Do** set condensed caps with at least 0.06em tracking, and keep every figure tabular.
- **Do** gate any new motion on a real state change and give it a `prefers-reduced-motion` exit.
- **Do** leave the flap's material literals alone — the face gradient, the two hinge seams, the run-fill inset and the mask's `#000` are object material, not tokens waiting to be extracted.
- **Do** draw new icons on the 24 grid at 1.6 stroke, round caps and joins, `currentColor`.
- **Do** format money as `Rs. N` with grouped thousands — compact only on flap figures, two decimals only in tables.
- **Do** match Streamlit primaries with `button[kind^="primary"]`, and remember the sidebar is emitted before main in the DOM, so a stylesheet injected early in the script lands later in document order.

### Don't:
- **Don't** tint a column, a label or a figure to show direction; the word, the icon and the `+`/`−` carry it.
- **Don't** fold the four figures into a card grid above a 720px container.
- **Don't** introduce a fourth surface tone, or a radius outside 2px / 6px / 10px / 14px / pill — and never soften the mechanism: the flap tile, the platform chip, the meter track and the run-strip bar stay at 2px.
- **Don't** set a new type size as a literal. Use the six-token ramp or add a step to it; only the container-scaled flap figure is declared inline.
- **Don't** animate on rerun. A board that flips when nothing changed is a toy, not an instrument.
- **Don't** use content-shaped grey bars for empty states; use the blank flap.
- **Don't** set a chip's ink from `{colors.void}`. That token flips with the mode; chip hues do not.
- **Don't** expect `st.dataframe`'s body to take CSS — it is a canvas grid, and only its header row responds.
- **Don't** carry a hue below recessive ink's contrast onto body-size text: the dimmed-figure amber (~3.0:1 on `{colors.panel-2}`) is licensed for the large-format figure alone and is not a text colour.
