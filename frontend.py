# -*- coding: utf-8 -*-
# ======================================================
# SYSTEM: Human Performance & Market OS v2.0
# ARCHITECT: Abdulrahman (Lead Software Engineer)
# MODULE: INTEGRATED BIOMETRIC & FINANCIAL GATEWAY
# ======================================================

import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import asyncio
import random
import time

# 1. PROFESSIONAL UI CONFIGURATION
class SystemUI:
    @staticmethod
    def setup():
        # إعداد الصفحة لمرة واحدة فقط في بداية الكود
        st.set_page_config(
            page_title="Human Performance OS v2.0| Biometric & Market",
            page_icon="🧠",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # هندسة التصميم (CSS Injection) لتوحيد شكل الكودين
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
            
            /* تصميم القائمة الجانبية */
            section[data-testid="stSidebar"] {
                background-color: var(--sidebar-bg) !important;
                border-right: 1px solid #30363d;
            }

            /* العناوين الاحترافية */
            .main-title { 
                font-family: 'Orbitron', sans-serif; 
                color: var(--primary); 
                text-shadow: 0 0 20px rgba(0, 255, 136, 0.4); 
                font-size: 2.8em; 
                text-align: center; 
            }

            /* تخصيص التبويبات (Tabs) لتبدو كجزء من نظام تقني */
            .stTabs [data-baseweb="tab-list"] { gap: 10px; }
            .stTabs [data-baseweb="tab"] {
                font-family: 'Orbitron';
                background-color: #161b22 !important;
                border: 1px solid #30363d !important;
                border-radius: 5px 5px 0 0;
                color: #8b949e !important;
                padding: 10px 20px;
            }
            .stTabs [aria-selected="true"] {
                color: var(--primary) !important;
                border-color: var(--primary) !important;
            }

            /* تخصيص السلايدرز والأزرار */
            .stSlider [data-baseweb="slider"] div { background-color: var(--accent-red) !important; }
            .stButton > button {
                background-color: #21262d !important;
                color: white !important;
                border: 1px solid #30363d !important;
                font-family: 'Orbitron';
                width: 100%;
            }
            </style>
        """, unsafe_allow_html=True)

# تشغيل الإعدادات
SystemUI.setup()
# 2. CORE ENGINES: BIOMETRIC & MARKET PULSE
class DataEngine:
    DB_PATH = 'luna_integrated_v2.db'
    
    @staticmethod
    def init_db():
        """تهيئة قاعدة البيانات للسجلات الصحية"""
        conn = sqlite3.connect(DataEngine.DB_PATH)
        conn.execute('''CREATE TABLE IF NOT EXISTS performance_logs 
                        (timestamp TEXT, performance_score REAL, hr INTEGER, steps INTEGER)''')
        conn.commit()
        conn.close()

    @staticmethod
    def save_biometric_log(score, hr, steps):
        """حفظ قراءات الجسم"""
        conn = sqlite3.connect(DataEngine.DB_PATH)
        conn.execute("INSERT INTO performance_logs VALUES (?, ?, ?, ?)",
                       (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), score, hr, steps))
        conn.commit()
        conn.close()

    @staticmethod
    @st.cache_resource(show_spinner=False, ttl="1h")
    def fetch_market_data(tickers, period):
        """جلب بيانات الأسهم من YFinance مع ذاكرة مؤقتة"""
        try:
            tickers_obj = yf.Tickers(tickers)
            data = tickers_obj.history(period=period)
            if data.empty or "Close" not in data:
                return None
            return data["Close"]
        except Exception as e:
            st.sidebar.error(f"Market Link Error: {str(e)}")
            return None

    @staticmethod
    def get_luna_ai_analysis(score, hr, steps):
        """منطق ذكاء LUNA لربط القراءات"""
        status = "🟢 OPTIMAL" if score >= 60 else "🔴 CRITICAL"
        hr_msg = "نبض مستقر" if 60 <= hr <= 100 else "تنبيه في النبض"
        activity = "نشاط ممتاز" if steps > 5000 else "تحرك لرفع الأداء"
        
        return f"الحالة: {status}\n{hr_msg} | {activity}\nكفاءة النظام: {score}%"

# 3. GLOBAL VARIABLES & CONSTANTS
STOCKS_LIBRARY = [
    "AAPL", "MSFT", "GOOGL", "NVDA", "AMZN", "TSLA", "META", "AMD", 
    "BTC-USD", "ETH-USD", "NFLX", "ORCL", "CRM", "INTC", "IBM"
]

HORIZON_MAP = {
    "1 Month": "1mo", "3 Months": "3mo", "6 Months": "6mo", 
    "1 Year": "1y", "5 Years": "5y", "Max": "max"
}

# تشغيل قاعدة البيانات عند الإقلاع
DataEngine.init_db()

# إعداد الـ Session State لمنع فقدان البيانات عند التحديث
if "tickers_input" not in st.session_state:
    st.session_state.tickers_input = ["AAPL", "NVDA", "TSLA", "BTC-USD"]
if "current_score" not in st.session_state:
    st.session_state.current_score = 46.6
# 4. SIDEBAR: THE COMMAND CENTER
with st.sidebar:
    st.markdown("<h2 style='color:#00ff88; font-family:Orbitron;'>🛡️ COMMAND CENTER</h2>", unsafe_allow_html=True)
    
    # قسم تحليل LUNA AI (يظهر دائماً في الأعلى)
    st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>🤖 AI VERDICT</h3>", unsafe_allow_html=True)
    
    luna_msg = st.session_state.get('last_verdict', "بانتظار مزامنة البيانات...")
    st.markdown(f"""
        <div style="background: rgba(0,255,136,0.1); border: 1px solid #00ff88; padding: 15px; border-radius: 10px; border-left: 5px solid #00ff88;">
            <p style="color:#00ff88; font-weight:bold; margin-bottom:5px;">LUNA Intelligence:</p>
            <p style="font-size:0.9em; color:white; white-space: pre-wrap;">{luna_msg}</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()

    # قسم التحكم في الأسهم (Market Settings)
    with st.expander("📊 MARKET SETTINGS", expanded=True):
        selected_tickers = st.multiselect(
            "Select Tickers",
            options=sorted(list(set(STOCKS_LIBRARY) | set(st.session_state.tickers_input))),
            default=st.session_state.tickers_input,
            help="اختر الأسهم أو العملات الرقمية لمراقبتها"
        )
        
        selected_horizon = st.pills(
            "Time Horizon",
            options=list(HORIZON_MAP.keys()),
            default="6 Months"
        )

    st.divider()

    # قسم المؤشرات الحيوية (Biometric Sensors)
    with st.expander("💓 SENSOR SIMULATION", expanded=True):
        hr_input = st.slider("Heart Rate (BPM)", 40, 190, 75)
        step_input = st.number_input("Daily Steps", value=6000, step=500)
        
        # زر المزامنة الرئيسي
        if st.button("🚀 INITIATE SYSTEM SYNC", use_container_width=True):
            with st.spinner("Processing Neural & Market Signals..."):
                # محاكاة حساب النتيجة الحيوية
                new_score = round(random.uniform(30, 98), 1)
                st.session_state.current_score = new_score
                st.session_state.tickers_input = selected_tickers
                
                # تحديث تحليل LUNA
                st.session_state.last_verdict = DataEngine.get_luna_ai_analysis(
                    new_score, hr_input, step_input
                )
                
                # حفظ في قاعدة البيانات
                DataEngine.save_biometric_log(new_score, hr_input, step_input)
                
                # إعادة تشغيل لتحديث الرسوم البيانية
                st.rerun()

    st.markdown(f"<div style='text-align:center; color:#30363d; font-size:0.7em; margin-top:20px;'>SECURE SESSION: {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
# 5. MAIN DASHBOARD AREA
st.markdown("<h1 class='main-title'>LUNA OS v2.0 | Integrated</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#8b949e; margin-bottom:30px;'>Senior Engineer: Abdulrahman | Biometric & Market Pulse Terminal</p>", unsafe_allow_html=True)

# إنشاء التبويبات الرئيسية لدمج النظامين
tab_bio, tab_market = st.tabs(["🧬 BIOMETRIC TELEMETRY", "📊 MARKET INTELLIGENCE"])

# --- TAB 1: BIOMETRIC TELEMETRY (الجزء الخاص بصحتك) ---
with tab_bio:
    col_gauge, col_timeline = st.columns([1, 2], gap="large")
    
    with col_gauge:
        st.markdown("<h3 style='color:#00ff88; font-family:Orbitron; font-size:1.2em;'>🧠 Neural Status</h3>", unsafe_allow_html=True)
        
        # جلب القيمة الحالية من الـ Session
        current_perf = st.session_state.get('current_score', 46.6)
        
        # تصميم العداد (Gauge) المتقدم
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = current_perf,
            number = {'font': {'color': 'white', 'family': 'Orbitron', 'size': 40}},
            gauge = {
                'axis': {'range': [0, 100], 'tickcolor': "#00ff88"},
                'bar': {'color': "#00ff88"},
                'bgcolor': "rgba(0,0,0,0)",
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': current_perf
                }
            }
        ))
        fig_gauge.update_layout(height=320, paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0, l=10, r=10))
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        # رسالة تنبيه أسفل العداد
        if current_perf < 50:
            st.markdown("<p style='text-align:center; color:#ff4b4b; font-weight:bold;'>🔴 CRITICAL PERFORMANCE LOSS</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='text-align:center; color:#00ff88; font-weight:bold;'>🟢 OPTIMAL NEURAL STATE</p>", unsafe_allow_html=True)

    with col_timeline:
        st.markdown("<h3 style='color:#00ff88; font-family:Orbitron; font-size:1.2em;'>📈 Health Timeline</h3>", unsafe_allow_html=True)
        
        # جلب البيانات التاريخية من SQLite
        conn = sqlite3.connect(DataEngine.DB_PATH)
        df_hist = pd.read_sql_query("SELECT * FROM performance_logs ORDER BY timestamp DESC LIMIT 20", conn)
        conn.close()
        
        if not df_hist.empty:
            # رسم بياني مساحي (Area Chart)
            fig_area = px.area(df_hist.iloc[::-1], x='timestamp', y='performance_score')
            fig_area.update_traces(line_color='#00ff88', fillcolor='rgba(0, 255, 136, 0.1)', markers=True)
            fig_area.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                height=350,
                xaxis=dict(showgrid=False, color="#8b949e"),
                yaxis=dict(showgrid=True, gridcolor='#1f2937', color="#8b949e"),
                margin=dict(t=20, b=20, l=0, r=0)
            )
            st.plotly_chart(fig_area, use_container_width=True)
        else:
            st.info("No biometric data logged yet. Use 'INITIATE SYNC' to start.")
