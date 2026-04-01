# streamlit_app_with_facepanel.py
# Human Performance OS - Streamlit UI with FacePanel integration (FacePanel replaced with PIL-based implementation)
# Integrated FacePanel: decision badge, confidence, explain, agent icons, feedback buttons
# Note: This version avoids cairosvg and external TTF dependencies for better portability.

# -------------------------------
# PART 1/4
# LIBRARIES, UI CONFIG, AUTH, BACKEND CONNECTOR
# -------------------------------

# المكتبات الأساسية
import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
import requests
import asyncio
from datetime import datetime
import random
from bleak import BleakScanner, BleakClient
from typing import Tuple, Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont
import io
import os

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
# 2. AuthManager: تسجيل الدخول والخروج وإدارة التوكن
# -------------------------------
class AuthManager:
    LOGIN_ENDPOINT = "http://localhost:8000/api/v2/auth/login"
    REGISTER_ENDPOINT = "http://localhost:8000/api/v2/auth/register"

    @staticmethod
    def init_session():
        if "auth" not in st.session_state:
            st.session_state.auth = {"is_authenticated": False, "token": None, "user": None}

    @staticmethod
    def login(username: str, password: str) -> Tuple[bool, dict]:
        AuthManager.init_session()
        try:
            resp = requests.post(AuthManager.LOGIN_ENDPOINT, data={"username": username, "password": password})
            if resp.status_code == 200:
                data = resp.json()
                # store token and minimal user info; backend token may include user_id
                st.session_state.auth.update({
                    "is_authenticated": True,
                    "token": data.get("access_token"),
                    "user": {"username": username}
                })
                return True, data
            return False, {"error": resp.text}
        except Exception as e:
            return False, {"error": str(e)}

    @staticmethod
    def register(username: str, password: str) -> Tuple[bool, dict]:
        try:
            resp = requests.post(AuthManager.REGISTER_ENDPOINT, json={"username": username, "password": password})
            if resp.status_code == 200:
                return True, resp.json()
            return False, {"error": resp.text}
        except Exception as e:
            return False, {"error": str(e)}

    @staticmethod
    def logout():
        st.session_state.auth = {"is_authenticated": False, "token": None, "user": None}

    @staticmethod
    def is_authenticated() -> bool:
        AuthManager.init_session()
        return bool(st.session_state.auth.get("is_authenticated", False))

    @staticmethod
    def get_token() -> Optional[str]:
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
        if st.button("Sign In"):
            ok, resp = AuthManager.login(username, password)
            if ok:
                st.success("Signed in successfully.")
                st.experimental_rerun()
            else:
                st.error(f"Login failed: {resp.get('error')}")
        if st.button("Register"):
            ok, resp = AuthManager.register(username, password)
            if ok:
                st.success("Registered successfully. Please login.")
            else:
                st.error(f"Register failed: {resp.get('error')}")
        return False

# -------------------------------
# 3. BackendConnector: الاتصال بالباك اند
# -------------------------------
class BackendConnector:
    BASE_URL = "http://localhost:8000/api/v2"

    @staticmethod
    def _full_url(path: str) -> str:
        return f"{BackendConnector.BASE_URL.rstrip('/')}/{path.lstrip('/')}"

    @staticmethod
    def get(path: str, params: dict = None, require_auth: bool = True) -> Tuple[bool, dict]:
        url = BackendConnector._full_url(path)
        headers = {}
        if require_auth:
            headers.update(AuthManager.get_auth_header())
        try:
            resp = requests.get(url, params=params or {}, headers=headers)
            resp.raise_for_status()
            return True, resp.json()
        except requests.RequestException as e:
            return False, {"error": str(e)}

    @staticmethod
    def post(path: str, payload: dict = None, require_auth: bool = True) -> Tuple[bool, dict]:
        url = BackendConnector._full_url(path)
        headers = {"Content-Type": "application/json"}
        if require_auth:
            headers.update(AuthManager.get_auth_header())
        try:
            resp = requests.post(url, json=payload or {}, headers=headers)
            resp.raise_for_status()
            return True, resp.json()
        except requests.RequestException as e:
            return False, {"error": str(e)}

# -------------------------------
# PART 2/4
# CORE BRIDGE, SIDEBAR CONTROL, SYNC LOGIC, DASHBOARD
# -------------------------------

# -------------------------------
# 4. CoreBridge: قاعدة البيانات المحلية (للتاريخ فقط)
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

