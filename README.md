# Ottolingo (Arabisch voor beginners)

Visueel oefenprogramma voor macOS met praktisch Arabisch vocabulaire voor reizigers en dagelijks gebruik.

## Features

- Nederlands ↔ Arabisch oefenen (meerkeuze of typen)
- Luisteroefening met macOS text-to-speech (stem: Majed)
- 7 thematische woordenlijsten: Basis, Begroetingen, Eten & drinken, Familie & mensen, Reizen, Tijd & getallen, Winkelen (321 woorden)
- Slimme herhaling: fout-gewogen selectie + confusion matrix zorgt dat je zwakke plekken vaker oefent
- Vergelijkbare woorden verschijnen vaker als afleiders bij meerkeuze
- Commentaar bij woorden toont grammaticale context (geslacht, dialect, culturele noot)
- Keuze uit Arabische lettertypen (Amiri, Noto Naskh, Cairo, etc.)

## Starten

1. Installeer dependencies:

```bash
uv sync
```

2. Start de app:

```bash
uv run streamlit run app.py
```

## Woordenlijst uitbreiden

Woorden staan in `data/` met per categorie een submap:

```
data/
├── Basis/words.csv
├── Begroetingen/words.csv
├── Eten en drinken/words.csv
└── ...
```

Nieuwe categorie toevoegen = map aanmaken met een CSV erin. De app ontdekt categorieën automatisch. CSV-kolommen: `dutch`, `arabic`, `transliteration`, `comment`.

## Opmerking over audio

De luisteroefening gebruikt het macOS commando `say` met Arabische stem.
Extra stemmen installeren: Systeeminstellingen → Toegankelijkheid → Gesproken materiaal → Systeemstem → Beheer stemmen (kies Arabisch).

## Ideeën voor verdere verbeteringen

- Spaced repetition met dagplanning (vandaag, morgen, over 3 dagen)
- Voortgang persistent opslaan tussen sessies
- Lastige-woorden-modus: alleen woorden met laag succespercentage
- Mini-toets: 10 vragen met eindscore en verbeteradvies
- Sneltoetsen 1-5 voor meerkeuze
- Time challenge: zoveel mogelijk goed binnen 60/120 seconden
- Schrijfoefening: Arabisch typen vanaf transliteratie of audio
- Alfabet oefenen: Arabische letters (vorm, klank, positie in woord)
