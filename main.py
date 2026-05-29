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
import datetime as _dt

app = FastAPI(title="减肥体重管理系统")


def _dict(row):
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, (_dt.date, _dt.datetime)):
            d[k] = v.isoformat()
    return d


# ==================== Auth ====================

@app.post("/api/auth/register", response_model=TokenResponse)
def register(body: UserRegister):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (body.username,))
    if cur.fetchone():
        raise HTTPException(400, "用户名已存在")
    pw_hash = hash_password(body.password)
    cur.execute(
        "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
        (body.username, pw_hash))
    user_id = cur.fetchone()["id"]
    token = create_token(user_id, body.username)
    return {"token": token, "username": body.username}


@app.post("/api/auth/login", response_model=TokenResponse)
def login(body: UserLogin):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, password_hash FROM users WHERE username = %s", (body.username,))
    row = cur.fetchone()
    if not row or not check_password(body.password, row["password_hash"]):
        raise HTTPException(401, "用户名或密码错误")
    token = create_token(row["id"], body.username)
    return {"token": token, "username": body.username}


# ==================== Weight ====================

@app.get("/api/weight")
def list_weight(request: Request, date_from: str = None, date_to: str = None):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    uid = user["user_id"]
    if date_from and date_to:
        cur.execute(
            "SELECT * FROM weight_records WHERE user_id=%s AND date BETWEEN %s AND %s ORDER BY date DESC",
            (uid, date_from, date_to))
    elif date_from:
        cur.execute(
            "SELECT * FROM weight_records WHERE user_id=%s AND date >= %s ORDER BY date DESC",
            (uid, date_from))
    else:
        cur.execute(
            "SELECT * FROM weight_records WHERE user_id=%s ORDER BY date DESC LIMIT 90", (uid,))
    return [_dict(r) for r in cur.fetchall()]


@app.post("/api/weight", response_model=WeightRecordOut)
def add_weight(request: Request, record: WeightRecord):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO weight_records (user_id, date, weight_kg, note) VALUES (%s,%s,%s,%s) RETURNING *",
        (user["user_id"], record.date, record.weight_kg, record.note))
    return _dict(cur.fetchone())


@app.delete("/api/weight/{record_id}")
def delete_weight(request: Request, record_id: int):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM weight_records WHERE id=%s AND user_id=%s",
                (record_id, user["user_id"]))
    if not cur.fetchone():
        raise HTTPException(404, "记录不存在")
    cur.execute("DELETE FROM weight_records WHERE id=%s", (record_id,))
    return {"ok": True}


# ==================== Diet ====================

@app.get("/api/diet")
def list_diet(request: Request, date: str = None):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    uid = user["user_id"]
    if date:
        cur.execute(
            "SELECT * FROM diet_records WHERE user_id=%s AND date=%s ORDER BY created_at DESC",
            (uid, date))
    else:
        cur.execute(
            "SELECT * FROM diet_records WHERE user_id=%s ORDER BY date DESC, created_at DESC LIMIT 100",
            (uid,))
    return [_dict(r) for r in cur.fetchall()]


@app.post("/api/diet", response_model=DietRecordOut)
def add_diet(request: Request, record: DietRecord):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO diet_records (user_id, date, meal_type, food_name, calories_kcal, note) VALUES (%s,%s,%s,%s,%s,%s) RETURNING *",
        (user["user_id"], record.date, record.meal_type, record.food_name, record.calories_kcal, record.note))
    return _dict(cur.fetchone())


@app.delete("/api/diet/{record_id}")
def delete_diet(request: Request, record_id: int):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM diet_records WHERE id=%s AND user_id=%s",
                (record_id, user["user_id"]))
    if not cur.fetchone():
        raise HTTPException(404, "记录不存在")
    cur.execute("DELETE FROM diet_records WHERE id=%s", (record_id,))
    return {"ok": True}


@app.get("/api/diet/summary")
def diet_summary(request: Request, date: str):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT COALESCE(SUM(calories_kcal), 0) AS total FROM diet_records WHERE user_id=%s AND date=%s",
        (user["user_id"], date))
    return {"date": date, "total_calories": float(cur.fetchone()["total"])}


# ==================== Exercise ====================

@app.get("/api/exercise")
def list_exercise(request: Request, date: str = None):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    uid = user["user_id"]
    if date:
        cur.execute(
            "SELECT * FROM exercise_records WHERE user_id=%s AND date=%s ORDER BY created_at DESC",
            (uid, date))
    else:
        cur.execute(
            "SELECT * FROM exercise_records WHERE user_id=%s ORDER BY date DESC, created_at DESC LIMIT 100",
            (uid,))
    return [_dict(r) for r in cur.fetchall()]


@app.post("/api/exercise", response_model=ExerciseRecordOut)
def add_exercise(request: Request, record: ExerciseRecord):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO exercise_records (user_id, date, exercise_name, duration_min, calories_burned, note) VALUES (%s,%s,%s,%s,%s,%s) RETURNING *",
        (user["user_id"], record.date, record.exercise_name, record.duration_min, record.calories_burned, record.note))
    return _dict(cur.fetchone())


