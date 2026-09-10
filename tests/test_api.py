import unittest
from fastapi.testclient import TestClient
from app.main import app

class TestFelisEyeAPI(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_settings_endpoints(self):
        res = self.client.get("/api/settings")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("threshold_high_confidence", data)

        # Update settings
        update_res = self.client.put("/api/settings", json={
            "threshold_high_confidence": 0.40
        })
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.json()["settings"]["threshold_high_confidence"], 0.40)

    def test_people_list_endpoint(self):
        res = self.client.get("/api/people")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("people", data)
        self.assertIn("total", data)

    def test_history_endpoints(self):
        res = self.client.get("/api/history")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("events", data)

    def test_stats_endpoint(self):
        res = self.client.get("/api/settings/stats")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("people_count", data)
        self.assertIn("embeddings_count", data)

    def test_person_update_and_detail_endpoint(self):
        from app.db.database import create_person, delete_person
        pid = create_person(
            full_name="Test Subject Alpha",
            dob_or_age="28",
            gender="Female",
            notes="Initial notes",
            custom_fields={"Role": "Tester", "Dept": "QA"}
        )
        try:
            # Check detail endpoint returns photos and custom fields
            get_res = self.client.get(f"/api/people/{pid}")
            self.assertEqual(get_res.status_code, 200)
            person_data = get_res.json()
            self.assertEqual(person_data["full_name"], "Test Subject Alpha")
            self.assertIn("photos", person_data)
            self.assertEqual(person_data["custom_fields"].get("Role"), "Tester")

            # Update person via PUT
            update_res = self.client.put(f"/api/people/{pid}", json={
                "full_name": "Test Subject Beta",
                "dob_or_age": "29",
                "gender": "Female",
                "notes": "Updated notes",
                "custom_fields": {"Role": "Lead", "Dept": "Security", "Clearance": "Top Secret"}
            })
            self.assertEqual(update_res.status_code, 200)
            updated_info = update_res.json()["person"]
            self.assertEqual(updated_info["full_name"], "Test Subject Beta")
            self.assertEqual(updated_info["notes"], "Updated notes")
            self.assertEqual(updated_info["custom_fields"]["Clearance"], "Top Secret")

            # Verify persisted with GET
            verify_res = self.client.get(f"/api/people/{pid}")
            self.assertEqual(verify_res.status_code, 200)
            self.assertEqual(verify_res.json()["full_name"], "Test Subject Beta")
            self.assertEqual(verify_res.json()["custom_fields"]["Clearance"], "Top Secret")
        finally:
            delete_person(pid)

if __name__ == "__main__":
    unittest.main()
