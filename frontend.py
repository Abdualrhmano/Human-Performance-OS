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
from typing import Dict, Any, Optional

# ==================== HUMAN PERFORMANCE OS v3.0 | ULTRA-PRO ====================
st.set_page_config(
    page_title="🧠 Human Performance OS v3.0 | Elite Health Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== ELITE DATA ARCHITECTURE ====================
DB_PATH = 'elite_performance_v3.db'

class EliteHealthEngine:
    @staticmethod
    def init_db():
        """Initialize elite database schema"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS elite_health_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                score REAL,
                sleep_hours REAL,
                focus_hours REAL,
                energy_level INTEGER,
                habit_consistency REAL,
                heart_rate INTEGER,
                steps INTEGER,
                calories REAL,
                stress_level REAL,
                recovery_score REAL,
                user_id TEXT,
                recommendation TEXT,
                encrypted_data TEXT
            )
        ''')
        conn.commit()
        conn.close()

    @staticmethod
    def get_elite_data(limit: int = 50) -> pd.DataFrame:
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query(
                f"SELECT * FROM elite_health_logs ORDER BY id DESC LIMIT {limit}", 
                conn
            )
            conn.close()
            return df.iloc[::-1].reset_index(drop=True)
        except:
            return pd.DataFrame()

# Initialize elite database
EliteHealthEngine.init_db()

# ==================== ULTRA-ELITE CYBERMEDICAL CSS v3.0 ====================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@300;400;700;900&family=JetBrains+Mono:wght@200;300;400;500;700&family=Share+Tech+Mono:wght@300;400;700&display=swap');

/* ELITE GLOBAL SYSTEM */
:root {
    --neon-primary: #00ff88;
    --neon-secondary: #00d4aa;
    --neon-glow: rgba(0,255,136,0.6);
    --glass-bg: rgba(6,26,26,0.4);
    --glass-glow: rgba(0,255,136,0.15);
}

* {
    scrollbar-width: thin !important;
    scrollbar-color: var(--neon-primary) rgba(1,2,3,0.8) !important;
}

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: rgba(1,2,3,0.9); border-radius: 4px; }
::-webkit-scrollbar-thumb { 
    background: linear-gradient(45deg, var(--neon-primary), var(--neon-secondary));
    border-radius: 4px; 
    box-shadow: 0 0 8px var(--neon-glow);
}

.stApp { 
    background: 
        radial-gradient(circle at 20% 80%, rgba(0,119,255,0.1) 0%, transparent 50%),
        radial-gradient(circle at 80% 20%, rgba(120,119,198,0.1) 0%, transparent 50%),
        radial-gradient(circle at 40% 40%, rgba(255,119,198,0.1) 0%, transparent 50%),
        linear-gradient(135deg, #010203 0%, #0a111a 50%, #010203 100%);
    background-size: 800px 800px, 400px 400px;
    animation: elitePulse 12s ease-in-out infinite;
}

@keyframes elitePulse {
    0%, 100% { background-position: 0% 50%, 0% 0%, 0% 0%, 0% 50%; }
    33% { background-position: 100% 50%, 0% 100%, 100% 0%, 100% 50%; }
    66% { background-position: 0% 0%, 100% 100%, 0% 100%, 0% 0%; }
}

/* ELITE HEADERS */
h1 { 
    font-family: 'Orbitron', monospace !important;
    font-weight: 900 !important;
    font-size: 4rem !important;
    background: linear-gradient(135deg, #00ff88, #00d4aa, #00ff88, #00d4aa);
    background-size: 300% 300%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: eliteGradient 3s ease infinite, neonFloat 6s ease-in-out infinite;
    text-shadow: none !important;
}

h2 { 
    font-family: 'Orbitron', monospace !important;
    font-weight: 700 !important;
    color: #00ff88 !important;
    text-shadow: 0 0 20px rgba(0,255,136,0.8);
    letter-spacing: 3px;
}

@keyframes eliteGradient {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

@keyframes neonFloat {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-8px); }
}

/* ELITE GLASSMORPHISM CARDS */
.elite-card, .stMetric, [data-testid="column"] > div, .st-bo {
    background: linear-gradient(145deg, rgba(6,26,26,0.6) 0%, rgba(13,17,23,0.8) 100%) !important;
    backdrop-filter: blur(20px) saturate(180%) !important;
    border: 1px solid transparent !important;
    border-image: linear-gradient(45deg, var(--neon-primary), var(--neon-secondary)) 1 !important;
    border-radius: 20px !important;
    box-shadow: 
        0 8px 32px rgba(0,0,0,0.6),
        0 0 0 1px rgba(0,255,136,0.1),
        inset 0 1px 0 rgba(255,255,255,0.1),
        0 20px 40px rgba(0,255,136,0.1);
    transition: all 0.4s cubic-bezier(0.23, 1, 0.320, 1);
    position: relative;
    overflow: hidden;
}

.elite-card::before, .stMetric::before {
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(0,255,136,0.1), transparent);
    transition: left 0.6s;
}

.elite-card:hover::before, .stMetric:hover::before { left: 100%; }

.elite-card:hover, .stMetric:hover {
    transform: translateY(-8px) scale(1.02) !important;
    box-shadow: 
        0 20px 60px rgba(0,255,136,0.25),
        0 0 0 1px rgba(0,255,136,0.3),
        inset 0 1px 0 rgba(255,255,255,0.2) !important;
}

/* ELITE BUTTONS */
.stButton > button {
    background: linear-gradient(145deg, transparent, rgba(0,255,136,0.1)) !important;
    border: 2px solid transparent !important;
    border-image: linear-gradient(45deg, var(--neon-primary), var(--neon-secondary)) 1 !important;
    border-radius: 16px !important;
    font-family: 'Orbitron', monospace !important;
    font-weight: 700 !important;
    color: var(--neon-primary) !important;
    text-transform: uppercase !important;
    letter-spacing: 2px !important;
    padding: 12px 32px !important;
    transition: all 0.4s cubic-bezier(0.23, 1, 0.320, 1) !important;
    position: relative;
    overflow: hidden;
}

.stButton > button:hover {
    background: linear-gradient(45deg, var(--neon-primary), var(--neon-secondary)) !important;
    color: #010203 !important;
    transform: translateY(-3px) !important;
    box-shadow: 0 15px 35px rgba(0,255,136,0.4) !important;
}

/* TERMINAL DISPLAY */
.ai-terminal {
    background: linear-gradient(180deg, rgba(0,8,12,0.95) 0%, rgba(6,26,26,0.98) 100%) !important;
    border: none !important;
    border-left: 4px solid var(--neon-primary) !important;
    border-radius: 0 16px 16px 0 !important;
    font-family: 'Share Tech Mono', monospace !important;
    color: #d0f7f2 !important;
    padding: 24px !important;
    position: relative;
}

.ai-terminal::after {
    content: '▮';
    position: absolute;
    right: 20px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--neon-primary);
    animation: blink 1s infinite;
}

@keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}

/* ELITE METRICS */
[data-testid="stMetricLabel"] { color: #618783 !important; font-weight: 500; }
[data-testid="stMetricValue"] { 
    color: var(--neon-primary) !important; 
    font-family: 'Orbitron', monospace !important;
    font-weight: 900 !important;
    font-size: 2.2rem !important;
    text-shadow: 0 0 15px var(--neon-glow) !important;
}

/* DATAFRAME ELITE */
.stDataFrame {
    background: rgba(6,26,26,0.6) !important;
    border: 2px solid var(--neon-primary) !important;
    border-radius: 16px !important;
}
</style>
""", unsafe_allow_html=True)

