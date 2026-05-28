# Ottolingo — Evidence-Based Learning Features Plan

## Achtergrond

Op basis van taalverwervingsonderzoek (SM-2/SuperMemo, Pimsleur, Ebbinghaus) en Arabisch-specifiek didactisch advies implementeren we de volgende 6 features om het leereffect te maximaliseren.

## 1. Spaced Repetition (SM-2 intervallen)

**Probleem:** Momenteel worden woorden fout-gewogen herhaald maar zonder tijdsplanning. Woorden die je gisteren goed had, hoef je vandaag niet te oefenen — maar over 6 dagen wél.

**Onderzoek:**
- SM-2 intervallen: 1 dag → 6 dagen → vorig interval × easiness factor (EF 1.3–2.5)
- Doel: 90% retentie
- Ebbinghaus: zonder herhaling halveert geheugen in dagen

**Implementatie:**
- Per woord opslaan: `last_reviewed`, `interval_days`, `easiness_factor`, `repetition_count`
- Bij app-start: bereken welke woorden "due" zijn (vandaag of eerder)
- Na beantwoording: update EF en interval op basis van resultaat
- Voortgang persistent opslaan (JSON bestand)
- Toon in UI: "X woorden te herhalen vandaag"

## 2. Dagelijks budget voor nieuwe woorden

**Probleem:** Bij 321 woorden kan een beginner overspoeld raken. 20 nieuwe woorden/dag levert ~200 reviews/dag — onhoudbaar.

**Onderzoek:**
- Optimaal voor beginners: 5-7 nieuwe woorden per dag
- Opschalen naar 10-15 na 2-3 weken
- Max 20 nieuwe woorden/dag (plafond)

**Implementatie:**
- Woorden markeren als "gezien" of "nieuw"
- Per sessie maximaal N nieuwe woorden introduceren (instelbaar, default 7)
- Prioriteit: eerst due reviews, dan nieuwe woorden
- Toon: "5 nieuwe woorden vandaag | 12 herhalingen"

## 3. Arabisch schrift oefenmodus

**Probleem:** Onderzoek zegt unaniem: leer het schrift vanaf dag 1, niet via transliteratie. Het Arabisch alfabet is leerbaar in 1-2 weken.

**Onderzoek:**
- 28 letters, 4 vormen per letter (geïsoleerd, begin, midden, eind)
- Fonetisch schrift — eenmaal geleerd kun je alles lezen
- Letters groeperen op vorm-gelijkenis versnelt het leren

**Implementatie:**
- Nieuwe modus: "Schrift oefenen"
- Oefentypen:
  - Letter herkennen (toon letter → kies klank)
  - Klank → letter kiezen
  - Positievarianten (begin/midden/eind van een woord)
- Data: `data/Alfabet/` met CSV: letter, naam, transliteratie, vorm_geisoleerd, vorm_begin, vorm_midden, vorm_eind
- Integratie met spaced repetition

## 4. Woordfamilies / wortelsysteem

**Probleem:** Arabisch vocabulaire is gebouwd op 3-letter wortels. Dit patroon herkennen versnelt het leren enorm (1 wortel → 5-10 woorden).

**Onderzoek:**
- 9.273 geregistreerde wortels in klassiek Arabisch
- k-t-b → kitaab (boek), kaatib (schrijver), maktaba (bibliotheek), maktub (geschreven)
- Patronen herkennen is effectiever dan losse woorden stampen

**Implementatie:**
- `root` kolom toevoegen aan CSV's (optioneel veld)
- In UI na beantwoording: "Dit woord komt van de wortel [k-t-b] (schrijven). Verwante woorden: ..."
- Modus "Woordfamilies": toon de wortel, laat alle bekende woorden met die wortel zien

## 5. Contextsinnen

**Probleem:** Losse woorden onthouden is minder effectief dan woorden in context. 6-12 ontmoetingen in context zijn nodig voor echte acquisitie.

**Onderzoek:**
- Contextual learning: woorden leren in zinnen levert betere retentie
- Nation (2001): meaning-focused input is essentieel naast deliberate study

**Implementatie:**
- `example` kolom toevoegen aan CSV's (optioneel): korte Arabische voorbeeldzin
- `example_nl` kolom: Nederlandse vertaling van de zin
- Tonen bij feedback (na goed of fout antwoord)
- Later: oefenmodus "Vul het ontbrekende woord in"

## 6. Sessie-timer met aanmoediging

**Probleem:** Beginners oefenen te lang of te kort. Onderzoek toont dat 15-20 min SRS optimaal is.

**Onderzoek:**
- Pomodoro-onderzoek: 25 min gestructureerd > langere ongeplande sessies
- SRS optimaal: 15-20 min review per dag
- Consistentie > duur

**Implementatie:**
- Timer tonen in sidebar (optioneel aan/uit)
- Na 15 min: zachte melding "Goed gedaan! Je hebt 15 minuten geoefend. Morgen weer?"
- Na 25 min: "Overweeg een pauze — kort en vaak is beter dan lang en soms"
- Streak-teller: hoeveel dagen achtereen geoefend
- Opslaan in persistent state

---

## Prioriteitsvolgorde

1. Spaced repetition + persistent opslag (fundament voor alles)
2. Dagelijks budget (voorkomt overwelming)
3. Sessie-timer (laagdrempelig, motiveert consistentie)
4. Schriftoefening (unaniem advies: doe dit vroeg)
5. Contextsinnen (verrijkt bestaande woorden)
6. Woordfamilies (krachtig maar vereist data-uitbreiding)

## Persistent state

Alle features vereisen dat voortgang bewaard blijft tussen sessies. Implementatie:
- JSON bestand: `~/.ottolingo/progress.json`
- Bevat: per-woord SRS state, sessie-geschiedenis, streak-data
- Laden bij app-start, opslaan bij elke update
