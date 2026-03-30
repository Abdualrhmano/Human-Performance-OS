# ======================================================
# SYSTEM: Human Performance OS v2.0 (INTEGRATED)
# ARCHITECT: Abdulrahman (Lead Software Engineer)
# MODULE: LUNA CORE & BIOMETRIC GATEWAY
# ======================================================

import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import asyncio
import random
from bleak import BleakClient, BleakScanner

from snowflake.cortex import complete
import textwrap

class LUNAChat:
    def __init__(self, model="local-luna-core"):
        self.model = model

    def get_response(self, prompt, history):
        # حذفنا سطر snowflake تماماً هنا عشان نمنع الخطأ
        try:
            # رد محاكي ذكي يظهر كأن LUNA هي اللي بترد
            response = f"LUNA OS: Command '{prompt}' received. Analyzing neural telemetry... [Status: Stable]"
            return response
        except Exception as e:
            return f"Neural Link Error: {str(e)}"

    def render_ui(self):
        st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>🤖 Neural Chat Link</h3>", unsafe_allow_html=True)
        
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # 1. حاوية عرض الرسائل
        chat_container = st.container(height=400)
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # 2. استقبال المدخلات (Chat Input)
        if prompt := st.chat_input("Send command to LUNA..."):
            # عرض رسالة المستخدم فوراً
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.chat_message("assistant"):
                    # استدعاء الرد المحلي
                    response_text = self.get_response(prompt, st.session_state.messages)
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})

        # 2. منطقة إدخال المستخدم والرد اللحظي
        if prompt := st.chat_input("Send command to LUNA OS..."):
            # حفظ رسالة المستخدم
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with chat_container:
                # عرض رسالة المستخدم فوراً
                with st.chat_message("user"):
                    st.markdown(prompt)

                # عرض رد الـ AI (هنا كان الغلط في المسافات)
                with st.chat_message("assistant"):
                    response_gen = self.get_response(prompt, st.session_state.messages[:-1])
                    
                    if isinstance(response_gen, str):
                        st.markdown(response_gen)
                        full_response = response_gen
                    else:
                        full_response = st.write_stream(response_gen)
                    
                    # حفظ الرد النهائي في الذاكرة
                    st.session_state.messages.append({"role": "assistant", "content": full_response})

