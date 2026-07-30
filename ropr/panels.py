# -*- coding: utf-8 -*-
"""버튼을 하나씩 눌러서 뽑는 결과 화면들.

메인 뽑기에서 아래 컨텐츠가 나오면 글자만 찍는 대신 이 패널이 뜬다.
    인생의고도전 / 너의상위는 / 지츠'다이스'룰 / 이캐릭들필수·금지에요 /
    녜힁제조기 / 내가 제일 운 없어
"""

import random
import tkinter as tk
from tkinter import ttk

from . import images, sound
from .data import COLOR_HEX
from .engine import DrawResult
from .theme import ACCENT, ACCENT_DK, GOLD, INK, LINE, MUTED, PANEL, SOFT


class SpinPanel(tk.Frame):
    """버튼을 누르면 값이 촤르륵 돌다가 멈추는 화면의 공통 부모."""

    title = ""

    def __init__(self, master, app, content=None):
        super().__init__(master, bg=PANEL)
        self.app = app
        self.base = app.base
        self.content = content or {}
        self._jobs = []
        self._busy = set()
        self._show_desc()
        self.build()

    def _show_desc(self):
        """이 룰이 뭐 하는 룰인지 맨 위에 적어준다."""
        text = (self.content.get("desc") or "").strip()
        if not text:
            return
        tk.Label(self, text=text, bg="#f5f7fb", fg="#41506b", justify="left",
                 wraplength=880, font=(self.base, 10), anchor="w",
                 padx=12, pady=8).pack(fill="x", padx=18, pady=(12, 0))

    # ------------------------------------------------------------- 하위 클래스용
    def build(self):
        raise NotImplementedError

    def summary(self):
        """기록/복사에 쓸 현재 상태."""
        raise NotImplementedError

    # ---------------------------------------------------------------- 연출
    def spin(self, key, label, frames, final, button=None, once=False,
             fg=None, badge=None, badge_unit=None, on_done=None, end_sound=None):
        """label 의 글자를 frames 안에서 촤르륵 바꾸다가 final 에서 멈춘다."""
        if key in self._busy:
            return
        self._busy.add(key)
        if button is not None:
            button.configure(state="disabled")
        frames = [f for f in frames if f is not None] or [final]

        def step(delay, n):
            if delay > 235:
                label.configure(text=str(final), fg=fg or ACCENT)
                if badge is not None:
                    badge.show(badge_unit, config_path=self.app.config_path)
                self._busy.discard(key)
                if button is not None and not once:
                    button.configure(state="normal")   # once=True 면 한 번만 눌린다
                (end_sound or sound.settle)()
                if on_done:
                    on_done()
                self.app.refresh_panel_history()
                return
            label.configure(text=str(random.choice(frames)), fg=MUTED)
            if badge is not None:
                badge.show(None, spinning=True)
            if n % 2 == 0:
                sound.tick()
            self._jobs.append(self.after(int(delay), lambda: step(delay * 1.14, n + 1)))

        step(38, 0)

    def busy(self):
        return bool(self._busy)

    def stop(self):
        for job in self._jobs:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self._jobs = []
        self._busy.clear()

    # ------------------------------------------------------------ 만들기 도우미
    def heading(self, text, parent=None):
        tk.Label(parent or self, text=text, bg=PANEL, fg="#475569",
                 font=(self.base, 10, "bold")).pack(anchor="w", padx=18, pady=(12, 2))

    def hint(self, text, parent=None):
        tk.Label(parent or self, text=text, bg=PANEL, fg=MUTED,
                 font=(self.base, 9)).pack(anchor="w", padx=18, pady=(6, 0))

    def value_label(self, parent, width=5, size=20, placeholder="–"):
        return tk.Label(parent, text=placeholder, bg=SOFT, fg=MUTED, width=width,
                        font=(self.base, size, "bold"), highlightthickness=1,
                        highlightbackground=LINE, pady=2)


