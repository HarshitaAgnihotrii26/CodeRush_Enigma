
import os
import io
import threading
import sqlite3
import datetime
import json
import uuid
import msvcrt
from contextlib import contextmanager

from flask import Flask, render_template, request, jsonify, send_file, after_this_request

from model import (
    train_model_background,
    extract_embedding_for_image,
    predict_with_model,
    load_model_if_exists,
    MODEL_PATH
)

# CSV file path for auto-saving attendance
ATTENDANCE_CSV = os.path.join(DATA_DIR, "attendance", "attendance.csv")

# =====================================================
# APP CONFIG
# =====================================================
APP_DIR = os.path.dirname(os.path.abspath(__file__)) or "."
DATA_DIR = os.environ.get("DATA_DIR", APP_DIR)
DB_PATH = os.path.join(DATA_DIR, "attendance.db")
DATASET_DIR = os.path.join(DATA_DIR, "dataset")
TRAIN_STATUS_FILE = os.path.join(DATA_DIR, "train_status.json")
DOCUMENTS_DIR = os.path.join(DATA_DIR, "uploads", "documents")

os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(os.path.dirname(ATTENDANCE_CSV), exist_ok=True)
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

# Initialize attendance CSV with header if not exists
if not os.path.exists(ATTENDANCE_CSV):
    with open(ATTENDANCE_CSV, "w") as f:
        f.write("id,student_id,name,timestamp\n")

app = Flask(__name__, static_folder="static", template_folder="templates")

@app.after_request
def add_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# =====================================================
# MODEL CACHE (🔥 VERY IMPORTANT)
# =====================================================
MODEL_CACHE = {
    "model": None,
    "loaded_at": None
}

def get_cached_model():
    if MODEL_CACHE["model"] is None:
        model = load_model_if_exists()
        if model is not None:
            if isinstance(model, dict) and model.get("embed_size") != 32:
                invalidate_model_cache()
                return None
        MODEL_CACHE["model"] = model
        MODEL_CACHE["loaded_at"] = datetime.datetime.utcnow()
    return MODEL_CACHE["model"]

def invalidate_model_cache():
    """Clear the model cache so it reloads on next recognition."""
    MODEL_CACHE["model"] = None
    MODEL_CACHE["loaded_at"] = None

def save_attendance_to_csv(attendance_id, student_id, name, timestamp):
    """Append attendance record to CSV file."""
    with open(ATTENDANCE_CSV, "a", encoding="utf-8") as f:
        f.write(f"{attendance_id},{student_id},{name},{timestamp}\n")

# =====================================================
# DATABASE INIT
# =====================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            roll TEXT,
            class TEXT,
            section TEXT,
            reg_no TEXT,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            name TEXT,
            timestamp TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            original_name TEXT,
            student_id INTEGER,
            description TEXT,
            uploaded_at TEXT
        )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_attendance_timestamp ON attendance(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_documents_student ON documents(student_id)")

    conn.commit()
    conn.close()

init_db()

# =====================================================
# TRAIN STATUS HELPERS (thread-safe with file locking)
# =====================================================
def write_train_status(status):
    with open(TRAIN_STATUS_FILE, "r+b") as f:
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        try:
            f.seek(0)
            f.truncate()
            json.dump(status, f)
            f.flush()
        finally:
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)

def read_train_status():
    if not os.path.exists(TRAIN_STATUS_FILE):
        return {"running": False, "progress": 0, "message": "Not trained"}
    try:
        with open(TRAIN_STATUS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"running": False, "progress": 0, "message": "Not trained"}

if not os.path.exists(TRAIN_STATUS_FILE):
    write_train_status({"running": False, "progress": 0, "message": "No training yet"})

# =====================================================
# ROUTES
# =====================================================
@app.route("/")
def index():
    return render_template("index.html")

# ---------------- DASHBOARD ----------------
@app.route("/attendance_stats")
def attendance_stats():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT date(timestamp) FROM attendance")
        rows = c.fetchall()

    today = datetime.date.today()
    days = [(today - datetime.timedelta(days=i)) for i in range(29, -1, -1)]
    counts = []

    for d in days:
        counts.append(sum(1 for r in rows if r[0] == d.isoformat()))

    return jsonify({
        "dates": [d.strftime("%d-%b") for d in days],
        "counts": counts
    })

