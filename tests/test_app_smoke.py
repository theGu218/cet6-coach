"""界面冒烟测试：8 个页面都能打开，核心流程能走通。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import temp_dir
from unittest.mock import patch

import main


class AppSmokeTests(unittest.TestCase):
    def test_all_pages_and_core_flows(self):
        with temp_dir() as tmp:
            with patch("repositories.store.user_data_dir", return_value=Path(tmp)), \
                 patch.object(main.messagebox, "showinfo"), \
                 patch.object(main.messagebox, "askyesno", return_value=True):
                app = main.CET6App()
                app.withdraw()
                try:
                    for page in ("home", "vocab", "reading", "accumulation", "writing",
                                 "translation", "stats", "settings"):
                        app.navigate(page)
                        app.update()
                        self.assertEqual(app.current, page)

                    # 词汇：开始今日复习并答一题
                    app.navigate("vocab")
                    view = app.main.view
                    view.start_session("daily")
                    app.update()
                    self.assertTrue(view.queue)
                    question = view.question
                    view.answer(question["answer"])
                    app.update()
                    self.assertEqual(view.correct_count, 1)

                    # 阅读：选词填空全答对后提交
                    app.navigate("reading")
                    view = app.main.view
                    exam = view._exam()
                    view.answers = {str(blank["num"]): blank["answer"]
                                    for blank in exam["cloze"]["blanks"]}
                    view._submit_cloze()
                    app.update()
                    self.assertTrue(view.results)
                    self.assertTrue(all(item["correct"] for item in view.results))
                    self.assertEqual(app.store.stats()["sessions"], 1)

                    # 积累本：添加并检索
                    app.navigate("accumulation")
                    view = app.main.view
                    item_id = app.accumulation_service.add({
                        "category": "作文句式", "title": "冒烟测试句式",
                        "pattern": "Not only does [A], but it also [B].",
                        "example": "Not only does it save time, but it also cuts cost.",
                        "example_zh": "它既节省时间，又降低成本。"})
                    app.update()
                    self.assertTrue(any(entry.get("id") == item_id
                                        for entry in app.accumulation_service.all_items()))

                    # 写作与翻译：保存草稿
                    app.navigate("writing")
                    view = app.main.view
                    view.editor.insert("1.0", "This is a smoke test essay.")
                    view._save()
                    self.assertTrue(app.store.data["writings"])

                    app.navigate("translation")
                    view = app.main.view
                    view.editor.insert("1.0", "This is a smoke test translation.")
                    view._save()
                    self.assertTrue(app.store.data["translations"])

                    # 设置：保存目标
                    app.navigate("settings")
                    view = app.main.view
                    view.words_var.set(25)
                    view._save_settings()
                    self.assertEqual(app.store.settings["daily_words"], 25)
                finally:
                    app._on_close()


if __name__ == "__main__":
    unittest.main()
