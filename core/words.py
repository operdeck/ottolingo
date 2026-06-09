"""Word-list loading from CSV (no streamlit)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


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