class Gauge(tk.Canvas):
    """인생의 고도를 보여주는 세로 막대."""

    def __init__(self, master, color, height=86, width=30):
        super().__init__(master, width=width, height=height, bg=PANEL,
                         highlightthickness=0, bd=0)
        self.color = color
        self.h = height
        self.w = width
        self.draw(0, 1)

    def draw(self, value, maximum):
        self.delete("all")
        pad = 3
        self.create_rectangle(pad, pad, self.w - pad, self.h - pad,
                              outline=LINE, fill=SOFT)
        ratio = 0 if maximum <= 0 else max(0.0, min(1.0, value / float(maximum)))
        filled = int((self.h - 2 * pad) * ratio)
        if filled > 0:
            self.create_rectangle(pad, self.h - pad - filled, self.w - pad,
                                  self.h - pad, outline="", fill=self.color)
        # 기구 모양 표식
        y = self.h - pad - filled
        self.create_oval(self.w / 2 - 6, y - 12, self.w / 2 + 6, y,
                         fill=self.color, outline="#ffffff", width=1)
        self.create_line(self.w / 2, y, self.w / 2, y + 4, fill="#ffffff")


# ------------------------------------------------------------------ 인생의고도전
class AltitudePanel(SpinPanel):
    title = "인생의 고도"

    def build(self):
        roller = self.app.roller
        self.lo, self.hi = roller.altitude_range()
        self.elo, self.ehi = roller.altitude_extra_range()
        self.colors = roller._colors()
        self.rows = {}

        self.heading("색깔별로 버튼을 눌러서 고도를 뽑으세요  ( %d ~ %d )" % (self.lo, self.hi))

        grid = tk.Frame(self, bg=PANEL)
        grid.pack(anchor="w", padx=18, pady=(4, 0))

        for col, color in enumerate(self.colors):
            hex_color = COLOR_HEX.get(color, INK)
            card = tk.Frame(grid, bg=PANEL, highlightthickness=1,
                            highlightbackground=LINE)
            card.grid(row=0, column=col, padx=6, pady=4, sticky="n")

            tk.Label(card, text=color, bg=PANEL, fg=hex_color,
                     font=(self.base, 12, "bold")).pack(pady=(8, 2))

            body = tk.Frame(card, bg=PANEL)
            body.pack(padx=10)
            gauge = Gauge(body, hex_color)
            gauge.pack(side="left", padx=(0, 8))

            right = tk.Frame(body, bg=PANEL)
            right.pack(side="left")
            total = tk.Label(right, text="–", bg=SOFT, fg=MUTED, width=4,
                             font=(self.base, 24, "bold"),
                             highlightthickness=1, highlightbackground=LINE)
            total.pack()
            detail = tk.Label(right, text="", bg=PANEL, fg=MUTED,
                              font=(self.base, 9))
            detail.pack(pady=(2, 0))

            base_btn = ttk.Button(card, text="고도 뽑기", style="Slot.TButton",
                                  command=lambda c=color: self.roll_base(c))
            base_btn.pack(fill="x", padx=10, pady=(8, 2))
            extra_btn = ttk.Button(card, text="추가 고도", style="Extra.TButton",
                                   state="disabled",
                                   command=lambda c=color: self.roll_extra(c))
            extra_btn.pack(fill="x", padx=10, pady=(0, 10))

            self.rows[color] = {
                "gauge": gauge, "total": total, "detail": detail,
                "base_btn": base_btn, "extra_btn": extra_btn,
                "base": None, "extra": None,
            }

        self.hint("[추가 고도] 로 나온 숫자는 기존 고도에 자동으로 더해집니다.")

    def _redraw(self, color):
        row = self.rows[color]
        base, extra = row["base"], row["extra"]
        total = (base or 0) + (extra or 0)
        row["total"].configure(text=str(total), fg=COLOR_HEX.get(color, ACCENT))
        row["detail"].configure(
            text="%d + %d" % (base, extra) if extra is not None else "")
        row["gauge"].draw(total, self.hi + self.ehi)

    def roll_base(self, color):
        row = self.rows[color]
        value = self.app.roller.roll((self.lo, self.hi))
        frames = list(range(self.lo, self.hi + 1))

        def done():
            row["base"] = value
            row["extra"] = None
            row["extra_btn"].configure(state="normal")
            self._redraw(color)

        self.spin("base:" + color, row["total"], frames, value,
                  button=row["base_btn"], fg=COLOR_HEX.get(color, ACCENT),
                  on_done=done)

    def roll_extra(self, color):
        row = self.rows[color]
        if row["base"] is None:
            return
        value = self.app.roller.roll((self.elo, self.ehi))
        frames = ["+%d" % n for n in range(self.elo, self.ehi + 1)]

        def done():
            row["extra"] = value
            self._redraw(color)

        self.spin("extra:" + color, row["total"], frames, "+%d" % value,
                  button=row["extra_btn"], fg=GOLD, on_done=done)

    def summary(self):
        res = DrawResult(self.app.current_title, desc=self.content.get("desc", ""))
        res.head("인생의 고도  ( %d ~ %d,  추가 %d ~ %d )"
                 % (self.lo, self.hi, self.elo, self.ehi))
        for color in self.colors:
            row = self.rows[color]
            if row["base"] is None:
                res.item("%s  :  아직 안 뽑음" % color, color=color)
            elif row["extra"] is None:
                res.item("%s  :  %d" % (color, row["base"]), color=color)
            else:
                res.item("%s  :  %d + %d  =  %d"
                         % (color, row["base"], row["extra"],
                            row["base"] + row["extra"]), color=color)
        return res


