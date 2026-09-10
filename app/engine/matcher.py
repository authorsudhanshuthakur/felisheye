import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from app.core.config import settings

class FaceMatcher:
    def __init__(self):
        pass

    @staticmethod
    def compute_distance(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Computes Euclidean distance between two 128D unit vectors.
        Range is [0.0, 2.0]. Lower means more identical.
        """
        return float(np.linalg.norm(vec1 - vec2))

    @staticmethod
    def distance_to_similarity(distance: float) -> float:
        """
        Converts Euclidean distance to a safe, interpretable 0-100% similarity score.
        For unit vectors, d=0.0 -> 100%, d=0.40 -> ~80%, d=0.60 -> ~60%, d>=1.0 -> 0%.
        """
        # Linear mapped similarity for standard face metrics
        sim = max(0.0, min(100.0, (1.0 - (distance / 1.0)) * 100.0))
        return round(sim, 1)

    def classify_distance(
        self, 
        distance: float,
        threshold_high: Optional[float] = None,
        threshold_match: Optional[float] = None,
        threshold_low: Optional[float] = None
    ) -> Tuple[str, str]:
        """
        Categorizes distance into 4 strict confidence tiers:
        Returns (tier_enum, human_label)
        """
        th_high = threshold_high if threshold_high is not None else settings.THRESHOLD_HIGH_CONFIDENCE
        th_match = threshold_match if threshold_match is not None else settings.THRESHOLD_POSSIBLE_MATCH
        th_low = threshold_low if threshold_low is not None else settings.THRESHOLD_LOW_CONFIDENCE

        if distance <= th_high:
            return "HIGH_CONFIDENCE", "High Confidence"
        elif distance <= th_match:
            return "POSSIBLE_MATCH", "Possible Match"
        elif distance <= th_low:
            return "LOW_CONFIDENCE", "Low Confidence"
        else:
            return "UNKNOWN", "Unknown Person"

    def match_against_known(
        self,
        query_vector: np.ndarray,
        known_items: List[Dict[str, Any]],  # List of {'person_id': ..., 'name': ..., 'vector': np.ndarray, 'profile_photo_path': ..., ...}
        threshold_high: Optional[float] = None,
        threshold_match: Optional[float] = None,
        threshold_low: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Finds the closest match from known enrolled profiles.
        """
        if not known_items or query_vector is None:
            return {
                "matched": False,
                "tier": "UNKNOWN",
                "tier_label": "Unknown Person",
                "similarity": 0.0,
                "distance": 2.0,
                "person": None,
                "top_candidates": []
            }

        candidates = []
        for item in known_items:
            known_vec = item.get("vector")
            if known_vec is None or len(known_vec) != 128:
                continue
            dist = self.compute_distance(query_vector, known_vec)
            sim = self.distance_to_similarity(dist)
            tier, tier_label = self.classify_distance(
                dist, threshold_high, threshold_match, threshold_low
            )
            candidates.append({
                "person_id": item.get("person_id"),
                "full_name": item.get("full_name"),
                "distance": round(dist, 4),
                "similarity": sim,
                "tier": tier,
                "tier_label": tier_label,
                "profile_photo_path": item.get("profile_photo_path"),
                "custom_fields": item.get("custom_fields", {}),
                "notes": item.get("notes", "")
            })

        # Sort candidates by smallest distance (highest similarity)
        candidates.sort(key=lambda x: x["distance"])

        if not candidates:
            return {
                "matched": False,
                "tier": "UNKNOWN",
                "tier_label": "Unknown Person",
                "similarity": 0.0,
                "distance": 2.0,
                "person": None,
                "top_candidates": []
            }

        best = candidates[0]
        # Considered a valid match if High Confidence or Possible Match
        is_matched = best["tier"] in ("HIGH_CONFIDENCE", "POSSIBLE_MATCH")

        return {
            "matched": is_matched,
            "tier": best["tier"],
            "tier_label": best["tier_label"],
            "similarity": best["similarity"],
            "distance": best["distance"],
            "person": {
                "id": best["person_id"],
                "full_name": best["full_name"],
                "profile_photo_path": best["profile_photo_path"],
                "custom_fields": best["custom_fields"],
                "notes": best["notes"]
            } if best["tier"] != "UNKNOWN" else None,
            "top_candidates": candidates[:5]
        }

    def check_duplicate(
        self,
        query_vector: np.ndarray,
        known_items: List[Dict[str, Any]],
        threshold_dup: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Checks if the face vector matches an existing profile closely enough
        to suggest a duplicate enrollment.
        """
        th_dup = threshold_dup if threshold_dup is not None else settings.THRESHOLD_DUPLICATE_WARN
        for item in known_items:
            known_vec = item.get("vector")
            if known_vec is None:
                continue
            dist = self.compute_distance(query_vector, known_vec)
            if dist <= th_dup:
                sim = self.distance_to_similarity(dist)
                return {
                    "is_duplicate": True,
                    "person_id": item.get("person_id"),
                    "full_name": item.get("full_name"),
                    "distance": round(dist, 4),
                    "similarity": sim,
                    "profile_photo_path": item.get("profile_photo_path")
                }
        return None

matcher = FaceMatcher()
