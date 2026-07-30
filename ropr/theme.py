# -*- coding: utf-8 -*-
"""색과 글꼴 (ui.py 와 panels.py 가 같이 쓴다)."""

from tkinter import font as tkfont

BG = "#eef0f4"
PANEL = "#ffffff"
INK = "#1b1f27"
MUTED = "#6b7280"
LINE = "#d5d9e0"
ACCENT = "#c8102e"
ACCENT_DK = "#8e0a1f"
GOLD = "#b5872a"
SOFT = "#fbfbfd"

FONT_CANDIDATES = (
    "맑은 고딕", "Malgun Gothic", "NanumGothic", "Nanum Gothic",
    "Noto Sans CJK KR", "AppleGothic", "WenQuanYi Zen Hei", "DejaVu Sans",
)


def pick_font(root):
    families = set(tkfont.families(root))
    for name in FONT_CANDIDATES:
        if name in families:
            return name
    return "TkDefaultFont"
