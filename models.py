from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List


# ---- Auth ----
class UserRegister(BaseModel):
    username: str = Field(min_length=2, max_length=30)
    password: str = Field(min_length=4, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str
    username: str


# ---- Weight ----
class WeightRecord(BaseModel):
    date: str
    weight_kg: float = Field(gt=0)
    note: str = ""


class WeightRecordOut(WeightRecord):
    id: int
    created_at: str


# ---- Diet ----
class DietRecord(BaseModel):
    date: str
    meal_type: str = Field(pattern=r"^(早餐|午餐|晚餐|加餐)$")
    food_name: str
    calories_kcal: float = Field(ge=0)
    note: str = ""


class DietRecordOut(DietRecord):
    id: int
    created_at: str


# ---- Exercise ----
class ExerciseRecord(BaseModel):
    date: str
    exercise_name: str
    duration_min: float = Field(ge=0)
    calories_burned: float = Field(ge=0)
    note: str = ""


class ExerciseRecordOut(ExerciseRecord):
    id: int
    created_at: str


# ---- Goal ----
class Goal(BaseModel):
    target_weight_kg: float = Field(gt=0)
    start_date: str
    end_date: str
    daily_calorie_target: Optional[float] = None
    height_cm: float = Field(default=0, ge=0)


class GoalOut(Goal):
    id: int
    is_active: int
    created_at: str


# ---- PK ----
class PKCreate(BaseModel):
    name: str = "减肥PK"
    member_usernames: List[str] = Field(min_length=1, max_length=3)


class PKMemberInfo(BaseModel):
    user_id: int
    username: str
    target_weight_kg: Optional[float] = None
    current_weight_kg: Optional[float] = None
    start_weight_kg: Optional[float] = None
    progress_pct: float = 0
    total_lost_kg: float = 0


class PKGroupOut(BaseModel):
    id: int
    name: str
    creator_id: int
    created_at: str
    members: List[PKMemberInfo]
