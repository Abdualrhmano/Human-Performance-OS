# frontend.py
# Human Performance OS - Streamlit UI with FacePanel integration (PIL-based, no cairosvg)
# مدمج: إصلاحات، تسجيل، دوال مساعدة، وإضافة ChartPanel لعرض الرسوم البيانية المتقدمة

import os
import io
import json
import time
import threading
import asyncio
import logging
from typing import Tuple, Optional, Dict, Any, List

import streamlit as st
import pandas as pd
import sqlite3
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Logger
LOG = logging.getLogger("frontend")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# -------------------------------
# Configuration
# -------------------------------
API_BASE = os.environ.get("HPOS_API_BASE", "http://localhost:8000/api/v2")  # FastAPI base with API prefix
WS_BASE = API_BASE.replace("http://", "ws://").replace("https://", "wss://")
DB_PATH = os.environ.get("DB_PATH", "human_performance_v2.db")
ASSETS_DIR = os.environ.get("ASSETS_DIR", "assets")

# -------------------------------
# Helper fonts / text sizing (مطلوبة للرسوم)
# -------------------------------
def load_font(size: int = 14, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size=size)
        except Exception:
            continue
    return ImageFont.load_default()

def get_text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        pass
    try:
        return draw.textsize(text, font=font)
    except Exception:
        pass
    try:
        return font.getsize(text)
    except Exception:
        pass
    avg_char_w = max(6, int(getattr(font, "size", 14) * 0.5))
    return (len(text) * avg_char_w, int(avg_char_w * 1.6))

