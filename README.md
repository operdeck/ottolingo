<p align="center">
  <img src="docs/banner.svg" alt="Ottolingo - Leer Arabisch & Japans" width="100%"/>
</p>

# Ottolingo

Visueel oefenprogramma voor macOS met praktisch vocabulaire voor reizigers en dagelijks gebruik. Ondersteunt meerdere talen. Gebaseerd op taalverwervingsonderzoek (spaced repetition, active recall, optimale sessielengte).

## Talen

| Taal | Woorden | Schrift | Categorieën |
|------|---------|---------|-------------|
| 🇸🇦 Arabisch | 321 | 28 letters (4 vormen) | 7 thematisch |
| 🇯🇵 Japans | 325 | 46 Hiragana | 7 thematisch |

## Features

- Nederlands ↔ doeltaal oefenen (meerkeuze of typen)
- Luisteroefening met macOS text-to-speech (Arabisch: Majed, Japans: Kyoko)
- 7 thematische woordenlijsten per taal + schriftoefeningen
- **Multi-taal**: kies je taal in de sidebar; voortgang wordt per taal apart bewaard
- **Spaced repetition (SM-2)**: woorden komen terug op wetenschappelijk optimale intervallen (1d, 6d, 15d, 35d...)
- **Dagelijks budget**: max 7 nieuwe woorden per sessie, zodat reviews beheersbaar blijven
- **Confusion matrix**: onthoudt welke woorden je verwart en gebruikt die als slimmere afleiders
- **Schrift oefenen**: Arabisch alfabet (4 lettervarianten) of Hiragana (karakter ↔ klank); antwoord wordt meteen gecheckt na keuze, geen aparte "Controleer"-knop nodig; sessie-statistieken (% goed) zichtbaar naast het overzicht
- **Slimme feedback**: bij een fout antwoord ga je niet automatisch verder — je leest de correctie en drukt zelf op "Volgend woord"; bij goed antwoord mét extra uitleg wacht de app iets langer voordat er verdergegaan wordt
- **Woordfamilies**: toont verwante woorden via het Arabische wortelsysteem (k-t-b → kitaab, maktaba...)
- **Contextsinnen**: voorbeeldzinnen bij woorden voor beter onthouden
- **Sessie-statistieken & timer**: te herhalen, nieuw, streak en timer compact rechtsboven in de header — kost geen extra verticale ruimte
- Streak-teller: houdt bij hoeveel dagen op rij je oefent
- Commentaar bij woorden toont grammaticale context (geslacht, dialect, culturele noot); correct lettertype gebruikt in foutmeldingen
- Keuze uit lettertypen per taal (Arabisch: Amiri, Noto Naskh, Cairo, etc.)
- Voortgang wordt persistent opgeslagen per gebruiker (~/.ottolingo/)

## Starten

1. Installeer dependencies:

```bash
uv sync
```

2. Start de app:

```bash
uv run streamlit run app.py
```

## Tests

```bash
uv run pytest
```

## Data structuur

Woorden staan in `data/` georganiseerd per taal en categorie:

```
data/
├── arabic/
│   ├── Alfabet/letters.csv
│   ├── Basis/words.csv
│   ├── Begroetingen/words.csv
│   ├── Eten en drinken/words.csv
│   └── ...
├── japanese/
│   ├── Hiragana/characters.csv
│   ├── Basis/words.csv
│   ├── Begroetingen/words.csv
│   └── ...
```

Nieuwe categorie toevoegen = map aanmaken met een CSV erin. De app ontdekt categorieën automatisch.

### CSV-kolommen per taal

**Arabisch**: `dutch`, `arabic`, `transliteration`, `comment`, `root`, `example`, `example_nl`

**Japans**: `dutch`, `japanese`, `romaji`, `comment`, `example`, `example_nl`

(alleen `dutch`, doeltaal-kolom, en transcriptie zijn verplicht)

## Didactische achtergrond

Zie [docs/plans/learning-science.md](docs/plans/learning-science.md) voor de wetenschappelijke onderbouwing van de leerfeatures.

## Opmerking over audio

De luisteroefening gebruikt het macOS commando `say` met taalspecifieke stemmen.
Extra stemmen installeren: Systeeminstellingen → Toegankelijkheid → Gesproken materiaal → Systeemstem → Beheer stemmen (kies Arabisch of Japans).

## Ideeën voor verdere verbeteringen

- Meer talen toevoegen (zelfde structuur: languages.py + data/\<taal\>/)
- Lastige-woorden-modus: alleen woorden met laag succespercentage
- Mini-toets: 10 vragen met eindscore en verbeteradvies
- Sneltoetsen 1-5 voor meerkeuze
- Time challenge: zoveel mogelijk goed binnen 60/120 seconden
- Schrijfoefening: doeltaal typen vanaf transliteratie of audio
- Meer voorbeeldzinnen invullen voor alle categorieën
