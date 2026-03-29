# ======================================================
# SYSTEM: Human Performance OS v2.0
# MODULE: STREAMLIT FRONTEND BRIDGE (UI/UX)
# ======================================================

import streamlit as st
import requests
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# ------------------------------------------------------
# 1. CORE CONFIGURATION & STYLING (هندسة الهوية البصرية)
# ------------------------------------------------------
class UIStyle:
    @staticmethod
    def apply():
        st.set_page_config(page_title="Human Performance OS v2.0", page_icon="🧠", layout="wide")
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono&display=swap');
            
            html, body, [data-testid="stSidebar"] { font-family: 'JetBrains Mono', monospace; }
            .stApp { background-color: #05070a; color: #e6edf3; }
            
            /* Glassmorphism Cards */
            .metric-card {
                background: rgba(22, 27, 34, 0.8);
                border: 1px solid #30363d;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 10px;
                border-left: 4px solid #00ff88;
            }
            
            /* Professional Header */
            .main-header {
                background: linear-gradient(90deg, #00ff88, #00bd68);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-family: 'Orbitron', sans-serif;
                font-size: 3em;
                font-weight: bold;
                text-align: center;
                margin-bottom: 0px;
            }
            
            /* Sidebar Styling */
            [data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
            
            /* AI Insight Box */
            .ai-box {
                background: rgba(0, 255, 136, 0.05);
                border: 1px solid rgba(0, 255, 136, 0.2);
                padding: 15px;
                border-radius: 8px;
                color: #00ff88;
                font-size: 0.95em;
                line-height: 1.6;
            }
            </style>
        """, unsafe_allow_html=True)

# ------------------------------------------------------
# 2. DATA ARCHITECT (إدارة البيانات المحلية)
# ------------------------------------------------------
class DataVault:
    @staticmethod
    def fetch_history():
        """جلب البيانات من قاعدة البيانات التي ينشئها الباك إند"""
        try:
            # نتصل بنفس قاعدة البيانات التي يستخدمها الـ Backend
            conn = sqlite3.connect('human_performance_v2.db')
            df = pd.read_sql_query("""
                SELECT timestamp, performance_score, ai_recommendation 
                FROM performance_logs ORDER BY timestamp DESC LIMIT 10
            """, conn)
            conn.close()
            return df
        except:
            return pd.DataFrame()

# ------------------------------------------------------
# 3. BACKEND BRIDGE (الربط مع API الباك إند)
# ------------------------------------------------------
class BackendBridge:
    BASE_URL = "http://localhost:8000/api/v2"

    @staticmethod
    def sync_data(token, metrics):
        """إرسال البيانات للباك إند واستلام التحليل"""
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.post(f"{BackendBridge.BASE_URL}/performance/sync", 
                                     json=metrics, headers=headers)
            return response.json() if response.status_code == 200 else None
        except:
            return None

# ------------------------------------------------------
# 4. DASHBOARD RENDERER (بناء الواجهة)
# ------------------------------------------------------
UIStyle.apply()

# --- SIDEBAR: AUTH & INPUT ---
with st.sidebar:
    st.markdown("<h2 style='color:#00ff88'>🛡️ SYSTEM AUTH</h2>", unsafe_allow_html=True)
    access_token = st.text_input("ACCESS_TOKEN", type="password", help="ضع توكن الدخول هنا")
    
    st.divider()
    st.markdown("<h2 style='color:#00ff88'>📡 SENSOR INPUTS</h2>", unsafe_allow_html=True)
    
    hr = st.slider("💓 Heart Rate (BPM)", 40, 160, 75)
    steps = st.number_input("👟 Total Steps", value=8000)
    screen = st.slider("📱 Screen Time (Hrs)", 0.0, 16.0, 4.0)
    sleep = st.slider("🌙 Sleep Duration (Hrs)", 0.0, 12.0, 7.5)
    
    sync_btn = st.button("EXECUTE NEURAL SYNC")

# --- MAIN PAGE: VISUALIZATION ---
st.markdown("<h1 class='main-header'>LUNA SOVEREIGN OS</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#8b949e'>Neural-Biometric Synchronization Protocol v2.0</p>", unsafe_allow_html=True)

col_charts, col_status = st.columns([2, 1])

with col_charts:
    st.markdown("### 📊 Performance Timeline")
    history_df = DataVault.fetch_history()
    
    if not history_df.empty:
        # رسم بياني احترافي
        fig = px.line(history_df, x='timestamp', y='performance_score', markers=True)
        fig.update_traces(line_color='#00ff88', line_width=3, marker=dict(size=10, color='#fff'))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#8b949e', xaxis_showgrid=False, yaxis_showgrid=True,
            yaxis=dict(gridcolor='#161b22'), margin=dict(l=0, r=0, t=20, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("### 📜 Recent Logs")
        st.table(history_df.head(5))
    else:
        st.info("System Standby: Connect to human_performance_v2.db to see logs.")

with col_status:
    st.markdown("### 🧠 Live Analysis")
    
    if sync_btn:
        if not access_token:
            st.error("Missing Authentication Token")
        else:
            with st.spinner("Synchronizing with LUNA Brain..."):
                metrics = {
                    "heart_rate": hr,
                    "steps": steps,
                    "screen_time": screen,
                    "sleep_hours": sleep
                }
                result = BackendBridge.sync_data(access_token, metrics)
                
                if result:
                    # العداد الدائري (Gauge)
                    score = result['performance_score']
                    fig_score = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = score,
                        gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#00ff88"}},
                        title = {'text': "PERFORMANCE INDEX", 'font': {'color': '#00ff88', 'size': 18}}
                    ))
                    fig_score.update_layout(height=280, paper_bgcolor='rgba(0,0,0,0)', font_color='white')
                    st.plotly_chart(fig_score, use_container_width=True)
                    
                    st.markdown(f"""
                        <div class="metric-card">
                            <p style='color:#00ff88; font-weight:bold;'>🤖 LUNA INSIGHT:</p>
                            <div class="ai-box">{result['ai_insight']}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    st.success("Data Persisted Successfully")
                else:
                    st.error("Sync Failed: Check API Status or Token")
    else:
        st.markdown("""
            <div style='text-align: center; padding-top: 50px; opacity: 0.3;'>
                <img src="https://cdn-icons-png.flaticon.com/512/2103/2103633.png" width="100">
                <p>AWAITING NEURAL INPUT</p>
            </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='text-align:center; margin-top:50px; color:#30363d'>LUNA CORE v2.0 | SECURE BIOMETRIC GATEWAY</div>", unsafe_allow_html=True)
