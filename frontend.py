import streamlit as st
import requests
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import json
import time
import numpy as np

# ==================== HUMAN PERFORMANCE OS v2.0 ====================
st.set_page_config(
    page_title="🧠 Human Performance OS v2.0 | Biometric Analytics Core",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== ULTRA-ADVANCED HEALTH CYBERPUNK CSS ====================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@200;300;400;500;700&family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');

/* CORE MATRIX SYSTEM */
* { scrollbar-width: thin; scrollbar-color: #00ff88 #010203; }
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #010203; }
::-webkit-scrollbar-thumb { background: #00ff88; border-radius: 4px; }

/* GLOBAL HYPER-MATRIX */
html, body, [data-testid="stSidebar"] { 
    font-family: 'JetBrains Mono', monospace; 
    font-weight: 300; 
    color: #d0f7f2; 
    background: linear-gradient(135deg, #010203 0%, #0a0f14 50%, #010203 100%);
}

.stApp { 
    background: linear-gradient(135deg, #010203 0%, #0a0f14 50%, #010203 100%);
    background-size: 400% 400%;
    animation: matrixPulse 8s ease infinite;
}

/* ANIMATED PULSE EFFECT */
@keyframes matrixPulse {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

/* HYPER-CARDS v2.0 */
.st-bo, .block-container { 
    background: linear-gradient(145deg, rgba(6, 26, 26, 0.85) 0%, rgba(13, 17, 23, 0.9) 100%) !important;
    border: 1px solid transparent;
    background-clip: padding-box;
    border-image: linear-gradient(45deg, #00ff88, #00d4aa, #00ff88) 1 !important;
    border-radius: 16px; 
    box-shadow: 
        0 0 20px rgba(0,255,136,0.15),
        0 0 40px rgba(0,255,136,0.08),
        inset 0 1px 0 rgba(255,255,255,0.1);
    backdrop-filter: blur(10px);
    transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.st-bo:hover { 
    transform: translateY(-4px);
    box-shadow: 
        0 12px 40px rgba(0,255,136,0.25),
        0 0 60px rgba(0,255,136,0.15) !important;
}

/* ULTRA BUTTONS v2.0 */
.stButton > button {
    width: 100%; height: 50px;
    background: linear-gradient(45deg, transparent 0%, rgba(0,255,136,0.1) 100%);
    color: #00ff88 !important;
    border: 2px solid transparent;
    border-image: linear-gradient(45deg, #00ff88, #00d4aa) 1;
    border-radius: 25px;
    font-family: 'Orbitron', monospace !important;
    font-weight: 700 !important;
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 2px;
    position: relative;
    overflow: hidden;
    transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.stButton > button:hover {
    background: linear-gradient(45deg, #00ff88, #00d4aa) !important;
    color: #010203 !important;
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0,255,136,0.4);
}

.stButton > button:active {
    transform: translateY(0);
}

/* NEON HEADERS */
h1, h2, h3, h4, h5, h6 { 
    color: #00ff88 !important; 
    text-transform: uppercase; 
    letter-spacing: 2px;
    text-shadow: 0 0 10px rgba(0,255,136,0.5);
    font-family: 'Orbitron', monospace !important;
    font-weight: 700 !important;
}

/* AI INSIGHT TERMINAL */
.ai-terminal {
    background: linear-gradient(180deg, rgba(0,8,12,0.95) 0%, rgba(6,26,26,0.98) 100%);
    border: 2px solid #00ff88;
    border-radius: 12px;
    padding: 20px;
    font-family: 'Share Tech Mono', monospace;
    color: #00ff88;
    box-shadow: 
        0 0 20px rgba(0,255,136,0.2),
        inset 0 0 20px rgba(0,255,136,0.05);
    position: relative;
    overflow: hidden;
}

.ai-terminal::before {
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(0,255,136,0.1), transparent);
    animation: scanline 3s infinite;
}

@keyframes scanline {
    0% { left: -100%; }
    100% { left: 100%; }
}

/* METRIC DISPLAY */
.metric-container {
    background: rgba(0,255,136,0.03);
    border: 1px solid rgba(0,255,136,0.3);
    border-radius: 12px;
    padding: 20px;
    margin: 10px 0;
}

/* ENHANCED DATAFRAME */
.stDataFrame {
    border: 2px solid #00ff88 !important;
    border-radius: 12px !important;
    background: rgba(6,26,26,0.8) !important;
}

/* SLIDER ENHANCEMENT */
.stSlider > div > div > div > div > div {
    background: linear-gradient(45deg, #00ff88, #00d4aa) !important;
}
</style>
""", unsafe_allow_html=True)

# ==================== ADVANCED DATA LAYER ====================
DB_PATH = 'human_performance_v2.db' # اسم قاعدة البيانات الجديدة

class LunaDataEngine:
    @staticmethod
    def get_latest_data(limit: int = 20) -> pd.DataFrame:
        try:
            conn = sqlite3.connect(DB_PATH)
            # تحديث الاستعلام ليشمل حقول الساعة الذكية الجديدة
            query = f"""
                SELECT 
                    id, timestamp, score, sleep_hours, focus_hours, 
                    energy_level, habit_consistency, heart_rate, steps, calories, 
                    user_id, recommendation, encrypted_data
                FROM health_logs 
                ORDER BY id DESC LIMIT {limit}
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df.iloc[::-1].reset_index(drop=True)
        except Exception as e:
            print(f"Data Read Warning: {e}")
            return pd.DataFrame()

# ==================== LUNA CORE HEADER ====================
def render_header():
    st.markdown("""
        <div style='text-align: center; padding: 30px 20px;'>
            <h1 style='
                font-size: 3.5rem; 
                background: linear-gradient(45deg, #00ff88, #00d4aa, #00ff88);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                text-shadow: 0 0 30px rgba(0,255,136,0.5);
                margin: 0;
                animation: neonGlow 2s ease-in-out infinite alternate;
            '>
                ⚡ Human Performance OS v2.0
            </h1>
            <p style='
                color: #618783; 
                font-size: 1.2rem; 
                margin: 10px 0 0 0;
                font-family: JetBrains Mono;
                letter-spacing: 1px;
            '>
                Biometric Analytics & Health Optimization Core | AI-Driven Metrics
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <style>
        @keyframes neonGlow {
            from { filter: drop-shadow(0 0 5px #00ff88); }
            to { filter: drop-shadow(0 0 20px #00ff88); }
        }
        </style>
    """, unsafe_allow_html=True)

# ==================== MAIN EXECUTION ====================
render_header()
st.divider()

# ==================== HYPER-CONTROL PANEL (WITH SMARTWATCH INPUT) ====================
with st.sidebar:
    st.markdown("## 🧠 NEURAL CONTROL MATRIX")
    
    # Protocol Container
    with st.container(border=True):
        st.markdown("### 🔬 HEALTH METRICS INPUT PROTOCOL")
        
        col1, col2 = st.columns(2)
        with col1:
            sleep = st.select_slider("🌙 Sleep Cycle", options=range(0, 13), value=8)
            energy = st.select_slider("⚡ Energy Vector", options=range(1, 11), value=7)
            hr = st.number_input("💓 Heart Rate (BPM)", 40, 220, 75, 1) # نبضات القلب
        with col2:
            focus = st.slider("🎯 Neural Focus", 0.0, 12.0, 4.0, 0.5)
            consistency = st.slider("🔄 Synaptic Consistency", 0.0, 1.0, 0.8, 0.05)
            steps = st.number_input("🏃 Steps Count", 0, 50000, 8000, 100) # عدد الخطوات
            calories = st.number_input("🔥 Calories (kcal)", 0, 5000, 350, 10) # السعرات

        st.markdown("### 🔐 AUTHENTICATION VECTOR")
        api_key = st.text_input("🔑 Neural API Key", type="password", value="luna-v2-demo")
        
        st.markdown("---")
        analyze_btn = st.button("🚀 EXECUTE NEURAL ANALYSIS", type="primary", use_container_width=True)

# ==================== CORE DATA ENGINE ====================
history_df = LunaDataEngine.get_latest_data()

if analyze_btn:
    with st.spinner('🔮 Accessing Human Performance Neural Core... Synchronizing biometric matrix...'):
        time.sleep(1.8)
        
        # Payload المعدل ليشمل حقول الساعة الذكية الجديدة
        payload = {
            "sleep_hours": sleep, 
            "focus_hours": focus, 
            "energy_level": energy, 
            "habit_consistency": consistency,
            "heart_rate": hr,
            "steps": steps,
            "calories": calories
        }
        headers = {"x-api-key": api_key}
        
        try:
            response = requests.post("http://localhost:8000/evaluate", json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                history_df = LunaDataEngine.get_latest_data()
                st.balloons()
                st.success("✅ Neural Protocol Executed | Health Data Matrix Updated")
            else:
                st.error("❌ Authentication Vector Invalid | Health Core Access Denied")
        except requests.exceptions.RequestException:
            st.error("🌐 Health Backend Failure | Verify human_performance_backend.py is operational")

# ==================== HYPER-VISUALIZATION LAYOUT (HEALTH DASHBOARD) ====================
col_left, col_center, col_right = st.columns([1, 1.2, 1.5])

with col_left:
    st.markdown("## 🧠 PERFORMANCE GAUGE")
    
    if not history_df.empty:
        latest = history_df.iloc[-1]
        
        # Advanced 3D Gauge
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=latest['score'],
            number={'font': {'color': "#00ff88", 'size': 28}},
            delta={'reference': 7.0, 'increasing': {'color': "#00ff88"}},
            gauge={
                'axis': {'range': [None, 10], 'tickwidth': 1, 'tickcolor': "#00ff88"},
                'bar': {'color': "#00ff88", 'thickness': 0.15},
                'bgcolor': "rgba(6,26,26,0.8)",
                'borderwidth': 2,
                'bordercolor': "#00ff88",
                'steps': [
                    {'range': [0, 4], 'color': 'rgba(255,75,75,0.6)'},
                    {'range': [4, 7], 'color': 'rgba(255,165,0,0.6)'},
                    {'range': [7, 10], 'color': 'rgba(0,255,136,0.8)'}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': latest['score']
                }
            }
        ))
        
        # تصليح العنوان ليكون في سطر واحد لتجنب خطأ الـ f-string
        gauge_title = f"HEALTH SCORE <br>Matrix: {latest['score']:.1f}/10"
        
        fig_gauge.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': "#d0f7f2", 'family': "Orbitron"},
            title={'text': gauge_title, 'font': {'size': 16, 'color': '#00ff88'}, 'y': 0.75},
            height=300
        )
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        # Neural Recommendation Terminal (صندوق نصيحة الصحة بالذكاء الاصطناعي)
        with st.container():
            st.markdown(f"""
            <div class="ai-terminal">
                <div style='color: #00ff88; font-weight: 500; margin-bottom: 10px;'>🤖 HEALTH OS AI INSIGHT</div>
                <div style='color: #d0f7f2; line-height: 1.5; font-size: 14px;'>
                    {latest['recommendation']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        # إضافة الـ Metrics الحية في col_left
        st.markdown(f"""
        <div style="display: flex; justify-content: space-around; background: rgba(0,255,136,0.05); padding: 10px; border-radius: 10px; border: 1px solid rgba(0,255,136,0.3); margin-top: 15px;">
            <div style="text-align: center;"><b>BPM</b><br><span style="color:#00ff88; font-size:20px;">{int(latest['heart_rate'])}</span></div>
            <div style="text-align: center;"><b>Steps</b><br><span style="color:#00ff88; font-size:20px;">{latest['steps']}</span></div>
            <div style="text-align: center;"><b>Kcal</b><br><span style="color:#00ff88; font-size:20px;">{latest['calories']}</span></div>
        </div>
        """, unsafe_allow_html=True)

with col_center:
    st.markdown("## 📊 BIOMETRIC TRENDS")
    if not history_df.empty:
        # Multi-trace Advanced Chart (HEALTH VERSION)
        fig_trends = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Performance Matrix (Health Score)', 'Activity Consistency (Steps)'),
            vertical_spacing=0.12,
            row_heights=[0.7, 0.3]
        )
        
        # الرسم البياني للسكور
        fig_trends.add_trace(
            go.Scatter(
                x=history_df['timestamp'],
                y=history_df['score'],
                mode='lines+markers',
                name='Health Score',
                line=dict(color='#00ff88', width=4),
                marker=dict(size=10, color='#00ff88', line=dict(width=2))
            ),
            row=1, col=1
        )
        
        # الرسم البياني للخطوات
        fig_trends.add_trace(
            go.Scatter(
                x=history_df['timestamp'],
                y=history_df['steps'],
                mode='lines+markers',
                name='Daily Steps',
                line=dict(color='#00d4aa', width=3, dash='dash')
            ),
            row=2, col=1
        )
        
        fig_trends.update_layout(
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(6, 26, 26, 0.6)',
            font={'color': "#d0f7f2"},
            showlegend=True,
            legend=dict(
                yanchor="top", y=0.99, xanchor="left", x=0.01,
                bgcolor="rgba(6,26,26,0.8)", bordercolor="#00ff88"
            )
        )
        
        st.plotly_chart(fig_trends, use_container_width=True)

with col_right:
    st.markdown("## 📜 HEALTH LOG MATRIX")
    if not history_df.empty:
        # Enhanced formatted dataframe
        display_df = history_df.copy()
        display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%H:%M %m/%d')
        display_df['score'] = display_df['score'].round(1)
        
        # تعديل الأعمدة المعروضة لتشمل بيانات الساعة الجديدة
        st.dataframe(
            display_df[[
                'timestamp', 'score', 'sleep_hours', 
                'focus_hours', 'heart_rate', 'steps', 'calories'
            ]].tail(10),
            use_container_width=True,
            hide_index=True,
            column_config={
                "score": st.column_config.NumberColumn(
                    "Health Score", format="%.1f", 
                    help="Calculated biometric performance metric"
                ),
                "steps": st.column_config.NumberColumn(
                    "Total Steps", format="%d", help="Steps counted from smartwatch"
                )
            }
        )

# ==================== FOOTER ====================
st.divider()
st.markdown("""
    <div style='text-align: center; padding: 20px; color: #30363d; font-family: JetBrains Mono;'>
        🔒 Secure Health Architecture | 
        🧠 AI-Driven Analytics Engine | 
        💾 SQLite v2 Persistence Layer | 
        ⚡ Real-time Smartwatch Processing
    </div>
""", unsafe_allow_html=True)
