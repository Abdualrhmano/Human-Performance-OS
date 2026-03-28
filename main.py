from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import uvicorn
import sqlite3
import google.generativeai as genai
from datetime import datetime
import os
import base64
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ==================== CONFIGURATION ====================
# ضع مفتاح Gemini API الخاص بك هنا
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE" 
SECRET_KEY = b"1Xt5YfM4ZNuFdwp3OfVkwkhhQLagWKtt" 
DB_NAME = 'human_performance_v2.db'

# تهيئة الذكاء الاصطناعي للنظام الصحي
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    print(f"AI Engine Warning: {e}")

app = FastAPI(title="Human Performance OS v2.0 - Core Engine")

# ==================== DATABASE LAYER (HEALTH DATA) ====================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # إنشاء الجدول مع حقول الساعة الذكية (Bio-metrics)
    c.execute('''CREATE TABLE IF NOT EXISTS health_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT, 
                  score REAL, 
                  sleep_hours REAL,
                  focus_hours REAL, 
                  energy_level INTEGER,
                  habit_consistency REAL, 
                  heart_rate INTEGER,   -- نبضات القلب
                  steps INTEGER,        -- الخطوات
                  calories INTEGER,     -- السعرات
                  user_id TEXT,
                  recommendation TEXT, 
                  encrypted_data TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ==================== MODELS & SECURITY ====================
class HealthMetrics(BaseModel):
    sleep_hours: float
    focus_hours: float
    energy_level: int
    habit_consistency: float
    heart_rate: int
    steps: int
    calories: int

def encrypt_health_data(data: dict) -> str:
    try:
        aesgcm = AESGCM(SECRET_KEY)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, json.dumps(data).encode(), None)
        return base64.b64encode(nonce + ct).decode()
    except:
        return "SECURE_DATA_BLOB"

# ==================== HEALTH ANALYSIS ENGINE ====================
def get_health_ai_advice(metrics: HealthMetrics, score: float):
    prompt = f"""
    You are the Human Performance OS Health Coach.
    Analyze these Biometrics: 
    Heart Rate: {metrics.heart_rate} BPM, Steps: {metrics.steps}, Calories: {metrics.calories} kcal.
    Sleep: {metrics.sleep_hours}h, Focus: {metrics.focus_hours}h.
    Performance Score: {score}/10.
    Provide a concise (2 sentences) professional health & biohacking recommendation in Arabic.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "حافظ على وتيرة نشاطك الحالية، وتأكد من شرب كميات كافية من الماء لدعم عملية الاستشفاء."

# ==================== API ENDPOINTS ====================
@app.post("/evaluate")
async def evaluate_health(metrics: HealthMetrics, x_api_key: str = Header(None)):
    # التحقق من بروتوكول الوصول
    if x_api_key != "luna-v2-demo":
        raise HTTPException(status_code=401, detail="Access Protocol Denied")
    
    # حساب النتيجة الصحية (Health Score)
    # خوارزمية تجمع بين النشاط البدني (الساعة) والنشاط الذهني (التركيز)
    step_bonus = min(metrics.steps / 10000, 1.0) * 2.0 # بونص للخطوات حتى 10 آلاف
    score = round((metrics.focus_hours * 0.3) + (metrics.energy_level * 0.2) + (metrics.habit_consistency * 2.0) + step_bonus, 2)
    if score > 10: score = 10.0
    
    # طلب تحليل الذكاء الاصطناعي بناءً على بيانات الساعة
    recommendation = get_health_ai_advice(metrics, score)
    
    # تشفير البيانات للحماية
    enc_data = encrypt_health_data(metrics.dict())
    
    # حفظ في قاعدة البيانات الصحية
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""INSERT INTO health_logs 
                     (timestamp, score, sleep_hours, focus_hours, energy_level, habit_consistency, heart_rate, steps, calories, user_id, recommendation, encrypted_data) 
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                   score, metrics.sleep_hours, metrics.focus_hours, 
                   metrics.energy_level, metrics.habit_consistency,
                   metrics.heart_rate, metrics.steps, metrics.calories,
                   "HP_USER_01", recommendation, enc_data))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail="Data Storage Logic Error")

    return {
        "performance_score": score,
        "recommendation": recommendation,
        "heart_rate_status": "Stable" if 60 <= metrics.heart_rate <= 100 else "Check Activity",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
