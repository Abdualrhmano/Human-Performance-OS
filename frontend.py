import streamlit as st
import requests
import pandas as pd
import sqlite3
import time
import plotly.graph_objects as go
from datetime import datetime

# 1. إعدادات الصفحة الاحترافية
st.set_page_config(
    page_title="Human Performance OS v2.0",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. تصميم CSS احترافي (Cyberpunk / Matrix Style)
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #e6edf3; font-family: 'Courier New', Courier, monospace; }
    .stSlider > div > div > div > div { background-color: #00ff88; }
    .stSelectSlider > div > div > div > div { background-color: #00ff88; }
    .stButton>button { width: 100%; border-radius: 20px; height: 3.5em; background-color: transparent; color: #00ff88; font-weight: bold; border: 2px solid #00ff88; font-size: 1.1em; text-transform: uppercase; transition: all 0.3s; }
    .stButton>button:hover { background-color: #00ff88; color: black; box-shadow: 0 0 15px #00ff88; }
    .metric-card { background-color: #161b22; padding: 25px; border-radius: 20px; border: 1px solid #30363d; margin-bottom: 20px; box-shadow: 5px 5px 15px rgba(0,0,0,0.3); }
    .recommendation-text { font-size: 1.3em; color: #e6edf3; line-height: 1.6; border-left: 4px solid #00ff88; padding-left: 15px; }
    h1, h2, h3 { color: #00ff88 !important; text-transform: uppercase; letter-spacing: 2px; }
    </style>
    """, unsafe_allow_html=True)

# 3. وظائف جلب البيانات (Database Functions)
DB_PATH = 'performance.db'

def get_latest_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM performance_logs ORDER BY id DESC LIMIT 10", conn)
        conn.close()
        return df.iloc[::-1] # ترتيب من الأقدم للأحدث للرسم البياني
    except:
        return pd.DataFrame()

# العنوان العلوي
st.markdown("<h1 style='text-align: center;'>🚀 Human Performance OS Core</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888;'>v2.0 - Biometric Decision Engine & Security Trace</p>", unsafe_allow_html=True)
st.divider()

# --- قسم المدخلات (Sidebar) ---
with st.sidebar:
    st.markdown("## 📊 Input Data Stream")
    with st.container():
        st.markdown("<div style='background-color: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #30363d;'>", unsafe_allow_html=True)
        sleep = st.select_slider("🌙 Sleep (Hours)", options=[i for i in range(0, 13)], value=8)
        focus = st.slider("🎯 Deep Focus (Hours)", 0.0, 12.0, 4.0)
        energy = st.select_slider("⚡ Energy Level (1-10)", options=[i for i in range(1, 11)], value=7)
        consistency = st.slider("🔄 Habit Consistency (0-1)", 0.0, 1.0, 0.8)
        
        st.markdown("### 🔐 Security & Protocol")
        api_key = st.text_input("Enter API Protocol Key", type="password", value="demo-key")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("EXECUTE ANALYSIS PROTOCAL")

# --- قسم المخرجات والتحليلات (Main Area) ---
# جلب البيانات التاريخية
history_df = get_latest_data()

# 4. محاكاة الـ Analysis عند الضغط
if analyze_btn:
    with st.spinner('Accessing LUNA Core Engine... Decrypting Security Layer...'):
        time.sleep(1.5)
        payload = {"sleep_hours": sleep, "focus_hours": focus, "energy_level": energy, "habit_consistency": consistency}
        headers = {"x-api-key": api_key}
        
        try:
            response = requests.post("http://localhost:8000/evaluate", json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                st.toast(f"Protocol: {data['db_status']}", icon='✅')
                
                # تحديث البيانات التاريخية بعد الحفظ الجديد
                history_df = get_latest_data()
            else:
                st.error("Engine Error: Invalid Key or Server Offline.")
        except:
            st.error("Protocol Failure: Backend Connection Failed. Ensure main.py is running.")

# تقسيم الشاشة للتحليلات البصرية
col1, col2 = st.columns([1.2, 2])

with col1:
    st.markdown("## 🧠 Engine Verdict")
    if not history_df.empty:
        # جلب أحدث نتيجة
        latest = history_df.iloc[-1]
        score = latest['score']
        rec = latest['recommendation']
        
        # 5. رسم بياني العداد (Gauge Chart) تفاعلي واحترافي
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Performance Score", 'font': {'size': 24, 'color': '#00ff88'}},
            delta = {'reference': 6, 'increasing': {'color': "#00ff88"}, 'decreasing': {'color': "#ff4b4b"}},
            gauge = {
                'axis': {'range': [0, 10], 'tickwidth': 1, 'tickcolor': "#30363d"},
                'bar': {'color': "#00ff88"},
                'bgcolor': "#161b22",
                'borderwidth': 2,
                'bordercolor': "#30363d",
                'steps': [
                    {'range': [0, 4], 'color': '#ff4b4b'},
                    {'range': [4, 7], 'color': '#ffa500'},
                    {'range': [7, 10], 'color': '#00ff88'}
                ],
                'threshold': {
                    'line': {'color': "white", 'width': 4},
                    'thickness': 0.75,
                    'value': score
                }
            }
        ))
        fig_gauge.update_layout(paper_bgcolor='#0d1117', plot_bgcolor='#0d1117', font={'color': "white", 'family': "Arial"})
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        # عرض النصيحة
        st.markdown(f"""
        <div class="metric-card">
            <h3>Latest AI Insight</h3>
            <p class="recommendation-text">{rec}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # عرض التشفير
        with st.expander("🔐 Security Trace (AES-256 Encrypted Payload)"):
            st.code(latest['encrypted_data'], language="text")
    else:
        st.info("No verdict available. Run your first analysis.")

with col2:
    st.markdown("## 📈 Performance Progress")
    if not history_df.empty:
        # 6. رسم بياني خطي (Line Chart) تفاعلي باستخدام Plotly
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=history_df['timestamp'],
            y=history_df['score'],
            mode='lines+markers',
            name='Score',
            line=dict(color='#00ff88', width=3),
            marker=dict(size=8, color='white', line=dict(color='#00ff88', width=2))
        ))
        
        fig_line.update_layout(
            paper_bgcolor='#0d1117',
            plot_bgcolor='#161b22',
            font={'color': "white"},
            xaxis=dict(title="Timestamp", showgrid=False, zeroline=False),
            yaxis=dict(title="Score (0-10)", showgrid=True, gridcolor='#30363d', range=[0, 10]),
            margin=dict(l=40, r=40, t=40, b=40),
            hovermode="x unified"
        )
        st.plotly_chart(fig_line, use_container_width=True)
        
        # عرض السجلات الخام (Raw Logs)
        st.markdown("### 📜 System Logs (Database Record)")
        # تنسيق الوقت لعرض أفضل
        history_df['timestamp'] = pd.to_datetime(history_df['timestamp']).dt.strftime('%H:%M:%S (%Y-%m-%d)')
        st.dataframe(history_df[['timestamp', 'score', 'user_id']].iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("No historical data to visualize. Run analysis to start logging.")

st.divider()
st.markdown("<p style='text-align: center; color: #555;'>Secure & Smart Biometric Analytics Architecture</p>", unsafe_allow_html=True)
