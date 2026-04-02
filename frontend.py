# frontend.py
"""
Human Performance OS - Streamlit UI (enhanced FacePanel)
- Robust text sizing (Pillow compatibility)
- Improved FacePanel visuals: badges, confidence ring, icons, explanatory shapes
- Safe Bluetooth scanning (bleak fallback / mock)
- Backend integration via BackendConnector (uses API_BASE env)
- Defensive error handling and clear logging
"""

import os
import io
import json
import time
import threading
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple

import streamlit as st
import pandas as pd
import sqlite3
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter

LOG = logging.getLogger("frontend")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# -------------------------
# Configuration
# -------------------------
API_BASE = os.environ.get("HPOS_API_BASE", "http://127.0.0.1:8000")
API_PREFIX = "/api/v2"
DB_PATH = os.environ.get("DB_PATH", "human_performance_v2.db")
ASSETS_DIR = os.environ.get("ASSETS_DIR", "assets")

# -------------------------
# Optional BLE & WS libs
# -------------------------
try:
    from bleak import BleakScanner, BleakClient
    BLE_AVAILABLE = True
except Exception:
    BLE_AVAILABLE = False

try:
    import websocket  # websocket-client
    WS_CLIENT_AVAILABLE = True
except Exception:
    WS_CLIENT_AVAILABLE = False

# -------------------------
# Utilities: fonts & text sizing
# -------------------------
def load_font(size: int = 16, bold: bool = False) -> ImageFont.ImageFont:
    """Load a TrueType font with fallbacks."""
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
    """
    Robust text size helper:
    - prefer textbbox
    - fallback to textsize, font.getsize
    - final conservative estimate
    """
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
    avg_char_w = max(6, int(getattr(font, "size", 16) * 0.5))
    return (len(text) * avg_char_w, int(avg_char_w * 1.6))

# -------------------------
# Backend helpers
# -------------------------
class BackendConnector:
    BASE = API_BASE.rstrip("/")

    @staticmethod
    def _url(path: str) -> str:
        p = path.lstrip("/")
        return f"{BackendConnector.BASE}{API_PREFIX}/{p}"

    @staticmethod
    def post(path: str, payload: dict = None, headers: dict = None, timeout: int = 12) -> Tuple[bool, dict]:
        url = BackendConnector._url(path)
        hdrs = {"Content-Type": "application/json"}
        if headers:
            hdrs.update(headers)
        try:
            resp = requests.post(url, json=payload or {}, headers=hdrs, timeout=timeout)
            resp.raise_for_status()
            # try to decode JSON safely
            try:
                return True, resp.json()
            except Exception:
                return True, {"raw_text": resp.text}
        except requests.HTTPError as he:
            LOG.exception("POST %s failed: %s", url, he)
            # include status code and response text if available
            status_code = None
            text = None
            if he.response is not None:
                status_code = he.response.status_code
                try:
                    text = he.response.json()
                except Exception:
                    text = he.response.text
            return False, {"error": str(he), "status_code": status_code, "response": text}
        except Exception as e:
            LOG.exception("POST %s failed: %s", url, e)
            return False, {"error": str(e)}

    @staticmethod
    def get(path: str, params: dict = None, headers: dict = None, timeout: int = 10) -> Tuple[bool, dict]:
        url = BackendConnector._url(path)
        hdrs = {}
        if headers:
            hdrs.update(headers)
        try:
            resp = requests.get(url, params=params or {}, headers=hdrs, timeout=timeout)
            resp.raise_for_status()
            try:
                return True, resp.json()
            except Exception:
                return True, {"raw_text": resp.text}
        except Exception as e:
            LOG.exception("GET %s failed: %s", url, e)
            return False, {"error": str(e)}

# -------------------------
# CoreBridge (DB)
# -------------------------
class CoreBridge:
    DB = DB_PATH

    @staticmethod
    def init_db():
        conn = sqlite3.connect(CoreBridge.DB)
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
    def save_log(score, hr=None, steps=None, user_id=None, job_id=None, sleep_hours=None, screen_time=None):
        conn = sqlite3.connect(CoreBridge.DB)
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
    def fetch_recent(limit: int = 20):
        try:
            conn = sqlite3.connect(CoreBridge.DB)
            df = pd.read_sql_query(f"SELECT * FROM performance_logs ORDER BY timestamp DESC LIMIT {limit}", conn)
            conn.close()
            return df
        except Exception:
            return pd.DataFrame()

