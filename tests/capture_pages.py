"""给新版本各页面截图（用于验收）：python tests/capture_pages.py"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import patch

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import temp_dir  # noqa: E402

OUT = ROOT / "design" / "screens"


def seed(app) -> None:
    service = app.vocab_service
    words = [item["word"] for item in app.words[:24]]
    for index, word in enumerate(words):
        state = app.store.word_state(word)
        state["seen"] = 2
        state["correct"] = 1
        state["stage"] = 1
        state["status"] = "待复习"
        state["next_review"] = "2026-11-02"
        if index % 4 == 0:
            state["needs_review"] = True
            state["wrong_count"] = 2
            state["last_wrong_answer"] = "放弃"
        if index % 6 == 0:
            state["status"] = "已掌握"
            state["stage"] = 4
        app.store.set_word_state(word, state)
    app.store.touch("words", 24)
    app.store.touch("new_words", 12)
    app.store.touch("reviews", 18)
    app.store.touch("questions", 25)
    app.store.touch("minutes", 35)
    for offset, day in enumerate(["2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30",
                                  "2026-10-31", "2026-11-01", "2026-11-02"]):
        app.store.data["activity"][day] = {"minutes": 20 + offset * 8, "words": 20 + offset * 4,
                                           "questions": 5 + offset, "new_words": 10, "reviews": 12}
    app.store.add_session("仔细阅读", 4, 5, 610, "2023年12月 · 第2套 仔细阅读", exam_id="2023-12-2")
    app.store.add_session("选词填空", 8, 10, 480, "2023年6月 · 第1套 选词填空", exam_id="2023-06-1")
    app.store.save()


def grab(app, name: str) -> None:
    import ctypes
    import ctypes.wintypes as wt
    app.attributes("-topmost", True)
    app.lift()
    for _ in range(3):
        app.update()
        time.sleep(0.15)
    hwnd = ctypes.windll.user32.GetParent(app.winfo_id())
    rect = wt.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    path = OUT / f"{name}.png"
    ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom), all_screens=True).save(path)
    app.attributes("-topmost", False)
    print("saved", path)


def main() -> None:
    import ctypes
    try:  # 与 main.py 一致，先声明 DPI 感知，否则截图会与窗口尺寸错位
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    OUT.mkdir(parents=True, exist_ok=True)
    with temp_dir() as tmp:
        import main as app_module
        with patch("repositories.store.user_data_dir", return_value=Path(tmp)):
            app = app_module.CET6App()
            app.geometry("1240x820+60+40")
            seed(app)
            app.navigate("home")
            grab(app, "01-home")

            app.navigate("vocab")
            grab(app, "02-vocabulary")
            view = app.main.view
            view.start_session("daily")
            question = view.question
            view.answer(question["answer"])   # 先答对一题
            grab(app, "03-vocabulary-quiz")
            if len(view.queue) > 1:
                view._next_question()
                question = view.question
                wrong = next(i for i in range(4) if i != question["answer"])
                view.answer(wrong)
                grab(app, "04-vocabulary-wrong")

            app.navigate("reading")
            grab(app, "05-reading-cloze")
            app.main.view.kind = "careful"
            app.main.view._load_exam()
            grab(app, "06-reading-careful")
            view = app.main.view
            exam = view._exam()
            passage = exam["careful"][0]
            question = passage["questions"][0]
            wrong = next(letter for letter in ("A", "B", "C", "D") if letter != question["answer"])
            view.answers[str(question["num"])] = wrong
            view._submit_careful_question(passage, question)
            grab(app, "06b-reading-feedback")

            app.navigate("accumulation")
            grab(app, "07-accumulation")

            app.navigate("writing")
            grab(app, "08-writing")

            app.navigate("translation")
            grab(app, "09-translation")

            app.navigate("stats")
            grab(app, "10-stats")

            app.navigate("settings")
            grab(app, "11-settings")

            app._on_close()


if __name__ == "__main__":
    main()
