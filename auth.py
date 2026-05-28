"""JWT authentication utilities."""
import hashlib
import hmac
import json
import os
import time
from functools import wraps
from base64 import urlsafe_b64encode, urlsafe_b64decode

from fastapi import Request, HTTPException

SECRET = os.environ.get("JWT_SECRET", "weight-tracker-secret-change-in-production")


def _b64encode(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return urlsafe_b64decode(data.encode())


def create_token(user_id: int, username: str) -> str:
    header = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64encode(json.dumps({
        "user_id": user_id,
        "username": username,
        "exp": int(time.time()) + 30 * 24 * 3600,  # 30 days
    }).encode())
    signature = hmac.new(SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64encode(signature)}"


def verify_token(token: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload, signature = parts
        expected_sig = _b64encode(
            hmac.new(SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(signature, expected_sig):
            return None
        data = json.loads(_b64decode(payload))
        if data.get("exp", 0) < time.time():
            return None
        return data
    except Exception:
        return None


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return _b64encode(salt) + "$" + _b64encode(dk)


def check_password(password: str, stored: str) -> bool:
    try:
        salt_b64, hash_b64 = stored.split("$")
        salt = _b64decode(salt_b64)
        expected = _b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def get_current_user(request: Request) -> dict:
    """Extract and verify user from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "请先登录")
    token = auth[7:]
    user = verify_token(token)
    if user is None:
        raise HTTPException(401, "登录已过期，请重新登录")
    return user
