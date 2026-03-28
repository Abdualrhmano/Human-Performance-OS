# main.py - AI-Powered Human Performance OS
from fastapi import FastAPI, Depends, Request, HTTPException, Header
from pydantic import BaseModel
import uvicorn
import os
import base64
import json
import sqlite3
import google.generativeai as genai
from datetime import datetime
from typing import Dict, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# 1. إعدادات الأمان والذكاء الاصطناعي
# ضع مفتاحك هنا مكان النص بالأسفل
GEMINI_API_KEY = "AIzaSyCG7WK6t9Fn73Oq2ajJ337KRUrW57X82Ao" 
SECRET_KEY = b"1Xt5YfM4ZNuFdwp3OfVkwkhhQLagWKtt"
API_KEYS = {"demo-key": "user1"}

# تهيئة موديل Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI(title="LUNA AI Core")

# 2. قاعدة البيانات
def init_db():
    conn = sqlite3.connect('performance.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS performance_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT, user_id TEXT, score REAL,
                  recommendation TEXT, encrypted_data TEXT)''')
    conn.commit()
    conn.close()

init_db()

class UserMetrics(BaseModel):
    sleep_hours: float
    focus_hours: float
    energy_level: float
    habit_consistency: float

# 3. محرك تحليل الذكاء الاصطناعي (AI Analysis Engine)
def get_ai_insight(metrics: UserMetrics, score: float):
    prompt = f"""
    You are LUNA, an AI Performance Coach. Analyze these metrics:
    Sleep: {metrics.sleep_hours}h, Focus: {metrics.focus_hours}h, 
    Energy: {metrics.energy_level}/10, Consistency: {metrics.habit_consistency*100}%.
    System Score: {score}/10.
    
    Provide a professional, 2-sentence biohacking recommendation in Arabic. 
    Focus on neuro-efficiency and recovery.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "أداء مستقر. ركز على شرب الماء وتنظيم فترات الراحة لزيادة الإنتاجية."

# 4. التشفير
def encrypt_data(data: Dict[str, Any]) -> str:
    aesgcm = AESGCM(SECRET_KEY)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, json.dumps(data).encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()

# 5. Endpoint الأساسي
@app.post("/evaluate")
async def evaluate_performance(metrics: UserMetrics, x_api_key: str = Header(None)):
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid Key")
    
    # حساب السكور المبدئي
    score = round((metrics.focus_hours * 0.4) + (metrics.energy_level * 0.3) + (metrics.habit_consistency * 3.0), 2)
    
    # طلب تحليل الذكاء الاصطناعي من Gemini
    recommendation = get_ai_insight(metrics, score)
    
    # تشفير البيانات وحفظها
    encrypted_metrics = encrypt_data(metrics.dict())
    current_time = datetime.now().isoformat()
    
    conn = sqlite3.connect('performance.db')
    c = conn.cursor()
    c.execute("INSERT INTO performance_logs (timestamp, user_id, score, recommendation, encrypted_data) VALUES (?,?,?,?,?)",
              (current_time, API_KEYS[x_api_key], score, recommendation, encrypted_metrics))
    conn.commit()
    conn.close()

    return {
        "performance_score": score,
        "recommendation": recommendation,
        "encrypted_data": encrypted_metrics,
        "timestamp": current_time
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
