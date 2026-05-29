"""Spaced Repetition System (SM-2 based) with persistent storage."""

from __future__ import annotations

import json
import time
from pathlib import Path

PROGRESS_DIR = Path.home() / ".ottolingo"

DEFAULT_EASINESS = 2.5
MIN_EASINESS = 1.3


def _ensure_dir() -> None:
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)


def _user_file(user: str) -> Path:
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in user.lower())
    return PROGRESS_DIR / f"{safe_name}.json"


def list_users() -> list[str]:
    _ensure_dir()
    users = []
    for f in sorted(PROGRESS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            users.append(data.get("user", f.stem))
        except (json.JSONDecodeError, OSError):
            continue
    return users


def load_progress(user: str = "") -> dict:
    _ensure_dir()
    if not user:
        return _default_progress()
    path = _user_file(user)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return _default_progress(user)
    return _default_progress(user)


def _default_progress(user: str = "") -> dict:
    return {"user": user, "language": "", "words": {}, "sessions": [], "streak": {"last_date": "", "count": 0}}


def save_progress(data: dict) -> None:
    user = data.get("user", "")
    if not user:
        return
    _ensure_dir()
    path = _user_file(user)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_word_state(progress: dict, word_key: str) -> dict:
    if word_key not in progress["words"]:
        progress["words"][word_key] = {
            "easiness": DEFAULT_EASINESS,
            "interval": 0,
            "repetitions": 0,
            "last_review": 0.0,
            "next_review": 0.0,
            "right": 0,
            "wrong": 0,
            "confusions": {},
        }
    return progress["words"][word_key]


def sm2_update(word_state: dict, quality: int) -> None:
    """Update word state using SM-2 algorithm.

    quality: 0-5 scale (0-1 = complete failure, 2 = wrong but remembered after seeing,
             3 = correct with difficulty, 4 = correct, 5 = perfect/easy)
    """
    now = time.time()
    word_state["last_review"] = now

    if quality >= 3:
        word_state["right"] += 1
        if word_state["repetitions"] == 0:
            word_state["interval"] = 1
        elif word_state["repetitions"] == 1:
            word_state["interval"] = 6
        else:
            word_state["interval"] = round(word_state["interval"] * word_state["easiness"])
        word_state["repetitions"] += 1
    else:
        word_state["wrong"] += 1
        word_state["repetitions"] = 0
        word_state["interval"] = 1

    ef = word_state["easiness"]
    ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    word_state["easiness"] = max(MIN_EASINESS, ef)

    word_state["next_review"] = now + word_state["interval"] * 86400


def is_due(word_state: dict) -> bool:
    if word_state["repetitions"] == 0 and word_state["last_review"] == 0.0:
        return False  # never seen = new word, not "due"
    return time.time() >= word_state["next_review"]


def is_new(word_state: dict) -> bool:
    return word_state["last_review"] == 0.0


def due_words(progress: dict, all_keys: list[str]) -> list[str]:
    result = []
    for key in all_keys:
        state = get_word_state(progress, key)
        if is_due(state):
            result.append(key)
    return result


def new_words(progress: dict, all_keys: list[str]) -> list[str]:
    return [key for key in all_keys if is_new(get_word_state(progress, key))]


def update_streak(progress: dict, today: str) -> None:
    streak = progress["streak"]
    if streak["last_date"] == today:
        return
    from datetime import date, timedelta
    yesterday = (date.fromisoformat(today) - timedelta(days=1)).isoformat()
    if streak["last_date"] == yesterday:
        streak["count"] += 1
    elif streak["last_date"] != today:
        streak["count"] = 1
    streak["last_date"] = today


def get_language(user: str) -> str:
    if not user:
        return ""
    path = _user_file(user)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("language", "")
        except (json.JSONDecodeError, OSError):
            return ""
    return ""


def save_language(user: str, language: str) -> None:
    if not user:
        return
    _ensure_dir()
    path = _user_file(user)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = _default_progress(user)
    else:
        data = _default_progress(user)
    data["language"] = language
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_words_key(language: str) -> str:
    if language:
        return f"words_{language}"
    return "words"


def load_progress_for_language(user: str, language: str) -> dict:
    _ensure_dir()
    if not user:
        return _default_progress()
    path = _user_file(user)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = _default_progress(user)
    else:
        data = _default_progress(user)

    words_key = get_words_key(language)
    # Migrate: if old "words" key exists and no language-specific key yet, move it
    if words_key not in data and "words" in data and data["words"] and language:
        old_lang = data.get("language", "arabic")
        old_key = get_words_key(old_lang)
        if old_key not in data:
            data[old_key] = data["words"]
        data["words"] = {}

    words = data.get(words_key, {})
    return {
        "user": user,
        "language": language,
        "words": words,
        "sessions": data.get("sessions", []),
        "streak": data.get("streak", {"last_date": "", "count": 0}),
    }


def save_progress_for_language(data: dict) -> None:
    user = data.get("user", "")
    if not user:
        return
    _ensure_dir()
    path = _user_file(user)

    if path.exists():
        try:
            full_data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            full_data = _default_progress(user)
    else:
        full_data = _default_progress(user)

    language = data.get("language", "")
    words_key = get_words_key(language)
    full_data["user"] = user
    full_data["language"] = language
    full_data[words_key] = data.get("words", {})
    full_data["streak"] = data.get("streak", {"last_date": "", "count": 0})
    full_data["sessions"] = data.get("sessions", [])

    path.write_text(json.dumps(full_data, ensure_ascii=False, indent=2), encoding="utf-8")
