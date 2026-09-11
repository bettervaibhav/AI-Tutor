"""
history_service.py — Persistent SQLite Learning History
==========================================================
Stores learning sessions, generated lesson JSON, and doubt history.
Survives backend restarts and allows Continue Learning.

Tables:
  learning_sessions  — metadata (topic, step, completion, timestamps)
  lesson_content     — full generated lesson JSON + concept map
  doubts             — each doubt + AI answer + concept tag
"""

import os
import json
import uuid
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / "tutor_history.db"


def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_sessions (
                id                   TEXT PRIMARY KEY,
                user_id              TEXT DEFAULT 'anonymous',
                topic                TEXT NOT NULL,
                subject              TEXT DEFAULT 'General',
                language             TEXT DEFAULT 'hinglish',
                difficulty           TEXT DEFAULT 'Class 11-12',
                teaching_style       TEXT DEFAULT 'Feynman',
                voice                TEXT DEFAULT 'prof_aether',
                started_at           TEXT NOT NULL,
                last_accessed_at     TEXT,
                current_step         INTEGER DEFAULT 0,
                total_steps          INTEGER DEFAULT 0,
                completion_percentage REAL DEFAULT 0.0,
                completed            INTEGER DEFAULT 0,
                board_page           INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lesson_content (
                id               TEXT PRIMARY KEY,
                session_id       TEXT NOT NULL,
                topic            TEXT,
                concept_map      TEXT,
                generated_content TEXT NOT NULL,
                created_at       TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS doubts (
                id           TEXT PRIMARY KEY,
                session_id   TEXT NOT NULL,
                question     TEXT NOT NULL,
                answer       TEXT,
                concept      TEXT,
                strategy_used TEXT,
                step_index   INTEGER DEFAULT 0,
                created_at   TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE
            )
        """)
        conn.commit()


# Initialize on import
try:
    init_db()
except Exception as _e:
    print(f"[Warning] DB init failed: {_e}")


# ─────────────────────────────────────────────
# SESSION CRUD
# ─────────────────────────────────────────────

def create_session(data: dict) -> dict:
    session_id = data.get("id") or str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute("""
            INSERT INTO learning_sessions
              (id, user_id, topic, subject, language, difficulty, teaching_style, voice,
               started_at, last_accessed_at, current_step, total_steps,
               completion_percentage, completed, board_page)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            session_id,
            data.get("user_id", "anonymous"),
            data.get("topic", ""),
            data.get("subject", "General"),
            data.get("language", "hinglish"),
            data.get("difficulty", "Class 11-12"),
            data.get("teaching_style", "Feynman"),
            data.get("voice", "prof_aether"),
            data.get("started_at", now),
            now,
            data.get("current_step", 0),
            data.get("total_steps", 0),
            data.get("completion_percentage", 0.0),
            int(data.get("completed", False)),
            data.get("board_page", 0),
        ))
        conn.commit()

    return {"id": session_id, "started_at": now}


def update_session(session_id: str, updates: dict) -> bool:
    ALLOWED = {
        "current_step", "total_steps", "completion_percentage",
        "completed", "board_page",
    }
    fields = {k: v for k, v in updates.items() if k in ALLOWED}
    if not fields:
        return False

    fields["last_accessed_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [session_id]

    with get_db() as conn:
        conn.execute(
            f"UPDATE learning_sessions SET {set_clause} WHERE id = ?", values
        )
        conn.commit()
    return True


def save_lesson_content(session_id: str, topic: str, lesson: dict,
                        concept_map: dict = None) -> str:
    lesson_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute("""
            INSERT INTO lesson_content (id, session_id, topic, concept_map, generated_content, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            lesson_id,
            session_id,
            topic,
            json.dumps(concept_map) if concept_map else None,
            json.dumps(lesson),
            now,
        ))
        conn.commit()

    return lesson_id


def update_lesson_content(session_id: str, lesson: dict) -> bool:
    """Update the generated_content for an existing session (used when steps are appended)."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute("""
            UPDATE lesson_content SET generated_content = ?, created_at = ?
            WHERE session_id = ?
        """, (json.dumps(lesson), now, session_id))
        conn.commit()
    return True


def save_doubt(session_id: str, doubt_data: dict) -> str:
    doubt_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute("""
            INSERT INTO doubts (id, session_id, question, answer, concept, strategy_used, step_index, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doubt_id,
            session_id,
            doubt_data.get("question", ""),
            doubt_data.get("answer", ""),
            doubt_data.get("concept", ""),
            doubt_data.get("strategy_used", ""),
            doubt_data.get("step_index", 0),
            now,
        ))
        conn.commit()

    return doubt_id


# ─────────────────────────────────────────────
# SESSION READ
# ─────────────────────────────────────────────

def get_session(session_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM learning_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not row:
            return None

        session = dict(row)

        # Load lesson content
        lesson_row = conn.execute(
            "SELECT * FROM lesson_content WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
            (session_id,)
        ).fetchone()
        if lesson_row:
            ldata = dict(lesson_row)
            session["lesson"] = json.loads(ldata["generated_content"])
            session["concept_map"] = (
                json.loads(ldata["concept_map"]) if ldata.get("concept_map") else None
            )
            session["lesson_id"] = ldata["id"]
        else:
            session["lesson"] = None
            session["concept_map"] = None

        # Load doubts
        doubts = conn.execute(
            "SELECT * FROM doubts WHERE session_id = ? ORDER BY created_at",
            (session_id,)
        ).fetchall()
        session["doubts"] = [dict(d) for d in doubts]

        return session


def get_concept_map(session_id: str) -> dict | None:
    """Lightweight: fetch only the concept map for a session (used by continue-endpoint)."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT concept_map, generated_content FROM lesson_content WHERE session_id = ? LIMIT 1",
            (session_id,)
        ).fetchone()
        if not row:
            return None
        r = dict(row)
        return {
            "concept_map": json.loads(r["concept_map"]) if r.get("concept_map") else None,
            "partial_lesson": json.loads(r["generated_content"]) if r.get("generated_content") else None,
        }


def list_sessions(user_id: str = None, limit: int = 30) -> list:
    """Lightweight list — does NOT include full lesson JSON."""
    with get_db() as conn:
        if user_id and user_id != "anonymous":
            rows = conn.execute("""
                SELECT id, user_id, topic, subject, language, difficulty, teaching_style, voice,
                       started_at, last_accessed_at, current_step, total_steps,
                       completion_percentage, completed, board_page
                FROM learning_sessions
                WHERE user_id = ?
                ORDER BY last_accessed_at DESC LIMIT ?
            """, (user_id, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT id, user_id, topic, subject, language, difficulty, teaching_style, voice,
                       started_at, last_accessed_at, current_step, total_steps,
                       completion_percentage, completed, board_page
                FROM learning_sessions
                ORDER BY last_accessed_at DESC LIMIT ?
            """, (limit,)).fetchall()

        return [dict(r) for r in rows]


def delete_session(session_id: str) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM doubts WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM lesson_content WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM learning_sessions WHERE id = ?", (session_id,))
        conn.commit()
    return True
