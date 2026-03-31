# modular_backend.py
# ======================================================
# Human Performance OS v2.0 - Modular Classes File
# All required imports are executed inside the first class (Libraries)
# Each subsystem is implemented as a separate class below
# Use this file to replace/extend your existing backend modules
# ======================================================

class Libraries:
    """
    جميع المكتبات المطلوبة مُجمعة هنا.
    تنفيذ الاستيرادات داخل جسم الكلاس يضمن أن الاستيراد يحدث عند تعريف الكلاس.
    (ملاحظة: هذا نمط غير شائع لكنه يطابق طلبك بوضع المكتبات في أول كلاس)
    """
    import os
    import json
    import time
    import uuid
    import jwt
    import base64
    import sqlite3
    import hashlib
    import threading
    import redis
    import uvicorn
    try:
        import google.generativeai as genai
        GENAI_AVAILABLE = True
    except Exception:
        GENAI_AVAILABLE = False
    from datetime import datetime, timedelta
    from typing import Optional, Dict, Any, Tuple, List
    from passlib.context import CryptContext
    from cryptography.fernet import Fernet
    from pydantic import BaseModel, Field
    from fastapi import FastAPI, Depends, Header, HTTPException
    from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
    from fastapi.middleware.cors import CORSMiddleware

# -------------------------------
# System configuration and keys
# -------------------------------
class SystemConfig:
    from Libraries import datetime, base64, Fernet
    OS_NAME = "Human Performance OS v2.0"
    GEMINI_API_KEY = Libraries.os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_KEY")
    SECRET_KEY = Libraries.os.getenv("SECRET_KEY", "super-secret-key").encode() if isinstance(Libraries.os.getenv("SECRET_KEY", None), str) else Libraries.b"1Xt5YfM4ZNuFdwp3OfVkwkhhQLagWKtt"
    ALGORITHM = "HS256"
    TOKEN_EXPIRY_HOURS = 24

    # Fernet key derivation (ensure 32 bytes)
    _padded_key = SECRET_KEY.ljust(32)[:32]
    FERNET_KEY = base64.urlsafe_b64encode(_padded_key)
    cipher_suite = Fernet(FERNET_KEY)

# -------------------------------
# Security provider (hashing, tokens)
# -------------------------------
class SecurityProvider:
    from Libraries import hashlib, jwt, datetime, timedelta
    @staticmethod
    def hash_password(password: str) -> str:
        salt = str(SystemConfig.SECRET_KEY)
        db_password = password + salt
        return SecurityProvider.hashlib.sha256(db_password.encode()).hexdigest()

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        return SecurityProvider.hash_password(plain) == hashed

    @staticmethod
    def generate_token(data: Dict[str, Any]) -> str:
        payload = data.copy()
        payload.update({"exp": SecurityProvider.datetime.utcnow() + SecurityProvider.timedelta(hours=SystemConfig.TOKEN_EXPIRY_HOURS)})
        return SecurityProvider.jwt.encode(payload, SystemConfig.SECRET_KEY, algorithm=SystemConfig.ALGORITHM)

# -------------------------------
# Data schemas (Pydantic)
# -------------------------------
class Schemas:
    from Libraries import BaseModel, Field
    class UserAuthSchema(BaseModel):
        username: str
        password: str

    class DeviceMetricsSchema(BaseModel):
        heart_rate: int = Field(..., example=75)
        steps: int = Field(..., example=8000)
        screen_time: float = Field(..., example=3.2)
        sleep_hours: float = Field(..., example=7.5)

