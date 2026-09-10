import cv2
import numpy as np
from typing import Dict, Any, Tuple
from app.core.config import settings

def calculate_sharpness(image: np.ndarray) -> float:
    """
    Computes sharpness using the variance of the Laplacian.
    Higher values indicate a sharper, clearer image.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    variance = float(lap.var())
    return variance

def calculate_brightness_contrast(image: np.ndarray) -> Tuple[float, float]:
    """
    Calculates mean brightness (0-255) and standard deviation contrast.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    mean_val = float(np.mean(gray))
    std_val = float(np.std(gray))
    return mean_val, std_val

def validate_face_quality(
    face_crop: np.ndarray, 
    bbox: Tuple[int, int, int, int]
) -> Dict[str, Any]:
    """
    Evaluates face crop quality: size, sharpness, lighting.
    Returns validation verdict and detailed quality metrics.
    """
    top, right, bottom, left = bbox
    width = right - left
    height = bottom - top
    
    if width <= 0 or height <= 0 or face_crop.size == 0:
        return {
            "is_valid": False,
            "reason": "Invalid or zero-sized face bounding box",
            "sharpness": 0.0,
            "brightness": 0.0,
            "contrast": 0.0,
            "size": (width, height),
            "warnings": ["Face region could not be extracted"]
        }
    
    sharpness = calculate_sharpness(face_crop)
    brightness, contrast = calculate_brightness_contrast(face_crop)
    
    warnings = []
    is_valid = True
    
    if width < settings.MIN_FACE_SIZE or height < settings.MIN_FACE_SIZE:
        warnings.append(f"Face is too small ({width}x{height}px). Move closer to the camera.")
        is_valid = False
        
    if sharpness < settings.MIN_SHARPNESS:
        warnings.append(f"Image appears blurry (sharpness score: {sharpness:.1f} < {settings.MIN_SHARPNESS}).")
        # For enrollment this is strict, for live scan it gives visual warning
        
    if brightness < settings.MIN_BRIGHTNESS:
        warnings.append(f"Lighting is too dark (brightness: {brightness:.1f}). Ensure front lighting.")
    elif brightness > settings.MAX_BRIGHTNESS:
        warnings.append(f"Lighting is overexposed (brightness: {brightness:.1f}). Reduce glare.")
        
    if contrast < 15.0:
        warnings.append("Low contrast detected across facial features.")
        
    return {
        "is_valid": is_valid and (sharpness >= 25.0) and (brightness >= 20.0),
        "sharpness": round(sharpness, 2),
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "size": (width, height),
        "warnings": warnings,
        "quality_score": round(min(1.0, (sharpness / 200.0) * 0.5 + (contrast / 60.0) * 0.3 + (1.0 - abs(brightness - 128) / 128) * 0.2), 2)
    }
