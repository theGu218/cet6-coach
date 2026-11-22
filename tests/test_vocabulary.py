"""词汇复习规则：队列优先级、阶段解锁、间隔复习、掌握判定。"""
import json
import random
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import temp_dir

from repositories.store import ProgressStore
from services.vocabulary_service import INTERVALS, VocabularyService

WORDS = [
    {"word": "abandon", "phonetic": "əˈbændən", "pos": "v.", "meaning": "放弃", "short_meaning": "放弃",
     "tier": "高频核心", "example": "They had to abandon the project.", "example_zh": "他们不得不放弃这个项目。"},
    {"word": "abolish", "pos": "v.", "meaning": "废除", "short_meaning": "废除", "tier": "高频核心",
     "example": "The law was abolished.", "example_zh": "那条法律被废除了。"},
    {"word": "abstract", "pos": "adj.", "meaning": "抽象的", "short_meaning": "抽象的", "tier": "六级拓展"},
    {"word": "absurd", "pos": "adj.", "meaning": "荒谬的", "short_meaning": "荒谬的", "tier": "六级拓展"},
    {"word": "abundant", "pos": "adj.", "meaning": "丰富的", "short_meaning": "丰富的", "tier": "基础回顾"},
    {"word": "abuse", "pos": "v.", "meaning": "滥用", "short_meaning": "滥用", "tier": "高频核心"},
]


class VocabularyServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = temp_dir()
        self.store = ProgressStore(Path(self.tmp.name) / "progress.json")
        self.service = VocabularyService(WORDS, self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def test_queue_order_wrong_then_due_then_new(self):
        wrong = self.store.word_state("abandon")
        wrong.update({"seen": 2, "needs_review": True, "next_review": date.today().isoformat()})
        self.store.set_word_state("abandon", wrong)
        due = self.store.word_state("abuse")
        due.update({"seen": 1, "next_review": date.today().isoformat()})
        self.store.set_word_state("abuse", due)
        queue = self.service.daily_queue()
        words = [item["word"] for item in queue]
        self.assertEqual(words[0], "abandon")
        self.assertEqual(words[1], "abuse")
        self.assertTrue(set(words[2:]))

    def test_stage_unlocks_question_modes(self):
        self.assertEqual(self.service.next_mode("absurd"), "en_zh")
        state = self.store.word_state("absurd")
        state["stage"] = 1
        self.store.set_word_state("absurd", state)
        self.assertEqual(self.service.next_mode("absurd"), "zh_en")
        state = self.store.word_state("abandon")
        state["stage"] = 2  # abandon 有例句 → 进入语境
        self.store.set_word_state("abandon", state)
        self.assertEqual(self.service.next_mode("abandon"), "context")

    def test_question_has_four_unique_options_and_matching_answer(self):
        question = self.service.make_question(WORDS[0], "en_zh")
        self.assertEqual(len(question["options"]), 4)
        self.assertEqual(len(set(question["options"])), 4)
        self.assertEqual(question["options"][question["answer"]], question["correct"])
        zh_en = self.service.make_question(WORDS[0], "zh_en")
        self.assertIn("abandon", zh_en["options"])
        self.assertEqual(zh_en["options"][zh_en["answer"]], "abandon")

    def test_context_question_blanks_the_word(self):
        question = self.service.make_question(WORDS[0], "context")
        self.assertNotIn("abandon", question["prompt"].lower())
        self.assertIn("______", question["prompt"])

    def test_interval_grows_on_correct_answers(self):
        for day_index in range(3):
            day = (date.today() + timedelta(days=day_index)).isoformat()
            self.service.record("abuse", "en_zh", True, "滥用", on_date=day)
        state = self.store.word_state("abuse")
        self.assertGreaterEqual(state["successful_reviews"], 3)
        # 第 3 次答对用第 3 档间隔（4 天），最后一次作答在 2 天后
        expected = (date.today() + timedelta(days=2 + INTERVALS[2])).isoformat()
        self.assertEqual(state["next_review"], expected)
        self.assertEqual(state["status"], "待复习")

    def test_mastery_needs_multiple_days_and_context(self):
        # 同一天连续答对：不能掌握
        for _ in range(5):
            self.service.record("abuse", "en_zh", True, "滥用")
        self.assertNotEqual(self.store.word_state("abuse")["status"], "已掌握")
        self.assertFalse(self.store.word_state("abuse")["context_passed"])

    def test_wrong_answer_enters_review_same_day_and_keeps_history(self):
        self.service.record("abstract", "zh_en", False, "abstract")
        state = self.store.word_state("abstract")
        self.assertTrue(state["needs_review"])
        self.assertEqual(state["next_review"], date.today().isoformat())
        self.assertEqual(state["wrong_count"], 1)
        self.assertIn("abstract", self.service.wrong_words()[0]["word"])
        self.assertIn("abstract", self.store.data["word_history"])

    def test_reduced_word_leaves_new_queue_but_stays_searchable(self):
        self.service.set_reduced("abundant", True)
        new_words = [item["word"] for item in self.service.new_words(10)]
        self.assertNotIn("abundant", new_words)
        found = [item for item in self.service.words if item["word"] == "abundant"]
        self.assertTrue(found)

    def test_new_words_follow_tier_order(self):
        words = [item["word"] for item in self.service.new_words(5)]
        tiers = [self.service.item(word)["tier"] for word in words]
        order = {"高频核心": 0, "基础回顾": 1, "六级拓展": 2}
        self.assertEqual(tiers, sorted(tiers, key=lambda t: order[t]))

    def test_intervals_are_configured_as_designed(self):
        self.assertEqual(INTERVALS[0], 1)
        self.assertIn(7, INTERVALS)
        self.assertIn(15, INTERVALS)

    def test_correct_answer_clears_wrong_marker(self):
        self.service.record("abandon", "en_zh", False, "放弃")
        self.assertTrue(self.store.word_state("abandon")["needs_review"])
        self.service.record("abandon", "en_zh", True, "放弃")
        state = self.store.word_state("abandon")
        self.assertFalse(state["needs_review"])       # 答对即退出错词队列
        self.assertEqual(state["wrong_count"], 1)      # 但历史错误次数保留
        self.assertNotIn("abandon", [item["word"] for item in self.service.wrong_words()])

    def test_wrong_words_sorted_by_latest_mistake(self):
        self.service.record("abuse", "en_zh", False, "x", on_date="2026-11-01")
        self.service.record("abandon", "en_zh", False, "x", on_date="2026-11-05")
        words = [item["word"] for item in self.service.wrong_words()]
        self.assertEqual(words[0], "abandon")          # 最近错的排最前
        self.assertEqual(words[1], "abuse")

    def test_daily_queue_caps_review_volume(self):
        words = [{"word": f"w{i}", "pos": "v.", "meaning": f"m{i}", "short_meaning": f"m{i}",
                  "tier": "高频核心"} for i in range(80)]
        store = ProgressStore(Path(self.tmp.name) / "cap.json")
        service = VocabularyService(words, store)
        for item in words:
            state = store.word_state(item["word"])
            state.update({"seen": 1, "next_review": "2026-01-01"})
            store.set_word_state(item["word"], state)
        store.settings["daily_review_limit"] = 60
        queue = service.daily_queue()
        self.assertEqual(len(queue), 60)               # 复习部分封顶，不再无上限叠加

    def test_new_words_are_shuffled_within_tier(self):
        first_words = set()
        for seed in range(20):
            picked = self.service.new_words(1, rng=random.Random(seed))
            first_words.add(picked[0]["word"])
        self.assertGreater(len(first_words), 1)        # 不再固定按字母序出第一个

    def test_zh_en_falls_back_when_prompt_leaks_answer(self):
        words = [{"word": "apparatus", "pos": "n.", "meaning": "器械，设备",
                  "short_meaning": "apparatus", "tier": "高频核心"}]
        service = VocabularyService(words, self.store)
        question = service.make_question(words[0], "zh_en")
        self.assertEqual(question["mode"], "en_zh")   # 题干混入答案时降级，避免直接送答案

    def test_migration_clears_stale_wrong_marker(self):
        path = Path(self.tmp.name) / "progress.json"
        path.write_text(json.dumps({
            "schema": 3,
            "settings": {"daily_words": 20},
            "words": {"abandon": {"seen": 3, "needs_review": True, "last_result": True,
                                  "wrong_count": 1, "next_review": "2026-11-20"}},
        }), encoding="utf-8")
        store = ProgressStore(path)
        self.assertFalse(store.word_state("abandon")["needs_review"])
        self.assertTrue((Path(self.tmp.name) / "progress_v3_backup.json").exists())


if __name__ == "__main__":
    unittest.main()
