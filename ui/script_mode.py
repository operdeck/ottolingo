"""Script / alphabet practice mode (Arabic letters, Japanese Hiragana)."""

from __future__ import annotations

import random
import time

import pandas as pd
import streamlit as st

from config import AUTO_ADVANCE_DELAY_CORRECT_SECONDS, MULTIPLE_CHOICE_DISTRACTORS
from utils.audio import macos_tts_audio


def build_alpha_question(letters_df: pd.DataFrame, lang_config: dict) -> dict:
    letter = letters_df.sample(1).iloc[0]
    letter_data = letter.to_dict()
    # For Arabic: transliteration column in alphabet is "transliteration"
    # For Japanese: it's "romaji"
    alpha_translit = "transliteration" if "transliteration" in letters_df.columns else "romaji"
    char_col = "isolated" if "isolated" in letters_df.columns else "character"

    has_positions = lang_config["alphabet_has_positions"]

    if has_positions:
        exercise_type = random.choice(["letter_to_sound", "sound_to_letter", "position"])
    else:
        exercise_type = random.choice(["letter_to_sound", "sound_to_letter"])

    if exercise_type == "letter_to_sound":
        correct = letter_data[alpha_translit]
        pool = [r[alpha_translit] for _, r in letters_df.iterrows() if r[alpha_translit] != correct]
        random.shuffle(pool)
        options = [correct] + pool[:MULTIPLE_CHOICE_DISTRACTORS]
        random.shuffle(options)
    elif exercise_type == "sound_to_letter":
        correct = letter_data[char_col]
        pool = [r[char_col] for _, r in letters_df.iterrows() if r[char_col] != correct]
        random.shuffle(pool)
        options = [correct] + pool[:MULTIPLE_CHOICE_DISTRACTORS]
        random.shuffle(options)
    else:
        positions = {"initial": "begin", "medial": "midden", "final": "eind"}
        pos_key = random.choice(list(positions.keys()))
        correct = letter_data[pos_key]
        pool = [r[pos_key] for _, r in letters_df.iterrows() if r[pos_key] != correct]
        random.shuffle(pool)
        options = [correct] + pool[:MULTIPLE_CHOICE_DISTRACTORS]
        random.shuffle(options)
        letter_data["_pos_key"] = pos_key
        letter_data["_pos_label"] = positions[pos_key]

    return {"letter": letter_data, "type": exercise_type, "correct": correct, "options": options}


