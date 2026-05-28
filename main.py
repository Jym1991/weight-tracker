from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from database import get_db, init_db
from models import (
    UserRegister, UserLogin, TokenResponse,
    WeightRecord, WeightRecordOut,
    DietRecord, DietRecordOut,
    ExerciseRecord, ExerciseRecordOut,
    Goal, GoalOut,
    PKCreate, PKGroupOut, PKMemberInfo,
)
from auth import create_token, hash_password, check_password, get_current_user

app = FastAPI(title="减肥体重管理系统")

# ==================== Auth ====================

@app.post("/api/auth/register", response_model=TokenResponse)
def register(body: UserRegister):
    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE username = ?", (body.username,)).fetchone()
    if existing:
        raise HTTPException(400, "用户名已存在")
    pw_hash = hash_password(body.password)
    cur = db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (body.username, pw_hash))
    db.commit()
    user_id = cur.lastrowid
    token = create_token(user_id, body.username)
    return {"token": token, "username": body.username}


@app.post("/api/auth/login", response_model=TokenResponse)
def login(body: UserLogin):
    db = get_db()
    row = db.execute("SELECT id, password_hash FROM users WHERE username = ?", (body.username,)).fetchone()
    if not row or not check_password(body.password, row["password_hash"]):
        raise HTTPException(401, "用户名或密码错误")
    token = create_token(row["id"], body.username)
    return {"token": token, "username": body.username}


# ==================== Weight ====================