# ==================== ELITE HEADER SYSTEM ====================
def render_elite_header():
    st.markdown("""
        <div style='
            text-align: center; 
            padding: 40px 20px 20px;
            position: relative;
            overflow: hidden;
        '>
            <div style='
                position: absolute;
                top: 0; left: 0; right: 0; bottom: 0;
                background: linear-gradient(90deg, transparent 0%, rgba(0,255,136,0.03) 50%, transparent 100%);
                animation: eliteScan 4s linear infinite;
            '></div>
            <h1>⚡ Human Performance OS v3.0</h1>
            <p style='
                color: #618783; 
                font-size: 1.3rem; 
                margin: 15px 0;
                font-family: "JetBrains Mono", monospace;
                letter-spacing: 1px;
                opacity: 0.9;
            '>
                Elite Health Intelligence | Neural Optimization Matrix | Live Biometric Processing
            </p>
        </div>
    """, unsafe_allow_html=True)

render_elite_header()
st.divider()

# ==================== ELITE SIDEBAR CONTROL ====================
with st.sidebar:
    st.markdown("## 🧠 ELITE CONTROL MATRIX")
    
    # تعريف المتغير هنا يحل مشكلة NameError تماماً
    api_key_input = st.text_input(
        "🔑 Neural Access Key", 
        type="password", 
        value="luna-v4-elite",
        help="أدخل مفتاح الأمان للاتصال بـ Neural Core v4.0"
    )
    
    st.divider()
    
    # إدخالات البيانات (Sliders)
    st.markdown("### 🔬 BIOMETRIC INPUT")
    sleep_quality = st.slider("🌙 Sleep Quality", 0.0, 12.0, 7.0)
    focus_duration = st.slider("🎯 Focus Duration", 0.0, 12.0, 4.0)
    energy_level = st.slider("⚡ Energy Level", 1, 10, 5)
    stress_level = st.slider("😰 Stress Level", 0.0, 10.0, 2.0)
    
    st.divider()
    
    with st.container(border=True):
        st.markdown("### 🔬 BIOMETRIC INPUT")
        col1, col2 = st.columns(2)
        with col1:
            sleep = st.slider("🌙 Sleep Quality", 0.0, 12.0, 7.5, 0.25)
            energy = st.slider("⚡ Energy Level", 1, 10, 7)
        with col2:
            focus = st.slider("🎯 Focus Duration", 0.0, 10.0, 4.0, 0.5)
            stress = st.slider("😰 Stress Level", 0.0, 10.0, 3.0, 0.5)
        
