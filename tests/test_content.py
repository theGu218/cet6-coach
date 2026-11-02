"""内容完整性：词库、真题、解析、作文/翻译题库。"""
import json
import unittest
from pathlib import Path

import content

ROOT = Path(__file__).resolve().parent.parent


class ContentTests(unittest.TestCase):
    def test_vocabulary_layers_and_fields(self):
        words = content.vocabulary()
        self.assertGreaterEqual(len(words), 2000)
        self.assertEqual(len({word["word"].lower() for word in words}), len(words))
        tiers = {word.get("tier") for word in words}
        self.assertTrue({"高频核心", "基础回顾", "六级拓展"} <= tiers)
        for word in words[:200]:
            self.assertTrue(word["word"] and word["meaning"] and word["short_meaning"])

    def test_reading_exams_integrity(self):
        exams = content.reading()
        self.assertGreaterEqual(len(exams), 18)
        for exam in exams:
            self.assertTrue(exam["id"])
            self.assertTrue(exam["label"])
            cloze = exam["cloze"]
            self.assertEqual(len(cloze["wordbank"]), 15)
            self.assertEqual(len({entry["letter"] for entry in cloze["wordbank"]}), 15)
            self.assertEqual(len(cloze["blanks"]), 10)
            for blank in cloze["blanks"]:
                self.assertIn(f"{{{blank['num']}}}", cloze["passage"])
                self.assertTrue(blank["answer"])
            matching = exam["matching"]
            labels = {paragraph["label"] for paragraph in matching["paragraphs"]}
            self.assertEqual(len(matching["statements"]), 10)
            if matching.get("complete", True):
                for statement in matching["statements"]:
                    self.assertIn(statement["answer"], labels)
            else:
                self.assertTrue(matching.get("issue"), "不完整的题组必须写明原因")
            self.assertEqual(len(exam["careful"]), 2)
            for passage in exam["careful"]:
                self.assertEqual(len(passage["questions"]), 5)
                for question in passage["questions"]:
                    self.assertEqual(len(question["options"]), 4)
                    self.assertIn(question["answer"], ("A", "B", "C", "D"))

    def test_scraped_exams_have_complete_sections(self):
        exams = {exam["id"]: exam for exam in content.reading()}
        for exam_id in ("2024-06-1", "2024-12-3", "2025-06-2", "2025-12-3"):
            self.assertIn(exam_id, exams)
            exam = exams[exam_id]
            self.assertEqual(len(exam["cloze"]["blanks"]), 10)
            self.assertTrue(all(blank["answer"] for blank in exam["cloze"]["blanks"]))
            self.assertEqual(len(exam["matching"]["statements"]), 10)
            labels = {paragraph["label"] for paragraph in exam["matching"]["paragraphs"]}
            for statement in exam["matching"]["statements"]:
                self.assertIn(statement["answer"], labels)
            self.assertEqual(len(exam["careful"]), 2)
            for passage in exam["careful"]:
                self.assertEqual(len(passage["questions"]), 5)
                self.assertGreaterEqual(len(passage["paragraphs"]), 4)

    def test_analyses_are_structurally_complete_and_quote_original(self):
        folder = ROOT / "content" / "analyses"
        files = sorted(folder.glob("*.json")) if folder.exists() else []
        self.assertTrue(files, "至少应有一套真题解析")
        exams = {exam["id"]: exam for exam in content.reading()}
        for path in files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            exam = exams.get(payload["exam"])
            self.assertIsNotNone(exam, f"{path.name} 对应的真题不存在")
            self.assertEqual(len(payload["cloze"]["blanks"]), 10)
            self.assertEqual(len(payload["matching"]["statements"]), 10)
            total = sum(len(passage["questions"]) for passage in payload["careful"].values())
            self.assertEqual(total, 10)
            passage_text = exam["cloze"]["passage"]
            for blank in payload["cloze"]["blanks"].values():
                self.assertTrue(blank["explanation"])
                self.assertIn(blank["evidence"][:40], passage_text.replace("\n", " "))
            for passage in exam["careful"]:
                extra = payload["careful"][passage["id"]]
                body = " ".join(passage["paragraphs"])
                for question in extra["questions"].values():
                    self.assertTrue(question["explanation"])
                    quote = question["evidence_quote"].replace("\n", " ")
                    self.assertIn(quote[:40], body.replace("\n", " "), "原文定位必须是逐字片段")
                    self.assertTrue(question["distractors"])
            for statement in payload["matching"]["statements"].values():
                self.assertTrue(statement["explanation"])

    def test_answer_fixes_are_recorded(self):
        exams = content.reading()
        corrected = [question for exam in exams for passage in exam["careful"]
                     for question in passage["questions"] if question.get("original_answer")]
        self.assertTrue(corrected, "答案文件已知有误，应留下修正记录")
        for exam in exams:
            for passage in exam["careful"]:
                for question in passage["questions"]:
                    if question.get("original_answer"):
                        self.assertNotEqual(question["original_answer"], question["answer"])
                        self.assertIn(question["answer"], ("A", "B", "C", "D"))

    def test_writing_and_translation_tasks(self):
        writing = content.writing()
        translation = content.translation()
        self.assertGreaterEqual(len(writing), 20)
        self.assertGreaterEqual(len(translation), 50)
        for item in writing[:40]:
            self.assertTrue(item["id"] and item["label"])
            self.assertTrue(item["directions"])
            self.assertGreaterEqual(item["minutes"], 30)
        for item in translation[:40]:
            self.assertTrue(item["chinese"])
            self.assertGreaterEqual(len(item["chinese"]), 40)


if __name__ == "__main__":
    unittest.main()
