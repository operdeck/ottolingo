"""Word-list loading from CSV (no streamlit)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


def _load_thematic_groups(lang_config: dict) -> dict[str, dict]:
    """Load thematic groups from groups.yaml (no external dependency)."""
    path = Path(lang_config["data_dir"]) / "groups.yaml"
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:  # noqa: BLE001
        return {}
    return {
        key: {"label": str(val["label"]), "words": [str(w) for w in val.get("words", [])]}
        for key, val in data.items()
        if isinstance(val, dict) and "label" in val and "words" in val
    }


def discover_categories(lang_config: dict) -> list[str]:
    data_dir = lang_config["data_dir"]
    if not data_dir.exists():
        return []
    alphabet_dir = lang_config.get("alphabet_dir")
    folder_cats = sorted(
        d.name for d in data_dir.iterdir()
        if d.is_dir() and d.name != alphabet_dir and any(d.glob("*.csv"))
    )
    # Append thematic group labels that don't duplicate an existing folder name
    folder_set = set(folder_cats)
    thematic = _load_thematic_groups(lang_config)
    group_labels = [g["label"] for g in thematic.values() if g["label"] not in folder_set]
    return folder_cats + group_labels


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
    alphabet_dir = lang_config.get("alphabet_dir")

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

    # Folder-based category
    cat_dir = data_dir / category
    if cat_dir.exists():
        return load_category(cat_dir, word_columns)

    # Thematic group from groups.yaml
    thematic = _load_thematic_groups(lang_config)
    for group in thematic.values():
        if group["label"] == category:
            all_df = load_words(lang_config, "Alle woorden")
            filtered = all_df[all_df["dutch"].isin(group["words"])].copy()
            return filtered.reset_index(drop=True)

    # Fallback (shouldn't happen, but be safe)
    return load_category(data_dir / category, word_columns)