# ------------------------------------------------------------------- 너의상위는
class TierPanel(SpinPanel):
    title = "너의 상위는"

    def build(self):
        roller = self.app.roller
        self.lo, self.hi = roller.tier_range()
        self.colors = roller._colors()
        self.rows = {}

        self.heading("색깔별로 버튼을 눌러서 상위 개수를 뽑으세요  ( %d ~ %d )"
                     % (self.lo, self.hi))

        grid = tk.Frame(self, bg=PANEL)
        grid.pack(anchor="w", padx=18, pady=(4, 0))

        for col, color in enumerate(self.colors):
            hex_color = COLOR_HEX.get(color, INK)
            card = tk.Frame(grid, bg=PANEL, highlightthickness=1,
                            highlightbackground=LINE)
            card.grid(row=0, column=col, padx=6, pady=4, sticky="n")

            tk.Label(card, text=color, bg=PANEL, fg=hex_color,
                     font=(self.base, 12, "bold")).pack(pady=(8, 2))
            value = tk.Label(card, text="–", bg=SOFT, fg=MUTED, width=3,
                             font=(self.base, 30, "bold"),
                             highlightthickness=1, highlightbackground=LINE)
            value.pack(padx=14)
            pips = tk.Canvas(card, width=96, height=18, bg=PANEL,
                             highlightthickness=0, bd=0)
            pips.pack(pady=(6, 0))
            mark = tk.Label(card, text=" ", bg=PANEL, fg=GOLD, height=1,
                            font=(self.base, 10, "bold"))
            mark.pack()
            btn = ttk.Button(card, text="뽑 기", style="Slot.TButton",
                             command=lambda c=color: self.roll(c))
            btn.pack(fill="x", padx=10, pady=(6, 10))

            self.rows[color] = {"value": value, "pips": pips, "mark": mark,
                                "btn": btn, "n": None}
            self._pips(color, None)

    def _pips(self, color, value):
        canvas = self.rows[color]["pips"]
        canvas.delete("all")
        hex_color = COLOR_HEX.get(color, INK)
        for i in range(self.lo, self.hi + 1):
            x = 10 + (i - self.lo) * 19
            on = value is not None and i <= value and value > 0
            canvas.create_oval(x - 6, 3, x + 6, 15,
                               fill=hex_color if on else SOFT, outline=LINE)

    def roll(self, color):
        row = self.rows[color]
        value = self.app.roller.roll((self.lo, self.hi))
        top = value == self.hi

        def done():
            row["n"] = value
            self._pips(color, value)
            row["mark"].configure(text="★  %d  ★" % value if top else " ")

        self.spin("tier:" + color, row["value"], list(range(self.lo, self.hi + 1)),
                  value, button=row["btn"],
                  fg=GOLD if top else COLOR_HEX.get(color, ACCENT),
                  on_done=done, end_sound=sound.taunt if top else None)

    def summary(self):
        res = DrawResult(self.app.current_title, desc=self.content.get("desc", ""))
        res.head("너의 상위는  ( %d ~ %d )" % (self.lo, self.hi))
        for color in self.colors:
            n = self.rows[color]["n"]
            res.item("%s  :  %s" % (color, "아직 안 뽑음" if n is None else n),
                     color=color)
        return res


