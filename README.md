---
title: FelisEye Face Recognition
emoji: 👁️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# FelisEye — Private AI Face Recognition

**FelisEye** is a production-grade, 100% offline, privacy-first AI face recognition application built completely from scratch. It features real facial detection, alignment, 128D deep metric embedding generation, vector similarity matching, on-device anti-spoofing heuristics, multi-photo profile enrollment, duplicate identity detection, configurable confidence thresholds, and a custom **Neumorphic** interface with Light Mode (Sky-Blue) and Dark Mode (Sea-Blue).

---

## Key Features

1. **100% Offline & Zero-Cost Architecture**
   - No paid cloud APIs, external subscriptions, or third-party telemetry.
   - Runs locally on standard CPU/GPU hardware using dlib ResNet-128D deep metric biometrics.

2. **Real AI Biometric Recognition Engine**
   - **Detection**: HOG + Linear SVM with OpenCV Haar Cascade fallback.
   - **Landmark Alignment**: 68-point facial landmark normalization for rotation correction.
   - **Quality Assessment**: Laplacian blur detection, luminance/contrast analysis, and min dimension validation.
   - **Anti-Spoofing / Liveness**: 2D Fast Fourier Transform (FFT) frequency spectrum analysis, specular reflection detection, and Eye Aspect Ratio (EAR) tracking.
   - **128D Deep Embedding**: Normalized unit vectors projected into biometric metric space.
   - **4-Tier Classification**: **High Confidence**, **Possible Match**, **Low Confidence**, and **Unknown Person**.

3. **Enrollment & People Profile System**
   - System-generated unique IDs (`FE-YYYY-XXXX`).
   - Multi-photo enrollment with centroid embedding fusion.
   - Automatic pre-enrollment duplicate detection warning (`d < 0.38`).
   - Rich profile metadata: Name, Age/DOB, Gender, Notes, and arbitrary key-value custom fields.
   - Cascading data cleanup on profile deletion.

4. **Live Camera & Photo Scan Modes**
   - **Live Camera**: Throttled real-time recognition loop (2.5 FPS analysis, 60 FPS smooth canvas HUD overlays).
   - **Photo Upload**: Multi-face photograph analysis with spatial ordering (top-to-bottom, left-to-right) and individual face selection.

5. **Security & Privacy by Design**
   - **AES Biometric Encryption**: Local encryption of facial vector arrays in SQLite using cryptography keys (`AES-GCM` Fernet).
   - **Zero Retention**: Recognition scan event snapshots are not saved to disk by default.
   - **Complete Backup & Restore**: One-click export/import of database and photos into ZIP bundles.

6. **Premium Neumorphism Interface**
   - **Light Mode**: Sky-Blue (`#e2ebf6`) soft-shadow visual language.
   - **Dark Mode**: Sea-Blue (`#0a1626`) oceanic glow visual language.
   - Intuitive 4-section navigation: **Scan | People | History | Settings**.

---

## Project Structure

```
FelisEye/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Application paths, thresholds, constants
│   │   └── security.py         # AES encryption for vectors & SHA-256 hashing
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── detector.py         # Face detection & 68-point landmark alignment
│   │   ├── quality.py          # Blur, sharpness, lighting, contrast validator
│   │   ├── liveness.py         # FFT frequency texture & anti-spoofing heuristics
│   │   ├── embedder.py         # 128D ResNet embedding & centroid aggregation
│   │   └── matcher.py          # Euclidean distance, similarity %, & 4-tier classifier
│   ├── db/
│   │   ├── __init__.py
│   │   └── database.py         # SQLite schema, CRUD, embeddings, history, settings
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes_scan.py      # /api/scan/frame & /api/scan/photo endpoints
│   │   ├── routes_people.py    # /api/people CRUD, validation, & enrollment
│   │   ├── routes_history.py   # /api/history logs & CSV/JSON export
│   │   └── routes_settings.py  # /api/settings, stats, & backup/restore
│   └── main.py                 # FastAPI application & static routes
├── static/
│   ├── index.html              # Neumorphic Single Page Web Application
│   ├── css/
│   │   └── neumorphism.css     # Sky-Blue & Sea-Blue design system
│   └── js/
│       ├── app.js              # State manager, theme toggle, toasts
│       ├── camera.js           # WebRTC camera capture & Canvas HUD overlay
│       ├── scan.js             # Scan UI, photo upload, multi-face gallery
│       ├── people.js           # People directory & enrollment wizard
│       ├── history.js          # Recognition audit log controller
│       └── settings.js         # Biometric thresholds & backup controller
├── data/                       # Auto-created runtime storage (DB, photos, backups)
│   ├── feliseye.db
│   ├── .secret_key
│   ├── photos/
│   └── backups/
├── tests/
│   ├── test_engine.py          # Engine unit tests
│   ├── test_db.py              # SQLite database tests
│   ├── test_api.py             # REST API integration tests
│   └── test_e2e_recognition.py # End-to-end recognition test
├── run.py                      # Standalone launcher script
├── requirements.txt            # Python dependencies
└── README.md                   # Documentation
```

