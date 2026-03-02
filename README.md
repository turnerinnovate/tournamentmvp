# Tournament MVP

Simple Python web app to track and store martial arts tournament results, including uploaded videos.

## Features
- Upload and store a tournament video file.
- Tag result by tournament name, date, and event:
  - forms, weapons, combat, sparring, creative form, creative weapon, xtreme form, xtreme weapon
- Opponent field required for sparring/combat.
- Three judges + three scores (0-9) required for form/weapon events.
- Final result (1st/2nd/3rd).
- Tournament class with auto-calculated points.
- Saved results table with direct video links.

## Run locally
```bash
python app.py
```

Then open: http://localhost:5000

## Notes
- Data is saved in SQLite (`tournament_results.db`).
- Uploaded videos are saved in `uploads/`.