if st.button("🚀 EXECUTE ELITE ANALYSIS", use_container_width=True):
     with st.spinner('🧬 Synchronizing with Neural Core...'):
                # 1. تجهيز البيانات من السلايدرز (تأكد من مطابقة أسماء المتغيرات لديك)
                payload = {
                    "sleep_hours": float(sleep), 
                    "focus_hours": float(focus),
                    "energy_level": int(energy),
                    "stress_level": float(stress),
                    "heart_rate": 75,   # قيم افتراضية حتى يتم ربط الساعة
                    "steps": 8000,
                    "calories": 2500.0
                }
                
                # 2. إرسال البيانات للباك-إند باستخدام الـ Token
                headers = {"Authorization": f"Bearer {api_key}"}
                
                try:
                    # تأكد أن السيرفر (main.py) يعمل على بورت 8000
                    response = requests.post(
                        f"{API_BASE_URL}/evaluate", 
                        json=payload, 
                        headers=headers,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        st.success("✅ Neural Protocol Executed | Data Matrix Updated")
                        time.sleep(1) # تعطي وقت للمستخدم لرؤية النجاح
                        st.rerun()    # الآن نقوم بإعادة التحميل لتحديث الرسوم البيانية
                    else:
                        error_detail = response.json().get('detail', 'Unknown Error')
                        st.error(f"❌ Access Denied: {error_detail}")
                
                except Exception as e:
                    st.error(f"📡 Connection Refused: Ensure Backend (main.py) is running.")


# ==================== LIVE ELITE DATA ====================
elite_df = EliteHealthEngine.get_elite_data()

# ==================== ELITE METRICS GRID ====================
if not elite_df.empty:
    latest = elite_df.iloc[-1]
    
    st.markdown("## 📊 LIVE ELITE METRICS")
    metric_cols = st.columns(6)
    
    metrics_data = [
        ("Neural Score", f"{latest['score']:.1f}", "10"),
        ("💓 HR", f"{latest['heart_rate']}", "BPM"),
        ("🏃‍♂️ Steps", f"{int(latest['steps']):,}", ""),
        ("🔥 Calories", f"{latest['calories']:.0f}", "kcal"),
        ("🌙 Sleep", f"{latest['sleep_hours']:.1f}", "h"),
        ("🛡️ Recovery", f"{latest['recovery_score']:.1f}", "%")
    ]
    
    for i, (label, value, unit) in enumerate(metrics_data):
        with metric_cols[i]:
            st.metric(label, f"{value} {unit}", delta=None)

# ==================== ELITE VISUALIZATION DASHBOARD ====================
st.markdown("### 🧠 ELITE PERFORMANCE MATRIX")
col1, col2 = st.columns([1.2, 2])

with col1:
    if not elite_df.empty:
        # Ultra Elite Gauge
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=latest['score'],
            number={'font': {'size': 42, 'color': "#00ff88", 'family': "Orbitron"}},
            gauge={
                'shape': "angular",
                'axis': {'range': [0, 10], 'tickwidth': 1},
                'bar': {'color': "#00ff88"},
                'bgcolor': "rgba(6,26,26,0.8)",
                'borderwidth': 3,
                'bordercolor': "#00ff88",
                'steps': [
                    {'range': [0, 4], 'color': '#ff4b4b'},
                    {'range': [4, 7], 'color': '#ffa500'},
                    {'range': [7, 10], 'color': '#00ff88'}
                ]
            }
        ))
        
        fig_gauge.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=320,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        # Elite AI Terminal
        st.markdown(f"""
        <div class="ai-terminal elite-card">
            <div style='color: #00ff88; font-size: 16px; font-weight: 600; margin-bottom: 12px;'>🤖 ELITE AI DIRECTIVE</div>
            <div style='color: #d0f7f2; line-height: 1.6; font-size: 14px;'>
                {latest.get('recommendation', 'Neural optimization protocol active.')}
            </div>
        </div>
        """, unsafe_allow_html=True)

