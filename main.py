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
from fastapi.middleware.cors import CORSMiddleware  # حجر الزاوية للربط بالفرانت إند

# --- 1. CENTRAL CONFIGURATION ---
class SystemConfig:
    """إعدادات النظام السيادي - جميع المفاتيح هنا"""
    OS_NAME = "Human Performance OS v2.0"
    GEMINI_API_KEY = "AIzaSyCG7WK6t9Fn73Oq2ajJ337KRUrW57X82Ao"
    SECRET_KEY = b"1Xt5YfM4ZNuFdwp3OfVkwkhhQLagWKtt"
    ALGORITHM = "HS256"
    TOKEN_EXPIRY_HOURS = 24
    
    # تحويل مفتاحك الخاص لصيغة تشفير Fernet للبيانات الحساسة
    _padded_key = SECRET_KEY.ljust(32)[:32]
    FERNET_KEY = base64.urlsafe_b64encode(_padded_key)
    cipher_suite = Fernet(FERNET_KEY)

# --- 2. SECURITY PROVIDER ---
class SecurityProvider:
    """محرك الحماية والمصادقة"""
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @staticmethod
    def hash_password(password: str): 
        return SecurityProvider.pwd_context.hash(password)

    @staticmethod
    def verify_password(plain, hashed): 
        return SecurityProvider.pwd_context.verify(plain, hashed)

    @staticmethod
    def generate_token(data: dict):
        payload = data.copy()
        payload.update({"exp": datetime.utcnow() + timedelta(hours=SystemConfig.TOKEN_EXPIRY_HOURS)})
        return jwt.encode(payload, SystemConfig.SECRET_KEY, algorithm=SystemConfig.ALGORITHM)

# --- 3. DATA SCHEMAS (للتعامل مع الفرانت إند) ---
class UserAuthSchema(BaseModel):
    username: str
    password: str

class DeviceMetricsSchema(BaseModel):
    """النموذج الذي سيرسله الفرانت إند من الحساسات"""
    heart_rate: int = Field(..., example=75)
    steps: int = Field(..., example=8000)
    screen_time: float = Field(..., example=3.2)
    sleep_hours: float = Field(..., example=7.5)
# ======================================================
# SYSTEM: Human Performance OS v2.0
# MODULE 2: NEURAL ENGINES & DATABASE
# ======================================================

# --- 1. DATABASE ARCHITECT (مخزن الذاكرة) ---
class DatabaseManager:
    """إدارة قاعدة البيانات لضمان استقرار سجلات الأداء"""
    def __init__(self, db_name="human_performance_v2.db"):
        self.db_name = db_name
        self._create_tables()

    def _create_tables(self):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            # جدول المستخدمين
            c.execute('''CREATE TABLE IF NOT EXISTS users 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          username TEXT UNIQUE, 
                          password_hash TEXT)''')
            # جدول الأداء التاريخي
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

# --- 2. NEURAL PROCESSOR (محرك حساب السكور) ---
class NeuralProcessor:
    """الخوارزمية التي تدمج بيانات الساعة والموبايل"""
    @staticmethod
    def calculate_score(m: DeviceMetricsSchema):
        # 40% حركة، 30% نوم، 30% استقرار قلب، مع خصم لوقت الشاشة
        step_score = min((m.steps / 10000) * 40, 40)
        sleep_score = min((m.sleep_hours / 8) * 30, 30)
        hr_score = 30 if 60 <= m.heart_rate <= 100 else 15
        screen_penalty = max(0, (m.screen_time - 4) * 5) # خصم 5 نقاط لكل ساعة شاشة إضافية
        
        final = (step_score + sleep_score + hr_score) - screen_penalty
        return round(max(0, min(final, 100)), 2)

# --- 3. LUNA NEURAL BRAIN (الاتصال بـ Gemini) ---
class LunaNeuralBrain:
    """المحرك الذكي: يربط Gemini بذاكرة أداء المستخدم لتقديم تحليل سيادي"""
    
    def __init__(self, api_key: str):
        # إعداد الاتصال بجوجل باستخدام مفتاح الـ API الخاص بـ Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def get_history(self, db_conn, user_id: int):
        """سحب آخر 3 سجلات من قاعدة البيانات ليعرف الذكاء الاصطناعي سياق الأداء"""
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT performance_score, timestamp 
            FROM performance_logs 
            WHERE user_id = ? 
            ORDER BY timestamp DESC LIMIT 3
        """, (user_id,))
        rows = cursor.fetchall()
        
        if not rows: 
            return "لا يوجد سجلات سابقة للمقارنة."
        
        return "سجلات الأداء السابقة: " + ", ".join([f"سكور {r[0]} في {r[1]}" for r in rows])

    def generate_insight(self, metrics: dict, history: str):
        """توليد تحليل ذكي ونصيحة Biohacking باللغة العربية الفصحى"""
        
        # البرومبت المحدث لضمان لغة عربية احترافية تتناسب مع نظام سيادي
        prompt = f"""
        بصفتك العقل المدبر لنظام {SystemConfig.OS_NAME}. 
        البيانات الحيوية الحالية: {metrics}. 
        سياق التاريخ السابق: {history}. 
        
        المطلوب: 
        1. تقديم تحليل تقني سريع للأداء الحالي (هل هو تحسن أم تراجع؟).
        2. إعطاء نصيحة 'Biohacking' محددة لرفع الكفاءة العصبية والتركيز.
        
        الشروط:
        - الرد يجب أن يكون في جملتين فقط.
        - اللغة المستخدمة هي العربية الفصحى بأسلوب تقني راقٍ.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception: 
            # رد احتياطي ذكي في حال فشل الاتصال بالسيرفر
            return "نظام LUNA: حافظ على استقرار نشاطك الحيوي الآن لتحقيق أقصى كفاءة عصبية لاحقاً."


