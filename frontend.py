# streamlit_app_face_pro.py
# Human Performance OS - FacePanel PRO
# Features:
#  - A: SSE-style background updates (polling) for near-real-time results
#  - B: ONNX conversion helper (instructions + function)
#  - C: Enhanced HUD visuals (custom fonts, SVG icons, animated progress)
#  - D: Save uploads + metadata to uploads/{user}/{ts}.png + .json; decisions table in SQLite
#  - E: Progress stages (Upload -> Queued -> Analyzing -> Done) with timestamps
#
# Requirements (add to requirements.txt):
# streamlit, requests, Pillow, plotly, numpy, onnxruntime (for local ONNX inference), python-multipart
# Optional for conversion: torch, onnx, skl2onnx (depending on model type)
#
# Run:
# streamlit run streamlit_app_face_pro.py
#
# Notes:
# - Backend endpoints expected: /api/v2/decision/evaluate (POST) returns decision or decision_id
#   and /api/v2/decision/{id}/status (GET) returns status/progress; /api/v2/decision/{id}/feedback (POST)
# - If backend doesn't support status endpoint, the app will poll local cache/file produced by worker.
# - ONNX conversion helper is local-only; actual model conversion should run in environment with torch/skl2onnx.

import streamlit as st
import requests, os, io, json, time, threading, hashlib, sqlite3
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Dict, Any, List
import plotly.graph_objects as go
import plotly.express as px

# -------------------------
# Config / constants
# -------------------------
UPLOAD_DIR = "uploads"
DB_PATH = "human_performance_v2.db"
API_BASE = "http://localhost:8000/api/v2"
FONT_PATH = None  # set to "assets/Orbitron-Regular.ttf" if you add font file
SVG_ICONS = {
    "health": "💓",
    "productivity": "🧭",
    "feedback": "✉️"
}
POLL_INTERVAL = 1.5  # seconds for polling status

