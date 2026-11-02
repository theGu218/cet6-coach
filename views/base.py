"""页面基类：统一页头、滚动容器与页面刷新。"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ui import BG, CARD, MUTED, PRIMARY_SOFT, TEXT, clear, tk_label


class BaseView:
    def __init__(self, app, parent):
        self.app = app
        self.store = app.store
        self.parent = parent
        self.view = self
        parent.view = self  # 便于 show_page 传参

    # ---------------- 生命周期 ----------------
    def show(self) -> None:
        clear(self.parent)
        self.build()

    def build(self) -> None:  # pragma: no cover - 子类实现
        raise NotImplementedError

    def enter(self, **kwargs) -> None:  # 页面内跳转时接收参数
        pass

    # ---------------- 组件 ----------------
    def header(self, title: str, subtitle: str, action: tuple[str, callable] | None = None) -> ttk.Frame:
        frame = ttk.Frame(self.parent)
        frame.pack(fill="x", padx=30, pady=(24, 14))
        text = tk.Frame(frame, bg=BG)
        text.pack(side="left", fill="x", expand=True)
        tk_label(text, title, 21, True, TEXT, BG).pack(anchor="w")
        tk_label(text, subtitle, 10, False, MUTED, BG, wraplength=980,
                 justify="left").pack(anchor="w", pady=(4, 0))
        if action:
            label, command = action
            button = tk.Button(frame, text=label, font=("Microsoft YaHei UI", 11, "bold"),
                               fg="white", bg="#2F55C9", activebackground="#24449F",
                               activeforeground="white", relief="flat", bd=0, padx=22, pady=10,
                               cursor="hand2", command=command)
            button.pack(side="right")
        return frame

    def section(self, parent, title: str, subtitle: str = "") -> tk.Frame:
        box = tk.Frame(parent, bg=CARD)
        box.pack(fill="x", pady=(0, 2))
        tk_label(box, title, 14, True, TEXT, CARD).pack(anchor="w")
        if subtitle:
            tk_label(box, subtitle, 9, False, MUTED, CARD).pack(anchor="w", pady=(2, 0))
        return box

    def refresh(self) -> None:
        self.app.refresh_sidebar()

    # ---------------- 小工具 ----------------
    @staticmethod
    def letter(index: int) -> str:
        return "ABCD"[index] if 0 <= index < 4 else ""

    def empty_state(self, parent, text: str, hint: str = "") -> None:
        box = tk.Frame(parent, bg=PRIMARY_SOFT)
        box.pack(fill="x", pady=10)
        tk_label(box, text, 12, True, TEXT, PRIMARY_SOFT).pack(anchor="w", padx=18, pady=(16, 4))
        if hint:
            tk_label(box, hint, 10, False, MUTED, PRIMARY_SOFT).pack(anchor="w", padx=18, pady=(0, 16))
