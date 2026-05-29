"""Language configuration for Ottolingo."""

from __future__ import annotations

from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

LANGUAGES = {
    "arabic": {
        "name": "Arabisch",
        "flag": "🇸🇦",
        "target_col": "arabic",
        "translit_col": "transliteration",
        "data_dir": DATA_DIR / "arabic",
        "direction": "rtl",
        "fonts": ["Amiri", "Noto Naskh Arabic", "Noto Sans Arabic", "Cairo", "Tajawal"],
        "font_import": "family=Amiri:wght@400;700&family=Cairo:wght@400;700&family=Noto+Naskh+Arabic:wght@400;700&family=Noto+Sans+Arabic:wght@400;700&family=Tajawal:wght@400;700",
        "default_voice": "Majed",
        "voice_prefix": "ar_",
        "alphabet_dir": "Alfabet",
        "alphabet_label": "Alfabet",
        "alphabet_has_positions": True,
        "word_columns": ["dutch", "arabic", "transliteration", "comment", "root", "example", "example_nl"],
        "alphabet_columns": ["name", "transliteration", "isolated", "initial", "medial", "final", "comment"],
        "modes": ["Nederlands -> Arabisch", "Arabisch -> Nederlands", "Schrift oefenen"],
        "mode_labels": {
            "to_target": "Nederlands -> Arabisch",
            "to_dutch": "Arabisch -> Nederlands",
            "script": "Schrift oefenen",
        },
    },
    "japanese": {
        "name": "Japans",
        "flag": "🇯🇵",
        "target_col": "japanese",
        "translit_col": "romaji",
        "data_dir": DATA_DIR / "japanese",
        "direction": "ltr",
        "fonts": ["Noto Sans JP", "Hiragino Mincho Pro"],
        "font_import": "family=Noto+Sans+JP:wght@400;700",
        "default_voice": "Kyoko",
        "voice_prefix": "ja_",
        "alphabet_dir": "Hiragana",
        "alphabet_label": "Hiragana",
        "alphabet_has_positions": False,
        "word_columns": ["dutch", "japanese", "romaji", "comment", "example", "example_nl"],
        "alphabet_columns": ["name", "romaji", "character", "comment"],
        "modes": ["Nederlands -> Japans", "Japans -> Nederlands", "Hiragana oefenen"],
        "mode_labels": {
            "to_target": "Nederlands -> Japans",
            "to_dutch": "Japans -> Nederlands",
            "script": "Hiragana oefenen",
        },
    },
}

DEFAULT_LANGUAGE = "arabic"


def get_lang_config(lang_key: str) -> dict:
    return LANGUAGES[lang_key]
