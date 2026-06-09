"""Pure text helpers: no streamlit, no I/O."""

from __future__ import annotations


def normalize(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def similarity_score(a: str, b: str) -> float:
    a, b = a.strip(), b.strip()
    if not a or not b:
        return 0.0
    prefix = 0
    for c1, c2 in zip(a, b):
        if c1 == c2:
            prefix += 1
        else:
            break
    set_a, set_b = set(a), set(b)
    overlap = len(set_a & set_b) / max(len(set_a | set_b), 1)
    len_sim = 1.0 - abs(len(a) - len(b)) / max(len(a), len(b), 1)
    return prefix / max(len(a), len(b)) * 0.4 + overlap * 0.4 + len_sim * 0.2
