import cv2
import numpy as np
import face_recognition
from typing import List, Tuple, Dict, Any, Optional

class FaceDetector:
    def __init__(self, model: str = "hog"):
        """
        model: 'hog' (fast, CPU-friendly) or 'cnn' (GPU/heavy CPU)
        """
        self.model = model
        self._cascade = None

    def _get_cascade(self):
        if self._cascade is None:
            self._cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
        return self._cascade

    def detect_faces(
        self, 
        image_rgb: np.ndarray, 
        upsample: int = 1
    ) -> List[Tuple[int, int, int, int]]:
        """
        Detects face locations in RGB image.
        Returns list of (top, right, bottom, left) bounding boxes.
        """
        try:
            locations = face_recognition.face_locations(
                image_rgb, 
                number_of_times_to_upsample=upsample, 
                model=self.model
            )
            if locations:
                return locations
        except Exception as e:
            print(f"[Detector Warning] face_recognition failed: {e}")
            
        # Fallback to OpenCV Haar Cascade if HOG fails or finds nothing
        try:
            gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
            cascade = self._get_cascade()
            faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
            locations = []
            for (x, y, w, h) in faces:
                locations.append((y, x + w, y + h, x))
            return locations
        except Exception as e:
            print(f"[Detector Error] Cascade fallback failed: {e}")
            return []

    def get_landmarks(
        self, 
        image_rgb: np.ndarray, 
        face_locations: Optional[List[Tuple[int, int, int, int]]] = None
    ) -> List[Dict[str, List[Tuple[int, int]]]]:
        """
        Returns 68 facial landmarks per face.
        """
        try:
            return face_recognition.face_landmarks(image_rgb, face_locations)
        except Exception as e:
            print(f"[Landmark Warning] Could not extract landmarks: {e}")
            return []

    def align_and_crop_face(
        self, 
        image_rgb: np.ndarray, 
        bbox: Tuple[int, int, int, int], 
        landmarks: Optional[Dict[str, List[Tuple[int, int]]]] = None,
        target_size: Tuple[int, int] = (224, 224)
    ) -> np.ndarray:
        """
        Crops and aligns face so the eyes are horizontal.
        """
        top, right, bottom, left = bbox
        h, w, _ = image_rgb.shape
        
        # Add slight margin (15%) around face
        pad_y = int((bottom - top) * 0.15)
        pad_x = int((right - left) * 0.15)
        
        y1 = max(0, top - pad_y)
        y2 = min(h, bottom + pad_y)
        x1 = max(0, left - pad_x)
        x2 = min(w, right + pad_x)
        
        cropped = image_rgb[y1:y2, x1:x2]
        if cropped.size == 0:
            return np.zeros((target_size[1], target_size[0], 3), dtype=np.uint8)
            
        # If eye landmarks are available, compute rotation angle
        if landmarks and 'left_eye' in landmarks and 'right_eye' in landmarks:
            left_eye = np.mean(landmarks['left_eye'], axis=0)
            right_eye = np.mean(landmarks['right_eye'], axis=0)
            
            d_y = right_eye[1] - left_eye[1]
            d_x = right_eye[0] - left_eye[0]
            angle = np.degrees(np.arctan2(d_y, d_x))
            
            # Rotate if tilt is noticeable (> 3 degrees and < 45 degrees)
            if 3.0 < abs(angle) < 45.0:
                center = (cropped.shape[1] // 2, cropped.shape[0] // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                cropped = cv2.warpAffine(
                    cropped, M, (cropped.shape[1], cropped.shape[0]), 
                    flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
                )
                
        aligned_resized = cv2.resize(cropped, target_size, interpolation=cv2.INTER_AREA)
        return aligned_resized

detector = FaceDetector(model="hog")