# -------------------------------
# 5. SidebarControl: عناصر التحكم في الشريط الجانبي
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
# 6. SyncLogic: المزامنة مع الباك اند
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
                    # backend may return performance_score and ai_insight
                    score = resp.get("performance_score") or resp.get("score") or 50.0
                    insight = resp.get("ai_insight") or resp.get("insight") or resp.get("ai_recommendation")
                    st.session_state.current_score = score
                    st.session_state.last_verdict = insight
                    CoreBridge.save_log(score, hr_val, step_val)
                    st.success("✅ Sync complete")
                    st.rerun()
                else:
                    st.error(f"Sync failed: {resp.get('error')}")

# -------------------------------
# 7. Dashboard: العرض الرئيسي
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
# PART 3/4
# NEURAL CHAT, BLUETOOTH MANAGER
# -------------------------------

# -------------------------------
# 8. NeuralChat: صندوق المحادثة مع LUNA + بطاقة Verdict
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
            assistant_reply = f"تم استلام الأمر: {prompt}. جاري التحليل..."
            st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
            st.rerun()

# -------------------------------
# 9. BluetoothManager: إدارة المسح والاتصال عبر البلوتوث
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
        
        bt_status = st.checkbox("Enable Neural Link Scanner", value=False)
        
        if not bt_status:
            st.info("Bluetooth scanner is offline.")
            return

        st.success("Neural Link Scanner active. You can scan for devices or connect by address.")
        
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
# FacePanel: PIL-based implementation (no cairosvg dependency)
# -------------------------------
class FacePanel:
    ICONS_DIR = "assets/icons"  # اختياري: ضع أيقونات PNG هنا باسم health.png, productivity.png
    DEFAULT_SIZE = (900, 600)

    @staticmethod
    def _load_icon(name: str, size=(36,36)):
        """حاول تحميل أيقونة PNG من assets/icons، وإلا ارجع None."""
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
        """ارسم حلقة ثقة بسيطة باستخدام pieslice وinner circle."""
        cx, cy = center
        bbox = [cx-radius, cy-radius, cx+radius, cy+radius]
        # خلفية داكنة
        draw.ellipse(bbox, fill=(0,0,0,160))
        # جزء النسبة
        end_angle = int(360 * max(0.0, min(1.0, confidence)))
        draw.pieslice(bbox, start=-90, end=-90+end_angle, fill=color)
        # inner circle لعمل حلقة
        inner = int(radius * 0.6)
        draw.ellipse([cx-inner, cy-inner, cx+inner, cy+inner], fill=(0,0,0,0))

    @staticmethod
    def _wrap_text(draw: ImageDraw.Draw, text: str, font: ImageFont.ImageFont, max_width: int):
        words = text.split()
        lines = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if draw.textsize(test, font=font)[0] <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    @staticmethod
    def render(image_path: Optional[str] = None, decision: Optional[Dict[str, Any]] = None, user_id: Optional[int] = None):
        """
        Returns PNG bytes of composed face HUD.
        Use in Streamlit: st.image(FacePanel.render(...), use_column_width=True)
        """
        w, h = FacePanel.DEFAULT_SIZE
        base = Image.new("RGBA", (w, h), (10, 12, 15, 255))

        # وضع صورة الوجه أو placeholder
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

        # خطوط افتراضية مع fallback
        try:
            font_b = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
            font_s = ImageFont.truetype("DejaVuSans.ttf", 14)
        except Exception:
            font_b = ImageFont.load_default()
            font_s = ImageFont.load_default()

        # بيانات القرار الافتراضية
        badge_text = decision.get("decision_type", "No decision") if decision else "No decision"
        confidence_val = float(decision.get("confidence", 0.0)) if decision else 0.0
        explain = decision.get("reason", "Awaiting sync...") if decision else "No explanation yet."

        # شارة القرار أعلى يسار
        bx, by = 30, 20
        padding = (12, 8)
        tw, th = draw.textsize(badge_text, font=font_b)
        rect = [bx, by, bx + tw + padding[0]*2, by + th + padding[1]*2]
        draw.rounded_rectangle(rect, radius=10, fill=(0,0,0,160), outline=(0,255,136,200), width=2)
        draw.text((rect[0]+padding[0], rect[1]+padding[1]), badge_text, font=font_b, fill=(0,255,136,255))

        # مقياس الثقة أعلى يمين
        ring_center = (w - 90, 70)
        FacePanel._draw_confidence_ring(draw, ring_center, radius=48, confidence=confidence_val, color=(0,255,136,200))
        pct_text = f"{int(confidence_val*100)}%"
        tw2, th2 = draw.textsize(pct_text, font=font_b)
        draw.text((ring_center[0]-tw2/2, ring_center[1]-th2/2), pct_text, font=font_b, fill=(255,255,255,230))

        # أيقونات الوكلاء على الجانب الأيسر
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

        # شريط الشرح أسفل الصورة
        bar_h = 84
        rect2 = [30, h - bar_h - 20, w - 30, h - 20]
        draw.rounded_rectangle(rect2, radius=10, fill=(0,0,0,160))
        max_w = rect2[2] - rect2[0] - 20
        lines = FacePanel._wrap_text(draw, explain, font_s, max_w)
        y_text = rect2[1] + 10
        for ln in lines[:4]:
            draw.text((rect2[0]+10, y_text), ln, font=font_s, fill=(230,238,243,255))
            y_text += draw.textsize(ln, font=font_s)[1] + 4

        # لوحة تاريخ قرارات صغيرة على اليمين
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

        # دمج overlay مع base
        composed = Image.alpha_composite(base, overlay)

        # إرجاع بايت PNG جاهز للعرض
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
# PART 4/4
# MAIN APP
# -------------------------------