with col2:
    if not elite_df.empty and len(elite_df) > 5:
        # Elite Multi-Chart Dashboard
        fig_multi = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Neural Performance', 'Activity Vector', 'Recovery Matrix', 'Stress Analysis'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]],
            vertical_spacing=0.1
        )
        
        # Performance trace
        fig_multi.add_trace(
            go.Scatter(x=elite_df.tail(20)['timestamp'], y=elite_df.tail(20)['score'],
                      mode='lines+markers', name='Score', line=dict(color='#00ff88', width=4),
                      marker=dict(size=8, symbol='circle')),
            row=1, col=1
        )
        
        # Steps trace
        fig_multi.add_trace(
            go.Scatter(x=elite_df.tail(20)['timestamp'], y=elite_df.tail(20)['steps'],
                      mode='lines', name='Steps', line=dict(color='#00d4aa', width=3)),
            row=1, col=2
        )
        
        # Recovery trace
        fig_multi.add_trace(
            go.Scatter(x=elite_df.tail(20)['timestamp'], y=elite_df.tail(20)['recovery_score'],
                      mode='lines+markers', name='Recovery', line=dict(color='#ffaa00', width=3)),
            row=2, col=1
        )
        
        # Stress trace
        fig_multi.add_trace(
            go.Scatter(x=elite_df.tail(20)['timestamp'], y=elite_df.tail(20)['stress_level'],
                      mode='lines', name='Stress', line=dict(color='#ff6b6b', width=3, dash='dash')),
            row=2, col=2
        )
        
        fig_multi.update_layout(
            height=450,
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(6,26,26,0.7)'
        )
        
        st.plotly_chart(fig_multi, use_container_width=True)

# ==================== ELITE LOG MATRIX ====================
if not elite_df.empty:
    st.markdown("## 📜 ELITE PERFORMANCE LOGS")
    log_df = elite_df.tail(12).copy()
    log_df['timestamp'] = pd.to_datetime(log_df['timestamp']).dt.strftime('%H:%M %d/%m')
    log_df['score'] = log_df['score'].round(1)
    
    st.dataframe(
        log_df[['timestamp', 'score', 'heart_rate', 'steps', 'sleep_hours', 'recovery_score']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "score": st.column_config.NumberColumn("Elite Score", format="%.1f"),
            "steps": st.column_config.NumberColumn("Steps", format="%d")
        }
    )

# ==================== ELITE FOOTER ====================
st.divider()
st.markdown("""
<div style='
    text-align: center; 
    padding: 30px; 
    color: #618783; 
    font-family: "JetBrains Mono", monospace;
    font-size: 0.95rem;
    border-top: 1px solid rgba(0,255,136,0.2);
'>
    🔒 Elite Security Architecture | 
    🧠 Neural Intelligence Core v3.0 | 
    ⚡ Real-time Biometric Processing | 
    🎯 Precision Health Optimization
</div>
""", unsafe_allow_html=True)
