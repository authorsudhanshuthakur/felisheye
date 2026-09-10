import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.responses import FileResponse

from app.core.config import DATA_DIR, PHOTOS_DIR, DB_PATH, BACKUPS_DIR
from app.db.database import (
    get_all_settings, update_setting, export_backup_zip, restore_backup_zip,
    get_connection
)

router = APIRouter(prefix="/api/settings", tags=["Settings & Data Management"])

class SettingsUpdatePayload(BaseModel):
    threshold_high_confidence: Optional[float] = None
    threshold_possible_match: Optional[float] = None
    threshold_low_confidence: Optional[float] = None
    threshold_duplicate_warn: Optional[float] = None
    liveness_enabled: Optional[bool] = None
    liveness_min_score: Optional[float] = None
    encrypt_embeddings: Optional[bool] = None
    save_recognition_photos: Optional[bool] = None
    theme: Optional[str] = None

@router.get("")
async def get_settings():
    """Retrieves all active system configurations and biometric thresholds."""
    return get_all_settings()

@router.put("")
async def update_system_settings(payload: SettingsUpdatePayload):
    """Updates system configurations."""
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        update_setting(key, value)
    return {"success": True, "message": "Settings updated successfully.", "settings": get_all_settings()}

@router.get("/stats")
async def get_system_stats():
    """Returns database size, people count, embedding count, and history volume."""
    conn = get_connection()
    people_count = conn.execute("SELECT COUNT(*) FROM people").fetchone()[0]
    embeddings_count = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
    history_count = conn.execute("SELECT COUNT(*) FROM recognition_history").fetchone()[0]
    conn.close()

    # Calculate storage size
    total_photo_bytes = 0
    if PHOTOS_DIR.exists():
        for f in PHOTOS_DIR.glob("**/*"):
            if f.is_file():
                total_photo_bytes += f.stat().st_size
                
    db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0

    return {
        "people_count": people_count,
        "embeddings_count": embeddings_count,
        "history_count": history_count,
        "db_size_bytes": db_size,
        "db_size_kb": round(db_size / 1024, 2),
        "photo_storage_bytes": total_photo_bytes,
        "photo_storage_mb": round(total_photo_bytes / (1024 * 1024), 2)
    }

@router.get("/backup")
async def download_backup():
    """Generates and downloads a complete ZIP archive backup of database and facial photos."""
    try:
        zip_path = export_backup_zip()
        return FileResponse(
            path=str(zip_path),
            filename=zip_path.name,
            media_type="application/zip"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate backup: {str(e)}")

@router.post("/restore")
async def upload_restore_backup(file: UploadFile = File(...)):
    """Restores database and photos from an uploaded backup ZIP archive."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip backup files are supported.")
    
    temp_path = BACKUPS_DIR / f"temp_restore_{file.filename}"
    try:
        contents = await file.read()
        with open(temp_path, "wb") as f:
            f.write(contents)
            
        success = restore_backup_zip(temp_path)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to extract backup archive.")
            
        return {"success": True, "message": "Backup restored successfully."}
    finally:
        if temp_path.exists():
            temp_path.unlink()
