"""Word practice mode (Nederlands ↔ doeltaal, multiple choice or typing)."""

from __future__ import annotations

import time

import pandas as pd
import streamlit as st

from config import AUTO_ADVANCE_DELAY_CORRECT_SECONDS
from core.questions import grade_answer
from ui.state import build_question, get_stats, record_confusion, update_stats
from utils.audio import macos_tts_audio


def render(
    words_df: pd.DataFrame,
    mode: str,
    category: str,
    lang_config: dict,
    target_font: str,
    selected_voice: str,
) -> None:
    """Render the main word-practice screen."""
    mode_labels = lang_config["mode_labels"]

    if (
        "question" not in st.session_state
        or st.session_state.get("question", {}).get("mode") != mode
        or st.session_state.get("question", {}).get("answer_style") != st.session_state.answer_style
        or st.session_state.get("current_category") != category
    ):
        st.session_state.question = build_question(words_df, mode, lang_config)
        st.session_state.answered = False
        st.session_state.current_category = category

    question = st.session_state.question

    if mode == mode_labels["to_target"]:
        if lang_config["direction"] == "rtl":
            st.markdown(
                f"""
<style>
[data-testid="stMain"] [data-testid="stRadio"] label p,
[data-testid="stMain"] [data-testid="stRadio"] label span,
[data-testid="stMain"] [data-testid="stRadio"] label div {{
    font-size: 2.25rem !important;
    direction: rtl !important;
    text-align: right !important;
    font-family: '{target_font}', 'Amiri', 'Manrope', sans-serif !important;
}}
</style>
""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
<style>
[data-testid="stMain"] [data-testid="stRadio"] label p,
[data-testid="stMain"] [data-testid="stRadio"] label span,
[data-testid="stMain"] [data-testid="stRadio"] label div {{
    font-size: 2.25rem !important;
    font-family: '{target_font}', 'Noto Sans JP', 'Manrope', sans-serif !important;
}}
</style>
""",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            """
<style>
[data-testid="stMain"] [data-testid="stRadio"] label p,
[data-testid="stMain"] [data-testid="stRadio"] label span,
[data-testid="stMain"] [data-testid="stRadio"] label div {
    font-size: 1.35rem !important;
    direction: ltr !important;
    text-align: left !important;
}
</style>
""",
            unsafe_allow_html=True,
        )

    col_main, col_side = st.columns([2.0, 1.2], gap="large")

    with col_main:
        st.markdown(f"<span class='badge'>{question['mode']}</span>", unsafe_allow_html=True)
        st.markdown(f"<div class='prompt-title'>{question['prompt']}</div>", unsafe_allow_html=True)

        if question.get("prompt_target"):
            st.markdown(f"<div class='target-text'>{question['prompt_target']}</div>", unsafe_allow_html=True)

        qid = st.session_state.get("qid", 0)

        target_col = lang_config["target_col"]

        if mode == mode_labels["to_dutch"]:
            audio_payload = macos_tts_audio(question["meta"][target_col], voice=selected_voice)
            if audio_payload:
                audio_bytes, audio_format = audio_payload
                st.audio(audio_bytes, format=audio_format)

            # Show split characters (useful for Arabic and Japanese)
            if st.button("Toon losse tekens", key=f"split_{qid}"):
                target_word = question["meta"][target_col]
                # Split by word first to preserve word boundaries, then split each word into characters
                words_list = target_word.split()
                spaced_words = [" ".join(w) for w in words_list]
                spaced = "  /  ".join(spaced_words)
                st.markdown(f"<div class='target-text'>{spaced}</div>", unsafe_allow_html=True)

        trigger_auto_advance = False

        if question["answer_style"] == "Meerkeuze":
            st.markdown("<div class='answer-label'>Kies je antwoord</div>", unsafe_allow_html=True)
            selected = st.radio(
                "Kies je antwoord",
                question["options"],
                index=None,
                key=f"choice_{qid}",
                label_visibility="collapsed",
            )

            if mode == mode_labels["to_target"] and selected:
                spoken_key = f"{qid}:{selected}"
                if st.session_state.get("last_spoken_choice") != spoken_key:
                    audio_payload = macos_tts_audio(selected, voice=selected_voice)
                    if audio_payload:
                        audio_bytes, audio_format = audio_payload
                        st.audio(audio_bytes, format=audio_format, autoplay=True)
                        st.session_state.last_spoken_choice = spoken_key

            if st.button("Controleer", type="primary", disabled=st.session_state.answered):
                if selected is None:
                    st.warning("Kies eerst een antwoord.")
                else:
                    is_correct = selected == question["correct"]
                    update_stats(question["word_key"], is_correct)
                    if not is_correct:
                        record_confusion(question["word_key"], selected)
                    st.session_state.answered = True
                    st.session_state.last_result = is_correct
                    trigger_auto_advance = True
        else:
            typed = st.text_input(
                "Typ je antwoord",
                placeholder="Type hier",
                key=f"typed_{qid}",
            )

            if st.button("Controleer", type="primary", disabled=st.session_state.answered):
                if not typed.strip():
                    st.warning("Typ eerst een antwoord.")
                else:
                    is_correct = grade_answer(question, typed)
                    update_stats(question["word_key"], is_correct)
                    st.session_state.answered = True
                    st.session_state.last_result = is_correct
                    trigger_auto_advance = True

        if st.session_state.get("answered"):
            if st.session_state.get("last_result"):
                st.success("Goed gedaan!")
            else:
                translit = question["meta"].get(lang_config["translit_col"], "")
                if lang_config["direction"] == "rtl" and mode == mode_labels["to_target"]:
                    correct_html = (
                        f'<span style="font-family: \'{target_font}\', \'Amiri\', serif;'
                        f' font-size: 1.4rem; direction: rtl; display: inline-block;">'
                        f'{question["correct"]}</span>'
                    )
                    translit_part = f" ({translit})" if translit else ""
                    st.markdown(
                        f'<div style="color:#7f1d1d; background-color:#fef2f2; border:1px solid #fca5a5;'
                        f' border-radius:8px; padding:0.75rem 1rem; margin:0.25rem 0;">'
                        f'❌ Niet goed. Correct was: {correct_html}{translit_part}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.error(
                        f"Niet goed. Correct was: {question['correct']} ({translit})"
                    )
            comment = question["meta"].get("comment", "")
            if comment:
                st.info(f"💡 {comment}")
            root = question["meta"].get("root", "")
            if root:
                related = words_df[words_df["root"] == root]
                if len(related) > 1:
                    others = related[related["dutch"] != question["word_key"]]
                    if not others.empty:
                        family = " · ".join(f"{r[target_col]} ({r['dutch']})" for _, r in others.iterrows())
                        st.caption(f"Wortel [{root}]: {family}")
            example = question["meta"].get("example", "")
            if example:
                example_nl = question["meta"].get("example_nl", "")
                ex_text = f"📝 {example}"
                if example_nl:
                    ex_text += f" — {example_nl}"
                st.caption(ex_text)

        if st.session_state.get("answered") and trigger_auto_advance and st.session_state.get("last_result"):
            has_extra_info = bool(
                question["meta"].get("comment")
                or question["meta"].get("example")
                or question["meta"].get("root")
            )
            delay_seconds = AUTO_ADVANCE_DELAY_CORRECT_SECONDS * 2 if has_extra_info else AUTO_ADVANCE_DELAY_CORRECT_SECONDS
            time.sleep(delay_seconds)
            st.session_state.question = build_question(words_df, mode, lang_config)
            st.session_state.answered = False
            st.session_state.qid = st.session_state.get("qid", 0) + 1
            st.rerun()

        if st.button("Volgend woord"):
            st.session_state.question = build_question(words_df, mode, lang_config)
            st.session_state.answered = False
            st.session_state.qid = st.session_state.get("qid", 0) + 1
            st.rerun()

    with col_side:
        st.subheader("Jouw voortgang")
        _current_keys = set(words_df["dutch"].tolist())
        _show_all = st.toggle("Alle woorden", value=False, key="voortgang_show_all")
        stats = get_stats()
        if not _show_all:
            stats = {k: v for k, v in stats.items() if k in _current_keys}

        total_right = sum(v["right"] for v in stats.values())
        total_wrong = sum(v["wrong"] for v in stats.values())
        total = total_right + total_wrong

        if total > 0:
            accuracy = (100 * total_right) / total
            st.markdown(f"<div class='big-score'>{accuracy:.0f}% goed</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='big-score'>Nog geen score</div>", unsafe_allow_html=True)

        st.write(f"Goed: {total_right} | Fout: {total_wrong}")

        leaderboard = []
        for word, data in stats.items():
            attempts = data["right"] + data["wrong"]
            if attempts == 0:
                continue
            leaderboard.append(
                {
                    "woord": word,
                    "fouten": data["wrong"],
                    "pogingen": attempts,
                    "succes%": round((100 * data["right"]) / attempts),
                }
            )

        if leaderboard:
            board_df = (
                pd.DataFrame(leaderboard)
                .sort_values(
                    by=["succes%", "fouten", "pogingen", "woord"],
                    ascending=[True, False, False, True],
                    kind="mergesort",
                )
                .reset_index(drop=True)
            )
            st.dataframe(board_df, use_container_width=True, hide_index=True)
        else:
            st.caption("Maak je eerste oefening om statistieken te zien.")
