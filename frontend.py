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
# CONFIGURATION FAIZA (ULTRA-PROFESSIONAL)
st.set_page_config(
    page_title="🧠 Human Performance OS v2.0 | Advanced Health Analytics Core",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed" # نجعل القائمة الجانبية مغلقة للتركيز على الداشبورد
)

# ==================== ADVANCED DATA LAYER ====================
DB_PATH = 'human_performance_v2.db' # اسم قاعدة البيانات الجديدة

class HealthDataEngine:
    @staticmethod
    def get_latest_data(limit: int = 30) -> pd.DataFrame:
        try:
            conn = sqlite3.connect(DB_PATH)
            # استعلام جلب البيانات الصحية الكاملة (Bio-metrics)
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
            return df.iloc[::-1].reset_index(drop=True) # ترتيب من الأقدم للأحدث للرسم البياني
        except Exception as e:
            print(f"Data Read Error: {e}")
            return pd.DataFrame()

# ==================== ULTRA-ADVANCED HEALTH CYBERPUNK CSS ====================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@200;300;400;500;700&family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');

/* GLOBAL MATRIX SYSTEM */
html, body, [data-testid="stSidebar"] { 
    font-family: 'JetBrains Mono', monospace; 
    color: #d0f7f2; 
    background: #010203;
}

