"""设置与数据：学习目标、导入、备份、重置（重构设计方案 §10）。"""
from __future__ import annotations

import csv
import json
import os
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from repositories.store import SCHEMA, user_data_dir
from ui import (AMBER, BG, CARD, GREEN, MUTED, PRIMARY, PRIMARY_SOFT, RED, STRIP, TEXT,
                ScrollFrame, card, clear, tk_label)
from views.base import BaseView


class SettingsView(BaseView):
    def build(self) -> None:
        self.header("设置与数据", "每日目标、真题导入、学习记录备份；所有数据只保存在本机")
        scroll = ScrollFrame(self.parent, BG)
        scroll.pack(fill="both", expand=True, padx=30, pady=(0, 18))
        body = scroll.inner
        self._build_goal(body)
        self._build_import(body)
        self._build_data(body)
        self._build_about(body)
        self.refresh()

    # ---------------- 学习目标 ----------------
    def _build_goal(self, body) -> None:
        box = card(body, 20)
        box.master.pack(fill="x", pady=(0, 12))
        tk_label(box, "学习目标", 14, True).pack(anchor="w", pady=(0, 4))
        tk_label(box, "新词目标是上限，不是必须完成的数量；到期复习优先。", 9, False, MUTED).pack(
            anchor="w", pady=(0, 12))
        settings = self.store.settings
        row = tk.Frame(box, bg=CARD)
        row.pack(fill="x", pady=4)
        tk_label(row, "称呼", 10, False, MUTED, CARD, width=10, anchor="w").pack(side="left")
        self.name_var = tk.StringVar(value=settings.get("user_name", "同学"))
        ttk.Entry(row, textvariable=self.name_var, width=16).pack(side="left")

        row2 = tk.Frame(box, bg=CARD)
        row2.pack(fill="x", pady=4)
        tk_label(row2, "每日新词", 10, False, MUTED, CARD, width=10, anchor="w").pack(side="left")
        self.words_var = tk.IntVar(value=int(settings.get("daily_words", 20)))
        ttk.Spinbox(row2, from_=5, to=100, increment=5, textvariable=self.words_var, width=8).pack(side="left")
        tk_label(row2, "每日学习分钟", 10, False, MUTED, CARD, width=12, anchor="w").pack(side="left", padx=(20, 0))
        self.minutes_var = tk.IntVar(value=int(settings.get("study_minutes", 75)))
        ttk.Spinbox(row2, from_=20, to=300, increment=5, textvariable=self.minutes_var, width=8).pack(side="left")
        tk_label(row2, "阅读建议分钟", 10, False, MUTED, CARD, width=12, anchor="w").pack(side="left", padx=(20, 0))
        self.reading_var = tk.IntVar(value=int(settings.get("reading_minutes", 35)))
        ttk.Spinbox(row2, from_=10, to=90, increment=5, textvariable=self.reading_var, width=8).pack(side="left")

        ttk.Button(box, text="保存设置", style="Primary.TButton", command=self._save_settings).pack(
            anchor="e", pady=(14, 0))

    def _save_settings(self) -> None:
        try:
            payload = {
                "user_name": self.name_var.get().strip() or "同学",
                "daily_words": max(5, int(self.words_var.get())),
                "study_minutes": max(20, int(self.minutes_var.get())),
                "reading_minutes": max(10, int(self.reading_var.get())),
            }
        except (tk.TclError, ValueError):
            messagebox.showerror("数值不对", "请填写整数。", parent=self.app)
            return
        self.store.update_settings(**payload)
        messagebox.showinfo("已保存", "新的学习目标已生效。", parent=self.app)
        self.refresh()

    # ---------------- 内容导入 ----------------
    def _build_import(self, body) -> None:
        box = card(body, 20)
        box.master.pack(fill="x", pady=12)
        tk_label(box, "内容导入", 14, True).pack(anchor="w")
        tk_label(box, "单词 CSV 列：word, phonetic, pos, meaning, example, example_zh（word 与 meaning 必填）。\n"
                     "真题 JSON 支持选词填空 / 段落匹配 / 仔细阅读；也可以直接放 content/ 目录后重启。",
                 9, False, MUTED, justify="left", wraplength=860).pack(anchor="w", pady=(6, 12))
        row = tk.Frame(box, bg=CARD)
        row.pack(fill="x")
        ttk.Button(row, text="导入单词 CSV", command=self._import_words).pack(side="left")
        ttk.Button(row, text="导入真题 JSON", command=self._import_exams).pack(side="left", padx=8)
        ttk.Button(row, text="导出真题模板", command=self._export_template).pack(side="left")

    def _import_words(self) -> None:
        path = filedialog.askopenfilename(title="选择词表 CSV", filetypes=[("CSV 词表", "*.csv")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            known = {word["word"].lower() for word in self.app.words}
            imported = []
            for index, row in enumerate(rows):
                word = (row.get("word") or "").strip()
                meaning = (row.get("meaning") or "").strip()
                if not word or not meaning or word.lower() in known:
                    continue
                known.add(word.lower())
                imported.append({
                    "id": f"custom-{len(self.app.words) + index + 1}",
                    "word": word,
                    "phonetic": row.get("phonetic", ""),
                    "pos": row.get("pos", ""),
                    "meaning": meaning,
                    "short_meaning": meaning.split("；")[0].split(";")[0][:40],
                    "tier": "六级拓展",
                    "example": row.get("example", "") or f"Review {word} in your own sentence.",
                    "example_zh": row.get("example_zh", "") or "请自己造一个句子巩固这个词。",
                })
            if not imported:
                raise ValueError("没有新增单词：请检查列名，或这些词已在词库里。")
            self.store.data.setdefault("imported_words", []).extend(imported)
            self.store.save()
            self.app.reload_content()
            messagebox.showinfo("导入成功", f"已导入 {len(imported)} 个单词，重新进入词汇模块即可学习。",
                                parent=self.app)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("导入失败", str(exc), parent=self.app)

    def _import_exams(self) -> None:
        path = filedialog.askopenfilename(title="选择真题 JSON", filetypes=[("JSON 真题", "*.json")])
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
            exams = payload if isinstance(payload, list) else payload.get("exams", [])
            valid = []
            for exam in exams:
                if not isinstance(exam, dict) or not exam.get("id") or "cloze" not in exam:
                    continue
                valid.append(exam)
            if not valid:
                raise ValueError("文件里没有符合结构的真题对象（需要 id / cloze / matching / careful）。")
            imported = [exam for exam in self.store.data.setdefault("imported_exams", [])
                        if isinstance(exam, dict)]
            ids = {exam.get("id") for exam in imported}
            imported.extend(exam for exam in valid if exam["id"] not in ids)
            self.store.data["imported_exams"] = imported
            self.store.save()
            self.app.reload_content()
            messagebox.showinfo("导入成功", f"已导入 {len(valid)} 套真题，重新进入阅读模块即可选择。",
                                parent=self.app)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("导入失败", f"无法导入：{exc}", parent=self.app)

    def _export_template(self) -> None:
        path = filedialog.asksaveasfilename(title="保存真题模板", defaultextension=".json",
                                            initialfile="cet6_exam_template.json",
                                            filetypes=[("JSON", "*.json")])
        if not path:
            return
        template = {
            "exams": [{
                "id": "2024-06-1", "year": 2024, "month": 6, "set": 1,
                "label": "2024年6月 · 第1套", "title": "2024年6月六级真题（第1套）",
                "source": "自备真题（请填写真实来源）",
                "cloze": {"id": "2024-06-1-cloze", "title": "2024年6月 选词填空",
                          "passage": "Passage text with {26} ... {35} placeholders.",
                          "wordbank": [{"letter": "A", "word": "example"}],
                          "blanks": [{"num": 26, "answer": "A", "word": "example"}]},
                "matching": {"id": "2024-06-1-matching", "title": "段落匹配标题",
                             "paragraphs": [{"label": "A", "text": "段落内容"}],
                             "statements": [{"num": 36, "statement": "句子", "answer": "A"}]},
                "careful": [{"id": "2024-06-1-careful-1", "title": "Passage One",
                             "paragraphs": ["第一段"],
                             "questions": [{"num": 46, "stem": "题干",
                                            "options": ["A项", "B项", "C项", "D项"], "answer": "A"}]}],
            }]
        }
        Path(path).write_text(json.dumps(template, ensure_ascii=False, indent=1), encoding="utf-8")
        messagebox.showinfo("模板已导出", "请保留字段结构，把示例文字替换成你自己的真题内容后再导入。",
                            parent=self.app)

    # ---------------- 数据 ----------------
    def _build_data(self, body) -> None:
        box = card(body, 20)
        box.master.pack(fill="x", pady=12)
        tk_label(box, "学习数据", 14, True).pack(anchor="w")
        tk_label(box, f"保存位置：{self.store.path}", 9, False, MUTED).pack(anchor="w", pady=(6, 2))
        default_dir = Path(os.environ.get("APPDATA", "")) / "CET6Coach"
        if default_dir and self.store.path.parent != default_dir:
            tk_label(box, f"（%APPDATA% 不可写，已自动改用这个可写目录）", 9, False, AMBER).pack(anchor="w")
        if getattr(self.store, "save_failed", False):
            tk_label(box, "当前记录无法写入磁盘，关闭软件后会丢失；请把软件放到有写入权限的目录再试。",
                     9, False, RED).pack(anchor="w")
        migrated = self.store.data.get("meta", {}).get("migrated_from")
        note = f"数据版本：schema {SCHEMA}"
        if migrated:
            note += f"（已从 v{migrated} 自动升级，旧文件已备份为 progress_v{migrated}_backup.json）"
        tk_label(box, note, 9, False, GREEN if migrated else MUTED).pack(anchor="w", pady=(0, 12))
        row = tk.Frame(box, bg=CARD)
        row.pack(fill="x")
        ttk.Button(row, text="备份学习记录", command=self._backup).pack(side="left")
        ttk.Button(row, text="导入备份", command=self._restore).pack(side="left", padx=8)
        ttk.Button(row, text="打开数据目录", command=self.app.open_data_folder).pack(side="left")
        ttk.Button(row, text="重置全部学习记录", style="Danger.TButton",
                   command=self._reset).pack(side="right")

    def _backup(self) -> None:
        path = filedialog.asksaveasfilename(title="备份学习记录", defaultextension=".json",
                                            initialfile=f"cet6_backup_{datetime.now():%Y%m%d}.json",
                                            filetypes=[("JSON", "*.json")])
        if path:
            self.store.export_backup(path)
            messagebox.showinfo("备份完成", "学习记录已备份。", parent=self.app)

    def _restore(self) -> None:
        path = filedialog.askopenfilename(title="选择备份文件", filetypes=[("JSON", "*.json")])
        if not path:
            return
        if not messagebox.askyesno("覆盖当前记录", "导入备份会覆盖当前学习记录，确定继续吗？", parent=self.app):
            return
        try:
            self.store.import_backup(path)
            self.store.save()
            self.app.reload_content()
            messagebox.showinfo("已导入", "学习记录已恢复，页面会使用新的数据。", parent=self.app)
            self.app.navigate("home")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("导入失败", str(exc), parent=self.app)

    def _reset(self) -> None:
        if not messagebox.askyesno("高风险操作",
                                   "确定删除全部词汇进度、错题、成绩、作文与翻译草稿吗？\n"
                                   "个人导入的词表和真题会保留。建议先备份。", parent=self.app):
            return
        self.store.reset(keep_imported=True)
        self.app.reload_content()
        messagebox.showinfo("已重置", "学习记录已重置。", parent=self.app)
        self.app.navigate("home")

    # ---------------- 内容说明 ----------------
    def _build_about(self, body) -> None:
        box = card(body, 20)
        box.master.pack(fill="x", pady=12)
        tk_label(box, "内容说明", 14, True).pack(anchor="w")
        lines = [
            f"词库：{len(self.app.words)} 词，分「高频核心 / 基础回顾 / 六级拓展」三层，含音标、词性、释义与部分例句。",
            f"真题阅读：{len(self.app.exams)} 套（2023 年 6 月、12 月），标注年份与套数；原文来自公开整理的真题文本，"
            "答案经独立作答复核。",
            "解析：逐题给出原文定位、正确项依据与干扰项分析，由本软件整理，不代表官方标准答案。",
            "听力：本软件不包含听力训练，请用真题音频自行练习。",
            "所有记录只保存在本机，不联网、不上传。",
        ]
        for line in lines:
            tk_label(box, "• " + line, 9, False, MUTED, wraplength=860, justify="left").pack(anchor="w", pady=3)
