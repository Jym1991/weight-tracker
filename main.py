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
    try:
        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE username = ?", (body.username,)).fetchone()
        if existing:
            raise HTTPException(400, "用户名已存在")
        pw_hash = hash_password(body.password)
        cur = db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)", (body.username, pw_hash))
        db.commit()
        token = create_token(cur.lastrowid, body.username)
        return {"token": token, "username": body.username}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(500, f"ERR: {type(e).__name__}: {str(e)}")


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
            (user["user_id"], date_from, date_to)).fetchall()
    elif date_from:
        rows = db.execute(
            "SELECT * FROM weight_records WHERE user_id=? AND date >= ? ORDER BY date DESC",
            (user["user_id"], date_from)).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM weight_records WHERE user_id=? ORDER BY date DESC LIMIT 90",
            (user["user_id"],)).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/weight", response_model=WeightRecordOut)
def add_weight(request: Request, record: WeightRecord):
    user = get_current_user(request)
    db = get_db()
    cur = db.execute(
        "INSERT INTO weight_records (user_id, date, weight_kg, note) VALUES (?, ?, ?, ?)",
        (user["user_id"], record.date, record.weight_kg, record.note))
    db.commit()
    row = db.execute("SELECT * FROM weight_records WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.delete("/api/weight/{record_id}")
def delete_weight(request: Request, record_id: int):
    user = get_current_user(request)
    db = get_db()
    row = db.execute("SELECT id FROM weight_records WHERE id=? AND user_id=?", (record_id, user["user_id"])).fetchone()
    if not row: raise HTTPException(404, "记录不存在")
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
            (user["user_id"], date)).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM diet_records WHERE user_id=? ORDER BY date DESC, created_at DESC LIMIT 100",
            (user["user_id"],)).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/diet", response_model=DietRecordOut)
def add_diet(request: Request, record: DietRecord):
    user = get_current_user(request)
    db = get_db()
    cur = db.execute(
        "INSERT INTO diet_records (user_id, date, meal_type, food_name, calories_kcal, note) VALUES (?, ?, ?, ?, ?, ?)",
        (user["user_id"], record.date, record.meal_type, record.food_name, record.calories_kcal, record.note))
    db.commit()
    row = db.execute("SELECT * FROM diet_records WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.delete("/api/diet/{record_id}")
def delete_diet(request: Request, record_id: int):
    user = get_current_user(request)
    db = get_db()
    row = db.execute("SELECT id FROM diet_records WHERE id=? AND user_id=?", (record_id, user["user_id"])).fetchone()
    if not row: raise HTTPException(404, "记录不存在")
    db.execute("DELETE FROM diet_records WHERE id = ?", (record_id,))
    db.commit()
    return {"ok": True}


@app.get("/api/diet/summary")
def diet_summary(request: Request, date: str):
    user = get_current_user(request)
    db = get_db()
    row = db.execute(
        "SELECT COALESCE(SUM(calories_kcal), 0) AS total FROM diet_records WHERE user_id=? AND date = ?",
        (user["user_id"], date)).fetchone()
    return {"date": date, "total_calories": row["total"]}


# ==================== Exercise ====================

@app.get("/api/exercise")
def list_exercise(request: Request, date: str = None):
    user = get_current_user(request)
    db = get_db()
    if date:
        rows = db.execute(
            "SELECT * FROM exercise_records WHERE user_id=? AND date = ? ORDER BY created_at DESC",
            (user["user_id"], date)).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM exercise_records WHERE user_id=? ORDER BY date DESC, created_at DESC LIMIT 100",
            (user["user_id"],)).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/exercise", response_model=ExerciseRecordOut)