@app.delete("/api/exercise/{record_id}")
def delete_exercise(request: Request, record_id: int):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM exercise_records WHERE id=%s AND user_id=%s",
                (record_id, user["user_id"]))
    if not cur.fetchone():
        raise HTTPException(404, "记录不存在")
    cur.execute("DELETE FROM exercise_records WHERE id=%s", (record_id,))
    return {"ok": True}


@app.get("/api/exercise/summary")
def exercise_summary(request: Request, date: str):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT COALESCE(SUM(calories_burned), 0) AS total FROM exercise_records WHERE user_id=%s AND date=%s",
        (user["user_id"], date))
    return {"date": date, "total_calories_burned": float(cur.fetchone()["total"])}


# ==================== Goals ====================

@app.get("/api/goals")
def list_goals(request: Request):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM goals WHERE user_id=%s ORDER BY created_at DESC",
                (user["user_id"],))
    return [_dict(r) for r in cur.fetchall()]


@app.post("/api/goals", response_model=GoalOut)
def create_goal(request: Request, goal: Goal):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE goals SET is_active=0 WHERE user_id=%s", (user["user_id"],))
    cur.execute(
        "INSERT INTO goals (user_id, target_weight_kg, start_date, end_date, daily_calorie_target, height_cm) VALUES (%s,%s,%s,%s,%s,%s) RETURNING *",
        (user["user_id"], goal.target_weight_kg, goal.start_date, goal.end_date,
         goal.daily_calorie_target, goal.height_cm))
    return _dict(cur.fetchone())


@app.put("/api/goals/{goal_id}", response_model=GoalOut)
def update_goal(request: Request, goal_id: int, goal: Goal):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM goals WHERE id=%s AND user_id=%s",
                (goal_id, user["user_id"]))
    if not cur.fetchone():
        raise HTTPException(404, "目标不存在")
    cur.execute(
        "UPDATE goals SET target_weight_kg=%s, start_date=%s, end_date=%s, daily_calorie_target=%s, height_cm=%s WHERE id=%s RETURNING *",
        (goal.target_weight_kg, goal.start_date, goal.end_date,
         goal.daily_calorie_target, goal.height_cm, goal_id))
    return _dict(cur.fetchone())


