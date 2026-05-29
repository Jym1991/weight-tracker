from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from database import get_db, db_exec, db_exec_one, init_db
from models import (
    UserRegister, UserLogin, TokenResponse,
    WeightRecord, WeightRecordOut,
    DietRecord, DietRecordOut,
    ExerciseRecord, ExerciseRecordOut,
    Goal, GoalOut,
    PKCreate, PKGroupOut, PKMemberInfo,
)
from auth import create_token, hash_password, check_password, get_current_user
import datetime as _dt

app = FastAPI(title="减肥体重管理系统")


def _fmt(row):
    if row is None:
        return None
    return {k: (v.isoformat() if isinstance(v, (_dt.date, _dt.datetime)) else v) for k, v in row.items()}


def _f(v):
    """Ensure value is a plain Python float (pg8000 may return Decimal)."""
    if v is None:
        return None
    return float(v)


# ==================== Auth ====================

@app.post("/api/auth/register", response_model=TokenResponse)
def register(body: UserRegister):
    conn = get_db()
    if db_exec_one(conn, "SELECT id FROM users WHERE username = :u", {"u": body.username}):
        raise HTTPException(400, "用户名已存在")
    pw_hash = hash_password(body.password)
    row = db_exec_one(conn,
        "INSERT INTO users (username, password_hash) VALUES (:u, :p) RETURNING id",
        {"u": body.username, "p": pw_hash})
    token = create_token(row["id"], body.username)
    return {"token": token, "username": body.username}


@app.post("/api/auth/login", response_model=TokenResponse)
def login(body: UserLogin):
    conn = get_db()
    row = db_exec_one(conn,
        "SELECT id, password_hash FROM users WHERE username = :u", {"u": body.username})
    if not row or not check_password(body.password, row["password_hash"]):
        raise HTTPException(401, "用户名或密码错误")
    token = create_token(row["id"], body.username)
    return {"token": token, "username": body.username}


# ==================== Weight ====================

@app.get("/api/weight")
def list_weight(request: Request, date_from: str = None, date_to: str = None):
    user = get_current_user(request)
    conn = get_db()
    p = {"u": user["user_id"]}
    if date_from and date_to:
        p.update(df=date_from, dt=date_to)
        rows = db_exec(conn,
            "SELECT * FROM weight_records WHERE user_id=:u AND date BETWEEN :df AND :dt ORDER BY date DESC", p)
    elif date_from:
        p.update(df=date_from)
        rows = db_exec(conn,
            "SELECT * FROM weight_records WHERE user_id=:u AND date >= :df ORDER BY date DESC", p)
    else:
        rows = db_exec(conn,
            "SELECT * FROM weight_records WHERE user_id=:u ORDER BY date DESC LIMIT 90", p)
    return [_fmt(r) for r in rows]


@app.post("/api/weight", response_model=WeightRecordOut)
def add_weight(request: Request, record: WeightRecord):
    user = get_current_user(request)
    conn = get_db()
    row = db_exec_one(conn,
        "INSERT INTO weight_records (user_id, date, weight_kg, note) VALUES (:u, :d, :w, :n) RETURNING *",
        {"u": user["user_id"], "d": record.date, "w": record.weight_kg, "n": record.note})
    return _fmt(row)


@app.delete("/api/weight/{record_id}")
def delete_weight(request: Request, record_id: int):
    user = get_current_user(request)
    conn = get_db()
    if not db_exec_one(conn,
            "SELECT id FROM weight_records WHERE id=:id AND user_id=:u",
            {"id": record_id, "u": user["user_id"]}):
        raise HTTPException(404, "记录不存在")
    db_exec(conn, "DELETE FROM weight_records WHERE id = :id", {"id": record_id})
    return {"ok": True}


# ==================== Diet ====================

@app.get("/api/diet")
def list_diet(request: Request, date: str = None):
    user = get_current_user(request)
    conn = get_db()
    p = {"u": user["user_id"]}
    if date:
        p["d"] = date
        rows = db_exec(conn,
            "SELECT * FROM diet_records WHERE user_id=:u AND date = :d ORDER BY created_at DESC", p)
    else:
        rows = db_exec(conn,
            "SELECT * FROM diet_records WHERE user_id=:u ORDER BY date DESC, created_at DESC LIMIT 100", p)
    return [_fmt(r) for r in rows]


@app.post("/api/diet", response_model=DietRecordOut)
def add_diet(request: Request, record: DietRecord):
    user = get_current_user(request)
    conn = get_db()
    row = db_exec_one(conn,
        "INSERT INTO diet_records (user_id, date, meal_type, food_name, calories_kcal, note) VALUES (:u,:d,:m,:f,:c,:n) RETURNING *",
        {"u": user["user_id"], "d": record.date, "m": record.meal_type,
         "f": record.food_name, "c": record.calories_kcal, "n": record.note})
    return _fmt(row)


