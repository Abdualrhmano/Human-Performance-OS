# ============================
# PART A — Libraries + DataBus
# ============================

class Libraries:
    
    import os
    import sys
    import json
    import time
    import uuid
    import logging
    import base64
    import hashlib
    import threading
    import asyncio
    from typing import Optional, Dict, Any, List, Tuple
    from datetime import datetime, timedelta
    import typing
    # HTTP / Async client
    import aiohttp

    # FastAPI و Pydantic
    from fastapi import FastAPI, Depends, HTTPException, Header
    from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    from typing import Dict, Any, Optional

    # ASGI server
    import uvicorn

    # Databases
    import sqlite3

    # Caching / Queue
    import redis

    # Authentication / Security
    import jwt
    from passlib.context import CryptContext
    from cryptography.fernet import Fernet

    # AI client (Gemini) - optional
    try:
        import google.generativeai as genai
        GENAI_AVAILABLE ="AIzaSyCG7WK6t9Fn73Oq2ajJ337KRUrW57X82Ao"
    except Exception:
        GENAI_AVAILABLE = False

    # Logging helper
    LOG = logging.getLogger("human_performance")
    LOG.setLevel(logging.INFO)


# -------------------------------
# DataBus: إدارة DB وعمليات الهجرة
# -------------------------------
class DataBus:
    """
    واجهة بسيطة للتعامل مع SQLite + Redis (اختياري).
    - تتأكد من وجود الجداول المطلوبة
    - توفر دوال لإدراج performance_logs, jobs, decisions, user_profiles
    """
    def __init__(self, db_path: str = "human_performance_v2.db", redis_url: str = "redis://localhost:6379/0"):
        self.db_path = db_path
        self.redis_url = redis_url
        try:
            self.redis = Libraries.redis.from_url(redis_url, decode_responses=True)
        except Exception:
            self.redis = None
            Libraries.LOG.warning("Redis unavailable or not configured; continuing without Redis.")
        self._ensure_tables()

    def _connect(self):
        return Libraries.sqlite3.connect(self.db_path, detect_types=Libraries.sqlite3.PARSE_DECLTYPES | Libraries.sqlite3.PARSE_COLNAMES)

    def _ensure_tables(self):
        """
        ينشئ الجداول الأساسية إن لم تكن موجودة.
        يتعامل مع إضافة أعمدة job_id و decision_id في performance_logs بأمان.
        """
        with self._connect() as conn:
            cur = conn.cursor()
            # users (قد تكون موجودة بالفعل في كودك الأصلي)
            cur.execute('''CREATE TABLE IF NOT EXISTS users 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          username TEXT UNIQUE, 
                          password_hash TEXT)''')
            # performance_logs (مع job_id و decision_id)
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
                          user_id INTEGER,
                          decision_type TEXT,
                          decision_payload TEXT,
                          reason TEXT,
                          outcome TEXT,
                          created_at DATETIME
                        )''')
            # user_profiles
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
            Libraries.LOG.info("Database tables ensured/created.")

    # -------------------------
    # Performance log helpers
    # -------------------------
    def insert_performance_log(self, user_id: int, metrics: dict[str, any], performance_score: float, job_id: str | None) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""INSERT INTO performance_logs
                           (user_id, heart_rate, steps, screen_time, sleep_hours, performance_score, ai_recommendation, timestamp, job_id)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (user_id, metrics.get("hr"), metrics.get("steps"), metrics.get("screen_time"),
                         metrics.get("sleep_hours"), performance_score, None, Libraries.datetime.utcnow().isoformat(), job_id))
            conn.commit()
            log_id = cur.lastrowid
            Libraries.LOG.debug(f"Inserted performance_log id={log_id} for user={user_id}")
            return log_id

    def update_performance_log_ai(self, log_id: int, ai_text: str):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE performance_logs SET ai_recommendation = ? WHERE id = ?", (ai_text, log_id))
            conn.commit()
            Libraries.LOG.debug(f"Updated performance_log id={log_id} with AI text.")

    def link_job_to_log(self, log_id: int, job_id: str):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE performance_logs SET job_id = ? WHERE id = ?", (job_id, log_id))
            conn.commit()
            Libraries.LOG.debug(f"Linked job {job_id} to log {log_id}.")

    # -------------------------
    # Jobs management
    # -------------------------
    def create_job_record(self, job_id: str, user_id: int, job_type: str, payload: dict[str, any]) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""INSERT INTO jobs (job_id, user_id, type, payload, status, created_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (job_id, user_id, job_type, Libraries.json.dumps(payload), "queued", Libraries.datetime.utcnow().isoformat()))
            conn.commit()
            jid = cur.lastrowid
            Libraries.LOG.debug(f"Created job record {job_id} (db id {jid})")
            return jid

    def update_job_record(self, job_id: str, status: str, result: dict[str, any] | None: 
):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE jobs SET status = ?, result = ?, finished_at = ? WHERE job_id = ?", (status, Libraries.json.dumps(result) if result is not None else None, Libraries.datetime.utcnow().isoformat(), job_id))
            conn.commit()
            Libraries.LOG.debug(f"Updated job {job_id} -> {status}")

    def push_job_to_queue(self, queue_key: str, job_id: str):
        if self.redis:
            try:
                self.redis.lpush(queue_key, job_id)
                Libraries.LOG.debug(f"Pushed job {job_id} to queue {queue_key}")
            except Exception as e:
                Libraries.LOG.warning(f"Failed to push job to redis queue: {e}")

    def set_redis_job(self, prefix: str, job_id: str, payload: dict[str, any]):
        if self.redis:
            try:
                self.redis.set(prefix + job_id, Libraries.json.dumps(payload))
            except Exception:
                pass

    def get_redis_job(self, prefix: str, job_id: str) -> dict[str, any] | None :

        if not self.redis:
            return None
        raw = self.redis.get(prefix + job_id)
        return Libraries.json.loads(raw) if raw else None

    # -------------------------
    # Decision helpers
    # -------------------------
    def insert_decision(self, user_id: int, decision_type: str, decision_payload: dict[str, any], reason: str) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""INSERT INTO decisions (user_id, decision_type, decision_payload, reason, created_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (user_id, decision_type, Libraries.json.dumps(decision_payload), reason, Libraries.datetime.utcnow().isoformat()))
            conn.commit()
            did = cur.lastrowid
            Libraries.LOG.debug(f"Inserted decision id={did} for user={user_id}")
            return did

    # -------------------------
    # Profile helpers
    # -------------------------
    def upsert_user_profile(self, user_id: int, profile: dict[str, any]):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""INSERT OR REPLACE INTO user_profiles
                           (user_id, last_active, avg_sleep, avg_steps, risk_score, behavior_vector, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (user_id, Libraries.datetime.utcnow().isoformat(), profile.get("avg_sleep"), profile.get("avg_steps"),
                         profile.get("risk_score"), Libraries.json.dumps(profile.get("behavior_vector", {})), Libraries.datetime.utcnow().isoformat()))
            conn.commit()
            Libraries.LOG.debug(f"Upserted profile for user {user_id}")

    def fetch_recent_metrics(self, user_id: int, limit: int = 30):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT steps, sleep_hours, performance_score, timestamp FROM performance_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (user_id, limit))
            return cur.fetchall()

# ============================
# End of PART A
# ============================
