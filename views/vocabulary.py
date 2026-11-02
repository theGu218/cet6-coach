"""核心词汇：三阶段检测 + 错词重练 + 间隔复习（重构设计方案 §5）。"""
from __future__ import annotations

import random
import tkinter as tk
from tkinter import messagebox, ttk

from services.vocabulary_service import INTERVALS, MODE_NAMES
from ui import (AMBER, AMBER_SOFT, BG, CARD, GREEN, GREEN_SOFT, MUTED, PRIMARY,
                PRIMARY_SOFT, RED, RED_SOFT, STRIP, TEXT, ScrollFrame, card, clear,
                tk_label)
from views.base import BaseView

TIERS = ("全部", "高频核心", "基础回顾", "六级拓展")


class VocabularyView(BaseView):
    def build(self) -> None:
        self.service = self.app.vocab_service
        self.queue: list[dict] = []
        self.index = 0
        self.question = None
        self.answered = False
        self.selected = None
        self.correct_count = 0
        self.finished = 0
        self.retry: dict[str, int] = {}

        summary = self.service.summary()
        self.header("核心词汇",
                    f"到期 {summary['due']} 词 · 今日新学 {summary['new_today']}/{self.store.settings.get('daily_words', 20)}"
                    f" · 错词 {summary['wrong']} 个 · 共 {summary['total']} 词")

        self.tabs = ttk.Notebook(self.parent)
        self.tabs.pack(fill="both", expand=True, padx=30, pady=(0, 18))
        self.today_tab = ttk.Frame(self.tabs)
        self.quiz_tab = ttk.Frame(self.tabs)
        self.wrong_tab = ttk.Frame(self.tabs)
        self.star_tab = ttk.Frame(self.tabs)
        self.list_tab = ttk.Frame(self.tabs)
        for tab, name in [(self.today_tab, " 今日学习 "), (self.quiz_tab, " 四选一检测 "),
                          (self.wrong_tab, " 错词本 "), (self.star_tab, " 生词本 "),
                          (self.list_tab, " 词汇表 ")]:
            self.tabs.add(tab, text=name)
        self._build_today()
        self._build_wrong()
        self._build_stars()
        self._build_list()
        self._refresh_all()
        self.refresh()

    def enter(self, mode: str = "", **_) -> None:
        if mode in ("daily", "new", "wrong", "star"):
            self.start_session(mode)

    # ================= 今日学习 =================
    def _build_today(self) -> None:
        clear(self.today_tab)
        due = self.service.due_words()
        wrong = self.service.wrong_words()
        new = self.service.new_words(int(self.store.settings.get("daily_words", 20)))
        box = card(self.today_tab, 22)
        box.master.pack(fill="both", expand=True)
        tk_label(box, "今天从哪里开始？", 17, True).pack(anchor="w")
        tk_label(box, "到期复习优先。答错的词会进入本轮重练，并安排以后再次检测。",
                 10, False, MUTED).pack(anchor="w", pady=(4, 16))

        rows = [("到期旧词", f"{len(due)} 词", "按上次复习日期自动生成", PRIMARY),
                ("待强化错词", f"{len(wrong)} 词", "答错自动收录，保留错误历史", AMBER),
                ("今日新词", f"{len(new)} 词", f"每日上限 {self.store.settings.get('daily_words', 20)} 词", GREEN)]
        for title, value, note, color in rows:
            row = tk.Frame(box, bg=STRIP, padx=16, pady=14)
            row.pack(fill="x", pady=5)
            tk_label(row, title, 11, True, TEXT, STRIP).pack(side="left")
            tk_label(row, value, 15, True, color, STRIP).pack(side="left", padx=20)
            tk_label(row, note, 9, False, MUTED, STRIP).pack(side="left")

        stages = tk.Frame(box, bg=CARD)
        stages.pack(fill="x", pady=(18, 6))
        for i, (name, desc, state) in enumerate([
                ("① 英译汉", "建立基本词义识别", True),
                ("② 汉译英", "加强主动回忆", False),
                ("③ 语境选择", "检验真实理解", False)], 1):
            column = tk.Frame(stages, bg=PRIMARY_SOFT if state else STRIP, padx=14, pady=12)
            column.pack(side="left", fill="x", expand=True, padx=(0, 10) if i < 3 else (0, 0))
            tk_label(column, name, 12, True, PRIMARY if state else TEXT,
                     PRIMARY_SOFT if state else STRIP).pack(anchor="w")
            tk_label(column, desc, 9, False, MUTED, PRIMARY_SOFT if state else STRIP).pack(anchor="w", pady=(4, 0))
            if not state:
                tk_label(column, "答对上一阶段后解锁", 9, False, MUTED,
                         STRIP).pack(anchor="w", pady=(2, 0))

        buttons = tk.Frame(box, bg=CARD)
        buttons.pack(fill="x", pady=(16, 0))
        ttk.Button(buttons, text="开始今日复习", style="Primary.TButton",
                   command=lambda: self.start_session("daily")).pack(side="left")
        ttk.Button(buttons, text="只练错词",
                   command=lambda: self.start_session("wrong")).pack(side="left", padx=10)
        ttk.Button(buttons, text="学新词",
                   command=lambda: self.start_session("new")).pack(side="left")
        ttk.Button(buttons, text="浏览全部词汇",
                   command=lambda: self.tabs.select(self.list_tab)).pack(side="right")

    def _refresh_today(self) -> None:
        if getattr(self, "today_tab", None) is not None and self.today_tab.winfo_exists():
            self._build_today()

    # ================= 四选一检测 =================
    def start_session(self, mode: str) -> None:
        if mode == "wrong":
            items = self.service.wrong_words()
        elif mode == "new":
            items = self.service.new_words(int(self.store.settings.get("daily_words", 20)))
        elif mode == "star":
            items = self.service.starred_words()
        else:
            items = self.service.daily_queue()
        unique, seen = [], set()
        for item in items:
            key = item["word"].lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        if not unique:
            messagebox.showinfo("没有待练内容",
                                "这个队列已经清空。可以学新词，或到词汇表里挑几个词来练。",
                                parent=self.app)
            return
        self.queue = unique
        self.index = 0
        self.question = None
        self.answered = False
        self.selected = None
        self.correct_count = 0
        self.finished = 0
        self.retry = {}
        self.tabs.select(self.quiz_tab)
        self._render_question()

    def _render_question(self) -> None:
        clear(self.quiz_tab)
        if self.index >= len(self.queue):
            self._render_summary()
            return
        item = self.queue[self.index]
        if self.question is None:
            self.question = self.service.make_question(item)
        question = self.question

        pane = tk.Frame(self.quiz_tab, bg=BG)
        pane.pack(fill="both", expand=True)
        pane.columnconfigure(0, weight=3)
        pane.columnconfigure(1, weight=2)
        left = card(pane, 22)
        left.master.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        right = card(pane, 20)
        right.master.grid(row=0, column=1, sticky="nsew")

        top = tk.Frame(left, bg=CARD)
        top.pack(fill="x")
        tk_label(top, f"{question['mode_name']} · 第 {self.index + 1} / {len(self.queue)} 题",
                 10, True, PRIMARY).pack(side="left")
        tk_label(top, f"本轮答对 {self.correct_count}", 10, False, MUTED).pack(side="right")
        bar = ttk.Progressbar(left, maximum=len(self.queue), value=self.index + 1)
        bar.pack(fill="x", pady=(10, 18))

        size = 30 if question["mode"] == "en_zh" else (18 if question["mode"] == "context" else 22)
        tk_label(left, question["prompt"], size, True, TEXT,
                 justify="left", wraplength=620).pack(anchor="w", pady=(6, 4))
        tk_label(left, question["sub"], 10, False, MUTED, justify="left",
                 wraplength=620).pack(anchor="w", pady=(0, 16))

        for i, option in enumerate(question["options"]):
            base_bg, base_fg, note = CARD, TEXT, ""
            if self.answered:
                if i == question["answer"]:
                    base_bg, base_fg, note = GREEN_SOFT, GREEN, "　正确答案"
                elif i == self.selected:
                    base_bg, base_fg, note = RED_SOFT, RED, "　你的选择"
            state = "disabled" if self.answered else "normal"
            button = tk.Button(left, text=f"{self.letter(i)}. {option}{note}", anchor="w",
                               justify="left", wraplength=580, bg=base_bg, fg=base_fg,
                               font=("Microsoft YaHei UI", 11, "bold" if self.answered and i == question["answer"] else "normal"),
                               activebackground=PRIMARY_SOFT, relief="solid", bd=1, padx=14, pady=11,
                               cursor="hand2", command=lambda idx=i: self.answer(idx), state=state,
                               disabledforeground=base_fg)
            button.pack(fill="x", pady=4)

        if self.answered:
            self._render_feedback(left, question)

        tk_label(right, "本题学习辅助", 14, True).pack(anchor="w")
        if self.answered:
            tk_label(right, question["meaning"], 10, True, TEXT, wraplength=280,
                     justify="left").pack(anchor="w", pady=(12, 8))
            example = question["example"] or "这个词暂时没有收录语境例句，可以先看完整释义。"
            tk_label(right, example, 9, False, MUTED, wraplength=280, justify="left").pack(anchor="w")
            if question["example_zh"]:
                tk_label(right, question["example_zh"], 9, False, MUTED, wraplength=280,
                         justify="left").pack(anchor="w", pady=(6, 0))
        else:
            tk_label(right, "① 英译汉：先认词义\n\n② 汉译英：主动回忆\n\n③ 语境选择：看用法",
                     10, False, MUTED, justify="left").pack(anchor="w", pady=(12, 12))
        starred = self.store.is_starred(question["word"])
        ttk.Button(right, text="★ 已在生词本" if starred else "☆ 加入生词本",
                   command=self._toggle_star).pack(fill="x", pady=(18, 4))
        ttk.Button(right, text="查看完整词条",
                   command=lambda: self._show_word(question["word"])).pack(fill="x")
        self.refresh()

    def _render_feedback(self, parent, question: dict) -> None:
        correct = self.selected == question["answer"]
        state = self.service.state(question["word"])
        bg = GREEN_SOFT if correct else AMBER_SOFT
        fg = GREEN if correct else AMBER
        row = tk.Frame(parent, bg=bg, padx=14, pady=10)
        row.pack(fill="x", pady=(10, 4))
        if correct:
            text = f"回答正确 · 当前状态：{state.get('status', '待复习')} · 下次复习：{state.get('next_review', '待定')}"
            if state.get("status") == "已掌握":
                text += "（达到掌握条件，仍会低频复查）"
        else:
            text = f"已加入错词重练 · 本轮稍后还会出现 · 下次复习：{state.get('next_review', '今天')}"
        tk.Label(row, text=text, font=("Microsoft YaHei UI", 10, "bold"), fg=fg, bg=bg,
                 wraplength=300, justify="left", anchor="w").pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="下一题", style="Primary.TButton",
                   command=self._next_question).pack(side="right", padx=(8, 0))

    def answer(self, index: int) -> None:
        if self.answered:
            return
        self.selected = index
        self.answered = True
        self.finished += 1
        question = self.question
        correct = index == question["answer"]
        self.correct_count += int(correct)
        self.service.record(question["word"], question["mode"], correct,
                            question["options"][index])
        if not correct:
            count = self.retry.get(question["word"], 0)
            if count < 2:  # 本轮内最多重现两次，避免死循环
                self.retry[question["word"]] = count + 1
                gap = random.randint(3, 5)
                position = min(len(self.queue), self.index + gap)
                self.queue.insert(position, self.queue[self.index])
        self._render_question()
        self._refresh_all()
        self._refresh_today()

    def _next_question(self) -> None:
        self.index += 1
        self.answered = False
        self.selected = None
        self.question = None
        self._render_question()

    def _render_summary(self) -> None:
        clear(self.quiz_tab)
        box = card(self.quiz_tab, 30)
        box.master.pack(fill="both", expand=True)
        tk_label(box, "本组练习完成", 22, True, PRIMARY).pack(pady=(36, 8))
        tk_label(box, f"共作答 {self.finished} 题 · 答对 {self.correct_count} 题", 14, False,
                 TEXT).pack()
        tk_label(box, "本轮答对不等于永久掌握：错词仍会在到期复习里再次出现。",
                 10, False, MUTED).pack(pady=12)
        row = tk.Frame(box, bg=CARD)
        row.pack(pady=16)
        ttk.Button(row, text="再练一组", style="Primary.TButton",
                   command=lambda: self.start_session("daily")).pack(side="left", padx=4)
        ttk.Button(row, text="只练剩余错词",
                   command=lambda: self.start_session("wrong")).pack(side="left", padx=4)
        ttk.Button(row, text="返回今日学习",
                   command=lambda: self.tabs.select(self.today_tab)).pack(side="left", padx=4)
        self._refresh_all()

    def _toggle_star(self) -> None:
        if not self.question:
            return
        self.service.toggle_star(self.question["word"])
        self._render_question()
        self._refresh_stars()

    # ================= 错词本 =================
    def _build_wrong(self) -> None:
        clear(self.wrong_tab)
        items = self.service.wrong_words()
        top = tk.Frame(self.wrong_tab)
        top.pack(fill="x", pady=(0, 8))
        tk.Label(top, text=f"{len(items)} 个待强化词", font=("Microsoft YaHei UI", 12, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        ttk.Button(top, text="开始错词重练", style="Primary.TButton",
                   command=lambda: self.start_session("wrong")).pack(side="right")
        if not items:
            self.empty_state(self.wrong_tab, "暂时没有错词。",
                             "答错或拼错的词会自动进入这里，答对后仍需到期复习通过才会退出。")
            return
        columns = ("word", "meaning", "wrong", "last", "next")
        tree = ttk.Treeview(self.wrong_tab, columns=columns, show="headings")
        for key, title, width in [("word", "单词", 140), ("meaning", "释义", 320),
                                  ("wrong", "答错次数", 90), ("last", "最近错误答案", 190),
                                  ("next", "下次复习", 110)]:
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="w")
        tree.pack(fill="both", expand=True)
        for item in items:
            state = self.service.state(item["word"])
            tree.insert("", "end", iid=item["word"],
                        values=(item["word"], item.get("short_meaning", ""), state.get("wrong_count", 0),
                                state.get("last_wrong_answer") or "—", state.get("next_review", "今天")))
        tree.bind("<Double-1>", lambda _e: self._open_from_tree(tree))

    def _build_stars(self) -> None:
        clear(self.star_tab)
        items = self.service.starred_words()
        top = tk.Frame(self.star_tab)
        top.pack(fill="x", pady=(0, 8))
        tk.Label(top, text=f"{len(items)} 个主动收藏词", font=("Microsoft YaHei UI", 12, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        ttk.Button(top, text="复习生词本", command=lambda: self.start_session("star")).pack(side="right")
        if not items:
            self.empty_state(self.star_tab, "生词本还是空的。",
                             "做题或背词时点“加入生词本”，难词会集中到这里，方便重点复习。")
            return
        tree = ttk.Treeview(self.star_tab, columns=("word", "phonetic", "meaning", "status"),
                            show="headings")
        for key, title, width in [("word", "单词", 150), ("phonetic", "音标", 170),
                                  ("meaning", "释义", 380), ("status", "状态", 100)]:
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="w")
        tree.pack(fill="both", expand=True)
        for item in items:
            tree.insert("", "end", iid=item["word"],
                        values=(item["word"], item.get("phonetic", ""), item.get("short_meaning", ""),
                                self.service.state(item["word"]).get("status", "未学")))
        tree.bind("<Double-1>", lambda _e: self._open_from_tree(tree))

    def _open_from_tree(self, tree) -> None:
        selection = tree.selection()
        if selection:
            self._show_word(selection[0])

    # ================= 词汇表 =================
    def _build_list(self) -> None:
        clear(self.list_tab)
        top = tk.Frame(self.list_tab)
        top.pack(fill="x", pady=(0, 8))
        self.search = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.search, width=28)
        entry.pack(side="left", fill="x", expand=True)
        self.tier = tk.StringVar(value="全部")
        combo = ttk.Combobox(top, textvariable=self.tier, values=TIERS, state="readonly", width=12)
        combo.pack(side="left", padx=8)
        self.status_filter = tk.StringVar(value="全部状态")
        combo2 = ttk.Combobox(top, textvariable=self.status_filter, state="readonly", width=12,
                              values=("全部状态", "未学", "学习中", "待复习", "待巩固", "已掌握"))
        combo2.pack(side="left")
        self.search.trace_add("write", lambda *_: self._fill_list())
        combo.bind("<<ComboboxSelected>>", lambda _e: self._fill_list())
        combo2.bind("<<ComboboxSelected>>", lambda _e: self._fill_list())

        self.list_tree = ttk.Treeview(self.list_tab,
                                      columns=("word", "phonetic", "pos", "meaning", "tier", "status"),
                                      show="headings")
        for key, title, width in [("word", "单词", 120), ("phonetic", "音标", 140), ("pos", "词性", 80),
                                  ("meaning", "释义", 300), ("tier", "分层", 90), ("status", "状态", 80)]:
            self.list_tree.heading(key, text=title)
            self.list_tree.column(key, width=width, anchor="w")
        self.list_tree.pack(fill="both", expand=True)
        self.list_tree.bind("<Double-1>", lambda _e: self._open_from_tree(self.list_tree))
        self._fill_list()

    def _fill_list(self) -> None:
        if not getattr(self, "list_tree", None) or not self.list_tree.winfo_exists():
            return
        self.list_tree.delete(*self.list_tree.get_children())
        query = self.search.get().strip().lower()
        tier = self.tier.get()
        status_wanted = self.status_filter.get()
        count = 0
        for item in self.app.words:
            if query and query not in item["word"].lower() and query not in item.get("meaning", ""):
                continue
            if tier != "全部" and item.get("tier") != tier:
                continue
            state = self.service.state(item["word"])
            if status_wanted != "全部状态" and state.get("status", "未学") != status_wanted:
                continue
            self.list_tree.insert("", "end", iid=item["word"],
                                  values=(item["word"], item.get("phonetic", ""), item.get("pos", ""),
                                          item.get("short_meaning", ""), item.get("tier", ""),
                                          state.get("status", "未学")))
            count += 1
            if count >= 800:
                break

    def _refresh_all(self) -> None:
        self._refresh_wrong() if hasattr(self, "wrong_tab") and self.wrong_tab.winfo_exists() else None
        self._refresh_stars() if hasattr(self, "star_tab") and self.star_tab.winfo_exists() else None

    def _refresh_wrong(self) -> None:
        self._build_wrong()

    def _refresh_stars(self) -> None:
        self._build_stars()

    # ================= 词条详情 =================
    def _show_word(self, word: str) -> None:
        item = self.service.item(word)
        if not item:
            return
        state = self.service.state(word)
        window = tk.Toplevel(self.app)
        window.title(item["word"])
        window.geometry("620x600")
        window.configure(bg=CARD)
        box = card(window, 24)
        box.master.pack(fill="both", expand=True, padx=14, pady=14)
        tk_label(box, item["word"], 26, True, PRIMARY).pack(anchor="w")
        tk_label(box, f"{item.get('phonetic', '')}　{item.get('pos', '')}　{item.get('tier', '')}",
                 11, False, MUTED).pack(anchor="w", pady=(4, 0))
        tk_label(box, item["meaning"], 12, True, TEXT, wraplength=540,
                 justify="left").pack(anchor="w", pady=(16, 10))
        tk_label(box, item.get("example") or "暂未收录语境例句", 10, False, TEXT,
                 wraplength=540, justify="left").pack(anchor="w")
        if item.get("example_zh"):
            tk_label(box, item["example_zh"], 9, False, MUTED, wraplength=540,
                     justify="left").pack(anchor="w", pady=(4, 0))
        info = (f"状态：{state.get('status', '未学')}　阶段：{state.get('stage', 0)}/4　"
                f"见过 {state.get('seen', 0)} 次　答错 {state.get('wrong_count', 0)} 次\n"
                f"下次复习：{state.get('next_review') or '尚未安排'}　"
                f"答对天数：{len(state.get('correct_days', []))}")
        tk_label(box, info, 9, False, MUTED, justify="left").pack(anchor="w", pady=(16, 8))
        modes = state.get("mode_stats", {})
        if modes:
            detail = "　".join(f"{MODE_NAMES.get(key, key)} 对{v.get('correct', 0)}/错{v.get('wrong', 0)}"
                               for key, v in modes.items())
            tk_label(box, detail, 9, False, MUTED).pack(anchor="w")
        row = tk.Frame(box, bg=CARD)
        row.pack(fill="x", pady=(16, 0))
        starred = self.store.is_starred(word)
        ttk.Button(row, text="移出生词本" if starred else "加入生词本",
                   command=lambda: (self.service.toggle_star(word), window.destroy(),
                                    self._refresh_stars())).pack(side="left")
        reduced = state.get("reduced", False)
        ttk.Button(row, text="恢复优先学习" if reduced else "太简单，降低出现频率",
                   command=lambda: (self.service.set_reduced(word, not reduced), window.destroy())
                   ).pack(side="left", padx=8)
        ttk.Button(row, text="关闭", command=window.destroy).pack(side="right")
