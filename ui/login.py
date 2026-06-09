"""Login / user-selection screen."""

from __future__ import annotations

import streamlit as st

from srs import list_users


def render_login() -> None:
    """Show the user-selection screen. Calls ``st.stop()`` until a user is set."""
    if "current_user" not in st.session_state:
        st.session_state.current_user = None

    if st.session_state.current_user is not None:
        return

    known_users = list_users()

    name = st.text_input("Wie ben je?", placeholder="Typ je naam (nieuw of bestaand)")

    if known_users:
        st.caption("Of kies een bestaande:")
        for i, user in enumerate(known_users):
            if st.button(user, key=f"user_{i}"):
                st.session_state.current_user = user
                st.rerun()

    col_start, col_anon = st.columns(2)
    if col_start.button("Start", type="primary", disabled=not name.strip()):
        st.session_state.current_user = name.strip()
        st.rerun()
    if col_anon.button("Anoniem (niet opslaan)"):
        st.session_state.current_user = ""
        st.rerun()

    st.stop()
