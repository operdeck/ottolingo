from __future__ import annotations

import hashlib
import random
import subprocess
import tempfile
import time
from pathlib import Path

import pandas as pd
import streamlit as st

APP_TITLE = "Ottolingo - Arabisch Oefenen"
WORDS_FILE = Path(__file__).parent / "data" / "words.csv"
REPO_URL = "https://github.com/operdeck/ottolingo"
DEFAULT_ARABIC_VOICE = "Majed"
AUTO_ADVANCE_DELAY_CORRECT_SECONDS = 1.0
AUTO_ADVANCE_DELAY_WRONG_SECONDS = 1.8


st.set_page_config(page_title=APP_TITLE, page_icon="📘", layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;800&family=Amiri:wght@400;700&display=swap');

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


def load_words() -> pd.DataFrame:
    if not WORDS_FILE.exists():
        return pd.DataFrame(columns=["dutch", "arabic", "transliteration"])

    df = pd.read_csv(WORDS_FILE)
    expected = ["dutch", "arabic", "transliteration"]
    for col in expected:
        if col not in df.columns:
            df[col] = ""
    return df[expected].fillna("")


def get_stats() -> dict[str, dict[str, int]]:
    if "stats" not in st.session_state:
        st.session_state.stats = {}
    return st.session_state.stats


def ensure_stats_for_words(df: pd.DataFrame) -> None:
    stats = get_stats()
    for key in df["dutch"].tolist():
        if key not in stats:
            stats[key] = {"right": 0, "wrong": 0}


def weighted_pick(df: pd.DataFrame) -> pd.Series:
    stats = get_stats()
    weights = []
    rows = df.to_dict("records")

    for row in rows:
        item = stats.get(row["dutch"], {"right": 0, "wrong": 0})
        weights.append(1.0 + (item["wrong"] * 2.8) + (item["wrong"] - item["right"]) * 0.4)

    if st.session_state.get("last_word"):
        for i, row in enumerate(rows):
            if row["dutch"] == st.session_state.last_word and len(rows) > 1:
                weights[i] = max(0.2, weights[i] * 0.2)

    chosen = random.choices(rows, weights=weights, k=1)[0]
    st.session_state.last_word = chosen["dutch"]
    return pd.Series(chosen)


def build_question(df: pd.DataFrame, mode: str) -> dict:
    answer_style = st.session_state.get("answer_style", "Meerkeuze")
    row = weighted_pick(df)

    if mode == "Nederlands -> Arabisch":
        pool = [x for x in df["arabic"].tolist() if x != row["arabic"]]
        random.shuffle(pool)
        options = [row["arabic"]] + pool[:3]
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
        random.shuffle(pool)
        options = [row["dutch"]] + pool[:3]
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
    random.shuffle(pool)
    options = [row["dutch"]] + pool[:3]
    random.shuffle(options)
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


def update_stats(word_key: str, correct: bool) -> None:
    stats = get_stats()
    if word_key not in stats:
        stats[word_key] = {"right": 0, "wrong": 0}

    if correct:
        stats[word_key]["right"] += 1
    else:
        stats[word_key]["wrong"] += 1


st.title(APP_TITLE)
st.caption("Train slim: woorden met meer fouten komen vaker terug.")
st.link_button("Bekijk op GitHub", REPO_URL)

words_df = load_words()
if words_df.empty:
    st.error("Geen woorden gevonden. Voeg woorden toe in data/words.csv")
    st.stop()

ensure_stats_for_words(words_df)

with st.sidebar:
    st.subheader("Instellingen")
    mode = st.selectbox(
        "Oefenmodus",
        ["Nederlands -> Arabisch", "Arabisch -> Nederlands", "Luisteren -> Nederlands"],
    )

    st.session_state.answer_style = st.radio("Antwoordtype", ["Meerkeuze", "Typen"], horizontal=True)

    st.markdown("---")
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

if (
    "question" not in st.session_state
    or st.session_state.get("question", {}).get("mode") != mode
    or st.session_state.get("question", {}).get("answer_style")
    != st.session_state.answer_style
):
    st.session_state.question = build_question(words_df, mode)
    st.session_state.answered = False

question = st.session_state.question

if question["mode"] == "Nederlands -> Arabisch":
    st.markdown(
        """
<style>
[data-testid="stMain"] [data-testid="stRadio"] label p,
[data-testid="stMain"] [data-testid="stRadio"] label span,
[data-testid="stMain"] [data-testid="stRadio"] label div {
    font-size: 2.25rem !important;
    direction: rtl !important;
    text-align: right !important;
    font-family: 'Amiri', 'Manrope', sans-serif !important;
}
</style>
""",
        unsafe_allow_html=True,
    )
elif question["mode"] == "Arabisch -> Nederlands":
    st.markdown(
        """
<style>
[data-testid="stMain"] [data-testid="stRadio"] label p,
[data-testid="stMain"] [data-testid="stRadio"] label span,
[data-testid="stMain"] [data-testid="stRadio"] label div {
    font-size: 2.25rem !important;
    direction: ltr !important;
    text-align: left !important;
}
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
    font-size: 1.5rem !important;
    direction: ltr !important;
    text-align: left !important;
}
</style>
""",
        unsafe_allow_html=True,
    )

col_main, col_side = st.columns([2.4, 1.0], gap="large")

with col_main:
    st.markdown(f"<span class='badge'>{question['mode']}</span>", unsafe_allow_html=True)
    st.markdown(f"<div class='prompt-title'>{question['prompt']}</div>", unsafe_allow_html=True)

    if question["prompt_ar"]:
        st.markdown(f"<div class='arabic'>{question['prompt_ar']}</div>", unsafe_allow_html=True)

    qid = st.session_state.get("qid", 0)

    if question["mode"] == "Luisteren -> Nederlands":
        audio_payload = macos_tts_audio(question["meta"]["arabic"], voice=selected_arabic_voice)
        if audio_payload:
            audio_bytes, audio_format = audio_payload
            st.audio(audio_bytes, format=audio_format)
        else:
            st.info("Audio kon niet gegenereerd worden. Controleer of het macOS commando 'say' werkt.")

    if question["mode"] == "Arabisch -> Nederlands":
        if st.button("Spreek Arabisch woord uit", key=f"speak_ar_nl_{qid}"):
            audio_payload = macos_tts_audio(question["meta"]["arabic"], voice=selected_arabic_voice)
            if audio_payload:
                audio_bytes, audio_format = audio_payload
                st.audio(audio_bytes, format=audio_format, autoplay=True)
            else:
                st.info("Audio kon niet gegenereerd worden. Controleer of het macOS commando 'say' werkt.")

    trigger_auto_advance = False

    if question["answer_style"] == "Meerkeuze":
        selected = st.radio(
            "Kies je antwoord",
            question["options"],
            index=None,
            key=f"choice_{qid}",
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
                by=["fouten", "pogingen", "succes%", "woord"],
                ascending=[False, False, True, True],
                kind="mergesort",
            )
            .reset_index(drop=True)
        )
        board_df.insert(0, "#", board_df.index + 1)
        st.dataframe(board_df, use_container_width=True, hide_index=True)
    else:
        st.caption("Maak je eerste oefening om statistieken te zien.")
