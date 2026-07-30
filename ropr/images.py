# -*- coding: utf-8 -*-
"""그림 담당.

- 등급 문양(뱃지)은 외부 파일 없이 캔버스에 직접 그린다.
- 유닛 그림을 쓰고 싶으면 설정 파일 옆의 `이미지` 폴더에 넣어두면 자동으로 잡힌다.
    예)  이미지/루피.png      ← "루피 (초월)" 에 붙는다
         이미지/루피 (초월).png
  Tk 8.6 이상이면 png, 그 아래면 gif 만 읽을 수 있다.
"""

import re
import tkinter as tk

IMAGE_DIRNAME = "이미지"
SUFFIXES = (".png", ".gif", ".ppm", ".pgm")

GRADE_COLORS = {
    "초월": ("#8a5a00", "#f2c14e"),
    "불멸": ("#5b2c86", "#c9a0f0"),
    "영원": ("#14596b", "#7fd4e8"),
    "제한": ("#8e2b26", "#f0928c"),
    "신비": ("#1f6b4d", "#87e0b6"),
}
DEFAULT_COLORS = ("#4a5568", "#cbd5e0")

_cache = {}


def base_name(unit):
    """'루피 (초월)' → '루피'"""
    return re.sub(r'\s*\([^()]*\)\s*$', '', unit or '').strip()


def grade_of(unit):
    for grade in GRADE_COLORS:
        if grade in (unit or ''):
            return grade
    return None


def image_dir(config_path):
    return config_path.parent / IMAGE_DIRNAME


def find_image(config_path, unit):
    """유닛 이름에 맞는 그림 파일을 찾는다. 없으면 None."""
    if not unit:
        return None
    folder = image_dir(config_path)
    if not folder.is_dir():
        return None
    for stem in (unit, base_name(unit)):
        for suffix in SUFFIXES:
            path = folder / (stem + suffix)
            if path.is_file():
                return path
    return None


def load_image(config_path, unit):
    """PhotoImage 를 돌려준다. 못 읽으면 None. (한 번 읽은 건 재사용)"""
    path = find_image(config_path, unit)
    if path is None:
        return None
    key = str(path)
    if key in _cache:
        return _cache[key]
    try:
        _cache[key] = tk.PhotoImage(file=str(path))
    except Exception:
        _cache[key] = None
    return _cache[key]


class Badge(tk.Canvas):
    """등급 문양. 유닛 그림이 있으면 그림을, 없으면 직접 그린 문양을 보여준다."""

    def __init__(self, master, size=54, bg="#ffffff", **kw):
        super().__init__(master, width=size, height=size, highlightthickness=0,
                         bd=0, bg=bg, **kw)
        self.size = size
        self._photo = None
        self.show(None)

    def show(self, unit, grade=None, config_path=None, spinning=False):
        self.delete("all")
        s = self.size
        grade = grade or grade_of(unit)
        dark, light = GRADE_COLORS.get(grade, DEFAULT_COLORS)
        if spinning:
            dark, light = "#9aa1ae", "#e2e6ed"

        pad = 3
        self.create_oval(pad, pad, s - pad, s - pad, fill=light, outline=dark, width=2)
        self.create_oval(pad + 5, pad + 5, s - pad - 5, s - pad - 5,
                         outline=dark, width=1)

        photo = None
        if unit and config_path is not None and not spinning:
            photo = load_image(config_path, unit)
        if photo is not None:
            self._photo = photo          # 참조를 잡아둬야 안 사라진다
            self.create_image(s // 2, s // 2, image=photo)
            return

        mark = "?" if spinning else (grade[0] if grade else (base_name(unit)[:1] or "·"))
        self.create_text(s // 2, s // 2 + 1, text=mark, fill=dark,
                         font=("", int(s * 0.42), "bold"))
