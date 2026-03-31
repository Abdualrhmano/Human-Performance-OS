# -------------------------------
# PART 1/3
# LIBRARIES, UI CONFIG, DATABASE BRIDGE
# -------------------------------

# المكتبات الأساسية (موجودة هنا في أول كلاس كما طلبت)
import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import random
import asyncio
from bleak import BleakScanner, BleakClient

# -------------------------------
# 1. SystemUI: إعداد الواجهة والمظهر العام
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
            .chat-box { border: 1px solid #30363d; border-radius: 12px; padding: 15px; background: rgba(0,0,0,0.3); height: 400px; overflow-y: auto; }
            .luna-card { background: rgba(0,255,136,0.1); border: 1px solid #00ff88; padding: 15px; border-radius: 10px; border-left: 5px solid #00ff88; margin-bottom: 15px; }
            </style>
        """, unsafe_allow_html=True)

# -------------------------------
# 2. CoreBridge: جسر قاعدة البيانات والتحليلات
# -------------------------------
class CoreBridge:
    DB_PATH = "human_performance_v2.db"

    @staticmethod
    def init_db():
        conn = sqlite3.connect(CoreBridge.DB_PATH)
        conn.execute('''CREATE TABLE IF NOT EXISTS performance_logs 
                        (timestamp TEXT, performance_score REAL, hr INTEGER, steps INTEGER)''')
        conn.commit()
        conn.close()

    @staticmethod
    def save_log(score, hr, steps):
        conn = sqlite3.connect(CoreBridge.DB_PATH)
        query = "INSERT INTO performance_logs (timestamp, performance_score, hr, steps) VALUES (?, ?, ?, ?)"
        conn.execute(query, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), score, hr, steps))
        conn.commit()
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
    def get_luna_verdict(score, hr, steps):
        hr_advice = "🟢 نبض مستقر"
        if hr > 110:
            hr_advice = "⚠️ معدل النبض مرتفع جداً؛ يرجى ممارسة تمارين التنفس"
        elif hr < 50:
            hr_advice = "💤 النبض منخفض؛ قد تكون في حالة خمول"
        
        activity_advice = "🏃 استمر في التحرك لكسر حالة الخمول" if steps < 3000 else "💪 أداء حركي ممتاز"
        
        if score >= 80:
            status = "🔥 أداؤك في القمة!"
        elif score >= 50:
            status = "🟢 مستقر. حافظ على روتينك الحالي"
        else:
            status = "🔴 يوصى بالراحة الآن"
        
        return f"{status}\n\n{hr_advice}\n\n{activity_advice}"
       # -------------------------------
# PART 2/3
# SIDEBAR CONTROL, SYNC LOGIC, DASHBOARD
# -------------------------------

# -------------------------------
# 3. SidebarControl: عناصر التحكم في الشريط الجانبي
# -------------------------------
class SidebarControl:
    @staticmethod
    def render():
        with st.sidebar:
            st.markdown("<h2 style='color:#00ff88; font-family:Orbitron;'>🛡️ LUNA CORE</h2>", unsafe_allow_html=True)
            
            # مدخلات المستخدم
            hr_val = st.slider("💓 Heart Rate (BPM)", 40, 190, 75)
            step_val = st.number_input("👟 Daily Step Count", value=6000)
            
            # زر المزامنة
            init_sync = st.button("🚀 INITIATE SYSTEM SYNC")
            
            return hr_val, step_val, init_sync

# -------------------------------
# 4. SyncLogic: منطق المزامنة والمعالجة
# -------------------------------
class SyncLogic:
    @staticmethod
    def process_sync(hr_val, step_val, init_sync):
        if init_sync:
            with st.spinner("Processing Neural Signals..."):
                # توليد نتيجة عشوائية بين 30 و 95
                generated_score = round(random.uniform(30, 95), 1)
                
                # حفظ النتيجة في session
                st.session_state.current_score = generated_score
                st.session_state.last_verdict = CoreBridge.get_luna_verdict(generated_score, hr_val, step_val)
                
                # حفظ النتيجة في قاعدة البيانات
                CoreBridge.save_log(generated_score, hr_val, step_val)
                
                # إعادة تشغيل واجهة المستخدم لتحديث القيم
                st.rerun()

# -------------------------------
# 5. Dashboard: العرض الرئيسي، البطاقات، والـ Timeline
# -------------------------------
class Dashboard:
    @staticmethod
    def render(hr_val, step_val):
        display_score = st.session_state.get('current_score', 50.0)

        # العداد الرئيسي للأداء
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=display_score,
            number={'font': {'color': 'white', 'family': 'Orbitron'}},
            gauge={'axis': {'range': [0, 100], 'tickcolor': "#00ff88"}, 'bar': {'color': "#00ff88"}}
        ))
        fig_gauge.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
        st.plotly_chart(fig_gauge, use_container_width=True)

        # تحديد لون البطاقة حسب القيم
        hr_color = "#00ff88"
        if hr_val > 110:
            hr_color = "#ff4b4b"
        elif hr_val < 50:
            hr_color = "#4b9bff"

        step_color = "#00ff88"
        if step_val < 3000:
            step_color = "#ffa500"

        perf_color = "#00ff88"
        if display_score < 50:
            perf_color = "#ff4b4b"
        elif display_score >= 80:
            perf_color = "#4bff4b"

        # بطاقات إضافية لمعدل النبض والخطوات والأداء
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
                <div class='luna-card' style='border-left:5px solid {hr_color}; border-color:{hr_color};'>
                    <h4 style='color:{hr_color}; font-family:Orbitron;'>💓 Heart Rate</h4>
                    <p style='font-size:1.2em; color:white;'>{hr_val} BPM</p>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                <div class='luna-card' style='border-left:5px solid {step_color}; border-color:{step_color};'>
                    <h4 style='color:{step_color}; font-family:Orbitron;'>👟 Steps</h4>
                    <p style='font-size:1.2em; color:white;'>{step_val} steps</p>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
                <div class='luna-card' style='border-left:5px solid {perf_color}; border-color:{perf_color};'>
                    <h4 style='color:{perf_color}; font-family:Orbitron;'>⚡ Performance</h4>
                    <p style='font-size:1.2em; color:white;'>{display_score} %</p>
                </div>
            """, unsafe_allow_html=True)

        # الـ Timeline
        hist_df = CoreBridge.fetch_historical_data()
        if not hist_df.empty:
            st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>📈 Timeline</h3>", unsafe_allow_html=True)
            fig_line = px.area(hist_df.iloc[::-1], x='timestamp', y='performance_score')
            fig_line.update_traces(line_color='#00ff88', fillcolor='rgba(0,255,136,0.1)', line_width=3)
            fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, font={'color': "white"})
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No data yet.")
# -------------------------------
# PART 3/3
# NEURAL CHAT, BLUETOOTH MANAGER, MAIN APP
# -------------------------------

