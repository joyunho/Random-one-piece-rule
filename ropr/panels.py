# -*- coding: utf-8 -*-
"""버튼을 하나씩 눌러서 뽑는 결과 화면들.

메인 뽑기에서 아래 컨텐츠가 나오면 글자만 찍는 대신 이 패널이 뜬다.
    4인 강제전 / 인생의고도전 / 너의상위는 / 지츠'다이스'룰 /
    이캐릭들필수·금지에요 / 녜힁제조기 / 필수!랜덤유닛획득 / 개인미션전
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
        """검증 상태 배지 + 이 룰이 뭐 하는 룰인지 맨 위에 적어준다."""
        from . import data as _data
        text = (self.content.get("desc") or "").strip()
        status = _data.CONTENT_STATUS.get(self.content.get("id"), "custom")
        if not text and status not in _data.STATUS_LABEL:
            return

        box = tk.Frame(self, bg="#f5f7fb")
        box.pack(fill="x", padx=18, pady=(12, 0))
        tk.Label(box, text=" %s " % _data.STATUS_LABEL[status], bg="#f5f7fb",
                 fg=_data.STATUS_COLOR[status],
                 font=(self.base, 9, "bold")).pack(side="left", padx=(12, 8), pady=8)
        tk.Label(box, text=text or "세부 룰이 확인되지 않았습니다.",
                 bg="#f5f7fb", fg="#41506b", justify="left",
                 wraplength=820, font=(self.base, 10), anchor="w").pack(
                     side="left", pady=8, padx=(0, 12))

    # ------------------------------------------------------------- 하위 클래스용
    def build(self):
        raise NotImplementedError

    def summary(self):
        """기록/복사에 쓸 현재 상태."""
        raise NotImplementedError

    # ---------------------------------------------------------------- 연출
    def spin(self, key, label, frames, final, button=None, once=False,
             fg=None, badge=None, badge_unit=None, on_done=None, end_sound=None,
             cast=None):
        """label 의 글자를 frames 안에서 촤르륵 바꾸다가 final 에서 멈춘다.

        cast 를 주면 방송 창의 같은 이름 칸도 프레임마다 같이 돌아간다.
        (예: cast="빨강" 이면 방송 창의 빨강 카드)
        """
        if key in self._busy:
            return
        self._busy.add(key)
        if button is not None:
            button.configure(state="disabled")
        frames = [f for f in frames if f is not None] or [final]

        # 긴장감 트랙 한 덩어리를 여기서 한 번만 튼다. 틱과 마지막 화음까지
        # 미리 섞여 있어서, 트랙이 깔리면 프레임마다 소리를 낼 필요가 없다.
        # (winsound 는 새 소리를 틀면 앞의 소리를 끊어 버린다)
        track = sound.spin_start("settle", sound.SPIN_PANEL)

        def step(delay, n):
            if delay > 235:
                label.configure(text=str(final), fg=fg or ACCENT)
                if badge is not None:
                    badge.show(badge_unit, config_path=self.app.config_path)
                self._busy.discard(key)
                if button is not None and not once:
                    button.configure(state="normal")   # once=True 면 한 번만 눌린다
                if cast:
                    self.app.cast_live(cast, str(final), False)
                if end_sound is not None:
                    end_sound()          # 꽝처럼 따로 정한 소리는 그대로
                elif not track:
                    sound.settle()       # 트랙이 안 깔렸을 때만
                if on_done:
                    on_done()
                self.app.refresh_panel_history()
                return
            text = str(random.choice(frames))
            label.configure(text=text, fg=MUTED)
            if cast:
                self.app.cast_live(cast, text, True)
            if badge is not None:
                badge.show(None, spinning=True)
            if not track and n % 2 == 0:
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
        self.extra_span = roller.altitude_extra_range()   # 미확인이면 None
        self.colors = roller._colors()
        self.rows = {}
        self.eligible = None      # 졸업보상이 가장 늦은 1명

        self.heading("색깔별로 고도를 뽑으세요  ( %d ~ %d )" % (self.lo, self.hi))

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
            pick_btn = ttk.Button(card, text="졸업보상 꼴찌", style="Extra.TButton",
                                  command=lambda c=color: self.set_eligible(c))
            pick_btn.pack(fill="x", padx=10, pady=(0, 2))
            extra_btn = ttk.Button(card, text="추가 추첨", style="Extra.TButton",
                                   state="disabled",
                                   command=lambda c=color: self.roll_extra(c))
            extra_btn.pack(fill="x", padx=10, pady=(0, 10))

            self.rows[color] = {
                "gauge": gauge, "total": total, "detail": detail,
                "base_btn": base_btn, "pick_btn": pick_btn, "extra_btn": extra_btn,
                "base": None, "extra": None,
            }

        self.note_label = tk.Label(self, text="", bg=PANEL, fg=ACCENT_DK,
                                   font=(self.base, 11, "bold"))
        self.note_label.pack(anchor="w", padx=18, pady=(10, 0))

        if self.extra_span is None:
            self.hint("추가 추첨 범위가 영상에서 확인되지 않았습니다. "
                      "[설정] 탭에서 범위를 정해야 추가 추첨을 할 수 있습니다.")
        else:
            self.hint("졸업보상을 가장 늦게 받은 사람을 [졸업보상 꼴찌] 로 지정하면 "
                      "그 사람만 추가 추첨(%d~%d)을 한 번 할 수 있습니다." % self.extra_span)

    def set_eligible(self, color):
        """추가 추첨 자격자를 운영자가 지정한다."""
        self.eligible = color
        for name, row in self.rows.items():
            is_it = name == color
            row["pick_btn"].configure(state="disabled" if is_it else "normal")
            can_extra = is_it and row["base"] is not None and \
                self.extra_span is not None and row["extra"] is None
            row["extra_btn"].configure(state="normal" if can_extra else "disabled")
        self.note_label.configure(text="졸업보상 꼴찌 : %s" % color)
        self.app.refresh_panel_history()

    def _redraw(self, color):
        row = self.rows[color]
        base, extra = row["base"], row["extra"]
        total = (base or 0) + (extra or 0)
        row["total"].configure(text=str(total), fg=COLOR_HEX.get(color, ACCENT))
        row["detail"].configure(
            text="%d + %d" % (base, extra) if extra is not None else "")
        top = self.hi + (self.extra_span[1] if self.extra_span else 0)
        row["gauge"].draw(total, top)

    def roll_base(self, color):
        row = self.rows[color]
        if row["base"] is not None:
            return
        value = self.app.roller.roll((self.lo, self.hi))

        def done():
            row["base"] = value
            self._redraw(color)
            if self.eligible == color and self.extra_span is not None:
                row["extra_btn"].configure(state="normal")

        self.spin("base:" + color, row["total"], list(range(self.lo, self.hi + 1)),
                  value, cast=color, button=row["base_btn"], once=True,
                  fg=COLOR_HEX.get(color, ACCENT), on_done=done)

    def roll_extra(self, color):
        row = self.rows[color]
        if row["base"] is None or row["extra"] is not None:
            return
        if self.eligible != color or self.extra_span is None:
            return
        lo, hi = self.extra_span
        value = self.app.roller.roll((lo, hi))
        frames = ["+%d" % n for n in range(lo, hi + 1)]

        def done():
            row["extra"] = value
            self._redraw(color)

        self.spin("extra:" + color, row["total"], frames, "+%d" % value, cast=color,
                  button=row["extra_btn"], once=True, fg=GOLD, on_done=done)

    def summary(self):
        res = DrawResult(self.app.current_title, desc=self.content.get("desc", ""))
        res.head("인생의 고도  ( %d ~ %d )" % (self.lo, self.hi))
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
        if self.eligible:
            res.head("졸업보상 꼴찌 (추가 추첨 자격)")
            res.item("▶  졸업보상 꼴찌 :  %s" % self.eligible)
        if self.extra_span is None:
            res.warn("추가 추첨 범위가 정해지지 않았어요 → [설정] 탭에서 지정해 주세요.")
        return res


# ------------------------------------------------------------------- 너의상위는
class TierPanel(SpinPanel):
    title = "너의 상위는"

    def build(self):
        roller = self.app.roller
        self.lo, self.hi = roller.tier_range()
        self.zero = roller.tier_zero_roll()
        self.colors = roller._colors()
        self.rows = {}

        self.heading("색깔별로 %d ~ %d 를 뽑으세요.  %d 가 나오면 상위 없음(0상위)입니다."
                     % (self.lo, self.hi, self.zero))

        grid = tk.Frame(self, bg=PANEL)
        grid.pack(anchor="w", padx=18, pady=(4, 0))

        for col, color in enumerate(self.colors):
            hex_color = COLOR_HEX.get(color, INK)
            card = tk.Frame(grid, bg=PANEL, highlightthickness=1,
                            highlightbackground=LINE)
            card.grid(row=0, column=col, padx=6, pady=4, sticky="n")

            tk.Label(card, text=color, bg=PANEL, fg=hex_color,
                     font=(self.base, 12, "bold")).pack(pady=(8, 2))
            # 먼저 크게 뜨는 눈금
            value = tk.Label(card, text="–", bg=SOFT, fg=MUTED, width=3,
                             font=(self.base, 30, "bold"),
                             highlightthickness=1, highlightbackground=LINE)
            value.pack(padx=14)
            # 한 박자 뒤에 뜨는 실제 상위 개수
            applied = tk.Label(card, text=" ", bg=PANEL, fg=MUTED, height=1,
                               font=(self.base, 13, "bold"))
            applied.pack(pady=(6, 0))
            btn = ttk.Button(card, text="뽑 기", style="Slot.TButton",
                             command=lambda c=color: self.roll(c))
            btn.pack(fill="x", padx=10, pady=(6, 10))

            self.rows[color] = {"value": value, "applied": applied, "btn": btn,
                                "raw": None, "n": None}

        self.hint("눈금이 먼저 뜨고, 잠시 뒤에 적용 상위 개수가 나옵니다.")

    def roll(self, color):
        row = self.rows[color]
        if row["raw"] is not None:
            return
        raw = self.app.roller.roll((self.lo, self.hi))
        applied = self.app.roller.applied_tier(raw)
        zero = applied == 0

        def done():
            row["raw"] = raw
            row["n"] = applied
            # 눈금을 보여준 뒤 한 박자 쉬고 적용 결과를 공개한다
            self._jobs.append(self.after(
                600, lambda: self._show_applied(color, raw, applied, zero)))

        self.spin("tier:" + color, row["value"], list(range(self.lo, self.hi + 1)),
                  raw, cast=color, button=row["btn"], once=True,
                  fg=GOLD if zero else COLOR_HEX.get(color, ACCENT), on_done=done)

    def _show_applied(self, color, raw, applied, zero):
        row = self.rows[color]
        row["applied"].configure(
            text="%d  →  상위 %d %s" % (raw, applied, "(없음)" if zero else ""),
            fg=GOLD if zero else INK)
        (sound.taunt if zero else sound.settle)()
        self.app.refresh_panel_history()

    def summary(self):
        res = DrawResult(self.app.current_title, desc=self.content.get("desc", ""))
        res.head("너의 상위는  ( %d ~ %d 뽑기,  %d 는 0상위 )"
                 % (self.lo, self.hi, self.zero))
        for color in self.colors:
            row = self.rows[color]
            if row["raw"] is None:
                res.item("%s  :  아직 안 뽑음" % color, color=color)
            else:
                res.item("%s  :  %d  →  상위 %d" % (color, row["raw"], row["n"]),
                         color=color)
        return res


# ----------------------------------------------------------------- 4인 강제전
class Force4Panel(SpinPanel):
    title = "4인 강제전"

    def build(self):
        self.pool = self.app.roller._upper_names()
        self.unit = None

        self.heading("버튼을 눌러서 강제로 갈 상위를 뽑으세요")
        row = tk.Frame(self, bg=PANEL)
        row.pack(anchor="w", padx=18, pady=(4, 0))

        card = tk.Frame(row, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        card.grid(row=0, column=0, padx=6, sticky="n")

        self.badge = images.Badge(card, size=72, bg=PANEL)
        self.badge.pack(pady=(12, 6))
        self.name = tk.Label(card, text="–", bg=SOFT, fg=MUTED, width=24,
                             font=(self.base, 14, "bold"), wraplength=230,
                             highlightthickness=1, highlightbackground=LINE, pady=6)
        self.name.pack(padx=14)
        self.btn = ttk.Button(card, text="뽑 기", style="Slot.TButton",
                              command=self.roll)
        self.btn.pack(fill="x", padx=14, pady=(8, 12))

        if not self.pool:
            self.btn.configure(state="disabled")
            self.name.configure(text="(등록된 상위 없음)")
            tk.Label(self, text="상위 목록이 비어 있어요 → [캐릭터 관리] 탭에서 등록해 주세요.",
                     bg=PANEL, fg="#b91c1c",
                     font=(self.base, 11, "bold")).pack(anchor="w", padx=18, pady=8)
            return

        self.hint("여기 뜬 상위로 4명 모두 강제로 갑니다.")

    def roll(self):
        unit = self.app.roller.pick_any_upper()
        if unit is None:
            return

        def done():
            self.unit = unit

        self.spin("force4", self.name, self.pool, unit, button=self.btn, once=True,
                  cast="강제 상위",
                  fg=INK, badge=self.badge, badge_unit=unit, on_done=done)

    def summary(self):
        res = DrawResult(self.app.current_title, desc=self.content.get("desc", ""))
        res.head("상위 중에서 한 마리 뽑기")
        if not self.pool:
            res.warn("상위 목록이 비어 있어요 → [캐릭터 관리] 탭에서 등록해 주세요.")
            return res
        res.item("▶  %s" % (self.unit or "아직 안 뽑음"))
        if self.unit:
            res.note("4명 모두 이 상위로 갑니다.")
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
        self.reserved = {}   # 애니메이션 중에도 같은 상위가 또 뽑히지 않게

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
        if slot["unit"] is not None:
            return
        taken = [s["unit"] for g, s in self.slots.items() if g != grade and s["unit"]]
        taken += [u for g, u in self.reserved.items() if g != grade and u]
        unit = self.app.roller.pick_upper(grade, exclude=taken)
        if unit is None:
            unit = self.app.roller.pick_upper(grade) or "(없음)"
        frames = self.by_grade.get(grade) or [unit]
        self.reserved[grade] = unit

        def done():
            slot["unit"] = unit

        self.spin("unit:" + grade, slot["name"], frames, unit, cast=grade,
                  button=slot["btn"], once=True, fg=INK, badge=slot["badge"],
                  badge_unit=unit, on_done=done)

    def roll_dice(self, color):
        cell = self.dice[color]
        value = self.app.roller.roll(self.dice_span)
        lo, hi = self.dice_span

        def done():
            cell["n"] = value
            self._show_order()

        self.spin("dice:" + color, cell["value"], list(range(lo, hi + 1)), value,
                  cast=color,
                  button=cell["btn"], once=True,
                  fg=COLOR_HEX.get(color, ACCENT), on_done=done)

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

    def _slot_title(self, key):
        """설정키('legend_chars') -> 화면에 쓰는 이름('전설'). 방송 릴 이름표용."""
        for title, spec_key, _count in self.specs:
            if spec_key == key:
                return title
        return key

    def build(self):
        roller = self.app.roller
        self.specs = tuple((title, key, roller._int(count_key, default))
                           for title, key, count_key, default in self.spec_keys)
        self.slots = {}
        # 버튼을 누른 순간 바로 잡아두는 이름들. 애니메이션이 끝나기 전에
        # 다음 버튼을 눌러도 같은 캐릭터가 또 뽑히지 않게 한다.
        self.reserved = {}

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
        """이미 공개된 것 + 방금 눌러서 잡아둔 것."""
        shown = [s["value"] for (k, _i), s in self.slots.items()
                 if k == key and s["value"]]
        return shown + list(self.reserved.get(key, []))

    def _reveal_slot(self, key, index, picked):
        slot = self.slots[(key, index)]
        self.reserved.setdefault(key, []).append(picked)
        frames = self.app.roller.cfg.get(key) or [picked]

        def done():
            slot["value"] = picked

        # once=True : 한 번 뽑은 칸은 잠긴다 (원하는 이름 나올 때까지 다시 못 뽑음)
        self.spin("%s:%d" % (key, index), slot["name"], frames, picked,
                  cast="%s %d" % (self._slot_title(key), index + 1),
                  button=slot["btn"], once=True, fg=INK, on_done=done)

    def roll(self, key, index):
        slot = self.slots[(key, index)]
        if slot["value"] is not None:
            return
        picked = self.app.roller.pick_char(key, exclude=self._taken(key))
        if picked is None:
            slot["name"].configure(text="(더 뽑을 캐릭터 없음)", fg=MUTED)
            sound.thud()
            return
        self._reveal_slot(key, index, picked)

    def roll_all(self, key, count):
        """빈 칸을 한꺼번에. 결과를 먼저 중복 없이 확정하고 공개만 애니메이션으로."""
        empty = [i for i in range(count) if self.slots[(key, i)]["value"] is None]
        empty = [i for i in empty if "%s:%d" % (key, i) not in self._busy]
        if not empty:
            return
        picked = self.app.roller.pick_chars(key, len(empty),
                                            exclude=self._taken(key))
        if not picked:
            sound.thud()
            return
        for index, unit in zip(empty, picked):
            self._reveal_slot(key, index, unit)

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
        self.reserved_letters = []   # 누른 순간 바로 잡아둔다
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
        if self.letters[index] is not None:
            return
        used = [l for l in self.letters if l] + list(self.reserved_letters)
        letter = self.app.roller.pick_letter(exclude=used)
        if letter is None:
            cell["value"].configure(text="–", fg=MUTED)
            sound.thud()
            return
        self.reserved_letters.append(letter)

        def done():
            self.letters[index] = letter
            self._refresh_matched()

        self.spin("letter:%d" % index, cell["value"], self.letters_pool, letter,
                  cast="%d번째 글자" % (index + 1),
                  button=cell["btn"], once=True, fg=ACCENT, on_done=done)

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


class PersonalMissionPanel(SpinPanel):
    """미션 내용은 비밀이라 뽑지 않는다. 성공/실패 체크와 유카 계산만 해준다."""

    title = "개인미션전"

    def build(self):
        roller = self.app.roller
        self.colors = roller._colors()
        self.count = roller.mission_count()
        self.penalty = roller.mission_penalty()
        self.rows = {}

        self.heading("미션 %d개 · 실패 1개당 유카 +%d   (미션 내용은 각자만 압니다)"
                     % (self.count, self.penalty))
        grid = tk.Frame(self, bg=PANEL)
        grid.pack(anchor="w", padx=18, pady=(4, 0))

        for col, color in enumerate(self.colors):
            tone = COLOR_HEX.get(color, INK)
            card = tk.Frame(grid, bg=PANEL, highlightthickness=1,
                            highlightbackground=LINE)
            card.grid(row=0, column=col, padx=6, pady=4, sticky="n")
            tk.Label(card, text=color, bg=PANEL, fg=tone,
                     font=(self.base, 12, "bold")).pack(pady=(8, 4))

            marks = []
            for i in range(self.count):
                var = tk.BooleanVar(value=False)
                chk = ttk.Checkbutton(
                    card, text="미션 %d 실패" % (i + 1), style="Card.TCheckbutton",
                    variable=var, command=lambda c=color: self._recalc(c))
                chk.pack(anchor="w", padx=12)
                marks.append(var)

            total = tk.Label(card, text="유카 +0", bg=SOFT, fg=MUTED, width=10,
                             font=(self.base, 15, "bold"),
                             highlightthickness=1, highlightbackground=LINE, pady=3)
            total.pack(padx=12, pady=(8, 12))
            self.rows[color] = {"marks": marks, "total": total}

        self.team = tk.Label(self, text="팀 합계 유카 +0", bg=PANEL, fg=ACCENT_DK,
                             font=(self.base, 13, "bold"))
        self.team.pack(anchor="w", padx=18, pady=(12, 0))
        self.hint("종료 후 각자 미션을 공개해서 대조하세요. 경기 자체는 팀전입니다.")

    def _failed(self, color):
        return sum(1 for v in self.rows[color]["marks"] if v.get())

    def _recalc(self, color):
        row = self.rows[color]
        yuka = self._failed(color) * self.penalty
        row["total"].configure(text="유카 +%d" % yuka,
                               fg=ACCENT if yuka else MUTED)
        team = sum(self._failed(c) for c in self.colors) * self.penalty
        self.team.configure(text="팀 합계 유카 +%d" % team)
        self.app.refresh_panel_history()

    def summary(self):
        res = DrawResult(self.app.current_title, desc=self.content.get("desc", ""))
        res.head("비밀 미션 %d개  (실패 1개당 유카 +%d)" % (self.count, self.penalty))
        team = 0
        for color in self.colors:
            failed = self._failed(color)
            team += failed * self.penalty
            res.item("%s  :  실패 %d개  →  유카 +%d"
                     % (color, failed, failed * self.penalty), color=color)
        res.head("팀 합계")
        res.item("▶  팀 합계 유카 +%d" % team)
        res.note("미션 내용은 각자만 압니다. 종료 후 공개해서 대조하세요.")
        return res


PANELS = {
    "force4": Force4Panel,
    "altitude": AltitudePanel,
    "your_tier": TierPanel,
    "jits_dice": JitsDicePanel,
    "must_char": MustCharPanel,
    "ban_char": BanCharPanel,
    "nyehyung": NyehyungPanel,
    "personal_mission": PersonalMissionPanel,
}
