# ======================================================
# SYSTEM: Human Performance OS v2.0 (PART 1)
# ARCHITECT: Abdulrahman (Lead Software Engineer)
# MODULE: LOGIC, BLE & NEURAL SIMULATION ENGINE
# ======================================================

import streamlit as st
import requests
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import asyncio
import random
from bleak import BleakClient, BleakScanner

# ------------------------------------------------------
# 1. PROFESSIONAL UI CONFIGURATION
# ------------------------------------------------------
class SystemUI:
    @staticmethod
    def setup():
        st.set_page_config(page_title="Human Performance OS v2.0", page_icon="🧠", layout="wide")
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono:wght@300;500&display=swap');
            :root { --primary: #00ff88; --bg: #05070a; --card-bg: rgba(13, 17, 23, 0.9); }
            html, body, [data-testid="stSidebar"] { font-family: 'JetBrains Mono', monospace; background-color: var(--bg); }
            .main-title { font-family: 'Orbitron', sans-serif; color: var(--primary); text-shadow: 0 0 15px rgba(0, 255, 136, 0.4); font-size: 3.2em; text-align: center; margin-bottom: 0px; }
            .ai-insight-card { background: linear-gradient(145deg, rgba(0,255,136,0.05), rgba(0,0,0,0.5)); border-left: 5px solid var(--primary); padding: 25px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
            </style>
        """, unsafe_allow_html=True)

# ------------------------------------------------------
# 2. ADVANCED HYBRID BLUETOOTH ENGINE (تطوير المحاكاة)
# ------------------------------------------------------
class BluetoothEngine:
    HR_SERVICE_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

    @staticmethod
    async def scan_active_devices():
        """البحث عن الأجهزة الحقيقية أو توفير أجهزة محاكاة في حال فشل الاتصال بالسحاب"""
        try:
            devices = await BleakScanner.discover(timeout=2.0)
            if devices:
                return {d.name if d.name else f"Unknown ({d.address})": d.address for d in devices}
            raise Exception("No real devices found")
        except:
            # نظام المحاكاة للعمل في بيئة Codespaces
            return {
                "LUNA-Watch-Pro (Simulated)": "SIM:DEVICE:01",
                "Bio-Neural-Link (Simulated)": "SIM:DEVICE:02"
            }

    @staticmethod
    async def fetch_live_biometrics(address):
        """جلب البيانات من حساس حقيقي أو توليد بيانات محاكاة ذكية"""
        if "SIM" in str(address):
            await asyncio.sleep(1.5) # محاكاة وقت المعالجة
            return random.randint(65, 85)
            
        try:
            async with BleakClient(address, timeout=10.0) as client:
                if await client.is_connected():
                    raw_data = await client.read_gatt_char(BluetoothEngine.HR_SERVICE_UUID)
                    return raw_data[1]
                return None
        except Exception as e:
            st.sidebar.error(f"Hardware Link Error: {str(e)}")
            return None

# ------------------------------------------------------
# 3. CORE SYSTEM BRIDGE
# ------------------------------------------------------
class CoreBridge:
    DB_PATH = 'human_performance_v2.db'
    API_ENDPOINT = "http://localhost:8000/api/v2"

    @staticmethod
    def fetch_historical_data():
        try:
            conn = sqlite3.connect(CoreBridge.DB_PATH)
            df = pd.read_sql_query("SELECT * FROM performance_logs ORDER BY timestamp DESC LIMIT 15", conn)
            conn.close()
            return df
        except: return pd.DataFrame()

    @staticmethod
    def sync_neural_data(token, payload):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            response = requests.post(f"{CoreBridge.API_ENDPOINT}/performance/sync", json=payload, headers=headers)
            return response.json() if response.status_code == 200 else None
        except: return None
# ======================================================
# SYSTEM: Human Performance OS v2.0 (PART 2)
# MODULE: DASHBOARD RENDERER & UI INTERACTION
# ======================================================

# التشغيل الأولي لإعدادات الواجهة
SystemUI.setup()

# --- Sidebar Control Center ---
with st.sidebar:
    st.markdown("<h2 style='color:#00ff88; font-family:Orbitron;'>🔐 SECURITY</h2>", unsafe_allow_html=True)
    auth_token = st.text_input("NEURAL ACCESS KEY", type="password", placeholder="Enter JWT...")
    
    st.divider()
    st.markdown("<h2 style='color:#00ff88; font-family:Orbitron;'>📡 TELEMETRY</h2>", unsafe_allow_html=True)
    
    input_mode = st.toggle("Live Bluetooth Mode", value=False)
    
    selected_address = None
    if input_mode:
        if st.button("🔍 Scan for Active Devices"):
            with st.spinner("Scanning BLE Frequencies..."):
                # استدعاء المحرك الهجين (حقيقي/محاكي)
                st.session_state.ble_devices = asyncio.run(BluetoothEngine.scan_active_devices())
        
        if "ble_devices" in st.session_state and st.session_state.ble_devices:
            dev_name = st.selectbox("Select Target Device:", options=list(st.session_state.ble_devices.keys()))
            selected_address = st.session_state.ble_devices[dev_name]
            st.success(f"Linked: {selected_address}")
    
    st.divider()
    hr_val = st.slider("💓 Heart Rate (BPM)", 40, 190, 75)
    step_val = st.number_input("👟 Daily Step Count", value=6000)
    screen_val = st.slider("📱 Digital Exposure (H)", 0.0, 16.0, 5.0)
    sleep_val = st.slider("🌙 Circadian Rest (H)", 0.0, 12.0, 7.5)
    
    init_sync = st.button("🚀 INITIATE SYSTEM SYNC", use_container_width=True)

# --- Main Dashboard ---
st.markdown("<h1 class='main-title'>Human Performance OS v2.0</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#8b949e;'>Neural-Biometric Command Center | Senior Engineer: Abdulrahman</p>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

if init_sync:
    if not auth_token:
        st.warning("⚠️ Authentication key missing. Neural sync aborted.")
    else:
        active_hr = hr_val
        # ميزة البلوتوث (الحية أو المحاكاة)
        if input_mode and selected_address:
            with st.spinner(f"Establishing link..."):
                ble_hr = asyncio.run(BluetoothEngine.fetch_live_biometrics(selected_address))
                if ble_hr: active_hr = ble_hr
        
        with st.spinner("Processing Biometric Data..."):
            data_payload = {"heart_rate": active_hr, "steps": step_val, "screen_time": screen_val, "sleep_hours": sleep_val}
            sync_result = CoreBridge.sync_neural_data(auth_token, data_payload)
            
            if sync_result:
                st.toast("System Sync Complete", icon="✅")
                col_g, col_i = st.columns([1, 1.5], gap="large")
                
                with col_g:
                    fig = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = sync_result['performance_score'],
                        title = {'text': "PERFORMANCE INDEX", 'font': {'color': '#00ff88', 'family': 'Orbitron', 'size': 18}},
                        gauge = {
                            'axis': {'range': [0, 100], 'tickcolor': "#00ff88"},
                            'bar': {'color': "#00ff88"},
                            'bgcolor': "rgba(0,0,0,0)",
                            'threshold': {'line': {'color': "white", 'width': 4}, 'value': sync_result['performance_score']}
                        }
                    ))
                    fig.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig, use_container_width=True)
                
                with col_i:
                    source_label = 'Simulated Hardware' if "SIM" in str(selected_address) else ('Real Sensor' if input_mode else 'Manual Override')
                    st.markdown(f"""
                        <div class="ai-insight-card">
                            <h3 style="color:#00ff88; margin-top:0;">🤖 Neural Analysis Verdict</h3>
                            <p style="font-size:1.2em; line-height:1.6;">{sync_result['ai_insight']}</p>
                            <hr style="border: 0.5px solid rgba(0,255,136,0.2)">
                            <p style="color:#8b949e; font-size:0.9em;">
                                <b>Source:</b> {source_label} | 
                                <b>Telemetry:</b> HR {active_hr} BPM / Steps {step_val}
                            </p>
                        </div>
                    """, unsafe_allow_html=True)

# --- Analytics History ---
st.divider()
st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>📊 Performance History</h3>", unsafe_allow_html=True)
history_df = CoreBridge.fetch_historical_data()

if not history_df.empty:
    fig_hist = px.area(history_df, x='timestamp', y='performance_score')
    fig_hist.update_traces(line_color='#00ff88', fillcolor='rgba(0, 255, 136, 0.1)', line_width=4)
    fig_hist.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, color="#8b949e"),
        yaxis=dict(showgrid=True, gridcolor="#161b22", color="#8b949e"),
        height=350, margin=dict(l=0, r=0, t=20, b=0)
    )
    st.plotly_chart(fig_hist, use_container_width=True)
    
    with st.expander("View Raw Logs"):
        st.dataframe(history_df, use_container_width=True)

st.markdown(f"<div style='text-align:center; margin-top:50px; color:#30363d;'>Human Performance OS v2.0 | SECURE BIOMETRIC GATEWAY | {datetime.now().year}</div>", unsafe_allow_html=True)
