import os, json, time, logging, sqlite3
from datetime import datetime

# Redis optional
try:
    import redis
    REDIS_AVAILABLE = True
except Exception:
    redis = None
    REDIS_AVAILABLE = False

# Logging
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("luna_worker")

# Config
DB_PATH = os.getenv("DB_PATH", "human_performance_v2.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# -------------------------
# AgentProxy skeleton
# -------------------------
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
        # Placeholder AI logic (replace with Gemini or ML model)
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

# -------------------------
# Worker loop
# -------------------------
def run_worker():
    proxy = AgentProxy()
    while True:
        job_id = None
        payload = None

        # Try to get job from Redis queue
        if proxy.redis:
            job_id = proxy.redis.rpop("jobs")
            if job_id:
                raw = proxy.redis.get("payload:" + job_id)
                payload = json.loads(raw) if raw else {}

        # If no Redis, poll DB for queued jobs
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

        LOG.info(f"Processing job {job_id} with payload={payload}")
        result = proxy.process_direct(payload)
        proxy._cache_store(job_id, result)

        # Update DB
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE jobs SET status=?, result=?, finished_at=? WHERE job_id=?",
                        ("done", json.dumps(result), datetime.utcnow().isoformat(), job_id))
            cur.execute("UPDATE performance_logs SET ai_recommendation=? WHERE job_id=?",
                        (result["ai_recommendation"], job_id))
            conn.commit()
        LOG.info(f"Job {job_id} completed with result={result}")

if __name__ == "__main__":
    LOG.info("Starting LUNA Worker...")
    run_worker()
