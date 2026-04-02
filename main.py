# main_part3.py
"""
Human Performance OS - main_part3 (robust, full)
- Robust Redis handling with fakeredis + SQLite fallback
- Safe executor loop that works even if Redis is down
- Ensure DB schema includes required columns
- Clearer logging and error handling (prints full traceback on login errors)
- Minimal external requirements for local development
"""

import os
import json
import uuid
import logging
import sqlite3
import time
import threading
import traceback
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# JWT library (pyjwt)
try:
    import jwt
except Exception:
    jwt = None

# Try real redis
try:
    import redis as redis_lib
    REDIS_LIB_AVAILABLE = True
except Exception:
    redis_lib = None
    REDIS_LIB_AVAILABLE = False

# Try fakeredis (development fallback)
try:
    import fakeredis
    FAKEREDIS_AVAILABLE = True
except Exception:
    fakeredis = None
    FAKEREDIS_AVAILABLE = False

# Agents (project-specific; safe fallback if missing)
try:
    from agents import AIClient, run_agents_and_decide
except Exception:
    def run_agents_and_decide(user_id, payload, ai_client=None):
        return {"action": "monitor", "confidence": 0.0, "reason": "agents_unavailable", "agent_reports": []}

    class AIClient:
        def __init__(self, api_key=None):
            self.api_key = api_key

# APScheduler optional
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    APS_AVAILABLE = True
except Exception:
    BackgroundScheduler = None
    APS_AVAILABLE = False

