"""Sidebar: user, language, mode, word list, font and voice selection."""

from __future__ import annotations

import streamlit as st

from config import DEFAULT_ANSWER_STYLE
from core.words import discover_categories
from languages import LANGUAGES, get_lang_config
from srs import save_language, save_preferences
from utils.audio import list_macos_voices as _list_macos_voices


@st.cache_data(show_spinner=False)
def list_macos_voices(voice_prefix: str, default_voice: str) -> list[str]:
    return _list_macos_voices(voice_prefix, default_voice)


def render_sidebar(active_user: str) -> tuple[str, str, dict, str, str]:
    """Render the sidebar and return (mode, category, lang_config, target_font, voice)."""

    def _save_pref(key: str, value: str) -> None:
        """Persist a single UI preference for the active user."""
        prefs = st.session_state.get("user_prefs", {})
        if prefs.get(key) != value:
            prefs[key] = value
            st.session_state.user_prefs = prefs
            save_preferences(active_user, prefs)

    with st.sidebar:
        if active_user:
            st.caption(f"Ingelogd als **{active_user}**")
        else:
            st.caption("Anonieme sessie (niet opgeslagen)")
        if st.button("Wissel gebruiker", type="secondary"):
            st.session_state.current_user = None
            for key in list(st.session_state.keys()):
                if str(key).startswith("progress_"):
                    del st.session_state[key]
            st.rerun()

        st.markdown("---")

        # Language selection
        st.subheader("Taal")
        lang_options = list(LANGUAGES.keys())
        lang_labels = [f"{LANGUAGES[k]['flag']} {LANGUAGES[k]['name']}" for k in lang_options]
        current_lang_idx = lang_options.index(st.session_state.current_language)
        selected_lang_label = st.selectbox(
            "Taal", lang_labels, index=current_lang_idx, label_visibility="collapsed"
        )
        selected_lang = lang_options[lang_labels.index(selected_lang_label)]

        if selected_lang != st.session_state.current_language:
            st.session_state.current_language = selected_lang
            if active_user:
                save_language(active_user, selected_lang)
            for key in list(st.session_state.keys()):
                if str(key).startswith("progress_"):
                    del st.session_state[key]
            for key in ["question", "alpha_question", "current_category"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

        lang_config = get_lang_config(st.session_state.current_language)

        st.subheader("Oefenmodus")
        _saved_mode = st.session_state.get("user_prefs", {}).get("mode")
        _mode_index = lang_config["modes"].index(_saved_mode) if _saved_mode in lang_config["modes"] else 0
        mode = st.selectbox(
            "Oefenmodus",
            lang_config["modes"],
            index=_mode_index,
            label_visibility="collapsed",
        )
        _save_pref("mode", mode)

        st.subheader("Woordenlijst")
        categories = discover_categories(lang_config)
        _all_cats = ["Alle woorden"] + categories
        _saved_cat = st.session_state.get("user_prefs", {}).get("category")
        _cat_index = _all_cats.index(_saved_cat) if _saved_cat in _all_cats else 0
        category = st.selectbox(
            "Woordenlijst", _all_cats, index=_cat_index, label_visibility="collapsed"
        )
        _save_pref("category", category)

        _answer_styles = ["Meerkeuze", "Typen"]
        _default_style_idx = (
            _answer_styles.index(DEFAULT_ANSWER_STYLE) if DEFAULT_ANSWER_STYLE in _answer_styles else 0
        )
        _saved_style = st.session_state.get("user_prefs", {}).get("answer_style")
        _style_index = _answer_styles.index(_saved_style) if _saved_style in _answer_styles else _default_style_idx
        st.session_state.answer_style = st.radio(
            "Antwoordtype", _answer_styles, index=_style_index, horizontal=True
        )
        _save_pref("answer_style", st.session_state.answer_style)

        st.markdown("---")

        # Font selector (only for Arabic)
        if lang_config["direction"] == "rtl":
            st.subheader("Arabisch lettertype")
            _saved_font = st.session_state.get("user_prefs", {}).get("font")
            _font_index = lang_config["fonts"].index(_saved_font) if _saved_font in lang_config["fonts"] else 0
            target_font = st.selectbox(
                "Arabisch lettertype",
                lang_config["fonts"],
                index=_font_index,
                label_visibility="collapsed",
            )
            _save_pref("font", target_font)
        else:
            target_font = lang_config["fonts"][0]

        # Voice selector
        st.subheader(f"{lang_config['name']}e stem")
        all_voices = list_macos_voices(lang_config["voice_prefix"], lang_config["default_voice"])
        default_voice_index = 0
        if lang_config["default_voice"] in all_voices:
            default_voice_index = all_voices.index(lang_config["default_voice"])
        _saved_voice = st.session_state.get("user_prefs", {}).get("voice")
        _voice_index = all_voices.index(_saved_voice) if _saved_voice in all_voices else default_voice_index
        selected_voice = st.selectbox("Kies stem", all_voices, index=_voice_index)
        _save_pref("voice", selected_voice)

    return mode, category, lang_config, target_font, selected_voice
