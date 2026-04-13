import os
import cv2
import numpy as np
import pickle

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)) or ".", "model.pkl")
EMBED_SIZE = 32
PCA_COMPONENTS = 16
MAX_IMAGES_PER_CLASS = 15

# Use Haar cascade as fallback (built into OpenCV)
HAAR_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def detect_face_opencv(bgr_image):
    """Detect face using OpenCV Haar cascade (fast and compatible)."""
    gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
    faces = HAAR_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    if len(faces) == 0:
        return None
    # Return the largest face
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return (x, y, w, h)

# =====================================================
# FACE EMBEDDING
# =====================================================
def crop_face_and_embed(bgr_image, face_rect):
    """Crop face from image and create embedding with preprocessing.
    face_rect: (x, y, w, h) tuple from OpenCV detection
    """
    x, y, w, h = face_rect
    
    if w <= 0 or h <= 0:
        return None

    face = bgr_image[y:y+h, x:x+w]
    face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    
    face = cv2.equalizeHist(face)
    
    face = cv2.resize(face, (EMBED_SIZE, EMBED_SIZE), interpolation=cv2.INTER_AREA)
    
    face = cv2.GaussianBlur(face, (3, 3), 0)

    emb = face.flatten().astype(np.float32) / 255.0
    return emb


# =====================================================
# EXTRACT EMBEDDING FROM UPLOADED IMAGE
# =====================================================
# def extract_embedding_for_image(stream_or_bytes):
#     import mediapipe as mp

#     stream_or_bytes.seek(0)   # 🔥 IMPORTANT FIX
#     data = stream_or_bytes.read()

#     arr = np.frombuffer(data, np.uint8)
#     img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
#     if img is None:
#         return None

#     mp_face = mp.solutions.face_detection.FaceDetection(
#         model_selection=1,
#         min_detection_confidence=0.5
#     )

#     results = mp_face.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
#     if not results.detections:
#         return None

#     return crop_face_and_embed(img, results.detections[0])



def extract_embedding_for_image(stream_or_bytes):
    """Extract face embedding from uploaded image stream."""
    stream_or_bytes.seek(0)
    data = stream_or_bytes.read()

    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if img is None:
        return None

    face_rect = detect_face_opencv(img)
    if face_rect is None:
        return None

    return crop_face_and_embed(img, face_rect)

# =====================================================
# LOAD MODEL
# =====================================================
def load_model_if_exists():
    if not os.path.exists(MODEL_PATH):
        return None
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


# =====================================================
# PREDICTION (SVM)
# =====================================================
def predict_with_model(clf, emb):
    # Support both legacy direct classifier objects and saved pipeline dicts
    if isinstance(clf, dict):
        pca = clf.get("pca")
        model = clf.get("clf")
    else:
        pca = None
        model = clf

    X = np.array([emb])
    if pca is not None:
        X = pca.transform(X)

    # prefer predict_proba when available (RandomForest), else decision_function
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)[0]
        idx = int(np.argmax(proba))
        label = model.classes_[idx]
        confidence = float(proba[idx])
    elif hasattr(model, "decision_function"):
        scores = model.decision_function(X)
        if scores.ndim == 1:
            label = model.predict(X)[0]
            confidence = float(1 / (1 + np.exp(-abs(scores[0]))))
        else:
            idx = int(np.argmax(scores))
            label = model.classes_[idx]
            confidence = float(1 / (1 + np.exp(-scores[0][idx])))
    else:
        label = model.predict(X)[0]
        confidence = 1.0

    return label, confidence


# =====================================================
# TRAIN MODEL (OpenCV Face Detection + RandomForest)
# =====================================================
def train_model_background(dataset_dir, progress_callback=None, max_per_class=None):
    if max_per_class is None:
        max_per_class = MAX_IMAGES_PER_CLASS

    X, y = [], []

    student_dirs = [d for d in os.listdir(dataset_dir)
                    if os.path.isdir(os.path.join(dataset_dir, d))]

    total_students = max(1, len(student_dirs))
    processed = 0

    for sid in student_dirs:
        folder = os.path.join(dataset_dir, sid)
        files = [f for f in os.listdir(folder)
                 if f.lower().endswith((".jpg", ".jpeg", ".png"))]

        seen = 0
        for fn in files:
            path = os.path.join(folder, fn)
            img = cv2.imread(path)
            if img is None:
                continue

            face_rect = detect_face_opencv(img)
            if face_rect is None:
                continue

            emb = crop_face_and_embed(img, face_rect)
            if emb is None:
                continue

            X.append(emb)
            y.append(int(sid))
            seen += 1
            if max_per_class is not None and seen >= max_per_class:
                break

        processed += 1
        if progress_callback:
            pct = int((processed / total_students) * 80)
            progress_callback(pct, f"Processed {processed}/{total_students} students")

    if len(X) == 0:
        if progress_callback:
            progress_callback(0, "No training data found")
        return

    X = np.array(X)
    y = np.array(y)

    if progress_callback:
        progress_callback(85, "Applying PCA + training classifier...")

    from sklearn.decomposition import PCA
    from sklearn.ensemble import RandomForestClassifier

    n_samples, n_features = X.shape[0], X.shape[1]
    n_components = min(PCA_COMPONENTS, n_samples - 1, n_features)
    pca = None
    if n_components >= 1 and n_components < n_features:
        pca = PCA(n_components=n_components, svd_solver="randomized", random_state=42)
        X_reduced = pca.fit_transform(X)
    else:
        X_reduced = X

    clf = RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=42, max_depth=15)
    clf.fit(X_reduced, y)

    model_obj = {"clf": clf, "pca": pca, "embed_size": EMBED_SIZE}
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model_obj, f)

    if progress_callback:
        progress_callback(100, "Training complete")