class PerformanceAdvisor:
    """المسؤول عن دمج العقل والذاكرة"""
    def __init__(self, brain: LunaNeuralBrain):
        self.brain = brain
        
    def get_verdict(self, db_conn, user_id, metrics):
        history_text = self.brain.get_history(db_conn, user_id)
        return self.brain.generate_insight(metrics, history_text)
# ======================================================
# SYSTEM: Human Performance OS v2.0
# MODULE 3: MASTER API & FRONTEND BRIDGE (CORS)
# ======================================================

# --- 1. INITIALIZATION (تشغيل المحركات المركزية) ---
app = FastAPI(
    title=SystemConfig.OS_NAME,
    description="The Pulse of Human Performance OS",
    version="2.0.0"
)

# --- 2. CORS CONFIGURATION (جسر الربط بالفرانت إند) ---
# دي أهم خطوة عشان الكود يشتغل مع React/Vue/Flutter
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # يسمح بالاتصال من أي مصدر (موبايل/ويب)
    allow_credentials=True,
    allow_methods=["*"], # يسمح بكل أنواع الطلبات (GET, POST, etc.)
    allow_headers=["*"], # يسمح بكل أنواع الـ Headers
)

# --- 3. DEPENDENCIES (تعريف الأدوات المساعدة) ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v2/auth/login")
db_manager = DatabaseManager()
security = SecurityProvider()
brain = LunaNeuralBrain(api_key=SystemConfig.GEMINI_API_KEY)
advisor = PerformanceAdvisor(brain)

# --- 4. AUTHENTICATION (بوابة الدخول) ---
@app.post("/api/v2/auth/register", tags=["Security"])
async def register(user: UserAuthSchema):
    """تسجيل مستخدم جديد في النظام السيادي"""
    with sqlite3.connect(db_manager.db_name) as conn:
        cursor = conn.cursor()
        try:
            hashed = security.hash_password(user.password)
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
                           (user.username, hashed))
            conn.commit()
            return {"status": "success", "message": "Enrolled in OS v2.0"}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="User already exists")

@app.post("/api/v2/auth/login", tags=["Security"])
async def login(user: UserAuthSchema):
    """توليد توكن الدخول للفرانت إند"""
    with sqlite3.connect(db_manager.db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (user.username,))
        record = cursor.fetchone()
        
        if not record or not security.verify_password(user.password, record[1]):
            raise HTTPException(status_code=401, detail="Invalid Credentials")
        
        # إنشاء التوكن اللي الفرانت إند هيخزنه عنده
        token = security.generate_token(data={"sub": user.username, "user_id": record[0]})
        return {
            "access_token": token, 
            "token_type": "bearer",
            "username": user.username
        }
# ======================================================
# SYSTEM: Human Performance OS v2.0
# MODULE 4: MASTER SYNC & SERVER DEPLOYMENT
# ======================================================

# --- 1. THE NEURAL SYNC (مزامنة الأجهزة + الذكاء الاصطناعي) ---
@app.post("/api/v2/performance/sync", tags=["Neural Sync"])
async def sync_and_analyze(
    data: DeviceMetricsSchema, 
    token: str = Depends(oauth2_scheme)
):
    """
    هذا المسار يستقبل بيانات الساعة والموبايل، يحللها، 
    ويخزنها مشفرة مع نصيحة Gemini.
    """
    # أ. فك تشفير التوكن (التحقق من الهوية)
    try:
        payload = jwt.decode(token, SystemConfig.SECRET_KEY, algorithms=[SystemConfig.ALGORITHM])
        user_id = payload.get("user_id")
    except:
        raise HTTPException(status_code=403, detail="Invalid or Expired Session")

    # ب. معالجة السكور (الجهاز العصبي)
    performance_score = NeuralProcessor.calculate_score(data)
    
    # ج. استشارة العقل (LUNA Neural Brain)
    with sqlite3.connect(db_manager.db_name) as conn:
        current_metrics = {
            "hr": data.heart_rate, 
            "steps": data.steps, 
            "screen_time": data.screen_time, 
            "sleep": data.sleep_hours, 
            "score": performance_score
        }
        
        # استدعاء الذاكرة وتوليد النصيحة من Gemini
        ai_insight = advisor.get_verdict(conn, user_id, current_metrics)

        # د. الحفظ النهائي في قاعدة البيانات
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO performance_logs 
            (user_id, heart_rate, steps, screen_time, sleep_hours, 
             performance_score, ai_recommendation, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, data.heart_rate, data.steps, data.screen_time, data.sleep_hours, 
              performance_score, ai_insight, datetime.now()))
        conn.commit()

    # هـ. الرد النهائي للفرانت إند (JSON Response)
    return {
        "status": "synchronized",
        "performance_score": performance_score,
        "ai_insight": ai_insight,
        "metrics_summary": {
            "is_optimal": performance_score > 70,
            "heart_rate_status": "Stable" if data.heart_rate < 100 else "High"
        },
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# --- 2. SERVER ENTRY POINT (نقطة انطلاق النظام) ---
if __name__ == "__main__":
    # تشغيل السيرفر على جميع الواجهات للوصول إليه من الموبايل أو الويب
    print(f"🚀 {SystemConfig.OS_NAME} is waking up...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