@app.get("/api/goals/progress")
def goal_progress(request: Request):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM goals WHERE user_id=%s AND is_active=1 ORDER BY created_at DESC LIMIT 1",
        (user["user_id"],))
    goal = cur.fetchone()
    if not goal:
        return {"has_goal": False}

    cur.execute(
        "SELECT weight_kg FROM weight_records WHERE user_id=%s ORDER BY date DESC LIMIT 1",
        (user["user_id"],))
    latest = cur.fetchone()

    cw = float(latest["weight_kg"]) if latest else None
    tw = float(goal["target_weight_kg"])
    remaining = round(cw - tw, 1) if cw else None
    h = float(goal["height_cm"] or 0) / 100
    bmi = round(cw / (h * h), 1) if cw and h > 0 else None

    return {
        "has_goal": True, "target_weight_kg": tw, "current_weight_kg": cw,
        "remaining_kg": remaining,
        "start_date": str(goal["start_date"]), "end_date": str(goal["end_date"]),
        "daily_calorie_target": float(goal["daily_calorie_target"]) if goal.get("daily_calorie_target") else None,
        "height_cm": float(goal["height_cm"]), "bmi": bmi,
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
    cur = conn.cursor()
    uid = user["user_id"]

    cur.execute("SELECT * FROM goals WHERE user_id=%s AND is_active=1 ORDER BY created_at DESC LIMIT 1", (uid,))
    goal = cur.fetchone()
    cur.execute("SELECT weight_kg FROM weight_records WHERE user_id=%s ORDER BY date DESC LIMIT 1", (uid,))
    lw = cur.fetchone()
    cur.execute("SELECT COALESCE(SUM(calories_kcal),0) AS total FROM diet_records WHERE user_id=%s AND date=%s", (uid, today))
    diet = cur.fetchone()
    cur.execute("SELECT COALESCE(SUM(calories_burned),0) AS total FROM exercise_records WHERE user_id=%s AND date=%s", (uid, today))
    ex = cur.fetchone()

    result = {
        "date": today,
        "current_weight_kg": float(lw["weight_kg"]) if lw else None,
        "today_calories_in": float(diet["total"]),
        "today_calories_out": float(ex["total"]),
        "net_calories": float(diet["total"]) - float(ex["total"]),
    }
    if goal:
        result["target_weight_kg"] = float(goal["target_weight_kg"])
        result["daily_calorie_target"] = float(goal["daily_calorie_target"]) if goal.get("daily_calorie_target") else None
        result["height_cm"] = float(goal["height_cm"])
        if lw:
            result["remaining_kg"] = round(float(lw["weight_kg"]) - float(goal["target_weight_kg"]), 1)
    return result


# ==================== PK ====================

@app.get("/api/users/search")
def search_users(request: Request, q: str = ""):
    get_current_user(request)
    if len(q) < 1:
        return []
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users WHERE username LIKE %s LIMIT 10", (f"%{q}%",))
    return [_dict(r) for r in cur.fetchall()]


@app.post("/api/pk/create")
def pk_create(request: Request, body: PKCreate):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()

    member_ids = [user["user_id"]]
    for uname in body.member_usernames:
        cur.execute("SELECT id FROM users WHERE username=%s", (uname,))
        row = cur.fetchone()
        if not row: raise HTTPException(400, f"用户 '{uname}' 不存在")
        if row["id"] == user["user_id"]: raise HTTPException(400, "不能和自己PK")
        if row["id"] in member_ids: raise HTTPException(400, "不能重复添加")
        member_ids.append(row["id"])

    cur.execute("INSERT INTO pk_groups (name, creator_id) VALUES (%s,%s) RETURNING id",
                (body.name, user["user_id"]))
    gid = cur.fetchone()["id"]
    for mid in member_ids:
        cur.execute("INSERT INTO pk_members (group_id, user_id) VALUES (%s,%s)", (gid, mid))
    return {"ok": True, "group_id": gid}


def _member_progress(conn, uid: int) -> PKMemberInfo:
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE id=%s", (uid,))
    u = cur.fetchone()
    cur.execute("SELECT * FROM goals WHERE user_id=%s AND is_active=1 ORDER BY created_at DESC LIMIT 1", (uid,))
    goal = cur.fetchone()
    cur.execute("SELECT weight_kg FROM weight_records WHERE user_id=%s ORDER BY date DESC LIMIT 1", (uid,))
    latest = cur.fetchone()
    cur.execute("SELECT weight_kg FROM weight_records WHERE user_id=%s ORDER BY date ASC LIMIT 1", (uid,))
    earliest = cur.fetchone()

    info = PKMemberInfo(
        user_id=uid,
        username=u["username"] if u else "?",
        target_weight_kg=float(goal["target_weight_kg"]) if goal else None,
        current_weight_kg=float(latest["weight_kg"]) if latest else None,
        start_weight_kg=float(earliest["weight_kg"]) if earliest else None,
    )
    if latest and earliest and goal:
        total = float(earliest["weight_kg"]) - float(goal["target_weight_kg"])
        lost = float(earliest["weight_kg"]) - float(latest["weight_kg"])
        info.total_lost_kg = round(lost, 1)
        if total > 0:
            info.progress_pct = min(100, max(0, round(lost / total * 100, 1)))
        elif lost >= total:
            info.progress_pct = 100
    elif latest and earliest:
        info.total_lost_kg = round(float(earliest["weight_kg"]) - float(latest["weight_kg"]), 1)
    return info


@app.get("/api/pk/groups")
def pk_list_groups(request: Request):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT g.id, g.name, g.creator_id, g.created_at FROM pk_groups g "
        "JOIN pk_members m ON g.id=m.group_id WHERE m.user_id=%s ORDER BY g.created_at DESC",
        (user["user_id"],))
    rows = cur.fetchall()
    result = []
    for g in rows:
        cur.execute("SELECT user_id FROM pk_members WHERE group_id=%s", (g["id"],))
        members = cur.fetchall()
        infos = [_member_progress(conn, m["user_id"]) for m in members]
        result.append({
            "id": g["id"], "name": g["name"], "creator_id": g["creator_id"],
            "created_at": str(g["created_at"]),
            "members": [m.model_dump() for m in infos],
        })
    return result


@app.delete("/api/pk/{group_id}")
def pk_leave(request: Request, group_id: int):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM pk_members WHERE group_id=%s AND user_id=%s",
                (group_id, user["user_id"]))
    cur.execute("SELECT COUNT(*) AS c FROM pk_members WHERE group_id=%s", (group_id,))
    if cur.fetchone()["c"] == 0:
        cur.execute("DELETE FROM pk_groups WHERE id=%s", (group_id,))
    return {"ok": True}


@app.get("/api/pk/{group_id}")
def pk_detail(request: Request, group_id: int):
    user = get_current_user(request)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pk_members WHERE group_id=%s AND user_id=%s",
                (group_id, user["user_id"]))
    if not cur.fetchone():
        raise HTTPException(403, "不在此PK组中")
    cur.execute("SELECT * FROM pk_groups WHERE id=%s", (group_id,))
    g = cur.fetchone()
    cur.execute("SELECT user_id FROM pk_members WHERE group_id=%s", (group_id,))
    members = cur.fetchall()
    infos = [_member_progress(conn, m["user_id"]) for m in members]
    return {
        "id": g["id"], "name": g["name"], "creator_id": g["creator_id"],
        "created_at": str(g["created_at"]),
        "members": [m.model_dump() for m in infos],
    }


# ==================== Startup ====================

@app.on_event("startup")
def startup():
    if DATABASE_URL := __import__('os').environ.get("DATABASE_URL"):
        init_db()
    else:
        print("WARNING: DATABASE_URL not set")


import os as _os
STATIC_DIR = _os.path.join(_os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
