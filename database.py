import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "weight_tracker.db")
_conn = None


def get_db():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=DELETE")
        _conn.execute("PRAGMA foreign_keys=ON")
    return _conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS weight_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            date TEXT NOT NULL,
            weight_kg REAL NOT NULL,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS diet_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            date TEXT NOT NULL,
            meal_type TEXT NOT NULL CHECK(meal_type IN ('早餐','午餐','晚餐','加餐')),
            food_name TEXT NOT NULL,
            calories_kcal REAL NOT NULL,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS exercise_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            date TEXT NOT NULL,
            exercise_name TEXT NOT NULL,
            duration_min REAL NOT NULL,
            calories_burned REAL NOT NULL,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            target_weight_kg REAL NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            daily_calorie_target REAL,
            height_cm REAL DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS pk_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT '减肥PK',
            creator_id INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS pk_members (
            group_id INTEGER NOT NULL REFERENCES pk_groups(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            joined_at TEXT DEFAULT (datetime('now', 'localtime')),
            PRIMARY KEY (group_id, user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_weight_user ON weight_records(user_id, date);
        CREATE INDEX IF NOT EXISTS idx_diet_user ON diet_records(user_id, date);
        CREATE INDEX IF NOT EXISTS idx_exercise_user ON exercise_records(user_id, date);
        CREATE INDEX IF NOT EXISTS idx_goals_user ON goals(user_id);
        CREATE INDEX IF NOT EXISTS idx_pk_members_group ON pk_members(group_id);
        CREATE INDEX IF NOT EXISTS idx_pk_members_user ON pk_members(user_id);
    """)
    conn.commit()
