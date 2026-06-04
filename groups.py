"""
groups.py — thematic and morphological word-group helpers for Zoek & Oefen mode.

A group is a dict:
    {"label": str, "words": [dutch_word, ...]}

`get_all_groups` returns an ordered dict of {group_key: group_dict},
with thematic groups first, followed by Arabic root groups (if available).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import yaml

if TYPE_CHECKING:
    pass


def _groups_yaml_path(lang_config: dict) -> str:
    """Return the path to groups.yaml for the given language config."""
    lang_dir = lang_config.get("data_dir", "")
    return os.path.join(lang_dir, "groups.yaml")


def load_thematic_groups(lang_config: dict) -> dict[str, dict]:
    """Load manually curated thematic groups from groups.yaml.

    Returns {group_key: {"label": str, "words": [str]}} or {} if file missing.
    """
    path = _groups_yaml_path(lang_config)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    result: dict[str, dict] = {}
    for key, val in data.items():
        if isinstance(val, dict) and "label" in val and "words" in val:
            result[key] = {
                "label": str(val["label"]),
                "words": [str(w) for w in val.get("words", [])],
            }
    return result


def load_category_groups(lang_config: dict) -> dict[str, dict]:
    """Auto-derive one group per CSV category folder.

    Each folder under data/{language}/ (excluding the alphabet dir) becomes
    a group keyed by ``cat_{folder_name}`` containing all Dutch words in that
    folder's CSV files.  Requires no manual maintenance and is always in sync
    with the word lists.

    Returns {group_key: {"label": str, "words": [str]}}.
    """
    data_dir = Path(lang_config["data_dir"])
    alphabet_dir = lang_config.get("alphabet_dir", "")
    groups: dict[str, dict] = {}

    if not data_dir.exists():
        return groups

    for folder in sorted(data_dir.iterdir()):
        if not folder.is_dir() or folder.name == alphabet_dir:
            continue
        csv_files = sorted(folder.glob("*.csv"))
        if not csv_files:
            continue
        dutch_words: list[str] = []
        for csv_path in csv_files:
            try:
                df = pd.read_csv(csv_path)
                if "dutch" in df.columns:
                    dutch_words.extend(df["dutch"].dropna().astype(str).tolist())
            except Exception:  # noqa: BLE001
                continue
        if len(dutch_words) >= 2:
            key = f"cat_{folder.name.replace(' ', '_').lower()}"
            groups[key] = {"label": folder.name, "words": dutch_words}
    return groups


def load_root_groups(words_df: pd.DataFrame) -> dict[str, dict]:
    """Derive root-based groups from the 'root' column (Arabic only).

    Only groups with ≥ 2 Dutch words sharing the same root are included.
    Returns {root_key: {"label": str, "words": [str]}}.
    """
    if "root" not in words_df.columns:
        return {}
    root_col = words_df["root"].dropna().astype(str)
    root_col = root_col[root_col.str.strip() != ""]
    if root_col.empty:
        return {}

    groups: dict[str, dict] = {}
    for root, sub in words_df[words_df["root"].notna()].groupby("root"):
        root = str(root).strip()
        if not root:
            continue
        dutch_words = sub["dutch"].dropna().tolist()
        if len(dutch_words) >= 2:
            safe_key = f"root_{root.replace('-', '_')}"
            groups[safe_key] = {
                "label": f"Wortelletters [{root}]",
                "words": dutch_words,
            }
    return groups


def get_all_groups(
    lang_config: dict, words_df: pd.DataFrame
) -> dict[str, dict]:
    """Return all groups for a language.

    Order: YAML thematic groups → CSV category groups → Arabic root groups.
    YAML groups take priority: if a YAML key already exists, the auto-derived
    category group with the same key is skipped (no overwrite).
    Only groups whose words actually appear in words_df are kept.
    """
    available = set(words_df["dutch"].dropna().astype(str).tolist())

    thematic = load_thematic_groups(lang_config)
    category = load_category_groups(lang_config)
    root = load_root_groups(words_df)

    # Merge: YAML first, then category (no overwrite), then root
    combined: dict[str, dict] = {}
    for source in (thematic, category, root):
        for key, group in source.items():
            if key not in combined:
                combined[key] = group

    merged: dict[str, dict] = {}
    for key, group in combined.items():
        filtered_words = [w for w in group["words"] if w in available]
        if len(filtered_words) >= 2:
            merged[key] = {"label": group["label"], "words": filtered_words}
    return merged


def find_groups_for_word(dutch_word: str, groups: dict[str, dict]) -> list[str]:
    """Return the list of group keys that contain dutch_word."""
    return [
        key
        for key, group in groups.items()
        if dutch_word in group["words"]
    ]
