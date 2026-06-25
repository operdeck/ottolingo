# Ottolingo — Claude instructions

> All project context and coding rules live in **`AGENTS.md`** in the repo root.
> Read that file before making any changes.

Key points from `AGENTS.md` to keep top of mind:

- Run `uv run pytest` after every change — tests must stay green.
- `core/` and `utils/` are pure Python (no `streamlit`). All Streamlit code goes in `ui/`.
- Make changes in a **feature branch**; open a PR rather than committing to `main`.
- Do not touch behaviour beyond what was requested.
