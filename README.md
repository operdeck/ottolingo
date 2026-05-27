# Ottolingo (Arabisch voor beginners)

Visueel oefenprogramma voor macOS (Apple Silicon) met:
- Nederlands -> Arabisch
- Arabisch -> Nederlands
- Luisteren -> Nederlands (met macOS `say`)
- Fout-gewogen herhaling: woorden die je vaker fout doet komen vaker terug

## Starten

1. Installeer dependencies en maak automatisch een `.venv` met uv:

```bash
uv sync
```

2. Start de app:

```bash
uv run streamlit run app.py
```

## Woordenlijst uitbreiden

De woorden staan in `data/words.csv` met kolommen:
- `dutch`
- `arabic`
- `transliteration`

Je kunt:
- direct regels toevoegen in het CSV-bestand

## Opmerking over audio

De luisteroefening gebruikt het macOS commando `say` met Arabische stem `Majed`.
Extra stemmen installeren op macOS: Systeeminstellingen -> Toegankelijkheid -> Gesproken materiaal -> Systeemstem -> Beheer stemmen (kies Arabisch).
Als dat op jouw systeem niet werkt, controleer of de stem beschikbaar is:

```bash
say -v '?'
```
