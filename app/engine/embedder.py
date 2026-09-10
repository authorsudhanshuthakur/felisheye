import numpy as np
import face_recognition
from typing import List, Optional, Tuple, Union

class FaceEmbedder:
    def __init__(self, num_jitters: int = 1):
        """
        num_jitters: How many times to re-sample the face when calculating encoding.
        Higher is more accurate (e.g., 2 or 5 for enrollment, 1 for live scanning).
        """
        self.num_jitters = num_jitters

    def compute_embedding(
        self, 
        image_rgb: np.ndarray, 
        known_face_location: Optional[Tuple[int, int, int, int]] = None,
        jitters: Optional[int] = None
    ) -> Optional[np.ndarray]:
        """
        Extracts a 128-dimensional deep metric embedding from the face.
        Returns a normalized numpy array of float32, or None if no face found.
        """
        locations = [known_face_location] if known_face_location is not None else None
        num_jit = jitters if jitters is not None else self.num_jitters
        
        try:
            encodings = face_recognition.face_encodings(
                image_rgb, 
                known_face_locations=locations, 
                num_jitters=num_jit,
                model="large"
            )
            if encodings and len(encodings) > 0:
                vector = np.array(encodings[0], dtype=np.float32)
                # Normalize vector to unit length
                norm = np.linalg.norm(vector)
                if norm > 0:
                    vector = vector / norm
                return vector
        except Exception as e:
            print(f"[Embedder Error] Could not compute encoding: {e}")
            
        return None

    def compute_batch_embeddings(
        self,
        image_rgb: np.ndarray,
        face_locations: List[Tuple[int, int, int, int]]
    ) -> List[np.ndarray]:
        """
        Extracts embeddings for multiple detected faces in a single photograph.
        """
        if not face_locations:
            return []
        try:
            encodings = face_recognition.face_encodings(
                image_rgb,
                known_face_locations=face_locations,
                num_jitters=1,
                model="large"
            )
            normalized = []
            for enc in encodings:
                vec = np.array(enc, dtype=np.float32)
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                normalized.append(vec)
            return normalized
        except Exception as e:
            print(f"[Embedder Error] Batch encoding failed: {e}")
            return []

    def aggregate_embeddings(self, vectors: List[np.ndarray]) -> np.ndarray:
        """
        Aggregates multiple face embeddings (from different photos of the same person)
        into a single optimal centroid vector representation.
        """
        if not vectors:
            raise ValueError("No embeddings provided for aggregation")
        
        arr = np.array(vectors, dtype=np.float32)
        mean_vec = np.mean(arr, axis=0)
        norm = np.linalg.norm(mean_vec)
        if norm > 0:
            mean_vec = mean_vec / norm
        return mean_vec

embedder = FaceEmbedder(num_jitters=1)