# --------------------------------------------------------------- 지츠 다이스 룰
class JitsDicePanel(SpinPanel):
    title = "지츠'다이스'룰"

    def build(self):
        roller = self.app.roller
        self.grades = roller._grades()
        self.colors = roller._colors()
        self.by_grade = roller.uppers_by_grade()
        self.dice_span = roller.dice_range()
        self.slots = {}
        self.dice = {}

        self.heading("등급마다 버튼을 눌러서 상위를 한 마리씩 뽑으세요")
        grid = tk.Frame(self, bg=PANEL)
        grid.pack(anchor="w", padx=18, pady=(4, 0))

        for col, grade in enumerate(self.grades):
            card = tk.Frame(grid, bg=PANEL, highlightthickness=1,
                            highlightbackground=LINE)
            card.grid(row=0, column=col, padx=6, pady=4, sticky="n")
            tk.Label(card, text=grade, bg=PANEL, fg=INK,
                     font=(self.base, 12, "bold")).pack(pady=(8, 4))
            badge = images.Badge(card, size=54, bg=PANEL)
            badge.pack()
            badge.show(None, grade=grade)
            name = tk.Label(card, text="–", bg=SOFT, fg=MUTED, width=16,
                            font=(self.base, 11, "bold"), wraplength=150,
                            highlightthickness=1, highlightbackground=LINE, pady=4)
            name.pack(padx=10, pady=(6, 0))
            btn = ttk.Button(card, text="뽑 기", style="Slot.TButton",
                             command=lambda g=grade: self.roll_unit(g))
            btn.pack(fill="x", padx=10, pady=(6, 10))
            if not self.by_grade.get(grade):
                btn.configure(state="disabled")
                name.configure(text="(등록된 상위 없음)")
            self.slots[grade] = {"badge": badge, "name": name, "btn": btn,
                                 "unit": None}

        self.heading("주사위 — 높은 사람부터 위 상위 중에서 골라 갑니다  ( %d ~ %d )"
                     % self.dice_span)
        drow = tk.Frame(self, bg=PANEL)
        drow.pack(anchor="w", padx=18, pady=(4, 0))
        for col, color in enumerate(self.colors):
            hex_color = COLOR_HEX.get(color, INK)
            card = tk.Frame(drow, bg=PANEL, highlightthickness=1,
                            highlightbackground=LINE)
            card.grid(row=0, column=col, padx=6, pady=2, sticky="n")
            tk.Label(card, text=color, bg=PANEL, fg=hex_color,
                     font=(self.base, 11, "bold")).pack(pady=(6, 0))
            value = tk.Label(card, text="–", bg=SOFT, fg=MUTED, width=5,
                             font=(self.base, 22, "bold"),
                             highlightthickness=1, highlightbackground=LINE)
            value.pack(padx=10, pady=2)
            btn = ttk.Button(card, text="굴리기", style="Slot.TButton",
                             command=lambda c=color: self.roll_dice(c))
            btn.pack(fill="x", padx=10, pady=(2, 8))
            self.dice[color] = {"value": value, "btn": btn, "n": None}

        self.order = tk.Label(self, text="", bg=PANEL, fg=ACCENT_DK,
                              font=(self.base, 12, "bold"))
        self.order.pack(anchor="w", padx=18, pady=(10, 0))

    def roll_unit(self, grade):
        slot = self.slots[grade]
        taken = [s["unit"] for g, s in self.slots.items() if g != grade and s["unit"]]
        unit = self.app.roller.pick_upper(grade, exclude=taken)
        if unit is None:
            unit = self.app.roller.pick_upper(grade) or "(없음)"
        frames = self.by_grade.get(grade) or [unit]

        def done():
            slot["unit"] = unit

        self.spin("unit:" + grade, slot["name"], frames, unit,
                  button=slot["btn"], fg=INK, badge=slot["badge"],
                  badge_unit=unit, on_done=done)

    def roll_dice(self, color):
        cell = self.dice[color]
        value = self.app.roller.roll(self.dice_span)
        lo, hi = self.dice_span

        def done():
            cell["n"] = value
            self._show_order()

        self.spin("dice:" + color, cell["value"], list(range(lo, hi + 1)), value,
                  button=cell["btn"], fg=COLOR_HEX.get(color, ACCENT), on_done=done)

    def _show_order(self):
        rolled = {c: d["n"] for c, d in self.dice.items() if d["n"] is not None}
        if len(rolled) < len(self.colors):
            self.order.configure(
                text="주사위 %d / %d" % (len(rolled), len(self.colors)), fg=MUTED)
            return
        order = sorted(rolled, key=lambda c: rolled[c], reverse=True)
        self.order.configure(
            text="고르는 순서   " + "   →   ".join(
                "%d위 %s" % (i + 1, c) for i, c in enumerate(order)), fg=ACCENT_DK)

    def summary(self):
        res = DrawResult(self.app.current_title, desc=self.content.get("desc", ""))
        res.head("등급별 후보")
        for grade in self.grades:
            unit = self.slots[grade]["unit"]
            res.item("%s  :  %s" % (grade, unit or "아직 안 뽑음"))
        lo, hi = self.dice_span
        res.head("주사위 ( %d ~ %d )" % (lo, hi))
        rolled = {}
        for color in self.colors:
            n = self.dice[color]["n"]
            if n is not None:
                rolled[color] = n
            res.item("%s  :  %s" % (color, "아직 안 굴림" if n is None else n),
                     color=color)
        if len(rolled) == len(self.colors):
            order = sorted(rolled, key=lambda c: rolled[c], reverse=True)
            res.head("고르는 순서 (높은 사람부터)")
            res.item("   →   ".join("%d위 %s" % (i + 1, c)
                                    for i, c in enumerate(order)))
        return res


