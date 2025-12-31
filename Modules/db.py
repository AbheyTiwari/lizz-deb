import sqlite3
from pathlib import Path

DB_PATH = Path("data.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS topics (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        system_prompt TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

def get_topic_prompt(topic_id: str) -> str | None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT system_prompt FROM topics WHERE id = ?",
        (topic_id,)
    )

    row = cursor.fetchone()
    conn.close()

    return row[0] if row else None

def add_topic(topic_id: str, title: str, system_prompt: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO topics (id, title, system_prompt) VALUES (?, ?, ?)",
            (topic_id, title, system_prompt)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_topic(topic_id: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, title, system_prompt FROM topics WHERE id = ?",
        (topic_id,)
    )

    row = cursor.fetchone()
    conn.close()

    return {"id": row[0], "title": row[1], "system_prompt": row[2]} if row else None

def get_all_topics() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, system_prompt FROM topics")
    rows = cursor.fetchall()
    conn.close()

    return [{"id": row[0], "title": row[1], "system_prompt": row[2]} for row in rows]