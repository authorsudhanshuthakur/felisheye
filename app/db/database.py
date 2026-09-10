import os
import sqlite3
import json
import random
import string
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from app.core.config import DB_PATH, DATA_DIR, PHOTOS_DIR, BACKUPS_DIR, settings
from app.core.security import encrypt_vector, decrypt_vector

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initializes SQLite database tables and default settings."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # People Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS people (
        id TEXT PRIMARY KEY,
        full_name TEXT NOT NULL,
        dob_or_age TEXT,
        gender TEXT,
        notes TEXT,
        custom_fields TEXT DEFAULT '{}',
        profile_photo_path TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    
    # Embeddings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id TEXT NOT NULL,
        vector_data TEXT NOT NULL,
        photo_path TEXT,
        photo_hash TEXT,
        is_centroid INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (person_id) REFERENCES people (id) ON DELETE CASCADE
    )
    """)
    
    # History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recognition_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        result_status TEXT NOT NULL,
        matched_person_id TEXT,
        matched_person_name TEXT,
        similarity_score REAL,
        distance REAL,
        source TEXT NOT NULL,
        snapshot_path TEXT
    )
    """)
    
    # Settings Store Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings_store (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)
    
    # Create indexes for fast lookup
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_people_name ON people(full_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_person ON embeddings(person_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_time ON recognition_history(timestamp)")
    
    conn.commit()
    conn.close()

def generate_person_id() -> str:
    """Generates a unique, elegant ID like FE-2026-A8F2."""
    year = datetime.now().year
    conn = get_connection()
    while True:
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        candidate_id = f"FE-{year}-{suffix}"
        row = conn.execute("SELECT id FROM people WHERE id = ?", (candidate_id,)).fetchone()
        if not row:
            conn.close()
            return candidate_id

# ----------------- PEOPLE CRUD ----------------- #

def create_person(
    full_name: str,
    dob_or_age: Optional[str] = None,
    gender: Optional[str] = None,
    notes: Optional[str] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
    profile_photo_path: Optional[str] = None,
    custom_id: Optional[str] = None
) -> str:
    person_id = custom_id or generate_person_id()
    now_str = datetime.now().isoformat()
    custom_json = json.dumps(custom_fields or {})
    
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO people (id, full_name, dob_or_age, gender, notes, custom_fields, profile_photo_path, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (person_id, full_name.strip(), dob_or_age, gender, notes, custom_json, profile_photo_path, now_str, now_str)
    )
    conn.commit()
    conn.close()
    return person_id

def get_person(person_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
    if not row:
        conn.close()
        return None
    data = dict(row)
    data["custom_fields"] = json.loads(data.get("custom_fields") or "{}")
    photo_rows = conn.execute(
        "SELECT id as embedding_id, photo_path, is_centroid, created_at FROM embeddings WHERE person_id = ? AND photo_path IS NOT NULL AND is_centroid = 0 ORDER BY created_at ASC",
        (person_id,)
    ).fetchall()
    data["photos"] = [dict(pr) for pr in photo_rows]
    data["photos_count"] = len(data["photos"])
    conn.close()
    return data

def update_person(
    person_id: str,
    full_name: Optional[str] = None,
    dob_or_age: Optional[str] = None,
    gender: Optional[str] = None,
    notes: Optional[str] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
    profile_photo_path: Optional[str] = None
) -> bool:
    current = get_person(person_id)
    if not current:
        return False
    
    now_str = datetime.now().isoformat()
    new_name = full_name.strip() if full_name is not None else current["full_name"]
    new_dob = dob_or_age if dob_or_age is not None else current["dob_or_age"]
    new_gender = gender if gender is not None else current["gender"]
    new_notes = notes if notes is not None else current["notes"]
    new_custom = json.dumps(custom_fields if custom_fields is not None else current["custom_fields"])
    new_photo = profile_photo_path if profile_photo_path is not None else current["profile_photo_path"]
    
    conn = get_connection()
    conn.execute(
        """
        UPDATE people
        SET full_name = ?, dob_or_age = ?, gender = ?, notes = ?, custom_fields = ?, profile_photo_path = ?, updated_at = ?
        WHERE id = ?
        """,
        (new_name, new_dob, new_gender, new_notes, new_custom, new_photo, now_str, person_id)
    )
    conn.commit()
    conn.close()
    return True

def delete_person(person_id: str) -> bool:
    conn = get_connection()
    # Get associated photo files to delete from disk
    cursor = conn.execute("SELECT profile_photo_path FROM people WHERE id = ?", (person_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    
    # Also fetch embedding photos
    photo_rows = conn.execute("SELECT photo_path FROM embeddings WHERE person_id = ?", (person_id,)).fetchall()
    
    # Delete from DB (foreign key cascades delete embeddings)
    conn.execute("DELETE FROM people WHERE id = ?", (person_id,))
    conn.commit()
    conn.close()
    
    # Clean up disk files
    paths_to_delete = set()
    if row["profile_photo_path"]:
        paths_to_delete.add(row["profile_photo_path"])
    for pr in photo_rows:
        if pr["photo_path"]:
            paths_to_delete.add(pr["photo_path"])
            
    for p in paths_to_delete:
        try:
            full_p = DATA_DIR / p if not os.path.isabs(p) else Path(p)
            if full_p.exists() and full_p.is_file():
                full_p.unlink()
        except Exception as e:
            print(f"[Cleanup Warning] Failed to delete photo file {p}: {e}")
            
    return True

def get_all_people(
    search_query: Optional[str] = None,
    gender_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Tuple[List[Dict[str, Any]], int]:
    conn = get_connection()
    query = "SELECT * FROM people WHERE 1=1"
    params = []
    
    if search_query and search_query.strip():
        q = f"%{search_query.strip().lower()}%"
        query += " AND (LOWER(full_name) LIKE ? OR LOWER(id) LIKE ? OR LOWER(notes) LIKE ? OR LOWER(custom_fields) LIKE ?)"
        params.extend([q, q, q, q])
        
    if gender_filter and gender_filter.strip():
        query += " AND gender = ?"
        params.append(gender_filter.strip())
        
    # Total count
    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    total_count = conn.execute(count_query, params).fetchone()[0]
    
    # Paged items
    query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    rows = conn.execute(query, params).fetchall()
    
    people_list = []
    for r in rows:
        d = dict(r)
        d["custom_fields"] = json.loads(d.get("custom_fields") or "{}")
        # Count number of registered biometric samples
        emb_count = conn.execute("SELECT COUNT(*) FROM embeddings WHERE person_id = ?", (d["id"],)).fetchone()[0]
        d["photos_count"] = emb_count
        people_list.append(d)
        
    conn.close()
    return people_list, total_count

# ----------------- EMBEDDINGS MANAGEMENT ----------------- #

def add_embedding(
    person_id: str,
    vector: np.ndarray,
    photo_path: Optional[str] = None,
    photo_hash: Optional[str] = None,
    is_centroid: bool = False
) -> int:
    encrypted_str = encrypt_vector(vector)
    now_str = datetime.now().isoformat()
    
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO embeddings (person_id, vector_data, photo_path, photo_hash, is_centroid, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (person_id, encrypted_str, photo_path, photo_hash, 1 if is_centroid else 0, now_str)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_all_active_embeddings() -> List[Dict[str, Any]]:
    """
    Returns list of items for vector matching.
    Prefers centroid representation if exists, otherwise all individual embeddings.
    """
    conn = get_connection()
    cursor = conn.execute("""
        SELECT e.id as embedding_id, e.person_id, e.vector_data, e.is_centroid,
               p.full_name, p.dob_or_age, p.gender, p.notes, p.custom_fields, p.profile_photo_path
        FROM embeddings e
        JOIN people p ON e.person_id = p.id
    """)
    rows = cursor.fetchall()
    conn.close()
    
    items = []
    for r in rows:
        try:
            vec = decrypt_vector(r["vector_data"])
            items.append({
                "embedding_id": r["embedding_id"],
                "person_id": r["person_id"],
                "full_name": r["full_name"],
                "profile_photo_path": r["profile_photo_path"],
                "custom_fields": json.loads(r["custom_fields"] or "{}"),
                "notes": r["notes"],
                "vector": vec,
                "is_centroid": bool(r["is_centroid"])
            })
        except Exception as e:
            print(f"[Decryption Error] Skipped embedding {r['embedding_id']}: {e}")
            
    return items

def get_person_embeddings(person_id: str) -> List[np.ndarray]:
    conn = get_connection()
    rows = conn.execute("SELECT vector_data FROM embeddings WHERE person_id = ?", (person_id,)).fetchall()
    conn.close()
    vectors = []
    for r in rows:
        try:
            vectors.append(decrypt_vector(r["vector_data"]))
        except Exception:
            pass
    return vectors

def recompute_person_centroid(person_id: str) -> Optional[int]:
    """
    Recalculates and updates the centroid embedding for a person if multiple non-centroid embeddings exist.
    """
    from app.engine.embedder import embedder
    
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, vector_data FROM embeddings WHERE person_id = ? AND is_centroid = 0",
        (person_id,)
    ).fetchall()
    
    # Delete existing centroid embedding(s)
    conn.execute("DELETE FROM embeddings WHERE person_id = ? AND is_centroid = 1", (person_id,))
    conn.commit()
    
    if len(rows) > 1:
        vectors = []
        for r in rows:
            try:
                vectors.append(decrypt_vector(r["vector_data"]))
            except Exception:
                pass
        if len(vectors) > 1:
            centroid_vec = embedder.aggregate_embeddings(vectors)
            person_row = conn.execute("SELECT profile_photo_path FROM people WHERE id = ?", (person_id,)).fetchone()
            photo_path = person_row["profile_photo_path"] if person_row else None
            conn.close()
            return add_embedding(
                person_id=person_id,
                vector=centroid_vec,
                photo_path=photo_path,
                is_centroid=True
            )
    conn.close()
    return None

def delete_person_photo_embedding(person_id: str, embedding_id: int) -> bool:
    """
    Deletes an individual face embedding and associated photo file, provided at least one other photo remains.
    """
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM embeddings WHERE person_id = ? AND is_centroid = 0", (person_id,)).fetchone()[0]
    if count <= 1:
        conn.close()
        return False  # Do not delete the only biometric photo
    
    row = conn.execute("SELECT photo_path FROM embeddings WHERE id = ? AND person_id = ?", (embedding_id, person_id)).fetchone()
    if not row:
        conn.close()
        return False
    
    photo_path = row["photo_path"]
    conn.execute("DELETE FROM embeddings WHERE id = ? AND person_id = ?", (embedding_id, person_id))
    conn.commit()
    conn.close()
    
    if photo_path:
        try:
            full_p = DATA_DIR / photo_path if not os.path.isabs(photo_path) else Path(photo_path)
            if full_p.exists() and full_p.is_file():
                full_p.unlink()
        except Exception as e:
            print(f"[Cleanup Warning] Failed to delete photo file {photo_path}: {e}")
            
    recompute_person_centroid(person_id)
    return True


# ----------------- RECOGNITION HISTORY ----------------- #

def log_recognition_event(
    result_status: str,
    matched_person_id: Optional[str] = None,
    matched_person_name: Optional[str] = None,
    similarity_score: Optional[float] = None,
    distance: Optional[float] = None,
    source: str = "Live Camera",
    snapshot_path: Optional[str] = None
) -> int:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO recognition_history (timestamp, result_status, matched_person_id, matched_person_name, similarity_score, distance, source, snapshot_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (now_str, result_status, matched_person_id, matched_person_name, similarity_score, distance, source, snapshot_path)
    )
    new_id = cursor.lastrowid
    
    # Enforce history limit
    conn.execute(
        f"""
        DELETE FROM recognition_history 
        WHERE id NOT IN (
            SELECT id FROM recognition_history ORDER BY id DESC LIMIT {settings.HISTORY_MAX_ENTRIES}
        )
        """
    )
    conn.commit()
    conn.close()
    return new_id

def get_history(
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], int]:
    conn = get_connection()
    query = "SELECT * FROM recognition_history WHERE 1=1"
    params = []
    
    if status_filter and status_filter.strip():
        query += " AND result_status = ?"
        params.append(status_filter.strip())
        
    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    total = conn.execute(count_query, params).fetchone()[0]
    
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows], total

def clear_history() -> int:
    conn = get_connection()
    cursor = conn.execute("DELETE FROM recognition_history")
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count

# ----------------- SYSTEM SETTINGS STORE ----------------- #

def get_all_settings() -> Dict[str, Any]:
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM settings_store").fetchall()
    conn.close()
    stored = {}
    for r in rows:
        try:
            stored[r["key"]] = json.loads(r["value"])
        except Exception:
            stored[r["key"]] = r["value"]
            
    # Combine with config defaults
    defaults = {
        "threshold_high_confidence": settings.THRESHOLD_HIGH_CONFIDENCE,
        "threshold_possible_match": settings.THRESHOLD_POSSIBLE_MATCH,
        "threshold_low_confidence": settings.THRESHOLD_LOW_CONFIDENCE,
        "threshold_duplicate_warn": settings.THRESHOLD_DUPLICATE_WARN,
        "liveness_enabled": settings.LIVENESS_ENABLED,
        "liveness_min_score": settings.LIVENESS_MIN_SCORE,
        "encrypt_embeddings": settings.ENCRYPT_EMBEDDINGS,
        "save_recognition_photos": settings.SAVE_RECOGNITION_PHOTOS,
        "theme": "dark"
    }
    defaults.update(stored)
    return defaults

def update_setting(key: str, value: Any):
    conn = get_connection()
    val_str = json.dumps(value)
    conn.execute(
        "INSERT INTO settings_store (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, val_str)
    )
    conn.commit()
    conn.close()

# ----------------- BACKUP & RESTORE ----------------- #

def export_backup_zip() -> Path:
    """Creates a timestamped backup zip containing DB and photos."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"feliseye_backup_{timestamp}.zip"
    zip_path = BACKUPS_DIR / zip_filename
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        if DB_PATH.exists():
            zipf.write(DB_PATH, arcname="feliseye.db")
        if PHOTOS_DIR.exists():
            for root, _, files in os.walk(PHOTOS_DIR):
                for file in files:
                    file_p = Path(root) / file
                    rel_p = file_p.relative_to(DATA_DIR)
                    zipf.write(file_p, arcname=str(rel_p))
                    
    return zip_path

def restore_backup_zip(zip_file_path: Path) -> bool:
    """Restores DB and photos from a backup zip."""
    if not zip_file_path.exists():
        return False
    with zipfile.ZipFile(zip_file_path, 'r') as zipf:
        zipf.extractall(DATA_DIR)
    return True
