"""Pure question helpers (no streamlit)."""

from __future__ import annotations

import random

from config import MULTIPLE_CHOICE_DISTRACTORS
from utils.text import normalize, similarity_score


def grade_answer(question: dict, answer: str) -> bool:
    return normalize(answer) in [x for x in question["accepted"] if x]


def pick_confusable_options(
    correct: str,
    pool: list[str],
    confusions: dict[str, dict[str, int]] | None = None,
    word_key: str = "",
    n: int = MULTIPLE_CHOICE_DISTRACTORS,
) -> list[str]:
    if len(pool) <= n:
        return pool[:]

    confused_with = (confusions or {}).get(word_key, {})

    scored = []
    for item in pool:
        sim = similarity_score(correct, item)
        confusion_bonus = confused_with.get(item, 0) * 0.5
        scored.append((item, sim + confusion_bonus))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_confusable = [item for item, _ in scored[: n * 2]]
    random.shuffle(top_confusable)
    return top_confusable[:n]