class MainApp:
    @staticmethod
    def run():
        # 1. إعداد الواجهة
        SystemUI.setup()

        # 2. تهيئة قاعدة البيانات
        CoreBridge.init_db()

        # 3. عناصر التحكم في الـ Sidebar (مع تسجيل الدخول)
        hr_val, step_val, sleep_val, screen_val, init_sync = SidebarControl.render()

        # 4. تشغيل منطق المزامنة
        SyncLogic.process_sync(hr_val, step_val, sleep_val, screen_val, init_sync)

        # 5. العنوان الرئيسي
        st.markdown("<h1 class='main-title'>Human Performance OS v2.0</h1>", unsafe_allow_html=True)

        # 6. إنشاء التبويبات (أضفنا تبويب FACE)
        tab_metrics, tab_chat, tab_bt, tab_face = st.tabs(["📊 SYSTEM METRICS", "🤖 NEURAL CHAT", "🔵 BLUETOOTH", "🖼️ FACE"])

        # 7. عرض الـ Dashboard
        with tab_metrics:
            Dashboard.render(hr_val, step_val)

        # 8. عرض صندوق المحادثة
        with tab_chat:
            NeuralChat.render()

        # 9. عرض البلوتوث
        with tab_bt:
            BluetoothManager.render_ui()

        # 10. عرض لوحة الوجه المميّز
        with tab_face:
            st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>🖼️ Face Panel</h3>", unsafe_allow_html=True)
            uploaded = st.file_uploader("Upload face image", type=["png","jpg","jpeg"])
            image_path = None
            if uploaded:
                # save temp file per user (username used if available)
                username = st.session_state.get('auth', {}).get('user', {}).get('username', 'anon')
                image_path = f"temp_face_{username}.png"
                try:
                    with open(image_path, "wb") as f:
                        f.write(uploaded.getbuffer())
                except Exception as e:
                    st.error(f"Failed to save uploaded image: {e}")
                    image_path = None

            # Evaluate face now (calls decision/evaluate endpoint)
            decision = None
            if st.button("Evaluate Face Now"):
                if not AuthManager.is_authenticated():
                    st.warning("Please sign in first.")
                else:
                    # prepare a lightweight payload; you can extend to include image metadata
                    payload = {"user_id": None, "hr": hr_val, "steps": step_val, "sleep_hours": sleep_val, "screen_time": screen_val}
                    # attempt to extract user_id from token if possible (not guaranteed)
                    token = AuthManager.get_token()
                    # backend evaluate endpoint expects user_id and metrics; we pass None if unknown
                    ok, resp = BackendConnector.post("decision/evaluate", payload=payload, require_auth=True)
                    if ok:
                        decision = resp.get("decision")
                        # attach returned decision_id if present
                        if resp.get("decision_id"):
                            if isinstance(decision, dict):
                                decision["id"] = resp.get("decision_id")
                    else:
                        st.error(f"Evaluation failed: {resp.get('error')}")

            # render face panel (decision may be None)
            face_png = FacePanel.render(image_path=image_path, decision=decision, user_id=st.session_state.get('auth', {}).get('user', {}).get('id'))
            st.image(face_png, use_column_width=True)

# -------------------------------
# تشغيل التطبيق
# -------------------------------
if __name__ == "__main__":
    MainApp.run()