---

## Technology Stack & Rationale

| Component | Technology | Why Selected |
| :--- | :--- | :--- |
| **Backend Framework** | **FastAPI** + **Uvicorn** | High performance asynchronous I/O, auto validation via Pydantic, native WebSocket/multipart support. |
| **Face Recognition** | **face_recognition** (dlib ResNet-128D) | Established, open-source 128D deep metric model trained on 3 million faces, achieves 99.38% benchmark accuracy. |
| **Computer Vision** | **OpenCV** + **scikit-image** | Industry standard for fast affine transformations, Laplacian blur calculation, and FFT frequency spectrum analysis. |
| **Local Database** | **SQLite** + **PRAGMA WAL** | Zero-configuration, zero-cost, portable single-file database supporting foreign key cascading. |
| **Security / Encryption**| **Python `cryptography`** | AES-GCM Fernet encryption for biometric vector blobs stored in SQLite. |
| **Frontend UI** | **Vanilla ES6 + Modern CSS3** | Zero build step, instant local startup, lightweight, custom Neumorphic components. |

---

## Installation & Setup

### Prerequisites
- Python 3.10, 3.11, or 3.12
- Webcam (optional, for live camera recognition)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the Application
Run the launcher script:
```bash
python run.py
```
This starts the local FastAPI server at `http://127.0.0.1:8000` and automatically opens your default web browser.

---

## User Guide

### 1. Adding / Enrolling Your First Person
1. Click the **People** tab in the top navigation bar.
2. Click **+ Enroll Person**.
3. Enter the person's **Full Name** (e.g. `Eleanor Vance`).
4. Optionally specify Age / DOB, Gender, Notes, or click **+ Add Custom Field** (e.g., `Department: R&D`, `Access: Admin`).
5. Click **+ Select Photos** to upload 1 or more clear front-facing facial photos.
   - The engine automatically checks lighting, sharpness, and verifies single-face validity.
   - If the face matches an already registered person, a duplicate warning banner appears.
6. Click **Enroll Biometric Profile**.
   - A unique ID (e.g., `FE-2026-X9K2`) is assigned, and 128D embeddings are securely stored.

### 2. Live Camera Recognition
1. Navigate to the **Scan** tab.
2. Select **📹 Live Camera** and click **Start Camera**.
3. Position face in front of the camera:
   - Green bounding box with identity name & similarity indicates **High Confidence**.
   - Amber bounding box indicates **Possible Match**.
   - Red bounding box indicates **Unknown Person**.
4. If an unknown face is seen, click **+ Add / Enroll Person** to quickly register them directly from the scan.
5. Click **Capture Snapshot** to log a manual recognition event to the History audit log.

### 3. Photo Upload Recognition
1. In the **Scan** tab, select **🖼️ Upload Photograph**.
2. Drag and drop any image containing one or multiple faces.
3. The engine detects all faces and presents a multi-face selector gallery (`Face #1`, `Face #2`, etc.).
4. Click each face chip to view individual similarity scores and profile matches.

### 4. Viewing History & Data Management
- **History Tab**: View chronological recognition events with timestamps, match status, similarity %, and source. Export to CSV/JSON or clear logs.
- **Settings Tab**: Fine-tune High Confidence and Possible Match distance sliders, toggle Anti-Spoofing heuristics, view database disk footprint, and download a one-click ZIP backup.

---

## How Recognition Works

```
Input Image ──► Face Detection (HOG / Haar)
                     │
                     ▼
            Landmark Extraction (68 points) & Rotation Alignment
                     │
                     ▼
            Quality Assessment (Laplacian Sharpness, Lighting, Size)
                     │
                     ▼
            Anti-Spoofing (FFT Frequency Moiré & Texture Analysis)
                     │
                     ▼
            128D ResNet Deep Embedding Extraction (Unit Vector)
                     │
                     ▼
            Euclidean Distance Comparison vs Enrolled Profiles:
            ┌────────────────────────────────────────────────────────┐
            │  d <= 0.42           ──► HIGH CONFIDENCE  (>= 85% Sim) │
            │  0.42 < d <= 0.52    ──► POSSIBLE MATCH   (70-84% Sim) │
            │  0.52 < d <= 0.62    ──► LOW CONFIDENCE   (55-69% Sim) │
            │  d > 0.62            ──► UNKNOWN PERSON   (< 55% Sim)  │
            └────────────────────────────────────────────────────────┘
```

---

## Running the Automated Test Suite

Run the full suite of unit, database, API, and end-to-end tests:
```bash
python -m unittest discover tests
```

---

## Privacy & Biometric Ethics Notice
FelisEye is designed for private, lawful, and ethical biometric use. It operates completely offline with local storage and AES encryption. When deploying in any organizational environment, ensure full compliance with local biometric information privacy acts (such as GDPR, CCPA, or BIPA), including obtaining explicit informed consent before collecting or processing biometric identifiers.
