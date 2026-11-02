"""真题阅读：选词填空 / 段落匹配 / 仔细阅读，学习模式 + 考试模式 + 错题复盘。

对应重构设计方案 §6：逐题定位、干扰项分析、词汇收藏、错题原因标记与错题重练。
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from services.reading_service import ERROR_REASONS, KIND_NAMES
from ui import (AMBER, AMBER_SOFT, BG, CARD, GREEN, GREEN_SOFT, MUTED, PRIMARY,
                PRIMARY_SOFT, RED, RED_SOFT, STRIP, TEXT, Countdown, ScrollFrame, card,
                clear, tk_label)
from views.base import BaseView


class ReadingView(BaseView):
    def build(self) -> None:
        self.exams = self.app.exams
        self.service = self.app.reading_service
        self.exam_id = self.exams[0]["id"] if self.exams else ""
        self.kind = "cloze"
        self.mode = "learning"
        self.answers: dict = {}
        self.results: list[dict] = []
        self.question_index = 0
        self.passage_index = 0
        self.submitted_questions: set[str] = set()
        self.timer = None
        self.exam_finished = False

        ready = sum(1 for exam in self.exams if exam.get("has_analysis"))
        self.header("真题阅读",
                    f"共 {len(self.exams)} 套真题（{ready} 套已配逐题解析）｜ 学习模式逐题看解析，考试模式整组计时")
        self._build_toolbar()
        self.work = tk.Frame(self.parent, bg=BG)
        self.work.pack(fill="both", expand=True, padx=30, pady=(0, 18))
        self.tabs = ttk.Notebook(self.work)
        self.tabs.pack(fill="both", expand=True)
        self.practice_tab = ttk.Frame(self.tabs)
        self.retry_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.practice_tab, text=" 真题练习 ")
        self.tabs.add(self.retry_tab, text=" 错题重练 ")
        self._load_exam()

    def enter(self, exam_id: str = "", kind: str = "", **_) -> None:
        if exam_id and exam_id in self.service.by_id:
            self.exam_id = exam_id
            self._sync_selectors()
        if kind in KIND_NAMES:
            self.kind = kind
        self._load_exam()

    # ---------------- 工具栏 ----------------
    def _build_toolbar(self) -> None:
        bar = tf = tk.Frame(self.parent, bg=CARD, highlightbackground="#E1E6F0", highlightthickness=1)
        tf.pack(fill="x", padx=30, pady=(0, 10))
        inner = tk.Frame(bar, bg=CARD, padx=14, pady=10)
        inner.pack(fill="x")

        self.exam_var = tk.StringVar()
        self.exam_combo = ttk.Combobox(inner, textvariable=self.exam_var, state="readonly", width=26,
                                       values=[exam["label"] for exam in self.exams])
        self.exam_combo.pack(side="left")
        self.exam_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_exam_change())

        self.kind_var = tk.StringVar(value=KIND_NAMES[self.kind])
        kind_combo = ttk.Combobox(inner, textvariable=self.kind_var, state="readonly", width=12,
                                  values=[KIND_NAMES[k] for k in KIND_NAMES])
        kind_combo.pack(side="left", padx=8)
        kind_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_kind_change())

        self.mode_var = tk.StringVar(value="学习模式")
        mode_box = tk.Frame(inner, bg=CARD)
        mode_box.pack(side="left", padx=6)
        for label in ("学习模式", "考试模式"):
            ttk.Radiobutton(mode_box, text=label, value=label, variable=self.mode_var,
                            command=self._on_mode_change).pack(side="left", padx=(0, 8))

        self.analysis_label = tk.Label(inner, text="", font=("Microsoft YaHei UI", 9),
                                       fg=MUTED, bg=CARD)
        self.analysis_label.pack(side="left", padx=8)
        self.timer_label = tk.Label(inner, text="", font=("Microsoft YaHei UI", 12, "bold"),
                                    fg=MUTED, bg=CARD)
        self.timer_label.pack(side="right", padx=(8, 0))
        self.timer_button = ttk.Button(inner, text="计时", command=self._toggle_timer)
        self.timer_button.pack(side="right")

    def _sync_selectors(self) -> None:
        for exam in self.exams:
            if exam["id"] == self.exam_id:
                self.exam_var.set(exam["label"])
                break
        self.kind_var.set(KIND_NAMES[self.kind])

    def _on_exam_change(self) -> None:
        label = self.exam_var.get()
        for exam in self.exams:
            if exam["label"] == label:
                self.exam_id = exam["id"]
                break
        self._load_exam()

    def _on_kind_change(self) -> None:
        for key, name in KIND_NAMES.items():
            if name == self.kind_var.get():
                self.kind = key
                break
        self._load_exam()

    def _on_mode_change(self) -> None:
        self.mode = "learning" if self.mode_var.get() == "学习模式" else "exam"
        self._reset_session()

    def _toggle_timer(self) -> None:
        if self.timer is None:
            return
        running = self.timer.toggle()
        self.timer_button.configure(text="暂停" if running else "继续")

    def _reset_session(self) -> None:
        self.answers = {}
        self.results = []
        self.question_index = 0
        self.submitted_questions = set()
        self.exam_finished = False
        minutes = 10 if self.kind == "cloze" else (12 if self.kind == "matching" else 20)
        self.timer = Countdown(self.timer_label, minutes, self._time_up)
        self.timer_button.configure(text="计时")
        self._render()

    def _time_up(self) -> None:
        self.timer_button.configure(text="计时")
        messagebox.showinfo("时间到", "建议时间已到。可以先交卷，再逐题复盘。", parent=self.app)

    # ---------------- 渲染 ----------------
    def _exam(self) -> dict:
        return self.service.by_id[self.exam_id]

    def _load_exam(self) -> None:
        self._sync_selectors()
        if getattr(self, "analysis_label", None) is not None and self.exams:
            exam = self.service.by_id[self.exam_id]
            if exam.get("has_analysis"):
                self.analysis_label.configure(text="解析已就绪", fg=GREEN)
            else:
                self.analysis_label.configure(text="解析补充中（答案与判分可用）", fg=AMBER)
        self._reset_session()
        self._fill_retry()

    def _render(self) -> None:
        clear(self.practice_tab)
        if not self.exams:
            self.empty_state(self.practice_tab, "还没有内置真题。", "把真题 JSON 放进 content/ 后重新打开。")
            return
        if self.kind == "cloze":
            self._render_cloze()
        elif self.kind == "matching":
            self._render_matching()
        else:
            self._render_careful()

    # ---- 选词填空 ----
    def _render_cloze(self) -> None:
        exam = self._exam()
        cloze = exam["cloze"]
        pane = tk.Frame(self.practice_tab, bg=BG)
        pane.pack(fill="both", expand=True)
        pane.columnconfigure(0, weight=3)
        pane.columnconfigure(1, weight=2)
        left = card(pane, 16)
        left.master.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        right = card(pane, 18)
        right.master.grid(row=0, column=1, sticky="nsew")

        head = tk.Frame(left, bg=CARD)
        head.pack(fill="x", pady=(0, 8))
        tk_label(head, f"{exam['label']} · 选词填空", 12, True).pack(anchor="w")
        tk_label(head, f"共 {len(cloze['blanks'])} 空 · 建议 10 分钟", 9, False, MUTED).pack(
            anchor="w", pady=(2, 0))
        if exam.get("answer_note"):
            tk_label(left, exam["answer_note"], 9, False, AMBER, CARD).pack(anchor="w", pady=(0, 6))
        scroll = ScrollFrame(left, CARD)
        scroll.pack(fill="both", expand=True)
        body = scroll.inner
        passage = tk.Text(body, wrap="word", font=("Microsoft YaHei UI", 11), bg=CARD, fg=TEXT,
                          relief="flat", padx=4, pady=4, spacing1=3, spacing3=9, height=26,
                          borderwidth=0)
        passage.insert("1.0", cloze["passage"])
        passage.configure(state="disabled")
        passage.pack(fill="both", expand=True)
        if cloze.get("passage_zh"):
            ttk.Button(left, text="显示 / 隐藏全文参考译文",
                       command=lambda: self._show_text("选词填空 · 参考译文", cloze["passage_zh"])
                       ).pack(anchor="w", pady=(8, 0))

        tk_label(right, "选项词库", 13, True).pack(anchor="w")
        bank = tk.Frame(right, bg=CARD)
        bank.pack(fill="x", pady=(6, 12))
        for i, entry in enumerate(cloze["wordbank"]):
            tk_label(bank, f"{entry['letter']}) {entry['word']}", 10, False, TEXT, CARD,
                     anchor="w").grid(row=i // 3, column=i % 3, sticky="w", padx=(0, 14), pady=2)

        tk_label(right, "为每个空选择字母", 13, True).pack(anchor="w")
        grid = tk.Frame(right, bg=CARD)
        grid.pack(fill="x", pady=(8, 10))
        letters = [entry["letter"] for entry in cloze["wordbank"]]
        self.cloze_vars: dict[str, tk.StringVar] = {}
        for i, blank in enumerate(cloze["blanks"]):
            row = tk.Frame(grid, bg=CARD)
            row.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 14), pady=4)
            tk_label(row, f"{blank['num']}", 10, True, PRIMARY).pack(side="left")
            var = tk.StringVar(value=self.answers.get(str(blank["num"]), ""))
            combo = ttk.Combobox(row, textvariable=var, values=letters, state="readonly", width=5)
            combo.pack(side="left", padx=6)
            combo.bind("<<ComboboxSelected>>",
                       lambda _e, k=str(blank["num"]), v=var: self.answers.__setitem__(k, v.get()))
            self.cloze_vars[str(blank["num"])] = var

        actions = tk.Frame(right, bg=CARD)
        actions.pack(fill="x", pady=(6, 0))
        ttk.Button(actions, text="提交并查看解析", style="Primary.TButton",
                   command=self._submit_cloze).pack(side="left")
        ttk.Button(actions, text="重做本组", command=self._reset_session).pack(side="left", padx=8)

        results_scroll = ScrollFrame(right, CARD)
        results_scroll.pack(fill="both", expand=True, pady=(10, 0))
        self.cloze_result_area = results_scroll.inner
        self._render_cloze_results()

    def _render_cloze_results(self) -> None:
        area = getattr(self, "cloze_result_area", None)
        if area is None or not area.winfo_exists() or not self.results:
            return
        clear(area)
        score = sum(1 for item in self.results if item["correct"])
        tk_label(area, f"本轮成绩 {score} / {len(self.results)}", 12, True,
                 GREEN if score == len(self.results) else PRIMARY).pack(anchor="w", pady=(0, 8))
        for item in self.results:
            self._result_row(area, item, prefix=f"{item['num']}")

    # ---- 段落匹配 ----
    def _render_matching(self) -> None:
        exam = self._exam()
        matching = exam["matching"]
        if not matching.get("complete", True):
            box = card(self.practice_tab, 24)
            box.master.pack(fill="both", expand=True)
            tk_label(box, "本套段落匹配暂不提供", 16, True, AMBER).pack(anchor="w", pady=(10, 6))
            tk_label(box, matching.get("issue") or "来源文本不完整。", 11, False, TEXT,
                     wraplength=760, justify="left").pack(anchor="w")
            tk_label(box, "选词填空与仔细阅读可以正常练习；换一套真题做段落匹配即可。",
                     10, False, MUTED).pack(anchor="w", pady=(10, 0))
            return
        pane = tk.Frame(self.practice_tab, bg=BG)
        pane.pack(fill="both", expand=True)
        pane.columnconfigure(0, weight=3)
        pane.columnconfigure(1, weight=2)
        left = card(pane, 16)
        left.master.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        right = card(pane, 18)
        right.master.grid(row=0, column=1, sticky="nsew")

        head = tk.Frame(left, bg=CARD)
        head.pack(fill="x", pady=(0, 8))
        tk_label(head, f"{matching['title']}", 13, True).pack(side="left")
        tk_label(head, "段落匹配", 9, False, MUTED).pack(side="right")
        scroll = ScrollFrame(left, CARD)
        scroll.pack(fill="both", expand=True)
        text = readonly_text_widget(scroll.inner, self._article_text(matching), 11)
        text.pack(fill="both", expand=True)
        if matching.get("article_zh"):
            ttk.Button(left, text="显示 / 隐藏全文参考译文",
                       command=lambda: self._show_text("段落匹配 · 参考译文", matching["article_zh"])
                       ).pack(anchor="w", pady=(8, 0))

        tk_label(right, "为每句话选择所属段落", 13, True).pack(anchor="w")
        tk_label(right, "同一个段落可以被选多次", 9, False, MUTED).pack(anchor="w", pady=(2, 8))
        grid = tk.Frame(right, bg=CARD)
        grid.pack(fill="x")
        labels = [p["label"] for p in matching["paragraphs"]]
        self.match_vars: dict[str, tk.StringVar] = {}
        for i, statement in enumerate(matching["statements"]):
            row = tk.Frame(grid, bg=CARD)
            row.pack(fill="x", pady=3)
            tk_label(row, f"{statement['num']}.", 10, True, PRIMARY, width=4).pack(side="left")
            var = tk.StringVar(value=self.answers.get(str(statement["num"]), ""))
            box = ttk.Combobox(row, textvariable=var, values=labels, state="readonly", width=4)
            box.pack(side="left")
            box.bind("<<ComboboxSelected>>",
                     lambda _e, k=str(statement["num"]), v=var: self.answers.__setitem__(k, v.get()))
            self.match_vars[str(statement["num"])] = var
            tk_label(row, statement["statement"], 9, False, TEXT, CARD, wraplength=330,
                     justify="left").pack(side="left", padx=8)

        actions = tk.Frame(right, bg=CARD)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="提交并查看解析", style="Primary.TButton",
                   command=self._submit_matching).pack(side="left")
        ttk.Button(actions, text="重做本组", command=self._reset_session).pack(side="left", padx=8)
        results_scroll = ScrollFrame(right, CARD)
        results_scroll.pack(fill="both", expand=True, pady=(10, 0))
        self.match_result_area = results_scroll.inner
        self._render_match_results()

    @staticmethod
    def _article_text(matching: dict) -> str:
        parts = []
        for paragraph in matching["paragraphs"]:
            parts.append(f"{paragraph['label']}) {paragraph['text']}")
        return "\n\n".join(parts)

    def _render_match_results(self) -> None:
        area = getattr(self, "match_result_area", None)
        if area is None or not area.winfo_exists() or not self.results:
            return
        clear(area)
        score = sum(1 for item in self.results if item["correct"])
        tk_label(area, f"本轮成绩 {score} / {len(self.results)}", 12, True,
                 GREEN if score == len(self.results) else PRIMARY).pack(anchor="w", pady=(0, 8))
        for item in self.results:
            self._result_row(area, item, prefix=str(item["num"]))

    # ---- 仔细阅读 ----
    def _render_careful(self) -> None:
        exam = self._exam()
        if not exam["careful"]:
            self.empty_state(self.practice_tab, "这套真题没有仔细阅读。")
            return
        passage = exam["careful"][self.passage_index]
        pane = tk.Frame(self.practice_tab, bg=BG)
        pane.pack(fill="both", expand=True)
        pane.columnconfigure(0, weight=3)
        pane.columnconfigure(1, weight=2)
        left = card(pane, 16)
        left.master.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        right = card(pane, 20)
        right.master.grid(row=0, column=1, sticky="nsew")

        head = tk.Frame(left, bg=CARD)
        head.pack(fill="x", pady=(0, 8))
        tk_label(head, f"{exam['label']} · {passage['title']}", 12, True).pack(side="left")
        switch = tk.Frame(left, bg=CARD)
        switch.pack(fill="x", anchor="w", pady=(0, 6))
        for i, other in enumerate(exam["careful"]):
            ttk.Button(switch, text=other["title"], width=12,
                       style="Primary.TButton" if i == self.passage_index else "TButton",
                       command=lambda idx=i: self._switch_passage(idx)).pack(side="left", padx=(0, 6))

        scroll = ScrollFrame(left, CARD)
        scroll.pack(fill="both", expand=True)
        text = readonly_text_widget(scroll.inner, self._passage_text(passage), 11)
        text.pack(fill="both", expand=True)
        bottom = tk.Frame(left, bg=CARD)
        bottom.pack(fill="x", pady=(8, 0))
        if passage.get("passage_zh"):
            ttk.Button(bottom, text="全文参考译文（默认隐藏）",
                       command=lambda: self._show_text(f"{passage['title']} · 参考译文", passage["passage_zh"])
                       ).pack(side="left")
        if passage.get("vocabulary"):
            ttk.Button(bottom, text="重点词汇与长难句",
                       command=lambda: self._show_study(passage)).pack(side="left", padx=8)

        self._render_careful_questions(right, passage)

    def _switch_passage(self, index: int) -> None:
        self.passage_index = index
        self.question_index = 0
        self._render()

    def _render_careful_questions(self, parent, passage: dict) -> None:
        tk_label(parent, f"{passage['title']} · 共 {len(passage['questions'])} 题", 12, True).pack(anchor="w")
        if self.mode == "exam":
            tk_label(parent, "考试模式：全部作答后交卷，交卷前不显示答案", 9, False, MUTED).pack(anchor="w", pady=(2, 10))
            self._render_careful_exam(parent, passage)
            return

        question = passage["questions"][self.question_index]
        top = tk.Frame(parent, bg=CARD)
        top.pack(fill="x")
        tk_label(top, f"第 {self.question_index + 1} / {len(passage['questions'])} 题", 10, True,
                 PRIMARY).pack(side="left")
        submitted = str(question["num"]) in self.submitted_questions
        if submitted:
            chosen = self.answers.get(str(question["num"]), "")
            tk_label(top, "回答正确" if chosen == question["answer"] else "回答错误", 10, True,
                     GREEN if chosen == question["answer"] else RED).pack(side="right")

        scroll = ScrollFrame(parent, CARD)
        scroll.pack(fill="both", expand=True, pady=(10, 0))
        body = scroll.inner
        tk_label(body, question["stem"], 11, True, TEXT, wraplength=380, justify="left").pack(
            anchor="w", pady=(0, 10))
        var = tk.StringVar(value=self.answers.get(str(question["num"]), ""))
        for i, option in enumerate(question["options"]):
            bg, fg = CARD, TEXT
            if submitted:
                if self.letter(i) == question["answer"]:
                    bg, fg = GREEN_SOFT, GREEN
                elif self.letter(i) == self.answers.get(str(question["num"])):
                    bg, fg = RED_SOFT, RED
            button = tk.Radiobutton(body, text=f"{self.letter(i)}. {option}", variable=var,
                                    value=self.letter(i), anchor="w", justify="left", wraplength=370,
                                    font=("Microsoft YaHei UI", 10), bg=bg, fg=fg, activebackground=bg,
                                    selectcolor=bg, padx=4, pady=8,
                                    command=lambda qnum=str(question["num"]): self._pick_careful(qnum, var.get()))
            button.pack(fill="x", pady=2)
            if submitted:
                button.configure(state="disabled")

        controls = tk.Frame(parent, bg=CARD)
        controls.pack(fill="x", pady=(8, 0))
        if not submitted:
            ttk.Button(controls, text="提交本题", style="Primary.TButton",
                       command=lambda: self._submit_careful_question(passage, question)).pack(side="left")
        if submitted:
            if self.question_index < len(passage["questions"]) - 1:
                ttk.Button(controls, text="下一题", style="Primary.TButton",
                           command=lambda: self._move_question(1)).pack(side="left")
            else:
                ttk.Button(controls, text="提交本篇", style="Primary.TButton",
                           command=lambda: self._submit_careful_passage(passage)).pack(side="left")
        ttk.Button(controls, text="上一题", command=lambda: self._move_question(-1)).pack(side="right")

        if submitted:
            self._render_explanation(body, self._careful_result(passage, question))

    def _render_careful_exam(self, parent, passage: dict) -> None:
        scroll = ScrollFrame(parent, CARD)
        scroll.pack(fill="both", expand=True)
        body = scroll.inner
        self.exam_vars: dict[str, tk.StringVar] = {}
        for question in passage["questions"]:
            tk_label(body, f"{question['num']}. {question['stem']}", 10, True, TEXT,
                     wraplength=380, justify="left").pack(anchor="w", pady=(10, 4))
            var = tk.StringVar(value=self.answers.get(str(question["num"]), ""))
            self.exam_vars[str(question["num"])] = var
            for i, option in enumerate(question["options"]):
                tk.Radiobutton(body, text=f"{self.letter(i)}. {option}", variable=var,
                               value=self.letter(i), anchor="w", justify="left", wraplength=370,
                               font=("Microsoft YaHei UI", 9), bg=CARD, fg=TEXT,
                               activebackground=CARD, selectcolor=CARD, padx=2, pady=4,
                               command=lambda k=str(question["num"]), v=var: self.answers.__setitem__(k, v.get())
                               ).pack(fill="x")
        actions = tk.Frame(parent, bg=CARD)
        actions.pack(fill="x", pady=(8, 0))
        if not self.results:
            ttk.Button(actions, text="交卷并评分", style="Primary.TButton",
                       command=lambda: self._submit_careful_passage(passage)).pack(side="left")
            ttk.Button(actions, text="重做本组", command=self._reset_session).pack(side="left", padx=8)
        else:
            score = sum(1 for item in self.results if item["correct"])
            tk_label(actions, f"成绩 {score} / {len(self.results)}", 12, True, PRIMARY).pack(side="left")
            ttk.Button(actions, text="查看解析", command=self._show_full_review).pack(side="right")

    def _pick_careful(self, qnum: str, letter_value: str) -> None:
        self.answers[qnum] = letter_value

    def _submit_careful_question(self, passage: dict, question: dict) -> None:
        if not self.answers.get(str(question["num"])):
            messagebox.showinfo("还没选答案", "先选一个选项，再提交本题。", parent=self.app)
            return
        results = self.service.grade_careful(self.exam_id, passage["id"], self.answers)
        self.submitted_questions.add(str(question["num"]))
        self._record_partial(results, kind="careful")
        self._render()

    def _submit_careful_passage(self, passage: dict) -> None:
        missing = [q["num"] for q in passage["questions"] if not self.answers.get(str(q["num"]))]
        if missing and self.mode == "learning":
            if not messagebox.askyesno("还有未作答", f"还有 {len(missing)} 题没选，仍然提交吗？", parent=self.app):
                return
        results = self.service.grade_careful(self.exam_id, passage["id"], self.answers)
        seconds = self.timer.used_seconds() if self.timer else 0
        self.service.record(self.exam_id, "careful", results, seconds, mode=self.mode, sub_id=passage["id"])
        self.results = results
        self.exam_finished = True
        self._after_submit(results, passage["id"])
        self._render()

    def _record_partial(self, results: list[dict], kind: str) -> None:
        for item in results:
            if item["qid"] not in self.submitted_questions and str(item["num"]) not in self.submitted_questions:
                continue
            self.store.record_answer(item["key"], item["prompt"], item["answer"], item["chosen"],
                                     item["correct"], KIND_NAMES[kind], exam_id=self.exam_id,
                                     qid=str(item["num"]))

    def _careful_result(self, passage: dict, question: dict) -> dict:
        chosen = self.answers.get(str(question["num"]), "")
        merged = next((item for item in self.results if str(item["num"]) == str(question["num"])), None)
        if merged:
            return merged
        return {
            "key": f"{self.exam_id}-careful-{question['num']}", "num": question["num"],
            "prompt": question["stem"], "answer": question["answer"], "chosen": chosen or "未作答",
            "correct": chosen == question["answer"],
            "explanation": question.get("explanation", ""),
            "evidence": question.get("evidence_quote", ""),
            "evidence_paragraph": question.get("evidence_paragraph", 0),
            "distractors": question.get("distractors", {}),
            "verified": question.get("verified", None),
        }

    def _move_question(self, step: int) -> None:
        exam = self._exam()
        passage = exam["careful"][self.passage_index]
        self.question_index = max(0, min(len(passage["questions"]) - 1, self.question_index + step))
        self._render()

    # ---------------- 提交 ---------------- #
    def _submit_cloze(self) -> None:
        if not self.answers:
            messagebox.showinfo("还没有作答", "先给每个空选一个字母。", parent=self.app)
            return
        results = self.service.grade_cloze(self.exam_id, self.answers)
        seconds = self.timer.used_seconds() if self.timer else 0
        self.service.record(self.exam_id, "cloze", results, seconds, mode=self.mode)
        self.results = results
        self._after_submit(results, "cloze")
        self._render()

    def _submit_matching(self) -> None:
        if not self.answers:
            messagebox.showinfo("还没有作答", "先给每句话选一个段落。", parent=self.app)
            return
        results = self.service.grade_matching(self.exam_id, self.answers)
        seconds = self.timer.used_seconds() if self.timer else 0
        self.service.record(self.exam_id, "matching", results, seconds, mode=self.mode)
        self.results = results
        self._after_submit(results, "matching")
        self._render()

    def _after_submit(self, results: list[dict], kind: str) -> None:
        score = sum(1 for item in results if item["correct"])
        messagebox.showinfo("本组成绩", f"答对 {score} / {len(results)} 题。\n解析已显示在下方，错题可以标记原因。",
                            parent=self.app)
        self._fill_retry()
        self.refresh()

    def _show_full_review(self) -> None:
        window = tk.Toplevel(self.app)
        window.title("本篇解析")
        window.geometry("760x720")
        window.configure(bg=CARD)
        scroll = ScrollFrame(window, CARD)
        scroll.pack(fill="both", expand=True, padx=14, pady=14)
        body = scroll.inner
        for item in self.results:
            self._render_explanation(body, item)
        ttk.Button(body, text="关闭", command=window.destroy).pack(anchor="e", pady=10)

    # ---------------- 解析块 ---------------- #
    def _result_row(self, parent, item: dict, prefix: str = "") -> None:
        color = GREEN if item["correct"] else RED
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=(0, 6))
        tk_label(row, f"{'✓' if item['correct'] else '✗'} {prefix}", 10, True, color).pack(side="left")
        tk_label(row, f"答案 {item['answer']} · 你选 {item['chosen']}", 9, False, MUTED).pack(side="left", padx=8)
        if not item["correct"]:
            tags = tk.Frame(row, bg=CARD)
            tags.pack(side="right")
            for reason in ERROR_REASONS:
                ttk.Button(tags, text=reason, width=8,
                           command=lambda k=item["key"], r=reason: self._tag(k, r)).pack(side="left", padx=1)
        self._render_explanation(parent, item, compact=True)

    def _render_explanation(self, parent, item: dict, compact: bool = False) -> None:
        box = tk.Frame(parent, bg=STRIP, padx=12, pady=10)
        box.pack(fill="x", pady=(2, 10))
        tag = ""
        my_answer = item.get("my_answer")
        if my_answer:
            if my_answer == item.get("answer"):
                tag = " · 已独立作答复核"
            else:
                tag = " · 独立作答与答案不一致，请重点核对"
        if item.get("answer_source") == "已核对修正":
            tag += " · 本答案已按公开答案修正"
        tk_label(box, f"正确答案：{item['answer']}{tag}", 10, True, PRIMARY, STRIP,
                 wraplength=580, justify="left").pack(anchor="w")
        if item.get("evidence"):
            paragraph = item.get("evidence_paragraph")
            location = f"（第 {paragraph} 段）" if paragraph else ""
            tk_label(box, f"原文定位{location}：{item['evidence']}", 9, False, TEXT, STRIP,
                     wraplength=580, justify="left").pack(anchor="w", pady=(6, 0))
        if item.get("explanation"):
            tk_label(box, item["explanation"], 9, False, TEXT, STRIP,
                     wraplength=580, justify="left").pack(anchor="w", pady=(6, 0))
        distractors = item.get("distractors") or {}
        if distractors:
            tk_label(box, "干扰项分析", 9, True, MUTED, STRIP).pack(anchor="w", pady=(8, 2))
            for letter_value, reason in distractors.items():
                tk_label(box, f"{letter_value}　{reason}", 9, False, MUTED, STRIP,
                         wraplength=580, justify="left").pack(anchor="w")
        if not item.get("explanation") and not item.get("evidence"):
            tk_label(box, "这套真题的逐题解析还在补充中（先保证答案与原文准确）。", 9, False,
                     MUTED, STRIP).pack(anchor="w", pady=(6, 0))

    def _tag(self, key: str, reason: str) -> None:
        self.service.add_error_tag(key, reason)
        messagebox.showinfo("已记录", f"已标记错误原因：{reason}", parent=self.app)

    # ---------------- 错题重练 ---------------- #
    def _fill_retry(self) -> None:
        clear(self.retry_tab)
        queue = self.service.retry_queue()
        top = tk.Frame(self.retry_tab)
        top.pack(fill="x", pady=(6, 8))
        tk.Label(top, text=f"{len(queue)} 道待重练错题", font=("Microsoft YaHei UI", 12, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        if queue:
            ttk.Button(top, text="开始错题重练", style="Primary.TButton",
                       command=lambda: self._start_retry(queue)).pack(side="right")
        if not queue:
            self.empty_state(self.retry_tab, "暂时没有待重练的错题。",
                             "做错的阅读题会出现在这里，重练时可以标记错误原因。")
            return
        tree = ttk.Treeview(self.retry_tab, columns=("kind", "num", "prompt", "answer", "chosen", "reason"),
                            show="headings")
        for key, title, width in [("kind", "题型", 90), ("num", "题号", 60), ("prompt", "题目", 330),
                                  ("answer", "答案", 70), ("chosen", "我的答案", 80), ("reason", "错误原因", 90)]:
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="w")
        tree.pack(fill="both", expand=True)
        for item in queue:
            reason = self.store.error_tag(f"{item['exam_id']}-{item['kind']}-{item['num']}")
            tree.insert("", "end", values=(KIND_NAMES[item["kind"]], item["num"],
                                           item["stem"][:60], item["answer"], item["chosen"],
                                           reason or "—"))

    def _start_retry(self, queue: list[dict]) -> None:
        window = tk.Toplevel(self.app)
        window.title("错题重练")
        window.geometry("760x620")
        window.configure(bg=CARD)
        box = card(window, 20)
        box.master.pack(fill="both", expand=True, padx=14, pady=14)
        state = {"index": 0, "correct": 0}
        frame = tk.Frame(box, bg=CARD)
        frame.pack(fill="both", expand=True)

        def render() -> None:
            clear(frame)
            if state["index"] >= len(queue):
                tk_label(frame, f"重练完成：答对 {state['correct']} / {len(queue)}", 16, True, PRIMARY).pack(pady=40)
                tk_label(frame, "重练答对表示“本次已纠正”，仍要等后续到期复习通过才算真正掌握。",
                         10, False, MUTED).pack()
                ttk.Button(frame, text="关闭", style="Primary.TButton",
                           command=lambda: (window.destroy(), self._fill_retry())).pack(pady=20)
                return
            item = queue[state["index"]]
            tk_label(frame, f"{KIND_NAMES[item['kind']]} · {item['num']}　（第 {state['index'] + 1} / {len(queue)} 题）",
                     10, True, PRIMARY).pack(anchor="w")
            tk_label(frame, item["stem"], 12, True, TEXT, wraplength=660, justify="left").pack(anchor="w", pady=(10, 12))
            options = item.get("options") or []
            feedback = tk.Frame(frame, bg=CARD)
            feedback.pack(fill="x")
            var = tk.StringVar()
            for i, option in enumerate(options):
                tk.Radiobutton(frame, text=f"{self.letter(i)}. {option}", variable=var,
                               value=self.letter(i), anchor="w", justify="left", wraplength=640,
                               font=("Microsoft YaHei UI", 10), bg=CARD, fg=TEXT, selectcolor=CARD,
                               padx=4, pady=6).pack(fill="x")

            def check() -> None:
                chosen = var.get()
                correct = chosen == item["answer"]
                if correct:
                    state["correct"] += 1
                self.store.record_answer(f"{item['exam_id']}-{item['kind']}-{item['num']}",
                                         item["stem"], item["answer"], chosen or "未作答", correct,
                                         KIND_NAMES[item["kind"]], exam_id=item["exam_id"],
                                         qid=str(item["num"]))
                clear(feedback)
                tk_label(feedback, "回答正确" if correct else f"回答错误 · 正确答案 {item['answer']}",
                         11, True, GREEN if correct else RED).pack(anchor="w", pady=8)
                if item.get("evidence"):
                    tk_label(feedback, f"原文定位：{item['evidence']}", 9, False, TEXT,
                             wraplength=660, justify="left").pack(anchor="w")
                if item.get("explanation"):
                    tk_label(feedback, item["explanation"], 9, False, TEXT,
                             wraplength=660, justify="left").pack(anchor="w", pady=(4, 0))
                ttk.Button(feedback, text="下一题", style="Primary.TButton",
                           command=lambda: (state.__setitem__("index", state["index"] + 1), render())
                           ).pack(anchor="e", pady=8)

            if item["kind"] == "cloze":
                tk_label(frame, f"提示：正确词 = {item['word']}", 9, False, MUTED).pack(anchor="w", pady=(0, 6))
                ttk.Button(frame, text="核对答案", style="Primary.TButton", command=check).pack(anchor="w")
            else:
                ttk.Button(frame, text="提交本题", style="Primary.TButton", command=check).pack(anchor="w", pady=(8, 0))

        render()

    # ---------------- 辅助弹窗 ---------------- #
    def _show_text(self, title: str, content: str) -> None:
        window = tk.Toplevel(self.app)
        window.title(title)
        window.geometry("720x620")
        window.configure(bg=CARD)
        box = card(window, 20)
        box.master.pack(fill="both", expand=True, padx=14, pady=14)
        tk_label(box, title, 14, True, PRIMARY).pack(anchor="w", pady=(0, 8))
        text = readonly_text_widget(box, content, 11)
        text.pack(fill="both", expand=True)
        ttk.Button(box, text="关闭", command=window.destroy).pack(anchor="e", pady=(8, 0))

    def _show_study(self, passage: dict) -> None:
        window = tk.Toplevel(self.app)
        window.title(f"{passage['title']} · 重点词汇与长难句")
        window.geometry("720x640")
        window.configure(bg=CARD)
        box = card(window, 20)
        box.master.pack(fill="both", expand=True, padx=14, pady=14)
        tk_label(box, "重点词汇", 13, True, PRIMARY).pack(anchor="w")
        for entry in passage.get("vocabulary", []):
            note = f"　{entry.get('note')}" if entry.get("note") else ""
            tk_label(box, f"• {entry.get('word')}　{entry.get('meaning')}{note}", 10, False, TEXT,
                     wraplength=650, justify="left").pack(anchor="w", pady=2)
        sentence = passage.get("long_sentence") or {}
        if sentence:
            tk_label(box, "长难句拆解", 13, True, PRIMARY).pack(anchor="w", pady=(14, 4))
            tk_label(box, sentence.get("sentence", ""), 10, False, TEXT, wraplength=650,
                     justify="left").pack(anchor="w")
            tk_label(box, sentence.get("analysis", ""), 10, False, MUTED, wraplength=650,
                     justify="left").pack(anchor="w", pady=(6, 0))
        ttk.Button(box, text="关闭", command=window.destroy).pack(anchor="e", pady=(10, 0))

    def _passage_text(self, passage: dict) -> str:
        return "\n\n".join(passage["paragraphs"])


def readonly_text_widget(parent, content: str, size: int = 11) -> tk.Text:
    widget = tk.Text(parent, wrap="word", font=("Microsoft YaHei UI", size), bg=CARD, fg=TEXT,
                     relief="flat", padx=6, pady=6, spacing1=3, spacing3=9, borderwidth=0)
    widget.insert("1.0", content)
    widget.configure(state="disabled")
    return widget


def readonly_text(parent, content, size: int = 11):  # 兼容旧调用
    return readonly_text_widget(parent, content, size)
