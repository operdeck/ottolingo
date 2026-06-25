"""Session- and progress-coupled helpers (streamlit + st.session_state).

These wrap the pure SRS/question logic with Streamlit session state. They live
in ``ui`` (not ``core``) because they touch ``st.session_state``.
"""

from __future__ import annotations

import random
from datetime import date

import pandas as pd
import streamlit as st

from config import DEFAULT_ANSWER_STYLE, DEFAULT_LANGUAGE, DEFAULT_NEW_WORDS_PER_SESSION
from core.questions import pick_confusable_options
from srs import (
    due_words,
    get_word_state,
    load_progress_for_language,
    new_words,
    save_progress_for_language,
    sm2_update,
    update_streak,
)
from utils.text import normalize


def get_progress() -> dict:
    user = st.session_state.get("current_user", "")
    language = st.session_state.get("current_language", DEFAULT_LANGUAGE)
    cache_key = f"progress_{user}_{language}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = load_progress_for_language(user, language)
    return st.session_state[cache_key]


def get_stats() -> dict[str, dict[str, int]]:
    progress = get_progress()
    stats = {}
    for key, state in progress["words"].items():
        stats[key] = {"right": state["right"], "wrong": state["wrong"]}
    return stats


def ensure_stats_for_words(df: pd.DataFrame) -> None:
    progress = get_progress()
    for key in df["dutch"].tolist():
        get_word_state(progress, key)


def get_confusions() -> dict[str, dict[str, int]]:
    progress = get_progress()
    confusions = {}
    for key, state in progress["words"].items():
        if state.get("confusions"):
            confusions[key] = state["confusions"]
    return confusions


def record_confusion(word_key: str, confused_with: str) -> None:
    progress = get_progress()
    state = get_word_state(progress, word_key)
    if "confusions" not in state:
        state["confusions"] = {}
    state["confusions"][confused_with] = state["confusions"].get(confused_with, 0) + 1
    save_progress_for_language(progress)


def update_stats(word_key: str, correct: bool) -> None:
    progress = get_progress()
    state = get_word_state(progress, word_key)
    quality = 4 if correct else 1
    sm2_update(state, quality)
    update_streak(progress, date.today().isoformat())
    save_progress_for_language(progress)


def weighted_pick(df: pd.DataFrame) -> pd.Series:
    progress = get_progress()
    rows = df.to_dict("records")
    all_keys = [r["dutch"] for r in rows]

    due = set(due_words(progress, all_keys))
    new_pool = set(new_words(progress, all_keys))

    max_new = st.session_state.get("new_words_budget", DEFAULT_NEW_WORDS_PER_SESSION)
    new_introduced = st.session_state.get("new_introduced_today", 0)

    weights = []
    for row in rows:
        key = row["dutch"]
        state = get_word_state(progress, key)

        if key in due:
            total = state["right"] + state["wrong"]
            error_rate = state["wrong"] / max(total, 1)
            w = 5.0 + error_rate * 5.0
        elif key in new_pool and new_introduced < max_new:
            w = 2.0
        elif key in new_pool:
            w = 0.1
        else:
            w = 0.5
        weights.append(w)

    if st.session_state.get("last_word"):
        for i, row in enumerate(rows):
            if row["dutch"] == st.session_state.last_word and len(rows) > 1:
                weights[i] = max(0.05, weights[i] * 0.1)

    chosen = random.choices(rows, weights=weights, k=1)[0]
    st.session_state.last_word = chosen["dutch"]

    if chosen["dutch"] in new_pool:
        st.session_state.new_introduced_today = new_introduced + 1

    return pd.Series(chosen)


def build_question(df: pd.DataFrame, mode: str, lang_config: dict) -> dict:
    answer_style = st.session_state.get("answer_style", DEFAULT_ANSWER_STYLE)
    row = weighted_pick(df)
    target_col = lang_config["target_col"]
    translit_col = lang_config["translit_col"]
    lang_name = lang_config["name"]

    mode_labels = lang_config["mode_labels"]

    # For combined mode, randomly pick a direction
    if mode == mode_labels.get("combined"):
        effective_mode = random.choice([mode_labels["to_target"], mode_labels["to_dutch"]])
    else:
        effective_mode = mode

    if effective_mode == mode_labels["to_target"]:
        pool = [x for x in df[target_col].tolist() if x != row[target_col]]
        distractors = pick_confusable_options(row[target_col], pool, get_confusions(), row["dutch"])
        options = [row[target_col]] + distractors
        random.shuffle(options)
        return {
            "mode": effective_mode,
            "sidebar_mode": mode,
            "prompt": f"Wat is het {lang_name} voor: {row['dutch']}?",
            "prompt_target": "",
            "correct": row[target_col],
            "accepted": [normalize(row[target_col])] + ([normalize(row[translit_col])] if translit_col else []),
            "options": options,
            "word_key": row["dutch"],
            "meta": row.to_dict(),
            "answer_style": answer_style,
        }

    if effective_mode == mode_labels["to_dutch"]:
        pool = [x for x in df["dutch"].tolist() if x != row["dutch"]]
        distractors = pick_confusable_options(row["dutch"], pool, get_confusions(), row["dutch"])
        options = [row["dutch"]] + distractors
        random.shuffle(options)
        return {
            "mode": effective_mode,
            "sidebar_mode": mode,
            "prompt": f"Welk Nederlands woord hoort bij dit {lang_name}e woord?",
            "prompt_target": row[target_col],
            "correct": row["dutch"],
            "accepted": [normalize(row["dutch"])],
            "options": options,
            "word_key": row["dutch"],
            "meta": row.to_dict(),
            "answer_style": answer_style,
        }

    return {}
