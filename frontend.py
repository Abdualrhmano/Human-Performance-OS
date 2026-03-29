# ======================================================
# SYSTEM: Human Performance OS v2.0
# MODULE: STREAMLIT FRONTEND BRIDGE (UI/UX) - PRO VERSION
# ======================================================

import streamlit as st
import requests
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# ------------------------------------------------------
# 1. CORE CONFIGURATION & PROFESSIONAL STYLING (هندسة الهوية البصرية)
# ------------------------------------------------------
class UIStyle:
    @staticmethod
    def apply():
        st.set_page_config(page_title="Human Performance OS v2.0", page_icon="🧠", layout="wide")
        
        # تأثيرات CSS متقدمة للـ Glassmorphism والهوية البصرية
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono&display=swap');
            
            html, body, [data-testid="stSidebar"] { font-family: 'JetBrains Mono', monospace; }
            .stApp { background-color: #05070a; color: #e6edf3; }
            
            /* Glassmorphism Cards */
            .metric-card {
                background: rgba(13, 17, 23, 0.9);
                border: 1px solid rgba(48, 54, 61, 0.7);
                border-radius: 12px;
                padding: 25px;
                margin-bottom: 20px;
                border-left: 4px solid #00ff88;
                box-shadow: 0 4px 15px rgba(0,0,0,0.4);
            }
            
            /* Professional Header */
            .main-header {
                background: linear-gradient(90deg, #00ff88, #00bd68);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-family: 'Orbitron', sans-serif;
                font-size: 3.5em;
                font-weight: bold;
                text-align: center;
                margin-bottom: 0px;
            }
            
            /* AI Insight Box with Glow Effect */
            .ai-box {
                background: rgba(0, 255, 136, 0.03);
                border: 1px solid rgba(0, 255, 136, 0.3);
                padding: 20px;
                border-radius: 10px;
                color: #00ff88;
                font-size: 1.1em;
                line-height: 1.7;
                box-shadow: 0 0 10px rgba(0, 255, 136, 0.1);
            }
            
            /* Table Styling */
            [data-testid="stTable"] { border-radius: 8px; border: 1px solid #30363d; overflow: hidden; }
            </style>
        """, unsafe_allow_html=True)

    @staticmethod
    def get_performance_emoji(score):
        """توليد رمز تعبيري متجاوب مع السكور"""
        if score >= 80: return "🟢 (تحسن ملحوظ)"
        if score >= 50: return "🟡 (أداء مستقر)"
        return "🔴 (تراجع بحاجة لمعالجة)"

# ------------------------------------------------------
# 2. DATA ARCHITECT (إدارة البيانات المحلية - دون تغيير الملامح)
# ------------------------------------------------------
class DataVault:
    @staticmethod
    def fetch_history():
        """جلب البيانات التاريخية من قاعدة البيانات"""
        try:
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
# 3. BACKEND BRIDGE (الربط مع API السيادي - دون تغيير الملامح)
# ------------------------------------------------------
class BackendBridge:
    # ملاحظة: هات الرابط من الـ Forwarded Ports في Codespaces واضيفه هنا
    BASE_URL = "http://localhost:8000/api/v2" 

    @staticmethod
    def sync_data(token, metrics):
        """إرسال البيانات للباك إند واستلام التحليل"""
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(f"{BackendBridge.BASE_URL}/performance/sync", 
                                     json=metrics, headers=headers)
            return response.json() if response.status_code == 200 else None
        except:
            return None

# ------------------------------------------------------
# 4. DASHBOARD RENDERER (بناء الواجهة الاحترافية)
# ------------------------------------------------------
UIStyle.apply()

# --- SIDEBAR: AUTH & INPUT (إدخال البيانات) ---
with st.sidebar:
    st.markdown("<h1 style='color:#00ff88; font-family:Orbitron'>🛡️ AUTH</h1>", unsafe_allow_html=True)
    access_token = st.text_input("ACCESS_TOKEN", type="password", help="ضع توكن الدخول هنا")
    
    st.divider()
    st.markdown("<h1 style='color:#00ff88; font-family:Orbitron'>📡 SENSORS</h1>", unsafe_allow_html=True)
    
    hr = st.slider("💓 Heart Rate (BPM)", 40, 160, 75)
    steps = st.number_input("👟 Total Steps", value=8000, step=100)
    screen = st.slider("📱 Screen Time (Hrs)", 0.0, 16.0, 4.0)
    sleep = st.slider("🌙 Sleep Duration (Hrs)", 0.0, 12.0, 7.5)
    
    st.markdown("<br>", unsafe_allow_html=True)
    sync_btn = st.button("🚀 EXECUTE NEURAL SYNC", use_container_width=True)

# --- MAIN PAGE: VISUALIZATION (عرض البيانات) ---
st.markdown("<h1 class='main-header'>LUNA SOVEREIGN OS</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#8b949e'>Neural-Biometric Synchronization Protocol v2.0 | Entwickelt von Abdulrahman</p>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

col_gauge, col_charts = st.columns([1, 2], gap="large")

with col_gauge:
    st.markdown("### 🧠 Live Analysis")
    
    if sync_btn:
        if not access_token:
            st.error("Missing Authentication Token")
        else:
            with st.spinner("Synchronizing with LUNA Neural Brain..."):
                metrics = {
                    "heart_rate": hr,
                    "steps": steps,
                    "screen_time": screen,
                    "sleep_hours": sleep
                }
                result = BackendBridge.sync_data(access_token, metrics)
                
                if result:
                    # العداد الدائري الاحترافي والمطور (Custom Gauge)
                    score = result['performance_score']
                    emoji = UIStyle.get_performance_emoji(score)
                    
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = score,
                        title = {'text': f"PERFORMANCE INDEX<br>{emoji}", 'font': {'color': '#00ff88', 'size': 20}},
                        gauge = {
                            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#30363d"},
                            'bar': {'color': "#00ff88"},
                            'bgcolor': "rgba(0,0,0,0)",
                            'borderwidth': 1,
                            'bordercolor': "#30363d",
                            'steps': [
                                {'range': [0, 50], 'color': 'rgba(255, 0, 0, 0.05)'},
                                {'range': [50, 80], 'color': 'rgba(255, 255, 0, 0.05)'},
                                {'range': [80, 100], 'color': 'rgba(0, 255, 136, 0.05)'}
                            ],
                            'threshold': {
                                'line': {'color': "#fff", 'width': 2},
                                'thickness': 0.75,
                                'value': score
                            }
                        }
                    ))
                    fig_gauge.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', font_color='white', margin=dict(l=20, r=20, t=50, b=0))
                    st.plotly_chart(fig_gauge, use_container_width=True)
                    
                    st.markdown(f"""
                        <div class="metric-card">
                            <p style='color:#00ff88; font-weight:bold; font-size:1.2em; margin-bottom:10px;'>🤖 LUNA INTELLIGENCE VERDICT:</p>
                            <div class="ai-box">{result['ai_insight']}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    st.toast("Sync Complete", icon="✅")
                else:
                    st.error("Sync Failed: Check API Status or Token")
    else:
        st.markdown("""
            <div style='text-align: center; padding-top: 100px; opacity: 0.3;'>
                <img src="https://cdn-icons-png.flaticon.com/512/2103/2103633.png" width="100">
                <p style='font-size:1.2em; margin-top:20px'>AWAITING NEURAL UPLOAD</p>
            </div>
        """, unsafe_allow_html=True)

with col_charts:
    st.markdown("### 📊 Performance Timeline")
    history_df = DataVault.fetch_history()
    
    if not history_df.empty:
        # رسم بياني احترافي مطور (Professional Line Chart)
        fig = px.line(history_df, x='timestamp', y='performance_score', markers=True, title="Score Evolution over Time")
        fig.update_traces(line_color='#00ff88', line_width=4, marker=dict(size=10, color='#fff'))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#8b949e', xaxis_showgrid=False, yaxis_showgrid=True,
            yaxis=dict(gridcolor='#161b22', title="Score (0-100)"), xaxis=dict(title="Timestamp"),
            margin=dict(l=0, r=0, t=50, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("### 📜 System Logs (Recent 5 Entries)")
        # عرض الجدول بشكل أنيق ومفرز
        st.table(history_df.head(5))
    else:
        st.info("System Standby: Connect to human_performance_v2.db to view historical biometric data.")

st.markdown("<div style='text-align:center; margin-top:60px; color:#30363d; font-size:0.8em;'>LUNA CORE v2.0 | SECURE BIOMETRIC GATEWAY | DEVELOPED BY ABDULRAHMAN</div>", unsafe_allow_html=True)