@app.delete("/api/diet/{record_id}")
def delete_diet(request: Request, record_id: int):
    user = get_current_user(request)
    conn = get_db()
    if not db_exec_one(conn,
            "SELECT id FROM diet_records WHERE id=:id AND user_id=:u",
            {"id": record_id, "u": user["user_id"]}):
        raise HTTPException(404, "记录不存在")
    db_exec(conn, "DELETE FROM diet_records WHERE id = :id", {"id": record_id})
    return {"ok": True}


@app.get("/api/diet/summary")
def diet_summary(request: Request, date: str):
    user = get_current_user(request)
    conn = get_db()
    row = db_exec_one(conn,
        "SELECT COALESCE(SUM(calories_kcal), 0) AS total FROM diet_records WHERE user_id=:u AND date = :d",
        {"u": user["user_id"], "d": date})
    return {"date": date, "total_calories": _f(row["total"])}


# ==================== Exercise ====================

@app.get("/api/exercise")
def list_exercise(request: Request, date: str = None):
    user = get_current_user(request)
    conn = get_db()
    p = {"u": user["user_id"]}
    if date:
        p["d"] = date
        rows = db_exec(conn,
            "SELECT * FROM exercise_records WHERE user_id=:u AND date = :d ORDER BY created_at DESC", p)
    else:
        rows = db_exec(conn,
            "SELECT * FROM exercise_records WHERE user_id=:u ORDER BY date DESC, created_at DESC LIMIT 100", p)
    return [_fmt(r) for r in rows]


@app.post("/api/exercise", response_model=ExerciseRecordOut)
def add_exercise(request: Request, record: ExerciseRecord):
    user = get_current_user(request)
    conn = get_db()
    row = db_exec_one(conn,
        "INSERT INTO exercise_records (user_id, date, exercise_name, duration_min, calories_burned, note) VALUES (:u,:d,:en,:dm,:cb,:n) RETURNING *",
        {"u": user["user_id"], "d": record.date, "en": record.exercise_name,
         "dm": record.duration_min, "cb": record.calories_burned, "n": record.note})
    return _fmt(row)


@app.delete("/api/exercise/{record_id}")
def delete_exercise(request: Request, record_id: int):
    user = get_current_user(request)
    conn = get_db()
    if not db_exec_one(conn,
            "SELECT id FROM exercise_records WHERE id=:id AND user_id=:u",
            {"id": record_id, "u": user["user_id"]}):
        raise HTTPException(404, "记录不存在")
    db_exec(conn, "DELETE FROM exercise_records WHERE id = :id", {"id": record_id})
    return {"ok": True}


@app.get("/api/exercise/summary")
def exercise_summary(request: Request, date: str):
    user = get_current_user(request)
    conn = get_db()
    row = db_exec_one(conn,
        "SELECT COALESCE(SUM(calories_burned), 0) AS total FROM exercise_records WHERE user_id=:u AND date = :d",
        {"u": user["user_id"], "d": date})
    return {"date": date, "total_calories_burned": _f(row["total"])}


# ==================== Goals ====================

@app.get("/api/goals")
def list_goals(request: Request):
    user = get_current_user(request)
    conn = get_db()
    rows = db_exec(conn,
        "SELECT * FROM goals WHERE user_id=:u ORDER BY created_at DESC", {"u": user["user_id"]})
    return [_fmt(r) for r in rows]


@app.post("/api/goals", response_model=GoalOut)
def create_goal(request: Request, goal: Goal):
    user = get_current_user(request)
    conn = get_db()
    db_exec(conn, "UPDATE goals SET is_active = 0 WHERE user_id=:u", {"u": user["user_id"]})
    row = db_exec_one(conn,
        "INSERT INTO goals (user_id, target_weight_kg, start_date, end_date, daily_calorie_target, height_cm) VALUES (:u,:t,:s,:e,:d,:h) RETURNING *",
        {"u": user["user_id"], "t": goal.target_weight_kg, "s": goal.start_date,
         "e": goal.end_date, "d": goal.daily_calorie_target, "h": goal.height_cm})
    return _fmt(row)


@app.put("/api/goals/{goal_id}", response_model=GoalOut)
def update_goal(request: Request, goal_id: int, goal: Goal):
    user = get_current_user(request)
    conn = get_db()
    if not db_exec_one(conn,
            "SELECT id FROM goals WHERE id=:id AND user_id=:u", {"id": goal_id, "u": user["user_id"]}):
        raise HTTPException(404, "目标不存在")
    row = db_exec_one(conn,
        "UPDATE goals SET target_weight_kg=:t, start_date=:s, end_date=:e, daily_calorie_target=:d, height_cm=:h WHERE id=:id RETURNING *",
        {"t": goal.target_weight_kg, "s": goal.start_date, "e": goal.end_date,
         "d": goal.daily_calorie_target, "h": goal.height_cm, "id": goal_id})
    return _fmt(row)


