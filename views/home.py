"""今日复习：以任务为主，不以统计图表为主（重构设计方案 §3）。

顺序固定为：到期旧词与错词 → 今日新词 → 真题阅读 → 积累本复习。
"""
from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import ttk

from ui import (BG, CARD, GREEN, MUTED, PRIMARY, PRIMARY_SOFT, RED, STRIP, TEXT,
                ScrollFrame, card, tk_label)
from views.base import BaseView


class HomeView(BaseView):
    def build(self) -> None:
        stats = self.app.stats_service.overview()
        vocab = stats["vocab"]
        due = self.app.vocab_service.due_words()
        wrong = self.app.vocab_service.wrong_words()
        new_target = int(self.store.settings.get("daily_words", 20))
        new_today = stats["vocab"]["new_today"]
        recommend = self.app.reading_service.recommend()
        minutes = int(self.store.settings.get("study_minutes", 75))

        self.header("今天，先完成最重要的复习",
                    f"{date.today():%Y年%m月%d日} · 预计 {minutes} 分钟 · 到期复习优先",
                    action=("继续复习", lambda: self.app.show_page("vocab", mode="daily")))

        scroll = ScrollFrame(self.parent, BG)
        scroll.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        body = scroll.inner

        # ---- 今日建议 ----
        hero = tk.Frame(body, bg=PRIMARY_SOFT, highlightbackground="#D6E1FA", highlightthickness=1)
        hero.pack(fill="x", pady=(0, 14))
        inner = tk.Frame(hero, bg=PRIMARY_SOFT, padx=22, pady=18)
        inner.pack(fill="x")
        tk_label(inner, "今日建议", 9, True, PRIMARY, PRIMARY_SOFT).pack(anchor="w")
        if wrong:
            headline = f"先把 {len(wrong)} 个错词重练一遍，再处理到期旧词"
            note = "错词答对只代表“本次已纠正”，要通过后续到期复习才会退出强化队列。"
        elif due:
            headline = f"先复习 {len(due)} 个到期词，再开始今天的新内容"
            note = "到期复习优先；新词目标是上限，不是必须完成的数量。"
        else:
            headline = f"今天没有到期旧词，可以学 {min(new_target, max(new_target - new_today, 0))} 个新词"
            note = "学完新词后做一组真题阅读，再把好句式收进积累本。"
        tk_label(inner, headline, 17, True, TEXT, PRIMARY_SOFT).pack(anchor="w", pady=(6, 4))
        tk_label(inner, note, 10, False, MUTED, PRIMARY_SOFT).pack(anchor="w")

        # ---- 三张概览卡 ----
        grid = tk.Frame(body, bg=BG)
        grid.pack(fill="x")
        for i in range(3):
            grid.columnconfigure(i, weight=1)
        cards = [
            ("到期复习", f"{len(due)} 词", "优先完成", PRIMARY),
            ("今日新词", f"{new_today} / {new_target}", f"还差 {max(new_target - new_today, 0)} 词", PRIMARY),
            ("阅读正确率", f"{stats['reading_accuracy']}%", f"累计 {stats['reading_answered']} 题", GREEN),
        ]
        for i, (title, value, note, color) in enumerate(cards):
            box = card(grid, 18)
            box.master.grid(row=0, column=i, sticky="nsew",
                            padx=(0, 12) if i < 2 else (0, 0))
            tk_label(box, title, 10, False, MUTED).pack(anchor="w")
            tk_label(box, value, 22, True, color).pack(anchor="w", pady=(6, 2))
            tk_label(box, note, 9, False, MUTED).pack(anchor="w")

        # ---- 主体两栏 ----
        columns = tk.Frame(body, bg=BG)
        columns.pack(fill="both", expand=True, pady=(14, 0))
        columns.columnconfigure(0, weight=3)
        columns.columnconfigure(1, weight=2)

        left = card(columns, 20)
        left.master.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        tk_label(left, "今日复习清单", 15, True).pack(anchor="w")
        tk_label(left, "按优先级排列，完成后自动进入下一项", 9, False, MUTED).pack(anchor="w", pady=(3, 14))

        tasks = [
            ("旧词与错词复习",
             f"{len(wrong)} 错词 · {len(due)} 到期词",
             "vocab", "daily", "开始" if (due or wrong) else "查看"),
            ("新词学习与四选一检测",
             f"今日 {new_today}/{new_target} · 三阶段检测",
             "vocab", "new", "继续" if new_today else "开始"),
            ("真题阅读与复盘",
             (f"{recommend['label']} · 学习模式" if recommend else "真题已全部完成"),
             "reading", "", "开始" if recommend else "查看"),
            ("积累本复习",
             f"{len(self.store.data['accumulation'])} 条自建表达",
             "accumulation", "review", "复习"),
        ]
        for index, (title, note, key, mode, label) in enumerate(tasks, 1):
            row = tk.Frame(left, bg=STRIP, padx=12, pady=10)
            row.pack(fill="x", pady=5)
            row.columnconfigure(1, weight=1)
            kwargs = {"mode": mode} if key == "vocab" and mode else (
                {"review": True} if key == "accumulation" else {})
            badge = tk.Label(row, text=str(index), font=("Microsoft YaHei UI", 10, "bold"),
                             fg=PRIMARY, bg=PRIMARY_SOFT, width=3, pady=4)
            badge.grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 10))
            title_label = tk_label(row, title, 11, True, TEXT, STRIP, anchor="w", justify="left")
            title_label.grid(row=0, column=1, sticky="w")
            note_label = tk_label(row, note, 9, False, MUTED, STRIP, anchor="w", justify="left",
                                  wraplength=1)
            note_label.grid(row=1, column=1, sticky="w", pady=(2, 0))
            ttk.Button(row, text=label, style="Primary.TButton" if index == 1 else "TButton",
                       command=lambda k=key, kw=kwargs: self.app.show_page(k, **kw)).grid(
                row=0, column=2, rowspan=2, sticky="e", padx=(10, 0))
            row.bind("<Configure>", lambda event, labels=(title_label, note_label):
                     [lb.configure(wraplength=max(120, event.width - 210)) for lb in labels])

        right = card(columns, 20)
        right.master.grid(row=0, column=1, sticky="nsew")
        tk_label(right, "复习顺序", 15, True).pack(anchor="w")
        steps = ["01　到期旧词与错词", "02　新词和阶段检测", "03　真题阅读与复盘", "04　表达积累（可选）"]
        for step in steps:
            tk_label(right, step, 10, False, TEXT).pack(anchor="w", pady=5)

        # 本周学习
        tk.Label(right, text="", bg=CARD, height=0).pack()
        line = tk.Frame(right, bg="#EEF1F7", height=1)
        line.pack(fill="x", pady=(14, 12))
        tk_label(right, "本周学习", 15, True).pack(anchor="w")
        self._draw_week(right, stats["weekly"])

        done = [stats["tasks_done"]["reviews"], new_today > 0, stats["tasks_done"]["reading"]]
        tk_label(right, f"今日完成度：{sum(1 for d in done if d)} / 3 项核心任务", 10, True,
                 PRIMARY if all(done) else MUTED).pack(anchor="w", pady=(14, 0))
        self.refresh()

    def _draw_week(self, parent, series: list[dict]) -> None:
        canvas = tk.Canvas(parent, height=112, width=248, bg=CARD, highlightthickness=0)
        canvas.pack(anchor="w", pady=(8, 0))
        peak = max([item["value"] for item in series] + [1])
        width, gap = 22, 12
        for i, item in enumerate(series):
            x = 4 + i * (width + gap)
            height = max(5, int(item["value"] / peak * 66))
            color = PRIMARY if i == len(series) - 1 else "#B9C9F2"
            canvas.create_rectangle(x, 78 - height, x + width, 78, fill=color, width=0)
            canvas.create_text(x + width / 2, 92, text=item["label"], font=("Microsoft YaHei UI", 9),
                               fill=MUTED)