def render(mode: str, lang_config: dict, target_font: str, selected_voice: str) -> None:
    """Render the alphabet/script practice screen and stop the run."""
    alphabet_dir = lang_config["data_dir"] / lang_config["alphabet_dir"]
    alphabet_files = list(alphabet_dir.glob("*.csv")) if alphabet_dir.exists() else []

    if not alphabet_files:
        st.error(f"{lang_config['alphabet_label']}bestand niet gevonden.")
        st.stop()

    letters_df = pd.read_csv(alphabet_files[0])

    if (
        "alpha_question" not in st.session_state
        or st.session_state.get("alpha_mode") != mode
    ):
        st.session_state.alpha_mode = mode
        st.session_state.alpha_answered = False
        st.session_state.alpha_question = build_alpha_question(letters_df, lang_config)

    aq = st.session_state.alpha_question
    letter_data = aq["letter"]
    correct = aq["correct"]
    options = aq["options"]

    char_col = "isolated" if "isolated" in letter_data else "character"
    alpha_translit = "transliteration" if "transliteration" in letter_data else "romaji"

    if aq["type"] in ("sound_to_letter", "position"):
        if lang_config["direction"] == "rtl":
            st.markdown(
                f"""<style>
section.main [data-testid="stRadio"] label p,
section.main [data-testid="stRadio"] label span,
section.main [data-testid="stRadio"] label div {{
    font-size: 2.75rem !important;
    font-family: '{target_font}', 'Amiri', serif !important;
    direction: rtl !important;
}}
</style>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""<style>
section.main [data-testid="stRadio"] label p,
section.main [data-testid="stRadio"] label span,
section.main [data-testid="stRadio"] label div {{
    font-size: 2.75rem !important;
    font-family: '{target_font}', 'Noto Sans JP', sans-serif !important;
}}
</style>""",
                unsafe_allow_html=True,
            )

    col_main, col_side = st.columns([2.0, 1.2], gap="large")
    with col_main:
        st.markdown(f"<span class='badge'>{lang_config['alphabet_label']} oefenen</span>", unsafe_allow_html=True)

        if aq["type"] == "letter_to_sound":
            st.markdown(f"<div class='target-text' style='font-size:4rem'>{letter_data[char_col]}</div>", unsafe_allow_html=True)
            st.markdown("<div class='prompt-title'>Welke klank hoort bij dit karakter?</div>", unsafe_allow_html=True)

        elif aq["type"] == "sound_to_letter":
            st.markdown(f"<div class='prompt-title'>Welk karakter maakt de klank: <b>{letter_data[alpha_translit]}</b> ({letter_data['name']})?</div>", unsafe_allow_html=True)

        else:  # position (Arabic only)
            pos_label = letter_data.get("_pos_label", "")
            st.markdown(f"<div class='prompt-title'>Hoe ziet <b>{letter_data['name']}</b> ({letter_data[char_col]}) eruit aan het <b>{pos_label}</b> van een woord?</div>", unsafe_allow_html=True)

        qid = st.session_state.get("alpha_qid", 0)
        selected = st.radio("Kies", options, index=None, key=f"alpha_{qid}", label_visibility="collapsed")

        alpha_trigger_auto_advance = False
        if selected:
            if aq["type"] == "sound_to_letter":
                speak_text = selected
            else:
                speak_text = letter_data[char_col]
            spoken_key = f"alpha_{qid}:{selected}"
            if st.session_state.get("alpha_last_spoken") != spoken_key:
                audio_payload = macos_tts_audio(speak_text, voice=selected_voice)
                if audio_payload:
                    audio_bytes, audio_format = audio_payload
                    st.audio(audio_bytes, format=audio_format, autoplay=True)
                    st.session_state.alpha_last_spoken = spoken_key
            if not st.session_state.get("alpha_answered"):
                is_correct = selected == correct
                st.session_state.alpha_answered = True
                st.session_state.alpha_last_result = is_correct
                if is_correct:
                    st.session_state.alpha_session_right = st.session_state.get("alpha_session_right", 0) + 1
                else:
                    st.session_state.alpha_session_wrong = st.session_state.get("alpha_session_wrong", 0) + 1
                alpha_trigger_auto_advance = is_correct

        if st.session_state.get("alpha_answered"):
            if st.session_state.get("alpha_last_result"):
                st.success("Goed gedaan!")
            else:
                if aq["type"] in ("sound_to_letter", "position") and lang_config["direction"] == "rtl":
                    correct_html = (
                        f'<span style="font-family: \'{target_font}\', \'Amiri\', serif;'
                        f' font-size: 2rem; direction: rtl; display: inline-block;">'
                        f'{correct}</span>'
                    )
                    st.markdown(
                        f'<div style="color:#7f1d1d; background-color:#fef2f2; border:1px solid #fca5a5;'
                        f' border-radius:8px; padding:0.75rem 1rem; margin:0.25rem 0;">'
                        f'❌ Niet goed. Correct was: {correct_html}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.error(f"Niet goed. Correct was: {correct}")
            if letter_data.get("comment"):
                st.info(f"💡 {letter_data['comment']}")

        if alpha_trigger_auto_advance and st.session_state.get("alpha_last_result"):
            delay = AUTO_ADVANCE_DELAY_CORRECT_SECONDS * 2 if letter_data.get("comment") else AUTO_ADVANCE_DELAY_CORRECT_SECONDS
            time.sleep(delay)
            st.session_state.alpha_question = build_alpha_question(letters_df, lang_config)
            st.session_state.alpha_answered = False
            st.session_state.alpha_qid = qid + 1
            st.rerun()

        if st.session_state.get("alpha_answered") and not st.session_state.get("alpha_last_result"):
            if st.button("Volgend karakter", key="alpha_next"):
                st.session_state.alpha_question = build_alpha_question(letters_df, lang_config)
                st.session_state.alpha_answered = False
                st.session_state.alpha_qid = qid + 1
                st.rerun()

    with col_side:
        st.subheader(f"{lang_config['alphabet_label']} overzicht")
        _s_right = st.session_state.get("alpha_session_right", 0)
        _s_wrong = st.session_state.get("alpha_session_wrong", 0)
        _s_total = _s_right + _s_wrong
        if _s_total > 0:
            _s_pct = round(100 * _s_right / _s_total)
            st.markdown(f"<div class='big-score'>{_s_pct}% goed</div>", unsafe_allow_html=True)
            st.write(f"Goed: {_s_right} | Fout: {_s_wrong}")
        display_cols = [char_col, "name", alpha_translit]
        rename_map = {char_col: "Karakter", "name": "Naam", alpha_translit: "Klank"}
        st.dataframe(
            letters_df[display_cols].rename(columns=rename_map),
            use_container_width=True,
            hide_index=True,
            height=400,
        )

    st.stop()