@app.get("/api/goals/progress")
def goal_progress(request: Request):
    user = get_current_user(request)
    conn = get_db()
    goal = db_exec_one(conn,
        "SELECT * FROM goals WHERE user_id=:u AND is_active = 1 ORDER BY created_at DESC LIMIT 1",
        {"u": user["user_id"]})
    if not goal:
        return {"has_goal": False}

    latest = db_exec_one(conn,
        "SELECT weight_kg FROM weight_records WHERE user_id=:u ORDER BY date DESC LIMIT 1",
        {"u": user["user_id"]})

    cw = _f(latest["weight_kg"]) if latest else None
    tw = _f(goal["target_weight_kg"])
    remaining = round(cw - tw, 1) if cw else None
    h = _f(goal["height_cm"] or 0) / 100
    bmi = round(cw / (h * h), 1) if cw and h > 0 else None

    return {
        "has_goal": True, "target_weight_kg": tw, "current_weight_kg": cw,
        "remaining_kg": remaining, "start_date": str(goal["start_date"]),
        "end_date": str(goal["end_date"]),
        "daily_calorie_target": _f(goal.get("daily_calorie_target")) if goal.get("daily_calorie_target") else None,
        "height_cm": _f(goal["height_cm"]), "bmi": bmi,
    }


# ==================== Stats ====================

@app.get("/api/stats/bmi")
def calc_bmi(request: Request, weight_kg: float, height_cm: float):
    get_current_user(request)
    if height_cm <= 0:
        raise HTTPException(400, "身高必须大于0")
    h = height_cm / 100
    bmi = round(weight_kg / (h * h), 1)
    if bmi < 18.5: label = "偏瘦"
    elif bmi < 24: label = "正常"
    elif bmi < 28: label = "偏胖"
    else: label = "肥胖"
    return {"bmi": bmi, "label": label}


@app.get("/api/stats/overview")
def overview(request: Request, date: str = None):
    user = get_current_user(request)
    today = date or _dt.date.today().isoformat()
    conn = get_db()
    p = {"u": user["user_id"], "d": today}

    goal = db_exec_one(conn,
        "SELECT * FROM goals WHERE user_id=:u AND is_active = 1 ORDER BY created_at DESC LIMIT 1", {"u": user["user_id"]})
    lw = db_exec_one(conn,
        "SELECT weight_kg FROM weight_records WHERE user_id=:u ORDER BY date DESC LIMIT 1", {"u": user["user_id"]})
    diet = db_exec_one(conn,
        "SELECT COALESCE(SUM(calories_kcal), 0) AS total FROM diet_records WHERE user_id=:u AND date = :d", p)
    ex = db_exec_one(conn,
        "SELECT COALESCE(SUM(calories_burned), 0) AS total FROM exercise_records WHERE user_id=:u AND date = :d", p)

    result = {
        "date": today,
        "current_weight_kg": _f(lw["weight_kg"]) if lw else None,
        "today_calories_in": _f(diet["total"]),
        "today_calories_out": _f(ex["total"]),
        "net_calories": _f(diet["total"]) - _f(ex["total"]),
    }
    if goal:
        result["target_weight_kg"] = _f(goal["target_weight_kg"])
        result["daily_calorie_target"] = _f(goal.get("daily_calorie_target")) if goal.get("daily_calorie_target") else None
        result["height_cm"] = _f(goal["height_cm"])
        if lw:
            result["remaining_kg"] = round(_f(lw["weight_kg"]) - _f(goal["target_weight_kg"]), 1)
    return result


# ==================== PK ====================

@app.get("/api/users/search")
def search_users(request: Request, q: str = ""):
    get_current_user(request)
    if len(q) < 1:
        return []
    conn = get_db()
    rows = db_exec(conn, "SELECT id, username FROM users WHERE username LIKE :q LIMIT 10", {"q": f"%{q}%"})
    return [_fmt(r) for r in rows]


@app.post("/api/pk/create")
def pk_create(request: Request, body: PKCreate):
    user = get_current_user(request)
    conn = get_db()

    member_ids = [user["user_id"]]
    for uname in body.member_usernames:
        row = db_exec_one(conn, "SELECT id FROM users WHERE username = :u", {"u": uname})
        if not row:
            raise HTTPException(400, f"用户 '{uname}' 不存在")
        if row["id"] == user["user_id"]:
            raise HTTPException(400, "不能和自己PK")
        if row["id"] in member_ids:
            raise HTTPException(400, "不能重复添加同一用户")
        member_ids.append(row["id"])

    row = db_exec_one(conn,
        "INSERT INTO pk_groups (name, creator_id) VALUES (:n, :c) RETURNING id",
        {"n": body.name, "c": user["user_id"]})
    gid = row["id"]
    for mid in member_ids:
        db_exec(conn, "INSERT INTO pk_members (group_id, user_id) VALUES (:g, :u)", {"g": gid, "u": mid})
    return {"ok": True, "group_id": gid}


