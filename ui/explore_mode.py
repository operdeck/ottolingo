"""Zoek & Oefen (explore) mode: search words and drill thematic groups."""

from __future__ import annotations

import random
import time

import streamlit as st

from config import AUTO_ADVANCE_DELAY_CORRECT_SECONDS, DEFAULT_ANSWER_STYLE
from core.questions import grade_answer, pick_confusable_options
from core.words import load_words
from groups import find_groups_for_word, get_all_groups
from ui.state import ensure_stats_for_words, get_confusions, record_confusion, update_stats
from utils.audio import macos_tts_audio
from utils.text import normalize


def render(lang_config: dict, target_font: str, selected_voice: str) -> None:
    """Render the explore screen (search + drill phases) and stop the run."""
    # Always use the full word list for explore mode, regardless of category selection.
    all_words_df = load_words(lang_config, "Alle woorden")
    ensure_stats_for_words(all_words_df)

    target_col = lang_config["target_col"]
    translit_col = lang_config["translit_col"]
    mode_labels = lang_config["mode_labels"]

    groups = get_all_groups(lang_config, all_words_df)

    # Reset explore state when language changes.
    if st.session_state.get("explore_language") != st.session_state.current_language:
        for _k in [
            "explore_phase", "explore_drill_words", "explore_group_label",
            "explore_drill_plan", "explore_drill_qidx", "explore_drill_answered",
            "explore_drill_question", "explore_drill_qidx_built", "explore_drill_results",
            "explore_search",
        ]:
            st.session_state.pop(_k, None)
        st.session_state.explore_language = st.session_state.current_language

    if "explore_phase" not in st.session_state:
        st.session_state.explore_phase = "search"

    # ── DRILL PHASE ────────────────────────────────────────────────────────────
    if st.session_state.explore_phase == "drill":
        drill_words = st.session_state.get("explore_drill_words", [])
        group_label = st.session_state.get("explore_group_label", "")
        drill_df = all_words_df[all_words_df["dutch"].isin(drill_words)].reset_index(drop=True)

        if drill_df.empty:
            st.warning("Geen woorden gevonden voor deze groep.")
            st.session_state.explore_phase = "search"
            st.rerun()

        # Build a randomised plan of (word, direction) pairs once per drill session.
        if "explore_drill_plan" not in st.session_state:
            words_shuffled = drill_df["dutch"].tolist()
            random.shuffle(words_shuffled)
            drill_plan = [
                {
                    "dutch": dutch,
                    "direction": mode_labels["to_target"] if i % 2 == 0 else mode_labels["to_dutch"],
                }
                for i, dutch in enumerate(words_shuffled)
            ]
            st.session_state.explore_drill_plan = drill_plan
            st.session_state.explore_drill_qidx = 0
            st.session_state.explore_drill_results = []

        drill_plan = st.session_state.explore_drill_plan
        total_q = len(drill_plan)
        qidx = st.session_state.get("explore_drill_qidx", 0)

        col_main, col_side = st.columns([2.0, 1.2], gap="large")

        with col_main:
            st.markdown(
                f"<span class='badge'>Zoek & Oefen — {group_label}</span>",
                unsafe_allow_html=True,
            )
            st.progress(min(qidx / max(total_q, 1), 1.0), text=f"Vraag {min(qidx + 1, total_q)} van {total_q}")

            if st.button("← Terug naar zoeken", type="secondary"):
                st.session_state.explore_phase = "search"
                for _k in ["explore_drill_plan", "explore_drill_qidx", "explore_drill_answered",
                           "explore_drill_question", "explore_drill_qidx_built", "explore_drill_results"]:
                    st.session_state.pop(_k, None)
                st.rerun()

            # ── Summary screen ─────────────────────────────────────────────
            if qidx >= total_q:
                results = st.session_state.get("explore_drill_results", [])
                n_right = sum(1 for r in results if r)
                n_wrong = len(results) - n_right
                pct = round(100 * n_right / max(len(results), 1))
                st.markdown(
                    f"<div class='big-score'>Klaar! {pct}% goed</div>",
                    unsafe_allow_html=True,
                )
                st.write(f"Goed: {n_right} | Fout: {n_wrong}")
                if st.button("Opnieuw oefenen", type="primary"):
                    for _k in ["explore_drill_plan", "explore_drill_qidx", "explore_drill_answered",
                               "explore_drill_question", "explore_drill_qidx_built", "explore_drill_results"]:
                        st.session_state.pop(_k, None)
                    st.rerun()

            else:
                # ── Active question ─────────────────────────────────────────
                step = drill_plan[qidx]
                drill_mode = step["direction"]

                # Build question for the specific word at this step.
                if (
                    "explore_drill_question" not in st.session_state
                    or st.session_state.get("explore_drill_qidx_built") != qidx
                ):
                    row_matches = drill_df[drill_df["dutch"] == step["dutch"]]
                    row = row_matches.iloc[0] if not row_matches.empty else drill_df.iloc[0]

                    if drill_mode == mode_labels["to_target"]:
                        pool = [x for x in drill_df[target_col].tolist() if x != row[target_col]]
                        distractors = pick_confusable_options(row[target_col], pool, get_confusions(), row["dutch"])
                        options = [row[target_col]] + distractors
                        random.shuffle(options)
                        eq = {
                            "mode": drill_mode,
                            "prompt": f"Wat is het {lang_config['name']} voor: {row['dutch']}?",
                            "prompt_target": "",
                            "correct": row[target_col],
                            "accepted": [normalize(row[target_col]), normalize(row[translit_col])],
                            "options": options,
                            "word_key": row["dutch"],
                            "meta": row.to_dict(),
                            "answer_style": st.session_state.get("answer_style", DEFAULT_ANSWER_STYLE),
                        }
                    else:
                        pool = [x for x in drill_df["dutch"].tolist() if x != row["dutch"]]
                        distractors = pick_confusable_options(row["dutch"], pool, get_confusions(), row["dutch"])
                        options = [row["dutch"]] + distractors
                        random.shuffle(options)
                        eq = {
                            "mode": drill_mode,
                            "prompt": f"Welk Nederlands woord hoort bij dit {lang_config['name']}e woord?",
                            "prompt_target": row[target_col],
                            "correct": row["dutch"],
                            "accepted": [normalize(row["dutch"])],
                            "options": options,
                            "word_key": row["dutch"],
                            "meta": row.to_dict(),
                            "answer_style": st.session_state.get("answer_style", DEFAULT_ANSWER_STYLE),
                        }
                    st.session_state.explore_drill_question = eq
                    st.session_state.explore_drill_qidx_built = qidx
                    st.session_state.explore_drill_answered = False

                eq = st.session_state.explore_drill_question

                st.markdown(f"<div class='prompt-title'>{eq['prompt']}</div>", unsafe_allow_html=True)
                if eq.get("prompt_target"):
                    st.markdown(
                        f"<div class='target-text'>{eq['prompt_target']}</div>",
                        unsafe_allow_html=True,
                    )

                if drill_mode == mode_labels["to_dutch"]:
                    audio_payload = macos_tts_audio(eq["meta"][target_col], voice=selected_voice)
                    if audio_payload:
                        audio_bytes, audio_format = audio_payload
                        st.audio(audio_bytes, format=audio_format)

                trigger_advance = False

                if eq["answer_style"] == "Meerkeuze":
                    # Apply the same large-font CSS for target-language options as the regular practice mode
                    if drill_mode == mode_labels["to_target"]:
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
                    selected_ans = st.radio(
                        "Kies je antwoord",
                        eq["options"],
                        index=None,
                        key=f"expl_mc_{qidx}",
                        label_visibility="collapsed",
                    )
                    if drill_mode == mode_labels["to_target"] and selected_ans:
                        spoken_key = f"expl_{qidx}:{selected_ans}"
                        if st.session_state.get("expl_last_spoken") != spoken_key:
                            audio_payload = macos_tts_audio(selected_ans, voice=selected_voice)
                            if audio_payload:
                                audio_bytes, audio_format = audio_payload
                                st.audio(audio_bytes, format=audio_format, autoplay=True)
                                st.session_state.expl_last_spoken = spoken_key

                    if st.button(
                        "Controleer",
                        type="primary",
                        disabled=st.session_state.get("explore_drill_answered", False),
                        key=f"expl_check_{qidx}",
                    ):
                        if selected_ans is None:
                            st.warning("Kies eerst een antwoord.")
                        else:
                            is_correct = selected_ans == eq["correct"]
                            update_stats(eq["word_key"], is_correct)
                            if not is_correct:
                                record_confusion(eq["word_key"], selected_ans)
                            st.session_state.explore_drill_answered = True
                            st.session_state.explore_drill_last_result = is_correct
                            results = st.session_state.get("explore_drill_results", [])
                            results.append(is_correct)
                            st.session_state.explore_drill_results = results
                            trigger_advance = is_correct
                else:
                    typed = st.text_input(
                        "Typ je antwoord",
                        placeholder="Type hier",
                        key=f"expl_typed_{qidx}",
                    )
                    if st.button(
                        "Controleer",
                        type="primary",
                        disabled=st.session_state.get("explore_drill_answered", False),
                        key=f"expl_check_{qidx}",
                    ):
                        if not typed.strip():
                            st.warning("Typ eerst een antwoord.")
                        else:
                            is_correct = grade_answer(eq, typed)
                            update_stats(eq["word_key"], is_correct)
                            st.session_state.explore_drill_answered = True
                            st.session_state.explore_drill_last_result = is_correct
                            results = st.session_state.get("explore_drill_results", [])
                            results.append(is_correct)
                            st.session_state.explore_drill_results = results
                            trigger_advance = is_correct

                if st.session_state.get("explore_drill_answered"):
                    if st.session_state.get("explore_drill_last_result"):
                        st.success("Goed gedaan!")
                    else:
                        translit = eq["meta"].get(translit_col, "")
                        if lang_config["direction"] == "rtl" and drill_mode == mode_labels["to_target"]:
                            correct_html = (
                                f'<span style="font-family: \'{target_font}\', \'Amiri\', serif;'
                                f' font-size: 1.4rem; direction: rtl; display: inline-block;">'
                                f'{eq["correct"]}</span>'
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
                                f"Niet goed. Correct was: {eq['correct']}"
                                + (f" ({translit})" if translit else "")
                            )
                    comment = eq["meta"].get("comment", "")
                    if comment:
                        st.info(f"💡 {comment}")
                    example = eq["meta"].get("example", "")
                    if example:
                        example_nl = eq["meta"].get("example_nl", "")
                        ex_text = f"📝 {example}"
                        if example_nl:
                            ex_text += f" — {example_nl}"
                        st.caption(ex_text)

                if trigger_advance and st.session_state.get("explore_drill_answered") and st.session_state.get("explore_drill_last_result"):
                    time.sleep(AUTO_ADVANCE_DELAY_CORRECT_SECONDS)
                    st.session_state.explore_drill_qidx = qidx + 1
                    for _k in ["explore_drill_question", "explore_drill_qidx_built", "explore_drill_answered"]:
                        st.session_state.pop(_k, None)
                    st.rerun()

                if st.session_state.get("explore_drill_answered") and not st.session_state.get("explore_drill_last_result"):
                    if st.button("Volgend woord", key=f"expl_next_{qidx}"):
                        st.session_state.explore_drill_qidx = qidx + 1
                        for _k in ["explore_drill_question", "explore_drill_qidx_built", "explore_drill_answered"]:
                            st.session_state.pop(_k, None)
                        st.rerun()

        with col_side:
            st.subheader("Groep")
            st.write(f"**{group_label}**")
            st.caption(f"{total_q} vragen")
            for w in drill_words[:25]:
                st.write(f"• {w}")
            if len(drill_words) > 25:
                st.caption(f"… en {len(drill_words) - 25} meer")

        st.stop()

    # ── SEARCH PHASE ────────────────────────────────────────────────────────────
    col_main, col_side = st.columns([2.0, 1.2], gap="large")

    with col_main:
        st.markdown("<span class='badge'>Zoek & Oefen</span>", unsafe_allow_html=True)
        st.markdown(
            "<div class='prompt-title'>Zoek een woord of blader door thema's</div>",
            unsafe_allow_html=True,
        )

        search_query = st.text_input(
            "Zoek",
            value=st.session_state.get("explore_search", ""),
            placeholder="Type een Nederlands woord…",
            label_visibility="collapsed",
            key="explore_search_input",
        )
        st.session_state.explore_search = search_query

        if search_query.strip():
            q_lower = search_query.strip().lower()
            matches = all_words_df[
                all_words_df["dutch"].str.lower().str.contains(q_lower, na=False, regex=False)
            ]

            if matches.empty:
                st.info(f"Geen woorden gevonden voor '{search_query}'.")
                all_dutch = all_words_df["dutch"].tolist()
                close = [w for w in all_dutch if q_lower[:3] in w.lower() or w.lower()[:3] == q_lower[:3]]
                if close:
                    st.caption("Misschien bedoel je: " + " · ".join(close[:6]))
            else:
                for _, row in matches.head(5).iterrows():
                    dutch_word = str(row["dutch"])
                    target_word = str(row[target_col])
                    translit = str(row.get(translit_col, "") or "")
                    comment = str(row.get("comment", "") or "")

                    word_groups = find_groups_for_word(dutch_word, groups)

                    with st.container(border=True):
                        c1, c2 = st.columns([1, 1])
                        with c1:
                            st.markdown(f"**{dutch_word}**")
                            if comment:
                                st.caption(comment)
                        with c2:
                            if lang_config["direction"] == "rtl":
                                st.markdown(
                                    f"<div class='target-text' style='font-size:1.8rem; text-align:right'>{target_word}</div>",
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.markdown(
                                    f"<div class='target-text' style='font-size:1.8rem'>{target_word}</div>",
                                    unsafe_allow_html=True,
                                )
                            if translit:
                                st.caption(translit)

                        if word_groups:
                            badges = " ".join(
                                f"<span class='badge'>{groups[gk]['label']}</span>"
                                for gk in word_groups
                            )
                            st.markdown(badges, unsafe_allow_html=True)

                        example = str(row.get("example", "") or "")
                        if example:
                            example_nl = str(row.get("example_nl", "") or "")
                            ex_text = f"📝 {example}"
                            if example_nl:
                                ex_text += f" — {example_nl}"
                            st.caption(ex_text)

                        if word_groups:
                            btn_cols = st.columns(min(len(word_groups), 3))
                            for i, gk in enumerate(word_groups[:3]):
                                with btn_cols[i]:
                                    if st.button(
                                        f"Oefen: {groups[gk]['label']}",
                                        key=f"drill_{dutch_word}_{gk}",
                                        use_container_width=True,
                                    ):
                                        st.session_state.explore_phase = "drill"
                                        st.session_state.explore_drill_words = groups[gk]["words"]
                                        st.session_state.explore_group_label = groups[gk]["label"]
                                        for _k in ["explore_drill_plan", "explore_drill_qidx", "explore_drill_answered",
                                                   "explore_drill_question", "explore_drill_qidx_built", "explore_drill_results"]:
                                            st.session_state.pop(_k, None)
                                        st.rerun()
        else:
            st.caption("Voer een zoekterm in om een woord op te zoeken, of kies een thema hieronder.")

    with col_side:
        st.subheader("Thema's")
        for gk, group in groups.items():
            label = group["label"]
            n_words = len(group["words"])
            if st.button(f"{label} ({n_words})", key=f"group_btn_{gk}", use_container_width=True):
                st.session_state.explore_phase = "drill"
                st.session_state.explore_drill_words = group["words"]
                st.session_state.explore_group_label = label
                for _k in ["explore_drill_plan", "explore_drill_qidx", "explore_drill_answered",
                           "explore_drill_question", "explore_drill_qidx_built", "explore_drill_results"]:
                    st.session_state.pop(_k, None)
                st.rerun()

    st.stop()
