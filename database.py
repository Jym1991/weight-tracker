import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL 未设置")
    conn = psycopg2.connect(DATABASE_URL)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    conn.autocommit = True
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS weight_records (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            date DATE NOT NULL,
            weight_kg DOUBLE PRECISION NOT NULL,
            note TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS diet_records (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            date DATE NOT NULL,
            meal_type TEXT NOT NULL,
            food_name TEXT NOT NULL,
            calories_kcal DOUBLE PRECISION NOT NULL,
            note TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS exercise_records (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            date DATE NOT NULL,
            exercise_name TEXT NOT NULL,
            duration_min DOUBLE PRECISION NOT NULL,
            calories_burned DOUBLE PRECISION NOT NULL,
            note TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS goals (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            target_weight_kg DOUBLE PRECISION NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            daily_calorie_target DOUBLE PRECISION,
            height_cm DOUBLE PRECISION DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS pk_groups (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL DEFAULT '减肥PK',
            creator_id INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS pk_members (
            group_id INTEGER NOT NULL REFERENCES pk_groups(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            joined_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (group_id, user_id)
        );
    """)
    # Indexes
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_weight_user ON weight_records(user_id, date)",
        "CREATE INDEX IF NOT EXISTS idx_diet_user ON diet_records(user_id, date)",
        "CREATE INDEX IF NOT EXISTS idx_exercise_user ON exercise_records(user_id, date)",
        "CREATE INDEX IF NOT EXISTS idx_goals_user ON goals(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_pk_members_group ON pk_members(group_id)",
        "CREATE INDEX IF NOT EXISTS idx_pk_members_user ON pk_members(user_id)",
    ]:
        try:
            cur.execute(idx_sql)
        except Exception:
            pass
    conn.close()
