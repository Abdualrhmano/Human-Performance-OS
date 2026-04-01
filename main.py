
import os
import json
import uuid
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import uuid
from fastapi import Depends
# Optional Redis
try:
    import redis
    REDIS_AVAILABLE = True
except Exception:
    redis = None
    REDIS_AVAILABLE = False

# Config
DB_PATH = os.getenv("DB_PATH", "human_performance_v2.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
TOKEN_EXPIRY_HOURS = int(os.getenv("TOKEN_EXPIRY_HOURS", "24"))

# Logging
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("human_performance")

# -------------------------
# Simple Security Provider
# -------------------------
class SecurityProvider:
    @staticmethod
    def hash_password(password: str) -> str:
        import hashlib
        salt = str(SECRET_KEY)
        return hashlib.sha256((password + salt).encode()).hexdigest()

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        return SecurityProvider.hash_password(plain) == hashed

    @staticmethod
    def generate_token(data: dict) -> str:
        import jwt
        payload = data.copy()
        payload.update({"exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)})
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> dict:
        
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
            LOG.info("Redis not available; running without Redis.")
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

    # Users
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

    # Performance logs
    def insert_performance_log(self, user_id: int, metrics: dict, performance_score: float, job_id: Optional[str]) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""INSERT INTO performance_logs
                           (user_id, heart_rate, steps, screen_time, sleep_hours, performance_score, ai_recommendation, timestamp, job_id)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (user_id, metrics.get("hr"), metrics.get("steps"), metrics.get("screen_time"),
                         metrics.get("sleep_hours"), performance_score, None, datetime.utcnow().isoformat(), job_id))
            conn.commit()
            return cur.lastrowid

    def update_performance_log_ai(self, log_id: int, ai_text: str):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE performance_logs SET ai_recommendation = ? WHERE id = ?", (ai_text, log_id))
            conn.commit()

    def link_job_to_log(self, log_id: int, job_id: str):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE performance_logs SET job_id = ? WHERE id = ?", (job_id, log_id))
            conn.commit()

    # Jobs
    def create_job_record(self, job_id: str, user_id: int, job_type: str, payload: dict) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""INSERT INTO jobs (job_id, user_id, type, payload, status, created_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (job_id, user_id, job_type, json.dumps(payload), "queued", datetime.utcnow().isoformat()))
            conn.commit()
            return cur.lastrowid

    def update_job_record(self, job_id: str, status: str, result: Optional[dict]):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE jobs SET status = ?, result = ?, finished_at = ? WHERE job_id = ?",
                        (status, json.dumps(result) if result is not None else None, datetime.utcnow().isoformat(), job_id))
            conn.commit()

    def push_job_to_queue(self, queue_key: str, job_id: str):
        if self.redis:
            try:
                self.redis.lpush(queue_key, job_id)
            except Exception as e:
                LOG.warning(f"Failed to push job to redis queue: {e}")

    def set_redis_job(self, prefix: str, job_id: str, payload: dict):
        if self.redis:
            try:
                self.redis.set(prefix + job_id, json.dumps(payload))
            except Exception:
                pass

    def get_redis_job(self, prefix: str, job_id: str) -> Optional[dict]:
        if not self.redis:
            return None
        raw = self.redis.get(prefix + job_id)
        return json.loads(raw) if raw else None

    # Decisions
    def insert_decision(self, user_id: int, decision_type: str, decision_payload: dict, reason: str) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""INSERT INTO decisions (user_id, decision_type, decision_payload, reason, created_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (user_id, decision_type, json.dumps(decision_payload), reason, datetime.utcnow().isoformat()))
            conn.commit()
            return cur.lastrowid

    def fetch_recent_metrics(self, user_id: int, limit: int = 30):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT steps, sleep_hours, performance_score, timestamp FROM performance_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (user_id, limit))
            return cur.fetchall()

    def upsert_user_profile(self, user_id: int, profile: dict):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""INSERT OR REPLACE INTO user_profiles
                           (user_id, last_active, avg_sleep, avg_steps, risk_score, behavior_vector, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (user_id, datetime.utcnow().isoformat(), profile.get("avg_sleep"), profile.get("avg_steps"),
                         profile.get("risk_score"), json.dumps(profile.get("behavior_vector", {})), datetime.utcnow().isoformat()))
            conn.commit()

db = DataBus()

# -------------------------
# Decision Engine (MVP)
# -------------------------
class DecisionEngine:
    def __init__(self, db: DataBus):
        self.db = db
        self.weights = {"hr": -0.3, "steps": 0.4, "sleep_hours": 0.5, "screen_time": -0.2}
        self.policy_stats = {}

    def _context_hash(self, profile: dict, metrics: dict) -> str:
        key = f"{profile.get('avg_steps',0)}|{profile.get('avg_sleep',0)}"
        return key

    def evaluate_context(self, user_id: int, profile: dict, metrics: dict) -> dict:
        if metrics.get("hr",0) > 120:
            return {"action":"auto_act", "confidence":0.95, "reason":"High heart rate detected"}
        if metrics.get("sleep_hours",0) < 4:
            return {"action":"nudge", "confidence":0.8, "reason":"Very low sleep"}

        score = (metrics.get("steps",0)/10000)*self.weights["steps"] + \
                (metrics.get("sleep_hours",0)/8)*self.weights["sleep_hours"] + \
                (metrics.get("screen_time",0)/10)*self.weights["screen_time"] + \
                (metrics.get("hr",0)/100)*self.weights["hr"]

        if score < -0.5:
            action = "auto_act"
            conf = min(0.9, 0.6 + abs(score)/2)
        elif score < 0.0:
            action = "nudge"
            conf = 0.6
        else:
            action = "monitor"
            conf = 0.5

        # epsilon-greedy stub
        import random
        epsilon = 0.1
        ctx = self._context_hash(profile, metrics)
        stats = self.policy_stats.get(ctx, {})
        if random.random() < epsilon and stats:
            action = random.choice(["auto_act","nudge","monitor"])
            conf = 0.4

        return {"action": action, "confidence": round(conf,2), "reason": f"heuristic_score={round(score,3)}"}

    def record_outcome(self, decision_id: int, reward: float):
        with sqlite3.connect(self.db.db_path) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE decisions SET outcome = ? WHERE id = ?", (str(reward), decision_id))
            conn.commit()

