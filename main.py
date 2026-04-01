
import os
import sys
import json
import logging
import base64
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Optional imports
try:
    import redis
    REDIS_AVAILABLE = True
except Exception:
    redis = None
    REDIS_AVAILABLE = False

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except Exception:
    genai = None
    GENAI_AVAILABLE = False

# -------------------------
# Configuration (env vars)
# -------------------------
DB_PATH = os.getenv("DB_PATH", "human_performance_v2.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
GEMINI_KEY = os.getenv("GEMINI_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")  # change in prod
ALGORITHM = os.getenv("ALGORITHM", "HS256")
TOKEN_EXPIRY_HOURS = int(os.getenv("TOKEN_EXPIRY_HOURS", "24"))

# Logging
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("human_performance")

# Configure Gemini if available and key present
if GENAI_AVAILABLE and GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
        LOG.info("Gemini client configured.")
    except Exception as e:
        LOG.warning(f"Gemini configure failed: {e}")
        GENAI_AVAILABLE = False

# -------------------------
# Security provider (simple)
# -------------------------
class SecurityProvider:
    @staticmethod
    def hash_password(password: str) -> str:
        # deterministic hash using SECRET_KEY as salt (simple; replace with passlib in prod)
        salt = str(SECRET_KEY)
        db_password = password + salt
        return hashlib.sha256(db_password.encode()).hexdigest()

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        return SecurityProvider.hash_password(plain) == hashed

    @staticmethod
    def generate_token(data: dict) -> str:
        payload = data.copy()
        payload.update({"exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)})
        import jwt
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> dict:
        import jwt
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v2/auth/login")

# -------------------------
# DataBus (SQLite + optional Redis)
# -------------------------
class DataBus:
    def __init__(self, db_path: str = DB_PATH, redis_url: str = REDIS_URL):
        self.db_path = db_path
        self.redis_url = redis_url
        self.redis = None
        if REDIS_AVAILABLE:
            try:
                self.redis = redis.from_url(redis_url, decode_responses=True)
                LOG.info("Connected to Redis.")
            except Exception as e:
                LOG.warning(f"Redis connection failed: {e}")
                self.redis = None
        else:
            LOG.info("Redis library not available; continuing without Redis.")
        self._ensure_tables()

    def _connect(self):
        return sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

    def _ensure_tables(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS users 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          username TEXT UNIQUE, 
                          password_hash TEXT)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS performance_logs 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          user_id INTEGER, 
                          heart_rate INTEGER, 
                          steps INTEGER, 
                          screen_time FLOAT, 
                          sleep_hours FLOAT, 
                          performance_score REAL, 
                          ai_recommendation TEXT, 
                          timestamp DATETIME,
                          job_id TEXT,
                          decision_id INTEGER)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS jobs (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          job_id TEXT UNIQUE,
                          user_id INTEGER,
                          type TEXT,
                          payload TEXT,
                          status TEXT,
                          result TEXT,
                          created_at DATETIME,
                          started_at DATETIME,
                          finished_at DATETIME
                        )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS decisions (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          user_id INTEGER,
                          decision_type TEXT,
                          decision_payload TEXT,
                          reason TEXT,
                          outcome TEXT,
                          created_at DATETIME
                        )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS user_profiles (
                          user_id INTEGER PRIMARY KEY,
                          last_active DATETIME,
                          avg_sleep FLOAT,
                          avg_steps FLOAT,
                          risk_score FLOAT,
                          behavior_vector TEXT,
                          updated_at DATETIME
                        )''')
            conn.commit()
            LOG.info("Database tables ensured/created.")

    # User helpers
    def create_user(self, username: str, password_hash: str) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
            conn.commit()
            return cur.lastrowid

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
            row = cur.fetchone()
            if not row:
                return None
            return {"id": row[0], "username": row[1], "password_hash": row[2]}

db = DataBus()

# -------------------------
# Pydantic Schemas
# -------------------------
class UserAuthSchema(BaseModel):
    username: str = Field(..., example="alice")
    password: str = Field(..., example="secret")

class HealthResponse(BaseModel):
    status: str
    db: bool
    redis: bool
    ai: bool
    time: str

# -------------------------
# FastAPI app
# -------------------------
app = FastAPI(title="Human Performance OS v2.0", version="2.0.0",
              description="AI-Driven Performance Orchestration System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root
@app.get("/", tags=["default"])
async def root():
    return {"message": "Human Performance OS is Running", "status": "Online"}

# Health endpoint
@app.get("/api/v2/health", response_model=HealthResponse, tags=["System"])
async def health():
    db_ok = False
    redis_ok = False
    ai_ok = False

    # DB check
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("SELECT 1")
        db_ok = True
    except Exception as e:
        LOG.warning(f"DB health check failed: {e}")
        db_ok = False

    # Redis check
    try:
        if db.redis:
            db.redis.ping()
            redis_ok = True
    except Exception as e:
        LOG.warning(f"Redis health check failed: {e}")
        redis_ok = False

    # AI check (basic)
    try:
        ai_ok = GENAI_AVAILABLE and bool(GEMINI_KEY)
    except Exception:
        ai_ok = False

    status = "ok" if db_ok and (not REDIS_AVAILABLE or redis_ok) else "degraded"
    return {"status": status, "db": db_ok, "redis": redis_ok, "ai": ai_ok, "time": datetime.utcnow().isoformat()}

# -------------------------
# Auth endpoints: register + login
# -------------------------
@app.post("/api/v2/auth/register", tags=["Security"])
async def register(user: UserAuthSchema):
    existing = db.get_user(user.username)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    hashed = SecurityProvider.hash_password(user.password)
    try:
        user_id = db.create_user(user.username, hashed)
        LOG.info(f"Registered user {user.username} id={user_id}")
        return {"status": "success", "message": "Enrolled in OS v2.0", "user_id": user_id}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="User already exists")
    except Exception as e:
        LOG.error(f"Register failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/api/v2/auth/login", tags=["Security"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.get_user(form_data.username)
    if not user or not SecurityProvider.verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")
    token = SecurityProvider.generate_token({"sub": user["username"], "user_id": user["id"]})
    return {"access_token": token, "token_type": "bearer"}

# Dependency to get current user from token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = SecurityProvider.decode_token(token)
        username = payload.get("sub")
        user_id = payload.get("user_id")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.get_user(username)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return {"id": user_id, "username": username}
    except Exception as e:
        LOG.warning(f"Token decode failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# Example protected endpoint
@app.get("/api/v2/me", tags=["Security"])
async def me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}

# -------------------------
# Performance Schema
# -------------------------
class DeviceMetricsSchema(BaseModel):
    hr: int
    steps: int
    screen_time: float
    sleep_hours: float

# -------------------------
# Performance sync endpoint
# -------------------------
@app.post("/api/v2/performance/sync", tags=["Performance"])
async def sync_metrics(metrics: DeviceMetricsSchema, current_user: dict = Depends(get_current_user)):
    # حساب score بسيط (placeholder)
    score = (metrics.hr/100) + (metrics.steps/10000) + (metrics.sleep_hours/8) - (metrics.screen_time/10)
    job_id = str(uuid.uuid4())
    log_id = db.insert_performance_log(current_user["id"], metrics.dict(), score, job_id)
    db.create_job_record(job_id, current_user["id"], "insight", metrics.dict())
    db.push_job_to_queue("jobs", job_id)
    db.set_redis_job("payload:", job_id, metrics.dict())
    return {"job_id": job_id, "log_id": log_id}
    
# -------------------------
# Run (for direct execution)
# -------------------------
if __name__ == "__main__":
    LOG.info("Starting Human Performance OS (part1)...")
    uvicorn.run("main_fixed_part1:app", host="0.0.0.0", port=8000, reload=True)
