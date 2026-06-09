"""Ottolingo — Streamlit entrypoint. Wires the UI modules together."""

from __future__ import annotations

import time

import streamlit as st

from config import (
    APP_TITLE,
    DEFAULT_LANGUAGE,
    DEFAULT_NEW_WORDS_PER_SESSION,
    REPO_URL,
    SESSION_TARGET_MINUTES,
)
from core.words import load_words
from languages import LANGUAGES
from srs import due_words, get_language, new_words
from ui import explore_mode, practice_mode, script_mode
from ui.login import render_login
from ui.sidebar import render_sidebar
from ui.state import ensure_stats_for_words, get_progress
from ui.styles import APP_CSS

st.set_page_config(page_title=APP_TITLE, page_icon="📘", layout="wide")
st.markdown(APP_CSS, unsafe_allow_html=True)

# --- Page header ---
col_hdr_title, col_hdr_right = st.columns([3, 2])
with col_hdr_title:
    st.title(APP_TITLE)

# --- User selection (stops the run until a user is chosen) ---
render_login()
active_user = st.session_state.current_user

# Load saved language preference
if "current_language" not in st.session_state:
    saved_lang = get_language(active_user) if active_user else ""
    st.session_state.current_language = saved_lang if saved_lang in LANGUAGES else DEFAULT_LANGUAGE

# --- Sidebar ---
mode, category, lang_config, target_font, selected_voice = render_sidebar(active_user)

# Load words
words_df = load_words(lang_config, category)
if words_df.empty:
    st.error("Geen woorden gevonden voor deze categorie.")
    st.stop()

ensure_stats_for_words(words_df)

progress = get_progress()
all_word_keys = words_df["dutch"].tolist()
due_list = due_words(progress, all_word_keys)
new_list = new_words(progress, all_word_keys)
streak_count = progress["streak"]["count"]

if "session_start" not in st.session_state:
    st.session_state.session_start = time.time()
elapsed_min = int((time.time() - st.session_state.session_start) / 60)
target_min = SESSION_TARGET_MINUTES
_today_text = (
    f"📚 {len(due_list)} te herhalen · ✨ {min(len(new_list), DEFAULT_NEW_WORDS_PER_SESSION)} nieuw"
    + (f" · 🔥 {streak_count}d" if streak_count > 0 else "")
    + f" · ⏱ {elapsed_min}/{target_min} min"
)
with col_hdr_right:
    st.progress(min(elapsed_min / target_min, 1.0), text=_today_text)
    st.link_button("GitHub ↗", REPO_URL, use_container_width=True)

# Dynamic font CSS for target language
if lang_config["direction"] == "rtl":
    st.markdown(
        f"""
<style>
.target-text {{
    font-family: '{target_font}', 'Amiri', serif !important;
    direction: rtl !important;
    text-align: right !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f"""
<style>
.target-text {{
    font-family: '{target_font}', 'Noto Sans JP', sans-serif !important;
    direction: ltr !important;
    text-align: left !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )

# --- Mode dispatch ---
mode_labels = lang_config["mode_labels"]

if mode == mode_labels["script"]:
    script_mode.render(mode, lang_config, target_font, selected_voice)

if mode == mode_labels.get("explore"):
    explore_mode.render(lang_config, target_font, selected_voice)

practice_mode.render(words_df, mode, category, lang_config, target_font, selected_voice)
