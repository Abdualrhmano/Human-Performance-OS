# luna_worker_part3.py
import os
import json
import time
import logging
import sqlite3
from datetime import datetime

# Optional Redis
try:
    import redis
    REDIS_AVAILABLE = True
except Exception:
    redis = None
    REDIS_AVAILABLE = False

# Logging
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("luna_worker")

DB_PATH = os.getenv("DB_PATH", "human_performance_v2.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Lightweight copies of DecisionEngine and ProfileService (to avoid circular imports)
class DecisionEngineLocal:
    def __init__(self, db_path):
        self.db_path = db_path
        self.weights = {"hr": -0.3, "steps": 0.4, "sleep_hours": 0.5, "screen_time": -0.2}
        self.policy_stats = {}

    def _context_hash(self, profile: dict, metrics: dict) -> str:
        return f"{profile.get('avg_steps',0)}|{profile.get('avg_sleep',0)}"

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

class ProfileServiceLocal:
    def __init__(self, db_path):
        self.db_path = db_path

    def compute_profile(self, user_id: int) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT steps, sleep_hours, performance_score FROM performance_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 30", (user_id,))
            rows = cur.fetchall()
        if not rows:
            profile = {"avg_steps":0, "avg_sleep":0, "risk_score":0.0, "behavior_vector":{}}
            return profile
        steps = [r[0] or 0 for r in rows]
        sleep = [r[1] or 0 for r in rows]
        perf = [r[2] or 0 for r in rows]
        avg_steps = sum(steps)/len(steps)
        avg_sleep = sum(sleep)/len(sleep)
        risk = max(0.0, 1.0 - (avg_sleep/8.0) - (avg_steps/10000.0))
        behavior_vector = {"steps_trend": avg_steps, "sleep_trend": avg_sleep, "perf_mean": sum(perf)/len(perf)}
        profile = {"avg_steps": avg_steps, "avg_sleep": avg_sleep, "risk_score": risk, "behavior_vector": behavior_vector}
        return profile

# AgentProxy (simple)
class AgentProxy:
    def __init__(self):
        self.redis = None
        if REDIS_AVAILABLE:
            try:
                self.redis = redis.from_url(REDIS_URL, decode_responses=True)
                LOG.info("Connected to Redis.")
            except Exception as e:
                LOG.warning(f"Redis connect fail: {e}")
        self.cache = {}

    def _cache_lookup(self, job_id):
        if self.redis:
            raw = self.redis.get("result:" + job_id)
            return json.loads(raw) if raw else None
        return self.cache.get(job_id)

    def _cache_store(self, job_id, result):
        if self.redis:
            self.redis.set("result:" + job_id, json.dumps(result))
        else:
            self.cache[job_id] = result

    def process_direct(self, payload: dict) -> dict:
        hr = payload.get("hr", 0)
        steps = payload.get("steps", 0)
        sleep = payload.get("sleep_hours", 0)
        screen = payload.get("screen_time", 0)
        if hr > 100:
            rec = "Reduce stress and rest more."
        elif sleep < 6:
            rec = "Improve sleep routine."
        elif steps < 5000:
            rec = "Increase daily activity."
        else:
            rec = "Keep up the good work!"
        return {"ai_recommendation": rec}

# Worker loop
def run_worker():
    proxy = AgentProxy()
    de = DecisionEngineLocal(DB_PATH)
    ps = ProfileServiceLocal(DB_PATH)

    while True:
        job_id = None
        payload = None

        if proxy.redis:
            job_id = proxy.redis.rpop("jobs")
            if job_id:
                raw = proxy.redis.get("payload:" + job_id)
                payload = json.loads(raw) if raw else {}

        if not job_id:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT job_id, payload FROM jobs WHERE status='queued' LIMIT 1")
                row = cur.fetchone()
                if row:
                    job_id, raw_payload = row
                    payload = json.loads(raw_payload)

        if not job_id:
            time.sleep(2)
            continue

        LOG.info(f"Processing job {job_id} payload={payload}")
        result = proxy.process_direct(payload or {})
        proxy._cache_store(job_id, result)

        # Update job and performance log with AI result
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE jobs SET status=?, result=?, finished_at=? WHERE job_id=?",
                        ("done", json.dumps(result), datetime.utcnow().isoformat(), job_id))
            cur.execute("UPDATE performance_logs SET ai_recommendation=? WHERE job_id=?",
                        (result.get("ai_recommendation"), job_id))
            conn.commit()

        # Decision making
        user_id = (payload or {}).get("user_id")
        if user_id:
            profile = ps.compute_profile(user_id)
            decision = de.evaluate_context(user_id, profile, payload or {})
            # insert decision record
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""INSERT INTO decisions (user_id, decision_type, decision_payload, reason, created_at)
                               VALUES (?, ?, ?, ?, ?)""",
                            (user_id, decision["action"], json.dumps(payload or {}), decision["reason"], datetime.utcnow().isoformat()))
                conn.commit()
                decision_id = cur.lastrowid
                # link decision to performance_log
                cur.execute("UPDATE performance_logs SET decision_id = ? WHERE job_id = ?", (decision_id, job_id))
                conn.commit()
            LOG.info(f"Decision recorded id={decision_id} action={decision['action']} reason={decision['reason']}")

        LOG.info(f"Job {job_id} completed with result={result}")

if __name__ == "__main__":
    LOG.info("Starting LUNA Worker v3...")
    run_worker()
