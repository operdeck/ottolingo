"""Unit tests for language configuration and data loading."""

from __future__ import annotations

import pandas as pd
import pytest

from languages import DEFAULT_LANGUAGE, LANGUAGES, get_lang_config


def test_all_languages_have_required_keys():
    required_keys = [
        "name", "flag", "target_col", "translit_col", "data_dir",
        "direction", "fonts", "default_voice", "voice_prefix",
        "alphabet_dir", "alphabet_label", "alphabet_has_positions",
        "word_columns", "alphabet_columns", "modes", "mode_labels",
    ]
    for lang_key, config in LANGUAGES.items():
        for key in required_keys:
            assert key in config, f"'{key}' missing in language '{lang_key}'"


def test_default_language_exists():
    assert DEFAULT_LANGUAGE in LANGUAGES


def test_get_lang_config_returns_dict():
    config = get_lang_config("arabic")
    assert isinstance(config, dict)
    assert config["name"] == "Arabisch"


def test_get_lang_config_invalid_raises():
    with pytest.raises(KeyError):
        get_lang_config("klingon")


def test_data_directories_exist():
    for lang_key, config in LANGUAGES.items():
        assert config["data_dir"].exists(), f"Data dir for '{lang_key}' does not exist"


def test_alphabet_files_exist():
    for lang_key, config in LANGUAGES.items():
        alpha_dir = config["data_dir"] / config["alphabet_dir"]
        assert alpha_dir.exists(), f"Alphabet dir for '{lang_key}' does not exist"
        csv_files = list(alpha_dir.glob("*.csv"))
        assert len(csv_files) > 0, f"No CSV in alphabet dir for '{lang_key}'"


def test_word_csvs_have_correct_columns():
    for lang_key, config in LANGUAGES.items():
        data_dir = config["data_dir"]
        word_columns = config["word_columns"]
        alphabet_dir = config["alphabet_dir"]

        for cat_dir in data_dir.iterdir():
            if not cat_dir.is_dir() or cat_dir.name == alphabet_dir:
                continue
            for csv_file in cat_dir.glob("*.csv"):
                df = pd.read_csv(csv_file)
                # At minimum: dutch + target_col + translit_col
                assert "dutch" in df.columns, f"'dutch' missing in {csv_file}"
                assert config["target_col"] in df.columns, (
                    f"'{config['target_col']}' missing in {csv_file}"
                )
                assert config["translit_col"] in df.columns, (
                    f"'{config['translit_col']}' missing in {csv_file}"
                )


def test_alphabet_csvs_have_correct_columns():
    for lang_key, config in LANGUAGES.items():
        alpha_dir = config["data_dir"] / config["alphabet_dir"]
        for csv_file in alpha_dir.glob("*.csv"):
            df = pd.read_csv(csv_file)
            assert "name" in df.columns, f"'name' missing in {csv_file}"
            # Should have a character column
            has_char = "character" in df.columns or "isolated" in df.columns
            assert has_char, f"No character/isolated column in {csv_file}"


def test_no_empty_target_words():
    """Every word should have a non-empty target language value."""
    for lang_key, config in LANGUAGES.items():
        data_dir = config["data_dir"]
        target_col = config["target_col"]
        alphabet_dir = config["alphabet_dir"]

        for cat_dir in data_dir.iterdir():
            if not cat_dir.is_dir() or cat_dir.name == alphabet_dir:
                continue
            for csv_file in cat_dir.glob("*.csv"):
                df = pd.read_csv(csv_file)
                empty = df[df[target_col].isna() | (df[target_col] == "")]
                assert empty.empty, (
                    f"Empty {target_col} values in {csv_file}: "
                    f"{empty['dutch'].tolist()}"
                )


def test_mode_labels_consistency():
    for lang_key, config in LANGUAGES.items():
        labels = config["mode_labels"]
        modes = config["modes"]
        assert labels["to_target"] in modes
        assert labels["to_dutch"] in modes
        assert labels["script"] in modes
