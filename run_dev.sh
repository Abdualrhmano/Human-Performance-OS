#!/usr/bin/env bash
set -euo pipefail

# ملف env واسم البيئة الافتراضية
ENV_FILE=".env"
VENV_DIR=".venv"

# بورتات افتراضية (يمكن تعديلها في .env)
PORT_BACKEND="${PORT_BACKEND:-8000}"
PORT_FRONTEND="${PORT_FRONTEND:-8501}"
API_MODULE="${API_MODULE:-main:app}"   # عدّل إذا كان اسم التطبيق مختلفاً

LOG_DIR="logs"
UVICORN_LOG="$LOG_DIR/uvicorn.log"
STREAMLIT_LOG="$LOG_DIR/streamlit.log"

# إنشاء مجلد السجلات
mkdir -p "$LOG_DIR"

# تحميل متغيرات .env إن وُجد
if [ -f "$ENV_FILE" ]; then
  echo "Loading environment from $ENV_FILE"
  # export all variables in .env (تجاهل التعليقات والأسطر الفارغة)
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
else
  echo "Warning: $ENV_FILE not found. Proceeding without it."
fi

# إنشاء و تفعيل venv إن لم يكن موجوداً
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment in $VENV_DIR..."
  python3 -m venv "$VENV_DIR"
fi

# تفعيل البيئة
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# حدّث pip وأدوات البناء
python -m pip install --upgrade pip setuptools wheel >/dev/null

# تثبيت الحزم الأساسية إن لم تكن مثبتة (خفيفة)
REQUIREMENTS="${REQUIREMENTS:-requirements.txt}"
if [ -f "$REQUIREMENTS" ]; then
  echo "Installing requirements from $REQUIREMENTS (this may take a moment)..."
  pip install -r "$REQUIREMENTS"
else
  echo "No $REQUIREMENTS found — skipping pip install."
fi

# تحقق من وجود GEMINI_KEY (تنبيه فقط، لا يوقف التشغيل)
if [ -z "${GEMINI_KEY:-}" ]; then
  echo "Note: GEMINI_KEY is not set. Agents will use fallback heuristics."
else
  echo "GEMINI_KEY found (hidden). Gemini calls will be enabled."
fi

# دوال مساعدة لإطلاق الخدمات في الخلفية
start_uvicorn() {
  echo "Starting uvicorn on port $PORT_BACKEND (logs -> $UVICORN_LOG)"
  nohup uvicorn "$API_MODULE" --host 0.0.0.0 --port "$PORT_BACKEND" --reload > "$UVICORN_LOG" 2>&1 &
  echo $! > "$LOG_DIR/uvicorn.pid"
}

start_streamlit() {
  FRONTEND_FILE="${FRONTEND_FILE:-frontend.py}"
  if [ ! -f "$FRONTEND_FILE" ]; then
    echo "Warning: $FRONTEND_FILE not found. Skipping Streamlit."
    return
  fi
  echo "Starting Streamlit on port $PORT_FRONTEND (logs -> $STREAMLIT_LOG)"
  nohup streamlit run "$FRONTEND_FILE" --server.port "$PORT_FRONTEND" --server.address 0.0.0.0 > "$STREAMLIT_LOG" 2>&1 &
  echo $! > "$LOG_DIR/streamlit.pid"
}

# إيقاف الخدمات
stop_all() {
  echo "Stopping services..."
  if [ -f "$LOG_DIR/uvicorn.pid" ]; then
    kill "$(cat "$LOG_DIR/uvicorn.pid")" 2>/dev/null || true
    rm -f "$LOG_DIR/uvicorn.pid"
  fi
  if [ -f "$LOG_DIR/streamlit.pid" ]; then
    kill "$(cat "$LOG_DIR/streamlit.pid")" 2>/dev/null || true
    rm -f "$LOG_DIR/streamlit.pid"
  fi
  echo "Stopped."
}

# افعل trap لإيقاف عند Ctrl+C
trap 'stop_all; exit 0' INT TERM

# شغّل الخدمات
start_uvicorn
start_streamlit

echo "Services started."
echo "Backend: http://localhost:$PORT_BACKEND"
echo "Frontend: http://localhost:$PORT_FRONTEND"
echo "Logs: $LOG_DIR/"

# عرض tail للسجلات الأساسية (اختياري)
echo "Tailing logs (press Ctrl+C to stop and keep services running)..."
tail -n 200 -f "$UVICORN_LOG" "$STREAMLIT_LOG"
