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
    def __init__(self, model="claude-3-5-sonnet"):
        self.model = model

    def get_response(self, prompt, history):
        try:
            session = st.connection("snowflake").session()
            full_prompt = f"System: You are LUNA AI, the neural core of the Human Performance OS. Answer Senior Engineer Abdulrahman briefly and professionally.\n"
            for msg in history[-5:]:
                full_prompt += f"{msg['role']}: {msg['content']}\n"
            full_prompt += f"User: {prompt}"
            return complete(self.model, full_prompt, stream=True, session=session)
        except Exception as e:
            return f"Neural Link Error: {str(e)}"

    def render_ui(self):
        st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>🤖 Neural Chat Link</h3>", unsafe_allow_html=True)
        if "messages" not in st.session_state:
            st.session_state.messages = []

        chat_container = st.container(height=400)
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if prompt := st.chat_input("Send command to LUNA OS..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant"):
                    response_gen = self.get_response(prompt, st.session_state.messages)
                    full_response = st.write_stream(response_gen)
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
            }

            /* إعدادات الخلفية العامة والخطوط */
            .stApp { background-color: var(--bg); color: #e6edf3; font-family: 'JetBrains Mono', monospace; }
            
            /* تصميم القائمة الجانبية (Sidebar) مطابق للصورة */
            section[data-testid="stSidebar"] {
                background-color: var(--sidebar-bg) !important;
                border-right: 1px solid #30363d;
            }

            /* العنوان الرئيسي المتوهج */
            .main-title { 
                font-family: 'Orbitron', sans-serif; 
                color: var(--primary); 
                text-shadow: 0 0 20px rgba(0, 255, 136, 0.4); 
                font-size: 3em; 
                text-align: center; 
                margin-bottom: 5px; 
            }

            /* تخصيص السلايدرز للون الأحمر */
            .stSlider [data-baseweb="slider"] div { background-color: var(--accent-red) !important; }
            
            /* بطاقة LUNA AI Verdict */
            .luna-card {
                background: rgba(0, 255, 136, 0.05);
                border: 1px solid var(--primary);
                border-left: 6px solid var(--primary);
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.5);
            }
            
            /* تصميم الأزرار التقني */
            .stButton > button {
                background-color: #21262d !important;
                color: white !important;
                border: 1px solid #30363d !important;
                border-radius: 8px !important;
                font-family: 'Orbitron', sans-serif !important;
                transition: 0.3s ease;
                width: 100%;
            }
            .stButton > button:hover {
                border-color: var(--primary) !important;
                color: var(--primary) !important;
                box-shadow: 0 0 15px rgba(0, 255, 136, 0.2);
            }
            </style>
        """, unsafe_allow_html=True)

# 2. CORE SYSTEM BRIDGE
class CoreBridge:
    DB_PATH = 'human_performance_v2.db'
    
    @staticmethod
    def init_db():
        conn = sqlite3.connect(CoreBridge.DB_PATH)
        conn.execute('''CREATE TABLE IF NOT EXISTS performance_logs 
                        (timestamp TEXT, performance_score REAL, hr INTEGER, steps INTEGER)''')
        conn.commit()
        conn.close()

    @staticmethod
    def save_log(score, hr, steps):
        conn = sqlite3.connect(CoreBridge.DB_PATH)
        conn.execute("INSERT INTO performance_logs (timestamp, performance_score, hr, steps) VALUES (?, ?, ?, ?)",
                       (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), score, hr, steps))
        conn.commit()
        conn.close()

    @staticmethod
    def get_luna_verdict(score, hr, steps):
        hr_advice = "🟢 نبض مستقر"
        if hr > 110: hr_advice = "⚠️ تنبيه: معدل النبض مرتفع جداً؛ يرجى ممارسة تمارين التنفس."
        elif hr < 50: hr_advice = "💤 تنبيه: النبض منخفض؛ قد تكون في حالة إرشادية أو خمول."

        activity_advice = "🏃 استمر في التحرك لكسر حالة الخمول." if steps < 3000 else "🌟 معدل نشاطك الحركي جيد جداً."

        if score >= 80: status = "🔥 أداؤك في القمة! النظام في حالة تناغم كامل."
        elif score >= 50: status = "🟢 وضع مستقر. حافظ على روتينك الحالي مع شرب الماء."
        else: status = "🔴 تراجع ملحوظ في الأداء الحيوي. نظام LUNA يوصي بالراحة الآن."

        return f"{status}\n\n{hr_advice}\n{activity_advice}"

    @staticmethod
    def fetch_historical_data():
        try:
            conn = sqlite3.connect(CoreBridge.DB_PATH)
            df = pd.read_sql_query("SELECT * FROM performance_logs ORDER BY timestamp DESC LIMIT 15", conn)
            conn.close()
            return df
        except: return pd.DataFrame()

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
        fig_gauge.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        if display_score < 50:
            st.markdown("<p style='text-align:center; color:#ff4b4b; font-weight:bold;'>🔴 CRITICAL: تراجع في الأداء الحيوي</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='text-align:center; color:#00ff88; font-weight:bold;'>🟢 OPTIMAL: حالة النظام مستقرة</p>", unsafe_allow_html=True)

    with col_right:
        st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>📈 Performance Timeline</h3>", unsafe_allow_html=True)
        
        hist_df = CoreBridge.fetch_historical_data()
        
        if not hist_df.empty:
            fig_line = px.area(hist_df.iloc[::-1], x='timestamp', y='performance_score')
            fig_line.update_traces(
                line_color='#00ff88', 
                fillcolor='rgba(0, 255, 136, 0.1)', 
                markers=True,
                line_width=3
            )
            fig_line.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                height=350,
                xaxis=dict(showgrid=True, gridcolor='#1f2937', title="Time Protocol"),
                yaxis=dict(showgrid=True, gridcolor='#1f2937', title="Score"),
                font={'color': "white"}
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No telemetry logs found. Initiate Sync to populate data.")

with tab_ai:
    # استدعاء كلاس الدردشة (تأكد أنك وضعت تعريف الكلاس في أول الملف)
    luna_chat = LUNAChat()
    luna_chat.render_ui()
    
    # رسالة حالة العداد (تحت العداد مباشرة)
    if display_score < 50:
        st.markdown("<p style='text-align:center; color:#ff4b4b; font-weight:bold;'>🔴 CRITICAL: تراجع في الأداء الحيوي</p>", unsafe_allow_html=True)
    else:
        st.markdown("<p style='text-align:center; color:#00ff88; font-weight:bold;'>🟢 OPTIMAL: حالة النظام مستقرة</p>", unsafe_allow_html=True)

with col_right:
    st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>📈 Performance Timeline</h3>", unsafe_allow_html=True)
    
    # جلب البيانات التاريخية من قاعدة البيانات
    hist_df = CoreBridge.fetch_historical_data()
    
    if not hist_df.empty:
        # رسم بياني مساحي (Area Chart) يشبه الصورة 2
        fig_line = px.area(hist_df.iloc[::-1], x='timestamp', y='performance_score')
        fig_line.update_traces(
            line_color='#00ff88', 
            fillcolor='rgba(0, 255, 136, 0.1)', 
            markers=True,
            line_width=3
        )
        fig_line.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)', 
            height=350,
            xaxis=dict(showgrid=True, gridcolor='#1f2937', title="Time Protocol"),
            yaxis=dict(showgrid=True, gridcolor='#1f2937', title="Score"),
            font={'color': "white"}
        )
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("No telemetry logs found. Initiate Sync to populate data.")

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
