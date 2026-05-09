import sqlite3
from datetime import datetime
from config import DB_PATH


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL UNIQUE,
            title TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS announcement (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            text TEXT,
            media_type TEXT,
            media_file_id TEXT,
            button_text TEXT,
            button_url TEXT,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            photo_file_id TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            username TEXT,
            first_name TEXT,
            model_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (model_id) REFERENCES models(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    conn.commit()
    conn.close()


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

def set_setting(key: str, value: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, str(value)))

    conn.commit()
    conn.close()


def get_setting(key: str, default=None):
    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()

    conn.close()

    if not row:
        return default

    return row["value"]


def save_post_interval_minutes(minutes: int):
    set_setting("post_interval_minutes", str(int(minutes)))


def get_post_interval_minutes() -> int:
    value = get_setting("post_interval_minutes", "0")

    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


# ==========================================================
# GRUPOS
# ==========================================================

def save_group(chat_id: int, title: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO groups (chat_id, title, active, created_at, updated_at)
        VALUES (?, ?, 1, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET
            title = excluded.title,
            active = 1,
            updated_at = excluded.updated_at
    """, (chat_id, title, now(), now()))

    conn.commit()
    conn.close()


def mark_group_inactive(chat_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE groups
        SET active = 0, updated_at = ?
        WHERE chat_id = ?
    """, (now(), chat_id))

    conn.commit()
    conn.close()


def get_active_groups():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT chat_id, title
        FROM groups
        WHERE active = 1
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    conn.close()
    return rows


# ==========================================================
# ANÚNCIO
# ==========================================================

def save_announcement(text: str, media_type: str, media_file_id: str, button_text: str, button_url: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO announcement (
            id, text, media_type, media_file_id, button_text, button_url, updated_at
        ) VALUES (1, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            text = excluded.text,
            media_type = excluded.media_type,
            media_file_id = excluded.media_file_id,
            button_text = excluded.button_text,
            button_url = excluded.button_url,
            updated_at = excluded.updated_at
    """, (text, media_type, media_file_id, button_text, button_url, now()))

    conn.commit()
    conn.close()


def get_announcement():
    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM announcement WHERE id = 1")
    row = cur.fetchone()

    conn.close()
    return row


def clear_announcement():
    conn = connect()
    cur = conn.cursor()

    cur.execute("DELETE FROM announcement WHERE id = 1")

    conn.commit()
    conn.close()


# ==========================================================
# MODELOS PARTICIPANTES
# ==========================================================

def add_model(name: str, photo_file_id: str):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO models (name, photo_file_id, active, created_at)
        VALUES (?, ?, 1, ?)
    """, (name, photo_file_id, now()))

    conn.commit()
    conn.close()


def get_active_models():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, photo_file_id, created_at
        FROM models
        WHERE active = 1
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    conn.close()
    return rows


def get_model(model_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, photo_file_id, active
        FROM models
        WHERE id = ?
    """, (model_id,))

    row = cur.fetchone()
    conn.close()
    return row


def delete_model(model_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute("UPDATE models SET active = 0 WHERE id = ?", (model_id,))
    cur.execute("DELETE FROM votes WHERE model_id = ?", (model_id,))

    conn.commit()
    conn.close()


# ==========================================================
# VOTOS
# ==========================================================

def get_user_vote(user_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT v.id, v.model_id, m.name AS model_name
        FROM votes v
        LEFT JOIN models m ON m.id = v.model_id
        WHERE v.user_id = ?
    """, (user_id,))

    row = cur.fetchone()
    conn.close()
    return row


def save_vote(user_id: int, username: str, first_name: str, model_id: int):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO votes (user_id, username, first_name, model_id, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, username, first_name, model_id, now()))

    conn.commit()
    conn.close()


def get_ranking():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            m.id,
            m.name,
            COUNT(v.id) AS total_votes
        FROM models m
        LEFT JOIN votes v ON v.model_id = m.id
        WHERE m.active = 1
        GROUP BY m.id, m.name
        ORDER BY total_votes DESC, m.id ASC
    """)

    rows = cur.fetchall()
    conn.close()
    return rows


def get_total_votes():
    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS total FROM votes")
    row = cur.fetchone()

    conn.close()
    return int(row["total"] or 0)


def reset_votes():
    conn = connect()
    cur = conn.cursor()

    cur.execute("DELETE FROM votes")

    conn.commit()
    conn.close()
