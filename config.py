"""Application configuration loaded from config.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).parent / "config.yaml"


def _load() -> dict:
    with _CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


_cfg = _load()

# App
APP_TITLE: str = _cfg["app"]["title"]
REPO_URL: str = _cfg["app"]["repo_url"]

# UI
AUTO_ADVANCE_DELAY_CORRECT_SECONDS: float = _cfg["ui"]["auto_advance_delay_correct_seconds"]
AUTO_ADVANCE_DELAY_WRONG_SECONDS: float = _cfg["ui"]["auto_advance_delay_wrong_seconds"]

# Session
DEFAULT_LANGUAGE: str = _cfg["session"]["default_language"]
DEFAULT_ANSWER_STYLE: str = _cfg["session"]["default_answer_style"]
DEFAULT_NEW_WORDS_PER_SESSION: int = _cfg["session"]["new_words_per_session"]
SESSION_TARGET_MINUTES: int = _cfg["session"]["target_minutes"]
MULTIPLE_CHOICE_DISTRACTORS: int = _cfg["session"]["multiple_choice_distractors"]

# SRS
DEFAULT_EASINESS: float = _cfg["srs"]["default_easiness"]
MIN_EASINESS: float = _cfg["srs"]["min_easiness"]