.stApp { 
    background: radial-gradient(circle at center, #0a111a 0%, #010203 100%);
    background-size: cover;
}

/* NEON GLOW HEADERS */
h1, h2, h3, h4, h5, h6 { 
    color: #00ff88 !important; 
    text-transform: uppercase; 
    letter-spacing: 2.5px;
    font-family: 'Orbitron', monospace !important;
    text-shadow: 0 0 15px rgba(0,255,136,0.7), 0 0 30px rgba(0,255,136,0.4);
    animation: neonPulse 2s ease-in-out infinite alternate;
}

@keyframes neonPulse {
    from { text-shadow: 0 0 10px rgba(0,255,136,0.6); }
    to { text-shadow: 0 0 25px rgba(0,255,136,0.9), 0 0 35px rgba(0,255,136,0.5); }
}

/* HYPER-CARDS v3.0 (GLASSMORPHISM + NEON BORDER) */
[data-testid="stMetricValue"] > div, .st-bo, .ai-terminal { 
    background: rgba(6, 26, 26, 0.4) !important;
    border: 1px solid rgba(0, 255, 136, 0.3) !important;
    border-radius: 12px; 
    padding: 15px;
    backdrop-filter: blur(10px);
    box-shadow: 0 0 15px rgba(0,255,136,0.1), inset 0 0 10px rgba(0,255,136,0.05);
    transition: all 0.3s ease;
}

[data-testid="stMetricValue"] > div:hover { 
    transform: scale(1.03);
    border-color: #00ff88 !important;
    box-shadow: 0 0 25px rgba(0,255,136,0.3) !important;
}

/* AI TERMINAL (CHAT-LIKE INSIGHT) */
.ai-terminal {
    font-family: 'Share Tech Mono', monospace;
    border-left: 4px solid #00ff88 !important;
}

/* التحديث التلقائي - Auto-refresh (Streamlit Native Feature) */
st.cache_data.clear() # نمسح الكاش عشان نجيب بيانات جديدة
</style>
""", unsafe_allow_html=True)

# ==================== MAIN HEADER & AUTO-REFRESH ====================
with st.container():
    st.markdown("<h1 style='text-align: center; font-size: 3.5rem; margin-bottom: 0;'>⚡ Human Performance OS v2.0</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #618783; font-family: JetBrains Mono; font-size: 1.1rem;'>Biometric Analytics & Health Optimization Core | AI-Driven Live Matrix</p>", unsafe_allow_html=True)
    st.divider()

# جلب البيانات الصحية الحية
history_df = HealthDataEngine.get_latest_data()

# ==================== LIVE METRICS KEYBOARD ====================
# هذا الجزء يظهر الأرقام اللحظية من أحدث عملية تحليل
if not history_df.empty:
    latest = history_df.iloc[-1]
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # تنسيق الـ Metric بشكل احترافي
    metric_style = "color:#00ff88; font-family:Orbitron; font-weight:700;"
    
    with col1: st.metric("Overall Score", f"{latest['score']:.1f}/10", help="AI-calculated performance matrix")
    with col2: st.metric("💓 Heart Rate", f"{int(latest['heart_rate'])} BPM", help="Last recorded biometric trace")
    with col3: st.metric("🏃 Steps", f"{latest['steps']}", help="Smartwatch activity vector")
    with col4: st.metric("🔥 Calories", f"{latest['calories']} kcal", help="Energy expenditure estimate")
    with col5: st.metric("🌙 Sleep", f"{latest['sleep_hours']:.1f}h", help="Restorative cycle duration")

# ==================== MAIN VISUALIZATION LAYOUT ====================
st.markdown("## 📊 NEURAL HEALTH DASHBOARD")
col_gauge, col_trends = st.columns([1, 2.5])

with col_gauge:
    if not history_df.empty:
        latest = history_df.iloc[-1]
        
        # 4. العداد (Gauge) التفاعلي ثلاثي الأبعاد باستخدام Plotly
        # عدلناه ليكون Score Matrix
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = latest['score'],
            number = {'font': {'color': "#00ff88", 'size': 35}},
            delta = {'reference': 7.0, 'increasing': {'color': "#00ff88"}},
            gauge = {
                'axis': {'range': [0, 10], 'tickwidth': 1, 'tickcolor': "#618783"},
                'bar': {'color': "#00ff88", 'thickness': 0.15},
                'bgcolor': "rgba(6,26,26,0.8)",
                'borderwidth': 2,
                'bordercolor': "#00ff88",
                'steps': [
                    {'range': [0, 4], 'color': 'rgba(255,75,75,0.6)'},
                    {'range': [4, 7], 'color': 'rgba(255,165,0,0.6)'},
                    {'range': [7, 10], 'color': 'rgba(0,255,136,0.8)'}
                ]
            }
        ))
        
        fig_gauge.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': "white", 'family': "'Orbitron', monospace"},
            title={'text': "HEALTH SCORE matrix", 'font': {'size': 20, 'color': '#00ff88'}, 'y': 0.8},
            margin=dict(l=30,r=30,t=60,b=30),
            height=300
        )
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        # 5. عرض نصيحة الذكاء الاصطناعي (Gemini Arabic Output)
        st.markdown(f"""
        <div class="ai-terminal">
            <div style='color: #00ff88; font-weight: 500; margin-bottom: 10px;'>🤖 HEALTH OS AI Insight</div>
            <div style='color: #d0f7f2; line-height: 1.5; font-size: 14px; font-family: "JetBrains Mono";'>
                {latest['recommendation']}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("System Standby. Awaiting first biometric data stream.")

with col_trends:
    if not history_df.empty:
        # 6. رسم بياني خطي متطور باستخدام Plotly (Multi-trace Health Version)
        fig_trends = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Performance Matrix (Health Score)', 'Activity Tracker (Steps)'),
            vertical_spacing=0.15,
            row_heights=[0.7, 0.3]
        )
        
        # رسم السكور
        fig_trends.add_trace(
            go.Scatter(
                x=history_df['timestamp'],
                y=history_df['score'],
                mode='lines+markers',
                name='Health Score',
                line=dict(color='#00ff88', width=4),
                marker=dict(size=10, color='#010203', line=dict(color='#00ff88', width=2))
            ),
            row=1, col=1
        )
        
        # رسم الخطوات
        fig_trends.add_trace(
            go.Scatter(
                x=history_df['timestamp'],
                y=history_df['steps'],
                mode='lines',
                name='Steps Count',
                line=dict(color='#00d4aa', width=3, dash='dash')
            ),
            row=2, col=1
        )
        
        fig_trends.update_layout(
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(6, 26, 26, 0.4)',
            font={'color': "#d0f7f2"},
            showlegend=True,
            legend=dict(
                yanchor="top", y=0.99, xanchor="left", x=0.01,
                bgcolor="rgba(6,26,26,0.8)", bordercolor="#00ff88"
            ),
            hovermode="x unified"
        )
        
        # تخصيص المحاور
        fig_trends.update_xaxes(showgrid=False, zeroline=False, row=1, col=1)
        fig_trends.update_yaxes(title_text="Score", gridcolor='rgba(0,255,136,0.1)', range=[0, 10], row=1, col=1)
        fig_trends.update_xaxes(title_text="Timestamp Protocol", showgrid=False, zeroline=False, row=2, col=1)
        fig_trends.update_yaxes(title_text="Steps", gridcolor='rgba(0,255,136,0.1)', row=2, col=1)
        
        st.plotly_chart(fig_trends, use_container_width=True)

# ==================== HISTORICAL LOG MATRIX ====================
st.markdown("## 📜 HEALTH LOG MATRIX")
if not history_df.empty:
    # تنسيق الجدول بشكل احترافي
    display_df = history_df.copy()
    display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%H:%M %m/%d')
    display_df['score'] = display_df['score'].round(1)
    
    # تعديل الأعمدة المعروضة لتشمل بيانات الساعة الجديدة
    st.dataframe(
        display_df[[
            'timestamp', 'score', 'sleep_hours', 
            'focus_hours', 'heart_rate', 'steps', 'calories'
        ]].tail(15),
        use_container_width=True,
        hide_index=True,
        column_config={
            "score": st.column_config.NumberColumn(
                "Health Score", format="%.1f", help="AI-calculated biometric performance metric"
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

# ==================== AUTO-REFRESH SCRIPT (Streamlit Trick) ====================
# هذا النص البرمجي يضيف زر مخفي ويضغط عليه تلقائياً كل 10 ثوانٍ لعمل Refresh
st.markdown("""
<script>
    var refreshInterval = 10000; // 10 seconds
    setInterval(function(){
        window.location.reload();
    }, refreshInterval);
</script>
""", unsafe_allow_html=True)
