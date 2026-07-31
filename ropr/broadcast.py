# -*- coding: utf-8 -*-
"""방송 출력 창.

OBS 로 캡처할 별도 창. 운영자 창에서 뽑은 결과만 크게 보여 준다.
버튼도, 설정도, 파일 경로도 없다.

  - 어두운 배경 + 큰 글씨 + 색깔별 카드
  - 값이 정해지는 순간 번쩍이는 연출
  - 크로마키(초록) 배경으로 바꿔서 OBS 에서 배경만 빼는 것도 가능
"""

import re
import tkinter as tk

from .data import COLOR_HEX
from .theme import pick_font

# 방송 화면 전용 색 (운영자 창보다 진하고 대비가 세다)
BG_DARK = "#0d1017"
CARD = "#171c26"
CARD_EDGE = "#2b3444"
TEXT = "#f2f5fa"
DIM = "#8b95a7"
HOT = "#ff3b57"
GOLD = "#ffc94a"
CHROMA = "#00b140"          # OBS 크로마키용 초록

PRESETS = (("1280 x 720", 1280, 720), ("1920 x 1080", 1920, 1080))

# 색깔별 밝은 톤 (어두운 배경에서 잘 보이게)
BRIGHT = {
    "빨강": "#ff5c5c",
    "파랑": "#5aa9ff",
    "보라": "#b98cff",
    "노랑": "#ffc94a",
}


def bright(color):
    return BRIGHT.get(color, COLOR_HEX.get(color, TEXT))


# 강원랜디는 운영자 창에서 "강제상위 (5.85%)" 처럼 확률을 같이 보여 준다.
# 방송 화면에서는 확률이 필요 없고 자리만 차지해서 뺀다.
_PERCENT = re.compile(r"\s*\(\s*\d+(?:\.\d+)?\s*%\s*\)")


def strip_percent(text):
    return _PERCENT.sub("", text).strip()