# 1. PROFESSIONAL UI CONFIGURATION
class SystemUI:
    @staticmethod
    def setup():
        st.set_page_config(page_title="Human Performance OS v2.0", page_icon="🧠", layout="wide")
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono:wght@300;500&display=swap');
            
            :root { 
                --primary: #00ff88; 
                --bg: #05070a; 
                --sidebar-bg: #0d1117;
                --accent-red: #ff4b4b;
                --card-bg: rgba(13, 17, 23, 0.8);
            }

            /* إعدادات الخلفية العامة والخطوط */
            .stApp { background-color: var(--bg); color: #e6edf3; font-family: 'JetBrains Mono', monospace; }
            
            /* تصميم القائمة الجانبية (Sidebar) */
            section[data-testid="stSidebar"] {
                background-color: var(--sidebar-bg) !important;
                border-right: 1px solid #30363d;
            }

            /* العنوان الرئيسي المتوهج */
            .main-title { 
                font-family: 'Orbitron', sans-serif; 
                color: var(--primary); 
                text-shadow: 0 0 20px rgba(0, 255, 136, 0.4); 
                font-size: 2.5em; 
                text-align: center; 
                margin-bottom: 20px; 
            }

            /* تصميم السلايدرز التقني */
            .stSlider [data-baseweb="slider"] div { background-color: var(--accent-red) !important; }
            
            /* بطاقة الذكاء الاصطناعي والنتائج */
            .luna-card {
                background: var(--card-bg);
                border: 1px solid var(--primary);
                border-left: 6px solid var(--primary);
                padding: 15px;
                border-radius: 10px;
                margin: 10px 0;
            }
            
            /* تصميم أزرار البلوتوث والمزامنة */
            .stButton > button {
                background-color: #21262d !important;
                color: white !important;
                border: 1px solid #30363d !important;
                border-radius: 8px !important;
                font-family: 'Orbitron', sans-serif !important;
                transition: 0.3s ease;
            }
            .stButton > button:hover {
                border-color: var(--primary) !important;
                color: var(--primary) !important;
                box-shadow: 0 0 15px rgba(0, 255, 136, 0.2);
            }

            /* حاوية الدردشة العصبي (Neural Chat Box) */
            .chat-box {
                border: 1px solid #30363d;
                border-radius: 12px;
                padding: 15px;
                background: rgba(0, 0, 0, 0.3);
                height: 400px;
                overflow-y: auto;
            }
            </style>
        """, unsafe_allow_html=True)

class CoreBridge:
    DB_PATH = "human_performance_v2.db"
    
    @staticmethod
    def init_db():
        import sqlite3
        conn = sqlite3.connect(CoreBridge.DB_PATH)
        conn.execute('''CREATE TABLE IF NOT EXISTS performance_logs 
                        (timestamp TEXT, performance_score REAL, hr INTEGER, steps INTEGER)''')
        conn.commit()
        conn.close()

# --- واجهة المستخدم الرئيسية (Sidebar & Controls) ---
SystemUI.setup()
CoreBridge.init_db()

with st.sidebar:
    st.markdown("<h2 style='color:#00ff88; font-family:Orbitron;'>📡 LUNA CONNECT</h2>", unsafe_allow_html=True)
    
    # خانة البلوتوث المطلوبة
    st.markdown("### 🔵 Bluetooth Protocol")
    bt_status = st.toggle("Enable Neural Link Scanner")
    if bt_status:
        st.success("Searching for Biometric Devices...")
    else:
        st.warning("Bluetooth Offline")
    
    st.divider()
    
    # العدادات والتحكم (التي كانت في الكود الأول)
    hr_val = st.slider("💓 Heart Rate (BPM)", 40, 190, 75)
    steps_val = st.number_input("👟 Daily Step Count", 0, 30000, 5000)
    
    if st.button("🔄 Sync Telemetry"):
        st.toast("Syncing with Local Database...")

# --- مساحة العمل الرئيسية ---
st.markdown('<h1 class="main-title">🛡️ LUNA CORE v2.0</h1>', unsafe_allow_html=True)

col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.markdown('<div class="luna-card">', unsafe_allow_html=True)
    st.markdown("<h3 style='color:#00ff88; margin-top:0;'>🤖 AI VERDICT</h3>", unsafe_allow_html=True)
    st.info("LUNA Intelligence: النظام مستقر، الأداء الحيوي ضمن النطاق الطبيعي لليوم.")
    st.markdown('</div>', unsafe_allow_html=True)

    # بوكس الذكاء الاصطناعي (Neural Chat)
    st.markdown("### 🧠 Neural Chat Link")
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    chat_container = st.container(border=True)
    with chat_container:
        # هنا يتم عرض الرسائل كما في الكود المحلي السابق
        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).write(msg["content"])
            
    if prompt := st.chat_input("Send command to LUNA..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        # محاكاة رد النظام
        st.session_state.messages.append({"role": "assistant", "content": f"Recieved: {prompt}. Analysis complete."})
        st.rerun()

with col_right:
    st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>📊 Metrics</h3>", unsafe_allow_html=True)
    # هنا تضع كود الرسم البياني (Plotly) الذي قمنا بتعديله مسبقاً
    st.caption("Historical Data visualization will appear here.")
       
class CoreBridge:
    DB_PATH = "human_performance_v2.db"

    @staticmethod
    def init_db():
        conn = sqlite3.connect(CoreBridge.DB_PATH)
        # إنشاء الجدول بالأعمدة الأربعة مباشرة
        conn.execute('''CREATE TABLE IF NOT EXISTS performance_logs 
                        (timestamp TEXT, performance_score REAL, hr INTEGER, steps INTEGER)''')
        
        # فحص ذكي لإضافة الأعمدة لو الجدول قديم (Migration)
        cursor = conn.execute("PRAGMA table_info(performance_logs)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'hr' not in columns:
            conn.execute("ALTER TABLE performance_logs ADD COLUMN hr INTEGER DEFAULT 75")
        if 'steps' not in columns:
            conn.execute("ALTER TABLE performance_logs ADD COLUMN steps INTEGER DEFAULT 0")
        conn.commit()
        conn.close()

    @staticmethod
    def save_log(score, hr, steps):
        conn = sqlite3.connect(CoreBridge.DB_PATH)
        query = "INSERT INTO performance_logs (timestamp, performance_score, hr, steps) VALUES (?, ?, ?, ?)"
        conn.execute(query, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), score, hr, steps))
        conn.commit()
        conn.close()

    @staticmethod
    def fetch_historical_data():
        try:
            conn = sqlite3.connect(CoreBridge.DB_PATH)
            df = pd.read_sql_query("SELECT * FROM performance_logs ORDER BY timestamp DESC LIMIT 20", conn)
            conn.close()
            return df
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def get_luna_verdict(score, hr, steps):
        hr_advice = "🟢 نبض مستقر"
        if hr > 110: hr_advice = "⚠️ معدل النبض مرتفع جداً؛ يرجى ممارسة تمارين التنفس"
        elif hr < 50: hr_advice = "💤 النبض منخفض؛ قد تكون في حالة إرشادية أو خمول"
        
        activity_advice = "🏃 استمر في التحرك لكسر حالة الخمول" if steps < 3000 else "💪 أداء حركي ممتاز"
        
        if score >= 80: status = "🔥 أداؤك في القمة! النظام في حالة تناغم كامل"
        elif score >= 50: status = "🟢 مستقر. حافظ على روتينك الحالي مع شرب الماء"
        else: status = "🔴 يوصي بالراحة الآن LUNA تلاحظ تراجع في الأداء الحيوي"
        
        return f"{status}\n\n{hr_advice}\n\n{activity_advice}"

# 3. INITIALIZATION
SystemUI.setup()
CoreBridge.init_db()

# --- SIDEBAR CONTROL CENTER ---
with st.sidebar:
    st.markdown("<h2 style='color:#00ff88; font-family:Orbitron;'>🛡️ LUNA CORE</h2>", unsafe_allow_html=True)
    auth_token = st.text_input("NEURAL ACCESS KEY", type="password", value="A7-X9-RAG-CORE-V10")
    
    st.divider()
    st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>🤖 AI VERDICT</h3>", unsafe_allow_html=True)
    
    # استرجاع البيانات السابقة من الـ Session
    luna_msg = st.session_state.get('last_verdict', "في انتظار مزامنة البيانات للتحليل...")
    current_score = st.session_state.get('current_score', 0.0)
    
    st.markdown(f"""
        <div style="background: rgba(0,255,136,0.1); border: 1px solid #00ff88; padding: 15px; border-radius: 10px; border-left: 5px solid #00ff88;">
            <p style="color:#00ff88; font-weight:bold; margin-bottom:5px;">LUNA Intelligence:</p>
            <p style="font-size:0.95em; color:white;">{luna_msg}</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>📡 TELEMETRY</h3>", unsafe_allow_html=True)
    
    hr_val = st.slider("💓 Heart Rate (BPM)", 40, 190, 75)
    step_val = st.number_input("👟 Daily Step Count", value=6000)
    
    init_sync = st.button("🚀 INITIATE SYSTEM SYNC")

# --- SYNC LOGIC ---
if init_sync:
    with st.spinner("Processing Neural Signals..."):
        generated_score = round(random.uniform(30, 95), 1)
        st.session_state.current_score = generated_score
        st.session_state.last_verdict = CoreBridge.get_luna_verdict(generated_score, hr_val, step_val)
        CoreBridge.save_log(generated_score, hr_val, step_val)
        st.rerun()
        
# --- 1. MAIN DASHBOARD AREA & TABS CONFIGURATION ---
st.markdown("<h1 class='main-title'>Human Performance OS v2.0</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#8b949e; margin-bottom:10px;'>Senior Engineer: Abdulrahman | Neural-Biometric Protocol Active</p>", unsafe_allow_html=True)

# إضافة نظام التبويبات لدمج الـ Dashboard والشات
tab_metrics, tab_ai = st.tabs(["📊 SYSTEM METRICS", "🤖 NEURAL CHAT LINK"])

with tab_metrics:
    # تقسيم الشاشة لعرض العداد والتحليل (نفس كودك الأصلي)
    col_left, col_right = st.columns([1, 1.5], gap="large")

    with col_left:
        st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>🧠 Live Analysis</h3>", unsafe_allow_html=True)
        
        display_score = st.session_state.get('current_score', 46.6)
        
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = display_score,
            number = {'font': {'color': 'white', 'family': 'Orbitron'}},
            gauge = {
                'axis': {'range': [0, 100], 'tickcolor': "#00ff88"},
                'bar': {'color': "#00ff88"},
                'bgcolor': "rgba(0,0,0,0)",
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': display_score
                }
            }
        ))
            # 1. العداد وتنبيه الحالة (مرة واحدة فقط)
    fig_gauge.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
    st.plotly_chart(fig_gauge, use_container_width=True, key="main_performance_gauge")
    
    if display_score < 50:
        st.markdown("<p style='text-align:center; color:#ff4b4b; font-weight:bold;'>🔴 CRITICAL: تراجع في الأداء الحيوي</p>", unsafe_allow_html=True)
    else:
        st.markdown("<p style='text-align:center; color:#00ff88; font-weight:bold;'>🟢 OPTIMAL: حالة النظام مستقرة</p>", unsafe_allow_html=True)

    # 2. تنظيم التبويبات (الشات والبيانات)
    tab_neural, tab_sys = st.tabs(["🤖 NEURAL LINK", "📊 SYSTEM METRICS"])

    with tab_neural:
        # هنا الشات والـ Timeline جنب بعض بشكل احترافي
        col_chat, col_timeline = st.columns([2, 1])
        
        with col_chat:
            luna_chat = LUNAChat()
            luna_chat.render_ui()

        with col_timeline:
            st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>📈 Timeline</h3>", unsafe_allow_html=True)
            hist_df = CoreBridge.fetch_historical_data()
            if not hist_df.empty:
                fig_line = px.area(hist_df.iloc[::-1], x='timestamp', y='performance_score')
                fig_line.update_traces(
                    line_color='#00ff88', 
                    fillcolor='rgba(0, 255, 136, 0.1)', 
                    marker=dict(size=8, color='#00ff88'), 
                    line_width=3
                )
                fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, font={'color': "white"})
                st.plotly_chart(fig_line, use_container_width=True, key="unique_performance_chart")
            else:
                st.info("No data yet.")


