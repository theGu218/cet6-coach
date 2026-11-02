"""写作训练：真题作文、30 分钟限时、草稿保存、范文对照（重构设计方案 §8）。"""
from __future__ import annotations

import re
import tkinter as tk
from tkinter import messagebox, ttk

from ui import (AMBER, BG, CARD, GREEN, MUTED, PRIMARY, PRIMARY_SOFT, STRIP, TEXT,
                Countdown, ScrollFrame, card, clear, editor_text, tk_label)
from views.base import BaseView


class WritingView(BaseView):
    def build(self) -> None:
        self.tasks = self.app.writings
        self.index = 0
        self.timer = None
        self.header("写作训练", "30 分钟 · 150–200 词｜先独立写，再对照范文和表达")
        if not self.tasks:
            self.empty_state(self.parent, "暂无作文题目。", "content/writing.json 里还没有真题作文数据。")
            return

        bar = tk.Frame(self.parent, bg=CARD, highlightbackground="#E1E6F0", highlightthickness=1)
        bar.pack(fill="x", padx=30, pady=(0, 10))
        inner = tk.Frame(bar, bg=CARD, padx=14, pady=10)
        inner.pack(fill="x")
        self.task_var = tk.StringVar()
        self.combo = ttk.Combobox(inner, textvariable=self.task_var, state="readonly", width=48,
                                  values=[task["label"] for task in self.tasks])
        self.combo.pack(side="left")
        self.combo.bind("<<ComboboxSelected>>", lambda _e: self._on_change())
        tk_label(inner, "", 9, False, MUTED, CARD).pack(side="left", padx=8)
        self.timer_label = tk.Label(inner, text="", font=("Microsoft YaHei UI", 12, "bold"),
                                    fg=MUTED, bg=CARD)
        self.timer_label.pack(side="right", padx=(8, 0))
        ttk.Button(inner, text="开始 / 暂停", command=self._toggle).pack(side="right")

        self.area = tk.Frame(self.parent, bg=BG)
        self.area.pack(fill="both", expand=True, padx=30, pady=(0, 18))
        self._load(0)

    def enter(self, task_id: str = "", **_) -> None:
        for index, task in enumerate(self.tasks):
            if task.get("id") == task_id:
                self._load(index)
                return

    def _on_change(self) -> None:
        for index, task in enumerate(self.tasks):
            if task["label"] == self.task_var.get():
                self._load(index)
                return

    def _toggle(self) -> None:
        if self.timer:
            running = self.timer.toggle()
            if running is False:
                pass

    def _load(self, index: int) -> None:
        self.index = index
        task = self.tasks[index]
        self.task_var.set(task["label"])
        clear(self.area)
        pass

        pane = tk.Frame(self.area, bg=BG)
        pane.pack(fill="both", expand=True)
        pane.columnconfigure(0, weight=2)
        pane.columnconfigure(1, weight=3)
        left = card(pane, 18)
        left.master.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        right = card(pane, 16)
        right.master.grid(row=0, column=1, sticky="nsew")

        scroll = ScrollFrame(left, CARD)
        scroll.pack(fill="both", expand=True)
        body = scroll.inner
        tk_label(body, task.get("label", ""), 10, True, PRIMARY).pack(anchor="w")
        tk_label(body, task.get("title", ""), 15, True, TEXT, wraplength=270, justify="left").pack(
            anchor="w", pady=(4, 10))
        if task.get("sentence"):
            hint = tk.Frame(body, bg=PRIMARY_SOFT, padx=12, pady=10)
            hint.pack(fill="x", pady=(0, 10))
            tk_label(hint, "给定首句", 9, True, PRIMARY, PRIMARY_SOFT).pack(anchor="w")
            tk_label(hint, task["sentence"], 10, False, TEXT, PRIMARY_SOFT, wraplength=250,
                     justify="left", anchor="w").pack(anchor="w", pady=(4, 0))
        tk_label(body, "Directions", 10, True, TEXT).pack(anchor="w", pady=(4, 4))
        tk_label(body, task.get("directions", ""), 9, False, MUTED, wraplength=270,
                 justify="left").pack(anchor="w")
        if task.get("outline"):
            tk_label(body, "推荐思路", 10, True, TEXT).pack(anchor="w", pady=(12, 4))
            for i, line in enumerate(task["outline"], 1):
                tk_label(body, f"{i}. {line}", 9, False, MUTED, wraplength=270,
                         justify="left").pack(anchor="w", pady=2)
        if task.get("expressions"):
            tk_label(body, "可复用表达（可加入积累本）", 10, True, TEXT).pack(anchor="w", pady=(12, 4))
            for expression in task["expressions"]:
                row = tk.Frame(body, bg=CARD)
                row.pack(fill="x", pady=2)
                tk_label(row, "• " + (expression.get("en") if isinstance(expression, dict) else str(expression)),
                         9, False, PRIMARY, wraplength=270, justify="left").pack(side="left")
                ttk.Button(row, text="收", width=3,
                           command=lambda e=expression: self._collect(e, task)).pack(side="right")

        head = tk.Frame(right, bg=CARD)
        head.pack(fill="x")
        tk_label(head, "我的作文", 13, True).pack(side="left")
        self.count_label = tk_label(head, "0 词", 9, False, MUTED)
        self.count_label.pack(side="left", padx=10)
        self.editor = editor_text(right, 12)
        self.editor.pack(fill="both", expand=True, pady=(8, 0))
        saved = self.store.composition("writing", task["id"]).get("text", "")
        if saved:
            self.editor.insert("1.0", saved)
        self.editor.bind("<KeyRelease>", lambda _e: self._update_count())

        actions = tk.Frame(right, bg=CARD)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="保存草稿", style="Primary.TButton",
                   command=self._save).pack(side="left")
        ttk.Button(actions, text="范文对照", command=self._show_sample).pack(side="left", padx=8)
        ttk.Button(actions, text="加入我的表达", command=self._collect_all).pack(side="left")
        self._update_count()
        minutes = int(task.get("minutes", 30))
        self.timer = Countdown(self.timer_label, minutes,
                               lambda: messagebox.showinfo("时间到", "建议写作时间已到，可以开始对照范文了。",
                                                           parent=self.app))
        self.refresh()

    def _update_count(self) -> None:
        if not getattr(self, "editor", None):
            return
        text = self.editor.get("1.0", "end-1c")
        count = len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", text))
        color = GREEN if 150 <= count <= 200 else MUTED
        self.count_label.configure(text=f"{count} 词｜建议 150–200 词", fg=color)

    def _save(self) -> None:
        task = self.tasks[self.index]
        text = self.editor.get("1.0", "end-1c").strip()
        self.store.save_composition("writing", task["id"], text)
        messagebox.showinfo("已保存", "草稿已保存到本机，下次可以接着改。", parent=self.app)
        self.refresh()

    def _show_sample(self) -> None:
        task = self.tasks[self.index]
        if not task.get("sample"):
            messagebox.showinfo(
                "范文待补充",
                "这篇真题的参考范文还在整理中。可以先用左侧“推荐思路”和“可复用表达”自查结构。",
                parent=self.app)
            return
        window = tk.Toplevel(self.app)
        window.title("参考范文｜" + task["label"])
        window.geometry("740x680")
        window.configure(bg=CARD)
        scroll = ScrollFrame(window, CARD)
        scroll.pack(fill="both", expand=True, padx=14, pady=14)
        body = scroll.inner
        tk_label(body, "参考范文（不是唯一答案）", 14, True, PRIMARY).pack(anchor="w")
        text = tk.Text(body, wrap="word", font=("Microsoft YaHei UI", 11), bg=CARD, fg=TEXT,
                       relief="flat", padx=4, pady=4, spacing1=3, spacing3=8, height=18, borderwidth=0)
        text.insert("1.0", task["sample"])
        text.configure(state="disabled")
        text.pack(fill="both", expand=True, pady=(8, 0))
        if task.get("sample_zh"):
            tk_label(body, "范文思路", 12, True, TEXT).pack(anchor="w", pady=(10, 4))
            tk_label(body, task["sample_zh"], 10, False, MUTED, wraplength=680, justify="left").pack(anchor="w")
        ttk.Button(body, text="关闭", command=window.destroy).pack(anchor="e", pady=(10, 0))

    def _collect(self, expression, task: dict) -> None:
        en = expression.get("en") if isinstance(expression, dict) else str(expression)
        zh = expression.get("zh", "") if isinstance(expression, dict) else ""
        self.service_add(en, zh, task)
        messagebox.showinfo("已加入积累本", "已保存到「我的笔记」，可以在积累本里查看和复习。", parent=self.app)

    def _collect_all(self) -> None:
        task = self.tasks[self.index]
        for expression in task.get("expressions", []):
            en = expression.get("en") if isinstance(expression, dict) else str(expression)
            zh = expression.get("zh", "") if isinstance(expression, dict) else ""
            self.service_add(en, zh, task, quiet=True)
        messagebox.showinfo("已加入积累本", f"已加入 {len(task.get('expressions', []))} 条表达。", parent=self.app)

    def service_add(self, en: str, zh: str, task: dict, quiet: bool = False) -> None:
        self.app.accumulation_service.add({
            "category": "作文句式",
            "title": en[:40],
            "pattern": en,
            "example": en,
            "example_zh": zh,
            "scene": f"{task.get('theme') or '作文'}",
            "source": f"{task.get('label', '')} 范文表达",
        })