# ------------------------------------------- 이캐릭들필수에요 / 이캐릭들금지에요
class CharPickPanel(SpinPanel):
    """칸마다 버튼을 눌러서 캐릭터를 하나씩 뽑는 화면."""

    head_text = ""
    summary_head = ""
    spec_keys = ()      # ((표시이름, 설정키, 개수설정키, 기본개수), ...)

    def build(self):
        roller = self.app.roller
        self.specs = tuple((title, key, roller._int(count_key, default))
                           for title, key, count_key, default in self.spec_keys)
        self.slots = {}

        self.heading(self.head_text)
        wrap = tk.Frame(self, bg=PANEL)
        wrap.pack(anchor="w", padx=18, pady=(4, 0))

        for col, (title, key, count) in enumerate(self.specs):
            box = tk.Frame(wrap, bg=PANEL, highlightthickness=1,
                           highlightbackground=LINE)
            box.grid(row=0, column=col, padx=8, sticky="n")
            tk.Label(box, text="%s %d명" % (title, count), bg=PANEL, fg=ACCENT_DK,
                     font=(self.base, 12, "bold")).pack(pady=(8, 4))

            pool = self.app.roller.cfg.get(key) or []
            for i in range(count):
                row = tk.Frame(box, bg=PANEL)
                row.pack(fill="x", padx=10, pady=2)
                name = tk.Label(row, text="–", bg=SOFT, fg=MUTED, width=17,
                                font=(self.base, 11, "bold"), anchor="w",
                                highlightthickness=1, highlightbackground=LINE,
                                padx=6, pady=3)
                name.pack(side="left")
                btn = ttk.Button(row, text="뽑기", width=6, style="Slot.TButton",
                                 command=lambda k=key, n=i: self.roll(k, n))
                btn.pack(side="left", padx=(6, 0))
                if not pool:
                    btn.configure(state="disabled")
                    name.configure(text="(목록 비어 있음)")
                self.slots[(key, i)] = {"name": name, "btn": btn, "value": None}

            ttk.Button(box, text="%s 전부 뽑기" % title,
                       command=lambda k=key, c=count: self.roll_all(k, c)
                       ).pack(fill="x", padx=10, pady=(6, 10))

    def _taken(self, key):
        return [s["value"] for (k, _i), s in self.slots.items()
                if k == key and s["value"]]

    def roll(self, key, index):
        slot = self.slots[(key, index)]
        picked = self.app.roller.pick_char(key, exclude=self._taken(key))
        if picked is None:
            slot["name"].configure(text="(더 뽑을 캐릭터 없음)", fg=MUTED)
            sound.thud()
            return
        frames = self.app.roller.cfg.get(key) or [picked]

        def done():
            slot["value"] = picked

        self.spin("%s:%d" % (key, index), slot["name"], frames, picked,
                  button=slot["btn"], fg=INK, on_done=done)

    def roll_all(self, key, count):
        for i in range(count):
            if self.slots[(key, i)]["value"] is None:
                self.roll(key, i)

    def summary(self):
        res = DrawResult(self.app.current_title, desc=self.content.get("desc", ""))
        res.head(self.summary_head)
        for title, key, count in self.specs:
            picked = [self.slots[(key, i)]["value"] for i in range(count)]
            done = [p for p in picked if p]
            res.item("%s %d/%d  :  %s" % (title, len(done), count,
                                          ",  ".join(done) if done else "아직 안 뽑음"))
        return res


