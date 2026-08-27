"""
Authored icon set for Loot Ledger.

One drawing grid (24), one stroke weight (1.6), round caps and joins, no fills
except where a shape is deliberately solid. Everything inherits `currentColor`
so an icon takes the colour of whatever it sits in.

The board's own vocabulary lives here too: arrivals and departures are drawn as
arrows entering and leaving a platform edge, not as generic up/down chevrons.
"""

_PATHS = {
    # --- board vocabulary -------------------------------------------------
    "arrival": '<path d="M12 3v11"/><path d="m7.5 9.5 4.5 4.5 4.5-4.5"/><path d="M4 20h16"/>',
    "departure": '<path d="M12 14V3"/><path d="m7.5 7.5 4.5-4.5 4.5 4.5"/><path d="M4 20h16"/>',
    "board": ('<rect x="3" y="4" width="18" height="16" rx="1.5"/>'
              '<path d="M3 9h18"/><path d="M8 13h8"/><path d="M8 16.5h5"/>'),
    "platform": '<path d="M4 17h16"/><path d="M7 17V9"/><path d="M12 17V6"/><path d="M17 17v-5"/>',
    "clock": '<circle cx="12" cy="12" r="8.25"/><path d="M12 7.5V12l3 1.8"/>',

    # --- money ------------------------------------------------------------
    "wallet": ('<path d="M3.75 7.5A2.25 2.25 0 0 1 6 5.25h11.25A1.75 1.75 0 0 1 19 7v1"/>'
               '<rect x="3.75" y="7.5" width="16.5" height="11.25" rx="2"/>'
               '<circle cx="16" cy="13.1" r="1.15"/>'),
    "coins": ('<ellipse cx="9" cy="7" rx="5.25" ry="2.5"/>'
              '<path d="M3.75 7v4.5c0 1.38 2.35 2.5 5.25 2.5s5.25-1.12 5.25-2.5V7"/>'
              '<path d="M14.25 11.2c3.3.25 6 1.6 6 3.05 0 1.38-2.35 2.5-5.25 2.5-1.4 0-2.68-.26-3.62-.69"/>'
              '<path d="M9.75 16.6v1.4c0 1.38 2.35 2.5 5.25 2.5s5.25-1.12 5.25-2.5v-3.7"/>'),
    "handshake": ('<path d="M8.5 12.5 6 15l2.5 2.5"/><path d="M15.5 12.5 18 15l-2.5 2.5"/>'
                  '<path d="M6 15H3.75"/><path d="M20.25 15H18"/>'
                  '<path d="M9 7.5h6l2.25 3.25H6.75L9 7.5Z"/>'),
    "receivable": '<path d="M12 20V7"/><path d="m7 12 5-5 5 5"/><path d="M4 4h16"/>',
    "payable": '<path d="M12 4v13"/><path d="m7 12 5 5 5-5"/><path d="M4 20h16"/>',

    # --- actions ----------------------------------------------------------
    "plus": '<path d="M12 5.25v13.5"/><path d="M5.25 12h13.5"/>',
    "minus": '<path d="M5.25 12h13.5"/>',
    "close": '<path d="m6.5 6.5 11 11"/><path d="m17.5 6.5-11 11"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "download": ('<path d="M12 3.75v10.5"/><path d="m7.75 10 4.25 4.25L16.25 10"/>'
                 '<path d="M4.5 19.5h15"/>'),
    "upload": ('<path d="M12 20.25V9.75"/><path d="m7.75 14 4.25-4.25L16.25 14"/>'
               '<path d="M4.5 4.5h15"/>'),
    "refresh": ('<path d="M20 12a8 8 0 1 1-2.4-5.7"/><path d="M20 3.5V8h-4.5"/>'),
    "stop": '<rect x="7" y="7" width="10" height="10" rx="1.5"/>',
    "send": '<path d="M4.5 12 20 4.5 15.5 20l-3.6-5.9L4.5 12Z"/><path d="m11.9 14.1 3.6-6.1"/>',
    "trash": ('<path d="M4.5 6.75h15"/><path d="M9.75 6.75V4.9h4.5v1.85"/>'
              '<path d="M6.75 6.75 7.6 19a1 1 0 0 0 1 .95h6.8a1 1 0 0 0 1-.95l.85-12.25"/>'
              '<path d="M10.25 10.5v5.75"/><path d="M13.75 10.5v5.75"/>'),
    "edit": ('<path d="M4.5 19.5h4L19 9a2.12 2.12 0 0 0-3-3L5.5 16.5l-1 3Z"/>'
             '<path d="m14.75 7.25 2 2"/>'),
    "settings": ('<circle cx="12" cy="12" r="2.9"/>'
                 '<path d="M12 3.75v2.1M12 18.15v2.1M20.25 12h-2.1M5.85 12h-2.1'
                 'M17.83 6.17l-1.48 1.48M7.65 16.35l-1.48 1.48'
                 'M17.83 17.83l-1.48-1.48M7.65 7.65 6.17 6.17"/>'),
    "expand": ('<path d="M9.5 4.5h-5v5"/><path d="M14.5 19.5h5v-5"/>'
               '<path d="m4.5 4.5 5.5 5.5"/><path d="m19.5 19.5-5.5-5.5"/>'),
    "collapse": ('<path d="M4.5 9.5h5v-5"/><path d="M19.5 14.5h-5v5"/>'
                 '<path d="m9.5 9.5-5-5"/><path d="m14.5 14.5 5 5"/>'),
    "history": ('<path d="M3.9 10.5A8.25 8.25 0 1 1 4 14.4"/>'
                '<path d="M3.75 4.5V10.5H9.75"/><path d="M12 8v4.3l2.9 1.7"/>'),
    "chat": ('<path d="M20.25 11.4c0 3.9-3.7 7.05-8.25 7.05a9.5 9.5 0 0 1-2.5-.33L4.5 19.5l1.2-3.35'
             'A6.8 6.8 0 0 1 3.75 11.4c0-3.9 3.7-7.05 8.25-7.05s8.25 3.15 8.25 7.05Z"/>'),
    "signal": ('<path d="M12 20.25V13"/><circle cx="12" cy="9.5" r="2.4"/>'
               '<path d="M7.4 14.1a6.5 6.5 0 0 1 0-9.2"/><path d="M16.6 4.9a6.5 6.5 0 0 1 0 9.2"/>'),
    "alert": ('<path d="M12 4.75 21 19.5H3L12 4.75Z"/><path d="M12 10.25v4"/>'
              '<circle cx="12" cy="16.9" r=".9" fill="currentColor" stroke="none"/>'),
    "info": ('<circle cx="12" cy="12" r="8.25"/><path d="M12 11.25v5"/>'
             '<circle cx="12" cy="8.1" r=".9" fill="currentColor" stroke="none"/>'),
    "chevron_down": '<path d="m7 10 5 5 5-5"/>',
    "chevron_left": '<path d="m14 7-5 5 5 5"/>',
    "chevron_right": '<path d="m10 7 5 5-5 5"/>',
    "external": ('<path d="M13.5 4.5h6v6"/><path d="m19.5 4.5-8 8"/>'
                 '<path d="M18 14.25v4.25a1.25 1.25 0 0 1-1.25 1.25H5.5a1.25 1.25 0 0 1-1.25-1.25V7.25A1.25 1.25 0 0 1 5.5 6h4.25"/>'),
    "sheet": ('<rect x="4" y="3.75" width="16" height="16.5" rx="1.5"/>'
              '<path d="M4 9h16"/><path d="M4 15h16"/><path d="M10.5 9v11.25"/>'),
    "seed": ('<path d="M12 20.25v-6.5"/>'
             '<path d="M12 13.75c0-3.2 2.4-5.8 5.4-5.8 0 3.2-2.4 5.8-5.4 5.8Z"/>'
             '<path d="M12 13.75c0-2.6-2-4.7-4.4-4.7 0 2.6 2 4.7 4.4 4.7Z"/>'),
}

_SOLID = {"stop"}


def icon(name: str, size: int = 20, cls: str = "", stroke: float = 1.6) -> str:
    """Inline SVG string for `name`. Unknown names render nothing rather than a box."""
    path = _PATHS.get(name)
    if not path:
        return ""
    fill = "currentColor" if name in _SOLID else "none"
    stroke_attr = "none" if name in _SOLID else "currentColor"
    classes = f"ll-icon {cls}".strip()
    return (
        f'<svg class="{classes}" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="{fill}" stroke="{stroke_attr}" stroke-width="{stroke}" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" '
        f'focusable="false">{path}</svg>'
    )


def names():
    return sorted(_PATHS)