# -------------------------
# Utilities: DB, file save, hashing
# -------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS performance_logs 
                    (timestamp TEXT, performance_score REAL, hr INTEGER, steps INTEGER)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS decisions
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, decision_id TEXT, user TEXT, created_at TEXT, status TEXT, payload TEXT)''')
    conn.commit()
    conn.close()

def save_upload(user: str, image_bytes: bytes, metadata: dict) -> str:
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    user_dir = os.path.join(UPLOAD_DIR, user or "anon")
    os.makedirs(user_dir, exist_ok=True)
    img_path = os.path.join(user_dir, f"{ts}.png")
    meta_path = os.path.join(user_dir, f"{ts}.json")
    with open(img_path, "wb") as f:
        f.write(image_bytes)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    return img_path

def record_decision(decision_id: str, user: str, status: str, payload: dict):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO decisions (decision_id, user, created_at, status, payload) VALUES (?, ?, ?, ?, ?)",
                 (str(decision_id), user or "anon", datetime.utcnow().isoformat(), status, json.dumps(payload)))
    conn.commit()
    conn.close()

def update_decision_status(decision_id: str, status: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE decisions SET status=? WHERE decision_id=?", (status, str(decision_id)))
    conn.commit()
    conn.close()

# -------------------------
# Auth & Backend connector
# -------------------------
class AuthManager:
    LOGIN_ENDPOINT = f"{API_BASE}/auth/login"
    REGISTER_ENDPOINT = f"{API_BASE}/auth/register"
    @staticmethod
    def init_session():
        if "auth" not in st.session_state:
            st.session_state.auth = {"is_authenticated": False, "token": None, "user": None}
    @staticmethod
    def login(username: str, password: str):
        AuthManager.init_session()
        try:
            resp = requests.post(AuthManager.LOGIN_ENDPOINT, data={"username": username, "password": password}, timeout=10)
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
    def get_token():
        AuthManager.init_session()
        return st.session_state.auth.get("token")

class BackendConnector:
    @staticmethod
    def post(path: str, payload: dict = None, require_auth: bool = True, timeout: int = 30):
        url = f"{API_BASE}/{path.lstrip('/')}"
        headers = {"Content-Type":"application/json"}
        if require_auth:
            token = AuthManager.get_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
        try:
            r = requests.post(url, json=payload or {}, headers=headers, timeout=timeout)
            r.raise_for_status()
            return True, r.json()
        except Exception as e:
            return False, {"error": str(e)}
    @staticmethod
    def get(path: str, params: dict = None, require_auth: bool = True, timeout: int = 10):
        url = f"{API_BASE}/{path.lstrip('/')}"
        headers = {}
        if require_auth:
            token = AuthManager.get_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
        try:
            r = requests.get(url, params=params or {}, headers=headers, timeout=timeout)
            r.raise_for_status()
            return True, r.json()
        except Exception as e:
            return False, {"error": str(e)}

# -------------------------
# Image helpers & HUD composition (PIL)
# -------------------------
def compress_image_bytes(uploaded_file, max_size: int = 800, quality: int = 78) -> bytes:
    img = Image.open(uploaded_file).convert("RGBA")
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    bg = Image.new("RGB", img.size, (10,12,15))
    bg.paste(img, mask=img.split()[3] if img.mode=="RGBA" else None)
    buf = io.BytesIO()
    bg.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()

def compose_face_hud(image_bytes: bytes, decision: Optional[dict]=None, agents: Optional[list]=None, history: Optional[list]=None, output_size=(900,900)) -> bytes:
    base = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    base.thumbnail(output_size, Image.LANCZOS)
    w,h = base.size
    overlay = Image.new("RGBA", base.size, (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    # badge
    badge = decision.get("decision_type","No decision") if decision else "No decision"
    try:
        font_b = ImageFont.truetype(FONT_PATH, 18) if FONT_PATH else ImageFont.load_default()
    except Exception:
        font_b = ImageFont.load_default()
    pad = (12,8)
    tw, th = d.textsize(badge, font=font_b)
    rect = (20,20, 20+tw+pad[0]*2, 20+th+pad[1]*2)
    d.rounded_rectangle(rect, radius=10, fill=(0,0,0,160), outline=(0,255,136,200), width=2)
    d.text((rect[0]+pad[0], rect[1]+pad[1]), badge, font=font_b, fill=(0,255,136,255))
    # confidence ring (simple)
    conf = float(decision.get("confidence",0.0)) if decision else 0.0
    cx, cy, r = w-80, 80, 52
    d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(0,0,0,120))
    # arc by drawing pieslice
    start = -90
    end = start + int(360 * max(0.0, min(1.0, conf)))
    d.pieslice((cx-r, cy-r, cx+r, cy+r), start, end, fill=(0,255,136,200))
    inner = int(r*0.6)
    d.ellipse((cx-inner, cy-inner, cx+inner, cy+inner), fill=(0,0,0,0))
    # confidence text
    txt = f"{int(conf*100)}%"
    tw, th = d.textsize(txt, font=font_b)
    d.text((cx-tw/2, cy-th/2), txt, font=font_b, fill=(255,255,255,230))
    # explain bar bottom
    explain = decision.get("reason","Awaiting sync...") if decision else "No explanation yet."
    rect2 = (20, h-100, w-20, h-30)
    d.rounded_rectangle(rect2, radius=10, fill=(0,0,0,160))
    # wrap text
    try:
        font_s = ImageFont.truetype(FONT_PATH, 14) if FONT_PATH else ImageFont.load_default()
    except Exception:
        font_s = ImageFont.load_default()
    max_w = rect2[2]-rect2[0]-20
    words = explain.split()
    lines = []
    cur = ""
    for wd in words:
        if d.textsize((cur+" "+wd).strip(), font=font_s)[0] < max_w:
            cur = (cur+" "+wd).strip()
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    y = rect2[1]+10
    for ln in lines[:3]:
        d.text((rect2[0]+10, y), ln, font=font_s, fill=(230,238,243,255))
        y += d.textsize(ln, font=font_s)[1]+4
    # agents left
    if not agents:
        agents = [{"icon":"💓","title":"Health","summary":"HR ok"},{"icon":"🧭","title":"Productivity","summary":"Focus stable"}]
    ax, ay = 20, 100
    for a in agents:
        box = (ax, ay, ax+180, ay+44)
        d.rounded_rectangle(box, radius=8, fill=(0,0,0,120), outline=(255,255,255,20))
        d.text((ax+8, ay+6), f"{a.get('icon','⚕️')} {a.get('title','Agent')}", font=font_s, fill=(200,255,220,255))
        d.text((ax+8, ay+22), a.get('summary','-')[:48], font=font_s, fill=(180,230,200,220))
        ay += 52
    # history right
    if not history:
        history = []
    hx, hy = w-260, 120
    boxh = (hx, hy, hx+240, hy + max(80, len(history)*34 + 28))
    d.rounded_rectangle(boxh, radius=10, fill=(0,0,0,120), outline=(0,255,136,80))
    d.text((hx+10, hy+8), "Recent decisions", font=font_b, fill=(0,255,136,255))
    yy = hy+30
    for h in history[:3]:
        ts = h.get("created_at","")[:16]
        typ = h.get("decision_type","-")
        confs = f"{int(h.get('confidence',0)*100)}%"
        d.text((hx+10, yy), f"{ts} • {typ} • {confs}", font=font_s, fill=(220,240,230,230))
        yy += 28
    # compose
    composed = Image.alpha_composite(base, overlay)
    out = io.BytesIO()
    composed.save(out, format="PNG")
    return out.getvalue()

# -------------------------
# ONNX helper (B)
# -------------------------
def convert_model_to_onnx_example(pytorch_model, sample_input, out_path="model.onnx"):
    """
    Example helper: run in environment with torch installed.
    from this function you should:
      - export torch model to ONNX
      - optionally run onnxruntime.quantization for int8
    This function is a placeholder; run conversion offline where torch is available.
    """
    try:
        import torch
        torch.onnx.export(pytorch_model, sample_input, out_path, opset_version=13, do_constant_folding=True)
        return True, out_path
    except Exception as e:
        return False, str(e)

# -------------------------
# Background evaluation + polling (A + E)
# -------------------------
def submit_evaluation(image_bytes: bytes, metrics: dict) -> Dict[str,Any]:
    """
    Submit to backend evaluate endpoint. Backend should return {'decision_id': '...'} or full decision.
    We save upload + metadata, record decision row with status 'queued', and return response.
    """
    user = st.session_state.get('auth', {}).get('user', {}).get('username', 'anon')
    meta = {"user": user, "metrics": metrics, "submitted_at": datetime.utcnow().isoformat()}
    img_path = save_upload(user, image_bytes, meta)
    ok, resp = BackendConnector.post("decision/evaluate", payload=metrics, require_auth=True)
    if ok:
        # if backend returns decision_id, record and poll
        decision_id = resp.get("decision_id") or resp.get("id") or resp.get("decision", {}).get("id")
        record_decision(decision_id, user, "queued", resp)
        return {"ok": True, "resp": resp, "decision_id": decision_id, "img_path": img_path}
    else:
        return {"ok": False, "error": resp.get("error")}

def poll_decision_status(decision_id: str, timeout: int = 60) -> Dict[str,Any]:
    """
    Poll backend for status until done or timeout. Expects endpoint GET /decision/{id}/status returning JSON:
      {"status":"queued|analyzing|done","progress":0.5,"decision":{...}}
    If backend lacks this endpoint, fallback to re-fetching /decision/{id}.
    """
    start = time.time()
    while time.time() - start < timeout:
        ok, resp = BackendConnector.get(f"decision/{decision_id}/status", require_auth=True)
        if not ok:
            ok2, resp2 = BackendConnector.get(f"decision/{decision_id}", require_auth=True)
            if ok2:
                # try to infer status
                status = resp2.get("status") or "done"
                if status == "done":
                    update_decision_status(decision_id, "done")
                    return {"status":"done", "decision": resp2.get("decision") or resp2}
                else:
                    time.sleep(POLL_INTERVAL)
                    continue
            else:
                return {"status":"error", "error": resp.get("error")}
        else:
            status = resp.get("status")
            if status == "done":
                update_decision_status(decision_id, "done")
                return {"status":"done", "decision": resp.get("decision") or resp}
            else:
                time.sleep(POLL_INTERVAL)
                continue
    return {"status":"timeout", "error":"Polling timed out"}

# -------------------------
# Streamlit UI: Face Panel PRO
# -------------------------
def face_panel_pro():
    st.markdown("<h3 style='color:#00ff88; font-family:Orbitron;'>🖼️ Face Panel PRO</h3>", unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload face image", type=["png","jpg","jpeg"])
    col1, col2 = st.columns([2,1])
    with col2:
        hr = st.number_input("Heart Rate (BPM)", 40, 190, 75)
        steps = st.number_input("Daily Steps", value=6000)
        sleep_hours = st.number_input("Sleep Hours", value=7.0, step=0.5)
        screen_time = st.number_input("Screen Time (hrs)", value=3.0, step=0.5)
    # session keys
    if "face_stage" not in st.session_state:
        st.session_state.face_stage = "idle"
    if "face_decision_id" not in st.session_state:
        st.session_state.face_decision_id = None
    if "face_result" not in st.session_state:
        st.session_state.face_result = None
    if uploaded:
        # compress preview
        try:
            thumb = compress_image_bytes(uploaded, max_size=800, quality=80)
            st.image(thumb, caption="Preview (compressed)", use_column_width=True)
        except Exception as e:
            st.error(f"Image error: {e}")
            return
    # Evaluate button
    if st.button("Evaluate Face (PRO)"):
        if not AuthManager.get_token():
            st.warning("Please sign in first.")
        elif not uploaded:
            st.warning("Upload an image first.")
        else:
            st.session_state.face_stage = "queued"
            st.session_state.face_result = None
            # submit
            metrics = {"user_id": st.session_state.get('auth', {}).get('user', {}).get('id'), "hr": hr, "steps": steps, "sleep_hours": sleep_hours, "screen_time": screen_time}
            submit_resp = submit_evaluation(thumb, metrics)
            if not submit_resp.get("ok"):
                st.session_state.face_stage = "error"
                st.error(f"Submit failed: {submit_resp.get('error')}")
            else:
                st.session_state.face_decision_id = submit_resp.get("decision_id")
                st.session_state.face_stage = "queued"
                # start background poll thread to update result file
                def poll_worker(dec_id):
                    res = poll_decision_status(dec_id, timeout=120)
                    # save to file for main thread to pick up
                    try:
                        with open("last_face_eval.json", "w") as f:
                            json.dump(res, f)
                    except Exception:
                        pass
                threading.Thread(target=poll_worker, args=(st.session_state.face_decision_id,), daemon=True).start()
                st.experimental_rerun()
    # show progress stages
    st.markdown("**Progress**")
    stage = st.session_state.face_stage
    if stage == "idle":
        st.info("Idle. Upload an image and press Evaluate.")
    elif stage == "queued":
        st.info("Queued. Waiting for worker to pick up the job.")
    elif stage == "analyzing":
        st.info("Analyzing... please wait.")
    elif stage == "done":
        st.success("Done. See HUD below.")
    elif stage == "error":
        st.error("Error during processing.")
    # check for background result file
    if os.path.exists("last_face_eval.json"):
        try:
            with open("last_face_eval.json", "r") as f:
                res = json.load(f)
            os.remove("last_face_eval.json")
            if res.get("status") == "done":
                st.session_state.face_stage = "done"
                st.session_state.face_result = res.get("decision") or res
            else:
                st.session_state.face_stage = res.get("status") or "error"
                st.session_state.face_result = res
        except Exception:
            pass
    # compose HUD
    decision = st.session_state.face_result or None
    history = []
    # fetch recent decisions for user
    user = st.session_state.get('auth', {}).get('user', {}).get('username', 'anon')
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT payload, created_at FROM decisions WHERE user=? ORDER BY created_at DESC LIMIT 3", (user,))
        rows = cur.fetchall()
        for r in rows:
            try:
                payload = json.loads(r[0]) if isinstance(r[0], str) else r[0]
            except Exception:
                payload = {}
            history.append({"created_at": r[1], "decision_type": payload.get("decision_type") or payload.get("action") or "Result", "confidence": payload.get("confidence", 0.0)})
        conn.close()
    except Exception:
        history = []
    # base image bytes
    if uploaded:
        base_bytes = thumb
    else:
        # placeholder
        placeholder = Image.new("RGBA", (800,600), (10,12,15,255))
        d = ImageDraw.Draw(placeholder)
        d.ellipse((160,80,480,400), fill=(30,40,60,255))
        buf = io.BytesIO()
        placeholder.save(buf, format="PNG")
        base_bytes = buf.getvalue()
    hud_png = compose_face_hud(base_bytes, decision=decision, agents=None, history=history, output_size=(900,900))
    st.image(hud_png, use_column_width=True)
    # decision controls
    st.markdown("---")
    st.markdown("### Decision Controls")
    if decision:
        # normalize
        if isinstance(decision, dict) and decision.get("decision"):
            dec = decision.get("decision")
        else:
            dec = decision
        st.markdown(f"**Action:** {dec.get('decision_type') or dec.get('action') or '—'}")
        st.markdown(f"**Confidence:** {round(float(dec.get('confidence',0))*100,1)}%")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Accept"):
                did = st.session_state.face_decision_id or dec.get("id") or dec.get("decision_id")
                if did:
                    payload = {"feedback_type":"accepted","adherence":True,"notes":"Accepted via UI"}
                    ok, resp = BackendConnector.post(f"decision/{did}/feedback", payload=payload, require_auth=True)
                    if ok:
                        st.success("Feedback submitted.")
                    else:
                        st.error(f"Feedback failed: {resp.get('error')}")
                else:
                    st.warning("No decision id available.")
        with c2:
            if st.button("❌ Reject"):
                did = st.session_state.face_decision_id or dec.get("id") or dec.get("decision_id")
                if did:
                    payload = {"feedback_type":"rejected","adherence":False,"notes":"Rejected via UI"}
                    ok, resp = BackendConnector.post(f"decision/{did}/feedback", payload=payload, require_auth=True)
                    if ok:
                        st.success("Feedback submitted.")
                    else:
                        st.error(f"Feedback failed: {resp.get('error')}")
                else:
                    st.warning("No decision id available.")
    else:
        st.info("No decision yet. Run evaluation.")

# -------------------------
# Dashboard & main
# -------------------------
def dashboard_ui(hr_val, step_val):
    display_score = st.session_state.get('current_score', 50.0)
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=display_score,
        number={'font': {'color': 'white', 'family': 'Orbitron'}},
        gauge={'axis': {'range': [0, 100], 'tickcolor': "#00ff88"}, 'bar': {'color': "#00ff88"}}
    ))
    fig_gauge.update_layout(height=260, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
    st.plotly_chart(fig_gauge, use_container_width=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div style='background:rgba(0,255,136,0.04); padding:10px; border-radius:8px;'><h4>💓 Heart Rate</h4><p>{hr_val} BPM</p></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div style='background:rgba(0,255,136,0.04); padding:10px; border-radius:8px;'><h4>👟 Steps</h4><p>{step_val} steps</p></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div style='background:rgba(0,255,136,0.04); padding:10px; border-radius:8px;'><h4>⚡ Performance</h4><p>{display_score} %</p></div>", unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Human Performance OS PRO", page_icon="🧠", layout="wide")
    init_db()
    # sidebar
    with st.sidebar:
        st.markdown("<h2 style='color:#00ff88; font-family:Orbitron;'>🛡️ LUNA CORE PRO</h2>", unsafe_allow_html=True)
        AuthManager.init_session()
        # simple login UI
        if AuthManager.get_token():
            user = st.session_state.auth.get("user", {}).get("username", "User")
            st.markdown(f"👋 مرحباً، **{user}**")
            if st.button("Sign Out"):
                st.session_state.auth = {"is_authenticated": False, "token": None, "user": None}
                st.experimental_rerun()
        else:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Sign In"):
                ok, resp = AuthManager.login(username, password)
                if ok:
                    st.success("Signed in.")
                    st.experimental_rerun()
                else:
                    st.error(f"Login failed: {resp.get('error')}")
        hr_val = st.slider("💓 Heart Rate (BPM)", 40, 190, 75)
        step_val = st.number_input("👟 Daily Step Count", value=6000)
        sleep_val = st.number_input("😴 Sleep Hours", value=7.0)
        screen_val = st.number_input("📱 Screen Time (hrs)", value=3.0)
        if st.button("🚀 INITIATE SYSTEM SYNC"):
            if not AuthManager.get_token():
                st.warning("Sign in first.")
            else:
                ok, resp = BackendConnector.post("performance/sync", payload={"hr":hr_val,"steps":step_val,"sleep_hours":sleep_val,"screen_time":screen_val}, require_auth=True)
                if ok:
                    st.session_state.current_score = resp.get("performance_score") or st.session_state.get('current_score',50)
                    st.success("Sync complete.")
                else:
                    st.error(f"Sync failed: {resp.get('error')}")
    st.markdown("<h1 style='font-family:Orbitron; color:#00ff88;'>Human Performance OS PRO</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📊 Dashboard", "🖼️ Face PRO"])
    with tab1:
        dashboard_ui(hr_val, step_val)
    with tab2:
        face_panel_pro()

if __name__ == "__main__":
    main()
