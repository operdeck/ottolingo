# Ottolingo — agent instructions

> **Canonical file.** All other agent/tool instruction files (`.github/copilot-instructions.md`,
> `CLAUDE.md`, `.clinerules/`) derive from this one. Keep this file up to date when the
> project changes; then propagate to the others.

---

## Project context

Ottolingo is a **Streamlit** language-practice app (Dutch ↔ Arabic / Japanese / Italian)
for macOS. Progress is stored per user in `~/.ottolingo/*.json`.

### File map

| File | Role |
|------|------|
| `app.py` | Streamlit entrypoint. Thin orchestrator: page config, header, dispatch. |
| `config.py` / `config.yaml` | Settings loader + values. |
| `languages.py` | `LANGUAGES` dict + `get_lang_config()`. |
| `srs.py` | SM-2 algorithm, progress I/O, users, streak. Pure (no streamlit). |
| `groups.py` | Thematic / category / root word groups. Pure (no streamlit). |
| `core/words.py` | CSV word-list loading. Pure. |
| `core/questions.py` | `grade_answer`, `pick_confusable_options`. Pure. |
| `utils/text.py` | `normalize`, `similarity_score`. Pure. |
| `utils/audio.py` | macOS `say` text-to-speech. Pure. |
| `ui/styles.py` | The app CSS (`APP_CSS`). |
| `ui/state.py` | Session/progress helpers (uses `st.session_state`). |
| `ui/login.py` | Login / user-selection screen. |
| `ui/sidebar.py` | Sidebar: language, mode, word list, font, voice. |
| `ui/script_mode.py` | Alphabet / Hiragana practice screen. |
| `ui/explore_mode.py` | Zoek & Oefen (search + drill) screen. |
| `ui/practice_mode.py` | Main word-practice screen. |
| `tests/` | `pytest` + Streamlit `AppTest` smoke tests. |
| `data/<lang>/<Category>/*.csv` | Word lists. |

### Architecture rule

- `core/` and `utils/` are **pure** Python: no `streamlit`, no `st.session_state`.
- `ui/` holds all Streamlit code. Session-coupled helpers live in `ui/state.py`.
- `app.py` only wires things together; each practice screen is a `render()`
  function in its own `ui/*_mode.py` module.

### Commands

```bash
uv sync                       # install deps (run once)
uv run pytest                 # run tests — MUST stay green
uv run streamlit run app.py   # manual smoke test (optional)
```

---

## Small-model friendliness

This codebase is intentionally designed to be navigable by **small local models
with limited context windows**. Preserve these properties when making changes:

- **Keep files small and focused.** Each module should be understandable in
  isolation without loading the whole repo. Prefer ≤ ~250 lines.
- **Work in small, verifiable steps.** One logical change at a time; run
  `uv run pytest` between steps.
- **Explicit over implicit.** No magic imports, no hidden indirection, no
  clever metaclass tricks. A model should be able to follow the call chain
  by reading two or three files at most.
- **Self-contained functions.** Avoid functions that silently depend on
  far-away global state. Pass data in, return data out.
- **Clear, descriptive names.** Names should make the purpose obvious without
  needing to read the body.

---

## Coding rules

1. **Read before you edit.** Open the file you are changing first. Use the file
   map above to find the right module.
2. **Run `uv run pytest` after every change.** If it is not green, fix or revert
   before moving on. Never proceed on red tests.
3. **Respect the layers.** Pure logic (no `streamlit`, no `st.session_state`)
   goes in `core/` or `utils/`. Anything that touches Streamlit goes in `ui/`;
   session-coupled helpers belong in `ui/state.py`.
4. **Keep public names stable.** If you move a function, update its imports so
   call sites keep working.
5. **Do not touch behaviour unless asked.** No new features, no renames of
   existing UI text, no "improvements" beyond the request.
6. **Keep `srs.py` and `groups.py` pure.** No Streamlit imports there.
7. **Target file size:** keep modules small and single-purpose; prefer ≤ ~250
   lines. If a file grows past that, consider splitting it.
8. **Make changes in a branch.** For every enhancement or bug fix, create a
   feature branch and open a PR rather than committing directly to `main`.

### What "done" looks like

Behaviour stays stable, tests stay green, and the change is scoped only to what
was requested.
