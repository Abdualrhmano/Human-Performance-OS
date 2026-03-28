from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
import uvicorn
import sqlite3
import google.generativeai as genai
from datetime import datetime
import os
import base64
import json
import time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ==================== CONFIGURATION ====================
# استبدل هذا المفتاح بمفتاحك الذي حصلت عليه من Google AI Studio
GEMINI_API_KEY = "AIzaSyCG7WK6t9Fn73Oq2ajJ337KRUrW57X82Ao" 
SECRET_KEY = b"1Xt5YfM4ZNuFdwp3OfVkwkhhQLagWKtt" # مفتاح التشفير (يجب أن يكون 32 حرف)
DB_NAME = 'luna_performance_v2.db'

# تهيئة ذكاء LUNA الاصطناعي
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    print(f"AI Core Warning: {e}")

app = FastAPI(title="Human Performance OS v2.0")

# ==================== DATABASE LAYER ====================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # إنشاء الجدول ليتطابق تماماً مع متطلبات ملف الـ Frontend
    c.execute('''CREATE TABLE IF NOT EXISTS performance_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT, 
                  score REAL, 
                  sleep_hours REAL,
                  focus_hours REAL, 
                  energy_level INTEGER,
                  habit_consistency REAL, 
                  user_id TEXT,
                  recommendation TEXT, 
                  encrypted_data TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ==================== MODELS & SECURITY ====================
class UserMetrics(BaseModel):
    sleep_hours: float
    focus_hours: float
    energy_level: int
    habit_consistency: float

def encrypt_payload(data: dict) -> str:
    try:
        aesgcm = AESGCM(SECRET_KEY)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, json.dumps(data).encode(), None)
        return base64.b64encode(nonce + ct).decode()
    except:
        return "Encryption_Error"

# ==================== AI LOGIC ENGINE ====================
def get_luna_ai_advice(metrics: UserMetrics, score: float):
    prompt = f"""
    You are LUNA, a neuro-performance AI. 
    Analyze metrics: Sleep {metrics.sleep_hours}h, Focus {metrics.focus_hours}h, Energy {metrics.energy_level}/10. 
    Calculated Score: {score}/10.
    Provide a professional, brief (2 sentences) recommendation in Arabic about human performance.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "أداء جيد. استمر في ممارسة عاداتك الصحية للحفاظ على استقرار مستوى الطاقة والتركيز."

# ==================== API ENDPOINTS ====================
@app.post("/evaluate")
async def evaluate_performance(metrics: UserMetrics, x_api_key: str = Header(None)):
    # التحقق من مفتاح الوصول (يجب أن يطابق الموجود في الفرونت)
    if x_api_key != "luna-v2-demo":
        raise HTTPException(status_code=401, detail="Unauthorized Access Protocol")
    
    # حساب النتيجة بناءً على لوجيك LUNA
    # النتيجة من 10 (التركيز 40%، الطاقة 30%، الاستمرارية 30%)
    score = round((metrics.focus_hours * 0.4) + (metrics.energy_level * 0.3) + (metrics.habit_consistency * 3.0), 2)
    if score > 10: score = 10.0
    
    # طلب نصيحة الذكاء الاصطناعي
    recommendation = get_luna_ai_advice(metrics, score)
    
    # تشفير البيانات الحساسة قبل الحفظ
    encrypted_metrics = encrypt_payload(metrics.dict())
    
    # حفظ في قاعدة البيانات الموحدة
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""INSERT INTO performance_logs 
                     (timestamp, score, sleep_hours, focus_hours, energy_level, habit_consistency, user_id, recommendation, encrypted_data) 
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                   score, metrics.sleep_hours, metrics.focus_hours, 
                   metrics.energy_level, metrics.habit_consistency, 
                   "LUNA_ADMIN", recommendation, encrypted_metrics))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Matrix Storage Failure")

    return {
        "performance_score": score,
        "recommendation": recommendation,
        "status": "Success",
        "timestamp": datetime.now().isoformat()
    }

# تشغيل السيرفر
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
