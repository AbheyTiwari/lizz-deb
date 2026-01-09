import sqlite3
import hashlib
import secrets
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path("data.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == password_hash

def generate_token() -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(32)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Topics table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS topics (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        system_prompt TEXT NOT NULL
    )
    """)

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    # Chat messages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        user_name TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (topic_id) REFERENCES topics (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    # Create index on email for faster lookups
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
    """)

    # Create index on sessions for cleanup
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)
    """)

    # Create index on chat messages
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_chat_topic_time ON chat_messages(topic_id, created_at DESC)
    """)

    conn.commit()
    conn.close()

# Topic functions
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

# User functions
def create_user(name: str, email: str, password: str) -> dict | None:
    """Create a new user"""
    conn = get_connection()
    cursor = conn.cursor()

    user_id = secrets.token_urlsafe(16)
    password_hash = hash_password(password)

    try:
        cursor.execute(
            "INSERT INTO users (id, name, email, password_hash) VALUES (?, ?, ?, ?)",
            (user_id, name, email, password_hash)
        )
        conn.commit()
        
        return {
            "id": user_id,
            "name": name,
            "email": email,
            "password_hash": password_hash
        }
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_email(email: str) -> dict | None:
    """Get user by email"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name, email, password_hash, created_at FROM users WHERE email = ?",
        (email,)
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "password_hash": row[3],
            "created_at": row[4]
        }
    return None

def get_user_by_id(user_id: str) -> dict | None:
    """Get user by ID"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?",
        (user_id,)
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "created_at": row[3]
        }
    return None

# Session functions
def create_session(user_id: str, expires_in_days: int = 30) -> str:
    """Create a new session for user"""
    conn = get_connection()
    cursor = conn.cursor()

    token = generate_token()
    expires_at = datetime.now() + timedelta(days=expires_in_days)

    cursor.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires_at.isoformat())
    )
    conn.commit()
    conn.close()

    return token

def get_session(token: str) -> dict | None:
    """Get session and user info by token"""
    conn = get_connection()
    cursor = conn.cursor()

    # Clean up expired sessions first
    cursor.execute(
        "DELETE FROM sessions WHERE expires_at < ?",
        (datetime.now().isoformat(),)
    )

    # Get session with user info
    cursor.execute("""
        SELECT s.token, s.user_id, s.expires_at, u.name, u.email
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ? AND s.expires_at > ?
    """, (token, datetime.now().isoformat()))

    row = cursor.fetchone()
    conn.commit()
    conn.close()

    if row:
        return {
            "session_token": row[0],
            "user_id": row[1],
            "expires_at": row[2],
            "name": row[3],
            "email": row[4]
        }
    return None

def delete_session(token: str) -> bool:
    """Delete a session (logout)"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
    deleted = cursor.rowcount > 0
    
    conn.commit()
    conn.close()

    return deleted

def cleanup_expired_sessions():
    """Clean up all expired sessions"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM sessions WHERE expires_at < ?",
        (datetime.now().isoformat(),)
    )
    deleted = cursor.rowcount
    
    conn.commit()
    conn.close()

    return deleted

# Chat message functions
def save_chat_message(topic_id: str, user_id: str, user_name: str, message: str) -> bool:
    """Save a chat message"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO chat_messages (topic_id, user_id, user_name, message) VALUES (?, ?, ?, ?)",
            (topic_id, user_id, user_name, message)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Failed to save message: {e}")
        return False
    finally:
        conn.close()

def get_chat_messages(topic_id: str, limit: int = 50) -> list[dict]:
    """Get recent chat messages for a topic"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, user_name, message, created_at
        FROM chat_messages
        WHERE topic_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (topic_id, limit))

    rows = cursor.fetchall()
    conn.close()

    # Reverse to get chronological order
    messages = []
    for row in reversed(rows):
        messages.append({
            "user_id": row[0],
            "user_name": row[1],
            "message": row[2],
            "timestamp": row[3]
        })
    
    return messages