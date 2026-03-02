from __future__ import annotations

import cgi
import html
import os
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "tournament_results.db"
HOST = "0.0.0.0"
PORT = 5000

UPLOAD_DIR.mkdir(exist_ok=True)

FORM_EVENTS = {
    "forms",
    "weapons",
    "creative form",
    "creative weapon",
    "xtreme form",
    "xtreme weapon",
}
MATCH_EVENTS = {"sparring", "combat"}
ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}
CLASS_MULTIPLIERS = {"local": 1, "regional": 2, "state": 3, "national": 4}
PLACEMENT_BASE_POINTS = {"1st": 10, "2nd": 7, "3rd": 5}


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_name TEXT NOT NULL,
                tournament_date TEXT NOT NULL,
                event_type TEXT NOT NULL,
                opponent TEXT,
                judge1_name TEXT,
                judge2_name TEXT,
                judge3_name TEXT,
                score1 REAL,
                score2 REAL,
                score3 REAL,
                placement TEXT NOT NULL,
                tournament_class TEXT NOT NULL,
                tournament_points INTEGER NOT NULL,
                video_filename TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_results() -> list[sqlite3.Row]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM results ORDER BY tournament_date DESC, created_at DESC"
        ).fetchall()


def save_result(data: dict[str, str | float | int | None]) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO results (
                tournament_name, tournament_date, event_type, opponent,
                judge1_name, judge2_name, judge3_name,
                score1, score2, score3,
                placement, tournament_class, tournament_points, video_filename
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["tournament_name"],
                data["tournament_date"],
                data["event_type"],
                data["opponent"],
                data["judge1_name"],
                data["judge2_name"],
                data["judge3_name"],
                data["score1"],
                data["score2"],
                data["score3"],
                data["placement"],
                data["tournament_class"],
                data["tournament_points"],
                data["video_filename"],
            ),
        )