# import os
# import cv2
# import numpy as np
# import pickle
# from sklearn.ensemble import RandomForestClassifier

# MODEL_PATH = "model.pkl"

# # ---- Utility: extract face crop -> small grayscale vector (embedding) ----
# def crop_face_and_embed(bgr_image, detection):
#     h, w = bgr_image.shape[:2]
#     bbox = detection.location_data.relative_bounding_box
#     x1 = int(max(0, bbox.xmin * w))
#     y1 = int(max(0, bbox.ymin * h))
#     x2 = int(min(w, (bbox.xmin + bbox.width) * w))
#     y2 = int(min(h, (bbox.ymin + bbox.height) * h))
#     if x2 <= x1 or y2 <= y1:
#         return None
#     face = bgr_image[y1:y2, x1:x2]
#     face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
#     face = cv2.resize(face, (32,32), interpolation=cv2.INTER_AREA)
#     emb = face.flatten().astype(np.float32) / 255.0
#     return emb

# def extract_embedding_for_image(stream_or_bytes):
#     # accepts a file-like stream (werkzeug FileStorage.stream)
#     import mediapipe as mp
#     mp_face = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
#     # read image from stream into numpy BGR
#     data = stream_or_bytes.read()
#     arr = np.frombuffer(data, np.uint8)
#     img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
#     if img is None:
#         return None
#     results = mp_face.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
#     if not results.detections:
#         return None
#     emb = crop_face_and_embed(img, results.detections[0])
#     return emb

# # ---- Load model helpers ----
# def load_model_if_exists():
#     if not os.path.exists(MODEL_PATH):
#         return None
#     with open(MODEL_PATH, "rb") as f:
#         return pickle.load(f)

# def predict_with_model(clf, emb):
#     # returns label and confidence (max probability)
#     proba = clf.predict_proba([emb])[0]
#     idx = np.argmax(proba)
#     label = clf.classes_[idx]
#     conf = float(proba[idx])
#     return label, conf

# # ---- Training function used in background ----
# def train_model_background(dataset_dir, progress_callback=None):
#     """
#     dataset_dir/
#         student_id/
#             img1.jpg
#             img2.jpg
#     progress_callback(progress_percent, message) -> optional
#     """
#     import mediapipe as mp
#     mp_face = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)

#     X = []
#     y = []
#     student_dirs = [d for d in os.listdir(dataset_dir) if os.path.isdir(os.path.join(dataset_dir, d))]
#     total_students = max(1, len(student_dirs))
#     processed = 0

#     for sid in student_dirs:
#         folder = os.path.join(dataset_dir, sid)
#         files = [f for f in os.listdir(folder) if f.lower().endswith((".jpg",".jpeg",".png"))]
#         for fn in files:
#             path = os.path.join(folder, fn)
#             img = cv2.imread(path)
#             if img is None:
#                 continue
#             results = mp_face.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
#             if not results.detections:
#                 continue
#             emb = crop_face_and_embed(img, results.detections[0])
#             if emb is None:
#                 continue
#             X.append(emb)
#             y.append(int(sid))
#         processed += 1
#         if progress_callback:
#             pct = int((processed/total_students)*80)  # training progress up to 80% during feature extraction
#             progress_callback(pct, f"Processed {processed}/{total_students} students")

#     if len(X) == 0:
#         if progress_callback:
#             progress_callback(0, "No training data found")
#         return

#     # convert
#     X = np.stack(X)
#     y = np.array(y)

#     # fit RandomForest
#     if progress_callback:
#         progress_callback(85, "Training RandomForest...")
#     clf = RandomForestClassifier(n_estimators=150, n_jobs=-1, random_state=42)
#     clf.fit(X, y)

#     with open(MODEL_PATH, "wb") as f:
#         pickle.dump(clf, f)

#     if progress_callback:
#         progress_callback(100, "Training complete")
