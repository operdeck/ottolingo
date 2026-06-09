# Ottolingo — project context (always read this first)

Ottolingo is a **Streamlit** language-practice app (Dutch ↔ Arabic / Japanese)
for macOS. Progress is stored per user in `~/.ottolingo/*.json`.

## File map

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

## Architecture rule

- `core/` and `utils/` are **pure** Python: no `streamlit`, no `st.session_state`.
- `ui/` holds all Streamlit code. Session-coupled helpers live in `ui/state.py`.
- `app.py` only wires things together; each practice screen is a `render()`
  function in its own `ui/*_mode.py` module.

## Commands

```bash
uv sync                       # install deps (run once)
uv run pytest                 # run tests — MUST stay green
uv run streamlit run app.py   # manual smoke test (optional)
```

## What "done" looks like

Keep modules small and single-purpose. New logic goes in the matching layer
(`core`/`utils` if pure, `ui` if it touches Streamlit). Behaviour stays stable
and tests stay green.
