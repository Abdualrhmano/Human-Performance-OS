import streamlit as st
import requests
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# 1. إعدادات الصفحة الفائقة
st.set_page_config(
    page_title="LUNA Sovereign OS | Performance Core",
    page_icon="🧠",
    layout="wide"
)

# 2. هندسة التصميم (Custom CSS) - نظام الهوية البصرية
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    
    html, body, [data-testid="stSidebar"] { font-family: 'JetBrains Mono', monospace; }
    
    .stApp { background-color: #05070a; }
    
    /* كروت البيانات */
    .metric-card {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
        border: 1px solid #30363d;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,255,136,0.05);
        transition: transform 0.3s;
    }
    .metric-card:hover { transform: translateY(-5px); border-color: #00ff88; }
    
    /* الـ Button الاحترافي */
    .stButton>button {
        width: 100%;
        background: transparent;
        color: #00ff88;
        border: 2px solid #00ff88;
        border-radius: 50px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 2px;
        padding: 10px 20px;
        transition: all 0.4s;
    }
    .stButton>button:hover {
        background: #00ff88;
        color: #000;
        box-shadow: 0 0 20px #00ff88;
    }
    
    /* تحسين النصوص */
    h1, h2, h3 { color: #00ff88 !important; }
    .ai-box {
        background: rgba(0, 255, 136, 0.03);
        border-left: 5px solid #00ff88;
        padding: 15px;
        border-radius: 5px;
        font-style: italic;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. جلب البيانات التاريخية
def load_db_data():
    try:
        conn = sqlite3.connect('performance.db')
        df = pd.read_sql_query("SELECT * FROM performance_logs ORDER BY id DESC LIMIT 15", conn)
        conn.close()
        return df
    except: return pd.DataFrame()

# --- Header ---
st.markdown("<h1 style='text-align: center;'>⚡ LUNA SOVEREIGN OS</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8b949e;'>Neural Performance Analytics & Biometric Intelligence</p>", unsafe_allow_html=True)
st.divider()

# --- Layout: Sidebar Control Panel ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2103/2103633.png", width=80)
    st.markdown("### 🛠️ SYSTEM CONTROLS")
    
    with st.expander("INPUT STREAM", expanded=True):
        sleep = st.select_slider("🌙 Sleep Quality", options=list(range(0, 13)), value=7)
        focus = st.slider("🎯 Deep Focus (Hrs)", 0.0, 12.0, 4.0)
        energy = st.select_slider("⚡ Energy Index", options=list(range(1, 11)), value=6)
        consistency = st.slider("🔄 Habit Sync", 0.0, 1.0, 0.7)
    
    api_key = st.text_input("🔑 API PROTOCOL", value="demo-key", type="password")
    execute = st.button("RUN NEURAL ANALYSIS")

# --- Main Dashboard Area ---
df_history = load_db_data()

col_main, col_side = st.columns([2, 1])

with col_main:
    st.markdown("### 📈 ANALYTICS TIMELINE")
    if not df_history.empty:
        # رسم بياني متطور (Area Chart)
        fig = px.area(df_history.iloc[::-1], x='timestamp', y='score', 
                      title="Performance Drift Over Time")
        fig.update_traces(line_color='#00ff88', fillcolor='rgba(0, 255, 136, 0.1)')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                          font_color='#8b949e', xaxis_showgrid=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("System standby. Awaiting first data stream...")

    st.markdown("### 📜 SYSTEM LOGS (SQLite)")
    st.dataframe(df_history[['timestamp', 'score', 'recommendation']].head(5), 
                 use_container_width=True, hide_index=True)

with col_side:
    st.markdown("### 🧠 ENGINE STATUS")
    
    if execute:
        with st.spinner("Processing through Gemini AI..."):
            payload = {"sleep_hours": sleep, "focus_hours": focus, "energy_level": energy, "habit_consistency": consistency}
            try:
                res = requests.post("http://localhost:8000/evaluate", json=payload, headers={"x-api-key": api_key})
                if res.status_code == 200:
                    data = res.json()
                    
                    # العداد (Gauge)
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = data['performance_score'],
                        gauge = {'axis': {'range': [0, 10]}, 'bar': {'color': "#00ff88"}},
                        title = {'text': "CURRENT SCORE", 'font': {'size': 18, 'color': '#00ff88'}}
                    ))
                    fig_gauge.update_layout(height=250, paper_bgcolor='rgba(0,0,0,0)', font_color='white', margin=dict(l=20,r=20,t=40,b=20))
                    st.plotly_chart(fig_gauge, use_container_width=True)
                    
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4>🤖 AI RECOMMENDATION</h4>
                        <p class="ai-box">{data['recommendation']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else: st.error("Access Denied: Check Protocol Key")
            except: st.error("Engine Offline: Start main.py")
    else:
        st.markdown("<div style='text-align: center; padding: 50px; color: #30363d;'>READY FOR INPUT</div>", unsafe_allow_html=True)

st.divider()
st.markdown("<p style='text-align: center; color: #30363d; font-size: 0.8em;'>LUNA ARCHITECTURE | AES-256 ENCRYPTED | SQLITE PERSISTENCE</p>", unsafe_allow_html=True)
