import unittest
import numpy as np
import cv2
from app.engine.quality import calculate_sharpness, calculate_brightness_contrast, validate_face_quality
from app.engine.liveness import analyze_frequency_texture, analyze_specular_reflection, evaluate_liveness
from app.engine.matcher import matcher
from app.core.security import encrypt_vector, decrypt_vector

class TestFelisEyeEngine(unittest.TestCase):

    def setUp(self):
        # Create a synthetic 150x150 test face image (with eyes and nose shapes)
        self.test_img = np.full((200, 200, 3), 180, dtype=np.uint8)
        # Draw eyes
        cv2.circle(self.test_img, (70, 80), 12, (50, 50, 50), -1)
        cv2.circle(self.test_img, (130, 80), 12, (50, 50, 50), -1)
        # Draw nose & mouth
        cv2.rectangle(self.test_img, (95, 95), (105, 120), (100, 100, 100), -1)
        cv2.rectangle(self.test_img, (70, 140), (130, 155), (80, 40, 40), -1)

    def test_quality_sharpness_and_lighting(self):
        sharpness = calculate_sharpness(self.test_img)
        self.assertGreater(sharpness, 0.0)
        
        brightness, contrast = calculate_brightness_contrast(self.test_img)
        self.assertGreater(brightness, 100.0)
        self.assertGreater(contrast, 5.0)

        quality = validate_face_quality(self.test_img, (20, 180, 180, 20))
        self.assertIn("sharpness", quality)
        self.assertIn("quality_score", quality)

    def test_liveness_heuristics(self):
        freq_score = analyze_frequency_texture(self.test_img)
        self.assertGreaterEqual(freq_score, 0.0)
        self.assertLessEqual(freq_score, 1.0)

        spec_score = analyze_specular_reflection(self.test_img)
        self.assertGreater(spec_score, 0.0)

        liveness_res = evaluate_liveness(self.test_img)
        self.assertIn("is_live", liveness_res)
        self.assertIn("liveness_score", liveness_res)

    def test_vector_security_encryption(self):
        # 128D unit vector
        raw_vec = np.random.randn(128).astype(np.float32)
        raw_vec /= np.linalg.norm(raw_vec)

        encrypted = encrypt_vector(raw_vec)
        self.assertIsInstance(encrypted, str)
        self.assertNotEqual(encrypted, "")

        decrypted = decrypt_vector(encrypted)
        self.assertEqual(len(decrypted), 128)
        np.testing.assert_allclose(raw_vec, decrypted, atol=1e-5)

    def test_matcher_confidence_tiers(self):
        # Match identical
        v1 = np.ones(128, dtype=np.float32)
        v1 /= np.linalg.norm(v1)
        
        dist_zero = matcher.compute_distance(v1, v1)
        self.assertAlmostEqual(dist_zero, 0.0, places=4)
        sim_100 = matcher.distance_to_similarity(dist_zero)
        self.assertEqual(sim_100, 100.0)

        tier, label = matcher.classify_distance(0.35)
        self.assertEqual(tier, "HIGH_CONFIDENCE")

        tier, label = matcher.classify_distance(0.48)
        self.assertEqual(tier, "POSSIBLE_MATCH")

        tier, label = matcher.classify_distance(0.58)
        self.assertEqual(tier, "LOW_CONFIDENCE")

        tier, label = matcher.classify_distance(0.85)
        self.assertEqual(tier, "UNKNOWN")

    def test_matcher_duplicate_check(self):
        v1 = np.random.randn(128).astype(np.float32)
        v1 /= np.linalg.norm(v1)

        known = [{
            "person_id": "FE-2026-TEST",
            "full_name": "Test Candidate",
            "vector": v1,
            "profile_photo_path": "photos/test.jpg"
        }]

        dup = matcher.check_duplicate(v1, known)
        self.assertIsNotNone(dup)
        self.assertTrue(dup["is_duplicate"])
        self.assertEqual(dup["person_id"], "FE-2026-TEST")

if __name__ == "__main__":
    unittest.main()
