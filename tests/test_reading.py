"""真题阅读：判分、错题、错误原因统计、错题重练。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import temp_dir

import content
from repositories.store import ProgressStore
from services.reading_service import ReadingService


class ReadingServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exams = content.reading()
        assert cls.exams, "content/reading.json 为空"

    def setUp(self):
        self.tmp = temp_dir()
        self.store = ProgressStore(Path(self.tmp.name) / "progress.json")
        self.service = ReadingService(self.exams, self.store)
        self.exam = self.exams[0]

    def tearDown(self):
        self.tmp.cleanup()

    def test_grade_cloze_all_correct(self):
        answers = {str(blank["num"]): blank["answer"] for blank in self.exam["cloze"]["blanks"]}
        results = self.service.grade_cloze(self.exam["id"], answers)
        self.assertEqual(len(results), 10)
        self.assertTrue(all(item["correct"] for item in results))
        self.assertEqual(results[0]["word"], self.exam["cloze"]["blanks"][0]["word"])

    def test_grade_careful_marks_wrong_and_keeps_option_letters(self):
        passage = self.exam["careful"][0]
        answers = {}
        for index, question in enumerate(passage["questions"]):
            answers[str(question["num"])] = question["answer"] if index else (
                "A" if question["answer"] != "A" else "B")
        results = self.service.grade_careful(self.exam["id"], passage["id"], answers)
        self.assertEqual(len(results), 5)
        self.assertFalse(results[0]["correct"])
        self.assertTrue(all(item["correct"] for item in results[1:]))

    def test_record_updates_wrong_bank_and_sessions(self):
        passage = self.exam["careful"][0]
        question = passage["questions"][0]
        answers = {str(question["num"]): ("A" if question["answer"] != "A" else "B")}
        results = self.service.grade_careful(self.exam["id"], passage["id"], answers)
        self.service.record(self.exam["id"], "careful", results, 65, mode="learning", sub_id=passage["id"])
        self.assertEqual(len(self.service.wrong_bank()), 5)
        self.assertEqual(self.store.data["sessions"][-1]["category"], "仔细阅读")
        by_kind = self.service.accuracy_by_kind()
        self.assertTrue(by_kind["仔细阅读"][1] >= 5)

    def test_error_tags_count_in_reason_stats(self):
        results = self.service.grade_cloze(self.exam["id"], {})
        self.service.record(self.exam["id"], "cloze", results, 30)
        result = results[0]
        self.service.add_error_tag(result["key"], "词汇不懂")
        reasons = self.service.accuracy_by_reason()
        self.assertEqual(reasons["词汇不懂"], 1)
        self.assertTrue(all(item["answer"] for item in results))
        self.assertIn(result["key"], [item["question_id"] for item in self.service.wrong_bank()])

    def test_retry_queue_restores_question_text(self):
        blank = self.exam["cloze"]["blanks"][0]
        results = self.service.grade_cloze(self.exam["id"], {str(blank["num"]): "X"})
        self.service.record(self.exam["id"], "cloze", results[:1], 10)
        queue = self.service.retry_queue("cloze")
        self.assertTrue(queue)
        self.assertIn("answer", queue[0])
        self.assertEqual(queue[0]["answer"], blank["answer"])

    def test_recommend_skips_finished_exam(self):
        first = self.service.recommend()
        self.assertIsNotNone(first)
        for kind in ("cloze", "matching", "careful"):
            record = self.store.reading_record(first["id"])
            record[kind] = {"correct": 5, "total": 10}
            self.store.save()
        second = self.service.recommend()
        self.assertNotEqual(first["id"], second["id"])

    def test_status_reports_finished_kinds(self):
        record = self.store.reading_record(self.exam["id"])
        record["cloze"] = {"correct": 8, "total": 10}
        self.store.save()
        status = self.service.status(self.exam["id"])
        self.assertIn("cloze", status["done"])


if __name__ == "__main__":
    unittest.main()
