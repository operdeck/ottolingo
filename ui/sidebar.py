"""Sidebar: user, language, mode, word list, font and voice selection."""

from __future__ import annotations

import streamlit as st

from config import DEFAULT_ANSWER_STYLE
from core.words import discover_categories
from languages import LANGUAGES, get_lang_config
from srs import save_language
from utils.audio import list_macos_voices as _list_macos_voices


@st.cache_data(show_spinner=False)
def list_macos_voices(voice_prefix: str, default_voice: str) -> list[str]:
    return _list_macos_voices(voice_prefix, default_voice)


def render_sidebar(active_user: str) -> tuple[str, str, dict, str, str]:
    """Render the sidebar and return (mode, category, lang_config, target_font, voice)."""
    with st.sidebar:
        if active_user:
            st.caption(f"Ingelogd als **{active_user}**")
        else:
            st.caption("Anonieme sessie (niet opgeslagen)")
        if st.button("Wissel gebruiker", type="tertiary"):
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
        mode = st.selectbox(
            "Oefenmodus",
            lang_config["modes"],
            label_visibility="collapsed",
        )

        st.subheader("Woordenlijst")
        categories = discover_categories(lang_config)
        category = st.selectbox(
            "Woordenlijst", ["Alle woorden"] + categories, label_visibility="collapsed"
        )

        _answer_styles = ["Meerkeuze", "Typen"]
        _default_style_idx = (
            _answer_styles.index(DEFAULT_ANSWER_STYLE) if DEFAULT_ANSWER_STYLE in _answer_styles else 0
        )
        st.session_state.answer_style = st.radio(
            "Antwoordtype", _answer_styles, index=_default_style_idx, horizontal=True
        )

        st.markdown("---")

        # Font selector (only for Arabic)
        if lang_config["direction"] == "rtl":
            st.subheader("Arabisch lettertype")
            target_font = st.selectbox(
                "Arabisch lettertype",
                lang_config["fonts"],
                label_visibility="collapsed",
            )
        else:
            target_font = lang_config["fonts"][0]

        # Voice selector
        st.subheader(f"{lang_config['name']}e stem")
        all_voices = list_macos_voices(lang_config["voice_prefix"], lang_config["default_voice"])
        default_voice_index = 0
        if lang_config["default_voice"] in all_voices:
            default_voice_index = all_voices.index(lang_config["default_voice"])
        selected_voice = st.selectbox("Kies stem", all_voices, index=default_voice_index)

    return mode, category, lang_config, target_font, selected_voice
