import io
import json
import uuid
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Query
from pydantic import BaseModel

from app.core.config import PHOTOS_DIR, DATA_DIR, settings
from app.core.security import compute_image_hash
from app.engine.detector import detector
from app.engine.quality import validate_face_quality
from app.engine.embedder import embedder
from app.engine.matcher import matcher
from app.db.database import (
    create_person, get_person, update_person, delete_person, get_all_people,
    add_embedding, get_all_active_embeddings, get_all_settings,
    recompute_person_centroid, delete_person_photo_embedding
)

router = APIRouter(prefix="/api/people", tags=["People Profiles & Enrollment"])

def _read_image(file_bytes: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    return np.array(img)

@router.get("")
async def list_people(
    search: Optional[str] = Query(None, description="Search by name, ID, or custom fields"),
    gender: Optional[str] = Query(None, description="Filter by gender"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Retrieves paginated list of registered people profiles with filters."""
    people, total = get_all_people(search_query=search, gender_filter=gender, limit=limit, offset=offset)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "people": people
    }

@router.get("/{person_id}")
async def get_person_profile(person_id: str):
    """Retrieves full details of a specific profile."""
    person = get_person(person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person profile not found.")
    return person

@router.post("/validate-photo")
async def validate_enrollment_photo(
    file: UploadFile = File(...)
):
    """
    Validates a facial photo prior to enrollment.
    Checks face count, image quality (sharpness, lighting, size),
    and checks if the face already belongs to an existing enrolled person.
    """
    try:
        contents = await file.read()
        image_rgb = _read_image(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")

    face_locations = detector.detect_faces(image_rgb, upsample=1)
    
    if len(face_locations) == 0:
        return {
            "valid": False,
            "error_type": "NO_FACE",
            "message": "No face detected in the photo. Please use a clear, front-facing photo.",
            "quality": None,
            "duplicate_warning": None
        }
        
    if len(face_locations) > 1:
        return {
            "valid": False,
            "error_type": "MULTIPLE_FACES",
            "message": f"Found {len(face_locations)} faces. Enrollment photos must contain exactly one face.",
            "quality": None,
            "duplicate_warning": None
        }

    loc = face_locations[0]
    top, right, bottom, left = loc
    face_crop = image_rgb[top:bottom, left:right]
    quality = validate_face_quality(face_crop, loc)

    if not quality["is_valid"]:
        return {
            "valid": False,
            "error_type": "POOR_QUALITY",
            "message": "Image quality is too low for reliable biometrics: " + ", ".join(quality["warnings"]),
            "quality": quality,
            "duplicate_warning": None
        }

    # Generate 128D embedding to test for duplicate
    vec = embedder.compute_embedding(image_rgb, known_face_location=loc, jitters=2)
    duplicate_info = None
    
    if vec is not None:
        known_items = get_all_active_embeddings()
        system_settings = get_all_settings()
        dup_match = matcher.check_duplicate(
            vec, 
            known_items, 
            threshold_dup=system_settings.get("threshold_duplicate_warn")
        )
        if dup_match:
            duplicate_info = dup_match

    return {
        "valid": True,
        "message": "Face photo validated successfully.",
        "quality": quality,
        "duplicate_warning": duplicate_info
    }

@router.post("")
async def enroll_person(
    full_name: str = Form(...),
    dob_or_age: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    custom_fields: Optional[str] = Form("{}"),
    force_duplicate: bool = Form(False),
    photos: List[UploadFile] = File(...)
):
    """
    Enrolls a new person into the database with one or multiple photos.
    Validates faces, generates embeddings, checks duplicates, and stores data locally.
    """
    if not full_name or not full_name.strip():
        raise HTTPException(status_code=400, detail="Full name is required.")
    
    if not photos or len(photos) == 0:
        raise HTTPException(status_code=400, detail="At least one facial photograph is required.")

    try:
        parsed_custom = json.loads(custom_fields or "{}")
    except Exception:
        parsed_custom = {}

    processed_vectors = []
    saved_photo_paths = []
    primary_profile_photo_path = None
    known_items = get_all_active_embeddings()
    system_settings = get_all_settings()

    for idx, photo_file in enumerate(photos):
        contents = await photo_file.read()
        try:
            image_rgb = _read_image(contents)
        except Exception:
            continue

        face_locations = detector.detect_faces(image_rgb, upsample=1)
        if len(face_locations) != 1:
            # Skip invalid multi-face or no-face photos
            continue
            
        loc = face_locations[0]
        face_crop = image_rgb[loc[0]:loc[2], loc[3]:loc[1]]
        quality = validate_face_quality(face_crop, loc)
        
        if not quality["is_valid"]:
            continue

        vec = embedder.compute_embedding(image_rgb, known_face_location=loc, jitters=2)
        if vec is None:
            continue

        # Check duplicate on first valid vector unless force_duplicate is set
        if idx == 0 and not force_duplicate:
            dup_match = matcher.check_duplicate(
                vec, 
                known_items, 
                threshold_dup=system_settings.get("threshold_duplicate_warn")
            )
            if dup_match:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "DUPLICATE_FACE_DETECTED",
                        "message": f"This face matches existing profile '{dup_match['full_name']}' (ID: {dup_match['person_id']}) with {dup_match['similarity']}% similarity.",
                        "matched_person": dup_match
                    }
                )

        # Align and save face image to disk
        aligned_face = detector.align_and_crop_face(image_rgb, loc, target_size=(240, 240))
        img_id = uuid.uuid4().hex[:8]
        filename = f"face_{img_id}.jpg"
        save_path = PHOTOS_DIR / filename
        
        Image.fromarray(aligned_face).save(save_path, format="JPEG", quality=92)
        rel_path = f"photos/{filename}"
        
        if primary_profile_photo_path is None:
            primary_profile_photo_path = rel_path
            
        saved_photo_paths.append((rel_path, compute_image_hash(contents), vec))
        processed_vectors.append(vec)

    if not processed_vectors:
        raise HTTPException(
            status_code=400,
            detail="None of the uploaded photos contained a single clear, usable face."
        )

    # 1. Create person profile
    person_id = create_person(
        full_name=full_name.strip(),
        dob_or_age=dob_or_age,
        gender=gender,
        notes=notes,
        custom_fields=parsed_custom,
        profile_photo_path=primary_profile_photo_path
    )

    # 2. Store individual embeddings
    for rel_path, img_hash, vec in saved_photo_paths:
        add_embedding(
            person_id=person_id,
            vector=vec,
            photo_path=rel_path,
            photo_hash=img_hash,
            is_centroid=False
        )

    # 3. If multiple photos, compute & store aggregated centroid embedding
    if len(processed_vectors) > 1:
        centroid_vec = embedder.aggregate_embeddings(processed_vectors)
        add_embedding(
            person_id=person_id,
            vector=centroid_vec,
            photo_path=primary_profile_photo_path,
            is_centroid=True
        )

    return {
        "success": True,
        "person_id": person_id,
        "full_name": full_name,
        "photos_enrolled": len(processed_vectors),
        "profile_photo_path": primary_profile_photo_path,
        "message": f"Successfully enrolled {full_name} with unique ID {person_id}."
    }

class UpdatePersonPayload(BaseModel):
    full_name: Optional[str] = None
    dob_or_age: Optional[str] = None
    gender: Optional[str] = None
    notes: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None
    profile_photo_path: Optional[str] = None

@router.put("/{person_id}")
async def edit_person(person_id: str, payload: UpdatePersonPayload):
    """Updates personal details, custom fields, or profile photo of a person profile."""
    success = update_person(
        person_id=person_id,
        full_name=payload.full_name,
        dob_or_age=payload.dob_or_age,
        gender=payload.gender,
        notes=payload.notes,
        custom_fields=payload.custom_fields,
        profile_photo_path=payload.profile_photo_path
    )
    if not success:
        raise HTTPException(status_code=404, detail="Person profile not found.")
    
    updated_person = get_person(person_id)
    return {"success": True, "message": "Profile updated successfully.", "person": updated_person}

@router.post("/{person_id}/photos")
async def add_person_photos(
    person_id: str,
    photos: List[UploadFile] = File(...)
):
    """
    Adds one or more face photos to an existing person profile.
    Validates face quality, generates embeddings, saves aligned face image,
    and updates the person's aggregated centroid embedding.
    """
    person = get_person(person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person profile not found.")

    if not photos or len(photos) == 0:
        raise HTTPException(status_code=400, detail="No photos uploaded.")

    saved_count = 0
    added_photos = []

    for photo_file in photos:
        contents = await photo_file.read()
        try:
            image_rgb = _read_image(contents)
        except Exception:
            continue

        face_locations = detector.detect_faces(image_rgb, upsample=1)
        if len(face_locations) != 1:
            continue

        loc = face_locations[0]
        face_crop = image_rgb[loc[0]:loc[2], loc[3]:loc[1]]
        quality = validate_face_quality(face_crop, loc)
        if not quality["is_valid"]:
            continue

        vec = embedder.compute_embedding(image_rgb, known_face_location=loc, jitters=2)
        if vec is None:
            continue

        aligned_face = detector.align_and_crop_face(image_rgb, loc, target_size=(240, 240))
        img_id = uuid.uuid4().hex[:8]
        filename = f"face_{img_id}.jpg"
        save_path = PHOTOS_DIR / filename

        Image.fromarray(aligned_face).save(save_path, format="JPEG", quality=92)
        rel_path = f"photos/{filename}"

        emb_id = add_embedding(
            person_id=person_id,
            vector=vec,
            photo_path=rel_path,
            photo_hash=compute_image_hash(contents),
            is_centroid=False
        )
        saved_count += 1
        added_photos.append({"embedding_id": emb_id, "photo_path": rel_path})

    if saved_count == 0:
        raise HTTPException(
            status_code=400,
            detail="None of the uploaded photos contained a single clear, usable face."
        )

    # Recompute centroid embedding
    recompute_person_centroid(person_id)

    # If the person has no profile photo, set it to the first new photo
    if not person.get("profile_photo_path") and added_photos:
        update_person(person_id=person_id, profile_photo_path=added_photos[0]["photo_path"])

    updated_person = get_person(person_id)
    return {
        "success": True,
        "message": f"Successfully added {saved_count} biometric photo(s).",
        "photos_added": saved_count,
        "person": updated_person
    }

@router.delete("/{person_id}/photos/{embedding_id}")
async def remove_person_photo(person_id: str, embedding_id: int):
    """
    Removes a specific biometric sample photo for a person.
    Requires at least one photo sample to remain in the profile.
    """
    person = get_person(person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person profile not found.")
    
    deleted = delete_person_photo_embedding(person_id, embedding_id)
    if not deleted:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete this photo. Either the photo does not exist, or it is the only biometric sample for this profile."
        )
    
    updated_person = get_person(person_id)
    # If the deleted photo was the primary profile photo, update to another remaining photo
    if updated_person and updated_person.get("photos") and person.get("profile_photo_path"):
        remaining_paths = [p["photo_path"] for p in updated_person["photos"]]
        if person["profile_photo_path"] not in remaining_paths:
            update_person(person_id=person_id, profile_photo_path=remaining_paths[0])
            updated_person = get_person(person_id)

    return {"success": True, "message": "Photo sample removed successfully.", "person": updated_person}

@router.delete("/{person_id}")
async def remove_person(person_id: str):
    """Permanently removes person, biometric embeddings, and photo files."""
    success = delete_person(person_id)
    if not success:
        raise HTTPException(status_code=404, detail="Person profile not found.")
    return {"success": True, "message": f"Profile {person_id} and all biometric data permanently deleted."}