class BroadcastWindow(tk.Toplevel):
    """운영자 창을 따라가는 방송 전용 화면."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.base = pick_font(self)
        self.chroma = False
        self._flash_jobs = []
        # 슬롯 이름 -> 그 값을 보여주는 라벨. 스핀 중에는 이걸 직접 고쳐서
        # 화면을 통째로 다시 그리지 않는다 (다시 그리면 깜빡이고 느리다)
        self._slots = {}
        self._cards = {}
        self._spinning = set()
        self._live_text = {}
        self._reel_job = None
        self._value_size = 40

        self.title("방송 출력 — OBS 로 이 창을 캡처하세요")
        self.minsize(480, 320)
        self.set_preset(1280, 720)
        self.configure(bg=BG_DARK)
        self.protocol("WM_DELETE_WINDOW", self.hide)

        self._build()
        self.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))

    # ------------------------------------------------------------------ 뼈대
    def _build(self):
        self.root_frame = tk.Frame(self, bg=BG_DARK)
        self.root_frame.pack(fill="both", expand=True)

        # 위쪽 : 룰 이름
        self.head = tk.Frame(self.root_frame, bg=BG_DARK)
        self.head.pack(fill="x", side="top", pady=(26, 0))
        self.rule_label = tk.Label(self.head, text="랜 덤  원 피 스  룰", bg=BG_DARK,
                                   fg=TEXT, font=(self.base, 46, "bold"))
        self.rule_label.pack()
        self.desc_label = tk.Label(self.head, text="", bg=BG_DARK, fg=DIM,
                                   font=(self.base, 15), wraplength=1120,
                                   justify="center")
        self.desc_label.pack(pady=(8, 0))
        # 창 크기를 바꿔도 설명이 양옆으로 잘리지 않게
        self._wrap_to_card(self.head, self.desc_label, pad=120)

        # 아래쪽부터 자리를 잡아 둬야 가운데(body)가 남는 공간을 다 먹는다
        self.stage = tk.Label(self.root_frame, text="", bg=BG_DARK, fg=DIM,
                              font=(self.base, 16, "bold"))
        self.stage.pack(side="bottom", pady=(0, 22))

        # 돌아가는 릴 : 지금 뽑고 있는 값이 촤르륵 지나간다
        self.reel = tk.Frame(self.root_frame, bg=BG_DARK)
        self.reel_slot = tk.Label(self.reel, text="", bg=BG_DARK, fg=DIM,
                                  font=(self.base, 20, "bold"))
        self.reel_slot.pack(side="left", padx=(0, 22))
        self.reel_value = tk.Label(self.reel, text="", bg=CARD, fg=TEXT,
                                   font=(self.base, 40, "bold"), padx=28, pady=6,
                                   highlightthickness=3, highlightbackground=CARD_EDGE)
        self.reel_value.pack(side="left")

        # 가운데 : 결과
        self.body = tk.Frame(self.root_frame, bg=BG_DARK)
        self.body.pack(fill="both", expand=True, side="top", padx=40, pady=20)

    # ------------------------------------------------------------------ 조작
    def toggle_fullscreen(self):
        self.attributes("-fullscreen", not self.attributes("-fullscreen"))

    def set_preset(self, width, height):
        """창 크기를 바꾼다. 화면보다 큰 값은 화면 안으로 줄인다.

        1280x720 을 그대로 띄우면 화면이 그보다 좁은 노트북에서 창이 화면
        양옆으로 삐져나가서, 글자 앞뒤가 잘려 보인다. (창 안에서는 멀쩡한데
        화면 밖이라 안 보이는 것) 그래서 화면 크기로 한 번 자른다.
        """
        self.attributes("-fullscreen", False)
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = min(width, screen_w)
        height = min(height, screen_h)
        # 화면 안에 들어오도록 가운데로
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 3)
        self.geometry("%dx%d+%d+%d" % (width, height, x, y))

    def set_chroma(self, on):
        """배경을 크로마키 초록으로. OBS 에서 배경만 빼고 쓸 때."""
        self.chroma = bool(on)
        bg = CHROMA if self.chroma else BG_DARK
        for widget in (self, self.root_frame, self.body, self.stage.master):
            try:
                widget.configure(bg=bg)
            except tk.TclError:
                pass
        for widget in (self.rule_label, self.desc_label, self.stage):
            widget.configure(bg=bg)
        for child in self.rule_label.master.winfo_children():
            try:
                child.configure(bg=bg)
            except tk.TclError:
                pass
        self.rule_label.master.configure(bg=bg)
        self.render()

    def hide(self):
        self.withdraw()

    def show(self):
        self.deiconify()
        self.lift()

    # ------------------------------------------------------------- 돌아가는 연출
    def live(self, slot, text, spinning):
        """운영자 창에서 값이 촤르륵 돌 때마다 방송 화면도 같이 돌린다.

        화면을 다시 그리지 않고 해당 라벨의 글자만 바꾼다.
        slot 은 '빨강' 처럼 카드 이름이고, 없으면 릴만 돌아간다.
        """
        if not self.winfo_exists():
            return
        if spinning:
            self._spinning.add(slot)
        else:
            self._spinning.discard(slot)

        self._reel(slot, text, spinning)

        self._live_text[slot] = (text, spinning)
        entry = self._slots.get(slot)
        if entry is not None:
            label, prefix = entry
            label.configure(text=prefix + text,
                            fg=DIM if spinning else TEXT,
                            font=(self.base, self._value_size, "bold"))
        card = self._cards.get(slot)
        if card is not None:
            card.configure(highlightbackground=(
                GOLD if spinning else bright(slot)),
                highlightthickness=6 if spinning else 3)
            if not spinning:
                self._flash_jobs.append(self.after(
                    260, lambda c=card, s=slot: self._card_calm(c, s)))

    def _card_calm(self, card, slot):
        try:
            card.configure(highlightbackground=bright(slot), highlightthickness=3)
        except tk.TclError:
            pass

    def _reel(self, slot, text, spinning):
        """아래쪽 릴. 돌 때는 흐리게, 멈추면 금색으로 '탁' 박힌다."""
        if self._reel_job is not None:
            try:
                self.after_cancel(self._reel_job)
            except Exception:
                pass
            self._reel_job = None

        if not self.reel.winfo_ismapped():
            self.reel.pack(side="bottom", pady=(0, 10))
        self.reel_slot.configure(text=slot or "", fg=bright(slot) if slot else DIM,
                                 bg=self._bg())
        self.reel.configure(bg=self._bg())
        if spinning:
            self.reel_value.configure(text=text, fg=DIM, bg=CARD,
                                      highlightbackground=CARD_EDGE)
        else:
            self.reel_value.configure(text=text, fg=GOLD, bg=CARD,
                                      highlightbackground=GOLD)
            # 잠깐 보여주고 치운다
            self._reel_job = self.after(1400, self._hide_reel)

    def _hide_reel(self):
        self._reel_job = None
        try:
            if not self._spinning:
                self.reel.pack_forget()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ 그리기
    def _bg(self):
        return CHROMA if self.chroma else BG_DARK

    def clear_body(self):
        for job in self._flash_jobs:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self._flash_jobs = []
        self._slots = {}
        self._cards = {}
        for child in self.body.winfo_children():
            child.destroy()

    def render(self):
        """운영자 창의 현재 상태를 그대로 다시 그린다."""
        result = self.app.last_result
        self.rule_label.configure(text=self.app.current_title or "랜 덤  원 피 스  룰",
                                  fg=HOT if self.app.current_title else TEXT)
        desc = (result.desc if result is not None else "") or ""
        self.desc_label.configure(text=" ".join(desc.split()))

        self.clear_body()
        if result is None:
            self.stage.configure(text="")
            return

        colored = [l for l in result.lines if l.color]
        if colored:
            self._draw_players(colored, result)
        else:
            self._draw_lines(result)

        # 아직 돌고 있는 칸은 방금 다시 그리면서 '아직 안 뽑음' 으로 되돌아간다.
        # 돌던 글자를 다시 얹어 줘야 화면이 깜빡이지 않는다.
        for slot in list(self._spinning):
            live = self._live_text.get(slot)
            entry = self._slots.get(slot)
            if live and entry:
                label, prefix = entry
                label.configure(text=prefix + live[0], fg=DIM)

        done = len([l for l in result.lines
                    if l.kind == "item" and "아직" not in l.text])
        total = len([l for l in result.lines if l.kind == "item"])
        self.stage.configure(
            text=("공개 %d / %d" % (done, total)) if total else "")

    @staticmethod
    def _wrap_to_card(card, label, pad=32):
        """카드가 실제로 배치/리사이즈될 때마다 글자 줄바꿈 폭을 맞춘다."""
        last = [None]

        def on_configure(event):
            # 줄바꿈 폭을 바꾸면 카드 크기가 또 변할 수 있어서 <Configure> 가
            # 다시 들어온다. 폭이 진짜 달라졌을 때만 손대서 되돌이를 막는다.
            if last[0] == event.width:
                return
            last[0] = event.width
            try:
                label.configure(wraplength=max(120, event.width - pad))
            except tk.TclError:      # 이미 지워진 카드
                pass
        # add="+" : 한 프레임에 여러 줄을 매달 때 앞의 것이 지워지지 않게
        card.bind("<Configure>", on_configure, add="+")

    def _draw_players(self, colored, result):
        """색깔별 결과는 크기가 똑같은 카드 네 장으로."""
        wrap = tk.Frame(self.body, bg=self._bg())
        wrap.pack(expand=True, fill="both")

        values = []
        for line in colored:
            text = line.text.split(":", 1)[1].strip() if ":" in line.text else line.text
            text = strip_percent(text)
            # 아직 안 뽑은 칸은 방송에서 '?' 하나로. 글자를 그대로 두면
            # 카드 네 장의 글자 크기가 그 문구에 맞춰 작아진다.
            values.append("?" if "아직" in text else text)

        # 글자 크기는 카드마다 따로 정하지 않고, 제일 긴 값 하나에 맞춰 통일한다
        # ('?' 는 자리만 지키는 값이라 크기 계산에서 뺀다)
        real = [v for v in values if v != "?"]
        longest = max((len(v) for v in real), default=1)
        size = 64 if longest <= 4 else (40 if longest <= 10 else
                                        (28 if longest <= 18 else 20))
        self._value_size = size

        # 카드 폭에 맞춰 글자를 줄바꿈한다.
        # width 를 글자 수로 주면 폰트 크기와 안 맞아서 양옆이 잘리고,
        # 여기서 update_idletasks() 를 부르면 그리는 도중에 render() 가 다시
        # 들어와 방금 만든 프레임이 지워진다. 그래서 카드가 실제로 배치될 때
        # <Configure> 로 알려 주는 픽셀 폭을 쓴다.
        for col, (line, value) in enumerate(zip(colored, values)):
            wrap.grid_columnconfigure(col, weight=1, uniform="cast")
            card = tk.Frame(wrap, bg=CARD, highlightthickness=3,
                            highlightbackground=bright(line.color))
            card.grid(row=0, column=col, padx=12, pady=10, sticky="nsew")

            tk.Label(card, text=line.color, bg=CARD, fg=bright(line.color),
                     font=(self.base, 26, "bold")).pack(pady=(22, 6))
            value_label = tk.Label(card, text=value, bg=CARD,
                                   fg=DIM if value == "?" else TEXT,
                                   font=(self.base, 64 if value == "?" else size,
                                         "bold"),
                                   justify="center")
            value_label.pack(expand=True, fill="x", pady=(0, 24), padx=12)
            self._wrap_to_card(card, value_label)
            # 스핀 중에 이 라벨만 바로 고칠 수 있게 기억해 둔다
            self._slots[line.color] = (value_label, "")
            self._cards[line.color] = card
        wrap.grid_rowconfigure(0, weight=1)

        # 색깔 카드 외의 굵은 결론(순서·판정 등)이 있으면 아래에 한 줄
        extra = [l.text for l in result.lines
                 if not l.color and l.kind == "item" and l.text.startswith("▶")]
        for text in extra[:2]:
            tk.Label(self.body, text=text.replace("▶", "").strip(),
                     bg=self._bg(), fg=GOLD,
                     font=(self.base, 26, "bold")).pack(pady=(16, 0))

    def _draw_lines(self, result):
        """색깔이 없는 결과는 큰 글씨 목록으로."""
        wrap = tk.Frame(self.body, bg=self._bg())
        wrap.pack(expand=True, fill="both")

        for line in result.lines:
            if line.kind == "head":
                tk.Label(wrap, text=line.text, bg=self._bg(), fg=DIM,
                         font=(self.base, 16, "bold")).pack(pady=(18, 2))
            elif line.kind == "warn":
                label = tk.Label(wrap, text=line.text, bg=self._bg(), fg=HOT,
                                 font=(self.base, 18, "bold"), wraplength=1100)
                label.pack(pady=4)
                self._wrap_to_card(wrap, label, pad=40)
            elif line.kind == "item":
                text = line.text.replace("▶", "").strip()
                big = line.text.startswith("▶")
                label = tk.Label(wrap, text=text, bg=self._bg(),
                                 fg=GOLD if big else TEXT,
                                 font=(self.base, 44 if big else 22, "bold"),
                                 wraplength=1140)
                label.pack(pady=(4, 2))
                self._wrap_to_card(wrap, label, pad=40)
                # "초월  :  로쿠규초월" 처럼 이름이 붙은 줄은 슬롯으로 잡아 둔다.
                # 그래야 그 줄도 스핀 중에 같이 돌릴 수 있다.
                if ":" in line.text:
                    name = line.text.split(":", 1)[0].strip()
                    self._slots[name] = (label, name + "  :  ")

    # ------------------------------------------------------------------ 연출
    def flash(self):
        """값이 하나 정해질 때 화면을 한 번 번쩍인다."""
        if not self.winfo_viewable():
            return
        original = self.rule_label.cget("fg")

        def back():
            try:
                self.rule_label.configure(fg=original)
            except tk.TclError:
                pass

        self.rule_label.configure(fg=GOLD)
        self._flash_jobs.append(self.after(140, back))
