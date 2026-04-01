# luna_worker_part3.py (enhanced)
import os
import json
import time
import logging
import sqlite3
import uuid
from datetime import datetime
from typing import Tuple, Optional, Dict, Any

# Optional Redis
try:
    import redis
    REDIS_AVAILABLE = True
except Exception:
    redis = None
    REDIS_AVAILABLE = False

# Agents and AI client
from agents import AIClient, run_agents_and_decide

# DataBus import (adjust path if DataBus is in a different module)
# Ensure main_part3.DataBus is importable without circular imports
from main_part3 import DataBus

# Logging
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("luna_worker")
LOG.setLevel(logging.INFO)

DB_PATH = os.getenv("DB_PATH", "human_performance_v2.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
GEMINI_KEY = os.getenv("GEMINI_KEY", "")

class AgentWorker:
    def __init__(self, db_path: str = DB_PATH, redis_url: str = REDIS_URL, gemini_key: str = GEMINI_KEY):
        # Initialize DataBus and Redis client (if available)
        self.db = DataBus(db_path=db_path, redis_url=redis_url)
        self.redis = self.db.redis
        self.ai_client = AIClient(api_key=gemini_key)
        LOG.info("AgentWorker initialized. Redis available: %s", bool(self.redis))

    # -------------------------
    # Job retrieval helpers
    # -------------------------
    def _pop_job_from_redis(self, queue_key: str = "jobs") -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        try:
            if not self.redis:
                return None, None
            job_id = self.redis.rpop(queue_key)
            if not job_id:
                return None, None
            raw = self.redis.get("payload:" + job_id)
            payload = json.loads(raw) if raw else {}
            return job_id, payload
        except Exception as e:
            LOG.warning("Redis pop error: %s", e)
            return None, None

    def _poll_job_from_db(self) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT job_id, payload FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1")
                row = cur.fetchone()
                if not row:
                    return None, None
                job_id, raw_payload = row
                payload = json.loads(raw_payload) if raw_payload else {}
                # mark started
                cur.execute("UPDATE jobs SET status=?, started_at=? WHERE job_id=?", ("processing", datetime.utcnow().isoformat(), job_id))
                conn.commit()
                return job_id, payload
        except Exception as e:
            LOG.error("DB poll error: %s", e)
            return None, None

    # -------------------------
    # DB update helpers
    # -------------------------
    def _update_job_and_log(self, job_id: str, result: Dict[str, Any], ai_text: Optional[str] = None):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("UPDATE jobs SET status=?, result=?, finished_at=? WHERE job_id=?",
                            ("done", json.dumps(result) if result is not None else None, datetime.utcnow().isoformat(), job_id))
                if ai_text is not None:
                    cur.execute("UPDATE performance_logs SET ai_recommendation=? WHERE job_id=?", (ai_text, job_id))
                conn.commit()
        except Exception as e:
            LOG.error("Failed to update job/log: %s", e)

    def _link_decision_to_log(self, decision_id: int, job_id: str):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("UPDATE performance_logs SET decision_id = ? WHERE job_id = ?", (decision_id, job_id))
                conn.commit()
        except Exception as e:
            LOG.error("Failed to link decision to log: %s", e)

    # -------------------------
    # Execution placeholder
    # -------------------------
    def _execute_action(self, user_id: int, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Placeholder for executing actions (notifications, schedule changes, device commands).
        Keep this minimal and safe. In production, delegate to a dedicated executor service.
        Returns an execution record dict.
        """
        LOG.info("Executing action for user %s: %s (payload summary)", user_id, action)
        # Example: push to Redis execution queue for another service to pick up
        exec_record = {
            "exec_id": str(uuid.uuid4()),
            "user_id": user_id,
            "action": action,
            "payload_summary": {k: payload.get(k) for k in ("hr","steps","sleep_hours","screen_time") if k in payload},
            "created_at": datetime.utcnow().isoformat()
        }
        try:
            if self.redis:
                # push to an 'executions' list for an executor service
                self.redis.lpush("executions", json.dumps(exec_record))
            # also persist in jobs table as an execution job (optional)
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""INSERT INTO jobs (job_id, user_id, type, payload, status, created_at)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (exec_record["exec_id"], user_id, "execution", json.dumps(exec_record), "queued", datetime.utcnow().isoformat()))
                conn.commit()
        except Exception as e:
            LOG.warning("Failed to enqueue execution: %s", e)
        return exec_record

    # -------------------------
    # Simple profile recompute (local)
    # -------------------------
    def _compute_profile_and_upsert(self, user_id: int) -> Dict[str, Any]:
        """
        Lightweight profile computation: averages over recent performance_logs.
        Upserts into behavioral_profiles via DataBus.upsert_behavioral_profile if available.
        """
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT steps, sleep_hours, performance_score FROM performance_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 30", (user_id,))
                rows = cur.fetchall()
            if not rows:
                profile = {"avg_steps": 0, "avg_sleep": 0, "risk_score": 0.0, "behavior_vector": {}}
            else:
                steps = [r[0] or 0 for r in rows]
                sleep = [r[1] or 0 for r in rows]
                perf = [r[2] or 0 for r in rows]
                avg_steps = sum(steps) / len(steps)
                avg_sleep = sum(sleep) / len(sleep)
                risk = max(0.0, 1.0 - (avg_sleep / 8.0) - (avg_steps / 10000.0))
                behavior_vector = {"steps_trend": avg_steps, "sleep_trend": avg_sleep, "perf_mean": sum(perf) / len(perf)}
                profile = {"avg_steps": avg_steps, "avg_sleep": avg_sleep, "risk_score": risk, "behavior_vector": behavior_vector}
            # upsert via DataBus if available
            try:
                self.db.upsert_behavioral_profile(user_id, profile)
            except Exception:
                LOG.debug("DataBus.upsert_behavioral_profile not available or failed; skipping upsert")
            return profile
        except Exception as e:
            LOG.error("Profile computation failed for user %s: %s", user_id, e)
            return {"avg_steps": 0, "avg_sleep": 0, "risk_score": 0.0, "behavior_vector": {}}

    # -------------------------
    # Main job processing
    # -------------------------
    def process_job(self, job_id: str, payload: Dict[str, Any]):
        LOG.info("Processing job %s payload keys=%s", job_id, list(payload.keys()))
        # 1) AI recommendation (fallback)
        try:
            ai_result = self.ai_client.call(f"Recommend action for payload: {json.dumps(payload)}")
            ai_text = ai_result.get("raw") if isinstance(ai_result, dict) else str(ai_result)
        except Exception as e:
            LOG.warning("AI processing failed: %s", e)
            ai_result = {"fallback": True}
            ai_text = None

        # 2) Update job and performance log with AI result
        self._update_job_and_log(job_id, ai_result, ai_text)

        # 3) Run agents and get decision
        user_id = payload.get("user_id")
        if not user_id:
            LOG.warning("No user_id in payload for job %s; skipping decision", job_id)
            return

        try:
            decision = run_agents_and_decide(user_id, payload, ai_client=self.ai_client)
        except Exception as e:
            LOG.error("Agents decision failed: %s", e)
            decision = {"action": "monitor", "confidence": 0.0, "reason": "agents_failed", "agent_reports": []}

        # 4) Safety policy: downgrade auto_act if confidence low unless severity high
        action = decision.get("action")
        confidence = float(decision.get("confidence", 0.0) or 0.0)
        severity_high = any(isinstance(r, dict) and r.get("severity") == "high" for r in decision.get("agent_reports", []) or [])
        if action == "auto_act" and (confidence < 0.9 and not severity_high):
            LOG.info("Downgrading auto_act to nudge due to low confidence (%s) for job %s", confidence, job_id)
            action = "nudge"
            decision["reason"] = (decision.get("reason", "") or "") + " (downgraded due to confidence)"

        # 5) Insert decision into DB via DataBus
        try:
            decision_payload = {
                "agent_reports": decision.get("agent_reports"),
                "payload": payload,
                "ai_result": ai_result
            }
            decision_id = self.db.insert_decision(
                job_id=job_id,
                user_id=user_id,
                decision_type=action,
                decision_payload=decision_payload,
                reason=decision.get("reason", ""),
                confidence=confidence,
                executor="executive_worker"
            )
            LOG.info("Inserted decision id=%s for job %s action=%s", decision_id, job_id, action)
        except Exception as e:
            LOG.error("Failed to insert decision: %s", e)
            decision_id = None

        # 6) Link decision to performance log
        if decision_id:
            try:
                self._link_decision_to_log(decision_id, job_id)
            except Exception:
                LOG.debug("Link decision to log failed")

        # 7) Update behavioral profile (lightweight) so future decisions use fresh profile
        try:
            profile = self._compute_profile_and_upsert(user_id)
            LOG.debug("Profile updated for user %s: %s", user_id, profile)
        except Exception:
            LOG.debug("Profile update skipped/failed")

        # 8) Optionally execute action (safe gating)
        if action == "auto_act":
            # Only execute if high confidence or severity_high
            if confidence >= 0.95 or severity_high:
                exec_record = self._execute_action(user_id, action, payload)
                LOG.info("Auto action executed (enqueued) exec_id=%s for decision_id=%s", exec_record.get("exec_id"), decision_id)
            else:
                LOG.info("Auto action not executed due to safety gating (confidence=%s, severity_high=%s)", confidence, severity_high)

        # done
        return

    # -------------------------
    # Worker loop
    # -------------------------
    def run(self):
        LOG.info("AgentWorker started loop")
        while True:
            job_id, payload = self._pop_job_from_redis()
            if not job_id:
                job_id, payload = self._poll_job_from_db()
            if not job_id:
                time.sleep(2)
                continue
            try:
                self.process_job(job_id, payload or {})
            except Exception as e:
                LOG.exception("Error processing job %s: %s", job_id, e)

def run_worker():
    worker = AgentWorker()
    worker.run()

if __name__ == "__main__":
    LOG.info("Starting Agent Worker v3 (enhanced)...")
    run_worker()
