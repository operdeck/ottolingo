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

from srs import (
    due_words,
    get_word_state,
    is_due,
    is_new,
    list_users,
    load_progress,
    new_words,
    save_progress,
    sm2_update,
    update_streak,
)

APP_TITLE = "Ottolingo - Arabisch Oefenen"
DATA_DIR = Path(__file__).parent / "data"
REPO_URL = "https://github.com/operdeck/ottolingo"
DEFAULT_ARABIC_VOICE = "Majed"
AUTO_ADVANCE_DELAY_CORRECT_SECONDS = 1.0
AUTO_ADVANCE_DELAY_WRONG_SECONDS = 1.8
DEFAULT_NEW_WORDS_PER_SESSION = 7


st.set_page_config(page_title=APP_TITLE, page_icon="📘", layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;800&family=Amiri:wght@400;700&family=Cairo:wght@400;700&family=Noto+Naskh+Arabic:wght@400;700&family=Noto+Sans+Arabic:wght@400;700&family=Tajawal:wght@400;700&display=swap');

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

.arabic {
    font-family: 'Amiri', serif;
    direction: rtl;
    text-align: right;
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
    font-family: 'Manrope', 'Amiri', sans-serif !important;
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


def discover_categories() -> list[str]:
    if not DATA_DIR.exists():
        return []
    return sorted(d.name for d in DATA_DIR.iterdir() if d.is_dir() and any(d.glob("*.csv")))


WORD_COLUMNS = ["dutch", "arabic", "transliteration", "comment", "root", "example", "example_nl"]


def load_category(category_dir: Path) -> pd.DataFrame:
    frames = []
    for csv_file in sorted(category_dir.glob("*.csv")):
        df = pd.read_csv(csv_file)
        for col in WORD_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        frames.append(df[WORD_COLUMNS])
    if not frames:
        return pd.DataFrame(columns=WORD_COLUMNS)
    return pd.concat(frames, ignore_index=True).fillna("")


def load_words(category: str = "Alle woorden") -> pd.DataFrame:
    if category == "Alle woorden":
        frames = [load_category(d) for d in sorted(DATA_DIR.iterdir()) if d.is_dir()]
        if not frames:
            return pd.DataFrame(columns=WORD_COLUMNS)
        combined = pd.concat(frames, ignore_index=True).fillna("")
        return combined.drop_duplicates(subset=["dutch", "arabic"], keep="first").reset_index(drop=True)

    return load_category(DATA_DIR / category)


def get_progress() -> dict:
    user = st.session_state.get("current_user", "")
    cache_key = f"progress_{user}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = load_progress(user)
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
    correct: str, pool: list[str], word_key: str = "", n: int = 4
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


def build_question(df: pd.DataFrame, mode: str) -> dict:
    answer_style = st.session_state.get("answer_style", "Meerkeuze")
    row = weighted_pick(df)

    if mode == "Nederlands -> Arabisch":
        pool = [x for x in df["arabic"].tolist() if x != row["arabic"]]
        distractors = pick_confusable_options(row["arabic"], pool, row["dutch"])
        options = [row["arabic"]] + distractors
        random.shuffle(options)
        return {
            "mode": mode,
            "prompt": f"Wat is het Arabisch voor: {row['dutch']}?",
            "prompt_ar": "",
            "correct": row["arabic"],
            "accepted": [normalize(row["arabic"]), normalize(row["transliteration"])],
            "options": options,
            "word_key": row["dutch"],
            "meta": row.to_dict(),
            "answer_style": answer_style,
        }

    if mode == "Arabisch -> Nederlands":
        pool = [x for x in df["dutch"].tolist() if x != row["dutch"]]
        distractors = pick_confusable_options(row["dutch"], pool, row["dutch"])
        options = [row["dutch"]] + distractors
        random.shuffle(options)
        return {
            "mode": mode,
            "prompt": "Welk Nederlands woord hoort bij dit Arabische woord?",
            "prompt_ar": row["arabic"],
            "correct": row["dutch"],
            "accepted": [normalize(row["dutch"])],
            "options": options,
            "word_key": row["dutch"],
            "meta": row.to_dict(),
            "answer_style": answer_style,
        }

    # Luisteren -> Nederlands
    pool = [x for x in df["dutch"].tolist() if x != row["dutch"]]
    distractors = pick_confusable_options(row["dutch"], pool, row["dutch"])
    options = [row["dutch"]] + distractors
    return {
        "mode": mode,
        "prompt": "Luister en kies het juiste Nederlandse woord.",
        "prompt_ar": row["arabic"],
        "correct": row["dutch"],
        "accepted": [normalize(row["dutch"])],
        "options": options,
        "word_key": row["dutch"],
        "meta": row.to_dict(),
        "answer_style": "Meerkeuze",
    }


def macos_tts_audio(text: str, voice: str = DEFAULT_ARABIC_VOICE) -> tuple[bytes, str] | None:
    cache_dir = Path(tempfile.gettempdir()) / "ottolingo_tts"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_key = hashlib.sha1(f"{voice}:{text}".encode("utf-8")).hexdigest()  # nosec B324
    aiff_path = cache_dir / f"{cache_key}.aiff"
    wav_path = cache_dir / f"{cache_key}.wav"

    if not aiff_path.exists():
        cmd = [
            "say",
            "-v",
            voice,
            "-o",
            str(aiff_path),
            text,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    if not wav_path.exists():
        convert_cmd = [
            "afconvert",
            "-f",
            "WAVE",
            "-d",
            "LEI16",
            str(aiff_path),
            str(wav_path),
        ]
        try:
            subprocess.run(convert_cmd, check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback to AIFF if conversion is unavailable.
            return aiff_path.read_bytes(), "audio/aiff"

    return wav_path.read_bytes(), "audio/wav"


@st.cache_data(show_spinner=False)
def list_macos_arabic_voices() -> list[str]:
    try:
        result = subprocess.run(["say", "-v", "?"], check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [DEFAULT_ARABIC_VOICE]

    voices: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        name, language = parts[0], parts[1]
        if language.startswith("ar_"):
            voices.append(name)

    if DEFAULT_ARABIC_VOICE not in voices:
        voices.append(DEFAULT_ARABIC_VOICE)

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
    save_progress(progress)


def update_stats(word_key: str, correct: bool) -> None:
    progress = get_progress()
    state = get_word_state(progress, word_key)
    quality = 4 if correct else 1
    sm2_update(state, quality)
    update_streak(progress, date.today().isoformat())
    save_progress(progress)


st.title(APP_TITLE)
st.caption("Train slim: woorden met meer fouten komen vaker terug.")
st.link_button("Bekijk op GitHub", REPO_URL)

# --- User selection ---
if "current_user" not in st.session_state:
    st.session_state.current_user = None

if st.session_state.current_user is None:
    known_users = list_users()
    options = known_users + ["+ Nieuwe gebruiker", "Anoniem (niet opslaan)"]
    choice = st.selectbox("Wie ben je?", options, index=None, placeholder="Kies je naam...")

    if choice == "+ Nieuwe gebruiker":
        new_name = st.text_input("Hoe heet je?", placeholder="Voer je naam in")
        if st.button("Start", disabled=not new_name.strip()):
            st.session_state.current_user = new_name.strip()
            st.rerun()
    elif choice == "Anoniem (niet opslaan)":
        st.session_state.current_user = ""
        st.rerun()
    elif choice:
        st.session_state.current_user = choice
        st.rerun()
    else:
        st.stop()

active_user = st.session_state.current_user

with st.sidebar:
    if active_user:
        st.caption(f"Ingelogd als **{active_user}**")
    else:
        st.caption("Anonieme sessie (niet opgeslagen)")
    if st.button("Wissel gebruiker", type="tertiary"):
        st.session_state.current_user = None
        st.rerun()

    st.markdown("---")
    st.subheader("Woordenlijst")
    categories = discover_categories()
    category = st.selectbox("Woordenlijst", ["Alle woorden"] + categories, label_visibility="collapsed")

    st.subheader("Oefenmodus")
    mode = st.selectbox(
        "Oefenmodus",
        ["Nederlands -> Arabisch", "Arabisch -> Nederlands", "Schrift oefenen"],
        label_visibility="collapsed",
    )

    st.session_state.answer_style = st.radio("Antwoordtype", ["Meerkeuze", "Typen"], horizontal=True)

    st.subheader("Arabisch lettertype")
    arabic_font = st.selectbox(
        "Arabisch lettertype",
        ["Amiri", "Noto Naskh Arabic", "Noto Sans Arabic", "Cairo", "Tajawal"],
        label_visibility="collapsed",
    )

    st.subheader("Arabische stem")

    all_voices = list_macos_arabic_voices()

    default_voice_index = 0
    if DEFAULT_ARABIC_VOICE in all_voices:
        default_voice_index = all_voices.index(DEFAULT_ARABIC_VOICE)

    selected_arabic_voice = st.selectbox(
        "Kies stem",
        all_voices,
        index=default_voice_index,
    )

words_df = load_words(category)
if words_df.empty:
    st.error("Geen woorden gevonden voor deze categorie.")
    st.stop()

ensure_stats_for_words(words_df)

progress = get_progress()
all_word_keys = words_df["dutch"].tolist()
due_list = due_words(progress, all_word_keys)
new_list = new_words(progress, all_word_keys)
streak_count = progress["streak"]["count"]

with st.sidebar:
    st.markdown("---")
    st.subheader("Vandaag")
    col_due, col_new = st.columns(2)
    col_due.metric("Te herhalen", len(due_list))
    col_new.metric("Nieuw", f"{min(len(new_list), DEFAULT_NEW_WORDS_PER_SESSION)}")
    if streak_count > 0:
        st.caption(f"🔥 {streak_count} {'dag' if streak_count == 1 else 'dagen'} op rij")

    if "session_start" not in st.session_state:
        st.session_state.session_start = time.time()
    elapsed_min = int((time.time() - st.session_state.session_start) / 60)
    target_min = 15
    progress_frac = min(elapsed_min / target_min, 1.0)
    st.progress(progress_frac, text=f"⏱ {elapsed_min} / {target_min} min")
    if 15 <= elapsed_min < 25:
        st.success("Goed gedaan! Doel bereikt. Morgen weer?")
    elif elapsed_min >= 25:
        st.info("Overweeg een pauze — kort en vaak is effectiever.")

st.markdown(
    f"""
<style>
.arabic {{
    font-family: '{arabic_font}', 'Amiri', serif !important;
}}
</style>
""",
    unsafe_allow_html=True,
)

if mode == "Schrift oefenen":
    alphabet_file = DATA_DIR / "Alfabet" / "letters.csv"
    if alphabet_file.exists():
        letters_df = pd.read_csv(alphabet_file)
    else:
        st.error("Alfabetbestand niet gevonden.")
        st.stop()

    def build_alpha_question(letters_df: pd.DataFrame) -> dict:
        letter = letters_df.sample(1).iloc[0]
        letter_data = letter.to_dict()
        exercise_type = random.choice(["letter_to_sound", "sound_to_letter", "position"])

        if exercise_type == "letter_to_sound":
            correct = letter_data["transliteration"]
            pool = [r["transliteration"] for _, r in letters_df.iterrows() if r["transliteration"] != correct]
            random.shuffle(pool)
            options = [correct] + pool[:4]
            random.shuffle(options)
        elif exercise_type == "sound_to_letter":
            correct = letter_data["isolated"]
            pool = [r["isolated"] for _, r in letters_df.iterrows() if r["isolated"] != correct]
            random.shuffle(pool)
            options = [correct] + pool[:4]
            random.shuffle(options)
        else:
            positions = {"initial": "begin", "medial": "midden", "final": "eind"}
            pos_key = random.choice(list(positions.keys()))
            correct = letter_data[pos_key]
            pool = [r[pos_key] for _, r in letters_df.iterrows() if r[pos_key] != correct]
            random.shuffle(pool)
            options = [correct] + pool[:4]
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
        st.session_state.alpha_question = build_alpha_question(letters_df)

    aq = st.session_state.alpha_question
    letter_data = aq["letter"]
    correct = aq["correct"]
    options = aq["options"]

    if aq["type"] in ("sound_to_letter", "position"):
        st.markdown(
            f"""<style>
[data-testid="stMain"] [data-testid="stRadio"] label p,
[data-testid="stMain"] [data-testid="stRadio"] label span,
[data-testid="stMain"] [data-testid="stRadio"] label div {{
    font-size: 2.5rem !important;
    font-family: '{arabic_font}', 'Amiri', serif !important;
    direction: rtl !important;
}}
</style>""",
            unsafe_allow_html=True,
        )

    col_main, col_side = st.columns([2.0, 1.2], gap="large")
    with col_main:
        st.markdown("<span class='badge'>Schrift oefenen</span>", unsafe_allow_html=True)

        if aq["type"] == "letter_to_sound":
            st.markdown(f"<div class='arabic' style='font-size:4rem'>{letter_data['isolated']}</div>", unsafe_allow_html=True)
            st.markdown("<div class='prompt-title'>Welke klank hoort bij deze letter?</div>", unsafe_allow_html=True)

        elif aq["type"] == "sound_to_letter":
            st.markdown(f"<div class='prompt-title'>Welke letter maakt de klank: <b>{letter_data['transliteration']}</b> ({letter_data['name']})?</div>", unsafe_allow_html=True)

        else:  # position
            pos_label = letter_data.get("_pos_label", "")
            st.markdown(f"<div class='prompt-title'>Hoe ziet <b>{letter_data['name']}</b> ({letter_data['isolated']}) eruit aan het <b>{pos_label}</b> van een woord?</div>", unsafe_allow_html=True)

        qid = st.session_state.get("alpha_qid", 0)
        selected = st.radio("Kies", options, index=None, key=f"alpha_{qid}", label_visibility="collapsed")

        if selected:
            if aq["type"] == "sound_to_letter":
                speak_text = selected
            else:
                speak_text = letter_data["isolated"]
            spoken_key = f"alpha_{qid}:{selected}"
            if st.session_state.get("alpha_last_spoken") != spoken_key:
                audio_payload = macos_tts_audio(speak_text, voice=selected_arabic_voice)
                if audio_payload:
                    audio_bytes, audio_format = audio_payload
                    st.audio(audio_bytes, format=audio_format, autoplay=True)
                    st.session_state.alpha_last_spoken = spoken_key

        if st.button("Controleer", type="primary", disabled=st.session_state.alpha_answered, key="alpha_check"):
            if selected is None:
                st.warning("Kies eerst een antwoord.")
            else:
                is_correct = selected == correct
                st.session_state.alpha_answered = True
                st.session_state.alpha_last_result = is_correct

        if st.session_state.get("alpha_answered"):
            if st.session_state.get("alpha_last_result"):
                st.success("Goed gedaan!")
            else:
                st.error(f"Niet goed. Correct was: {correct}")
            if letter_data.get("comment"):
                st.info(f"💡 {letter_data['comment']}")

        if st.button("Volgende letter", key="alpha_next"):
            st.session_state.alpha_question = build_alpha_question(letters_df)
            st.session_state.alpha_answered = False
            st.session_state.alpha_qid = qid + 1
            st.rerun()

    with col_side:
        st.subheader("Alfabet overzicht")
        st.dataframe(
            letters_df[["isolated", "name", "transliteration"]].rename(
                columns={"isolated": "Letter", "name": "Naam", "transliteration": "Klank"}
            ),
            use_container_width=True,
            hide_index=True,
            height=400,
        )

    st.stop()

if (
    "question" not in st.session_state
    or st.session_state.get("question", {}).get("mode") != mode
    or st.session_state.get("question", {}).get("answer_style")
    != st.session_state.answer_style
    or st.session_state.get("current_category") != category
):
    st.session_state.question = build_question(words_df, mode)
    st.session_state.answered = False
    st.session_state.current_category = category

question = st.session_state.question

if question["mode"] == "Nederlands -> Arabisch":
    st.markdown(
        f"""
<style>
[data-testid="stMain"] [data-testid="stRadio"] label p,
[data-testid="stMain"] [data-testid="stRadio"] label span,
[data-testid="stMain"] [data-testid="stRadio"] label div {{
    font-size: 2.25rem !important;
    direction: rtl !important;
    text-align: right !important;
    font-family: '{arabic_font}', 'Amiri', 'Manrope', sans-serif !important;
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

    if question["prompt_ar"]:
        st.markdown(f"<div class='arabic'>{question['prompt_ar']}</div>", unsafe_allow_html=True)

    qid = st.session_state.get("qid", 0)


    if question["mode"] == "Arabisch -> Nederlands":
        audio_payload = macos_tts_audio(question["meta"]["arabic"], voice=selected_arabic_voice)
        if audio_payload:
            audio_bytes, audio_format = audio_payload
            st.audio(audio_bytes, format=audio_format)
        if st.button("Toon losse letters", key=f"split_{qid}"):
            arabic_word = question["meta"]["arabic"]
            spaced = "  ".join(arabic_word)
            st.markdown(f"<div class='arabic' style='letter-spacing:0.3em'>{spaced}</div>", unsafe_allow_html=True)

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

        if question["mode"] == "Nederlands -> Arabisch" and selected:
            spoken_key = f"{qid}:{selected}"
            if st.session_state.get("last_spoken_choice") != spoken_key:
                audio_payload = macos_tts_audio(selected, voice=selected_arabic_voice)
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
            st.error(
                f"Niet goed. Correct was: {question['correct']} "
                f"({question['meta'].get('transliteration', '')})"
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
                    family = " · ".join(f"{r['arabic']} ({r['dutch']})" for _, r in others.iterrows())
                    st.caption(f"Wortel [{root}]: {family}")
        example = question["meta"].get("example", "")
        if example:
            example_nl = question["meta"].get("example_nl", "")
            ex_text = f"📝 {example}"
            if example_nl:
                ex_text += f" — {example_nl}"
            st.caption(ex_text)

    if st.session_state.get("answered") and trigger_auto_advance:
        delay_seconds = (
            AUTO_ADVANCE_DELAY_CORRECT_SECONDS
            if st.session_state.get("last_result")
            else AUTO_ADVANCE_DELAY_WRONG_SECONDS
        )
        time.sleep(delay_seconds)
        st.session_state.question = build_question(words_df, mode)
        st.session_state.answered = False
        st.session_state.qid = st.session_state.get("qid", 0) + 1
        st.rerun()

    if st.button("Volgend woord"):
        st.session_state.question = build_question(words_df, mode)
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