# -------------------------------
# DatabaseManager (SQLite simple)
# -------------------------------
class DatabaseManager:
    from Libraries import sqlite3, datetime
    def __init__(self, db_name: str = "human_performance_v2.db"):
        self.db_name = db_name
        self._create_tables()

    def _connect(self):
        return DatabaseManager.sqlite3.connect(self.db_name, detect_types=DatabaseManager.sqlite3.PARSE_DECLTYPES | DatabaseManager.sqlite3.PARSE_COLNAMES)

    def _create_tables(self):
        with self._connect() as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS users 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          username TEXT UNIQUE, 
                          password_hash TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS performance_logs 
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
            c.execute('''CREATE TABLE IF NOT EXISTS jobs (
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
            c.execute('''CREATE TABLE IF NOT EXISTS decisions (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          user_id INTEGER,
                          decision_type TEXT,
                          decision_payload TEXT,
                          reason TEXT,
                          outcome TEXT,
                          created_at DATETIME
                        )''')
            c.execute('''CREATE TABLE IF NOT EXISTS user_profiles (
                          user_id INTEGER PRIMARY KEY,
                          last_active DATETIME,
                          avg_sleep FLOAT,
                          avg_steps FLOAT,
                          risk_score FLOAT,
                          behavior_vector TEXT,
                          updated_at DATETIME
                        )''')
            conn.commit()

    # CRUD helpers
    def insert_user(self, username: str, password_hash: str) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
            conn.commit()
            return cur.lastrowid

    def get_user_by_username(self, username: str):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
            return cur.fetchone()

    def insert_performance_log(self, user_id: int, metrics: Dict[str, Any], performance_score: float, job_id: Optional[str] = None) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""INSERT INTO performance_logs
                           (user_id, heart_rate, steps, screen_time, sleep_hours, performance_score, ai_recommendation, timestamp, job_id)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (user_id, metrics.get("hr"), metrics.get("steps"), metrics.get("screen_time"),
                         metrics.get("sleep_hours"), performance_score, None, DatabaseManager.datetime.utcnow(), job_id))
            conn.commit()
            return cur.lastrowid

    def update_performance_log_ai(self, log_id: int, ai_text: str):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE performance_logs SET ai_recommendation = ? WHERE id = ?", (ai_text, log_id))
            conn.commit()

    def create_job(self, job_id: str, user_id: int, job_type: str, payload: Dict[str, Any]):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""INSERT INTO jobs (job_id, user_id, type, payload, status, created_at)
                           VALUES (?, ?, ?, ?, ?, ?)""", (job_id, user_id, job_type, json.dumps(payload), "queued", DatabaseManager.datetime.utcnow()))
            conn.commit()
            return cur.lastrowid

    def update_job(self, job_id: str, status: str, result: Optional[Dict[str, Any]] = None):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE jobs SET status = ?, result = ?, finished_at = ? WHERE job_id = ?", (status, json.dumps(result) if result else None, DatabaseManager.datetime.utcnow(), job_id))
            conn.commit()

    def insert_decision(self, user_id: int, decision_type: str, decision_payload: Dict[str, Any], reason: str) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""INSERT INTO decisions (user_id, decision_type, decision_payload, reason, created_at)
                           VALUES (?, ?, ?, ?, ?)""", (user_id, decision_type, json.dumps(decision_payload), reason, DatabaseManager.datetime.utcnow()))
            conn.commit()
            return cur.lastrowid

    def upsert_user_profile(self, user_id: int, profile: Dict[str, Any]):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""INSERT OR REPLACE INTO user_profiles
                           (user_id, last_active, avg_sleep, avg_steps, risk_score, behavior_vector, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (user_id, DatabaseManager.datetime.utcnow(), profile.get("avg_sleep"), profile.get("avg_steps"),
                         profile.get("risk_score"), json.dumps(profile.get("behavior_vector", {})), DatabaseManager.datetime.utcnow()))
            conn.commit()

# -------------------------------
# Neural processing (score calculation)
# -------------------------------
class NeuralProcessor:
    @staticmethod
    def calculate_score(m: Schemas.DeviceMetricsSchema) -> float:
        step_score = min((m.steps / 10000) * 40, 40)
        sleep_score = min((m.sleep_hours / 8) * 30, 30)
        hr_score = 30 if 60 <= m.heart_rate <= 100 else 15
        screen_penalty = max(0, (m.screen_time - 4) * 5)
        final = (step_score + sleep_score + hr_score) - screen_penalty
        return round(max(0, min(final, 100)), 2)

# -------------------------------
# LunaNeuralBrain (AI wrapper)
# -------------------------------
class LunaNeuralBrain:
    from Libraries import genai
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or SystemConfig.GEMINI_API_KEY
        if Libraries.GENAI_AVAILABLE and self.api_key:
            LunaNeuralBrain.genai.configure(api_key=self.api_key)
        self.model_name = 'gemini-1.5-flash'

    def build_prompt(self, metrics: Dict[str, Any], history: str) -> str:
        return f"بصفتك العقل المدبر لنظام {SystemConfig.OS_NAME}. البيانات: {metrics}. التاريخ: {history}. قدم نصيحة Biohacking في جملتين بالعربية الفصحى."

    def generate_direct(self, metrics: Dict[str, Any], history: str, timeout: int = 15) -> Tuple[str, Optional[str]]:
        if not Libraries.GENAI_AVAILABLE or not self.api_key:
            return "error", "AI backend unavailable"
        prompt = self.build_prompt(metrics, history)
        try:
            model = LunaNeuralBrain.genai.GenerativeModel(self.model_name)
            resp = model.generate_content(prompt, timeout=timeout)
            return "done", resp.text.strip()
        except Exception as e:
            return "error", str(e)

# -------------------------------
# PerformanceAdvisor (uses LunaNeuralBrain)
# -------------------------------
class PerformanceAdvisor:
    def __init__(self, brain: LunaNeuralBrain):
        self.brain = brain

    def get_verdict_direct(self, metrics: Dict[str, Any], history: str) -> str:
        status, result = self.brain.generate_direct(metrics, history)
        if status == "done":
            return result
        return "نظام LUNA: حافظ على استقرار نشاطك الحيوي حالياً."

# -------------------------------
# SentimentAnalyzer (heuristics + optional AI)
# -------------------------------
class SentimentAnalyzer:
    from Libraries import hashlib
    def __init__(self, mode: str = "fast", api_key: Optional[str] = None, redis_client: Optional["Libraries.redis.Redis"] = None):
        self.mode = mode
        self.api_key = api_key or SystemConfig.GEMINI_API_KEY
        self.redis = redis_client or Libraries.redis.from_url(Libraries.os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
        if self.mode == "ai" and Libraries.GENAI_AVAILABLE and self.api_key:
            LunaNeuralBrain.genai.configure(api_key=self.api_key)

    def _hash(self, text: str) -> str:
        return SentimentAnalyzer.hashlib.sha256(text.encode()).hexdigest()

    def analyze_fast(self, text: str) -> Dict[str, Any]:
        txt = text.lower()
        score = 0.0
        positives = ["جيد", "ممتاز", "سعيد", "مرتاح", "تحسن", "نجاح", "great", "good", "happy"]
        negatives = ["حزين", "متعب", "سيء", "قليل", "خائف", "قلق", "bad", "tired", "angry"]
        for p in positives:
            if p in txt:
                score += 1.0
        for n in negatives:
            if n in txt:
                score -= 1.0
        norm = max(1, len(txt.split()))
        sentiment_score = max(-1.0, min(1.0, score / norm))
        tone = "neutral"
        if sentiment_score > 0.1:
            tone = "positive"
        elif sentiment_score < -0.1:
            tone = "negative"
        return {"score": round(sentiment_score, 3), "tone": tone, "method": "fast"}

    def analyze_ai(self, text: str, timeout: int = 10) -> Dict[str, Any]:
        if not Libraries.GENAI_AVAILABLE:
            return {"error": "genai_unavailable", "method": "ai"}
        prompt = f"حدد نبرة النص التالي بالعربية: \"{text}\". أعطِ نتيجة بصيغة JSON: {{'tone':'positive|neutral|negative','score':-1..1,'notes':'...' }}."
        try:
            model = LunaNeuralBrain.genai.GenerativeModel('gemini-1.5-flash')
            resp = model.generate_content(prompt, timeout=timeout)
            raw = resp.text.strip()
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                j = Libraries.json.loads(raw[start:end+1])
                j["method"] = "ai"
                return j
            return {"raw": raw, "method": "ai"}
        except Exception as e:
            return {"error": str(e), "method": "ai"}

    def analyze(self, text: str) -> Dict[str, Any]:
        key = "sentiment:" + self._hash(text)
        cached = self.redis.get(key)
        if cached:
            return Libraries.json.loads(cached)
        if self.mode == "ai":
            res = self.analyze_ai(text)
        else:
            res = self.analyze_fast(text)
        try:
            self.redis.setex(key, int(Libraries.os.getenv("LUNA_CACHE_TTL", "3600")), Libraries.json.dumps(res))
        except Exception:
            pass
        return res

# -------------------------------
# AgentProxy (enqueue, caching, key rotation)
# -------------------------------
class AgentProxy:
    from Libraries import time
    def __init__(self, databus: DatabaseManager, redis_client: Optional["Libraries.redis.Redis"] = None, gemini_keys: str = ""):
        self.databus = databus
        self.redis = redis_client or Libraries.redis.from_url(Libraries.os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
        self.gemini_keys = [k.strip() for k in gemini_keys.split(",") if k.strip()]
        self.key_count = len(self.gemini_keys)

    def _pick_api_key(self) -> Optional[str]:
        if not self.key_count:
            return None
        idx = int(self.redis.incr("gemini:key:counter") or 0) % self.key_count
        return self.gemini_keys[idx]

    def _cache_lookup(self, prompt: str) -> Optional[str]:
        key = "luna:cache:" + Libraries.hashlib.sha256(prompt.encode()).hexdigest()
        return self.redis.get(key)

    def _cache_store(self, prompt: str, result: str, ttl: int = 3600):
        try:
            self.redis.setex("luna:cache:" + Libraries.hashlib.sha256(prompt.encode()).hexdigest(), ttl, result)
        except Exception:
            pass

    def enqueue_insight(self, user_id: int, metrics: Dict[str, Any], history: str, log_id: Optional[int] = None) -> str:
        prompt = f"User:{user_id} Metrics:{metrics} History:{history}"
        cached = self._cache_lookup(prompt)
        if cached:
            job_id = f"cached-{Libraries.hashlib.sha256(prompt.encode()).hexdigest()[:8]}"
            payload = {"job_id": job_id, "user_id": user_id, "metrics": metrics, "history": history, "result": cached, "status": "done", "created_at": Libraries.datetime.utcnow().isoformat(), "_log_id": log_id}
            self.databus.create_job(job_id, user_id, "insight_cached", payload)
            self.redis.set("luna:job:" + job_id, Libraries.json.dumps(payload))
            return job_id

        job_id = f"luna-{user_id}-{int(AgentProxy.time.time())}-{Libraries.hashlib.sha256(prompt.encode()).hexdigest()[:8]}"
        payload = {"job_id": job_id, "user_id": user_id, "metrics": metrics, "history": history, "prompt": prompt, "status": "queued", "created_at": Libraries.datetime.utcnow().isoformat(), "_log_id": log_id}
        self.databus.create_job(job_id, user_id, "insight", payload)
        self.redis.set("luna:job:" + job_id, Libraries.json.dumps(payload))
        self.redis.lpush("luna:queue", job_id)
        return job_id

    def process_direct(self, user_id: int, metrics: Dict[str, Any], history: str, timeout: int = 15) -> Tuple[str, Optional[str]]:
        prompt = f"بصفتك العقل المدبر لنظام {SystemConfig.OS_NAME}. البيانات: {metrics}. التاريخ: {history}. قدم نصيحة Biohacking في جملتين بالعربية الفصحى."
        cached = self._cache_lookup(prompt)
        if cached:
            return "cached", cached
        api_key = self._pick_api_key()
        if not api_key or not Libraries.GENAI_AVAILABLE:
            return "error", "AI backend unavailable"
        try:
            LunaNeuralBrain.genai.configure(api_key=api_key)
            model = LunaNeuralBrain.genai.GenerativeModel('gemini-1.5-flash')
            resp = model.generate_content(prompt, timeout=timeout)
            result = resp.text.strip()
            self._cache_store(prompt, result)
            return "done", result
        except Exception as e:
            return "error", str(e)

# -------------------------------
# SimpleWorker (example local worker)
# -------------------------------
class SimpleWorker:
    from Libraries import time
    def __init__(self, databus: DatabaseManager, agent_proxy: AgentProxy, poll_interval: float = 1.0):
        self.databus = databus
        self.agent = agent_proxy
        self.poll_interval = poll_interval
        self._running = False

    def _process_job(self, job_id: str):
        raw = self.databus.redis.get("luna:job:" + job_id)
        if not raw:
            return
        job = Libraries.json.loads(raw)
        self.databus.update_job(job_id, "processing", None)
        status, result = self.agent.process_direct(job["user_id"], job["metrics"], job["history"])
        if status == "done":
            if job.get("_log_id"):
                try:
                    self.databus.update_performance_log_ai(job["_log_id"], result)
                except Exception:
                    pass
            self.databus.update_job(job_id, "done", {"result": result})
            job["status"] = "done"
            job["result"] = result
            job["finished_at"] = Libraries.datetime.utcnow().isoformat()
            self.databus.redis.set("luna:job:" + job_id, Libraries.json.dumps(job))
        elif status == "cached":
            self.databus.update_job(job_id, "done", {"result": result})
            job["status"] = "done"
            job["result"] = result
            job["finished_at"] = Libraries.datetime.utcnow().isoformat()
            self.databus.redis.set("luna:job:" + job_id, Libraries.json.dumps(job))
        else:
            self.databus.update_job(job_id, "failed", {"error": result})
            job["status"] = "failed"
            job["error"] = result
            job["finished_at"] = Libraries.datetime.utcnow().isoformat()
            self.databus.redis.set("luna:job:" + job_id, Libraries.json.dumps(job))

    def start(self):
        self._running = True
        while self._running:
            job_id = self.databus.redis.rpop("luna:queue")
            if job_id:
                try:
                    self._process_job(job_id)
                except Exception:
                    pass
            else:
                SimpleWorker.time.sleep(self.poll_interval)

    def stop(self):
        self._running = False

# -------------------------------
# FastAPI integration helper (light wrapper)
# -------------------------------
class BackendAPI:
    from Libraries import FastAPI, CORSMiddleware, OAuth2PasswordBearer
    def __init__(self, db_manager: DatabaseManager, agent_proxy: AgentProxy, sentiment: SentimentAnalyzer):
        self.app = BackendAPI.FastAPI(title=SystemConfig.OS_NAME, version="2.0.0")
        self.app.add_middleware(BackendAPI.CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
        self.oauth2_scheme = BackendAPI.OAuth2PasswordBearer(tokenUrl="api/v2/auth/login")
        self.db = db_manager
        self.agent = agent_proxy
        self.sentiment = sentiment
        # mount endpoints
        self._mount_endpoints()

    def _mount_endpoints(self):
        from fastapi import Depends, HTTPException
        import jwt as _jwt

        @self.app.post("/api/v2/auth/register", tags=["Security"])
        async def register(user: Schemas.UserAuthSchema):
            try:
                hashed = SecurityProvider.hash_password(user.password)
                self.db.insert_user(user.username, hashed)
                return {"status": "success", "message": "Enrolled in OS v2.0"}
            except Exception:
                raise HTTPException(status_code=400, detail="User already exists or error")

        @self.app.post("/api/v2/auth/login", tags=["Security"])
        async def login(form_data: BackendAPI.OAuth2PasswordRequestForm = Depends()):
            rec = self.db.get_user_by_username(form_data.username)
            if not rec or not SecurityProvider.verify_password(form_data.password, rec[2]):
                raise HTTPException(status_code=401, detail="Invalid Credentials")
            token = SecurityProvider.generate_token({"sub": form_data.username, "user_id": rec[0]})
            return {"access_token": token, "token_type": "bearer"}

        @self.app.post("/api/v2/performance/sync", tags=["Neural Sync"])
        async def sync_and_analyze(data: Schemas.DeviceMetricsSchema, token: str = Depends(self.oauth2_scheme)):
            try:
                payload = Libraries.jwt.decode(token, SystemConfig.SECRET_KEY, algorithms=[SystemConfig.ALGORITHM])
                user_id = payload.get("user_id")
            except Exception:
                raise HTTPException(status_code=403, detail="Invalid or Expired Session")

            performance_score = NeuralProcessor.calculate_score(data)
            current_metrics = {"hr": data.heart_rate, "steps": data.steps, "sleep_hours": data.sleep_hours, "screen_time": data.screen_time, "score": performance_score}
            log_id = self.db.insert_performance_log(user_id, current_metrics, performance_score, job_id=None)

            # build history
            with self.db._connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT performance_score, timestamp FROM performance_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 3", (user_id,))
                rows = cur.fetchall()
                history = "no history" if not rows else " ; ".join([f"score {r[0]} at {r[1]}" for r in rows])

            job_id = self.agent.enqueue_insight(user_id=user_id, metrics=current_metrics, history=history, log_id=log_id)
            try:
                self.db.link_job_to_log(log_id, job_id)
            except Exception:
                pass

            return {"status": "accepted", "performance_score": performance_score, "job_id": job_id, "log_id": log_id}

        @self.app.get("/api/v2/jobs/{job_id}", tags=["Neural Jobs"])
        async def get_job_status(job_id: str, token: str = Depends(self.oauth2_scheme)):
            try:
                _ = Libraries.jwt.decode(token, SystemConfig.SECRET_KEY, algorithms=[SystemConfig.ALGORITHM])
            except Exception:
                raise HTTPException(status_code=403, detail="Invalid or Expired Session")

            raw = self.db._connect()
            job = self.db.redis.get("luna:job:" + job_id)
            if job:
                return {"job": Libraries.json.loads(job)}
            else:
                with self.db._connect() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT job_id, status, result, created_at, started_at, finished_at FROM jobs WHERE job_id = ?", (job_id,))
                    row = cur.fetchone()
                    if not row:
                        raise HTTPException(status_code=404, detail="Job not found")
                    return {"job": {"job_id": row[0], "status": row[1], "result": Libraries.json.loads(row[2]) if row[2] else None, "created_at": row[3], "started_at": row[4], "finished_at": row[5]}}

        @self.app.post("/api/v2/sentiment/analyze", tags=["Sentiment"])
        async def analyze_text(payload: Libraries.BaseModel = None, token: str = Depends(self.oauth2_scheme)):
            # expecting {"text": "..."}
            try:
                _ = Libraries.jwt.decode(token, SystemConfig.SECRET_KEY, algorithms=[SystemConfig.ALGORITHM])
            except Exception:
                raise HTTPException(status_code=403, detail="Invalid or Expired Session")
            text = payload.text if hasattr(payload, "text") else ""
            res = self.sentiment.analyze(text)
            return {"sentiment": res}

# End of modular_backend.py
