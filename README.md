# Tournament MVP

Simple local web app to track martial arts tournament results, upload videos, and store everything in SQLite.

## Run locally
```bash
python app.py
```

Then open:
- http://localhost:5000/
- http://localhost:5000/index.html

## What it supports
- Video upload + storage in `uploads/`
- Tournament name, date, event type
- Events: forms, weapons, combat, sparring, creative form, creative weapon, xtreme form, xtreme weapon
- Opponent required for sparring/combat
- 3 judges + 3 scores (0-9) required for form/weapon events
- Final result: 1st / 2nd / 3rd
- Tournament class based points auto-calculation (local/regional/state/national)
- Saved results list with video links

## Data storage
- SQLite DB: `tournament_results.db`
- Table: `results`