# -------------------------------
# System UI
# -------------------------------
class SystemUI:
    @staticmethod
    def setup():
        st.set_page_config(page_title="Human Performance OS v2.0", page_icon="🧠", layout="wide")
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono:wght@300;500&display=swap');
            :root { --primary: #00ff88; --bg: #05070a; --sidebar-bg: #0d1117; }
            .stApp { background-color: var(--bg); color: #e6edf3; font-family: 'JetBrains Mono', monospace; }
            section[data-testid="stSidebar"] { background-color: var(--sidebar-bg) !important; border-right: 1px solid #30363d; }
            .main-title { font-family: 'Orbitron', sans-serif; color: var(--primary); text-shadow: 0 0 20px rgba(0,255,136,0.4); font-size: 2.5em; text-align: center; margin-bottom: 20px; }
            .luna-card { background: rgba(0,255,136,0.06); border: 1px solid #00ff88; padding: 12px; border-radius: 10px; margin-bottom: 12px; }
            </style>
        """, unsafe_allow_html=True)

# -------------------------------
# AuthManager (lightweight)
# -------------------------------
class AuthManager:
    LOGIN_ENDPOINT = f"{API_BASE.rstrip('/')}/auth/login"
    REGISTER_ENDPOINT = f"{API_BASE.rstrip('/')}/auth/register"

    @staticmethod
    def init_session():
        if "auth" not in st.session_state:
            st.session_state.auth = {"is_authenticated": False, "token": None, "user": {}}

    @staticmethod
    def login(username: str, password: str) -> Tuple[bool, dict]:
        AuthManager.init_session()
        try:
            resp = requests.post(AuthManager.LOGIN_ENDPOINT, data={"username": username, "password": password}, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.auth.update({
                    "is_authenticated": True,
                    "token": data.get("access_token"),
                    "user": {"username": username, "id": data.get("user_id")}
                })
                return True, data
            return False, {"error": resp.text}
        except Exception as e:
            return False, {"error": str(e)}

    @staticmethod
    def logout():
        st.session_state.auth = {"is_authenticated": False, "token": None, "user": {}}

    @staticmethod
    def is_authenticated() -> bool:
        AuthManager.init_session()
        return bool(st.session_state.auth.get("is_authenticated", False))

    @staticmethod
    def get_token() -> Optional[str]:
        AuthManager.init_session()
        return st.session_state.auth.get("token")

    @staticmethod
    def get_auth_header() -> dict:
        token = AuthManager.get_token()
        return {"Authorization": f"Bearer {token}"} if token else {}

    @staticmethod
    def login_ui():
        AuthManager.init_session()
        if AuthManager.is_authenticated():
            user = st.session_state.auth.get("user", {})
            st.markdown(f"👋 مرحباً، **{user.get('username','User')}**")
            if st.button("Sign Out"):
                AuthManager.logout()
                st.experimental_rerun()
            return True
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Sign In"):
                ok, resp = AuthManager.login(username, password)
                if ok:
                    st.success("Signed in successfully.")
                    st.rerun()
                else:
                    st.error(f"Login failed: {resp.get('error')}")
        with col2:
            if st.button("Register"):
                try:
                    resp = requests.post(AuthManager.REGISTER_ENDPOINT, json={"username": username, "password": password}, timeout=8)
                    if resp.status_code == 200:
                        st.success("Registered successfully. Please login.")
                    else:
                        st.error(f"Register failed: {resp.text}")
                except Exception as e:
                    st.error(f"Register error: {e}")
        return False

# -------------------------------
# BackendConnector (simple wrapper)
# -------------------------------
class BackendConnector:
    BASE_URL = API_BASE

    @staticmethod
    def _full_url(path: str) -> str:
        base = BackendConnector.BASE_URL.rstrip('/')
        if not base.endswith("/api/v2"):
            base = base.rstrip('/') + "/api/v2"
        return f"{base}/{path.lstrip('/')}"

    @staticmethod
    def get(path: str, params: dict = None, require_auth: bool = True) -> Tuple[bool, dict]:
        url = BackendConnector._full_url(path)
        headers = {}
        if require_auth:
            headers.update(AuthManager.get_auth_header())
        try:
            resp = requests.get(url, params=params or {}, headers=headers, timeout=10)
            resp.raise_for_status()
            return True, resp.json()
        except Exception as e:
            return False, {"error": str(e)}

    @staticmethod
    def post(path: str, payload: dict = None, require_auth: bool = True) -> Tuple[bool, dict]:
        url = BackendConnector._full_url(path)
        headers = {"Content-Type": "application/json"}
        if require_auth:
            headers.update(AuthManager.get_auth_header())
        try:
            resp = requests.post(url, json=payload or {}, headers=headers, timeout=15)
            resp.raise_for_status()
            return True, resp.json()
        except Exception as e:
            return False, {"error": str(e)}

# -------------------------------
# CoreBridge (local DB logs) - Modified for compatibility
# -------------------------------
class CoreBridge:
    DB_PATH = DB_PATH

    @staticmethod
    def init_db():
        conn = sqlite3.connect(CoreBridge.DB_PATH)
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS performance_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                performance_score REAL,
                hr INTEGER,
                heart_rate INTEGER,
                steps INTEGER,
                sleep_hours REAL,
                screen_time REAL,
                user_id INTEGER,
                job_id TEXT,
                ai_recommendation TEXT
            )
        ''')
        conn.commit()
        conn.close()

    @staticmethod
    def save_log(score, hr, steps, user_id=None, job_id=None, sleep_hours=None, screen_time=None):
        conn = sqlite3.connect(CoreBridge.DB_PATH)
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA table_info(performance_logs);")
            cols = [r[1] for r in cur.fetchall()]
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if "hr" in cols and "steps" in cols:
                cur.execute("INSERT INTO performance_logs (timestamp, performance_score, hr, steps, sleep_hours, screen_time, user_id, job_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (ts, score, hr, steps, sleep_hours, screen_time, user_id, job_id))
            elif "heart_rate" in cols and "steps" in cols:
                cur.execute("INSERT INTO performance_logs (timestamp, performance_score, heart_rate, steps, sleep_hours, screen_time, user_id, job_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (ts, score, hr, steps, sleep_hours, screen_time, user_id, job_id))
            else:
                cur.execute("INSERT INTO performance_logs (timestamp, performance_score, user_id, job_id) VALUES (?, ?, ?, ?)",
                            (ts, score, user_id, job_id))
            conn.commit()
        except Exception as e:
            LOG.exception("save_log failed: %s", e)
        finally:
            conn.close()

    @staticmethod
    def fetch_historical_data(limit: int = 20):
        try:
            conn = sqlite3.connect(CoreBridge.DB_PATH)
            df = pd.read_sql_query(f"SELECT * FROM performance_logs ORDER BY timestamp DESC LIMIT {limit}", conn)
            conn.close()
            return df
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def fetch_recent(limit: int = 20):
        # compatibility helper used by ChartPanel
        return CoreBridge.fetch_historical_data(limit=limit)

# -------------------------------
# SidebarControl
# -------------------------------
class SidebarControl:
    @staticmethod
    def render():
        with st.sidebar:
            st.markdown("<h2 style='color:#00ff88; font-family:Orbitron;'>🛡️ LUNA CORE</h2>", unsafe_allow_html=True)
            AuthManager.login_ui()
            hr_val = st.slider("💓 Heart Rate (BPM)", 40, 190, 75)
            step_val = st.number_input("👟 Daily Step Count", value=6000)
            sleep_val = st.number_input("😴 Sleep Hours", value=7.0)
            screen_val = st.number_input("📱 Screen Time (hrs)", value=3.0)
            init_sync = st.button("🚀 INITIATE SYSTEM SYNC")
            return hr_val, step_val, sleep_val, screen_val, init_sync

# -------------------------------
# SyncLogic (calls backend sync endpoint)
# -------------------------------
class SyncLogic:
    @staticmethod
    def process_sync(hr_val, step_val, sleep_val, screen_val, init_sync):
        if init_sync and AuthManager.is_authenticated():
            with st.spinner("Processing Neural Signals..."):
                payload = {
                    "hr": hr_val,
                    "steps": step_val,
                    "sleep_hours": sleep_val,
                    "screen_time": screen_val
                }
                ok, resp = BackendConnector.post("performance/sync", payload=payload, require_auth=True)
                if ok:
                    score = resp.get("performance_score") or resp.get("score") or 50.0
                    insight = resp.get("ai_insight") or resp.get("insight") or resp.get("ai_recommendation")
                    st.session_state.current_score = score
                    st.session_state.last_verdict = insight
                    CoreBridge.save_log(score, hr_val, step_val, user_id=st.session_state.get('auth', {}).get('user', {}).get('id'))
                    st.success("✅ Sync complete")
                    st.rerun()
                else:
                    st.error(f"Sync failed: {resp.get('error')}")

# -------------------------------
# Dashboard
# -------------------------------
class Dashboard:
    @staticmethod
    def render(hr_val, step_val):
        display_score = st.session_state.get('current_score', 50.0)
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=display_score,
            number={'font': {'color': 'white', 'family': 'Orbitron'}},
            gauge={'axis': {'range': [0, 100], 'tickcolor': "#00ff88"}, 'bar': {'color': "#00ff88"}}
        ))
        fig_gauge.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
        st.plotly_chart(fig_gauge, use_container_width=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='luna-card'><h4>💓 Heart Rate</h4><p>{hr_val} BPM</p></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='luna-card'><h4>👟 Steps</h4><p>{step_val} steps</p></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='luna-card'><h4>⚡ Performance</h4><p>{display_score} %</p></div>", unsafe_allow_html=True)

        hist_df = CoreBridge.fetch_historical_data()
        if not hist_df.empty:
            st.markdown("<h3 style='color:#00ff88;'>📈 Timeline</h3>", unsafe_allow_html=True)
            fig_line = px.area(hist_df.iloc[::-1], x='timestamp', y='performance_score')
            fig_line.update_traces(line_color='#00ff88', fillcolor='rgba(0,255,136,0.1)', line_width=3)
            fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, font={'color': "white"})
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No data yet.")

# -------------------------------
# ChartPanel - رسوم بيانية متقدمة وAlerts
# -------------------------------
class ChartPanel:
    """
    ChartPanel: يعرض تب منفصل يحتوي على ملخصات و رسوم بيانية تفاعلية
    - استخدام: ChartPanel.render_tab()
    - يعتمد على CoreBridge.fetch_recent(limit) الذي يعيد DataFrame
    """
    @staticmethod
    def _kpi_cards(score: float, hr: int, steps: int, sleep_hours: float):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("⚡ Performance", f"{score:.1f}%", delta=None)
        col2.metric("💓 Heart Rate", f"{hr} BPM")
        col3.metric("👟 Steps", f"{steps}")
        col4.metric("😴 Sleep Hours", f"{sleep_hours:.1f} hrs")

    @staticmethod
    def _time_series(df: pd.DataFrame, ma_window: int, show_ma: bool, show_anomalies: bool, anomaly_thresh: float):
        if df.empty or 'timestamp' not in df.columns or 'performance_score' not in df.columns:
            st.info("لا توجد بيانات زمنية كافية للعرض.")
            return

        df_ts = df.copy()
        df_ts['timestamp'] = pd.to_datetime(df_ts['timestamp'], errors='coerce')
        df_ts = df_ts.dropna(subset=['timestamp'])
        df_ts = df_ts.sort_values('timestamp')

        # compute moving average
        if ma_window > 1:
            df_ts['ma'] = df_ts['performance_score'].rolling(window=ma_window, min_periods=1).mean()
        else:
            df_ts['ma'] = df_ts['performance_score']

        # simple anomaly detection via z-score on residuals
        df_ts['residual'] = df_ts['performance_score'] - df_ts['ma']
        resid_mean = df_ts['residual'].mean() if not df_ts['residual'].empty else 0.0
        resid_std = df_ts['residual'].std(ddof=0) if not df_ts['residual'].empty else 1.0
        df_ts['zscore'] = (df_ts['residual'] - resid_mean) / (resid_std if resid_std != 0 else 1.0)
        df_ts['anomaly'] = df_ts['zscore'].abs() > anomaly_thresh

        # plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_ts['timestamp'], y=df_ts['performance_score'],
                                 mode='lines+markers', name='Performance', line=dict(color='#00ff88')))
        if show_ma:
            fig.add_trace(go.Scatter(x=df_ts['timestamp'], y=df_ts['ma'],
                                     mode='lines', name=f'MA ({ma_window})', line=dict(color='#66ffb2', dash='dash')))
        if show_anomalies:
            anomalies = df_ts[df_ts['anomaly']]
            if not anomalies.empty:
                fig.add_trace(go.Scatter(x=anomalies['timestamp'], y=anomalies['performance_score'],
                                         mode='markers', name='Anomalies', marker=dict(color='red', size=10, symbol='x')))
        fig.update_layout(title="📈 أداء عبر الزمن", xaxis_title="الزمن", yaxis_title="أداء (%)",
                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white', height=360)
        st.plotly_chart(fig, use_container_width=True)

        # show anomaly table if any
        if show_anomalies:
            if df_ts['anomaly'].any():
                st.markdown("#### ⚠️ تنبيهات: قيم شاذة")
                st.dataframe(df_ts[df_ts['anomaly']][['timestamp', 'performance_score', 'ma', 'zscore']].sort_values('timestamp', ascending=False))
            else:
                st.info("لا توجد قيم شاذة حسب العتبة الحالية.")

    @staticmethod
    def _distribution(df: pd.DataFrame):
        if df.empty:
            st.info("لا توجد بيانات كافية لعرض التوزيعات.")
            return
        cols = []
        if 'performance_score' in df.columns:
            cols.append('performance_score')
        if 'hr' in df.columns or 'heart_rate' in df.columns:
            if 'hr' in df.columns:
                df['hr_val'] = df['hr']
            else:
                df['hr_val'] = df['heart_rate']
            cols.append('hr_val')
        if not cols:
            st.info("لا توجد أعمدة قابلة للعرض في التوزيع.")
            return

        fig = make_subplots(rows=1, cols=len(cols), subplot_titles=[c.replace('_',' ').title() for c in cols])
        for i, c in enumerate(cols, start=1):
            fig.add_trace(go.Histogram(x=df[c].dropna(), nbinsx=20, marker_color='#00ff88', opacity=0.9), row=1, col=i)
            fig.update_xaxes(title_text=c.replace('_',' ').title(), row=1, col=i)
        fig.update_layout(height=320, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def _scatter_metrics(df: pd.DataFrame):
        if df.empty:
            return
        if 'performance_score' in df.columns and ('hr' in df.columns or 'heart_rate' in df.columns):
            df_sc = df.copy()
            if 'hr' in df_sc.columns:
                df_sc['hr_val'] = df_sc['hr']
            else:
                df_sc['hr_val'] = df_sc['heart_rate']
            df_sc = df_sc.dropna(subset=['performance_score', 'hr_val'])
            fig = px.scatter(df_sc, x='hr_val', y='performance_score', color='steps' if 'steps' in df_sc.columns else None,
                             size='steps' if 'steps' in df_sc.columns else None,
                             labels={'hr_val': 'Heart Rate (BPM)', 'performance_score': 'Performance (%)'},
                             title="🔬 علاقة معدل ضربات القلب بالأداء")
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white', height=360)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("مطلوب أعمدة performance_score و hr لعرض الرسم التبادلي.")

    @staticmethod
    def render_tab():
        st.markdown("<h3 style='color:#00ff88;'>📊 Charts & Insights (Advanced)</h3>", unsafe_allow_html=True)
        df = CoreBridge.fetch_recent(1000)

        # default KPIs from latest record
        if not df.empty:
            latest = df.iloc[0].to_dict()
            score = float(latest.get('performance_score') or 0.0)
            hr = int(latest.get('hr') or latest.get('heart_rate') or 0)
            steps = int(latest.get('steps') or 0)
            sleep_hours = float(latest.get('sleep_hours') or 0.0)
        else:
            score, hr, steps, sleep_hours = 0.0, 0, 0, 0.0

        ChartPanel._kpi_cards(score, hr, steps, sleep_hours)

        # Controls
        with st.expander("🔧 Controls"):
            col1, col2, col3 = st.columns(3)
            with col1:
                ma_window = st.number_input("نافذة المتوسط المتحرك (MA)", min_value=1, max_value=60, value=7, step=1)
                show_ma = st.checkbox("عرض المتوسط المتحرك", value=True)
            with col2:
                show_anomalies = st.checkbox("كشف القيم الشاذة (Anomalies)", value=True)
                anomaly_thresh = st.slider("عتبة z-score للكشف", min_value=1.0, max_value=5.0, value=2.5, step=0.1)
            with col3:
                smoothing = st.selectbox("تنعيم السلسلة (اختياري)", options=["None", "EWMA (alpha=0.3)", "EWMA (alpha=0.1)"], index=0)
                export_csv = st.checkbox("تمكين تنزيل CSV", value=True)

        # apply smoothing if requested
        if not df.empty and smoothing != "None":
            alpha = 0.3 if "0.3" in smoothing else 0.1
            if 'performance_score' in df.columns:
                df = df.sort_values('timestamp')
                df['performance_score'] = df['performance_score'].ewm(alpha=alpha).mean()

        # date filters
        with st.expander("🔎 فلتر البيانات"):
            if not df.empty and 'timestamp' in df.columns:
                try:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                    min_date = st.date_input("من تاريخ", value=df['timestamp'].min().date())
                    max_date = st.date_input("إلى تاريخ", value=df['timestamp'].max().date())
                    if min_date and max_date:
                        df = df[(df['timestamp'].dt.date >= min_date) & (df['timestamp'].dt.date <= max_date)]
                except Exception:
                    pass

        # Time series with MA and anomalies
        if not df.empty:
            ChartPanel._time_series(df, ma_window=ma_window, show_ma=show_ma, show_anomalies=show_anomalies, anomaly_thresh=anomaly_thresh)
        else:
            st.info("لا توجد بيانات لعرض الرسوم البيانية.")

        # other charts
        ChartPanel._distribution(df)
        ChartPanel._scatter_metrics(df)

        # export
        if export_csv and not df.empty:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ تنزيل البيانات (CSV)", data=csv, file_name="hpos_user_data.csv", mime="text/csv")

# -------------------------------
# NeuralChat (simple)
# -------------------------------
class NeuralChat:
    @staticmethod
    def render():
        st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>🧠 Neural Chat Box</h3>", unsafe_allow_html=True)
        verdict_msg = st.session_state.get('last_verdict', "في انتظار مزامنة البيانات...")
        st.markdown(f"<div class='luna-card'><b>LUNA Verdict:</b><br>{verdict_msg}</div>", unsafe_allow_html=True)

        if "messages" not in st.session_state:
            st.session_state.messages = []
        for msg in st.session_state.messages:
            icon = "👤" if msg["role"] == "user" else "🤖"
            st.markdown(f"<div style='padding:8px; border-bottom:1px solid #30363d;'><b>{icon}</b> {msg['content']}</div>", unsafe_allow_html=True)

        if prompt := st.chat_input("Send command to LUNA..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            assistant_reply = f"تم استلام الأمر: {prompt}. جاري التحليل..."
            st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
            st.rerun()

# -------------------------------
# BluetoothManager (optional)
# -------------------------------
class BluetoothManager:
    @staticmethod
    async def scan_devices():
        try:
            from bleak import BleakScanner
        except Exception:
            return []
        devices = await BleakScanner.discover()
        return devices

    @staticmethod
    async def connect_to_device(address):
        try:
            from bleak import BleakClient
        except Exception:
            return False, "BLE not available"
        try:
            async with BleakClient(address) as client:
                if client.is_connected:
                    return True, f"✅ Connected to {address}"
                else:
                    return False, f"❌ Failed to connect to {address}"
        except Exception as e:
            return False, f"⚠️ Error: {str(e)}"

    @staticmethod
    def render_ui():
        st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>🔵 Bluetooth Protocol</h3>", unsafe_allow_html=True)
        bt_status = st.checkbox("Enable Neural Link Scanner", value=False)
        if not bt_status:
            st.info("Bluetooth scanner is offline.")
            return
        st.success("Neural Link Scanner active.")
        if st.button("🔍 Scan Devices"):
            with st.spinner("Scanning for Bluetooth devices..."):
                try:
                    devices = asyncio.run(BluetoothManager.scan_devices())
                    if devices:
                        st.markdown("**Found devices:**")
                        for d in devices:
                            name = d.name or "Unknown"
                            st.write(f"📡 {name} — {d.address}")
                            if st.button(f"Connect to {d.address}", key=f"connect_{d.address}"):
                                with st.spinner(f"Connecting to {d.address}..."):
                                    success, msg = asyncio.run(BluetoothManager.connect_to_device(d.address))
                                    if success:
                                        st.success(msg)
                                    else:
                                        st.error(msg)
                    else:
                        st.warning("No devices found.")
                except Exception as e:
                    st.error(f"Bluetooth scan failed: {str(e)}")

# -------------------------------
# FacePanel (PIL-based, no cairosvg)  -- لم أغير تصميم الواجهة الأصلية، فقط حسّنت الاستقرار
# -------------------------------
class FacePanel:
    ICONS_DIR = "assets/icons"
    DEFAULT_SIZE = (900, 600)

    @staticmethod
    def _load_icon(name: str, size=(36,36)):
        path = os.path.join(FacePanel.ICONS_DIR, f"{name}.png")
        try:
            if os.path.exists(path):
                ic = Image.open(path).convert("RGBA")
                ic.thumbnail(size, Image.LANCZOS)
                return ic
        except Exception:
            pass
        return None

    @staticmethod
    def _draw_confidence_ring(draw: ImageDraw.Draw, center, radius, confidence, color=(0,255,136,200)):
        cx, cy = center
        bbox = [cx-radius, cy-radius, cx+radius, cy+radius]
        draw.ellipse(bbox, fill=(0,0,0,160))
        end_angle = int(360 * max(0.0, min(1.0, confidence)))
        draw.pieslice(bbox, start=-90, end=-90+end_angle, fill=color)
        inner = int(radius * 0.6)
        draw.ellipse([cx-inner, cy-inner, cx+inner, cy+inner], fill=(0,0,0,0))

    @staticmethod
    def _wrap_text(draw: ImageDraw.Draw, text: str, font: ImageFont.ImageFont, max_width: int):
        # Normalize whitespace and remove newlines to avoid accidental multi-line rendering
        text = " ".join(str(text).split())
        words = text.split()
        lines = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            try:
                tw = draw.textsize(test, font=font)[0]
            except Exception:
                tw = get_text_size(draw, test, font)[0]
            if tw <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        # Remove empty lines and collapse duplicates
        cleaned = []
        seen = set()
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            if ln in seen:
                continue
            seen.add(ln)
            cleaned.append(ln)
        return cleaned

    @staticmethod
    def render(image_path: Optional[str] = None, decision: Optional[Dict[str, Any]] = None, user_id: Optional[int] = None):
        w, h = FacePanel.DEFAULT_SIZE
        base = Image.new("RGBA", (w, h), (10, 12, 15, 255))

        try:
            if image_path and os.path.exists(image_path):
                face = Image.open(image_path).convert("RGBA")
                face.thumbnail((int(w*0.65), int(h*0.9)), Image.LANCZOS)
                fx = 20
                fy = (h - face.size[1]) // 2
                base.paste(face, (fx, fy), face)
            else:
                ph = Image.new("RGBA", (int(w*0.65), int(h*0.9)), (0,0,0,0))
                pd = ImageDraw.Draw(ph)
                pd.ellipse((40,40,ph.size[0]-40, ph.size[1]-40), fill=(30,40,60,255))
                fx = 20
                fy = (h - ph.size[1]) // 2
                base.paste(ph, (fx, fy), ph)
        except Exception:
            pass

        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        draw = ImageDraw.Draw(overlay)

        try:
            font_b = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
            font_s = ImageFont.truetype("DejaVuSans.ttf", 14)
        except Exception:
            font_b = ImageFont.load_default()
            font_s = ImageFont.load_default()

        badge_text = decision.get("decision_type", "No decision") if decision else "No decision"
        confidence_val = float(decision.get("confidence", 0.0)) if decision else 0.0
        explain = decision.get("reason", "Awaiting sync...") if decision else "No explanation yet."

        bx, by = 30, 20
        padding = (12, 8)
        tw, th = draw.textsize(badge_text, font=font_b)
        rect = [bx, by, bx + tw + padding[0]*2, by + th + padding[1]*2]
        draw.rounded_rectangle(rect, radius=10, fill=(0,0,0,160), outline=(0,255,136,200), width=2)
        draw.text((rect[0]+padding[0], rect[1]+padding[1]), badge_text, font=font_b, fill=(0,255,136,255))

        ring_center = (w - 90, 70)
        FacePanel._draw_confidence_ring(draw, ring_center, radius=48, confidence=confidence_val, color=(0,255,136,200))
        pct_text = f"{int(confidence_val*100)}%"
        tw2, th2 = draw.textsize(pct_text, font=font_b)
        draw.text((ring_center[0]-tw2/2, ring_center[1]-th2/2), pct_text, font=font_b, fill=(255,255,255,230))

        icons = [("health", "Health", "HR ok"), ("productivity", "Productivity", "Focus stable")]
        ix, iy = 30, 120
        for key, title, summary in icons:
            icon_img = FacePanel._load_icon(key, size=(36,36))
            box = [ix, iy, ix+220, iy+44]
            draw.rounded_rectangle(box, radius=8, fill=(0,0,0,120), outline=(255,255,255,20))
            if icon_img:
                overlay.paste(icon_img, (ix+8, iy+4), icon_img)
                text_x = ix + 8 + icon_img.size[0] + 8
            else:
                draw.text((ix+8, iy+8), "💓" if key=="health" else "🧭", font=font_s, fill=(200,255,220,255))
                text_x = ix + 8 + 28
            draw.text((text_x, iy+6), title, font=font_s, fill=(200,255,220,255))
            draw.text((text_x, iy+22), summary, font=font_s, fill=(180,230,200,220))
            iy += 56

        bar_h = 84
        rect2 = [30, h - bar_h - 20, w - 30, h - 20]
        draw.rounded_rectangle(rect2, radius=10, fill=(0,0,0,160))
        max_w = rect2[2] - rect2[0] - 20
        lines = FacePanel._wrap_text(draw, explain, font_s, max_w)
        y_text = rect2[1] + 10
        for ln in lines[:4]:
            draw.text((rect2[0]+10, y_text), ln, font=font_s, fill=(230,238,243,255))
            y_text += draw.textsize(ln, font=font_s)[1] + 4

        hist_box = [w-260, 120, w-40, 260]
        draw.rounded_rectangle(hist_box, radius=10, fill=(0,0,0,120), outline=(0,255,136,80))
        draw.text((hist_box[0]+10, hist_box[1]+8), "Recent decisions", font=font_b, fill=(0,255,136,255))
        yy = hist_box[1] + 36
        recent = (decision.get("recent", []) if decision else [])[:3]
        if not recent:
            draw.text((hist_box[0]+10, yy), "- No recent decisions", font=font_s, fill=(220,240,230,230))
        else:
            for r in recent:
                ts = r.get("created_at", "")[:16]
                typ = r.get("decision_type", "—")
                confs = f"{int(r.get('confidence',0)*100)}%"
                draw.text((hist_box[0]+10, yy), f"{ts} • {typ} • {confs}", font=font_s, fill=(220,240,230,230))
                yy += 22

        composed = Image.alpha_composite(base, overlay)
        buf = io.BytesIO()
        composed.save(buf, format="PNG")
        buf.seek(0)
        return buf.getvalue()

    @staticmethod
    def _submit_feedback_ui(decision_id: Optional[int], feedback_type: str = "accepted", user_id: Optional[int] = None):
        if not decision_id:
            st.warning("No decision id available to attach feedback.")
            return
        payload = {
            "feedback_type": feedback_type,
            "adherence": True if feedback_type == "accepted" else False,
            "notes": f"User {feedback_type} via UI",
            "observed_effect": {"delta_score": 0.0, "window_hours": 24}
        }
        ok, resp = BackendConnector.post(f"decision/{decision_id}/feedback", payload=payload, require_auth=True)
        if ok:
            st.success("Feedback submitted.")
        else:
            st.error(f"Feedback failed: {resp.get('error')}")

# -------------------------------
# Client integration: submit evaluation + WS listener + polling fallback
# -------------------------------
def submit_evaluation_to_backend(payload: dict) -> dict:
    try:
        ok, resp = BackendConnector.post("decision/evaluate", payload=payload, require_auth=True)
        if ok:
            return {"ok": True, "decision_id": resp.get("decision_id"), "decision": resp.get("decision")}
        return {"ok": False, "error": resp.get("error")}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def poll_decision_status(decision_id: str, timeout: int = 60) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        ok, resp = BackendConnector.get(f"decision/{decision_id}/status", require_auth=True)
        if ok:
            status = resp.get("status")
            if status == "done":
                ok2, rec = BackendConnector.get(f"decision/{decision_id}", require_auth=True)
                if ok2:
                    return {"status":"done", "decision": rec.get("final_decision") or rec.get("decision") or rec.get("final_decision", {})}
        time.sleep(1.5)
    return {"status":"timeout"}

def _ws_thread(decision_id: str):
    if not WS_BASE:
        return
    try:
        import websocket
    except Exception:
        return
    url = f"{WS_BASE}/ws/decisions/{decision_id}"
    def on_message(ws, message):
        try:
            data = json.loads(message)
            if data.get("status") == "done":
                st.session_state.face_result = data.get("decision")
                st.session_state.face_stage = "done"
                try:
                    st.experimental_rerun()
                except Exception:
                    pass
        except Exception:
            pass
    def on_error(ws, error):
        pass
    def on_close(ws, close_status_code, close_msg):
        pass
    def on_open(ws):
        pass
    try:
        ws = websocket.WebSocketApp(url, on_message=on_message, on_error=on_error, on_close=on_close, on_open=on_open)
        ws.run_forever()
    except Exception:
        pass

def evaluate_face_flow(hr_val, step_val, sleep_val, screen_val, image_path=None):
    payload = {"user_id": None, "hr": hr_val, "steps": step_val, "sleep_hours": sleep_val, "screen_time": screen_val}
    submit_resp = submit_evaluation_to_backend(payload)
    if not submit_resp.get("ok"):
        st.error(f"Submit failed: {submit_resp.get('error')}")
        return None
    decision_id = submit_resp.get("decision_id")
    st.session_state.face_stage = "queued"
    st.session_state.face_decision_id = decision_id
    if submit_resp.get("decision"):
        st.session_state.face_result = submit_resp.get("decision")
        st.session_state.face_stage = "done"
    try:
        t = threading.Thread(target=_ws_thread, args=(decision_id,), daemon=True)
        t.start()
    except Exception:
        pass
    def poll_fallback():
        res = poll_decision_status(decision_id, timeout=30)
        if res.get("status") == "done":
            st.session_state.face_result = res.get("decision")
            st.session_state.face_stage = "done"
            try:
                st.experimental_rerun()
            except Exception:
                pass
    threading.Thread(target=poll_fallback, daemon=True).start()
    return decision_id

# -------------------------------
# MainApp
# -------------------------------
class MainApp:
    @staticmethod
    def run():
        SystemUI.setup()
        CoreBridge.init_db()

        hr_val, step_val, sleep_val, screen_val, init_sync = SidebarControl.render()
        SyncLogic.process_sync(hr_val, step_val, sleep_val, screen_val, init_sync)

        st.markdown("<h1 class='main-title'>Human Performance OS v2.0</h1>", unsafe_allow_html=True)
        # أضفت تب Charts دون تغيير بقية الواجهة
        tab_metrics, tab_chat, tab_bt, tab_face, tab_charts = st.tabs(["📊 SYSTEM METRICS", "🤖 NEURAL CHAT", "🔵 BLUETOOTH", "🖼️ FACE", "📈 CHARTS"])

        with tab_metrics:
            Dashboard.render(hr_val, step_val)

        with tab_chat:
            NeuralChat.render()

        with tab_bt:
            BluetoothManager.render_ui()

        with tab_face:
            st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>🖼️ Face Panel</h3>", unsafe_allow_html=True)
            uploaded = st.file_uploader("Upload face image", type=["png","jpg","jpeg"])
            image_path = None
            if uploaded:
                username = st.session_state.get('auth', {}).get('user', {}).get('username', 'anon')
                image_path = f"temp_face_{username}.png"
                try:
                    with open(image_path, "wb") as f:
                        f.write(uploaded.getbuffer())
                except Exception as e:
                    LOG.exception("Failed to save uploaded image: %s", e)
                    st.error("Failed to save uploaded image")

            # existing face UI actions (unchanged)
            if st.button("Evaluate face (legacy flow)"):
                # legacy evaluate flow example (keeps compatibility)
                evaluate_face_flow(hr_val, step_val, sleep_val, screen_val, image_path=image_path)

        with tab_charts:
            ChartPanel.render_tab()

        st.markdown("---")
        st.markdown("### History")
        df = CoreBridge.fetch_historical_data(10)
        if not df.empty:
            st.dataframe(df)
        else:
            st.info("No historical logs yet.")

if __name__ == "__main__":
    MainApp.run()