# --- TAB 2: MARKET INTELLIGENCE (الجزء الخاص بالبورصة والأسهم) ---
with tab_market:
    st.markdown("<h3 style='color:#00ff88; font-family:Orbitron; font-size:1.2em;'>📊 Market Peer Analysis</h3>", unsafe_allow_html=True)
    
    # جلب البيانات باستخدام المحرك الذي بنيناه في الجزء الثاني
    market_tickers = st.session_state.get('tickers_input', ["AAPL", "NVDA", "TSLA"])
    horizon_key = st.session_state.get('selected_horizon', "6 Months")
    
    # التحميل الفعلي للبيانات
    with st.spinner("Connecting to Global Market Hub..."):
        close_data = DataEngine.fetch_market_data(market_tickers, HORIZON_MAP[horizon_key])
        
    if close_data is not None and not close_data.empty:
        # 1. توحيد الأسعار (Normalization) لتبدأ جميعها من رقم 1 للمقارنة العادلة
        norm_df = close_data.div(close_data.iloc[0])
        
        col_m_main, col_m_stats = st.columns([3, 1])
        
        with col_m_main:
            # رسم بياني متطور باستخدام Altair (يشبه الأنظمة المالية الاحترافية)
            plot_data = norm_df.reset_index().melt(id_vars=["Date"], var_name="Stock", value_name="Normalized price")
            market_chart = alt.Chart(plot_data).mark_line(strokeWidth=2).encode(
                x=alt.X("Date:T", title="Timeline"),
                y=alt.Y("Normalized price:Q", scale=alt.Scale(zero=False), title="Performance Index"),
                color=alt.Color("Stock:N", scale=alt.Scale(scheme='category10')),
                tooltip=["Date", "Stock", "Normalized price"]
            ).properties(height=400).interactive()
            
            st.altair_chart(market_chart, use_container_width=True)

        with col_m_stats:
            st.markdown("<p style='color:#00ff88; font-family:Orbitron; font-size:0.9em;'>🏆 Top Performers</p>", unsafe_allow_html=True)
            # حساب أفضل وأسوأ سهم في الفترة المختارة
            latest_vals = norm_df.iloc[-1]
            best_stock = latest_vals.idxmax()
            worst_stock = latest_vals.idxmin()
            
            st.metric("LEADER", best_stock, f"{round((latest_vals.max()-1)*100, 1)}%")
            st.metric("LAGGARD", worst_stock, f"{round((latest_vals.min()-1)*100, 1)}%", delta_color="inverse")

        # 2. تحليل المقارنة الفردية (Individual vs Peer Average)
        st.divider()
        st.markdown("<h4 style='color:#8b949e; font-family:Orbitron;'>🔍 Peer-to-Peer Delta Analysis</h4>", unsafe_allow_html=True)
        
        if len(market_tickers) > 1:
            p_cols = st.columns(min(len(market_tickers), 4))
            for i, ticker in enumerate(market_tickers):
                # حساب متوسط الأقران (باستثناء السهم الحالي)
                peers = norm_df.drop(columns=[ticker])
                peer_avg = peers.mean(axis=1)
                
                # حساب الفرق (Delta)
                current_delta = norm_df[ticker].iloc[-1] - peer_avg.iloc[-1]
                
                with p_cols[i % 4]:
                    with st.container(border=True):
                        st.write(f"**{ticker}**")
                        delta_color = "green" if current_delta > 0 else "red"
                        st.markdown(f"<h3 style='color:{delta_color};'>{round(current_delta*100, 2)}%</h3>", unsafe_allow_html=True)
                        st.caption("Alpha vs Peers")
        else:
            st.warning("Select 2 or more tickers to enable Peer Comparison.")
    else:
        st.error("Failed to sync with Market Data. Ensure internet protocol is active.")

# --- FINAL SYSTEM FOOTER ---
st.markdown(f"""
    <div style='text-align:center; margin-top:60px; padding:40px; border-top:1px solid #161b22; background-color:#0d1117;'>
        <p style='font-family:Orbitron; font-size:1em; color:#00ff88; letter-spacing: 3px; margin-bottom:10px;'>
            LUNA CORE v10.0 | SOVEREIGN HUMAN OS
        </p>
        <p style='font-family:JetBrains Mono; font-size:0.8em; color:#8b949e;'>
            BIOMETRIC ENCRYPTION: ACTIVE • MARKET TELEMETRY: SYNCED • {datetime.now().year}
        </p>
        <p style='font-family:JetBrains Mono; font-size:0.7em; color:#30363d; margin-top:10px;'>
            LEAD SOFTWARE ENGINEER: ABDULRAHMAN ABDUL-MONEIM
        </p>
    </div>
""", unsafe_allow_html=True)

# ------------------------------------------------------
# END OF INTEGRATED SYSTEM
# ------------------------------------------------------
