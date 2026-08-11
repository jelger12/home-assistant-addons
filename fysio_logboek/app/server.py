"""Fysio Logboek — kleine API met SQLite-opslag.

De database staat in /data, dat is het persistente volume van de add-on en
gaat mee in de Home Assistant back-ups.
"""

import csv
import io
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

DB_PATH = os.environ.get("FYSIO_DB", "/data/fysio.db")
STATIC_DIR = Path(__file__).parent / "static"
UNITS = {"kg", "niveau", "geen"}

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS exercises (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    unit         TEXT NOT NULL DEFAULT 'kg',
    daily_target INTEGER NOT NULL DEFAULT 2,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS entries (
    id          TEXT PRIMARY KEY,
    exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    date        TEXT NOT NULL,
    reps        INTEGER NOT NULL,
    weight      REAL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS entries_exercise_date ON entries (exercise_id, date);
"""


@contextmanager
def db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id() -> str:
    return secrets.token_hex(6)


app = FastAPI(title="Fysio Logboek", docs_url=None, redoc_url=None)


@app.on_event("startup")
def init_db() -> None:
    with db() as conn:
        conn.executescript(SCHEMA)
        # Bestaande database van voor het dagdoel bijwerken.
        columns = {r["name"] for r in conn.execute("PRAGMA table_info(exercises)")}
        if "daily_target" not in columns:
            conn.execute(
                "ALTER TABLE exercises ADD COLUMN daily_target INTEGER NOT NULL DEFAULT 2"
            )


# ---------- modellen ----------


class ExerciseIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    unit: str = "kg"
    daily_target: int = Field(default=2, ge=1, le=12)


class EntryIn(BaseModel):
    exercise_id: str
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    reps: int = Field(ge=0, le=10_000)
    weight: Optional[float] = Field(default=None, ge=0, le=10_000)


class ImportIn(BaseModel):
    csv: str


# ---------- lezen ----------


@app.get("/api/state")
def get_state():
    with db() as conn:
        exercises = [
            dict(r)
            for r in conn.execute(
                "SELECT id, name, unit, daily_target FROM exercises "
                "ORDER BY sort_order, created_at"
            )
        ]
        entries = [
            dict(r)
            for r in conn.execute(
                "SELECT id, exercise_id, date, reps, weight FROM entries "
                "ORDER BY date DESC, created_at DESC"
            )
        ]
    return {"exercises": exercises, "entries": entries}


# ---------- oefeningen ----------


@app.post("/api/exercises", status_code=201)
def add_exercise(payload: ExerciseIn):
    if payload.unit not in UNITS:
        raise HTTPException(400, f"Eenheid moet een van {sorted(UNITS)} zijn")
    row = {
        "id": new_id(),
        "name": payload.name.strip(),
        "unit": payload.unit,
        "daily_target": payload.daily_target,
        "created_at": now(),
    }
    with db() as conn:
        order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 AS n FROM exercises"
        ).fetchone()["n"]
        conn.execute(
            "INSERT INTO exercises "
            "(id, name, unit, daily_target, sort_order, created_at) "
            "VALUES (:id, :name, :unit, :daily_target, :order, :created_at)",
            {**row, "order": order},
        )
    row.pop("created_at")
    return row


@app.patch("/api/exercises/{exercise_id}")
def rename_exercise(exercise_id: str, payload: ExerciseIn):
    with db() as conn:
        cur = conn.execute(
            "UPDATE exercises SET name = ?, unit = ?, daily_target = ? WHERE id = ?",
            (payload.name.strip(), payload.unit, payload.daily_target, exercise_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "Oefening bestaat niet")
    return {"ok": True}


@app.delete("/api/exercises/{exercise_id}", status_code=204)
def delete_exercise(exercise_id: str):
    with db() as conn:
        conn.execute("DELETE FROM exercises WHERE id = ?", (exercise_id,))


# ---------- sessies ----------


@app.post("/api/entries", status_code=201)
def add_entry(payload: EntryIn):
    with db() as conn:
        ex = conn.execute(
            "SELECT unit FROM exercises WHERE id = ?", (payload.exercise_id,)
        ).fetchone()
        if ex is None:
            raise HTTPException(404, "Oefening bestaat niet")
        weight = None if ex["unit"] == "geen" else (payload.weight or 0)
        row = {
            "id": new_id(),
            "exercise_id": payload.exercise_id,
            "date": payload.date,
            "reps": payload.reps,
            "weight": weight,
            "created_at": now(),
        }
        conn.execute(
            "INSERT INTO entries (id, exercise_id, date, reps, weight, created_at) "
            "VALUES (:id, :exercise_id, :date, :reps, :weight, :created_at)",
            row,
        )
    row.pop("created_at")
    return row


@app.delete("/api/entries/{entry_id}", status_code=204)
def delete_entry(entry_id: str):
    with db() as conn:
        conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))


# ---------- export en import ----------


@app.get("/api/export.csv", response_class=PlainTextResponse)
def export_csv():
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(
        [
            "datum",
            "oefening",
            "eenheid",
            "herhalingen",
            "gewicht",
            "volume",
            "sessie_van_dag",
            "doel_per_dag",
        ]
    )
    with db() as conn:
        rows = conn.execute(
            "SELECT e.date, x.name, x.unit, x.daily_target, e.reps, e.weight, "
            "ROW_NUMBER() OVER ("
            "  PARTITION BY e.exercise_id, e.date ORDER BY e.created_at"
            ") AS nth "
            "FROM entries e JOIN exercises x ON x.id = e.exercise_id "
            "ORDER BY e.date, x.name, e.created_at"
        )
        for r in rows:
            weight = "" if r["weight"] is None else r["weight"]
            volume = r["reps"] if weight == "" else round(r["reps"] * r["weight"], 2)
            writer.writerow(
                [
                    r["date"],
                    r["name"],
                    r["unit"],
                    r["reps"],
                    weight,
                    volume,
                    r["nth"],
                    r["daily_target"],
                ]
            )
    stamp = datetime.now().strftime("%Y-%m-%d")
    return PlainTextResponse(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="fysio-{stamp}.csv"'},
    )


@app.post("/api/import")
def import_csv(payload: ImportIn):
    """Leest een eerder geëxporteerde CSV en voegt ontbrekende regels toe."""
    reader = csv.DictReader(io.StringIO(payload.csv))
    added_ex = added_entries = 0
    seen: dict[tuple, int] = {}
    with db() as conn:
        known = {
            r["name"].lower(): r["id"]
            for r in conn.execute("SELECT id, name FROM exercises")
        }
        for line in reader:
            name = (line.get("oefening") or "").strip()
            date = (line.get("datum") or "").strip()
            if not name or not date:
                continue
            key = name.lower()
            if key not in known:
                unit = (line.get("eenheid") or "kg").strip()
                try:
                    target = max(1, min(12, int(line.get("doel_per_dag") or 2)))
                except ValueError:
                    target = 2
                ex_id = new_id()
                conn.execute(
                    "INSERT INTO exercises "
                    "(id, name, unit, daily_target, sort_order, created_at) "
                    "VALUES (?, ?, ?, ?, 999, ?)",
                    (ex_id, name, unit if unit in UNITS else "kg", target, now()),
                )
                known[key] = ex_id
                added_ex += 1
            reps = int(float(line.get("herhalingen") or 0))
            raw_weight = (line.get("gewicht") or "").strip()
            weight = float(raw_weight) if raw_weight else None
            # Meerdere sessies per dag zijn normaal, dus alleen ontdubbelen tot het
            # aantal identieke regels dat de CSV zelf bevat.
            fingerprint = (known[key], date, reps, weight)
            seen[fingerprint] = seen.get(fingerprint, 0) + 1
            already = conn.execute(
                "SELECT COUNT(*) AS n FROM entries WHERE exercise_id = ? AND date = ? "
                "AND reps = ? AND IFNULL(weight, -1) = IFNULL(?, -1)",
                fingerprint,
            ).fetchone()["n"]
            if already >= seen[fingerprint]:
                continue
            conn.execute(
                "INSERT INTO entries (id, exercise_id, date, reps, weight, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (new_id(), known[key], date, reps, weight, now()),
            )
            added_entries += 1
    return {"exercises": added_ex, "entries": added_entries}


@app.get("/api/health")
def health():
    return {"ok": True, "db": DB_PATH}


# De statische frontend als laatste, zodat /api/* voorrang houdt.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