@app.get("/api/weight")
def list_weight(request: Request, date_from: str = None, date_to: str = None):
    user = get_current_user(request)
    db = get_db()
    if date_from and date_to:
        rows = db.execute(
            "SELECT * FROM weight_records WHERE user_id=? AND date BETWEEN ? AND ? ORDER BY date DESC",
            (user["user_id"], date_from, date_to),
        ).fetchall()
    elif date_from:
        rows = db.execute(
            "SELECT * FROM weight_records WHERE user_id=? AND date >= ? ORDER BY date DESC",
            (user["user_id"], date_from),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM weight_records WHERE user_id=? ORDER BY date DESC LIMIT 90",
            (user["user_id"],),
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/weight", response_model=WeightRecordOut)
def add_weight(request: Request, record: WeightRecord):
    user = get_current_user(request)
    db = get_db()
    cur = db.execute(
        "INSERT INTO weight_records (user_id, date, weight_kg, note) VALUES (?, ?, ?, ?)",
        (user["user_id"], record.date, record.weight_kg, record.note),
    )
    db.commit()
    row = db.execute("SELECT * FROM weight_records WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.delete("/api/weight/{record_id}")
def delete_weight(request: Request, record_id: int):
    user = get_current_user(request)
    db = get_db()
    row = db.execute("SELECT id FROM weight_records WHERE id=? AND user_id=?", (record_id, user["user_id"])).fetchone()
    if not row:
        raise HTTPException(404, "记录不存在")
    db.execute("DELETE FROM weight_records WHERE id = ?", (record_id,))
    db.commit()
    return {"ok": True}


# ==================== Diet ====================

@app.get("/api/diet")
def list_diet(request: Request, date: str = None):
    user = get_current_user(request)
    db = get_db()
    if date:
        rows = db.execute(
            "SELECT * FROM diet_records WHERE user_id=? AND date = ? ORDER BY created_at DESC",
            (user["user_id"], date),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM diet_records WHERE user_id=? ORDER BY date DESC, created_at DESC LIMIT 100",
            (user["user_id"],),
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/diet", response_model=DietRecordOut)
def add_diet(request: Request, record: DietRecord):
    user = get_current_user(request)
    db = get_db()
    cur = db.execute(
        "INSERT INTO diet_records (user_id, date, meal_type, food_name, calories_kcal, note) VALUES (?, ?, ?, ?, ?, ?)",
        (user["user_id"], record.date, record.meal_type, record.food_name, record.calories_kcal, record.note),
    )
    db.commit()
    row = db.execute("SELECT * FROM diet_records WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.delete("/api/diet/{record_id}")
def delete_diet(request: Request, record_id: int):
    user = get_current_user(request)
    db = get_db()
    row = db.execute("SELECT id FROM diet_records WHERE id=? AND user_id=?", (record_id, user["user_id"])).fetchone()
    if not row:
        raise HTTPException(404, "记录不存在")
    db.execute("DELETE FROM diet_records WHERE id = ?", (record_id,))
    db.commit()
    return {"ok": True}


@app.get("/api/diet/summary")
def diet_summary(request: Request, date: str):
    user = get_current_user(request)
    db = get_db()
    row = db.execute(
        "SELECT COALESCE(SUM(calories_kcal), 0) AS total FROM diet_records WHERE user_id=? AND date = ?",
        (user["user_id"], date),
    ).fetchone()
    return {"date": date, "total_calories": row["total"]}


# ==================== Exercise ====================

@app.get("/api/exercise")
def list_exercise(request: Request, date: str = None):
    user = get_current_user(request)
    db = get_db()
    if date:
        rows = db.execute(
            "SELECT * FROM exercise_records WHERE user_id=? AND date = ? ORDER BY created_at DESC",
            (user["user_id"], date),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM exercise_records WHERE user_id=? ORDER BY date DESC, created_at DESC LIMIT 100",
            (user["user_id"],),
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/exercise", response_model=ExerciseRecordOut)
def add_exercise(request: Request, record: ExerciseRecord):
    user = get_current_user(request)
    db = get_db()
    cur = db.execute(
        "INSERT INTO exercise_records (user_id, date, exercise_name, duration_min, calories_burned, note) VALUES (?, ?, ?, ?, ?, ?)",
        (user["user_id"], record.date, record.exercise_name, record.duration_min, record.calories_burned, record.note),
    )
    db.commit()
    row = db.execute("SELECT * FROM exercise_records WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.delete("/api/exercise/{record_id}")
def delete_exercise(request: Request, record_id: int):
    user = get_current_user(request)
    db = get_db()
    row = db.execute("SELECT id FROM exercise_records WHERE id=? AND user_id=?", (record_id, user["user_id"])).fetchone()
    if not row:
        raise HTTPException(404, "记录不存在")
    db.execute("DELETE FROM exercise_records WHERE id = ?", (record_id,))
    db.commit()
    return {"ok": True}


@app.get("/api/exercise/summary")
def exercise_summary(request: Request, date: str):
    user = get_current_user(request)
    db = get_db()
    row = db.execute(
        "SELECT COALESCE(SUM(calories_burned), 0) AS total FROM exercise_records WHERE user_id=? AND date = ?",
        (user["user_id"], date),
    ).fetchone()
    return {"date": date, "total_calories_burned": row["total"]}


# ==================== Goals ====================

@app.get("/api/goals")
def list_goals(request: Request):
    user = get_current_user(request)
    db = get_db()
    rows = db.execute("SELECT * FROM goals WHERE user_id=? ORDER BY created_at DESC", (user["user_id"],)).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/goals", response_model=GoalOut)
def create_goal(request: Request, goal: Goal):
    user = get_current_user(request)
    db = get_db()
    db.execute("UPDATE goals SET is_active = 0 WHERE user_id=?", (user["user_id"],))
    cur = db.execute(
        "INSERT INTO goals (user_id, target_weight_kg, start_date, end_date, daily_calorie_target, height_cm) VALUES (?, ?, ?, ?, ?, ?)",
        (user["user_id"], goal.target_weight_kg, goal.start_date, goal.end_date, goal.daily_calorie_target, goal.height_cm),
    )
    db.commit()
    row = db.execute("SELECT * FROM goals WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.put("/api/goals/{goal_id}", response_model=GoalOut)
def update_goal(request: Request, goal_id: int, goal: Goal):
    user = get_current_user(request)
    db = get_db()
    row = db.execute("SELECT id FROM goals WHERE id=? AND user_id=?", (goal_id, user["user_id"])).fetchone()
    if not row:
        raise HTTPException(404, "目标不存在")
    db.execute(
        "UPDATE goals SET target_weight_kg=?, start_date=?, end_date=?, daily_calorie_target=?, height_cm=? WHERE id=?",
        (goal.target_weight_kg, goal.start_date, goal.end_date, goal.daily_calorie_target, goal.height_cm, goal_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    return dict(row)


@app.get("/api/goals/progress")
def goal_progress(request: Request):
    user = get_current_user(request)
    db = get_db()
    goal = db.execute(
        "SELECT * FROM goals WHERE user_id=? AND is_active = 1 ORDER BY created_at DESC LIMIT 1",
        (user["user_id"],),
    ).fetchone()
    if not goal:
        return {"has_goal": False}

    latest = db.execute(
        "SELECT weight_kg FROM weight_records WHERE user_id=? ORDER BY date DESC LIMIT 1",
        (user["user_id"],),
    ).fetchone()

    current_weight = latest["weight_kg"] if latest else None
    target_weight = goal["target_weight_kg"]
    remaining = round(current_weight - target_weight, 1) if current_weight else None

    height_cm = goal["height_cm"] or 0
    height_m = height_cm / 100
    bmi = round(current_weight / (height_m ** 2), 1) if current_weight and height_cm > 0 else None

    return {
        "has_goal": True,
        "target_weight_kg": target_weight,
        "current_weight_kg": current_weight,
        "remaining_kg": remaining,
        "start_date": goal["start_date"],
        "end_date": goal["end_date"],
        "daily_calorie_target": goal["daily_calorie_target"],
        "height_cm": height_cm,
        "bmi": bmi,
    }


# ==================== Stats ====================

@app.get("/api/stats/bmi")
def calc_bmi(request: Request, weight_kg: float, height_cm: float):
    get_current_user(request)
    if height_cm <= 0:
        raise HTTPException(400, "身高必须大于0")
    h = height_cm / 100
    bmi = round(weight_kg / (h * h), 1)
    if bmi < 18.5:
        label = "偏瘦"
    elif bmi < 24:
        label = "正常"
    elif bmi < 28:
        label = "偏胖"
    else:
        label = "肥胖"
    return {"bmi": bmi, "label": label}


@app.get("/api/stats/overview")
def overview(request: Request, date: str = None):
    import datetime as _dt
    user = get_current_user(request)
    today = date or _dt.date.today().isoformat()
    db = get_db()

    goal = db.execute(
        "SELECT * FROM goals WHERE user_id=? AND is_active = 1 ORDER BY created_at DESC LIMIT 1",
        (user["user_id"],),
    ).fetchone()
    latest_weight = db.execute(
        "SELECT weight_kg FROM weight_records WHERE user_id=? ORDER BY date DESC LIMIT 1",
        (user["user_id"],),
    ).fetchone()

    diet = db.execute(
        "SELECT COALESCE(SUM(calories_kcal), 0) AS total FROM diet_records WHERE user_id=? AND date = ?",
        (user["user_id"], today),
    ).fetchone()
    exercise = db.execute(
        "SELECT COALESCE(SUM(calories_burned), 0) AS total FROM exercise_records WHERE user_id=? AND date = ?",
        (user["user_id"], today),
    ).fetchone()

    result = {
        "date": today,
        "current_weight_kg": latest_weight["weight_kg"] if latest_weight else None,
        "today_calories_in": diet["total"],
        "today_calories_out": exercise["total"],
        "net_calories": diet["total"] - exercise["total"],
    }

    if goal:
        result["target_weight_kg"] = goal["target_weight_kg"]
        result["daily_calorie_target"] = goal["daily_calorie_target"]
        result["height_cm"] = goal["height_cm"]
        if latest_weight:
            result["remaining_kg"] = round(latest_weight["weight_kg"] - goal["target_weight_kg"], 1)

    return result


# ==================== PK (朋友PK) ====================

@app.get("/api/users/search")
def search_users(request: Request, q: str = ""):
    get_current_user(request)
    if len(q) < 1:
        return []
    db = get_db()
    rows = db.execute(
        "SELECT id, username FROM users WHERE username LIKE ? LIMIT 10",
        (f"%{q}%",),
    ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/pk/create")
def pk_create(request: Request, body: PKCreate):
    user = get_current_user(request)
    db = get_db()

    # Resolve usernames to user_ids
    member_ids = [user["user_id"]]
    for uname in body.member_usernames:
        row = db.execute("SELECT id FROM users WHERE username = ?", (uname,)).fetchone()
        if not row:
            raise HTTPException(400, f"用户 '{uname}' 不存在")
        if row["id"] == user["user_id"]:
            raise HTTPException(400, "不能和自己PK")
        if row["id"] in member_ids:
            raise HTTPException(400, "不能重复添加同一用户")
        member_ids.append(row["id"])

    cur = db.execute("INSERT INTO pk_groups (name, creator_id) VALUES (?, ?)", (body.name, user["user_id"]))
    gid = cur.lastrowid
    for mid in member_ids:
        db.execute("INSERT INTO pk_members (group_id, user_id) VALUES (?, ?)", (gid, mid))
    db.commit()
    return {"ok": True, "group_id": gid}


def _get_member_progress(db, user_id: int) -> PKMemberInfo:
    """Compute PK progress for a single user."""
    urow = db.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    goal = db.execute(
        "SELECT * FROM goals WHERE user_id=? AND is_active=1 ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    latest = db.execute(
        "SELECT weight_kg FROM weight_records WHERE user_id=? ORDER BY date DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    earliest = db.execute(
        "SELECT weight_kg FROM weight_records WHERE user_id=? ORDER BY date ASC LIMIT 1",
        (user_id,),
    ).fetchone()

    info = PKMemberInfo(
        user_id=user_id,
        username=urow["username"] if urow else "?",
        target_weight_kg=goal["target_weight_kg"] if goal else None,
        current_weight_kg=latest["weight_kg"] if latest else None,
        start_weight_kg=earliest["weight_kg"] if earliest else None,
    )

    if latest and earliest and goal:
        total_to_lose = earliest["weight_kg"] - goal["target_weight_kg"]
        lost_so_far = earliest["weight_kg"] - latest["weight_kg"]
        info.total_lost_kg = round(lost_so_far, 1)
        if total_to_lose > 0:
            pct = min(100, max(0, round(lost_so_far / total_to_lose * 100, 1)))
            info.progress_pct = pct
        elif lost_so_far >= total_to_lose:
            info.progress_pct = 100
    elif latest and earliest:
        info.total_lost_kg = round(earliest["weight_kg"] - latest["weight_kg"], 1)

    return info


@app.get("/api/pk/groups")
def pk_list_groups(request: Request):
    user = get_current_user(request)
    db = get_db()
    rows = db.execute(
        "SELECT g.id, g.name, g.creator_id, g.created_at FROM pk_groups g "
        "JOIN pk_members m ON g.id = m.group_id WHERE m.user_id = ? ORDER BY g.created_at DESC",
        (user["user_id"],),
    ).fetchall()

    result = []
    for g in rows:
        members = db.execute(
            "SELECT user_id FROM pk_members WHERE group_id = ?", (g["id"],)
        ).fetchall()
        member_infos = [_get_member_progress(db, m["user_id"]) for m in members]
        result.append({
            "id": g["id"],
            "name": g["name"],
            "creator_id": g["creator_id"],
            "created_at": g["created_at"],
            "members": [m.model_dump() for m in member_infos],
        })
    return result


@app.delete("/api/pk/{group_id}")
def pk_leave(request: Request, group_id: int):
    user = get_current_user(request)
    db = get_db()
    db.execute("DELETE FROM pk_members WHERE group_id=? AND user_id=?", (group_id, user["user_id"]))
    # Remove group if empty
    remaining = db.execute("SELECT COUNT(*) as c FROM pk_members WHERE group_id=?", (group_id,)).fetchone()
    if remaining["c"] == 0:
        db.execute("DELETE FROM pk_groups WHERE id=?", (group_id,))
    db.commit()
    return {"ok": True}


@app.get("/api/pk/{group_id}")
def pk_detail(request: Request, group_id: int):
    user = get_current_user(request)
    db = get_db()
    # Verify membership
    mem = db.execute(
        "SELECT 1 FROM pk_members WHERE group_id=? AND user_id=?", (group_id, user["user_id"])
    ).fetchone()
    if not mem:
        raise HTTPException(403, "你不在此PK组中")

    g = db.execute("SELECT * FROM pk_groups WHERE id=?", (group_id,)).fetchone()
    members = db.execute("SELECT user_id FROM pk_members WHERE group_id=?", (group_id,)).fetchall()
    member_infos = [_get_member_progress(db, m["user_id"]) for m in members]
    return {
        "id": g["id"],
        "name": g["name"],
        "creator_id": g["creator_id"],
        "created_at": g["created_at"],
        "members": [m.model_dump() for m in member_infos],
    }


# ==================== Startup ====================

@app.on_event("startup")
def startup():
    init_db()


import os
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
