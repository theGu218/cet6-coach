"""复盘统计：不是打卡数字，而是告诉用户下一步该练什么（重构设计方案 §6、§11）。"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ui import (AMBER, BG, CARD, GREEN, MUTED, PRIMARY, PRIMARY_SOFT, RED, STRIP, TEXT,
                ScrollFrame, card, tk_label)
from views.base import BaseView


class StatsView(BaseView):
    def build(self) -> None:
        self.stats = self.app.stats_service.overview()
        self.header("复盘统计", "看正确率、看错误原因、看下一步练什么；不追求无意义的打卡数字")

        scroll = ScrollFrame(self.parent, BG)
        scroll.pack(fill="both", expand=True, padx=30, pady=(0, 18))
        body = scroll.inner
        stats = self.stats
        vocab = stats["vocab"]

        grid = tk.Frame(body, bg=BG)
        grid.pack(fill="x")
        for i in range(4):
            grid.columnconfigure(i, weight=1)
        cards = [
            ("掌握词汇", f"{vocab['mastered']}", f"共 {vocab['total']} 词 · 待复习 {vocab['due']}", PRIMARY),
            ("连续学习", f"{stats['streak']} 天", f"今日 {stats['minutes_today']} 分钟", GREEN),
            ("阅读正确率", f"{stats['reading_accuracy']}%", f"累计 {stats['reading_answered']} 题", PRIMARY),
            ("待强化错词", f"{vocab['wrong']}", f"错题 {stats['wrong']} 道", AMBER),
        ]
        for i, (title, value, note, color) in enumerate(cards):
            box = card(grid, 16)
            box.master.grid(row=0, column=i, sticky="nsew", padx=(0, 12) if i < 3 else (0, 0))
            tk_label(box, title, 9, False, MUTED).pack(anchor="w")
            tk_label(box, value, 21, True, color).pack(anchor="w", pady=(5, 2))
            tk_label(box, note, 9, False, MUTED).pack(anchor="w")

        # 本周学习
        week = card(body, 18)
        week.master.pack(fill="x", pady=14)
        tk_label(week, "近 7 天学习活动", 13, True).pack(anchor="w")
        tk_label(week, "柱高 = 学习分钟 + 词汇作答 + 阅读题数，仅用于看节奏", 9, False, MUTED).pack(
            anchor="w", pady=(2, 8))
        self._draw_week(week, stats["weekly"])

        columns = tk.Frame(body, bg=BG)
        columns.pack(fill="both", expand=True)
        columns.columnconfigure(0, weight=1)
        columns.columnconfigure(1, weight=1)

        left = card(columns, 18)
        left.master.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        tk_label(left, "分题型正确率", 13, True).pack(anchor="w", pady=(0, 10))
        by_kind = stats["by_kind"]
        for name, (accuracy, total) in by_kind.items():
            row = tk.Frame(left, bg=CARD)
            row.pack(fill="x", pady=6)
            tk_label(row, name, 10, True, TEXT, CARD, width=10, anchor="w").pack(side="left")
            bar = tk.Canvas(row, height=12, bg=CARD, highlightthickness=0, width=200)
            bar.pack(side="left", padx=8)
            bar.create_rectangle(0, 0, 200, 12, fill="#EDF1F7", width=0)
            bar.create_rectangle(0, 0, max(2, int(accuracy / 100 * 200)), 12,
                                 fill=GREEN if accuracy >= 70 else (AMBER if accuracy >= 50 else RED), width=0)
            tk_label(row, f"{accuracy}%", 10, True, TEXT, CARD).pack(side="left")
            tk_label(row, f"{total} 题", 9, False, MUTED, CARD).pack(side="left", padx=6)

        right = card(columns, 18)
        right.master.grid(row=0, column=1, sticky="nsew")
        tk_label(right, "错因分布与下一步", 13, True).pack(anchor="w", pady=(0, 8))
        weak = self.app.stats_service.weak_points()
        if not weak:
            tk_label(right, "还没有错题记录。做完一组真题阅读后，这里会给出针对性建议。",
                     10, False, MUTED, wraplength=430, justify="left").pack(anchor="w", pady=8)
        else:
            for item in weak[:4]:
                box = tk.Frame(right, bg=STRIP, padx=12, pady=10)
                box.pack(fill="x", pady=4)
                top = tk.Frame(box, bg=STRIP)
                top.pack(fill="x")
                tk_label(top, item["reason"], 10, True, TEXT, STRIP).pack(side="left")
                tk_label(top, f"{item['count']} 题 · {item['share']}%", 9, False, MUTED, STRIP).pack(side="right")
                tk_label(box, item["advice"], 9, False, MUTED, STRIP, wraplength=420,
                         justify="left").pack(anchor="w", pady=(3, 0))

        # 词汇状态分布
        dist = card(body, 18)
        dist.master.pack(fill="x", pady=14)
        tk_label(dist, "词汇状态分布", 13, True).pack(anchor="w", pady=(0, 10))
        row = tk.Frame(dist, bg=CARD)
        row.pack(fill="x")
        states = [("已掌握", vocab["mastered"], GREEN), ("待复习", vocab["due"], PRIMARY),
                  ("学习中", max(0, vocab["learning"] - vocab["wrong"]), AMBER),
                  ("待巩固", vocab["wrong"], RED),
                  ("未学", max(0, vocab["total"] - vocab["mastered"] - vocab["learning"]), MUTED)]
        for name, value, color in states:
            column = tk.Frame(row, bg=STRIP, padx=14, pady=10)
            column.pack(side="left", fill="x", expand=True, padx=(0, 8))
            tk_label(column, name, 9, False, MUTED, STRIP).pack(anchor="w")
            tk_label(column, f"{value} 词", 15, True, color, STRIP).pack(anchor="w", pady=(2, 0))

        # 最近交卷
        recent = card(body, 18)
        recent.master.pack(fill="both", expand=True)
        tk_label(recent, "最近交卷记录", 13, True).pack(anchor="w", pady=(0, 8))
        tree = ttk.Treeview(recent, columns=("date", "category", "title", "score", "time", "mode"),
                            show="headings", height=8)
        for key, title, width in [("date", "时间", 140), ("category", "题型", 90), ("title", "练习", 360),
                                  ("score", "成绩", 80), ("time", "用时", 80), ("mode", "模式", 80)]:
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="w")
        tree.pack(fill="both", expand=True)
        for session in self.app.stats_service.recent_sessions(20):
            tree.insert("", "end", values=(
                session.get("date", "").replace("T", " "), session.get("category", ""),
                session.get("title", ""), f"{session.get('score', 0)} / {session.get('total', 0)}",
                f"{session.get('seconds', 0) // 60}分{session.get('seconds', 0) % 60}秒",
                "考试" if session.get("mode") == "exam" else "学习"))
        self.refresh()

    def _draw_week(self, parent, series: list[dict]) -> None:
        canvas = tk.Canvas(parent, height=170, bg=CARD, highlightthickness=0)
        canvas.pack(fill="x", pady=(6, 0))
        peak = max([item["value"] for item in series] + [1])
        width, gap = 46, 26
        for i, item in enumerate(series):
            x = 30 + i * (width + gap)
            height = max(4, int(item["value"] / peak * 110))
            color = PRIMARY if i == len(series) - 1 else "#B9C9F2"
            canvas.create_rectangle(x, 128 - height, x + width, 128, fill=color, width=0)
            canvas.create_text(x + width / 2, 112 - height, text=str(item["value"]),
                               font=("Microsoft YaHei UI", 9), fill=TEXT)
            canvas.create_text(x + width / 2, 146, text=item["label"], font=("Microsoft YaHei UI", 9),
                               fill=MUTED)
