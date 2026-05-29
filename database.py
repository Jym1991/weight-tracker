import os
import pg8000.native

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def _parse_url(url: str):
    """Parse postgresql://user:pass@host:port/dbname into pg8000 params."""
    # Format: postgresql://user:password@host:port/dbname
    url = url.replace("postgresql://", "")
    auth_host, dbname = url.split("/", 1)
    user_pass, host_port = auth_host.split("@", 1)
    user, password = user_pass.split(":", 1)
    if ":" in host_port:
        host, port = host_port.split(":", 1)
    else:
        host, port = host_port, "5432"
    return {"user": user, "password": password, "host": host, "port": int(port), "database": dbname}


def get_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL 未设置")
    params = _parse_url(DATABASE_URL)
    conn = pg8000.native.Connection(**params)
    return conn


def db_exec(conn, sql, params=None):
    """Execute query with named params dict and return list of dicts."""
    if params is None:
        params = {}
    elif isinstance(params, list):
        params = {f"p{i}": v for i, v in enumerate(params)}
    rows = conn.run(sql, **params)
    cols = [c["name"] for c in conn.columns] if conn.columns else []
    return [dict(zip(cols, row)) for row in (rows or [])]


def db_exec_one(conn, sql, params=None):
    rows = db_exec(conn, sql, params)
    return rows[0] if rows else None


def init_db():
    conn = get_db()
    conn.run("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.run("""
        CREATE TABLE IF NOT EXISTS weight_records (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            date DATE NOT NULL,
            weight_kg DOUBLE PRECISION NOT NULL,
            note TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.run("""
        CREATE TABLE IF NOT EXISTS diet_records (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            date DATE NOT NULL,
            meal_type TEXT NOT NULL,
            food_name TEXT NOT NULL,
            calories_kcal DOUBLE PRECISION NOT NULL,
            note TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.run("""
        CREATE TABLE IF NOT EXISTS exercise_records (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            date DATE NOT NULL,
            exercise_name TEXT NOT NULL,
            duration_min DOUBLE PRECISION NOT NULL,
            calories_burned DOUBLE PRECISION NOT NULL,
            note TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.run("""
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
        )
    """)
    conn.run("""
        CREATE TABLE IF NOT EXISTS pk_groups (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL DEFAULT '减肥PK',
            creator_id INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.run("""
        CREATE TABLE IF NOT EXISTS pk_members (
            group_id INTEGER NOT NULL REFERENCES pk_groups(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            joined_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (group_id, user_id)
        )
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
            conn.run(idx_sql)
        except Exception:
            pass
    conn.close()
