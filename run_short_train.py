import time
import os
import cv2
import numpy as np

from model import EMBED_SIZE, PCA_COMPONENTS

def build_embedding_from_image(img, embed_size):
    h, w = img.shape[:2]
    side = min(h, w)
    cx, cy = w // 2, h // 2
    x1 = max(0, cx - side // 2)
    y1 = max(0, cy - side // 2)
    crop = img[y1:y1+side, x1:x1+side]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    small = cv2.resize(gray, (embed_size, embed_size), interpolation=cv2.INTER_AREA)
    emb = small.flatten().astype(np.float32) / 255.0
    return emb

def collect_embeddings(dataset_dir, max_per_class=10):
    X, y = [], []
    student_dirs = [d for d in os.listdir(dataset_dir)
                    if os.path.isdir(os.path.join(dataset_dir, d))]
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
            emb = build_embedding_from_image(img, EMBED_SIZE)
            X.append(emb)
            y.append(int(sid))
            seen += 1
            if seen >= max_per_class:
                break
    return np.array(X), np.array(y)

if __name__ == '__main__':
    start = time.time()
    X, y = collect_embeddings('dataset', max_per_class=10)
    print('Collected samples:', X.shape)

    from sklearn.decomposition import PCA
    from sklearn.ensemble import RandomForestClassifier

    n_samples, n_features = X.shape[0], X.shape[1]
    n_components = min(PCA_COMPONENTS, n_samples - 1, n_features)
    pca = None
    if n_components >= 1 and n_components < n_features:
        pca = PCA(n_components=n_components, svd_solver='randomized', random_state=42)
        Xr = pca.fit_transform(X)
    else:
        Xr = X

    clf = RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=42, max_depth=15)
    t0 = time.time()
    clf.fit(Xr, y)
    t1 = time.time()

    print('Training (PCA+RF) elapsed:', t1 - t0)
    print('Total elapsed:', time.time() - start)
