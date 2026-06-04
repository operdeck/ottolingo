from __future__ import annotations

import hashlib
import random
import subprocess
import tempfile
import time
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from config import (
    APP_TITLE,
    AUTO_ADVANCE_DELAY_CORRECT_SECONDS,
    DEFAULT_ANSWER_STYLE,
    DEFAULT_LANGUAGE,
    DEFAULT_NEW_WORDS_PER_SESSION,
    MULTIPLE_CHOICE_DISTRACTORS,
    REPO_URL,
    SESSION_TARGET_MINUTES,
)
from groups import find_groups_for_word, get_all_groups
from languages import LANGUAGES, get_lang_config
from srs import (
    due_words,
    get_language,
    get_word_state,
    is_due,
    is_new,
    list_users,
    load_progress_for_language,
    new_words,
    save_language,
    save_progress_for_language,
    sm2_update,
    update_streak,
)


st.set_page_config(page_title=APP_TITLE, page_icon="📘", layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;800&family=Amiri:wght@400;700&family=Cairo:wght@400;700&family=Noto+Naskh+Arabic:wght@400;700&family=Noto+Sans+Arabic:wght@400;700&family=Tajawal:wght@400;700&family=Noto+Sans+JP:wght@400;700&display=swap');

:root {
    --bg-1: #fff4e6;
    --bg-2: #dff6ef;
    --card: #ffffffd9;
    --text: #132a2b;
    --accent: #0f766e;
    --accent-2: #f97316;
}

html, body, [class*="css"] {
    font-family: 'Manrope', sans-serif;
    color: var(--text);
}

.stApp {
    background:
        radial-gradient(circle at 10% 15%, #ffd8a8 0%, transparent 35%),
        radial-gradient(circle at 85% 20%, #99f6e4 0%, transparent 30%),
        linear-gradient(140deg, var(--bg-1), var(--bg-2));
}

.main-card {
    background: var(--card);
    border: 1px solid #ffffff;
    border-radius: 20px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 12px 30px rgba(19, 42, 43, 0.08);
}

.badge {
    display: inline-block;
    padding: .2rem .55rem;
    border-radius: 999px;
    background: #ecfeff;
    color: var(--accent);
    border: 1px solid #99f6e4;
    font-weight: 700;
    font-size: .8rem;
}

.prompt-title {
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: .5rem;
}

.answer-label {
    font-size: 1rem;
    font-weight: 700;
    margin: .4rem 0;
}

.target-text {
    font-size: 2rem;
    line-height: 1.4;
}

.target-text-rtl {
    font-family: 'Amiri', serif;
    direction: rtl;
    text-align: right;
    font-size: 2rem;
    line-height: 1.4;
}

.target-text-ltr {
    font-family: 'Noto Sans JP', sans-serif;
    direction: ltr;
    text-align: left;
    font-size: 2rem;
    line-height: 1.4;
}

.big-score {
    font-size: 1.6rem;
    font-weight: 800;
    color: var(--accent);
}

[data-testid="stMain"] [data-testid="stRadio"] label {
    align-items: center;
}

[data-testid="stMain"] [data-testid="stRadio"] label p,
[data-testid="stMain"] [data-testid="stRadio"] label span,
[data-testid="stMain"] [data-testid="stRadio"] label div {
    font-weight: 700 !important;
    line-height: 1.4 !important;
    font-family: 'Manrope', 'Amiri', 'Noto Sans JP', sans-serif !important;
}

.answer-area [data-testid="stTextInput"] input {
    font-size: 1.25rem;
    font-weight: 600;
}
</style>
""",
    unsafe_allow_html=True,
)


def normalize(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def discover_categories(lang_config: dict) -> list[str]:
    data_dir = lang_config["data_dir"]
    if not data_dir.exists():
        return []
    alphabet_dir = lang_config["alphabet_dir"]
    return sorted(
        d.name for d in data_dir.iterdir()
        if d.is_dir() and d.name != alphabet_dir and any(d.glob("*.csv"))
    )


def load_category(category_dir: Path, word_columns: list[str]) -> pd.DataFrame:
    frames = []
    for csv_file in sorted(category_dir.glob("*.csv")):
        df = pd.read_csv(csv_file)
        for col in word_columns:
            if col not in df.columns:
                df[col] = ""
        frames.append(df[word_columns])
    if not frames:
        return pd.DataFrame(columns=word_columns)
    return pd.concat(frames, ignore_index=True).fillna("")


def load_words(lang_config: dict, category: str = "Alle woorden") -> pd.DataFrame:
    data_dir = lang_config["data_dir"]
    word_columns = lang_config["word_columns"]
    target_col = lang_config["target_col"]
    alphabet_dir = lang_config["alphabet_dir"]

    if category == "Alle woorden":
        frames = [
            load_category(d, word_columns)
            for d in sorted(data_dir.iterdir())
            if d.is_dir() and d.name != alphabet_dir
        ]
        if not frames:
            return pd.DataFrame(columns=word_columns)
        combined = pd.concat(frames, ignore_index=True).fillna("")
        return combined.drop_duplicates(subset=["dutch", target_col], keep="first").reset_index(drop=True)

    return load_category(data_dir / category, word_columns)


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


def similarity_score(a: str, b: str) -> float:
    a, b = a.strip(), b.strip()
    if not a or not b:
        return 0.0
    prefix = 0
    for c1, c2 in zip(a, b):
        if c1 == c2:
            prefix += 1
        else:
            break
    set_a, set_b = set(a), set(b)
    overlap = len(set_a & set_b) / max(len(set_a | set_b), 1)
    len_sim = 1.0 - abs(len(a) - len(b)) / max(len(a), len(b), 1)
    return prefix / max(len(a), len(b)) * 0.4 + overlap * 0.4 + len_sim * 0.2


def pick_confusable_options(
    correct: str, pool: list[str], word_key: str = "", n: int = MULTIPLE_CHOICE_DISTRACTORS
) -> list[str]:
    if len(pool) <= n:
        return pool[:]

    confusions = get_confusions()
    confused_with = confusions.get(word_key, {})

    scored = []
    for item in pool:
        sim = similarity_score(correct, item)
        confusion_bonus = confused_with.get(item, 0) * 0.5
        scored.append((item, sim + confusion_bonus))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_confusable = [item for item, _ in scored[: n * 2]]
    random.shuffle(top_confusable)
    return top_confusable[:n]


def build_question(df: pd.DataFrame, mode: str, lang_config: dict) -> dict:
    answer_style = st.session_state.get("answer_style", DEFAULT_ANSWER_STYLE)
    row = weighted_pick(df)
    target_col = lang_config["target_col"]
    translit_col = lang_config["translit_col"]
    lang_name = lang_config["name"]

    mode_labels = lang_config["mode_labels"]

    if mode == mode_labels["to_target"]:
        pool = [x for x in df[target_col].tolist() if x != row[target_col]]
        distractors = pick_confusable_options(row[target_col], pool, row["dutch"])
        options = [row[target_col]] + distractors
        random.shuffle(options)
        return {
            "mode": mode,
            "prompt": f"Wat is het {lang_name} voor: {row['dutch']}?",
            "prompt_target": "",
            "correct": row[target_col],
            "accepted": [normalize(row[target_col]), normalize(row[translit_col])],
            "options": options,
            "word_key": row["dutch"],
            "meta": row.to_dict(),
            "answer_style": answer_style,
        }

    if mode == mode_labels["to_dutch"]:
        pool = [x for x in df["dutch"].tolist() if x != row["dutch"]]
        distractors = pick_confusable_options(row["dutch"], pool, row["dutch"])
        options = [row["dutch"]] + distractors
        random.shuffle(options)
        return {
            "mode": mode,
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


def macos_tts_audio(text: str, voice: str = "Majed") -> tuple[bytes, str] | None:
    cache_dir = Path(tempfile.gettempdir()) / "ottolingo_tts"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_key = hashlib.sha1(f"{voice}:{text}".encode("utf-8")).hexdigest()  # nosec B324
    aiff_path = cache_dir / f"{cache_key}.aiff"
    wav_path = cache_dir / f"{cache_key}.wav"

    if not aiff_path.exists():
        cmd = ["say", "-v", voice, "-o", str(aiff_path), text]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    if not wav_path.exists():
        convert_cmd = ["afconvert", "-f", "WAVE", "-d", "LEI16", str(aiff_path), str(wav_path)]
        try:
            subprocess.run(convert_cmd, check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return aiff_path.read_bytes(), "audio/aiff"

    return wav_path.read_bytes(), "audio/wav"


@st.cache_data(show_spinner=False)
def list_macos_voices(voice_prefix: str, default_voice: str) -> list[str]:
    try:
        result = subprocess.run(["say", "-v", "?"], check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [default_voice]

    voices: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        name, language = parts[0], parts[1]
        if language.startswith(voice_prefix):
            voices.append(name)

    if default_voice not in voices:
        voices.append(default_voice)

    return sorted(set(voices), key=str.lower)


def grade_answer(question: dict, answer: str) -> bool:
    return normalize(answer) in [x for x in question["accepted"] if x]


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


# --- Page header ---
col_hdr_title, col_hdr_right = st.columns([3, 2])
with col_hdr_title:
    st.title(APP_TITLE)

# --- User selection ---
if "current_user" not in st.session_state:
    st.session_state.current_user = None

if st.session_state.current_user is None:
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

active_user = st.session_state.current_user

# Load saved language preference
if "current_language" not in st.session_state:
    saved_lang = get_language(active_user) if active_user else ""
    st.session_state.current_language = saved_lang if saved_lang in LANGUAGES else DEFAULT_LANGUAGE

with st.sidebar:
    if active_user:
        st.caption(f"Ingelogd als **{active_user}**")
    else:
        st.caption("Anonieme sessie (niet opgeslagen)")
    if st.button("Wissel gebruiker", type="tertiary"):
        st.session_state.current_user = None
        for key in list(st.session_state.keys()):
            if key.startswith("progress_"):
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
            if key.startswith("progress_"):
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
    category = st.selectbox("Woordenlijst", ["Alle woorden"] + categories, label_visibility="collapsed")

    _answer_styles = ["Meerkeuze", "Typen"]
    _default_style_idx = _answer_styles.index(DEFAULT_ANSWER_STYLE) if DEFAULT_ANSWER_STYLE in _answer_styles else 0
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

# --- Script/Alphabet practice mode ---
mode_labels = lang_config["mode_labels"]

if mode == mode_labels["script"]:
    alphabet_dir = lang_config["data_dir"] / lang_config["alphabet_dir"]
    alphabet_files = list(alphabet_dir.glob("*.csv")) if alphabet_dir.exists() else []

    if not alphabet_files:
        st.error(f"{lang_config['alphabet_label']}bestand niet gevonden.")
        st.stop()

    letters_df = pd.read_csv(alphabet_files[0])

    def build_alpha_question(letters_df: pd.DataFrame, lang_config: dict) -> dict:
        letter = letters_df.sample(1).iloc[0]
        letter_data = letter.to_dict()
        translit_col = lang_config.get("translit_col", "transliteration")
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
[data-testid="stMain"] [data-testid="stRadio"] label p,
[data-testid="stMain"] [data-testid="stRadio"] label span,
[data-testid="stMain"] [data-testid="stRadio"] label div {{
    font-size: 2.5rem !important;
    font-family: '{target_font}', 'Amiri', serif !important;
    direction: rtl !important;
}}
</style>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""<style>
[data-testid="stMain"] [data-testid="stRadio"] label p,
[data-testid="stMain"] [data-testid="stRadio"] label span,
[data-testid="stMain"] [data-testid="stRadio"] label div {{
    font-size: 2.5rem !important;
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


# --- Zoek & Oefen (Explore) mode ---
if mode == mode_labels.get("explore"):
    # Always use the full word list for explore mode, regardless of category selection.
    all_words_df = load_words(lang_config, "Alle woorden")
    ensure_stats_for_words(all_words_df)

    target_col = lang_config["target_col"]
    translit_col = lang_config["translit_col"]

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

            if st.button("← Terug naar zoeken", type="tertiary"):
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
                        distractors = pick_confusable_options(row[target_col], pool, row["dutch"])
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
                        distractors = pick_confusable_options(row["dutch"], pool, row["dutch"])
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


# --- Word practice modes ---
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
    stats = get_stats()

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
