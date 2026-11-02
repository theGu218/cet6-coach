"""翻译训练：真题汉译英、草稿保存、原文与参考译文对照（重构设计方案 §8）。"""
from __future__ import annotations

import re
import tkinter as tk
from tkinter import messagebox, ttk

from ui import (BG, CARD, GREEN, MUTED, PRIMARY, PRIMARY_SOFT, TEXT, Countdown,
                ScrollFrame, card, clear, editor_text, tk_label)
from views.base import BaseView


class TranslationView(BaseView):
    def build(self) -> None:
        self.tasks = self.app.translations
        self.index = 0
        self.timer = None
        self.header("翻译训练", "汉译英 30 分钟｜先完整表达意思，再优化句式与用词")
        if not self.tasks:
            self.empty_state(self.parent, "暂无翻译题目。", "content/translation.json 里还没有真题翻译数据。")
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
            self.timer.toggle()

    def _load(self, index: int) -> None:
        self.index = index
        task = self.tasks[index]
        self.task_var.set(task["label"])
        clear(self.area)

        pane = tk.Frame(self.area, bg=BG)
        pane.pack(fill="both", expand=True)
        pane.columnconfigure(0, weight=2)
        pane.columnconfigure(1, weight=3)
        left = card(pane, 18)
        left.master.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        right = card(pane, 16)
        right.master.grid(row=0, column=1, sticky="nsew")

        tk_label(left, task.get("label", ""), 10, True, PRIMARY).pack(anchor="w")
        tk_label(left, "将下面的段落译成英文", 9, False, MUTED).pack(anchor="w", pady=(2, 10))
        scroll = ScrollFrame(left, CARD)
        scroll.pack(fill="both", expand=True)
        text = tk.Text(scroll.inner, wrap="word", font=("Microsoft YaHei UI", 13), bg=CARD, fg=TEXT,
                       relief="flat", padx=6, pady=6, spacing1=4, spacing3=10, borderwidth=0)
        text.insert("1.0", task.get("chinese", ""))
        text.configure(state="disabled")
        text.pack(fill="both", expand=True)
        if task.get("points"):
            tk_label(left, "重点表达（先自己译，再对照）", 10, True, TEXT).pack(anchor="w", pady=(10, 4))
            for point in task["points"]:
                line = f"{point['zh']} → {point['en']}" if isinstance(point, dict) else str(point)
                tk_label(left, line, 9, False, MUTED, wraplength=270, justify="left").pack(anchor="w", pady=2)
                ttk.Button(left, text="加入积累本",
                           command=lambda p=point: self._collect(p, task)).pack(anchor="e")

        head = tk.Frame(right, bg=CARD)
        head.pack(fill="x")
        tk_label(head, "我的译文", 13, True).pack(side="left")
        self.count_label = tk_label(head, "0 词", 9, False, MUTED)
        self.count_label.pack(side="left", padx=10)
        self.editor = editor_text(right, 12)
        self.editor.pack(fill="both", expand=True, pady=(8, 0))
        saved = self.store.composition("translation", task["id"]).get("text", "")
        if saved:
            self.editor.insert("1.0", saved)
        self.editor.bind("<KeyRelease>", lambda _e: self._update_count())

        actions = tk.Frame(right, bg=CARD)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="保存译文", style="Primary.TButton",
                   command=self._save).pack(side="left")
        ttk.Button(actions, text="参考译文对照", command=self._show_reference).pack(side="left", padx=8)
        self._update_count()
        self.timer = Countdown(self.timer_label, int(task.get("minutes", 30)),
                               lambda: messagebox.showinfo("时间到", "建议时间已到，可以开始对照参考译文。",
                                                           parent=self.app))
        self.refresh()

    def _update_count(self) -> None:
        if not getattr(self, "editor", None):
            return
        text = self.editor.get("1.0", "end-1c")
        count = len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", text))
        self.count_label.configure(text=f"{count} 词", fg=GREEN if count else MUTED)

    def _save(self) -> None:
        task = self.tasks[self.index]
        self.store.save_composition("translation", task["id"], self.editor.get("1.0", "end-1c").strip())
        messagebox.showinfo("已保存", "译文已保存到本机。", parent=self.app)
        self.refresh()

    def _show_reference(self) -> None:
        task = self.tasks[self.index]
        window = tk.Toplevel(self.app)
        window.title("参考译文｜" + task["label"])
        window.geometry("760x660")
        window.configure(bg=CARD)
        scroll = ScrollFrame(window, CARD)
        scroll.pack(fill="both", expand=True, padx=14, pady=14)
        body = scroll.inner
        tk_label(body, "参考译文（同一意思有多种译法）", 13, True, PRIMARY).pack(anchor="w")
        text = tk.Text(body, wrap="word", font=("Microsoft YaHei UI", 11), bg=CARD, fg=TEXT,
                       relief="flat", padx=4, pady=4, spacing1=3, spacing3=8, height=16, borderwidth=0)
        text.insert("1.0", task.get("reference") or "这篇真题的参考译文还在整理中。")
        text.configure(state="disabled")
        text.pack(fill="both", expand=True, pady=(8, 0))
        if task.get("points"):
            tk_label(body, "翻译要点", 12, True, TEXT).pack(anchor="w", pady=(10, 4))
            for point in task["points"]:
                line = f"• {point['zh']} → {point['en']}" if isinstance(point, dict) else f"• {point}"
                tk_label(body, line, 10, False, MUTED, wraplength=700, justify="left").pack(anchor="w")
        ttk.Button(body, text="关闭", command=window.destroy).pack(anchor="e", pady=(10, 0))

    def _collect(self, point, task: dict) -> None:
        if isinstance(point, dict):
            zh, en = point.get("zh", ""), point.get("en", "")
        else:
            zh, en = str(point), ""
        self.app.accumulation_service.add({
            "category": "翻译表达",
            "title": zh[:40] or en[:40],
            "pattern": en,
            "example": en,
            "example_zh": zh,
            "scene": f"{task.get('label', '')} 翻译",
            "source": f"{task.get('label', '')} 参考译文",
        })
        messagebox.showinfo("已加入积累本", "已保存到积累本，可在「翻译表达」分类下复习。", parent=self.app)
