import os
from pathlib import Path
from typing import Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
PHOTOS_DIR = DATA_DIR / "photos"
BACKUPS_DIR = DATA_DIR / "backups"
DB_PATH = DATA_DIR / "feliseye.db"
KEY_PATH = DATA_DIR / ".secret_key"

# Ensure runtime directories exist
for folder in [DATA_DIR, PHOTOS_DIR, BACKUPS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

class AppSettings:
    APP_NAME: str = "FelisEye"
    APP_VERSION: str = "1.0.0"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    
    # Biometric Recognition Thresholds (Euclidean Distance on 128D normalized vectors)
    # Lower distance = Higher similarity
    # d <= 0.42: High Confidence (Similarity >= ~85%)
    # 0.42 < d <= 0.52: Possible Match (Similarity ~70-84%)
    # 0.52 < d <= 0.62: Low Confidence (Similarity ~55-69%)
    # d > 0.62: Unknown (Similarity < 55%)
    THRESHOLD_HIGH_CONFIDENCE: float = 0.42
    THRESHOLD_POSSIBLE_MATCH: float = 0.52
    THRESHOLD_LOW_CONFIDENCE: float = 0.62
    
    # Duplicate Warning Threshold (Distance during enrollment below which we warn)
    THRESHOLD_DUPLICATE_WARN: float = 0.38
    
    # Anti-Spoofing / Liveness Settings
    LIVENESS_ENABLED: bool = True
    LIVENESS_MIN_SCORE: float = 0.50  # 0.0 to 1.0 composite liveness score
    
    # Quality Filter Thresholds
    MIN_FACE_SIZE: int = 70  # Minimum face width/height in pixels
    MIN_SHARPNESS: float = 60.0  # Laplacian variance threshold
    MIN_BRIGHTNESS: float = 40.0  # Mean grayscale brightness (0-255)
    MAX_BRIGHTNESS: float = 220.0
    
    # Privacy & Storage
    ENCRYPT_EMBEDDINGS: bool = True
    SAVE_RECOGNITION_PHOTOS: bool = False  # Zero retention by default
    HISTORY_MAX_ENTRIES: int = 1000

settings = AppSettings()
