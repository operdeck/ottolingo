# Coding rules for Ottolingo (keep context small)

You are likely running a small local model with a limited context window.
Work in **tiny, verifiable steps**. Do not try to hold the whole repo in mind.

## Golden rules

1. **One change at a time.** Make a small, focused edit, then verify before
   continuing.
2. **Read before you edit.** Open the file you are changing first. Use the file
   map in `01-project-context.md` to find the right module.
3. **Run `uv run pytest` after every change.** If it is not green, fix or revert
   before moving on. Never proceed on red tests.
4. **Respect the layers.** Pure logic (no `streamlit`, no `st.session_state`)
   goes in `core/` or `utils/`. Anything that touches Streamlit goes in `ui/`;
   session-coupled helpers belong in `ui/state.py`.
5. **Keep public names stable.** If you move a function, update its imports so
   call sites keep working.
6. **Do not touch behaviour unless asked.** No new features, no renames of
   existing UI text, no "improvements" beyond the request.
7. **Keep `srs.py` and `groups.py` pure.** No Streamlit imports there.
8. **Target file size:** keep modules small and single-purpose; prefer ≤ ~250
   lines. If a file grows past that, consider splitting it.
