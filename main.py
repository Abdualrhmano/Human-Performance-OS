# main.py - Production-Ready Human Performance OS Decision Engine
from fastapi import FastAPI, Depends, Request, HTTPException, Header
from pydantic import BaseModel
import uvicorn
import os
import base64
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# 1. Security Configuration
# تم تصحيح علامة التنصيص الزائدة هنا لضمان عمل المفتاح
SECRET_KEY = os.getenv("SECRET_KEY", b"1Xt5YfM4ZNuFdwp3OfVkwkhhQLagWKtt") 
API_KEYS = {"demo-key": "user1"}

# 2. Database Setup (حفظ البيانات)
def init_db():
    conn = sqlite3.connect('performance.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS performance_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  user_id TEXT,
                  score REAL,
                  recommendation TEXT,
                  encrypted_data TEXT)''')
    conn.commit()
    conn.close()

init_db()

# 3. Rate Limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/hour"])
app = FastAPI(title="Human Performance OS Decision Engine")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 4. Pydantic Schema
class UserMetrics(BaseModel):
    sleep_hours: float
    focus_hours: float
    energy_level: float
    habit_consistency: float

# 5. API Key Dependency
async def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return API_KEYS[x_api_key]

# 6. Encryption Logic
def encrypt_data(data: Dict[str, Any]) -> str:
    aesgcm = AESGCM(SECRET_KEY)
    nonce = os.urandom(12)
    data_bytes = json.dumps(data).encode()
    ciphertext = aesgcm.encrypt(nonce, data_bytes, None)
    return base64.b64encode(nonce + ciphertext).decode()

# 7. Scoring & Recommendation Logic
def calculate_performance_score(metrics: UserMetrics) -> float:
    focus = max(0, min(10, metrics.focus_hours))
    energy = max(0, min(10, metrics.energy_level))
    consistency = max(0, min(1, metrics.habit_consistency))
    score = (focus * 0.4) + (energy * 0.3) + (consistency * 3.0) 
    return round(score, 2)

def generate_recommendation(score: float) -> str:
    if score >= 8.0: return "Excellent performance! Maintain current habits."
    elif score >= 6.0: return "Good performance. Focus on sleep consistency."
    elif score >= 4.0: return "Moderate performance. Prioritize 7h+ sleep."
    else: return "Low performance. Start with 1h focused work daily."

# 8. Endpoints
@app.post("/evaluate")
@limiter.limit("10/minute")
async def evaluate_performance(
    metrics: UserMetrics,
    user_id: str = Depends(verify_api_key),
    request: Request = None
):
    score = calculate_performance_score(metrics)
    recommendation = generate_recommendation(score)
    encrypted_metrics = encrypt_data(metrics.dict())
    current_time = datetime.now().isoformat()

    # حفظ في قاعدة البيانات
    conn = sqlite3.connect('performance.db')
    c = conn.cursor()
    c.execute("INSERT INTO performance_logs (timestamp, user_id, score, recommendation, encrypted_data) VALUES (?,?,?,?,?)",
              (current_time, user_id, score, recommendation, encrypted_metrics))
    conn.commit()
    conn.close()

    return {
        "user_id": user_id,
        "performance_score": score,
        "recommendation": recommendation,
        "encrypted_data": encrypted_metrics,
        "timestamp": current_time,
        "db_status": "Saved"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