# Config
DB_PATH = os.getenv("DB_PATH", "human_performance_v2.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
TOKEN_EXPIRY_HOURS = int(os.getenv("TOKEN_EXPIRY_HOURS", "24"))
GEMINI_KEY = os.getenv("GEMINI_KEY", "")

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
LOG = logging.getLogger("main_part3")

# OAuth2: tokenUrl must match the login endpoint path
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v2/auth/login")

# -------------------------
# Security Provider
# -------------------------
class SecurityProvider:
    @staticmethod
    def hash_password(password: str) -> str:
        import hashlib
        salt = str(SECRET_KEY or "")
        return hashlib.sha256((password + salt).encode()).hexdigest()

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        try:
            return SecurityProvider.hash_password(plain) == hashed
        except Exception:
            return False

    @staticmethod
    def generate_token(data: dict) -> str:
        if jwt is None:
            raise RuntimeError("pyjwt is not installed")
        payload = data.copy()
        payload.update({"exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)})
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        # pyjwt may return bytes in some versions
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        return token

    @staticmethod
    def decode_token(token: str) -> dict:
        if jwt is None:
            raise RuntimeError("pyjwt is not installed")
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

# -------------------------
# DataBus (SQLite + Redis/fakeredis fallback)
# -------------------------
class DataBus:
    def __init__(self, db_path: str = DB_PATH, redis_url: str = REDIS_URL):
        self.db_path = db_path
        self.redis_url = redis_url
        self.redis = None
        self.redis_available = False

        # Try real redis library and connection
        if REDIS_LIB_AVAILABLE:
            try:
                self.redis = redis_lib.from_url(redis_url, decode_responses=True)
                try:
                    self.redis.ping()
                    self.redis_available = True
                    LOG.info("Connected to real Redis at %s", redis_url)
                except Exception as e:
                    LOG.warning("Real Redis ping failed during init: %s", e)
                    self.redis = None
                    self.redis_available = False
            except Exception as e:
                LOG.warning("Redis initialization failed: %s", e)
                self.redis = None
                self.redis_available = False
        else:
            LOG.info("redis library not installed or unavailable.")

        # If real Redis not available, try fakeredis (development)
        if not self.redis_available and FAKEREDIS_AVAILABLE:
            try:
                self.redis = fakeredis.FakeRedis(decode_responses=True)
                self.redis.ping()
                self.redis_available = True
                LOG.info("Using fakeredis (in-memory) as Redis fallback for development.")
            except Exception as e:
                LOG.warning("fakeredis init failed: %s", e)
                self.redis = None
                self.redis_available = False

        # Ensure SQLite tables exist (including fallback queue)
        self._ensure_tables()

    def _connect(self):
        return sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

    def _ensure_tables(self):
        with self._connect() as conn:
            cur = conn.cursor()
            # users
            cur.execute('''CREATE TABLE IF NOT EXISTS users 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          username TEXT UNIQUE, 
                          password_hash TEXT)''')
            # performance_logs: include hr and heart_rate for compatibility
            cur.execute('''CREATE TABLE IF NOT EXISTS performance_logs 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          user_id INTEGER, 
                          heart_rate INTEGER, 
                          hr INTEGER,
                          steps INTEGER, 
                          screen_time FLOAT, 
                          sleep_hours FLOAT, 
                          performance_score REAL, 
                          ai_recommendation TEXT, 
                          timestamp DATETIME,
                          job_id TEXT,
                          decision_id INTEGER)''')
            # jobs
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
            # decisions
            cur.execute('''CREATE TABLE IF NOT EXISTS decisions (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          job_id TEXT,
                          user_id INTEGER,
                          decision_type TEXT,
                          decision_payload TEXT,
                          reason TEXT,
                          confidence REAL,
                          executor TEXT,
                          created_at DATETIME,
                          outcome_recorded INTEGER DEFAULT 0,
                          outcome_id INTEGER
                        )''')
            # feedbacks
            cur.execute('''CREATE TABLE IF NOT EXISTS feedbacks (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          decision_id INTEGER,
                          user_id INTEGER,
                          feedback_type TEXT,
                          feedback_value TEXT,
                          observed_effect TEXT,
                          created_at DATETIME,
                          FOREIGN KEY(decision_id) REFERENCES decisions(id)
                        )''')
            # behavioral_profiles
            cur.execute('''CREATE TABLE IF NOT EXISTS behavioral_profiles (
                          user_id INTEGER PRIMARY KEY,
                          last_active DATETIME,
                          avg_sleep REAL,
                          avg_steps REAL,
                          focus_drop_after_hours REAL,
                          chronotype TEXT,
                          risk_score REAL,
                          behavior_vector TEXT,
                          updated_at DATETIME
                        )''')
            # fallback queue for executions when Redis is down
            cur.execute('''CREATE TABLE IF NOT EXISTS executions_queue (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          exec_id TEXT,
                          payload TEXT,
                          created_at DATETIME DEFAULT (datetime('now')),
                          processed INTEGER DEFAULT 0
                        )''')
            # notifications table (optional)
            cur.execute('''CREATE TABLE IF NOT EXISTS notifications (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          user_id INTEGER,
                          level TEXT,
                          title TEXT,
                          message TEXT,
                          payload TEXT,
                          channel TEXT,
                          status TEXT DEFAULT 'pending',
                          created_at DATETIME DEFAULT (datetime('now')),
                          sent_at DATETIME
                        )''')
            # indexes
            cur.execute("CREATE INDEX IF NOT EXISTS idx_decisions_user ON decisions(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedbacks(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_perflogs_user_time ON performance_logs(user_id, timestamp)")
            conn.commit()
            LOG.info("Database tables ensured/created at %s.", self.db_path)

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
            hr_val = metrics.get("hr") if metrics.get("hr") is not None else metrics.get("heart_rate")
            cur.execute("""INSERT INTO performance_logs
                           (user_id, heart_rate, hr, steps, screen_time, sleep_hours, performance_score, ai_recommendation, timestamp, job_id)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (user_id, hr_val, hr_val, metrics.get("steps"), metrics.get("screen_time"),
                         metrics.get("sleep_hours"), performance_score, None, datetime.utcnow().isoformat(), job_id))
            conn.commit()
            return cur.lastrowid

    def update_performance_log_ai(self, log_id: int, ai_text: str):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE performance_logs SET ai_recommendation = ? WHERE id = ?", (ai_text, log_id))
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
        if self.redis and self.redis_available:
            try:
                self.redis.lpush(queue_key, job_id)
            except Exception as e:
                LOG.warning("Failed to push job to redis queue: %s", e)

    def set_redis_job(self, prefix: str, job_id: str, payload: dict):
        if self.redis and self.redis_available:
            try:
                self.redis.set(prefix + job_id, json.dumps(payload))
            except Exception:
                pass

    def get_redis_job(self, prefix: str, job_id: str) -> Optional[dict]:
        if not self.redis or not self.redis_available:
            return None
        try:
            raw = self.redis.get(prefix + job_id)
            return json.loads(raw) if raw else None
        except Exception:
            return None

    # Executions queue fallback (SQLite)
    def enqueue_execution_fallback(self, exec_id: str, payload: dict):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO executions_queue (exec_id, payload, processed) VALUES (?, ?, 0)", (exec_id, json.dumps(payload)))
            conn.commit()

    def dequeue_execution_fallback(self) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, exec_id, payload FROM executions_queue WHERE processed=0 ORDER BY id ASC LIMIT 1")
            row = cur.fetchone()
            if not row:
                return None
            row_id, exec_id, payload_text = row
            cur.execute("UPDATE executions_queue SET processed=1 WHERE id=?", (row_id,))
            conn.commit()
            try:
                payload = json.loads(payload_text)
            except Exception:
                payload = {"raw": payload_text}
            payload["exec_id"] = exec_id
            return payload

    # Decisions & Feedback & Profiles
    def insert_decision(self, job_id: str, user_id: int, decision_type: str, decision_payload: dict, reason: str, confidence: float, executor: str = "executive") -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""INSERT INTO decisions (job_id, user_id, decision_type, decision_payload, reason, confidence, executor, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (job_id, user_id, decision_type, json.dumps(decision_payload), reason, confidence, executor, datetime.utcnow().isoformat()))
            conn.commit()
            return cur.lastrowid

    def insert_feedback(self, decision_id: int, user_id: int, feedback_type: str, feedback_value: dict, observed_effect: Optional[dict] = None) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""INSERT INTO feedbacks (decision_id, user_id, feedback_type, feedback_value, observed_effect, created_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (decision_id, user_id, feedback_type, json.dumps(feedback_value), json.dumps(observed_effect) if observed_effect else None, datetime.utcnow().isoformat()))
            conn.commit()
            fid = cur.lastrowid
            cur.execute("UPDATE decisions SET outcome_recorded = 1, outcome_id = ? WHERE id = ?", (fid, decision_id))
            conn.commit()
            return fid

    def fetch_decision(self, decision_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, job_id, user_id, decision_type, decision_payload, reason, confidence, executor, created_at, outcome_recorded, outcome_id FROM decisions WHERE id = ?", (decision_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "job_id": row[1],
                "user_id": row[2],
                "decision_type": row[3],
                "decision_payload": json.loads(row[4]) if row[4] else None,
                "reason": row[5],
                "confidence": row[6],
                "executor": row[7],
                "created_at": row[8],
                "outcome_recorded": bool(row[9]),
                "outcome_id": row[10]
            }

    def upsert_behavioral_profile(self, user_id: int, profile: dict):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""INSERT OR REPLACE INTO behavioral_profiles
                           (user_id, last_active, avg_sleep, avg_steps, focus_drop_after_hours, chronotype, risk_score, behavior_vector, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (user_id, datetime.utcnow().isoformat(), profile.get("avg_sleep"), profile.get("avg_steps"),
                         profile.get("focus_drop_after_hours"), profile.get("chronotype"), profile.get("risk_score"),
                         json.dumps(profile.get("behavior_vector", {})), datetime.utcnow().isoformat()))
            conn.commit()

    def fetch_recent_metrics(self, user_id: int, limit: int = 30):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT steps, sleep_hours, performance_score, timestamp FROM performance_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (user_id, limit))
            return cur.fetchall()

# instantiate DataBus
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
            self.db.upsert_behavioral_profile(user_id, profile)
            return profile

        steps = [r[0] or 0 for r in rows]
        sleep = [r[1] or 0 for r in rows]
        perf = [r[2] or 0 for r in rows]
        avg_steps = sum(steps)/len(steps)
        avg_sleep = sum(sleep)/len(sleep)
        risk = max(0.0, 1.0 - (avg_sleep/8.0) - (avg_steps/10000.0))
        behavior_vector = {"steps_trend": avg_steps, "sleep_trend": avg_sleep, "perf_mean": sum(perf)/len(perf)}
        profile = {"avg_steps": avg_steps, "avg_sleep": avg_sleep, "risk_score": risk, "behavior_vector": behavior_vector}
        self.db.upsert_behavioral_profile(user_id, profile)
        return profile

    def get_profile(self, user_id: int) -> dict:
        with sqlite3.connect(self.db.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT avg_sleep, avg_steps, risk_score, behavior_vector FROM behavioral_profiles WHERE user_id = ?", (user_id,))
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

# -------------------------
# Auth endpoints
# -------------------------
@app.post("/api/v2/auth/register", tags=["Security"])
async def register(user: UserAuthSchema):
    existing = db.get_user(user.username)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    hashed = SecurityProvider.hash_password(user.password)
    try:
        user_id = db.create_user(user.username, hashed)
        LOG.info("Registered user %s id=%s", user.username, user_id)
        return {"status": "success", "user_id": user_id}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="User already exists")
    except Exception as e:
        LOG.error("Register failed: %s", e)
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/api/v2/auth/login", tags=["Security"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        # debug: log incoming username (avoid logging passwords)
        LOG.debug("Login attempt for username: %s", getattr(form_data, "username", "<unknown>"))
        user = db.get_user(form_data.username)
        if not user or not SecurityProvider.verify_password(form_data.password, user["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")
        token = SecurityProvider.generate_token({"sub": user["username"], "user_id": user["id"]})
        return {"access_token": token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        # print full traceback to logs for debugging
        LOG.error("Login endpoint exception: %s", e)
        LOG.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Server error during login")

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
        LOG.warning("Token decode failed: %s", e)
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
        LOG.warning("DB health check failed: %s", e)
    try:
        if db.redis and db.redis_available:
            db.redis.ping()
            redis_ok = True
    except Exception as e:
        LOG.warning("Redis health check failed: %s", e)
    ai_ok = False
    status_str = "ok" if db_ok and (not REDIS_LIB_AVAILABLE or redis_ok) else "degraded"
    return {"status": status_str, "db": db_ok, "redis": redis_ok, "ai": ai_ok, "time": datetime.utcnow().isoformat()}

# Performance sync endpoint (creates log + job)
@app.post("/api/v2/performance/sync", tags=["Performance"])
async def sync_metrics(metrics: DeviceMetricsSchema, current_user: dict = Depends(get_current_user)):
    score = (metrics.hr / 100) + (metrics.steps / 10000) + (metrics.sleep_hours / 8) - (metrics.screen_time / 10)
    job_id = str(uuid.uuid4())
    payload = {"user_id": current_user["id"], **metrics.dict()}
    log_id = db.insert_performance_log(current_user["id"], metrics.dict(), score, job_id)
    db.create_job_record(job_id, current_user["id"], "insight", payload)

    # push to queue (try redis/fakeredis, fallback to sqlite)
    try:
        if db.redis and db.redis_available:
            db.redis.lpush("jobs", job_id)
            db.set_redis_job("payload:", job_id, payload)
            backend = "redis"
        else:
            db.enqueue_execution_fallback(job_id, payload)
            backend = "sqlite"
    except Exception as e:
        LOG.warning("Failed to queue job in redis; used fallback: %s", e)
        try:
            db.enqueue_execution_fallback(job_id, payload)
            backend = "sqlite"
        except Exception:
            LOG.exception("Fallback enqueue failed")
            raise HTTPException(status_code=500, detail="Failed to queue job")
    return {"job_id": job_id, "log_id": log_id, "queued_backend": backend}

# Profile & Decision endpoints
@app.get("/api/v2/profile/{user_id}", tags=["Profile"])
async def get_profile(user_id: int):
    ps = ProfileService(db)
    return ps.get_profile(user_id)

# Decision evaluate endpoint using agents and Gemini
@app.post("/api/v2/decision/evaluate", tags=["Decision"])
async def evaluate_decision(user_id: int, metrics: DeviceMetricsSchema):
    ps = ProfileService(db)
    profile = ps.compute_profile(user_id)
    ai_client = AIClient(api_key=GEMINI_KEY)
    payload = {**metrics.dict(), "profile": profile}
    try:
        decision = run_agents_and_decide(user_id, payload, ai_client=ai_client)
    except Exception as e:
        LOG.exception("run_agents_and_decide failed: %s", e)
        decision = {"action": "monitor", "confidence": 0.0, "reason": "agents_failed", "agent_reports": []}
    job_id = str(uuid.uuid4())
    try:
        did = db.insert_decision(
            job_id=job_id,
            user_id=user_id,
            decision_type=decision.get("action"),
            decision_payload={"agent_reports": decision.get("agent_reports"), "payload": payload},
            reason=decision.get("reason", ""),
            confidence=decision.get("confidence", 0.0),
            executor="evaluate_endpoint"
        )
    except Exception as e:
        LOG.exception("Failed to insert decision: %s", e)
        did = None
    return {"decision": decision, "decision_id": did}

# Feedback & Insight endpoints
@app.post("/api/v2/decision/{decision_id}/feedback", tags=["Decision"])
async def submit_feedback(decision_id: int, payload: dict, current_user: dict = Depends(get_current_user), background_tasks: BackgroundTasks = None):
    if not payload.get("feedback_type"):
        raise HTTPException(status_code=400, detail="feedback_type required")
    fid = db.insert_feedback(decision_id, current_user["id"], payload.get("feedback_type"), payload, payload.get("observed_effect"))
    def recompute_profile(uid: int):
        rows = db.fetch_recent_metrics(uid, limit=30)
        if not rows:
            profile = {"avg_steps":0, "avg_sleep":0, "risk_score":0.0, "behavior_vector":{}}
        else:
            steps = [r[0] or 0 for r in rows]
            sleep = [r[1] or 0 for r in rows]
            perf = [r[2] or 0 for r in rows]
            avg_steps = sum(steps)/len(steps)
            avg_sleep = sum(sleep)/len(sleep)
            risk = max(0.0, 1.0 - (avg_sleep/8.0) - (avg_steps/10000.0))
            behavior_vector = {"steps_trend": avg_steps, "sleep_trend": avg_sleep, "perf_mean": sum(perf)/len(perf)}
            profile = {"avg_steps": avg_steps, "avg_sleep": avg_sleep, "risk_score": risk, "behavior_vector": behavior_vector}
        db.upsert_behavioral_profile(uid, profile)
    try:
        if background_tasks:
            background_tasks.add_task(recompute_profile, current_user["id"])
    except Exception:
        LOG.debug("Background profile recompute scheduling failed")
    return {"status": "ok", "feedback_id": fid}

@app.get("/api/v2/decision/{decision_id}/insight", tags=["Decision"])
async def decision_insight(decision_id: int, current_user: dict = Depends(get_current_user)):
    dec = db.fetch_decision(decision_id)
    if not dec:
        raise HTTPException(status_code=404, detail="Decision not found")
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, feedback_type, feedback_value, observed_effect, created_at FROM feedbacks WHERE decision_id = ?", (decision_id,))
        feedback_rows = cur.fetchall()
    feedbacks = []
    for r in feedback_rows:
        feedbacks.append({
            "id": r[0],
            "feedback_type": r[1],
            "feedback_value": json.loads(r[2]) if r[2] else None,
            "observed_effect": json.loads(r[3]) if r[3] else None,
            "created_at": r[4]
        })
    dec["feedbacks"] = feedbacks
    return dec

# -------------------------
# Scheduler: periodic_check
# -------------------------
if APS_AVAILABLE:
    scheduler = BackgroundScheduler()
    def periodic_check():
        LOG.info("Periodic check started")
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT DISTINCT user_id FROM performance_logs WHERE timestamp > datetime('now','-1 day')")
                users = [r[0] for r in cur.fetchall()]
        except Exception as e:
            LOG.error("Periodic check DB read failed: %s", e)
            users = []

        ai_client = AIClient(api_key=GEMINI_KEY)
        for uid in users:
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT heart_rate, hr, steps, screen_time, sleep_hours, timestamp FROM performance_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (uid,))
                    row = cur.fetchone()
                if not row:
                    continue
                hr_val = row[1] if row[1] is not None else row[0]
                payload = {
                    "hr": hr_val,
                    "steps": row[2],
                    "screen_time": row[3],
                    "sleep_hours": row[4],
                    "timestamp": row[5],
                    "user_id": uid
                }
                decision = run_agents_and_decide(uid, payload, ai_client=ai_client)
                action = decision.get("action")
                confidence = float(decision.get("confidence", 0.0) or 0.0)
                severity_high = any(isinstance(r, dict) and r.get("severity") == "high" for r in decision.get("agent_reports", []) or [])
                if action == "auto_act" and (confidence < 0.9 and not severity_high):
                    LOG.info("Periodic: downgrading auto_act to nudge for user %s (conf=%s)", uid, confidence)
                    action = "nudge"
                    decision["reason"] = (decision.get("reason","") or "") + " (downgraded due to confidence)"
                job_id = str(uuid.uuid4())
                did = db.insert_decision(job_id=job_id, user_id=uid, decision_type=action, decision_payload={"agent_reports": decision.get("agent_reports"), "payload": payload}, reason=decision.get("reason",""), confidence=decision.get("confidence",0.0), executor="scheduler")
                LOG.info("Periodic decision created id=%s for user %s action=%s", did, uid, action)
            except Exception as e:
                LOG.exception("Periodic decision failed for user %s: %s", uid, e)

    try:
        scheduler.add_job(periodic_check, 'interval', minutes=15, id='periodic_check')
        scheduler.start()
        LOG.info("Scheduler started (periodic_check every 15 minutes)")
    except Exception as e:
        LOG.warning("Scheduler failed to start: %s", e)
else:
    LOG.info("APScheduler not available; periodic checks disabled.")

# -------------------------
# Executor loop (background thread) - robust: Redis first, SQLite fallback
# -------------------------
_worker_thread = None
_worker_stop = threading.Event()

def process_execution_item(exec_record: Dict[str, Any]):
    LOG.info("Processing execution: %s", exec_record.get("exec_id"))
    try:
        exec_id = exec_record.get("exec_id") or exec_record.get("job_id")
        if exec_id:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("UPDATE jobs SET status=?, finished_at=? WHERE job_id=?", ("done", datetime.utcnow().isoformat(), exec_id))
                conn.commit()
    except Exception:
        LOG.exception("Failed to mark job done for exec_record")

def process_executions_loop():
    LOG.info("Executor loop started (robust)")
    while not _worker_stop.is_set():
        try:
            item = None
            # Try Redis first if available
            if db.redis and db.redis_available:
                try:
                    raw = db.redis.rpop("executions")
                    if raw:
                        if isinstance(raw, bytes):
                            raw = raw.decode("utf-8")
                        try:
                            item = json.loads(raw)
                        except Exception:
                            item = {"raw": raw}
                except Exception as e:
                    LOG.warning("Redis rpop failed: %s. Disabling redis and falling back to sqlite.", e)
                    try:
                        if hasattr(db.redis, "close"):
                            db.redis.close()
                    except Exception:
                        pass
                    db.redis = None
                    db.redis_available = False

            # If no item from Redis, try SQLite fallback queue
            if item is None:
                item = db.dequeue_execution_fallback()

            if item:
                try:
                    process_execution_item(item)
                except Exception as e:
                    LOG.exception("Error processing item: %s", e)
            else:
                time.sleep(2)
        except Exception as e:
            LOG.exception("Executor loop unexpected error: %s", e)
            time.sleep(5)
    LOG.info("Executor loop stopped.")

def start_executor_background_thread():
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        LOG.info("Executor already running")
        return
    _worker_stop.clear()
    _worker_thread = threading.Thread(target=process_executions_loop, daemon=True)
    _worker_thread.start()
    LOG.info("Executor background thread started")

def stop_executor_background_thread():
    _worker_stop.set()
    if _worker_thread:
        _worker_thread.join(timeout=3.0)
    LOG.info("Executor background thread stopped")

# Start executor thread always (it will use fallback if Redis not available)
start_executor_background_thread()

# -------------------------
# App startup/shutdown events
# -------------------------
@app.on_event("startup")
def on_startup():
    db._ensure_tables()
    # re-check redis availability
    if REDIS_LIB_AVAILABLE and db.redis:
        try:
            db.redis.ping()
            db.redis_available = True
        except Exception:
            db.redis_available = False
    LOG.info("App startup complete. Redis available=%s", getattr(db, "redis_available", False))

@app.on_event("shutdown")
def on_shutdown():
    stop_executor_background_thread()
    try:
        if db.redis and hasattr(db.redis, "close"):
            db.redis.close()
    except Exception:
        pass
    if APS_AVAILABLE:
        try:
            scheduler.shutdown(wait=False)
        except Exception:
            pass
    LOG.info("App shutdown complete.")

# -------------------------
# Run app
# -------------------------
if __name__ == "__main__":
    LOG.info("Starting Human Performance OS v3 (main_part3)...")
    db._ensure_tables()
    if REDIS_LIB_AVAILABLE and db.redis and db.redis_available:
        LOG.info("Redis is available and will be used for queues.")
    elif FAKEREDIS_AVAILABLE and db.redis and db.redis_available:
        LOG.info("fakeredis in use (development).")
    else:
        LOG.info("No Redis available; using SQLite fallback for queues.")
    uvicorn.run("main_part3:app", host="0.0.0.0", port=8000, reload=True)