# -------------------------------
# 6. NeuralChat: صندوق المحادثة مع LUNA + بطاقة Verdict
# -------------------------------
class NeuralChat:
    @staticmethod
    def render():
        st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>🧠 Neural Chat Box</h3>", unsafe_allow_html=True)
        
        # بطاقة LUNA Verdict
        verdict_msg = st.session_state.get('last_verdict', "في انتظار مزامنة البيانات...")
        st.markdown(f"<div class='luna-card'><b>LUNA Verdict:</b><br>{verdict_msg}</div>", unsafe_allow_html=True)

        # صندوق الشات
        chat_container = st.container()
        with chat_container:
            if "messages" not in st.session_state:
                st.session_state.messages = []
            for msg in st.session_state.messages:
                icon = "👤" if msg["role"] == "user" else "🤖"
                st.markdown(f"<div style='padding:8px; border-bottom:1px solid #30363d;'><b>{icon}</b> {msg['content']}</div>", unsafe_allow_html=True)
        
        # إدخال رسالة جديدة
        if prompt := st.chat_input("Send command to LUNA..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            # هنا يمكن ربط المنطق الحقيقي لمعالجة الأوامر؛ حالياً نرد برد تجريبي
            assistant_reply = f"تم استلام الأمر: {prompt}. جاري التحليل..."
            st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
            st.rerun()

# -------------------------------
# 7. BluetoothManager: إدارة المسح والاتصال عبر البلوتوث
# -------------------------------
class BluetoothManager:
    @staticmethod
    async def scan_devices():
        """البحث عن أجهزة بلوتوث قريبة"""
        devices = await BleakScanner.discover()
        return devices

    @staticmethod
    async def connect_to_device(address):
        """الاتصال بجهاز بلوتوث عبر العنوان"""
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
        """واجهة المستخدم للتحكم في البلوتوث داخل تبويب البلوتوث"""
        st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>🔵 Bluetooth Protocol</h3>", unsafe_allow_html=True)
        
        # تفعيل/تعطيل الماسح
        bt_status = st.checkbox("Enable Neural Link Scanner", value=False)
        
        if not bt_status:
            st.info("Bluetooth scanner is offline.")
            return

        st.success("Neural Link Scanner active. You can scan for devices or connect by address.")
        
        # زر المسح
        if st.button("🔍 Scan Devices"):
            with st.spinner("Scanning for Bluetooth devices..."):
                try:
                    devices = asyncio.run(BluetoothManager.scan_devices())
                    if devices:
                        st.markdown("**Found devices:**")
                        for d in devices:
                            name = d.name or "Unknown"
                            st.write(f"📡 {name} — {d.address}")
                            # زر اتصال لكل جهاز
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

        # اتصال يدوي عبر العنوان
        address_input = st.text_input("Or enter device address to connect (e.g., AA:BB:CC:DD:EE:FF)")
        if address_input and st.button("Connect to Address"):
            with st.spinner(f"Connecting to {address_input}..."):
                try:
                    success, msg = asyncio.run(BluetoothManager.connect_to_device(address_input))
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                except Exception as e:
                    st.error(f"Connection attempt failed: {str(e)}")

# -------------------------------
# 8. MainApp: ربط كل الكلاسات وتشغيل التطبيق
# -------------------------------
class MainApp:
    @staticmethod
    def run():
        # 1. إعداد الواجهة
        SystemUI.setup()
        
        # 2. تهيئة قاعدة البيانات
        CoreBridge.init_db()
        
        # 3. عرض عناصر التحكم في الـ Sidebar
        hr_val, step_val, init_sync = SidebarControl.render()
        
        # 4. تشغيل منطق المزامنة (إذا تم الضغط)
        SyncLogic.process_sync(hr_val, step_val, init_sync)
        
        # 5. عرض العنوان الرئيسي
        st.markdown("<h1 class='main-title'>Human Performance OS v2.0</h1>", unsafe_allow_html=True)
        
        # 6. إنشاء التبويبات (Metrics, Chat, Bluetooth)
        tab_metrics, tab_chat, tab_bt = st.tabs(["📊 SYSTEM METRICS", "🤖 NEURAL CHAT", "🔵 BLUETOOTH"])
        
        # 7. عرض الـ Dashboard
        with tab_metrics:
            Dashboard.render(hr_val, step_val)
        
        # 8. عرض صندوق المحادثة
        with tab_chat:
            NeuralChat.render()
        
        # 9. عرض واجهة البلوتوث
        with tab_bt:
            BluetoothManager.render_ui()


# -------------------------------
# تشغيل التطبيق
# -------------------------------
if __name__ == "__main__":
    MainApp.run()