# --- 2. SYSTEM LOGS SECTION (Image 3 Style) ---
st.divider()
with st.expander("📂 VIEW SYSTEM DATABASE LOGS (SQLite3)"):
    st.markdown("<h4 style='color:#00ff88; font-family:Orbitron;'>📜 RAW TELEMETRY DATA</h4>", unsafe_allow_html=True)
    if not hist_df.empty:
        # تنسيق الجدول ليكون داكناً واحترافياً
        st.dataframe(
            hist_df.style.format({"performance_score": "{:.1f}"}),
            use_container_width=True
        )
    else:
        st.write("Database is currently empty. Waiting for neural signal...")

# --- 3. FINAL FOOTER ---
st.markdown(f"""
    <div style='text-align:center; margin-top:50px; padding:30px; color:#30363d; border-top:1px solid #161b22;'>
        <p style='font-family:Orbitron; font-size:0.9em; color:#00ff88; opacity:0.6; letter-spacing: 2px;'>
            LUNA CORE v10.0 | SOVEREIGN HUMAN OS
        </p>
        <p style='font-size:0.8em; font-family:JetBrains Mono;'>
            ENCRYPTED BIOMETRIC GATEWAY • {datetime.now().year} • LEAD ENG. ABDULRAHMAN
        </p>
    </div>
""", unsafe_allow_html=True)
