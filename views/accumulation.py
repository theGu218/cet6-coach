"""积累本：作文句式、主题词汇、翻译表达、我的笔记（重构设计方案 §7）。

独立一级导航：搜索、分类、收藏、编辑、隐藏答案式复习。
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from services.accumulation_service import CATEGORIES
from ui import (BG, CARD, GREEN, GREEN_SOFT, MUTED, PRIMARY, PRIMARY_SOFT, STRIP, TEXT,
                ScrollFrame, card, clear, tk_label)
from views.base import BaseView


class AccumulationView(BaseView):
    def build(self) -> None:
        self.service = self.app.accumulation_service
        self.query = ""
        self.category = "全部"
        self.starred_only = False
        self.revealed: set[str] = set()
        self.reviewing = False

        self.header("积累本", "作文句式 · 主题词汇 · 翻译表达 · 我的笔记 ｜ 每条都带使用场景和可替换部分",
                    action=("添加一条", self._open_editor))

        bar = tk.Frame(self.parent, bg=CARD, highlightbackground="#E1E6F0", highlightthickness=1)
        bar.pack(fill="x", padx=30, pady=(0, 10))
        inner = tk.Frame(bar, bg=CARD, padx=14, pady=10)
        inner.pack(fill="x")
        self.search_var = tk.StringVar()
        entry = ttk.Entry(inner, textvariable=self.search_var, width=30)
        entry.pack(side="left", fill="x", expand=True)
        self.search_var.trace_add("write", lambda *_: self._reload())
        self.cat_var = tk.StringVar(value="全部")
        combo = ttk.Combobox(inner, textvariable=self.cat_var, state="readonly", width=12,
                             values=self.service.categories())
        combo.pack(side="left", padx=8)
        combo.bind("<<ComboboxSelected>>", lambda _e: self._reload())
        self.star_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(inner, text="只看收藏", variable=self.star_var,
                        command=self._reload).pack(side="left", padx=6)
        ttk.Button(inner, text="隐藏答案复习", command=self._toggle_review).pack(side="left", padx=6)

        self.list_area = ScrollFrame(self.parent, BG)
        self.list_area.pack(fill="both", expand=True, padx=30, pady=(0, 18))
        self.entries = self.list_area.inner
        self._reload()
        self.refresh()

    def enter(self, review: bool = False, **_) -> None:
        if review:
            self.reviewing = True
            self.revealed.clear()
            self._reload()

    def _toggle_review(self) -> None:
        self.reviewing = not self.reviewing
        self.revealed.clear()
        self._reload()

    def _reload(self) -> None:
        self.query = self.search_var.get()
        self.category = self.cat_var.get()
        self.starred_only = self.star_var.get()
        self._render_list()

    def _render_list(self) -> None:
        clear(self.entries)
        items = self.service.filter(self.query, self.category, self.starred_only)
        if self.reviewing:
            items = [item for item in items if item.get("starred")] or items[:20]
        tk_label(self.entries, f"共 {len(items)} 条" + ("（隐藏答案复习中）" if self.reviewing else ""),
                 10, False, MUTED, BG).pack(anchor="w", pady=(0, 8))
        if not items:
            self.empty_state(self.entries, "这里还没有内容。",
                             "点右上角“添加一条”，把阅读里遇到的句式、翻译里的好表达存进来。")
            return
        for item in items:
            self._render_item(item)

    def _render_item(self, item: dict) -> None:
        box = tk.Frame(self.entries, bg=CARD, highlightbackground="#E1E6F0", highlightthickness=1)
        box.pack(fill="x", pady=5)
        inner = tk.Frame(box, bg=CARD, padx=16, pady=12)
        inner.pack(fill="x")

        top = tk.Frame(inner, bg=CARD)
        top.pack(fill="x")
        tk.Label(top, text=f" {item.get('category', '我的笔记')} ", font=("Microsoft YaHei UI", 9),
                 fg=PRIMARY, bg=PRIMARY_SOFT).pack(side="left")
        if item.get("builtin"):
            tk.Label(top, text=" 内置 ", font=("Microsoft YaHei UI", 9), fg=MUTED,
                     bg=STRIP).pack(side="left", padx=4)
        title = item.get("title") or item.get("pattern") or "（未命名）"
        tk_label(top, title, 12, True, TEXT, CARD, wraplength=640, justify="left").pack(
            side="left", padx=10)

        actions = tk.Frame(top, bg=CARD)
        actions.pack(side="right")
        star_text = "★" if item.get("starred") else "☆"
        tk.Button(actions, text=star_text, font=("Microsoft YaHei UI", 13), fg=PRIMARY, bg=CARD,
                  relief="flat", bd=0, command=lambda i=item: self._toggle_star(i)).pack(side="left", padx=2)
        if not item.get("builtin"):
            ttk.Button(actions, text="编辑", width=6,
                       command=lambda i=item: self._open_editor(i)).pack(side="left", padx=2)
            ttk.Button(actions, text="删除", width=6,
                       command=lambda i=item: self._remove(i)).pack(side="left")

        if item.get("scene"):
            tk_label(inner, f"使用场景：{item['scene']}", 9, False, MUTED, CARD,
                     wraplength=700, justify="left").pack(anchor="w", pady=(8, 0))
        pattern = item.get("pattern")
        if pattern:
            tk_label(inner, f"句式：{pattern}", 10, True, PRIMARY, CARD, wraplength=700,
                     justify="left").pack(anchor="w", pady=(4, 0))
        if item.get("substitutes"):
            subs = "　".join(f"[{sub}]" for sub in item["substitutes"])
            tk_label(inner, f"可替换部分：{subs}", 9, False, TEXT, CARD, wraplength=700,
                     justify="left").pack(anchor="w", pady=(4, 0))
        example = item.get("example")
        if example:
            hidden = self.reviewing and item.get("id") not in self.revealed
            if hidden:
                ttk.Button(inner, text="显示示例", style="Ghost.TButton",
                           command=lambda i=item: self._reveal(i)).pack(anchor="w", pady=(8, 0))
            else:
                tk_label(inner, f"示例：{example}", 10, False, TEXT, CARD, wraplength=700,
                         justify="left").pack(anchor="w", pady=(8, 0))
                if item.get("example_zh"):
                    tk_label(inner, item["example_zh"], 9, False, MUTED, CARD, wraplength=700,
                             justify="left").pack(anchor="w", pady=(2, 0))
        if item.get("note"):
            tk_label(inner, f"备注：{item['note']}", 9, False, MUTED, CARD, wraplength=700,
                     justify="left").pack(anchor="w", pady=(4, 0))
        if item.get("source"):
            tk_label(inner, f"来源：{item['source']}", 9, False, MUTED, CARD).pack(anchor="w", pady=(4, 0))

    def _reveal(self, item: dict) -> None:
        self.revealed.add(item.get("id", ""))
        self._render_list()

    def _toggle_star(self, item: dict) -> None:
        if item.get("builtin"):
            messagebox.showinfo("内置条目", "内置条目不能收藏；把它“添加一条”成自己的笔记后就可以收藏。",
                                parent=self.app)
            return
        self.service.toggle_star(item["id"])
        self._render_list()

    def _remove(self, item: dict) -> None:
        if messagebox.askyesno("删除", f"删除「{item.get('title', '')}」？此操作不可撤销。", parent=self.app):
            self.service.remove(item["id"])
            self._render_list()

    def _open_editor(self, item: dict | None = None) -> None:
        window = tk.Toplevel(self.app)
        window.title("编辑表达" if item else "添加一条表达")
        window.geometry("680x620")
        window.configure(bg=CARD)
        box = card(window, 20)
        box.master.pack(fill="both", expand=True, padx=14, pady=14)

        fields = [
            ("category", "分类", item.get("category", "作文句式") if item else "作文句式"),
            ("title", "标题", item.get("title", "") if item else ""),
            ("scene", "使用场景", item.get("scene", "") if item else ""),
            ("pattern", "句式 / 表达", item.get("pattern", "") if item else ""),
            ("substitutes", "可替换部分（用 / 分隔）", "/".join(item.get("substitutes", [])) if item else ""),
            ("example", "示例（英文）", item.get("example", "") if item else ""),
            ("example_zh", "示例翻译", item.get("example_zh", "") if item else ""),
            ("note", "备注", item.get("note", "") if item else ""),
        ]
        variables: dict[str, tk.StringVar] = {}
        for key, label, value in fields:
            row = tk.Frame(box, bg=CARD)
            row.pack(fill="x", pady=4)
            tk_label(row, label, 10, False, MUTED, CARD, width=16, anchor="w").pack(side="left")
            if key == "category":
                var = tk.StringVar(value=value)
                ttk.Combobox(row, textvariable=var, values=CATEGORIES, state="readonly",
                             width=28).pack(side="left", fill="x", expand=True)
            else:
                var = tk.StringVar(value=value)
                ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)
            variables[key] = var

        def save() -> None:
            payload = {key: var.get().strip() for key, var in variables.items()}
            payload["substitutes"] = [x.strip() for x in payload["substitutes"].split("/") if x.strip()]
            payload["category"] = payload["category"] or "我的笔记"
            payload["source"] = "手动添加"
            if not (payload["title"] or payload["pattern"]):
                messagebox.showinfo("还差一点", "至少填一个标题或句式。", parent=window)
                return
            if item:
                self.service.update(item["id"], **payload)
            else:
                self.service.add(payload)
            window.destroy()
            self._reload()

        ttk.Button(box, text="保存", style="Primary.TButton", command=save).pack(anchor="e", pady=(12, 0))
