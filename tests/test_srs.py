"""Unit tests for the SRS module."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from srs import (
    get_language,
    get_word_state,
    get_words_key,
    is_due,
    is_new,
    load_progress_for_language,
    save_language,
    save_progress_for_language,
    sm2_update,
    update_streak,
)


@pytest.fixture
def tmp_user(tmp_path, monkeypatch):
    """Use a temp directory for user data."""
    monkeypatch.setattr("srs.PROGRESS_DIR", tmp_path)
    return "testuser"


def test_get_words_key():
    assert get_words_key("arabic") == "words_arabic"
    assert get_words_key("japanese") == "words_japanese"
    assert get_words_key("") == "words"


def test_save_and_load_language(tmp_user, tmp_path, monkeypatch):
    monkeypatch.setattr("srs.PROGRESS_DIR", tmp_path)
    save_language(tmp_user, "japanese")
    assert get_language(tmp_user) == "japanese"

    save_language(tmp_user, "arabic")
    assert get_language(tmp_user) == "arabic"


def test_save_and_load_language_empty_user(tmp_path, monkeypatch):
    monkeypatch.setattr("srs.PROGRESS_DIR", tmp_path)
    save_language("", "japanese")
    assert get_language("") == ""


def test_progress_per_language_isolation(tmp_user, tmp_path, monkeypatch):
    monkeypatch.setattr("srs.PROGRESS_DIR", tmp_path)

    # Save Arabic progress
    ar_prog = load_progress_for_language(tmp_user, "arabic")
    ar_prog["words"]["huis"] = get_word_state(ar_prog, "huis")
    ar_prog["words"]["huis"]["right"] = 5
    save_progress_for_language(ar_prog)

    # Save Japanese progress
    jp_prog = load_progress_for_language(tmp_user, "japanese")
    jp_prog["words"]["いえ"] = get_word_state(jp_prog, "いえ")
    jp_prog["words"]["いえ"]["right"] = 3
    save_progress_for_language(jp_prog)

    # Reload and verify isolation
    ar_reloaded = load_progress_for_language(tmp_user, "arabic")
    jp_reloaded = load_progress_for_language(tmp_user, "japanese")

    assert "huis" in ar_reloaded["words"]
    assert ar_reloaded["words"]["huis"]["right"] == 5
    assert "いえ" not in ar_reloaded["words"]

    assert "いえ" in jp_reloaded["words"]
    assert jp_reloaded["words"]["いえ"]["right"] == 3
    assert "huis" not in jp_reloaded["words"]


def test_migration_from_old_format(tmp_user, tmp_path, monkeypatch):
    """Old user data (with 'words' key, no language) migrates correctly."""
    monkeypatch.setattr("srs.PROGRESS_DIR", tmp_path)

    # Write old-format file
    old_data = {
        "user": tmp_user,
        "words": {"boek": {"easiness": 2.5, "interval": 6, "repetitions": 2,
                           "last_review": 1000.0, "next_review": 2000.0,
                           "right": 5, "wrong": 1, "confusions": {}}},
        "sessions": [],
        "streak": {"last_date": "2026-05-28", "count": 3},
    }
    user_file = tmp_path / f"{tmp_user}.json"
    user_file.write_text(json.dumps(old_data), encoding="utf-8")

    # Load as Arabic — should get the old words
    prog = load_progress_for_language(tmp_user, "arabic")
    assert "boek" in prog["words"]
    assert prog["words"]["boek"]["right"] == 5

    # Load as Japanese — should be empty
    jp_prog = load_progress_for_language(tmp_user, "japanese")
    assert len(jp_prog["words"]) == 0


def test_sm2_correct_answer():
    state = get_word_state({"words": {}}, "test")
    sm2_update(state, 4)  # correct
    assert state["right"] == 1
    assert state["wrong"] == 0
    assert state["interval"] == 1
    assert state["repetitions"] == 1


def test_sm2_wrong_answer():
    state = get_word_state({"words": {}}, "test")
    state["repetitions"] = 3
    state["interval"] = 15
    sm2_update(state, 1)  # wrong
    assert state["wrong"] == 1
    assert state["repetitions"] == 0
    assert state["interval"] == 1


def test_is_new_and_is_due():
    state = get_word_state({"words": {}}, "test")
    assert is_new(state)
    assert not is_due(state)

    sm2_update(state, 4)
    assert not is_new(state)


def test_streak_update():
    progress = {"streak": {"last_date": "", "count": 0}}
    update_streak(progress, "2026-05-28")
    assert progress["streak"]["count"] == 1
    assert progress["streak"]["last_date"] == "2026-05-28"

    # Same day — no change
    update_streak(progress, "2026-05-28")
    assert progress["streak"]["count"] == 1

    # Next day — increment
    update_streak(progress, "2026-05-29")
    assert progress["streak"]["count"] == 2

    # Skip a day — reset
    update_streak(progress, "2026-05-31")
    assert progress["streak"]["count"] == 1
