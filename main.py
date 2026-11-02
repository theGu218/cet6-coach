"""CET-6 Coach 主程序：窗口、侧栏导航与页面路由。

只负责“壳”：数据、业务规则在 repositories / services，页面在 views。
"""
from __future__ import annotations

import os
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

import content
from repositories.store import APP_NAME, ProgressStore, resource_path, user_data_dir
from services.accumulation_service import AccumulationService
from services.reading_service import ReadingService
from services.stats_service import StatsService
from services.vocabulary_service import VocabularyService
from ui import (BG, BORDER, CARD, FONT, MUTED, PRIMARY, SIDEBAR, SIDEBAR_ACTIVE,
                SIDEBAR_CARD, SIDEBAR_HOVER, SIDEBAR_MUTED, SIDEBAR_TEXT,
                SIDEBAR_WIDTH, TEXT, configure_styles, tk_label)

APP_TITLE = "六级冲刺 · CET-6 Coach"
VERSION = "2.1.0"

NAV_ITEMS = [
    ("home", "今日复习"),
    ("vocab", "核心词汇"),
    ("reading", "真题阅读"),
    ("accumulation", "积累本"),
    ("writing", "写作训练"),
    ("translation", "翻译训练"),
    ("stats", "复盘统计"),
    ("settings", "设置与数据"),
]


