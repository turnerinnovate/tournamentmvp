# Tournament MVP

Simple HTML web app to track and store martial arts tournament results locally in your browser.

## Features
- Optional video upload for each result entry.
- Tag each result with:
  - tournament name
  - date
  - event (forms, weapons, combat, sparring, creative form, creative weapon, xtreme form, xtreme weapon)
- Opponent field required for sparring/combat.
- Three judge names + three scores (0-9) required for forms/weapon categories.
- Final placement: 1st / 2nd / 3rd.
- Tournament classes and points:
  - Intra school: 1st=3, 2nd=2, 3rd=1
  - Regional B: 1st=5, 2nd=3, 3rd=1
  - Regional A: 1st=8, 2nd=5, 3rd=3
  - Nationals: 1st=15, 2nd=10, 3rd=5
  - Worlds: 1st=20, 2nd=15, 3rd=10
- Saved results table with video links when a video is attached.

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
- Uploaded videos (if attached) are stored as data URLs in browser storage for this site.
- Storage size depends on browser limits.
