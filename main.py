# ======================================================
# SYSTEM: Human Performance OS v2.0
# MODULE 1: CORE ARCHITECTURE & SECURITY
# ======================================================

import os
import jwt
import base64
import sqlite3
import uvicorn
import google.generativeai as genai
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
import hashlib

# --- 1. CENTRAL CONFIGURATION ---
class SystemConfig:
    """إعدادات النظام السيادي - جميع المفاتيح هنا"""
    OS_NAME = "Human Performance OS v2.0"
    GEMINI_API_KEY = "AIzaSyCG7WK6t9Fn73Oq2ajJ337KRUrW57X82Ao"
    SECRET_KEY = b"1Xt5YfM4ZNuFdwp3OfVkwkhhQLagWKtt"
    ALGORITHM = "HS256"
    TOKEN_EXPIRY_HOURS = 24
    
    _padded_key = SECRET_KEY.ljust(32)[:32]
    FERNET_KEY = base64.urlsafe_b64encode(_padded_key)
    cipher_suite = Fernet(FERNET_KEY)

# --- 2. SECURITY PROVIDER ---
class SecurityProvider:
    """محرك حماية مستقر تماماً لبيئات الـ Cloud"""
    
    @staticmethod
    def hash_password(password: str):
        # استخدام hashlib لضمان الاستقرار في بيئة Codespaces
        salt = str(SystemConfig.SECRET_KEY)
        db_password = password + salt
        return hashlib.sha256(db_password.encode()).hexdigest()

    @staticmethod
    def verify_password(plain, hashed):
        return SecurityProvider.hash_password(plain) == hashed
        
    @staticmethod
    def generate_token(data: dict):
        payload = data.copy()
        payload.update({"exp": datetime.utcnow() + timedelta(hours=SystemConfig.TOKEN_EXPIRY_HOURS)})
        return jwt.encode(payload, SystemConfig.SECRET_KEY, algorithm=SystemConfig.ALGORITHM)

# --- 3. DATA SCHEMAS ---
class UserAuthSchema(BaseModel):
    username: str
    password: str

class DeviceMetricsSchema(BaseModel):
    heart_rate: int = Field(..., example=75)
    steps: int = Field(..., example=8000)
    screen_time: float = Field(..., example=3.2)
    sleep_hours: float = Field(..., example=7.5)

# ======================================================
# MODULE 2: NEURAL ENGINES & DATABASE
# ======================================================

class DatabaseManager:
    def __init__(self, db_name="human_performance_v2.db"):
        self.db_name = db_name
        self._create_tables()

    def _create_tables(self):
        with sqlite3.connect(self.db_name) as conn:
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
                          timestamp DATETIME)''')
            conn.commit()

class NeuralProcessor:
    @staticmethod
    def calculate_score(m: DeviceMetricsSchema):
        step_score = min((m.steps / 10000) * 40, 40)
        sleep_score = min((m.sleep_hours / 8) * 30, 30)
        hr_score = 30 if 60 <= m.heart_rate <= 100 else 15
        screen_penalty = max(0, (m.screen_time - 4) * 5)
        final = (step_score + sleep_score + hr_score) - screen_penalty
        return round(max(0, min(final, 100)), 2)

class LunaNeuralBrain:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def get_history(self, db_conn, user_id: int):
        cursor = db_conn.cursor()
        cursor.execute("SELECT performance_score, timestamp FROM performance_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 3", (user_id,))
        rows = cursor.fetchall()
        if not rows: return "لا يوجد سجلات سابقة."
        return "السجلات السابقة: " + ", ".join([f"سكور {r[0]} في {r[1]}" for r in rows])

    def generate_insight(self, metrics: dict, history: str):
        prompt = f"بصفتك العقل المدبر لنظام {SystemConfig.OS_NAME}. البيانات: {metrics}. التاريخ: {history}. قدم نصيحة Biohacking في جملتين بالعربية الفصحى."
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except:
            return "نظام LUNA: حافظ على استقرار نشاطك الحيوي حالياً."

class PerformanceAdvisor:
    def __init__(self, brain: LunaNeuralBrain):
        self.brain = brain
    def get_verdict(self, db_conn, user_id, metrics):
        history_text = self.brain.get_history(db_conn, user_id)
        return self.brain.generate_insight(metrics, history_text)

# ======================================================
# MODULE 3: MASTER API & FRONTEND BRIDGE
# ======================================================

app = FastAPI(title=SystemConfig.OS_NAME, version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v2/auth/login")
db_manager = DatabaseManager()
security = SecurityProvider()
brain = LunaNeuralBrain(api_key=SystemConfig.GEMINI_API_KEY)
advisor = PerformanceAdvisor(brain)

# ======================================================
# MODULE 4: ENDPOINTS & DEPLOYMENT
# ======================================================

@app.post("/api/v2/auth/register", tags=["Security"])
async def register(user: UserAuthSchema):
    with sqlite3.connect(db_manager.db_name) as conn:
        cursor = conn.cursor()
        try:
            hashed = security.hash_password(user.password)
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (user.username, hashed))
            conn.commit()
            return {"status": "success", "message": "Enrolled in OS v2.0"}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="User already exists")

@app.post("/api/v2/auth/login", tags=["Security"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    with sqlite3.connect(db_manager.db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (form_data.username,))
        record = cursor.fetchone()
        if not record or not security.verify_password(form_data.password, record[1]):
            raise HTTPException(status_code=401, detail="Invalid Credentials")
        
        token = security.generate_token(data={"sub": form_data.username, "user_id": record[0]})
        return {"access_token": token, "token_type": "bearer"}

@app.post("/api/v2/performance/sync", tags=["Neural Sync"])
async def sync_and_analyze(data: DeviceMetricsSchema, token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SystemConfig.SECRET_KEY, algorithms=[SystemConfig.ALGORITHM])
        user_id = payload.get("user_id")
    except:
        raise HTTPException(status_code=403, detail="Invalid or Expired Session")

    performance_score = NeuralProcessor.calculate_score(data)
    
    with sqlite3.connect(db_manager.db_name) as conn:
        current_metrics = {"hr": data.heart_rate, "steps": data.steps, "sleep": data.sleep_hours, "score": performance_score}
        ai_insight = advisor.get_verdict(conn, user_id, current_metrics)
        
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO performance_logs 
            (user_id, heart_rate, steps, screen_time, sleep_hours, performance_score, ai_recommendation, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", 
            (user_id, data.heart_rate, data.steps, data.screen_time, data.sleep_hours, performance_score, ai_insight, datetime.now()))
        conn.commit()

    return {"status": "success", "performance_score": performance_score, "ai_insight": ai_insight}

if __name__ == "__main__":
    print(f"🚀 {SystemConfig.OS_NAME} is waking up...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
