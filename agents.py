# agents.py
import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List

# Optional AI client import (Gemini)
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except Exception:
    genai = None
    GENAI_AVAILABLE = False

LOG = logging.getLogger("agents")
LOG.setLevel(logging.INFO)

# Configuration via env
GEMINI_KEY = os.getenv("GEMINI_KEY", "")
AI_TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "6"))

# -------------------------
# AI Client wrapper
# -------------------------
class AIClient:
    """
    Lightweight wrapper for calling Gemini or falling back to local heuristics.
    Methods:
      - call(prompt, system_prompt=None) -> dict
    """
    def __init__(self, api_key: str = GEMINI_KEY):
        self.available = GENAI_AVAILABLE and bool(api_key)
        if self.available:
            try:
                genai.configure(api_key=api_key)
                LOG.info("AIClient: Gemini configured")
            except Exception as e:
                LOG.warning(f"AIClient: Gemini configure failed: {e}")
                self.available = False
        else:
            LOG.info("AIClient: Gemini not available, using fallback")

    def call(self, prompt: str, system_prompt: Optional[str] = None, timeout: int = AI_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """
        Returns parsed JSON-like dict if possible. If AI not available or fails, returns fallback dict.
        """
        if self.available:
            try:
                # Minimal safe call pattern; adapt to your genai client usage
                response = genai.generate_text(prompt= (system_prompt or "") + "\n" + prompt)
                text = getattr(response, "text", None) or str(response)
                # try parse JSON
                try:
                    return json.loads(text)
                except Exception:
                    return {"raw": text}
            except Exception as e:
                LOG.warning(f"AIClient call failed: {e}")
                return {"error": "ai_call_failed", "message": str(e)}
        # Fallback deterministic stub
        return {"fallback": True, "raw": prompt[:512]}

# -------------------------
# Explainability helpers
# -------------------------
def explain_simple(reason: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"reason": reason, "details": details or {}}

def safe_json(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)

# -------------------------
# Base Agent
# -------------------------
class BaseAgent:
    def __init__(self, name: str, ai_client: Optional[AIClient] = None):
        self.name = name
        self.ai = ai_client or AIClient()
        self.version = "0.1"

    def analyze(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze payload and return a dict with keys:
          - assessment
          - action
          - severity (low|medium|high) optional
          - explain
        """
        raise NotImplementedError

# -------------------------
# Health Agent
# -------------------------
class HealthAgent(BaseAgent):
    SYSTEM_PROMPT = """
You are Health Agent. Input: JSON with hr, sleep_hours, steps, screen_time, timestamp.
Return JSON: {"assessment":"...","action":"...","severity":"low|medium|high","explain":"..."}
"""

    def analyze(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Try AI first for richer explanation
        try:
            prompt = f"Analyze health metrics: {json.dumps(payload)}"
            ai_out = self.ai.call(prompt, system_prompt=self.SYSTEM_PROMPT)
            if ai_out and ("assessment" in ai_out or "raw" in ai_out):
                # Normalize AI output if possible
                if "assessment" in ai_out:
                    return {
                        "agent": self.name,
                        "assessment": ai_out.get("assessment"),
                        "action": ai_out.get("action"),
                        "severity": ai_out.get("severity", "low"),
                        "explain": ai_out.get("explain") or ai_out.get("raw"),
                        "meta": {"source": "ai"}
                    }
        except Exception as e:
            LOG.debug(f"HealthAgent AI error: {e}")

        # Fallback heuristics
        hr = payload.get("hr", 0) or 0
        sleep = payload.get("sleep_hours", 0) or 0
        steps = payload.get("steps", 0) or 0
        screen = payload.get("screen_time", 0) or 0

        if hr > 120:
            return {
                "agent": self.name,
                "assessment": "tachycardia",
                "action": "recommend_rest",
                "severity": "high",
                "explain": explain_simple("HR above 120", {"hr": hr}),
                "meta": {"source": "heuristic"}
            }
        if sleep < 5:
            return {
                "agent": self.name,
                "assessment": "sleep_deprived",
                "action": "recommend_sleep_hygiene",
                "severity": "medium",
                "explain": explain_simple("Sleep less than 5 hours", {"sleep_hours": sleep}),
                "meta": {"source": "heuristic"}
            }
        if steps < 3000:
            return {
                "agent": self.name,
                "assessment": "low_activity",
                "action": "recommend_walk",
                "severity": "low",
                "explain": explain_simple("Steps below 3000", {"steps": steps}),
                "meta": {"source": "heuristic"}
            }
        return {
            "agent": self.name,
            "assessment": "ok",
            "action": "maintain",
            "severity": "low",
            "explain": explain_simple("Vitals within normal ranges", {"hr": hr, "sleep": sleep, "steps": steps}),
            "meta": {"source": "heuristic"}
        }

# -------------------------
# Productivity Agent
# -------------------------
class ProductivityAgent(BaseAgent):
    SYSTEM_PROMPT = """
You are Productivity Agent. Input: JSON with focus_blocks, interruptions, tasks_completed, session_length_hours.
Return JSON: {"assessment":"...","action":"...","impact_estimate":0.0,"explain":"..."}
"""

    def analyze(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            prompt = f"Analyze productivity metrics: {json.dumps(payload)}"
            ai_out = self.ai.call(prompt, system_prompt=self.SYSTEM_PROMPT)
            if ai_out and ("assessment" in ai_out or "raw" in ai_out):
                if "assessment" in ai_out:
                    return {
                        "agent": self.name,
                        "assessment": ai_out.get("assessment"),
                        "action": ai_out.get("action"),
                        "impact_estimate": ai_out.get("impact_estimate", 0.0),
                        "explain": ai_out.get("explain") or ai_out.get("raw"),
                        "meta": {"source": "ai"}
                    }
        except Exception as e:
            LOG.debug(f"ProductivityAgent AI error: {e}")

        # Heuristic fallback
        interruptions = payload.get("interruptions", 0) or 0
        focus_blocks = payload.get("focus_blocks", 0) or 0
        tasks = payload.get("tasks_completed", 0) or 0
        session_len = payload.get("session_length_hours", 0) or 0

        if interruptions > 5:
            return {
                "agent": self.name,
                "assessment": "high_interruptions",
                "action": "reduce_notifications",
                "impact_estimate": 0.2,
                "explain": explain_simple("Many interruptions detected", {"interruptions": interruptions}),
                "meta": {"source": "heuristic"}
            }
        if focus_blocks >= 3 and session_len > 6:
            return {
                "agent": self.name,
                "assessment": "focus_drop_risk",
                "action": "suggest_break",
                "impact_estimate": 0.15,
                "explain": explain_simple("Long session with multiple focus blocks", {"session_length_hours": session_len}),
                "meta": {"source": "heuristic"}
            }
        return {
            "agent": self.name,
            "assessment": "ok",
            "action": "maintain",
            "impact_estimate": 0.05,
            "explain": explain_simple("Productivity within expected range", {"tasks_completed": tasks}),
            "meta": {"source": "heuristic"}
        }

# -------------------------
# Executive Agent Orchestrator
# -------------------------
class ExecutiveAgent:
    """
    Collects reports from specialized agents and decides final action.
    Decision output:
      - action: auto_act | nudge | monitor
      - confidence: 0.0-1.0
      - reason: text
      - agent_reports: list
    """
    def __init__(self, safety_rules: Optional[Dict[str, Any]] = None):
        self.safety_rules = safety_rules or {}
        self.version = "0.2"

    def decide(self, user_id: int, agent_reports: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        # 1. Safety overrides
        for r in agent_reports:
            sev = r.get("severity")
            if sev == "high":
                return {
                    "action": "auto_act",
                    "confidence": 0.95,
                    "reason": f"High severity reported by {r.get('agent')}",
                    "agent_reports": agent_reports
                }

        # 2. Aggregate heuristic scoring
        score = 0.0
        weight_map = {"HealthAgent": 0.5, "ProductivityAgent": 0.5}
        for r in agent_reports:
            agent_name = r.get("agent", "")
            w = weight_map.get(agent_name, 0.3)
            # severity mapping
            sev = r.get("severity")
            sev_val = {"low": 0.0, "medium": 0.5, "high": 1.0}.get(sev, 0.0)
            # impact or confidence proxy
            impact = r.get("impact_estimate", 0.0) or 0.0
            score += w * (sev_val + impact)

        # Normalize and map to action
        if score >= 0.6:
            action = "auto_act"
            confidence = min(0.95, 0.6 + score * 0.4)
        elif score >= 0.25:
            action = "nudge"
            confidence = 0.6
        else:
            action = "monitor"
            confidence = 0.4

        reason = f"aggregated_score={round(score,3)}"
        return {
            "action": action,
            "confidence": round(confidence, 2),
            "reason": reason,
            "agent_reports": agent_reports
        }

# -------------------------
# Example integration helper
# -------------------------
def run_agents_and_decide(user_id: int, payload: Dict[str, Any], ai_client: Optional[AIClient] = None) -> Dict[str, Any]:
    """
    Convenience function to run HealthAgent and ProductivityAgent then ExecutiveAgent.
    Returns decision dict.
    """
    ai = ai_client or AIClient()
    health = HealthAgent("HealthAgent", ai)
    prod = ProductivityAgent("ProductivityAgent", ai)
    exec_agent = ExecutiveAgent()

    # Build agent payloads
    health_report = health.analyze(payload)
    prod_report = prod.analyze(payload)
    decision = exec_agent.decide(user_id, [health_report, prod_report], context={"timestamp": datetime.utcnow().isoformat()})
    # Ensure JSON safe
    decision["agent_reports"] = [safe_json(r) for r in decision.get("agent_reports", [])]
    return decision

# -------------------------
# Simple unit test snippet
# -------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    sample_payload = {
        "hr": 110,
        "sleep_hours": 4.5,
        "steps": 2000,
        "screen_time": 6.0,
        "focus_blocks": 2,
        "interruptions": 6,
        "tasks_completed": 3,
        "session_length_hours": 7
    }
    LOG.info("Running local agents test")
    dec = run_agents_and_decide(user_id=1, payload=sample_payload)
    print(json.dumps(dec, indent=2, ensure_ascii=False))
