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

## Ideeën voor verdere verbeteringen

### Quick wins

- Lastige woorden modus: alleen woorden met laag succespercentage
- Thema-sets: woorden per onderwerp (eten, reizen, werk, familie)
- Mini-toets: 10 willekeurige vragen met eindscore en verbeteradvies
- Sneltoetsen: toetsen 1-5 voor meerkeuze om sneller te oefenen
- Alfabet oefenen: expliciete modus voor Arabische letters (vorm, klank, transliteratie)

### Middelgrote features

- Time challenge (game mode): tijdslimiet (bijv. 60 of 120 sec) en zoveel mogelijk goede antwoorden
- Zinsniveau: korte voorbeeldzinnen per woord (niet alleen losse woorden)
- Dictee modus: alleen luisteren en zelf typen zonder opties
- Schrijfoefening Arabisch: typ Arabisch vanaf transliteratie of audio
- Omgekeerde transliteratie: Arabisch zien en transliteratie invullen
- Foutuitleg: toon waarom een antwoord fout was + vergelijkbare woorden

### Grotere uitbreidingen

- Herhaalplanning: spaced repetition met dagplanning (vandaag, morgen, over 3 dagen)
- Voortgang opslaan: scores persistent bewaren tussen sessies
- Export/import: woordenlijst en voortgang als CSV/JSON