def add_exercise(request: Request, record: ExerciseRecord):
    user = get_current_user(request)
    db = get_db()
    cur = db.execute(
        "INSERT INTO exercise_records (user_id, date, exercise_name, duration_min, calories_burned, note) VALUES (?, ?, ?, ?, ?, ?)",
        (user["user_id"], record.date, record.exercise_name, record.duration_min, record.calories_burned, record.note))
    db.commit()
    row = db.execute("SELECT * FROM exercise_records WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.delete("/api/exercise/{record_id}")
def delete_exercise(request: Request, record_id: int):
    user = get_current_user(request)
    db = get_db()
    row = db.execute("SELECT id FROM exercise_records WHERE id=? AND user_id=?", (record_id, user["user_id"])).fetchone()
    if not row: raise HTTPException(404, "记录不存在")
    db.execute("DELETE FROM exercise_records WHERE id = ?", (record_id,))
    db.commit()
    return {"ok": True}


@app.get("/api/exercise/summary")
def exercise_summary(request: Request, date: str):
    user = get_current_user(request)
    db = get_db()
    row = db.execute(
        "SELECT COALESCE(SUM(calories_burned), 0) AS total FROM exercise_records WHERE user_id=? AND date = ?",
        (user["user_id"], date)).fetchone()
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
        (user["user_id"], goal.target_weight_kg, goal.start_date, goal.end_date, goal.daily_calorie_target, goal.height_cm))
    db.commit()
    row = db.execute("SELECT * FROM goals WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.put("/api/goals/{goal_id}", response_model=GoalOut)
def update_goal(request: Request, goal_id: int, goal: Goal):
    user = get_current_user(request)
    db = get_db()
    row = db.execute("SELECT id FROM goals WHERE id=? AND user_id=?", (goal_id, user["user_id"])).fetchone()
    if not row: raise HTTPException(404, "目标不存在")
    db.execute(
        "UPDATE goals SET target_weight_kg=?, start_date=?, end_date=?, daily_calorie_target=?, height_cm=? WHERE id=?",
        (goal.target_weight_kg, goal.start_date, goal.end_date, goal.daily_calorie_target, goal.height_cm, goal_id))
    db.commit()
    row = db.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    return dict(row)


@app.get("/api/goals/progress")
def goal_progress(request: Request):
    user = get_current_user(request)
    db = get_db()
    goal = db.execute(
        "SELECT * FROM goals WHERE user_id=? AND is_active = 1 ORDER BY created_at DESC LIMIT 1",
        (user["user_id"],)).fetchone()
    if not goal: return {"has_goal": False}

    latest = db.execute(
        "SELECT weight_kg FROM weight_records WHERE user_id=? ORDER BY date DESC LIMIT 1",
        (user["user_id"],)).fetchone()

    cw = latest["weight_kg"] if latest else None
    tw = goal["target_weight_kg"]
    remaining = round(cw - tw, 1) if cw else None
    h = (goal["height_cm"] or 0) / 100
    bmi = round(cw / (h * h), 1) if cw and h > 0 else None

    return {
        "has_goal": True, "target_weight_kg": tw, "current_weight_kg": cw,
        "remaining_kg": remaining, "start_date": goal["start_date"], "end_date": goal["end_date"],
        "daily_calorie_target": goal["daily_calorie_target"], "height_cm": goal["height_cm"], "bmi": bmi,
    }


# ==================== Stats ====================

@app.get("/api/stats/bmi")
def calc_bmi(request: Request, weight_kg: float, height_cm: float):
    get_current_user(request)
    if height_cm <= 0: raise HTTPException(400, "身高必须大于0")
    h = height_cm / 100; bmi = round(weight_kg / (h * h), 1)
    if bmi < 18.5: label = "偏瘦"
    elif bmi < 24: label = "正常"
    elif bmi < 28: label = "偏胖"
    else: label = "肥胖"
    return {"bmi": bmi, "label": label}


@app.get("/api/stats/overview")
def overview(request: Request, date: str = None):
    import datetime as _dt
    user = get_current_user(request)
    today = date or _dt.date.today().isoformat()
    db = get_db()
    uid = user["user_id"]

    goal = db.execute("SELECT * FROM goals WHERE user_id=? AND is_active=1 ORDER BY created_at DESC LIMIT 1", (uid,)).fetchone()
    lw = db.execute("SELECT weight_kg FROM weight_records WHERE user_id=? ORDER BY date DESC LIMIT 1", (uid,)).fetchone()
    diet = db.execute("SELECT COALESCE(SUM(calories_kcal),0) AS total FROM diet_records WHERE user_id=? AND date=?", (uid, today)).fetchone()
    ex = db.execute("SELECT COALESCE(SUM(calories_burned),0) AS total FROM exercise_records WHERE user_id=? AND date=?", (uid, today)).fetchone()

    result = {
        "date": today,
        "current_weight_kg": lw["weight_kg"] if lw else None,
        "today_calories_in": diet["total"], "today_calories_out": ex["total"],
        "net_calories": diet["total"] - ex["total"],
    }
    if goal:
        result["target_weight_kg"] = goal["target_weight_kg"]
        result["daily_calorie_target"] = goal["daily_calorie_target"]
        result["height_cm"] = goal["height_cm"]
        if lw: result["remaining_kg"] = round(lw["weight_kg"] - goal["target_weight_kg"], 1)
    return result


# ==================== PK ====================

@app.get("/api/users/search")
def search_users(request: Request, q: str = ""):
    get_current_user(request)
    if len(q) < 1: return []
    db = get_db()
    rows = db.execute("SELECT id, username FROM users WHERE username LIKE ? LIMIT 10", (f"%{q}%",)).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/pk/create")
def pk_create(request: Request, body: PKCreate):
    user = get_current_user(request)
    db = get_db()

    mids = [user["user_id"]]
    for un in body.member_usernames:
        r = db.execute("SELECT id FROM users WHERE username = ?", (un,)).fetchone()
        if not r: raise HTTPException(400, f"用户 '{un}' 不存在")
        if r["id"] == user["user_id"]: raise HTTPException(400, "不能和自己PK")
        if r["id"] in mids: raise HTTPException(400, "不能重复添加")
        mids.append(r["id"])

    cur = db.execute("INSERT INTO pk_groups (name, creator_id) VALUES (?, ?)", (body.name, user["user_id"]))
    gid = cur.lastrowid
    for mid in mids: db.execute("INSERT INTO pk_members (group_id, user_id) VALUES (?, ?)", (gid, mid))
    db.commit()
    return {"ok": True, "group_id": gid}


def _mp(db, uid):
    u = db.execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchone()
    g = db.execute("SELECT * FROM goals WHERE user_id=? AND is_active=1 ORDER BY created_at DESC LIMIT 1", (uid,)).fetchone()
    la = db.execute("SELECT weight_kg FROM weight_records WHERE user_id=? ORDER BY date DESC LIMIT 1", (uid,)).fetchone()
    ea = db.execute("SELECT weight_kg FROM weight_records WHERE user_id=? ORDER BY date ASC LIMIT 1", (uid,)).fetchone()
    info = PKMemberInfo(
        user_id=uid, username=u["username"] if u else "?",
        target_weight_kg=g["target_weight_kg"] if g else None,
        current_weight_kg=la["weight_kg"] if la else None,
        start_weight_kg=ea["weight_kg"] if ea else None,
    )
    if la and ea and g:
        total = ea["weight_kg"] - g["target_weight_kg"]
        lost = ea["weight_kg"] - la["weight_kg"]
        info.total_lost_kg = round(lost, 1)
        if total > 0: info.progress_pct = min(100, max(0, round(lost / total * 100, 1)))
        elif lost >= total: info.progress_pct = 100
    elif la and ea: info.total_lost_kg = round(ea["weight_kg"] - la["weight_kg"], 1)
    return info


@app.get("/api/pk/groups")
def pk_list_groups(request: Request):
    user = get_current_user(request)
    db = get_db()
    rows = db.execute(
        "SELECT g.id, g.name, g.creator_id, g.created_at FROM pk_groups g "
        "JOIN pk_members m ON g.id=m.group_id WHERE m.user_id=? ORDER BY g.created_at DESC",
        (user["user_id"],)).fetchall()
    result = []
    for g in rows:
        ms = db.execute("SELECT user_id FROM pk_members WHERE group_id=?", (g["id"],)).fetchall()
        infos = [_mp(db, m["user_id"]) for m in ms]
        result.append({
            "id": g["id"], "name": g["name"], "creator_id": g["creator_id"],
            "created_at": g["created_at"], "members": [m.model_dump() for m in infos],
        })
    return result


@app.delete("/api/pk/{group_id}")
def pk_leave(request: Request, group_id: int):
    user = get_current_user(request)
    db = get_db()
    db.execute("DELETE FROM pk_members WHERE group_id=? AND user_id=?", (group_id, user["user_id"]))
    r = db.execute("SELECT COUNT(*) as c FROM pk_members WHERE group_id=?", (group_id,)).fetchone()
    if r["c"] == 0: db.execute("DELETE FROM pk_groups WHERE id=?", (group_id,))
    db.commit()
    return {"ok": True}


@app.get("/api/pk/{group_id}")
def pk_detail(request: Request, group_id: int):
    user = get_current_user(request)
    db = get_db()
    r = db.execute("SELECT 1 FROM pk_members WHERE group_id=? AND user_id=?", (group_id, user["user_id"])).fetchone()
    if not r: raise HTTPException(403, "不在此PK组中")
    g = db.execute("SELECT * FROM pk_groups WHERE id=?", (group_id,)).fetchone()
    ms = db.execute("SELECT user_id FROM pk_members WHERE group_id=?", (group_id,)).fetchall()
    infos = [_mp(db, m["user_id"]) for m in ms]
    return {"id": g["id"], "name": g["name"], "creator_id": g["creator_id"],
            "created_at": g["created_at"], "members": [m.model_dump() for m in infos]}


@app.get("/api/ping")
def ping():
    return {"ok": True}


# ==================== Startup ====================

@app.on_event("startup")
def startup():
    init_db()


import os
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