# -------------------------
# Profile Service
# -------------------------
class ProfileService:
    def __init__(self, db: DataBus):
        self.db = db

    def compute_profile(self, user_id: int) -> dict:
        rows = self.db.fetch_recent_metrics(user_id, limit=30)
        if not rows:
            profile = {"avg_steps":0, "avg_sleep":0, "risk_score":0.0, "behavior_vector":{}}
            self.db.upsert_user_profile(user_id, profile)
            return profile

        steps = [r[0] or 0 for r in rows]
        sleep = [r[1] or 0 for r in rows]
        perf = [r[2] or 0 for r in rows]
        avg_steps = sum(steps)/len(steps)
        avg_sleep = sum(sleep)/len(sleep)
        risk = max(0.0, 1.0 - (avg_sleep/8.0) - (avg_steps/10000.0))
        behavior_vector = {"steps_trend": avg_steps, "sleep_trend": avg_sleep, "perf_mean": sum(perf)/len(perf)}
        profile = {"avg_steps": avg_steps, "avg_sleep": avg_sleep, "risk_score": risk, "behavior_vector": behavior_vector}
        self.db.upsert_user_profile(user_id, profile)
        return profile

    def get_profile(self, user_id: int) -> dict:
        with sqlite3.connect(self.db.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT avg_sleep, avg_steps, risk_score, behavior_vector FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if not row:
                return self.compute_profile(user_id)
            return {"avg_sleep": row[0], "avg_steps": row[1], "risk_score": row[2], "behavior_vector": json.loads(row[3] or "{}")}

# -------------------------
# Pydantic Schemas & App
# -------------------------
class UserAuthSchema(BaseModel):
    username: str
    password: str

class DeviceMetricsSchema(BaseModel):
    hr: int
    steps: int
    screen_time: float
    sleep_hours: float

app = FastAPI(title="Human Performance OS v3 - DecisionEngine", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Auth endpoints (register/login) - same as before
@app.post("/api/v2/auth/register", tags=["Security"])
async def register(user: UserAuthSchema):
    existing = db.get_user(user.username)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    hashed = SecurityProvider.hash_password(user.password)
    try:
        user_id = db.create_user(user.username, hashed)
        LOG.info(f"Registered user {user.username} id={user_id}")
        return {"status": "success", "user_id": user_id}
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

# Root & health
@app.get("/", tags=["default"])
async def root():
    return {"message": "Human Performance OS is Running", "status": "Online"}

@app.get("/api/v2/health", tags=["System"])
async def health():
    db_ok = False
    redis_ok = False
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("SELECT 1")
        db_ok = True
    except Exception as e:
        LOG.warning(f"DB health check failed: {e}")
    try:
        if db.redis:
            db.redis.ping()
            redis_ok = True
    except Exception as e:
        LOG.warning(f"Redis health check failed: {e}")
    ai_ok = False
    status = "ok" if db_ok and (not REDIS_AVAILABLE or redis_ok) else "degraded"
    return {"status": status, "db": db_ok, "redis": redis_ok, "ai": ai_ok, "time": datetime.utcnow().isoformat()}

# Performance sync endpoint (creates log + job)
@app.post("/api/v2/performance/sync", tags=["Performance"])
async def sync_metrics(metrics: DeviceMetricsSchema, current_user: dict = Depends(get_current_user)):
    score = (metrics.hr / 100) + (metrics.steps / 10000) + (metrics.sleep_hours / 8) - (metrics.screen_time / 10)
    job_id = str(uuid.uuid4())
    payload = {"user_id": current_user["id"], **metrics.dict()}
    log_id = db.insert_performance_log(current_user["id"], metrics.dict(), score, job_id)
    db.create_job_record(job_id, current_user["id"], "insight", payload)
    db.push_job_to_queue("jobs", job_id)
    db.set_redis_job("payload:", job_id, payload)
    return {"job_id": job_id, "log_id": log_id}

# Profile & Decision endpoints
@app.get("/api/v2/profile/{user_id}", tags=["Profile"])
async def get_profile(user_id: int):
    ps = ProfileService(db)
    return ps.get_profile(user_id)

@app.post("/api/v2/decision/evaluate", tags=["Decision"])
async def evaluate_decision(user_id: int, metrics: DeviceMetricsSchema):
    ps = ProfileService(db)
    profile = ps.compute_profile(user_id)
    de = DecisionEngine(db)
    decision = de.evaluate_context(user_id, profile, metrics.dict())
    did = db.insert_decision(user_id, decision["action"], metrics.dict(), decision["reason"])
    return {"decision": decision, "decision_id": did}

if __name__ == "__main__":
    LOG.info("Starting Human Performance OS v3...")
    uvicorn.run("main_part3:app", host="0.0.0.0", port=8000, reload=True)
