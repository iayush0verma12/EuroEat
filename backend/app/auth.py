import hashlib
import os
import secrets
import time

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db import get_db

SECRET = os.environ.get("EUROEAT_SECRET", "dev-secret-change-me-" + "euroeat")
DEMO_USER = os.environ.get("EUROEAT_USER", "traveller")
DEMO_PASSWORD = os.environ.get("EUROEAT_PASSWORD", "EuroEat@2026")

bearer = HTTPBearer(auto_error=False)


def hash_pw(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()


def ensure_demo_user():
    with get_db() as db:
        if db.execute("SELECT 1 FROM users WHERE username=?", (DEMO_USER,)).fetchone():
            return
        salt = secrets.token_hex(8)
        db.execute(
            "INSERT INTO users (username, password_hash, salt, full_name, email, home_city, diet, settings_json) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (DEMO_USER, hash_pw(DEMO_PASSWORD, salt), salt, "Traveller", "traveller@euroeat.app",
             "London", "vegetarian",
             '{"currency":"EUR","language":"en","sparkles":true,"llm_model":"llama3.2","units":"km"}'))


def authenticate(username: str, password: str) -> str | None:
    with get_db() as db:
        row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not row or not secrets.compare_digest(row["password_hash"], hash_pw(password, row["salt"])):
        return None
    return jwt.encode({"sub": username, "exp": int(time.time()) + 12 * 3600}, SECRET, algorithm="HS256")


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if not creds:
        raise HTTPException(401, "Not authenticated")
    try:
        return jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])["sub"]
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
