import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from scipy.spatial import distance as dist
from app.core.config import settings

Tuple_Point = Tuple[int, int]

def _eye_aspect_ratio(eye_landmarks: List[Any]) -> float:
    """
    Computes Eye Aspect Ratio (EAR) based on 6 landmark points.
    EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
    """
    if len(eye_landmarks) < 6:
        return 0.3
    # Vertical distances
    a = np.linalg.norm(np.array(eye_landmarks[1]) - np.array(eye_landmarks[5]))
    b = np.linalg.norm(np.array(eye_landmarks[2]) - np.array(eye_landmarks[4]))
    # Horizontal distance
    c = np.linalg.norm(np.array(eye_landmarks[0]) - np.array(eye_landmarks[3]))
    if c == 0:
        return 0.3
    ear = (a + b) / (2.0 * c)
    return float(ear)

def analyze_frequency_texture(face_crop: np.ndarray) -> float:
    """
    Performs 2D Fast Fourier Transform (FFT) on grayscale face crop
    to analyze the energy distribution of high-frequency components vs low-frequency.
    Printed paper & digital screens often display anomalous high-frequency grid lines or flat low-frequency responses.
    """
    if face_crop.size == 0:
        return 0.0
    if len(face_crop.shape) == 3:
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = face_crop
        
    resized = cv2.resize(gray, (128, 128))
    f = np.fft.fft2(resized)
    fshift = np.fft.fftshift(f)
    magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1e-6)
    
    # Calculate energy in high frequency outer region vs central low frequency
    rows, cols = 128, 128
    crow, ccol = rows // 2, cols // 2
    r_inner = 20
    
    # Mask central low frequencies
    mask = np.ones((rows, cols), np.uint8)
    cv2.circle(mask, (ccol, crow), r_inner, 0, -1)
    
    high_freq_energy = np.mean(magnitude_spectrum[mask == 1])
    total_energy = np.mean(magnitude_spectrum)
    
    # Ratio of high-frequency texture
    ratio = high_freq_energy / (total_energy + 1e-6)
    # Natural live skin under normal conditions has ratio in ~0.8 to 1.3
    normalized_score = float(np.clip((ratio - 0.5) / 0.8, 0.0, 1.0))
    return normalized_score

def analyze_specular_reflection(face_crop: np.ndarray) -> float:
    """
    Checks for extreme flat reflection or digital screen back-lighting.
    """
    if face_crop.size == 0:
        return 0.5
    hsv = cv2.cvtColor(face_crop, cv2.COLOR_BGR2HSV)
    v = hsv[:, :, 2]
    # Check percentage of saturated pixels (>250)
    overexposed_ratio = np.sum(v > 248) / float(v.size)
    if overexposed_ratio > 0.25:  # Screen glare / severe flash
        return 0.3
    return 0.9

def evaluate_liveness(
    face_crop: np.ndarray,
    landmarks: Optional[Dict[str, List[Tuple_Point]]] = None
) -> Dict[str, Any]:
    """
    Modular on-device heuristic anti-spoofing analysis.
    Combines FFT frequency texture, specular check, and eye-aspect ratio when available.
    """
    if not settings.LIVENESS_ENABLED:
        return {
            "is_live": True,
            "liveness_score": 1.0,
            "status": "Disabled",
            "details": {"reason": "Anti-spoofing check disabled in settings"}
        }
        
    if face_crop.size == 0 or face_crop.shape[0] < 40 or face_crop.shape[1] < 40:
        return {
            "is_live": False,
            "liveness_score": 0.0,
            "status": "Insufficient Face Data",
            "details": {"reason": "Face region too small for texture analysis"}
        }
        
    freq_score = analyze_frequency_texture(face_crop)
    spec_score = analyze_specular_reflection(face_crop)
    
    ear_score = 0.8  # Default baseline
    if landmarks and 'left_eye' in landmarks and 'right_eye' in landmarks:
        left_ear = _eye_aspect_ratio(landmarks['left_eye'])
        right_ear = _eye_aspect_ratio(landmarks['right_eye'])
        avg_ear = (left_ear + right_ear) / 2.0
        # Normal open eyes have EAR between 0.18 and 0.40
        if 0.16 <= avg_ear <= 0.45:
            ear_score = 0.95
        elif avg_ear < 0.12:  # Closed or suspicious flat eye
            ear_score = 0.60
        else:
            ear_score = 0.75
            
    # Composite score
    composite = (freq_score * 0.50) + (spec_score * 0.25) + (ear_score * 0.25)
    composite = float(np.clip(composite, 0.0, 1.0))
    
    is_live = composite >= settings.LIVENESS_MIN_SCORE
    
    return {
        "is_live": is_live,
        "liveness_score": round(composite, 3),
        "status": "Real Face Verified" if is_live else "Suspicious / Potential Spoof",
        "details": {
            "frequency_score": round(freq_score, 3),
            "specular_score": round(spec_score, 3),
            "ear_score": round(ear_score, 3),
            "threshold": settings.LIVENESS_MIN_SCORE
        }
    }
