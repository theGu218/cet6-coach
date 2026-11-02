"""学习记录持久化：schema 迁移、备份、重置。"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import temp_dir
from unittest.mock import patch

from repositories.store import SCHEMA, ProgressStore


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = temp_dir()
        self.path = Path(self.tmp.name) / "progress.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_defaults_and_roundtrip(self):
        store = ProgressStore(self.path)
        self.assertEqual(store.data["schema"], SCHEMA)
        store.word_state("abandon")
        state = store.word_state("abandon")
        state["seen"] = 2
        store.set_word_state("abandon", state)
        store.save()
        again = ProgressStore(self.path)
        self.assertEqual(again.word_state("abandon")["seen"], 2)

    def test_legacy_v2_migration_keeps_data_and_backup(self):
        legacy = {
            "version": 2,
            "settings": {"daily_words": 30, "user_name": "小明"},
            "word_status": {"abandon": {"level": 3, "seen": 4, "correct": 3, "wrong_count": 1,
                                        "needs_review": True}},
            "starred_words": ["abandon"],
            "reading_error_tags": {"q1": "定位错误"},
            "writing": {"w1": {"text": "draft", "updated": "2026-11-01T10:00:00"}},
            "wrong_questions": {"q1": {"prompt": "x"}},
            "activity": {"2026-11-01": {"minutes": 20}},
        }
        self.path.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
        store = ProgressStore(self.path)
        self.assertEqual(store.migrated_from, 2)
        self.assertEqual(store.data["schema"], SCHEMA)
        self.assertEqual(store.settings["daily_words"], 30)
        self.assertEqual(store.settings["user_name"], "小明")
        state = store.word_state("abandon")
        self.assertEqual(state["seen"], 4)
        self.assertTrue(state["needs_review"])
        self.assertGreaterEqual(state["stage"], 3)
        self.assertIn("abandon", store.data["starred"])
        self.assertEqual(store.data["error_tags"]["q1"], "定位错误")
        backup = self.path.with_name("progress_v2_backup.json")
        self.assertTrue(backup.exists())

    def test_activity_streak_and_stats(self):
        store = ProgressStore(self.path)
        store.touch("words", 5)
        store.touch("minutes", 30)
        stats = store.stats()
        self.assertEqual(stats["words_today"], 5)
        self.assertEqual(stats["minutes_today"], 30)
        self.assertEqual(stats["streak"], 1)
        state = store.word_state("alpha")
        state.update({"seen": 2, "status": "已掌握"})
        store.set_word_state("alpha", state)
        self.assertEqual(store.stats()["mastered"], 1)

    def test_reset_keeps_imported_content(self):
        store = ProgressStore(self.path)
        store.data["imported_words"] = [{"word": "custom", "meaning": "自定义"}]
        store.data["imported_exams"] = [{"id": "imported-1"}]
        store.touch("words", 9)
        store.reset(keep_imported=True)
        self.assertEqual(store.activity_today()["words"], 0)
        self.assertEqual(len(store.data["imported_words"]), 1)
        self.assertEqual(len(store.data["imported_exams"]), 1)

    def test_broken_file_is_kept_aside(self):
        self.path.write_text("{not json", encoding="utf-8")
        store = ProgressStore(self.path)
        self.assertEqual(store.data["schema"], SCHEMA)
        broken = list(self.path.parent.glob("progress_broken_*.json"))
        self.assertTrue(broken)

    def test_backup_export_and_import(self):
        store = ProgressStore(self.path)
        store.touch("questions", 3)
        target = Path(self.tmp.name) / "backup.json"
        store.export_backup(target)
        other_path = Path(self.tmp.name) / "other.json"
        other = ProgressStore(other_path)
        other.import_backup(target)
        self.assertEqual(other.activity_today()["questions"], 3)


if __name__ == "__main__":
    unittest.main()