def render_page(message: str = "") -> str:
    rows = get_results()
    flash = f'<div class="flash">{html.escape(message)}</div>' if message else ""

    table_rows = ""
    if rows:
        for row in rows:
            judges = "-"
            if row["score1"] is not None:
                judges = (
                    f"{html.escape(row['judge1_name'] or '')}: {row['score1']}<br>"
                    f"{html.escape(row['judge2_name'] or '')}: {row['score2']}<br>"
                    f"{html.escape(row['judge3_name'] or '')}: {row['score3']}"
                )

            table_rows += f"""
              <tr>
                <td>{html.escape(row['tournament_name'])}</td>
                <td>{html.escape(row['tournament_date'])}</td>
                <td>{html.escape(row['event_type'].title())}</td>
                <td>{html.escape(row['opponent'] or '-')}</td>
                <td>{judges}</td>
                <td>{html.escape(row['placement'])}</td>
                <td>{html.escape(row['tournament_class'].title())}</td>
                <td>{row['tournament_points']}</td>
                <td><a href="/uploads/{quote(row['video_filename'])}" target="_blank">View</a></td>
              </tr>
            """
    else:
        table_rows = '<tr><td colspan="9">No results saved yet.</td></tr>'

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Martial Arts Tournament Tracker</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f7f7f9; color: #1e1e1e; }}
    .container {{ max-width: 1080px; margin: 2rem auto; padding: 1rem; }}
    .card {{ background: #fff; border-radius: 10px; padding: 1rem 1.25rem; box-shadow: 0 2px 12px rgba(0,0,0,0.08); margin-bottom: 1rem; }}
    form {{ display: grid; grid-template-columns: repeat(2, minmax(200px, 1fr)); gap: 12px 16px; }}
    .full {{ grid-column: 1 / -1; }}
    label {{ display: block; font-weight: 600; margin-bottom: 4px; }}
    input, select {{ width: 100%; box-sizing: border-box; padding: 8px 10px; border: 1px solid #ccc; border-radius: 8px; }}
    button {{ padding: 10px 16px; border: none; border-radius: 8px; background: #0b61d8; color: white; font-weight: 700; cursor: pointer; }}
    .flash {{ background: #f0f6ff; border: 1px solid #b7d1ff; color: #18448b; border-radius: 8px; padding: 10px; margin-bottom: 12px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
    th, td {{ border-bottom: 1px solid #e8e8e8; padding: 8px; text-align: left; vertical-align: top; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>Martial Arts Tournament Result Tracker</h1>
      {flash}
      <form method="POST" enctype="multipart/form-data">
        <div><label>Tournament Name</label><input name="tournament_name" required /></div>
        <div><label>Date</label><input name="tournament_date" type="date" required /></div>
        <div>
          <label>Event</label>
          <select id="event_type" name="event_type" required>
            <option value="">Select event...</option>
            <option value="forms">Forms</option><option value="weapons">Weapons</option>
            <option value="combat">Combat</option><option value="sparring">Sparring</option>
            <option value="creative form">Creative Form</option><option value="creative weapon">Creative Weapon</option>
            <option value="xtreme form">Xtreme Form</option><option value="xtreme weapon">Xtreme Weapon</option>
          </select>
        </div>
        <div><label>Opponent (sparring/combat)</label><input id="opponent" name="opponent" /></div>
        <div><label>Final Result</label><select name="placement" required><option value="">Select...</option><option value="1st">1st</option><option value="2nd">2nd</option><option value="3rd">3rd</option></select></div>
        <div><label>Tournament Class</label><select name="tournament_class" required><option value="">Select...</option><option value="local">Local (x1)</option><option value="regional">Regional (x2)</option><option value="state">State (x3)</option><option value="national">National (x4)</option></select></div>
        <div><label>Judge 1</label><input id="judge1_name" name="judge1_name" /></div>
        <div><label>Score 1 (0-9)</label><input id="score1" name="score1" type="number" min="0" max="9" step="0.1" /></div>
        <div><label>Judge 2</label><input id="judge2_name" name="judge2_name" /></div>
        <div><label>Score 2 (0-9)</label><input id="score2" name="score2" type="number" min="0" max="9" step="0.1" /></div>
        <div><label>Judge 3</label><input id="judge3_name" name="judge3_name" /></div>
        <div><label>Score 3 (0-9)</label><input id="score3" name="score3" type="number" min="0" max="9" step="0.1" /></div>
        <div class="full"><label>Upload Video</label><input name="video" type="file" accept="video/*" required /></div>
        <div class="full"><button type="submit">Save Tournament Result</button></div>
      </form>
    </div>

    <div class="card">
      <h2>Saved Results</h2>
      <table>
        <thead><tr><th>Tournament</th><th>Date</th><th>Event</th><th>Opponent</th><th>Judges / Scores</th><th>Placement</th><th>Class</th><th>Points</th><th>Video</th></tr></thead>
        <tbody>{table_rows}</tbody>
      </table>
    </div>
  </div>
  <script>
    const formEvents = new Set(["forms", "weapons", "creative form", "creative weapon", "xtreme form", "xtreme weapon"]);
    const matchEvents = new Set(["sparring", "combat"]);
    const eventSelect = document.getElementById("event_type");
    const opponentInput = document.getElementById("opponent");
    const judgeInputs = ["judge1_name", "judge2_name", "judge3_name", "score1", "score2", "score3"].map((id) => document.getElementById(id));
    function refreshConditionalFields() {{
      const event = eventSelect.value;
      opponentInput.required = matchEvents.has(event);
      judgeInputs.forEach((input) => input.required = formEvents.has(event));
    }}
    eventSelect.addEventListener("change", refreshConditionalFields);
    refreshConditionalFields();
  </script>
</body>
</html>"""


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            params = parse_qs(parsed.query)
            message = params.get("message", [""])[0]
            page = render_page(message)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page.encode("utf-8"))
            return

        if parsed.path.startswith("/uploads/"):
            filename = Path(parsed.path.replace("/uploads/", "", 1)).name
            target = UPLOAD_DIR / filename
            if target.exists() and target.is_file():
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/octet-stream")
                self.end_headers()
                self.wfile.write(target.read_bytes())
                return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            },
        )

        def get_value(name: str) -> str:
            value = form.getvalue(name)
            return value.strip() if isinstance(value, str) else ""

        tournament_name = get_value("tournament_name")
        tournament_date = get_value("tournament_date")
        event_type = get_value("event_type").lower()
        opponent = get_value("opponent")

        judge1_name = get_value("judge1_name")
        judge2_name = get_value("judge2_name")
        judge3_name = get_value("judge3_name")

        score1_raw = get_value("score1")
        score2_raw = get_value("score2")
        score3_raw = get_value("score3")

        placement = get_value("placement")
        tournament_class = get_value("tournament_class")

        video = form["video"] if "video" in form else None

        if not tournament_name or not tournament_date or not event_type:
            return self.redirect_with_message("Tournament name, date, and event are required.")
        if event_type in MATCH_EVENTS and not opponent:
            return self.redirect_with_message("Opponent is required for sparring/combat events.")
        if placement not in PLACEMENT_BASE_POINTS:
            return self.redirect_with_message("Placement must be 1st, 2nd, or 3rd.")
        if tournament_class not in CLASS_MULTIPLIERS:
            return self.redirect_with_message("Please select a tournament class.")

        score1 = score2 = score3 = None
        if event_type in FORM_EVENTS:
            try:
                score1, score2, score3 = float(score1_raw), float(score2_raw), float(score3_raw)
            except ValueError:
                return self.redirect_with_message("All three scores are required for forms/weapon events.")
            if any(score < 0 or score > 9 for score in [score1, score2, score3]):
                return self.redirect_with_message("Scores must be between 0 and 9.")
            if not judge1_name or not judge2_name or not judge3_name:
                return self.redirect_with_message("Please add all three judge names for forms/weapon events.")

        if not video or not getattr(video, "filename", ""):
            return self.redirect_with_message("Please upload a video file.")

        original_name = os.path.basename(video.filename)
        if not allowed_file(original_name):
            return self.redirect_with_message("Invalid video type. Allowed: mp4, mov, avi, mkv, webm.")

        unique_name = f"{uuid4().hex}_{original_name}"
        with open(UPLOAD_DIR / unique_name, "wb") as f:
            f.write(video.file.read())

        points = PLACEMENT_BASE_POINTS[placement] * CLASS_MULTIPLIERS[tournament_class]
        save_result(
            {
                "tournament_name": tournament_name,
                "tournament_date": tournament_date,
                "event_type": event_type,
                "opponent": opponent or None,
                "judge1_name": judge1_name or None,
                "judge2_name": judge2_name or None,
                "judge3_name": judge3_name or None,
                "score1": score1,
                "score2": score2,
                "score3": score3,
                "placement": placement,
                "tournament_class": tournament_class,
                "tournament_points": points,
                "video_filename": unique_name,
            }
        )
        return self.redirect_with_message("Result saved successfully.")

    def redirect_with_message(self, message: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", f"/?message={quote(message)}")
        self.end_headers()


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Serving on http://{HOST}:{PORT}")
    server.serve_forever()