class MustCharPanel(CharPickPanel):
    title = "이캐릭들필수에요"
    head_text = "칸마다 버튼을 눌러서 필수 캐릭터를 뽑으세요"
    summary_head = "필수로 써야 하는 캐릭터"
    spec_keys = (("전설", "legend_chars", "must_legend", 4),
                 ("히든", "hidden_chars", "must_hidden", 4))


class BanCharPanel(CharPickPanel):
    title = "이캐릭들금지에요"
    head_text = "칸마다 버튼을 눌러서 금지 캐릭터를 뽑으세요"
    summary_head = "금지된 캐릭터"
    spec_keys = (("전설", "legend_chars", "ban_legend", 7),
                 ("히든", "hidden_chars", "ban_hidden", 7))


# ------------------------------------------------------------------ 녜힁제조기
class NyehyungPanel(SpinPanel):
    title = "녜힁제조기"

    def build(self):
        roller = self.app.roller
        self.count = max(1, roller._int("nyehyung_count", 2))
        pool, _cores = roller.letter_pool()
        self.letters_pool = sorted(pool)
        self.letters = [None] * self.count
        self.letter_cells = []

        self.heading("상위 이름에 들어있는 글자를 %d개 뽑으세요" % self.count)
        row = tk.Frame(self, bg=PANEL)
        row.pack(anchor="w", padx=18, pady=(4, 0))

        for i in range(self.count):
            card = tk.Frame(row, bg=PANEL, highlightthickness=1,
                            highlightbackground=LINE)
            card.grid(row=0, column=i, padx=6, sticky="n")
            value = tk.Label(card, text="?", bg=SOFT, fg=MUTED, width=3,
                             font=(self.base, 32, "bold"),
                             highlightthickness=1, highlightbackground=LINE)
            value.pack(padx=12, pady=(10, 4))
            btn = ttk.Button(card, text="글자 뽑기", style="Slot.TButton",
                             command=lambda n=i: self.roll_letter(n))
            btn.pack(fill="x", padx=10, pady=(0, 10))
            if not self.letters_pool:
                btn.configure(state="disabled")
            self.letter_cells.append({"value": value, "btn": btn})

        if not self.letters_pool:
            tk.Label(self, text="상위 목록이 비어 있어요 → [캐릭터 관리] 탭에서 등록해 주세요.",
                     bg=PANEL, fg="#b91c1c",
                     font=(self.base, 11, "bold")).pack(anchor="w", padx=18, pady=8)
            self.matched_label = None
            return

        self.heading("사용 가능한 상위")
        self.matched_label = tk.Label(self, text="글자를 뽑으면 여기에 나옵니다.",
                                      bg=PANEL, fg=MUTED, justify="left",
                                      font=(self.base, 11), wraplength=880)
        self.matched_label.pack(anchor="w", padx=30, pady=(0, 2))
        self.hint("여기 뜬 상위들만 써서 클리어하면 됩니다.")

    def roll_letter(self, index):
        cell = self.letter_cells[index]
        used = [l for l in self.letters if l]
        letter = self.app.roller.pick_letter(exclude=used)
        if letter is None:
            cell["value"].configure(text="–", fg=MUTED)
            sound.thud()
            return

        def done():
            self.letters[index] = letter
            self._refresh_matched()

        self.spin("letter:%d" % index, cell["value"], self.letters_pool, letter,
                  button=cell["btn"], fg=ACCENT, on_done=done)

    def _matched(self):
        return self.app.roller.matched_uppers([l for l in self.letters if l])

    def _refresh_matched(self):
        if self.matched_label is None:
            return
        matched = self._matched()
        if not matched:
            self.matched_label.configure(text="글자를 뽑으면 여기에 나옵니다.", fg=MUTED)
            return
        self.matched_label.configure(
            text="(%d마리)   " % len(matched)
                 + "   ·   ".join("%s [%s]" % (n, "".join(h)) for n, h in matched),
            fg=INK)

    def summary(self):
        res = DrawResult(self.app.current_title, desc=self.content.get("desc", ""))
        picked = [l for l in self.letters if l]
        res.head("상위 이름에서 %d글자 뽑기" % self.count)
        res.item("뽑힌 글자  ▶   %s" % (" ,  ".join(picked) if picked else "아직 안 뽑음"))
        if not self.letters_pool:
            res.warn("상위 목록이 비어 있어요 → [캐릭터 관리] 탭에서 등록해 주세요.")
            return res
        matched = self._matched()
        res.head("사용 가능한 상위 (%d마리)" % len(matched))
        for name, hit in matched:
            res.item("%s   (%s)" % (name, "·".join(hit)))
        res.note("위 상위들만 써서 클리어하면 됩니다.")
        return res


