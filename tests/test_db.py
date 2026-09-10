import unittest
import numpy as np
from app.db.database import (
    init_db, create_person, get_person, update_person, delete_person,
    get_all_people, add_embedding, get_all_active_embeddings,
    log_recognition_event, get_history, clear_history,
    get_all_settings, update_setting, export_backup_zip
)

class TestFelisEyeDatabase(unittest.TestCase):

    def setUp(self):
        init_db()

    def test_person_crud_and_custom_fields(self):
        # Create
        pid = create_person(
            full_name="Sarah Connor",
            dob_or_age="34",
            gender="Female",
            notes="Authorized system admin",
            custom_fields={"Department": "Security", "AccessLevel": "Tier-5"}
        )
        self.assertTrue(pid.startswith("FE-"))

        # Retrieve
        person = get_person(pid)
        self.assertIsNotNone(person)
        self.assertEqual(person["full_name"], "Sarah Connor")
        self.assertEqual(person["custom_fields"]["Department"], "Security")

        # Update
        update_person(pid, full_name="Sarah Connor Reese", notes="Updated notes")
        updated = get_person(pid)
        self.assertEqual(updated["full_name"], "Sarah Connor Reese")
        self.assertEqual(updated["notes"], "Updated notes")

        # List & Search
        results, total = get_all_people(search_query="Sarah")
        self.assertGreaterEqual(total, 1)
        self.assertTrue(any(p["id"] == pid for p in results))

        # Add Embedding
        sample_vec = np.random.randn(128).astype(np.float32)
        sample_vec /= np.linalg.norm(sample_vec)
        emb_id = add_embedding(pid, sample_vec, photo_path="photos/test_sarah.jpg")
        self.assertGreater(emb_id, 0)

        # Retrieve active embeddings
        active_items = get_all_active_embeddings()
        self.assertTrue(any(it["person_id"] == pid for it in active_items))

        # Delete
        del_success = delete_person(pid)
        self.assertTrue(del_success)
        self.assertIsNone(get_person(pid))

    def test_recognition_history(self):
        clear_history()
        hid = log_recognition_event(
            result_status="HIGH_CONFIDENCE",
            matched_person_id="FE-2026-TEST",
            matched_person_name="Test Person",
            similarity_score=94.5,
            distance=0.28,
            source="Live Camera"
        )
        self.assertGreater(hid, 0)

        events, total = get_history()
        self.assertGreaterEqual(total, 1)
        self.assertEqual(events[0]["result_status"], "HIGH_CONFIDENCE")

        # Clear
        cleared = clear_history()
        self.assertGreaterEqual(cleared, 1)
        events_after, total_after = get_history()
        self.assertEqual(total_after, 0)

    def test_settings_store(self):
        update_setting("test_custom_key", 42.5)
        s = get_all_settings()
        self.assertEqual(s.get("test_custom_key"), 42.5)

    def test_backup_zip_export(self):
        zip_path = export_backup_zip()
        self.assertTrue(zip_path.exists())
        self.assertGreater(zip_path.stat().st_size, 0)

if __name__ == "__main__":
    unittest.main()
