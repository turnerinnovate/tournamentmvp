from __future__ import annotations

import cgi
import json
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
INDEX_FILE = BASE_DIR / "index.html"
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


def get_results() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM results ORDER BY tournament_date DESC, created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def save_result(data: dict) -> None:
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


class AppHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict | list, code: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_index(self) -> None:
        if not INDEX_FILE.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "index.html not found")
            return
        content = INDEX_FILE.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path in {"/", "/index.html"}:
            self._serve_index()
            return

        if parsed.path == "/api/results":
            results = get_results()
            for item in results:
                item["video_url"] = f"/uploads/{quote(item['video_filename'])}"
            self._send_json(results)
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
        if self.path != "/api/results":
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

        def val(name: str) -> str:
            value = form.getvalue(name)
            return value.strip() if isinstance(value, str) else ""

        tournament_name = val("tournament_name")
        tournament_date = val("tournament_date")
        event_type = val("event_type").lower()
        opponent = val("opponent")
        judge1_name, judge2_name, judge3_name = val("judge1_name"), val("judge2_name"), val("judge3_name")
        score1_raw, score2_raw, score3_raw = val("score1"), val("score2"), val("score3")
        placement, tournament_class = val("placement"), val("tournament_class")
        video = form["video"] if "video" in form else None

        if not tournament_name or not tournament_date or not event_type:
            return self._send_json({"error": "Tournament name, date, and event are required."}, HTTPStatus.BAD_REQUEST)
        if event_type in MATCH_EVENTS and not opponent:
            return self._send_json({"error": "Opponent is required for sparring/combat events."}, HTTPStatus.BAD_REQUEST)
        if placement not in PLACEMENT_BASE_POINTS:
            return self._send_json({"error": "Placement must be 1st, 2nd, or 3rd."}, HTTPStatus.BAD_REQUEST)
        if tournament_class not in CLASS_MULTIPLIERS:
            return self._send_json({"error": "Please select a tournament class."}, HTTPStatus.BAD_REQUEST)

        score1 = score2 = score3 = None
        if event_type in FORM_EVENTS:
            try:
                score1, score2, score3 = float(score1_raw), float(score2_raw), float(score3_raw)
            except ValueError:
                return self._send_json({"error": "All 3 scores are required for forms/weapon events."}, HTTPStatus.BAD_REQUEST)
            if any(score < 0 or score > 9 for score in [score1, score2, score3]):
                return self._send_json({"error": "Scores must be between 0 and 9."}, HTTPStatus.BAD_REQUEST)
            if not judge1_name or not judge2_name or not judge3_name:
                return self._send_json({"error": "Please add all 3 judge names for forms/weapon events."}, HTTPStatus.BAD_REQUEST)

        if not video or not getattr(video, "filename", ""):
            return self._send_json({"error": "Please upload a video file."}, HTTPStatus.BAD_REQUEST)

        original_name = os.path.basename(video.filename)
        if not allowed_file(original_name):
            return self._send_json({"error": "Invalid video type. Use mp4/mov/avi/mkv/webm."}, HTTPStatus.BAD_REQUEST)

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
        self._send_json({"ok": True, "message": "Result saved successfully."}, HTTPStatus.CREATED)


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Serving on http://{HOST}:{PORT}")
    server.serve_forever()
