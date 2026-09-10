import io
import base64
import cv2
import numpy as np
from PIL import Image
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.config import settings, PHOTOS_DIR, DATA_DIR
from app.engine.detector import detector
from app.engine.quality import validate_face_quality
from app.engine.liveness import evaluate_liveness
from app.engine.embedder import embedder
from app.engine.matcher import matcher
from app.db.database import get_all_active_embeddings, log_recognition_event, get_all_settings

router = APIRouter(prefix="/api/scan", tags=["Scan & Recognition"])

class FrameScanRequest(BaseModel):
    image_base64: str  # Data URL or raw base64
    log_event: bool = False
    source: str = "Live Camera"

def _decode_image_base64(b64_string: str) -> np.ndarray:
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
    img_bytes = base64.b64decode(b64_string)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return np.array(img)

def _decode_upload_file(file_bytes: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    return np.array(img)

@router.post("/frame")
async def scan_live_frame(payload: FrameScanRequest):
    """
    Analyzes a live camera frame. Returns detected faces, bounding boxes,
    quality metrics, liveness score, and biometric match results.
    """
    try:
        image_rgb = _decode_image_base64(payload.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image: {str(e)}")

    h, w, _ = image_rgb.shape
    system_settings = get_all_settings()
    
    # 1. Detect faces
    face_locations = detector.detect_faces(image_rgb)
    if not face_locations:
        return {
            "faces_detected": 0,
            "results": [],
            "message": "No face detected in camera view"
        }

    # Fetch active database embeddings for matching
    known_items = get_all_active_embeddings()

    results = []
    # Primary mode: one face, or process up to 3 faces in frame
    for idx, loc in enumerate(face_locations[:3]):
        top, right, bottom, left = loc
        face_crop = image_rgb[top:bottom, left:right]
        
        # 2. Quality validation
        quality = validate_face_quality(face_crop, loc)
        
        # 3. Facial landmarks (for liveness & alignment)
        landmarks_list = detector.get_landmarks(image_rgb, [loc])
        landmarks = landmarks_list[0] if landmarks_list else None
        
        # 4. Anti-spoofing / Liveness
        liveness = evaluate_liveness(face_crop, landmarks)
        
        # 5. Extract 128D Embedding
        vec = embedder.compute_embedding(image_rgb, known_face_location=loc, jitters=1)
        
        # 6. Biometric Matching
        if vec is not None:
            match_res = matcher.match_against_known(
                vec,
                known_items,
                threshold_high=system_settings.get("threshold_high_confidence"),
                threshold_match=system_settings.get("threshold_possible_match"),
                threshold_low=system_settings.get("threshold_low_confidence")
            )
        else:
            match_res = {
                "matched": False,
                "tier": "UNKNOWN",
                "tier_label": "Unknown Person",
                "similarity": 0.0,
                "distance": 2.0,
                "person": None,
                "top_candidates": []
            }
            
        # Log event if requested (e.g. manual snap or stable high confidence match)
        if payload.log_event and vec is not None:
            log_recognition_event(
                result_status=match_res["tier"],
                matched_person_id=match_res["person"]["id"] if match_res["person"] else None,
                matched_person_name=match_res["person"]["full_name"] if match_res["person"] else None,
                similarity_score=match_res["similarity"],
                distance=match_res["distance"],
                source=payload.source
            )
            
        results.append({
            "index": idx,
            "bbox": {
                "top": top,
                "right": right,
                "bottom": bottom,
                "left": left,
                "width": right - left,
                "height": bottom - top,
                "norm_top": top / h,
                "norm_right": right / w,
                "norm_bottom": bottom / h,
                "norm_left": left / w
            },
            "quality": quality,
            "liveness": liveness,
            "match": match_res
        })

    return {
        "faces_detected": len(face_locations),
        "frame_dimensions": {"width": w, "height": h},
        "results": results
    }

@router.post("/photo")
async def scan_photo(
    file: UploadFile = File(...),
    log_event: bool = Form(True)
):
    """
    Analyzes an uploaded photograph with multi-face support.
    Orders faces left-to-right / top-to-bottom and provides individual match results.
    """
    try:
        contents = await file.read()
        image_rgb = _decode_upload_file(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded image: {str(e)}")

    h, w, _ = image_rgb.shape
    system_settings = get_all_settings()
    
    # Detect all faces in photo
    face_locations = detector.detect_faces(image_rgb, upsample=1)
    if not face_locations:
        return {
            "faces_detected": 0,
            "results": [],
            "message": "No faces found in uploaded photograph."
        }

    # Sort faces spatially (top-to-bottom, left-to-right)
    # Sorting key: bucket top in 100px slices then by left coordinate
    face_locations.sort(key=lambda loc: (loc[0] // 100, loc[3]))
    
    known_items = get_all_active_embeddings()
    results = []

    for idx, loc in enumerate(face_locations):
        top, right, bottom, left = loc
        face_crop = image_rgb[top:bottom, left:right]
        quality = validate_face_quality(face_crop, loc)
        
        landmarks_list = detector.get_landmarks(image_rgb, [loc])
        landmarks = landmarks_list[0] if landmarks_list else None
        liveness = evaluate_liveness(face_crop, landmarks)
        
        vec = embedder.compute_embedding(image_rgb, known_face_location=loc, jitters=2)
        
        if vec is not None:
            match_res = matcher.match_against_known(
                vec,
                known_items,
                threshold_high=system_settings.get("threshold_high_confidence"),
                threshold_match=system_settings.get("threshold_possible_match"),
                threshold_low=system_settings.get("threshold_low_confidence")
            )
        else:
            match_res = {
                "matched": False,
                "tier": "UNKNOWN",
                "tier_label": "Unknown Person",
                "similarity": 0.0,
                "distance": 2.0,
                "person": None,
                "top_candidates": []
            }
            
        if log_event and vec is not None:
            log_recognition_event(
                result_status=match_res["tier"],
                matched_person_id=match_res["person"]["id"] if match_res["person"] else None,
                matched_person_name=match_res["person"]["full_name"] if match_res["person"] else None,
                similarity_score=match_res["similarity"],
                distance=match_res["distance"],
                source="Photo Upload"
            )
            
        # Encode face thumbnail as small data URL for preview
        thumb_b64 = ""
        try:
            pil_crop = Image.fromarray(face_crop)
            pil_crop.thumbnail((120, 120))
            buffered = io.BytesIO()
            pil_crop.save(buffered, format="JPEG", quality=85)
            thumb_b64 = "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode('utf-8')
        except Exception:
            pass

        results.append({
            "index": idx,
            "face_number": idx + 1,
            "thumbnail": thumb_b64,
            "bbox": {
                "top": top,
                "right": right,
                "bottom": bottom,
                "left": left,
                "width": right - left,
                "height": bottom - top,
                "norm_top": top / h,
                "norm_right": right / w,
                "norm_bottom": bottom / h,
                "norm_left": left / w
            },
            "quality": quality,
            "liveness": liveness,
            "match": match_res
        })

    return {
        "faces_detected": len(face_locations),
        "frame_dimensions": {"width": w, "height": h},
        "results": results
    }