# --------------------------------------------------------- 내가 제일 운 없어
class UnluckyPanel(SpinPanel):
    title = "내가 제일 운 없어"

    def build(self):
        roller = self.app.roller
        self.lo, self.hi = roller.unlucky_range()
        self.colors = roller._colors()
        self.rows = {}

        self.heading("색깔별로 행운의 토큰을 뽑으세요  ( %d ~ %d )" % (self.lo, self.hi))

        grid = tk.Frame(self, bg=PANEL)
        grid.pack(anchor="w", padx=18, pady=(4, 0))

        for col, color in enumerate(self.colors):
            hex_color = COLOR_HEX.get(color, INK)
            card = tk.Frame(grid, bg=PANEL, highlightthickness=1,
                            highlightbackground=LINE)
            card.grid(row=0, column=col, padx=6, pady=4, sticky="n")

            tk.Label(card, text=color, bg=PANEL, fg=hex_color,
                     font=(self.base, 12, "bold")).pack(pady=(8, 2))
            value = tk.Label(card, text="–", bg=SOFT, fg=MUTED, width=3,
                             font=(self.base, 30, "bold"),
                             highlightthickness=1, highlightbackground=LINE)
            value.pack(padx=14)
            coins = tk.Canvas(card, width=110, height=22, bg=PANEL,
                              highlightthickness=0, bd=0)
            coins.pack(pady=(6, 0))
            mark = tk.Label(card, text=" ", bg=PANEL, fg=ACCENT, height=1,
                            font=(self.base, 10, "bold"))
            mark.pack()
            btn = ttk.Button(card, text="토큰 뽑기", style="Slot.TButton",
                             command=lambda c=color: self.roll(c))
            btn.pack(fill="x", padx=10, pady=(6, 2))
            again = ttk.Button(card, text="스토리 과반 → 재뽑기", style="Extra.TButton",
                               state="disabled",
                               command=lambda c=color: self.reroll(c))
            again.pack(fill="x", padx=10, pady=(0, 10))

            self.rows[color] = {"value": value, "coins": coins, "mark": mark,
                                "btn": btn, "again": again, "n": None,
                                "rerolled": False}

        self.verdict = tk.Label(self, text="", bg=PANEL, fg=ACCENT_DK,
                                font=(self.base, 12, "bold"))
        self.verdict.pack(anchor="w", padx=18, pady=(10, 0))
        self.hint("제일 운 없는 사람은 스토리를 과반 이상 먹으면 [재뽑기] 로 토큰을 한 번 더 뽑을 수 있습니다.")

    def _coins(self, color, count):
        canvas = self.rows[color]["coins"]
        canvas.delete("all")
        for i in range(count):
            x = 12 + i * 19
            canvas.create_oval(x - 8, 3, x + 8, 19, fill=GOLD, outline="#7a5a10")
            canvas.create_text(x, 11, text="₩", fill="#7a5a10",
                               font=(self.base, 8, "bold"))
        if count == 0:
            canvas.create_text(55, 11, text="토큰 없음", fill=MUTED,
                               font=(self.base, 9))

    def roll(self, color, key="unlucky", button_key="btn", once=False):
        row = self.rows[color]
        value = self.app.roller.roll((self.lo, self.hi))

        def done():
            row["n"] = value
            self._coins(color, value)
            self._verdict()

        self.spin("%s:%s" % (key, color), row["value"],
                  list(range(self.lo, self.hi + 1)), value,
                  button=row[button_key], once=once,
                  fg=COLOR_HEX.get(color, ACCENT), on_done=done,
                  end_sound=sound.thud if value == self.lo else None)

    def reroll(self, color):
        """제일 운 없는 사람이 스토리를 과반 이상 먹었을 때 한 번 더."""
        row = self.rows[color]
        if row["rerolled"] or str(row["again"].cget("state")) != "normal":
            return
        row["rerolled"] = True
        self.roll(color, key="reroll", button_key="again", once=True)

    def _verdict(self):
        rolled = {c: r["n"] for c, r in self.rows.items() if r["n"] is not None}
        for row in self.rows.values():
            row["mark"].configure(text=" ")
        if len(rolled) < len(self.colors):
            self.verdict.configure(text="%d / %d 명 뽑음"
                                        % (len(rolled), len(self.colors)), fg=MUTED)
            return
        fewest = min(rolled.values())
        losers = [c for c in self.colors if rolled[c] == fewest]
        for color, row in self.rows.items():
            is_loser = color in losers
            row["mark"].configure(text="제일 운 없어" if is_loser else " ")
            if not row["rerolled"]:
                row["again"].configure(state="normal" if is_loser else "disabled")
        self.verdict.configure(
            text="제일 운 없는 사람   ▶   %s   (토큰 %d개)"
                 % (" · ".join(losers), fewest), fg=ACCENT_DK)

    def summary(self):
        res = DrawResult(self.app.current_title, desc=self.content.get("desc", ""))
        res.head("행운의 토큰  ( %d ~ %d )" % (self.lo, self.hi))
        rolled = {}
        for color in self.colors:
            n = self.rows[color]["n"]
            if n is not None:
                rolled[color] = n
            res.item("%s  :  %s" % (color, "아직 안 뽑음" if n is None else "%d개" % n),
                     color=color)
        if len(rolled) == len(self.colors):
            fewest = min(rolled.values())
            losers = [c for c in self.colors if rolled[c] == fewest]
            res.head("제일 운 없는 사람")
            res.item("▶  %s   (토큰 %d개)" % (" · ".join(losers), fewest))
        res.note("행운의 토큰을 쓰지 않고 클리어하면, 가진 토큰 숫자만큼 유카를 줄일 수 있습니다.")
        return res


PANELS = {
    "altitude": AltitudePanel,
    "your_tier": TierPanel,
    "jits_dice": JitsDicePanel,
    "must_char": MustCharPanel,
    "ban_char": BanCharPanel,
    "nyehyung": NyehyungPanel,
    "unlucky": UnluckyPanel,
}