# -------------------------
# BLE safe scan
# -------------------------
def scan_bluetooth_devices(timeout: int = 4) -> List[Dict[str, str]]:
    if not BLE_AVAILABLE:
        LOG.info("BLE not available in this environment.")
        return []
    try:
        import asyncio
        async def _scan():
            found = await BleakScanner.discover(timeout=timeout)
            return [{"name": d.name or "<unknown>", "address": d.address} for d in found]
        return asyncio.run(_scan())
    except Exception as e:
        LOG.warning("BLE scan failed: %s", e)
        return []

# -------------------------
# FacePanel (enhanced visuals)
# -------------------------
class FacePanel:
    DEFAULT_SIZE = (900, 600)
    ICONS_DIR = os.path.join(ASSETS_DIR, "icons")

    @staticmethod
    def _load_icon(name: str, size: Tuple[int, int] = (36, 36)) -> Optional[Image.Image]:
        path = os.path.join(FacePanel.ICONS_DIR, f"{name}.png")
        try:
            if os.path.exists(path):
                ic = Image.open(path).convert("RGBA")
                ic.thumbnail(size, Image.LANCZOS)
                return ic
        except Exception:
            LOG.debug("Failed to load icon %s", path)
        return None

    @staticmethod
    def _draw_confidence_ring(draw: ImageDraw.ImageDraw, center: Tuple[int, int], radius: int, confidence: float, color=(0, 200, 120, 220)):
        cx, cy = center
        bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
        # background ring
        draw.ellipse(bbox, fill=(10, 10, 10, 200))
        # progress pieslice
        end_angle = int(360 * max(0.0, min(1.0, confidence)))
        draw.pieslice(bbox, start=-90, end=-90 + end_angle, fill=color)
        # inner cutout
        inner = int(radius * 0.62)
        draw.ellipse([cx - inner, cy - inner, cx + inner, cy + inner], fill=(0, 0, 0, 0))

    @staticmethod
    def _rounded_rect(draw: ImageDraw.ImageDraw, rect: Tuple[int, int, int, int], radius: int, fill, outline=None, width=1):
        try:
            draw.rounded_rectangle(rect, radius=radius, fill=fill, outline=outline, width=width)
        except Exception:
            # fallback: normal rectangle
            draw.rectangle(rect, fill=fill, outline=outline, width=width)

    @staticmethod
    def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
        words = text.split()
        lines = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            tw, _ = get_text_size(draw, test, font)
            if tw <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    @staticmethod
    def render(image_path: Optional[str] = None, decision: Optional[Dict[str, Any]] = None, user_id: Optional[int] = None) -> bytes:
        w, h = FacePanel.DEFAULT_SIZE
        base = Image.new("RGBA", (w, h), (12, 14, 18, 255))

        # left panel for face
        left_w = int(w * 0.66)
        right_w = w - left_w

        # paste face or placeholder
        try:
            if image_path and os.path.exists(image_path):
                face = Image.open(image_path).convert("RGBA")
                face.thumbnail((left_w - 40, h - 80), Image.LANCZOS)
                fx = 20
                fy = (h - face.size[1]) // 2
                base.paste(face, (fx, fy), face)
            else:
                # placeholder circle avatar
                ph = Image.new("RGBA", (left_w - 40, h - 80), (0, 0, 0, 0))
                pd = ImageDraw.Draw(ph)
                cx = ph.size[0] // 2
                cy = ph.size[1] // 2
                r = min(cx, cy) - 20
                pd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(30, 40, 60, 255))
                # subtle glow
                glow = ph.filter(ImageFilter.GaussianBlur(radius=6))
                base.paste(glow, (20, (h - ph.size[1]) // 2), glow)
                base.paste(ph, (20, (h - ph.size[1]) // 2), ph)
        except Exception as e:
            LOG.exception("Face paste failed: %s", e)

        # overlay for right panel UI
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # fonts
        font_b = load_font(size=18, bold=True)
        font_m = load_font(size=14, bold=False)
        font_s = load_font(size=12, bold=False)

        # Decision summary badge (top-left)
        badge_text = (decision.get("decision_type") if decision else "No decision").upper()
        conf_val = float(decision.get("confidence", 0.0)) if decision else 0.0
        reason = decision.get("reason", "Awaiting analysis...") if decision else "No explanation yet."

        bx, by = 30, 18
        padding_x, padding_y = 12, 8
        tw, th = get_text_size(draw, badge_text, font_b)
        rect = (bx, by, bx + tw + padding_x * 2, by + th + padding_y * 2)
        FacePanel._rounded_rect(draw, rect, radius=12, fill=(6, 30, 40, 220), outline=(0, 200, 140, 200), width=2)
        draw.text((rect[0] + padding_x, rect[1] + padding_y), badge_text, font=font_b, fill=(0, 200, 140, 255))

        # Confidence ring (top-right)
        ring_center = (w - 90, 70)
        FacePanel._draw_confidence_ring(draw, ring_center, radius=52, confidence=conf_val, color=(0, 200, 140, 220))
        pct_text = f"{int(conf_val * 100)}%"
        tw2, th2 = get_text_size(draw, pct_text, font_b)
        draw.text((ring_center[0] - tw2 / 2, ring_center[1] - th2 / 2), pct_text, font=font_b, fill=(255, 255, 255, 230))

        # small explanatory label under ring
        sub_label = "Confidence"
        tw3, th3 = get_text_size(draw, sub_label, font_s)
        draw.text((ring_center[0] - tw3 / 2, ring_center[1] + 36), sub_label, font=font_s, fill=(200, 230, 220, 200))

        # icons list with titles and summaries (left of right panel)
        icons = [
            ("health", "Heart Rate", f"HR: {int(decision.get('hr', 0)) if decision else '—'}"),
            ("sleep", "Sleep", f"{decision.get('sleep_hours', '—')} hrs" if decision else "—"),
            ("steps", "Steps", f"{decision.get('steps', '—')}" if decision else "—")
        ]
        ix = left_w + 20
        iy = 120
        for key, title, summary in icons:
            box = (ix, iy, ix + right_w - 40, iy + 48)
            FacePanel._rounded_rect(draw, box, radius=10, fill=(8, 12, 16, 200), outline=(255, 255, 255, 12))
            icon_img = FacePanel._load_icon(key, size=(36, 36))
            if icon_img:
                overlay.paste(icon_img, (ix + 8, iy + 6), icon_img)
                text_x = ix + 8 + icon_img.size[0] + 8
            else:
                draw.text((ix + 8, iy + 8), "•", font=font_b, fill=(0, 200, 140, 255))
                text_x = ix + 8 + 20
            draw.text((text_x, iy + 6), title, font=font_m, fill=(220, 240, 230, 255))
            draw.text((text_x, iy + 26), summary, font=font_s, fill=(180, 220, 200, 220))
            iy += 64

        # explanation box (bottom)
        bar_h = 120
        rect2 = (left_w + 20, h - bar_h - 20, w - 20, h - 20)
        FacePanel._rounded_rect(draw, rect2, radius=12, fill=(6, 10, 12, 220))
        title_ex = "Explanation"
        draw.text((rect2[0] + 12, rect2[1] + 10), title_ex, font=font_b, fill=(0, 200, 140, 255))
        max_w = rect2[2] - rect2[0] - 24
        lines = FacePanel._wrap_text(draw, reason, font_s, max_w)
        y_text = rect2[1] + 36
        for ln in lines[:4]:
            draw.text((rect2[0] + 12, y_text), ln, font=font_s, fill=(220, 238, 243, 230))
            ln_h = get_text_size(draw, ln, font_s)[1]
            y_text += ln_h + 6

        # recent decisions mini-list
        hist_box = (w - 260, 120, w - 40, 260)
        FacePanel._rounded_rect(draw, hist_box, radius=10, fill=(6, 10, 12, 180), outline=(0, 200, 140, 60))
        draw.text((hist_box[0] + 10, hist_box[1] + 8), "Recent decisions", font=font_m, fill=(0, 200, 140, 255))
        yy = hist_box[1] + 36
        recent = (decision.get("recent", []) if decision else [])[:4]
        if not recent:
            draw.text((hist_box[0] + 10, yy), "- No recent decisions", font=font_s, fill=(200, 220, 210, 200))
        else:
            for r in recent:
                ts = r.get("created_at", "")[:16]
                typ = r.get("decision_type", "—")
                confs = f"{int(r.get('confidence', 0)*100)}%"
                line = f"{ts} • {typ} • {confs}"
                draw.text((hist_box[0] + 10, yy), line, font=font_s, fill=(200, 220, 210, 200))
                yy += get_text_size(draw, line, font_s)[1] + 6

        # composite and return PNG bytes
        composed = Image.alpha_composite(base, overlay)
        buf = io.BytesIO()
        composed.save(buf, format="PNG")
        buf.seek(0)
        return buf.getvalue()

# -------------------------
# UI Components & Flow
# -------------------------
def submit_evaluation(payload: dict, token: Optional[str] = None) -> dict:
    """
    Submit evaluation to backend.

    Note: main backend endpoint expects `user_id` as a query parameter and the metrics
    as JSON body. To avoid 422 Unprocessable Entity errors, we place user_id in the
    query string and send only the metrics in the JSON body.
    """
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Extract user_id for query param if present
    user_id = payload.get("user_id")
    # Prepare body without user_id
    body = {k: v for k, v in payload.items() if k != "user_id"}

    path = f"decision/evaluate?user_id={user_id}" if user_id is not None else "decision/evaluate"
    ok, resp = BackendConnector.post(path, payload=body, headers=headers)
    if ok:
        return {"ok": True, "response": resp}
    return {"ok": False, "error": resp.get("error", "unknown"), "details": resp}

def poll_decision(decision_id: str, token: Optional[str] = None, timeout: int = 30) -> Optional[dict]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    start = time.time()
    while time.time() - start < timeout:
        ok, resp = BackendConnector.get(f"decision/{decision_id}", headers=headers)
        if ok:
            return resp
        time.sleep(1.5)
    return None

# -------------------------
# Streamlit App
# -------------------------
def main():
    st.set_page_config(page_title="Human Performance OS - Face", layout="wide")
    st.title("Human Performance OS — Face Panel")

    # init DB
    CoreBridge.init_db()

    # simple auth simulation
    if "auth" not in st.session_state:
        st.session_state.auth = {"user": {"id": 1, "username": "testuser"}, "token": None}

    user = st.session_state.auth.get("user", {})
    st.sidebar.markdown(f"**User:** {user.get('username')} (id={user.get('id')})")

    # upload
    uploaded = st.file_uploader("Upload face image", type=["png", "jpg", "jpeg"])
    image_path = None
    if uploaded:
        tmp = f"tmp_face_{int(time.time())}.png"
        with open(tmp, "wb") as f:
            f.write(uploaded.getbuffer())
        image_path = tmp
        st.success("Image uploaded")

    # metrics
    st.sidebar.header("Device Metrics")
    hr = st.sidebar.number_input("Heart rate (bpm)", min_value=30, max_value=220, value=75)
    steps = st.sidebar.number_input("Steps", min_value=0, max_value=100000, value=6000)
    screen_time = st.sidebar.number_input("Screen time (hrs)", min_value=0.0, max_value=24.0, value=3.0)
    sleep_hours = st.sidebar.number_input("Sleep hours", min_value=0.0, max_value=24.0, value=7.0)

    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("Evaluate decision"):
            payload = {"user_id": user.get("id"), "hr": hr, "steps": steps, "screen_time": screen_time, "sleep_hours": sleep_hours}
            res = submit_evaluation(payload, token=st.session_state.auth.get("token"))
            if not res.get("ok"):
                # show more details when available
                err = res.get("error")
                details = res.get("details")
                if details and isinstance(details, dict):
                    st.error(f"Submit failed: {err} (status: {details.get('status_code')})")
                    LOG.debug("Submit details: %s", details)
                else:
                    st.error(f"Submit failed: {err}")
            else:
                resp = res.get("response")
                decision = resp.get("decision") or resp
                st.success("Evaluation submitted")
                st.json(decision)
                # render face panel
                try:
                    img_bytes = FacePanel.render(image_path=image_path, decision=decision, user_id=user.get("id"))
                    st.image(img_bytes, use_column_width=True)
                except Exception as e:
                    LOG.exception("Render failed: %s", e)
                    st.error("Failed to render face panel")
    with col2:
        st.markdown("### Bluetooth")
        if st.button("Scan BLE devices"):
            devices = scan_bluetooth_devices(timeout=4)
            if devices:
                st.write("Found devices:")
                st.json(devices)
            else:
                st.info("No BLE devices found or scanning not available.")

    st.markdown("---")
    st.markdown("### History")
    df = CoreBridge.fetch_recent(10)
    if not df.empty:
        st.dataframe(df)
    else:
        st.info("No historical logs yet.")

if __name__ == "__main__":
    main()