# ---------------- ADD STUDENT ----------------
@app.route("/add_student", methods=["GET", "POST"])
def add_student():
    if request.method == "GET":
        return render_template("add_student.html")

    data = request.form
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name required"}), 400

    with get_db_connection() as conn:
        c = conn.cursor()
        now = datetime.datetime.utcnow().isoformat()

        c.execute("""
            INSERT INTO students (name, roll, class, section, reg_no, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name,
            data.get("roll"),
            data.get("class"),
            data.get("sec"),
            data.get("reg_no"),
            now
        ))

        sid = c.lastrowid
        conn.commit()

    os.makedirs(os.path.join(DATASET_DIR, str(sid)), exist_ok=True)
    return jsonify({"student_id": sid})

# ---------------- UPLOAD FACE ----------------
@app.route("/upload_face", methods=["POST"])
def upload_face():
    sid = request.form.get("student_id")
    if not sid:
        return jsonify({"error": "student_id required"}), 400

    folder = os.path.join(DATASET_DIR, sid)
    os.makedirs(folder, exist_ok=True)

    saved = 0
    for f in request.files.getlist("images[]"):
        fname = f"{datetime.datetime.utcnow().timestamp():.6f}.jpg"
        f.save(os.path.join(folder, fname))
        saved += 1

    return jsonify({"saved": saved})

# ---------------- TRAIN MODEL ----------------
@app.route("/train_model")
def train_model_route():
    status = read_train_status()
    if status.get("running"):
        return jsonify({"status": "already_running"}), 202

    write_train_status({"running": True, "progress": 0, "message": "Starting"})

    def progress(p, m):
        write_train_status({"running": True, "progress": p, "message": m})
        # Invalidate model cache when training completes
        if p >= 100:
            invalidate_model_cache()

    t = threading.Thread(
        target=train_model_background,
        args=(DATASET_DIR, progress)
    )
    t.daemon = True
    t.start()

    return jsonify({"status": "started"}), 202

@app.route("/train_status")
def train_status():
    return jsonify(read_train_status())

# ---------------- MARK ATTENDANCE ----------------
@app.route("/mark_attendance")
def mark_attendance_page():
    return render_template("mark_attendance.html")

@app.route("/recognize_face", methods=["POST"])
def recognize_face():
    if "image" not in request.files:
        return jsonify({"recognized": False}), 400

    emb = extract_embedding_for_image(request.files["image"].stream)
    if emb is None:
        return jsonify({"recognized": False, "error": "No face"}), 200

    clf = get_cached_model()
    if clf is None:
        return jsonify({"recognized": False, "error": "Model not trained"}), 200

    label, conf = predict_with_model(clf, emb)
    if conf < 0.5:
        return jsonify({"recognized": False, "confidence": conf}), 200

    with get_db_connection() as conn:
        c = conn.cursor()

        c.execute("""
            SELECT timestamp FROM attendance
            WHERE student_id=?
            ORDER BY timestamp DESC LIMIT 1
        """, (int(label),))
        row = c.fetchone()
        if row:
            last = datetime.datetime.fromisoformat(row[0])
            if (datetime.datetime.utcnow() - last).total_seconds() < 30:
                return jsonify({
                    "recognized": True,
                    "student_id": int(label),
                    "confidence": conf,
                    "note": "Already marked"
                })

        c.execute("SELECT name FROM students WHERE id=?", (int(label),))
        result = c.fetchone()
        if result is None:
            return jsonify({"recognized": False, "error": "Student not found"}), 200
        name = result[0]

        ts = datetime.datetime.utcnow().isoformat()
        c.execute("""
            INSERT INTO attendance (student_id, name, timestamp)
            VALUES (?, ?, ?)
        """, (int(label), name, ts))
        attendance_id = c.lastrowid

        conn.commit()

    save_attendance_to_csv(attendance_id, int(label), name, ts)

    return jsonify({
        "recognized": True,
        "student_id": int(label),
        "name": name,
        "confidence": conf
    })

# ---------------- RECORDS ----------------
@app.route("/attendance_record")
def attendance_record():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM attendance ORDER BY timestamp DESC LIMIT 5000")
        rows = c.fetchall()
    return render_template("attendance_record.html", records=rows)

@app.route("/download_csv")
def download_csv():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM attendance ORDER BY timestamp DESC")
        rows = c.fetchall()

    out = io.StringIO()
    out.write("id,student_id,name,timestamp\n")
    for r in rows:
        out.write(",".join(map(str, r)) + "\n")

    mem = io.BytesIO(out.getvalue().encode())
    mem.seek(0)

    return send_file(mem, as_attachment=True,
                     download_name="attendance.csv",
                     mimetype="text/csv")

# =====================================================
# DOCUMENT UPLOAD ROUTES
# =====================================================
@app.route("/upload_document", methods=["POST"])
def upload_document():
    if "document" not in request.files:
        return jsonify({"success": False, "error": "No document provided"}), 400

    file = request.files["document"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected"}), 400

    # Validate file type
    allowed_extensions = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        return jsonify({"success": False, "error": "Invalid file type"}), 400

    # Generate unique filename
    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(DOCUMENTS_DIR, unique_name)
    file.save(file_path)

    # Get optional fields
    student_id = request.form.get("student_id", "").strip()
    description = request.form.get("description", "").strip()

    with get_db_connection() as conn:
        c = conn.cursor()
        now = datetime.datetime.utcnow().isoformat()

        c.execute("""
            INSERT INTO documents (filename, original_name, student_id, description, uploaded_at)
            VALUES (?, ?, ?, ?, ?)
        """, (unique_name, file.filename, student_id or None, description, now))

        doc_id = c.lastrowid
        conn.commit()

    return jsonify({"success": True, "id": doc_id})

@app.route("/list_documents")
def list_documents():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id, filename, original_name, student_id, description, uploaded_at FROM documents ORDER BY uploaded_at DESC LIMIT 100")
        rows = c.fetchall()

    docs = []
    for r in rows:
        docs.append({
            "id": r[0],
            "filename": r[2],  # original name
            "student_id": r[3],
            "description": r[4],
            "uploaded_at": r[5]
        })

    return jsonify(docs)

@app.route("/download_document/<int:doc_id>")
def download_document(doc_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT filename, original_name FROM documents WHERE id=?", (doc_id,))
        row = c.fetchone()

    if not row:
        return jsonify({"error": "Document not found"}), 404

    file_path = os.path.join(DOCUMENTS_DIR, row[0])
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    return send_file(file_path, as_attachment=True, download_name=row[1])

# =====================================================
if __name__ == "__main__":
    app.run(debug=True)
