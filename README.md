# Ottolingo (Arabisch voor beginners)

Visueel oefenprogramma voor macOS met praktisch Arabisch vocabulaire voor reizigers en dagelijks gebruik. Gebaseerd op taalverwervingsonderzoek (spaced repetition, active recall, optimale sessielengte).

## Features

- Nederlands ↔ Arabisch oefenen (meerkeuze of typen)
- Luisteroefening met macOS text-to-speech (stem: Majed)
- 7 thematische woordenlijsten + alfabet (321 woorden, 28 letters)
- **Spaced repetition (SM-2)**: woorden komen terug op wetenschappelijk optimale intervallen (1d, 6d, 15d, 35d...)
- **Dagelijks budget**: max 7 nieuwe woorden per sessie, zodat reviews beheersbaar blijven
- **Confusion matrix**: onthoudt welke woorden je verwart en gebruikt die als slimmere afleiders
- **Schrift oefenen**: leer de 28 Arabische letters (geïsoleerd, begin, midden, eind)
- **Woordfamilies**: toont verwante woorden via het Arabische wortelsysteem (k-t-b → kitaab, maktaba...)
- **Contextsinnen**: voorbeeldzinnen bij woorden voor beter onthouden
- **Sessie-timer**: moedigt korte dagelijkse sessies aan (15-20 min optimaal)
- Streak-teller: houdt bij hoeveel dagen op rij je oefent
- Commentaar bij woorden toont grammaticale context (geslacht, dialect, culturele noot)
- Keuze uit Arabische lettertypen (Amiri, Noto Naskh, Cairo, etc.)
- Voortgang wordt persistent opgeslagen (~/.ottolingo/progress.json)

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
├── Alfabet/letters.csv
├── Basis/words.csv
├── Begroetingen/words.csv
├── Eten en drinken/words.csv
└── ...
```

Nieuwe categorie toevoegen = map aanmaken met een CSV erin. De app ontdekt categorieën automatisch.

CSV-kolommen: `dutch`, `arabic`, `transliteration`, `comment`, `root`, `example`, `example_nl`
(alleen `dutch`, `arabic`, `transliteration` zijn verplicht)

## Didactische achtergrond

Zie [docs/plans/learning-science.md](docs/plans/learning-science.md) voor de wetenschappelijke onderbouwing van de leerfeatures.

## Opmerking over audio

De luisteroefening gebruikt het macOS commando `say` met Arabische stem.
Extra stemmen installeren: Systeeminstellingen → Toegankelijkheid → Gesproken materiaal → Systeemstem → Beheer stemmen (kies Arabisch).

## Ideeën voor verdere verbeteringen

- Lastige-woorden-modus: alleen woorden met laag succespercentage
- Mini-toets: 10 vragen met eindscore en verbeteradvies
- Sneltoetsen 1-5 voor meerkeuze
- Time challenge: zoveel mogelijk goed binnen 60/120 seconden
- Schrijfoefening: Arabisch typen vanaf transliteratie of audio
- Meer contextsinnen en wortels invullen voor alle categorieën
