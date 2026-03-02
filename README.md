# Tournament MVP

Simple HTML web app to track and store martial arts tournament results (including uploaded video) locally in your browser.

## Features
- Upload a video for each result entry.
- Tag each result with:
  - tournament name
  - date
  - event (forms, weapons, combat, sparring, creative form, creative weapon, xtreme form, xtreme weapon)
- Opponent field required for sparring/combat.
- Three judge names + three scores (0-9) required for forms/weapon categories.
- Final placement: 1st / 2nd / 3rd.
- Tournament class with auto-calculated points.
- Saved results table with video links.

## Run locally
No build step is required.

- Option 1: Open `index.html` directly in a browser.
- Option 2 (recommended): serve with Python:

```bash
python -m http.server 8000
```

Then open http://localhost:8000.

## Data storage
- Results are saved in `localStorage` in your browser.
- Uploaded videos are stored as data URLs in browser storage for this site.
- Storage size depends on browser limits.
