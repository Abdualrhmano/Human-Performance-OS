import streamlit as st
import requests
import pandas as pd
import sqlite3
import time

# 1. إعدادات الصفحة
st.set_page_config(page_title="Human Performance OS", page_icon="🚀", layout="wide")

# 2. تصميم CSS احترافي
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #00ff88; color: black; font-weight: bold; border: none; }
    .metric-card { background-color: #161b22; padding: 20px; border-radius: 15px; border-left: 5px solid #00ff88; margin-bottom: 20px; border: 1px solid #30363d; }
    .history-card { background-color: #0d1117; border: 1px solid #30363d; border-radius: 10px; padding: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 3. دالة لجلب البيانات من قاعدة البيانات
def get_history():
    try:
        conn = sqlite3.connect('performance.db')
        # جلب آخر 5 سجلات مرتبة بالأحدث
        df = pd.read_sql_query("SELECT timestamp, score, recommendation FROM performance_logs ORDER BY id DESC LIMIT 5", conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()

# العنوان
st.markdown("<h1 style='text-align: center; color: #00ff88;'>🚀 Human Performance OS</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888;'>v1.5 - Integrated Database & AI Analytics</p>", unsafe_allow_html=True)

st.divider()

col1, col2 = st.columns([1, 1.5])

with col1:
    st.markdown("### 📊 Input Performance Metrics")
    with st.container():
        sleep = st.select_slider("🌙 Sleep Hours", options=[i for i in range(0, 13)], value=8)
        focus = st.slider("🎯 Focus Sessions (Hours)", 0.0, 12.0, 4.0)
        energy = st.select_slider("⚡ Energy Level", options=[i for i in range(1, 11)], value=7)
        consistency = st.slider("🔄 Habit Consistency", 0.0, 1.0, 0.8)
        
        analyze_btn = st.button("EXECUTE AI ANALYSIS")

with col2:
    if analyze_btn:
        with st.spinner('Accessing LUNA Core Engine...'):
            time.sleep(1)
            payload = {"sleep_hours": sleep, "focus_hours": focus, "energy_level": energy, "habit_consistency": consistency}
            headers = {"x-api-key": "demo-key"}
            
            try:
                response = requests.post("http://localhost:8000/evaluate", json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    
                    # عرض النتيجة الحالية
                    st.markdown(f"""
                    <div class="metric-card">
                        <h2 style='color: #00ff88; margin:0;'>Current Score: {data['performance_score']}/10</h2>
                        <p style='font-size: 1.1em; color: #e6edf3;'>{data['recommendation']}</p>
                        <small style='color: #8b949e;'>Timestamp: {data['timestamp']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error("Engine Error: Unauthorized or Server Down")
            except:
                st.error("Backend Connection Failed. Ensure main.py is running.")

    # --- قسم السجل (History Section) ---
    st.markdown("### 📜 Performance History (Stored in DB)")
    history_df = get_history()
    if not history_df.empty:
        st.dataframe(history_df, use_container_width=True, hide_index=True)
    else:
        st.info("No data found in database yet. Run your first analysis!")

st.divider()
st.markdown("<p style='text-align: center; color: #555;'>Secure Architecture: AES-256 + SQLite3 + FastAPI</p>", unsafe_allow_html=True)