class CET6App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.store = ProgressStore()
        self._load_content()
        self.vocab_service = VocabularyService(self.words, self.store)
        self.reading_service = ReadingService(self.exams, self.store)
        self.stats_service = StatsService(self.store, self.vocab_service, self.reading_service)
        self.accumulation_service = AccumulationService(self.store, content.accumulation_seed())
        self.current = "home"
        self._views: dict = {}

        self.title(APP_TITLE)
        try:
            self.iconbitmap(resource_path("CET6Coach.ico"))
        except tk.TclError:
            pass
        self.geometry("1240x820")
        self.minsize(1080, 720)
        self.configure(bg=BG)
        self._center_window()
        configure_styles(self)
        self._build_menu()
        self._build_shell()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.navigate("home")

    # ---------------- 数据 ----------------
    def _load_content(self) -> None:
        self.words = list(content.vocabulary()) + list(self.store.data.get("imported_words", []))
        imported = [e for e in self.store.data.get("imported_exams", []) if isinstance(e, dict) and e.get("id")]
        self.exams = list(content.reading()) + imported
        self.writings = list(content.writing())
        self.translations = list(content.translation())

    def reload_content(self) -> None:
        self._load_content()
        self.vocab_service = VocabularyService(self.words, self.store)
        self.reading_service = ReadingService(self.exams, self.store)
        self.stats_service = StatsService(self.store, self.vocab_service, self.reading_service)
        self._views.clear()

    # ---------------- 窗口 ----------------
    def _center_window(self) -> None:
        self.update_idletasks()
        scale = max(1.0, self.winfo_fpixels("1i") / 96.0)
        width = min(int(1240 * scale), int(self.winfo_screenwidth() * 0.95))
        height = min(int(820 * scale), int(self.winfo_screenheight() * 0.92))
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (self.winfo_screenheight() - height) // 2 - 20)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(int(1040 * min(scale, 1.3)), int(700 * min(scale, 1.3)))

    def _build_menu(self) -> None:
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="备份学习记录…", command=self.backup_progress)
        file_menu.add_command(label="打开数据目录", command=self.open_data_folder)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self._on_close)
        menu.add_cascade(label="文件", menu=file_menu)
        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="使用指南", command=self.show_guide)
        help_menu.add_command(label="关于", command=self.show_about)
        menu.add_cascade(label="帮助", menu=help_menu)
        self.configure(menu=menu)

    def _build_shell(self) -> None:
        self.status = tk.Label(self, text="学习记录自动保存在本机", bd=0, bg="#E9EDF5", fg=MUTED,
                               font=(FONT, 9), anchor="w", padx=14, pady=5)
        self.status.pack(side="bottom", fill="x")
        self.sidebar = tk.Frame(self, bg=SIDEBAR, width=SIDEBAR_WIDTH)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk_label(self.sidebar, "CET—6", 24, True, "white", SIDEBAR).pack(anchor="w", padx=24, pady=(26, 0))
        tk_label(self.sidebar, "六级冲刺 · 学习工作台", 10, False, SIDEBAR_MUTED, SIDEBAR).pack(
            anchor="w", padx=24, pady=(4, 22))

        self.nav_buttons: dict[str, tk.Frame] = {}
        self.nav_labels: dict[str, tk.Label] = {}
        for key, text in NAV_ITEMS:
            holder = tk.Frame(self.sidebar, bg=SIDEBAR, cursor="hand2")
            holder.pack(fill="x", padx=12, pady=2)
            dot = tk.Label(holder, text="●", font=(FONT, 7), fg=SIDEBAR_MUTED, bg=SIDEBAR)
            dot.pack(side="left", padx=(12, 10), pady=10)
            label = tk.Label(holder, text=text, font=(FONT, 11, "bold"), fg=SIDEBAR_TEXT, bg=SIDEBAR,
                             anchor="w")
            label.pack(side="left", fill="x", expand=True, pady=10)
            for widget in (holder, dot, label):
                widget.bind("<Button-1>", lambda _e, k=key: self.navigate(k))
                widget.bind("<Enter>", lambda _e, k=key: self._nav_hover(k, True))
                widget.bind("<Leave>", lambda _e, k=key: self._nav_hover(k, False))
            self.nav_buttons[key] = holder
            self.nav_labels[key] = label

        bottom = tk.Frame(self.sidebar, bg=SIDEBAR_CARD, padx=16, pady=14)
        bottom.pack(side="bottom", fill="x", padx=14, pady=18)
        tk_label(bottom, "今日已学习", 9, False, SIDEBAR_MUTED, SIDEBAR_CARD).pack(anchor="w")
        self.sidebar_today = tk_label(bottom, "0 分钟", 15, True, "white", SIDEBAR_CARD)
        self.sidebar_today.pack(anchor="w", pady=(2, 8))
        self.sidebar_streak = tk_label(bottom, "连续学习 0 天", 12, True, "white", SIDEBAR_CARD)
        self.sidebar_streak.pack(anchor="w")
        tk_label(bottom, "先复习，再学新内容", 9, False, SIDEBAR_MUTED, SIDEBAR_CARD).pack(anchor="w", pady=(6, 0))

        self.main = ttk.Frame(self)
        self.main.pack(side="left", fill="both", expand=True)

    def _nav_hover(self, key: str, inside: bool) -> None:
        if key == self.current:
            return
        color = SIDEBAR_HOVER if inside else SIDEBAR
        holder = self.nav_buttons[key]
        holder.configure(bg=color)
        for child in holder.winfo_children():
            child.configure(bg=color)

    # ---------------- 路由 ----------------
    def navigate(self, key: str) -> None:
        if key not in dict(NAV_ITEMS):
            key = "home"
        self.current = key
        for name, holder in self.nav_buttons.items():
            active = name == key
            bg = SIDEBAR_ACTIVE if active else SIDEBAR
            holder.configure(bg=bg)
            for child in holder.winfo_children():
                child.configure(bg=bg, fg=("white" if active else SIDEBAR_TEXT))
        for child in self.main.winfo_children():
            child.destroy()
        view = self._view_class(key)(self, self.main)
        view.show()
        self.refresh_sidebar()

    def _view_class(self, key: str):
        from views import accumulation, home, reading, settings, stats, translation, vocabulary, writing
        return {
            "home": home.HomeView,
            "vocab": vocabulary.VocabularyView,
            "reading": reading.ReadingView,
            "accumulation": accumulation.AccumulationView,
            "writing": writing.WritingView,
            "translation": translation.TranslationView,
            "stats": stats.StatsView,
            "settings": settings.SettingsView,
        }[key]

    def show_page(self, key: str, **kwargs) -> None:
        """页面内跳转（例如首页“开始”按钮），支持传参给目标页面。"""
        from views import accumulation, home, reading, settings, stats, translation, vocabulary, writing
        classes = {
            "home": home.HomeView, "vocab": vocabulary.VocabularyView, "reading": reading.ReadingView,
            "accumulation": accumulation.AccumulationView, "writing": writing.WritingView,
            "translation": translation.TranslationView, "stats": stats.StatsView,
            "settings": settings.SettingsView,
        }
        self.navigate(key)
        current = self.main.winfo_children()
        if current and kwargs:
            view = getattr(current[0], "view", None)
            if view is not None and hasattr(view, "enter"):
                view.enter(**kwargs)

    def refresh_sidebar(self) -> None:
        stats = self.store.stats()
        minutes = self.store.minutes_today()
        self.sidebar_today.configure(text=f"{minutes} 分钟")
        self.sidebar_streak.configure(text=f"连续学习 {stats['streak']} 天")
        if self.store.save_failed:
            saved = "记录无法写入磁盘（只保存在内存）"
        else:
            saved = f"已自动保存 · {datetime.now():%H:%M}"
        self.status.configure(
            text=f"{saved}　｜　词库 {len(self.words)} 词　｜　数据目录 {self.store.path.parent}")

    # ---------------- 菜单动作 ----------------
    def backup_progress(self) -> None:
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(title="备份学习记录", defaultextension=".json",
                                            initialfile=f"cet6_backup_{datetime.now():%Y%m%d}.json",
                                            filetypes=[("JSON", "*.json")])
        if path:
            self.store.export_backup(path)
            messagebox.showinfo("备份完成", "学习记录已备份。", parent=self)

    def open_data_folder(self) -> None:
        import os
        os.startfile(str(self.store.path.parent))  # type: ignore[attr-defined]

    def show_guide(self) -> None:
        window = tk.Toplevel(self)
        window.title("使用指南")
        window.geometry("720x620")
        window.configure(bg=CARD)
        box = tk.Frame(window, bg=CARD, padx=24, pady=20)
        box.pack(fill="both", expand=True)
        guide = """一、每天怎么用
1. 打开「今日复习」，先做到期旧词和错词重练；
2. 再看今日新词，按 英译汉 → 汉译英 → 语境选择 逐级解锁；
3. 做一套真题阅读，学习模式逐题看解析，考试模式先整组计时；
4. 写作 / 翻译限时写，写完对照参考，把好句式收进积累本。

二、词汇掌握规则
答对不会立刻变“已掌握”：需要在不同学习日多次答对，并完成语境题，
才会进入“已掌握”。答错会进入“待巩固”，保留历史记录，当天重新到期。

三、真题说明
内置阅读题为历年六级真题（2023 年 6 月、12 月共 6 套），标注年份与套数；
解析由本软件整理，干扰项分析用于说明命题逻辑，不代表官方答案。

四、记录与备份
学习记录保存在 %APPDATA%\\CET6Coach\\progress.json，升级前会自动备份。
建议每月用「文件 → 备份学习记录」备份一次。"""
        text = tk.Text(box, wrap="word", font=(FONT, 11), bg=CARD, fg=TEXT, relief="flat",
                       padx=6, pady=6, spacing1=4, spacing3=8)
        text.insert("1.0", guide)
        text.configure(state="disabled")
        text.pack(fill="both", expand=True)
        ttk.Button(box, text="知道了", style="Primary.TButton", command=window.destroy).pack(anchor="e", pady=(10, 0))

    def show_about(self) -> None:
        messagebox.showinfo(
            "关于 CET-6 Coach",
            f"六级冲刺 {VERSION}\n本地原生学习软件\n\n"
            f"词库 {len(self.words)} 词 · 真题阅读 {len(self.exams)} 套\n"
            "所有记录只保存在本机，不联网、不上传。",
            parent=self)

    def _on_close(self) -> None:
        self.store.save()
        self.destroy()


def main() -> None:
    try:
        run()
    except Exception:  # noqa: BLE001 - 打包后没有控制台，必须留下日志
        import traceback
        try:
            log_path = user_data_dir() / "error.log"
            log_path.write_text(traceback.format_exc(), encoding="utf-8")
        except Exception:
            log_path = None
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "六级冲刺启动失败",
                "程序启动时出错。\n\n" + (f"详细信息已写入：\n{log_path}" if log_path else "也无法写入日志文件。"))
        except Exception:
            pass
        raise


def run() -> None:
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    app = CET6App()
    auto_close = os.environ.get("CET6COACH_AUTOCLOSE")
    if auto_close:  # 打包自检用：启动后自动关闭，便于 CI 判断能否正常启动
        app.after(int(float(auto_close) * 1000), app._on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
