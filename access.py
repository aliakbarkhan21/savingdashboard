"""
Who may open this board, and what it is allowed to contain.

Loot Ledger runs as two different things from one codebase, and they have
opposite requirements:

**The laptop instance** holds the real ledger — real names, real amounts. It is
the source of truth. On its own machine that needs no protection, but the point
of a phone-friendly layout is reaching it from a phone, which means putting it
through a tunnel and therefore onto the internet. A personal finance board on a
public address with no gate in front of it is not a personal finance board.

**The deployed instance** on Streamlit Community Cloud is a portfolio piece. Its
storage is ephemeral — a reboot re-clones the repo, and `tracker.db` is
gitignored, so the ledger came back empty every time. That was read as a bug,
and the obvious fix was to give it a real database. The obvious fix was wrong:
Community Cloud apps answer to anyone holding the URL, so persisting the real
ledger there would publish it. The ephemerality was doing an accidental job of
keeping it private.

So the deployment does not get the real data at all. It seeds its own sample
records and says so, which also fixes the thing that actually was broken — a
stranger opening the link used to find an empty board.

Configuration, all optional, read from `st.secrets` first and the environment
second:

    LOOT_LEDGER_DEMO       "1" to make this instance a public sample board.
    LOOT_LEDGER_PASSWORD   shared password to sit in front of the real ledger.
    [auth] in secrets      full OIDC sign-in via st.login(), used if present.

With none of them set the app behaves exactly as it always has: open, local,
real data. That is deliberate — the default has to stay the thing that works on
a laptop with no configuration at all.
"""
from __future__ import annotations

import hmac
import os

import streamlit as st

import db
import demo


def setting(name: str, default=None):
    """Read a secret, then an environment variable, then give up.

    st.secrets raises rather than returning empty when no secrets.toml exists at
    all, so every access is guarded — the same pattern the Gemini key uses.
    """
    try:
        found = st.secrets.get(name)
        if found not in (None, ""):
            return found
    except Exception:
        pass
    found = os.environ.get(name)
    return found if found not in (None, "") else default


def _truthy(value) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def is_demo() -> bool:
    """Whether this instance is a sample board rather than the real ledger."""
    return _truthy(setting("LOOT_LEDGER_DEMO", "0"))


def _oidc_configured() -> bool:
    try:
        return bool(st.secrets.get("auth"))
    except Exception:
        return False


def mode() -> str:
    """Which gate applies: 'open', 'oidc' or 'password'."""
    # A sample board has nothing private in it, so a login would only stand
    # between a recruiter and the thing they were sent to look at.
    #
    # The flag alone is NOT enough to drop the gate. `demo.is_active()` reads
    # the marker written into the database when sample rows were generated, so
    # this asks "is what is actually in here generated?" rather than "was this
    # instance labelled a demo?". Otherwise setting LOOT_LEDGER_DEMO against a
    # real ledger — a stray environment variable, a copied launch command —
    # would quietly unlock real records instead of doing nothing.
    if is_demo() and demo.is_active():
        return "open"
    if _oidc_configured():
        return "oidc"
    if setting("LOOT_LEDGER_PASSWORD"):
        return "password"
    return "open"


def seed_demo_if_empty() -> None:
    """Give a sample instance something to show.

    Only ever fires when the ledger is completely empty, so it cannot add sample
    rows on top of real ones — and it is a no-op unless this instance was
    explicitly marked as a demo.
    """
    if not is_demo():
        return
    counts = db.row_counts()
    if sum(counts.values()) > 0:
        return
    demo.seed(3)


# --------------------------------------------------------------- the gate

def _sign_in_screen(body: str) -> None:
    """The whole page, when the page is not allowed to be the board yet."""
    st.markdown(
        "<div style='max-width:380px;margin:12vh auto 0;text-align:center'>"
        "<div style='font-family:system-ui;font-weight:800;letter-spacing:.08em;"
        "font-size:22px'>LOOT&nbsp;<span style='color:#f5a524'>&bull;</span>&nbsp;LEDGER</div>"
        f"<p style='opacity:.65;font-size:14px;margin:14px 0 20px'>{body}</p></div>",
        unsafe_allow_html=True)


def gate() -> None:
    """Stop the run before anything renders unless this viewer is allowed in.

    Called immediately after set_page_config so a failed check never paints a
    single figure. st.stop() ends the script run; nothing below it executes.
    """
    how = mode()
    if how == "open":
        return

    if how == "oidc":
        if not getattr(st.user, "is_logged_in", False):
            _sign_in_screen("This board holds real financial records. "
                            "Sign in to open it.")
            left, mid, right = st.columns([1, 1.2, 1])
            with mid:
                if st.button("Sign in", type="primary", width="stretch"):
                    st.login()
            st.stop()
        return

    # --- shared password ---
    if st.session_state.get("_access_granted"):
        return

    _sign_in_screen("This board holds real financial records. "
                    "Enter the password to open it.")
    left, mid, right = st.columns([1, 1.2, 1])
    with mid:
        with st.form("access_gate", clear_on_submit=False):
            given = st.text_input("Password", type="password",
                                  label_visibility="collapsed",
                                  placeholder="Password")
            if st.form_submit_button("Open board", type="primary",
                                     width="stretch"):
                # compare_digest, not ==, so the comparison does not leak the
                # length or the position of the first wrong character through
                # how long it takes to fail.
                if hmac.compare_digest(str(given), str(setting("LOOT_LEDGER_PASSWORD"))):
                    st.session_state._access_granted = True
                    st.rerun()
                else:
                    st.session_state._access_denied = True
        if st.session_state.get("_access_denied"):
            st.error("That is not the password.")
    st.stop()


def sign_out_control() -> None:
    """Rendered in Settings. Absent when there is nothing to sign out of."""
    how = mode()
    if how == "open":
        return
    st.divider()
    st.markdown("**Session**")
    if how == "oidc":
        who = getattr(st.user, "email", None) or "this account"
        st.caption(f"Signed in as {who}.")
        if st.button("Sign out", width="stretch", key="sign_out"):
            st.logout()
    else:
        st.caption("This board is password protected.")
        if st.button("Lock board", width="stretch", key="lock_board"):
            st.session_state._access_granted = False
            st.session_state._access_denied = False
            st.rerun()
