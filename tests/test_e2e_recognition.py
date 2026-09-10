import io
import unittest
import numpy as np
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import init_db

class TestE2ERecognition(unittest.TestCase):

    def setUp(self):
        init_db()
        self.client = TestClient(app)

    def _create_synthetic_face_bytes(self, color=(120, 150, 180)):
        # Generate a 240x240 image with clear facial contrast
        img = Image.new("RGB", (240, 240), color=(240, 230, 220))
        draw = ImageDraw.Draw(img)
        # Face oval
        draw.ellipse([40, 30, 200, 210], fill=color)
        # Eyes
        draw.ellipse([70, 80, 95, 105], fill=(30, 30, 30))
        draw.ellipse([145, 80, 170, 105], fill=(30, 30, 30))
        # Pupils
        draw.ellipse([80, 90, 86, 96], fill=(255, 255, 255))
        draw.ellipse([155, 90, 161, 96], fill=(255, 255, 255))
        # Nose
        draw.polygon([(120, 105), (110, 140), (130, 140)], fill=(80, 80, 80))
        # Mouth
        draw.chord([80, 150, 160, 180], start=0, end=180, fill=(180, 50, 50))
        
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        return buf.getvalue()

    def test_complete_recognition_cycle(self):
        # 1. Check health & initial people list
        res = self.client.get("/api/people")
        self.assertEqual(res.status_code, 200)

        # 2. Get settings
        s_res = self.client.get("/api/settings")
        self.assertEqual(s_res.status_code, 200)
        self.assertIn("threshold_high_confidence", s_res.json())

        # 3. Test photo scan on an image
        face_bytes = self._create_synthetic_face_bytes()
        scan_res = self.client.post(
            "/api/scan/photo",
            files={"file": ("test_photo.jpg", face_bytes, "image/jpeg")},
            data={"log_event": "true"}
        )
        self.assertEqual(scan_res.status_code, 200)
        scan_data = scan_res.json()
        self.assertIn("faces_detected", scan_data)

        # 4. Check history was logged
        h_res = self.client.get("/api/history")
        self.assertEqual(h_res.status_code, 200)
        self.assertIn("events", h_res.json())

        # 5. Check backup zip generation
        b_res = self.client.get("/api/settings/backup")
        self.assertEqual(b_res.status_code, 200)
        self.assertEqual(b_res.headers["content-type"], "application/zip")

if __name__ == "__main__":
    unittest.main()
