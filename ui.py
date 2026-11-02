"""通用界面组件、配色与主题。

配色与 design/首页效果图.png、design/词汇检测效果图.png 保持一致：
深蓝侧栏（252px）+ 浅灰蓝工作区 + 白色卡片。
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

BG = "#F4F6FB"
CARD = "#FFFFFF"
SIDEBAR = "#122E60"
SIDEBAR_ACTIVE = "#2C4E9E"
SIDEBAR_HOVER = "#1B3A78"
SIDEBAR_TEXT = "#DCE5FA"
SIDEBAR_MUTED = "#A9B9DA"
SIDEBAR_CARD = "#0D2450"
PRIMARY = "#3157C8"
PRIMARY_DARK = "#24449F"
PRIMARY_SOFT = "#EAF0FF"
TEXT = "#172033"
MUTED = "#667085"
BORDER = "#E1E6F0"
GREEN = "#16865B"
GREEN_SOFT = "#EAF7F1"
RED = "#C43D4B"
RED_SOFT = "#FCEFF1"
AMBER = "#A15C08"
AMBER_SOFT = "#FFF7E9"
STRIP = "#F5F7FC"
FONT = "Microsoft YaHei UI"
MONO = "Consolas"

SIDEBAR_WIDTH = 252


def configure_styles(root: tk.Tk) -> None:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(".", font=(FONT, 10), background=BG, foreground=TEXT)
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Title.TLabel", font=(FONT, 22, "bold"), foreground=TEXT)
    style.configure("Subtitle.TLabel", font=(FONT, 10), foreground=MUTED)
    style.configure("Section.TLabel", font=(FONT, 14, "bold"), foreground=TEXT)
    style.configure("Card.TLabel", background=CARD, foreground=TEXT)
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("TButton", font=(FONT, 10), padding=(14, 9), borderwidth=0, focuscolor=BG)
    style.map("TButton", background=[("active", "#E7ECF8")])
    style.configure("Primary.TButton", background=PRIMARY, foreground="white", font=(FONT, 10, "bold"))
    style.map("Primary.TButton",
              background=[("active", PRIMARY_DARK), ("pressed", PRIMARY_DARK)],
              foreground=[("disabled", "#D5DAE6")])
    style.configure("Ghost.TButton", background=CARD, foreground=PRIMARY, font=(FONT, 10, "bold"))
    style.map("Ghost.TButton", background=[("active", PRIMARY_SOFT)])
    style.configure("Danger.TButton", foreground=RED)
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", font=(FONT, 10, "bold"), padding=(18, 10), background="#E9EDF5")
    style.map("TNotebook.Tab", background=[("selected", CARD)], foreground=[("selected", PRIMARY)])
    style.configure("Treeview", font=(FONT, 10), rowheight=34, background=CARD,
                    fieldbackground=CARD, borderwidth=0)
    style.configure("Treeview.Heading", font=(FONT, 10, "bold"), background="#EDF1F7",
                    foreground=TEXT, padding=8)
    style.map("Treeview", background=[("selected", "#DCE6FC")], foreground=[("selected", TEXT)])
    style.configure("TEntry", padding=8, fieldbackground=CARD)
    style.configure("TCombobox", padding=7, fieldbackground=CARD)
    style.configure("TCheckbutton", background=CARD, foreground=TEXT)
    style.configure("TRadiobutton", background=CARD, foreground=TEXT)
    style.configure("Horizontal.TProgressbar", background=PRIMARY, troughcolor="#E3E8F1", borderwidth=0)


def card(parent: tk.Misc, padding: int = 0) -> tk.Frame:
    """白底圆角卡片（Tk 没有圆角，用 1px 边框模拟）。"""
    outer = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
    if padding:
        outer.inner = tk.Frame(outer, bg=CARD, padx=padding, pady=padding)  # type: ignore[attr-defined]
        outer.inner.pack(fill="both", expand=True)  # type: ignore[attr-defined]
        return outer.inner  # type: ignore[return-value]
    return outer


def strip(parent: tk.Misc, padding: int = 12) -> tk.Frame:
    """浅灰底信息条（列表行、提示条）。"""
    return tk.Frame(parent, bg=STRIP, padx=padding, pady=padding)


def tk_label(parent: tk.Misc, text: str = "", size: int = 10, bold: bool = False,
             color: str = TEXT, bg: str = CARD, **kwargs) -> tk.Label:
    return tk.Label(parent, text=text, font=(FONT, size, "bold" if bold else "normal"),
                    fg=color, bg=bg, **kwargs)


def tag(parent: tk.Misc, text: str, fg: str = PRIMARY, bg: str = PRIMARY_SOFT) -> tk.Label:
    return tk.Label(parent, text=f" {text} ", font=(FONT, 9), fg=fg, bg=bg, padx=6, pady=2)


def clear(widget: tk.Misc) -> None:
    for child in widget.winfo_children():
        child.destroy()


def readonly_text(parent: tk.Misc, content: str, size: int = 11, bg: str = CARD,
                  foreground: str = TEXT, wrap: str = "word") -> tk.Text:
    widget = tk.Text(parent, wrap=wrap, font=(FONT, size), bg=bg, fg=foreground,
                     relief="flat", padx=4, pady=4, spacing1=3, spacing3=8,
                     insertwidth=0, highlightthickness=0, borderwidth=0)
    widget.insert("1.0", content)
    widget.configure(state="disabled")
    return widget


def editor_text(parent: tk.Misc, size: int = 12) -> tk.Text:
    return tk.Text(parent, wrap="word", font=(FONT, size), bg=CARD, fg=TEXT,
                   relief="flat", undo=True, padx=12, pady=12, spacing1=5,
                   spacing3=7, insertbackground=PRIMARY, highlightthickness=1,
                   highlightbackground=BORDER, highlightcolor=PRIMARY, borderwidth=0)


class ScrollFrame(ttk.Frame):
    """带滚动条的容器；内容放进 .inner。"""

    def __init__(self, parent: tk.Misc, bg: str = BG, bar: bool = True):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        if bar:
            self.scrollbar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._on_configure)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_configure(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas(self, event) -> None:
        self.canvas.itemconfigure(self.window, width=event.width)

    def _bind_wheel(self, _event=None) -> None:
        self.canvas.bind_all("<MouseWheel>", self._wheel)

    def _unbind_wheel(self, _event=None) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _wheel(self, event) -> None:
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def scroll_top(self) -> None:
        self.canvas.yview_moveto(0)


class Countdown:
    def __init__(self, label: tk.Label, minutes: int, on_finish=None):
        self.label = label
        self.total = minutes * 60
        self.remaining = self.total
        self.running = False
        self.on_finish = on_finish
        self.job = None
        self.render()

    def render(self) -> None:
        if self.label.winfo_exists():
            minutes, seconds = divmod(max(0, self.remaining), 60)
            color = RED if self.remaining <= 300 else MUTED
            self.label.configure(text=f"{minutes:02d}:{seconds:02d}", fg=color)

    def toggle(self) -> bool:
        self.running = not self.running
        if self.running:
            self._tick()
        elif self.job:
            self.label.after_cancel(self.job)
        return self.running

    def reset(self) -> None:
        self.running = False
        self.remaining = self.total
        if self.job:
            self.label.after_cancel(self.job)
        self.render()

    def used_seconds(self) -> int:
        return max(0, self.total - self.remaining)

    def _tick(self) -> None:
        if not self.running or not self.label.winfo_exists():
            return
        self.render()
        if self.remaining <= 0:
            self.running = False
            if self.on_finish:
                self.on_finish()
            return
        self.remaining -= 1
        self.job = self.label.after(1000, self._tick)