def _member_progress(conn, uid: int) -> PKMemberInfo:
    urow = db_exec_one(conn, "SELECT username FROM users WHERE id = :u", {"u": uid})
    goal = db_exec_one(conn,
        "SELECT * FROM goals WHERE user_id=:u AND is_active=1 ORDER BY created_at DESC LIMIT 1", {"u": uid})
    latest = db_exec_one(conn,
        "SELECT weight_kg FROM weight_records WHERE user_id=:u ORDER BY date DESC LIMIT 1", {"u": uid})
    earliest = db_exec_one(conn,
        "SELECT weight_kg FROM weight_records WHERE user_id=:u ORDER BY date ASC LIMIT 1", {"u": uid})

    info = PKMemberInfo(
        user_id=uid,
        username=urow["username"] if urow else "?",
        target_weight_kg=_f(goal["target_weight_kg"]) if goal else None,
        current_weight_kg=_f(latest["weight_kg"]) if latest else None,
        start_weight_kg=_f(earliest["weight_kg"]) if earliest else None,
    )

    if latest and earliest and goal:
        total_to_lose = _f(earliest["weight_kg"]) - _f(goal["target_weight_kg"])
        lost_so_far = _f(earliest["weight_kg"]) - _f(latest["weight_kg"])
        info.total_lost_kg = round(lost_so_far, 1)
        if total_to_lose > 0:
            info.progress_pct = min(100, max(0, round(lost_so_far / total_to_lose * 100, 1)))
        elif lost_so_far >= total_to_lose:
            info.progress_pct = 100
    elif latest and earliest:
        info.total_lost_kg = round(_f(earliest["weight_kg"]) - _f(latest["weight_kg"]), 1)

    return info


@app.get("/api/pk/groups")
def pk_list_groups(request: Request):
    user = get_current_user(request)
    conn = get_db()
    rows = db_exec(conn,
        "SELECT g.id, g.name, g.creator_id, g.created_at FROM pk_groups g "
        "JOIN pk_members m ON g.id = m.group_id WHERE m.user_id = :u ORDER BY g.created_at DESC",
        {"u": user["user_id"]})

    result = []
    for g in rows:
        members = db_exec(conn, "SELECT user_id FROM pk_members WHERE group_id = :g", {"g": g["id"]})
        member_infos = [_member_progress(conn, m["user_id"]) for m in members]
        result.append({
            "id": g["id"], "name": g["name"], "creator_id": g["creator_id"],
            "created_at": str(g["created_at"]),
            "members": [m.model_dump() for m in member_infos],
        })
    return result


@app.delete("/api/pk/{group_id}")
def pk_leave(request: Request, group_id: int):
    user = get_current_user(request)
    conn = get_db()
    db_exec(conn, "DELETE FROM pk_members WHERE group_id=:g AND user_id=:u",
            {"g": group_id, "u": user["user_id"]})
    row = db_exec_one(conn, "SELECT COUNT(*) as c FROM pk_members WHERE group_id=:g", {"g": group_id})
    if row["c"] == 0:
        db_exec(conn, "DELETE FROM pk_groups WHERE id=:g", {"g": group_id})
    return {"ok": True}


@app.get("/api/pk/{group_id}")
def pk_detail(request: Request, group_id: int):
    user = get_current_user(request)
    conn = get_db()
    if not db_exec_one(conn, "SELECT 1 FROM pk_members WHERE group_id=:g AND user_id=:u",
                       {"g": group_id, "u": user["user_id"]}):
        raise HTTPException(403, "你不在此PK组中")

    g = db_exec_one(conn, "SELECT * FROM pk_groups WHERE id=:g", {"g": group_id})
    members = db_exec(conn, "SELECT user_id FROM pk_members WHERE group_id=:g", {"g": group_id})
    member_infos = [_member_progress(conn, m["user_id"]) for m in members]
    return {
        "id": g["id"], "name": g["name"], "creator_id": g["creator_id"],
        "created_at": str(g["created_at"]),
        "members": [m.model_dump() for m in member_infos],
    }


# ==================== Startup ====================

@app.on_event("startup")
def startup():
    import os as _os
    if _os.environ.get("DATABASE_URL"):
        init_db()
    else:
        print("WARNING: DATABASE_URL not set")


import os as _os
STATIC_DIR = _os.path.join(_os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
