# ======================================================
# SYSTEM: LUNA SOVEREIGN OS v10.0 (INTEGRATED)
# ARCHITECT: Abdulrahman (Lead Software Engineer)
# MODULE: BIOMETRIC GATEWAY & NEURAL AI ASSISTANT
# ======================================================

import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import asyncio
import random
import textwrap
from concurrent.futures import ThreadPoolExecutor

# محاولة استيراد مكتبات Snowflake Cortex
try:
    from snowflake.core import Root
    from snowflake.cortex import complete
except ImportError:
    pass

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
            }

            .stApp { background-color: var(--bg); color: #e6edf3; font-family: 'JetBrains Mono', monospace; }
            
            section[data-testid="stSidebar"] {
                background-color: var(--sidebar-bg) !important;
                border-right: 1px solid #30363d;
            }

            .main-title { 
                font-family: 'Orbitron', sans-serif; 
                color: var(--primary); 
                text-shadow: 0 0 20px rgba(0, 255, 136, 0.4); 
                font-size: 3em; 
                text-align: center; 
                margin-bottom: 5px; 
            }

            /* تخصيص التبويبات Tabs لتناسب التصميم */
            .stTabs [data-baseweb="tab-list"] { gap: 10px; }
            .stTabs [data-baseweb="tab"] {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px 8px 0 0;
                padding: 10px 20px;
                color: #8b949e;
            }
            .stTabs [aria-selected="true"] {
                color: var(--primary) !important;
                border-color: var(--primary) !important;
            }

            .stSlider [data-baseweb="slider"] div { background-color: var(--accent-red) !important; }
            
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
            }
            </style>
        """, unsafe_allow_html=True)

# 2. CORE SYSTEM & AI BRIDGE
class CoreBridge:
    DB_PATH = 'human_performance_v2.db'
    MODEL = "claude-3-5-sonnet"
    EXECUTOR = ThreadPoolExecutor(max_workers=5)
    
    @staticmethod
    def init_db():
        conn = sqlite3.connect(CoreBridge.DB_PATH)
        conn.execute('''CREATE TABLE IF NOT EXISTS performance_logs 
                        (timestamp TEXT, performance_score REAL, hr INTEGER, steps INTEGER)''')
        conn.commit()
        conn.close()

    @staticmethod
    def get_snowflake_session():
        try: return st.connection("snowflake").session()
        except: return None

    @staticmethod
    def get_luna_verdict(score, hr, steps):
        if score >= 80: status = "🔥 أداؤك في القمة! النظام في حالة تناغم كامل."
        elif score >= 50: status = "🟢 وضع مستقر. حافظ على روتينك الحالي."
        else: status = "🔴 تراجع ملحوظ في الأداء الحيوي."
        return f"{status}\n\nالنبض: {hr} BPM | الخطوات: {steps}"

# 3. INITIALIZATION
SystemUI.setup()
CoreBridge.init_db()

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR CONTROL CENTER ---
with st.sidebar:
    st.markdown("<h2 style='color:#00ff88; font-family:Orbitron;'>🛡️ LUNA CORE</h2>", unsafe_allow_html=True)
    auth_token = st.text_input("NEURAL ACCESS KEY", type="password", value="A7-X9-RAG-CORE-V10")
    
    st.divider()
    st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>📡 TELEMETRY</h3>", unsafe_allow_html=True)
    hr_val = st.slider("💓 Heart Rate", 40, 190, 75)
    step_val = st.number_input("👟 Daily Steps", value=6000)
    init_sync = st.button("🚀 INITIATE SYSTEM SYNC")

    if init_sync:
        with st.spinner("Processing..."):
            score = round(random.uniform(30, 95), 1)
            st.session_state.current_score = score
            st.session_state.last_verdict = CoreBridge.get_luna_verdict(score, hr_val, step_val)
            conn = sqlite3.connect(CoreBridge.DB_PATH)
            conn.execute("INSERT INTO performance_logs VALUES (?, ?, ?, ?)",
                         (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), score, hr_val, step_val))
            conn.commit()
            conn.close()
            st.rerun()

# --- MAIN DASHBOARD ---
st.markdown("<h1 class='main-title'>LUNA SOVEREIGN OS</h1>", unsafe_allow_html=True)

# دمج النظامين عبر التبويبات (Tabs)
tab_bio, tab_ai = st.tabs(["📊 BIOMETRIC DASHBOARD", "🤖 NEURAL AI ASSISTANT"])

with tab_bio:
    col_l, col_r = st.columns([1, 1.5], gap="large")
    with col_l:
        st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>🧠 Live Analysis</h3>", unsafe_allow_html=True)
        display_score = st.session_state.get('current_score', 0.0)
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number", value = display_score,
            gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#00ff88"}, 'bgcolor': "rgba(0,0,0,0)"}
        ))
        fig_gauge.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_r:
        st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>📈 Performance Timeline</h3>", unsafe_allow_html=True)
        conn = sqlite3.connect(CoreBridge.DB_PATH)
        hist_df = pd.read_sql_query("SELECT * FROM performance_logs ORDER BY timestamp DESC LIMIT 15", conn)
        conn.close()
        if not hist_df.empty:
            fig_line = px.area(hist_df.iloc[::-1], x='timestamp', y='performance_score')
            fig_line.update_traces(line_color='#00ff88', fillcolor='rgba(0, 255, 136, 0.1)')
            fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
            st.plotly_chart(fig_line, use_container_width=True)

with tab_ai:
    st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>✨ Neural Link Interface</h3>", unsafe_allow_html=True)
    
    # عرض تاريخ المحادثة
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # مدخل الشات المرتبط بـ Snowflake Cortex
    if user_query := st.chat_input("Connect with LUNA Intelligence..."):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)
        
        with st.chat_message("assistant"):
            session = CoreBridge.get_snowflake_session()
            if session:
                with st.spinner("Thinking..."):
                    # منطق بناء البرومبت من الكود الثاني
                    prompt = f"<question>{user_query}</question>"
                    response_gen = complete(CoreBridge.MODEL, prompt, stream=True, session=session)
                    response = st.write_stream(response_gen)
            else:
                response = "⚠️ Connection to Snowflake not established. Please check your secrets.toml file."
                st.info(response)
            
            st.session_state.messages.append({"role": "assistant", "content": response})

# --- FOOTER ---
st.markdown(f"""
    <div style='text-align:center; margin-top:50px; padding:30px; color:#30363d; border-top:1px solid #161b22;'>
        <p style='font-family:Orbitron; font-size:0.9em; color:#00ff88; opacity:0.6;'>LUNA CORE v10.0 | SENIOR ENG. ABDULRAHMAN</p>
    </div>
""", unsafe_allow_html=True)
