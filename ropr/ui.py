# -*- coding: utf-8 -*-
"""화면(tkinter GUI)."""

import datetime
import random
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import config as config_mod
from . import broadcast, data, panels, sound
from .engine import Roller
from .theme import (ACCENT, ACCENT_DK, BG, GOLD, INK, LINE, MUTED, PANEL, SOFT,
                    pick_font)


def parse_int(text, fallback):
    try:
        return int(str(text).strip())
    except (TypeError, ValueError):
        return fallback


class ResultView(tk.Text):
    """뽑기 결과를 예쁘게 찍어주는 읽기 전용 텍스트."""

    def __init__(self, master, base, **kw):
        # width/height 를 1로 두어야 pack(expand) 이 창 크기에 맞춰 줄여준다
        kw.setdefault("width", 1)
        kw.setdefault("height", 1)
        super().__init__(
            master, wrap="word", relief="flat", bd=0, highlightthickness=0,
            bg=PANEL, fg=INK, padx=20, pady=14, cursor="arrow", **kw
        )
        self.tag_configure("title", font=(base, 16, "bold"), foreground=ACCENT,
                           spacing1=4, spacing3=8)
        self.tag_configure("desc", font=(base, 10), foreground="#41506b",
                           lmargin1=6, lmargin2=6, spacing1=2, spacing3=6)
        self.tag_configure("head", font=(base, 10, "bold"), foreground="#475569",
                           spacing1=12, spacing3=4)
        self.tag_configure("item", font=(base, 13), foreground=INK,
                           lmargin1=24, lmargin2=24, spacing3=4)
        self.tag_configure("note", font=(base, 10), foreground=MUTED,
                           lmargin1=16, lmargin2=16, spacing1=10)
        self.tag_configure("warn", font=(base, 11, "bold"), foreground="#b91c1c",
                           lmargin1=16, lmargin2=16, spacing1=6)
        for color, value in data.COLOR_HEX.items():
            self.tag_configure("c_" + color, foreground=value,
                               font=(base, 13, "bold"))
        self.configure(state="disabled")

    def show(self, result):
        self.configure(state="normal")
        self.delete("1.0", "end")
        if result is not None:
            self.insert("end", result.title + "\n", "title")
            for line in (result.desc or "").splitlines():
                if line.strip():
                    self.insert("end", line.strip() + "\n", "desc")
            for line in result.lines:
                tags = [line.kind]
                if line.color:
                    tags.append("c_" + line.color)
                self.insert("end", line.text + "\n", tuple(tags))
        self.configure(state="disabled")
        self.see("1.0")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = config_mod.load_config()
        self.roller = Roller(self.cfg)
        self.history = []
        self._spin_job = None
        self._spinning = False
        self._spin_track = False
        self.last_result = None
        self._history_index = None
        self.panel = None
        self.current_title = ""
        self.config_path = config_mod.config_path()
        self.cast = None            # 방송 출력 창 (필요할 때 만든다)

        sound.set_enabled(bool(self.cfg.get("sound", True)))
        sound.set_bgm(bool(self.cfg.get("bgm", True)))

        self.base = pick_font(self)
        self.title("%s  v%s" % (data.APP_TITLE, data.VERSION))
        self.geometry("1000x790")
        self.minsize(900, 680)
        self.configure(bg=BG)

        self._setup_style()
        self._build_header()
        self._build_status()   # 아래쪽부터 자리를 잡아야 창이 좁아져도 안 잘린다
        self._build_notebook()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Return>", self._shortcut_spin)
        self.bind("<space>", self._shortcut_spin)

        # 효과음 WAV 만들기는 창이 뜬 다음에 한 개씩. 한꺼번에 만들면 켤 때 멈춘다.
        self.after(120, self._warm_sounds)

    def _warm_sounds(self):
        if sound.warm_next():
            self.after(20, self._warm_sounds)

    def _shortcut_spin(self, event=None):
        """Enter/Space 단축키. 글자를 입력하는 칸에 있을 때는 무시한다."""
        widget = self.focus_get()
        if isinstance(widget, (tk.Text, tk.Entry, ttk.Entry, ttk.Combobox)):
            return None
        self._spin()
        return "break"

    # ------------------------------------------------------------------ 뼈대
    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        base = self.base
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=INK, font=(base, 10))
        style.configure("Card.TLabel", background=PANEL, foreground=INK, font=(base, 10))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=(base, 9))
        style.configure("Section.TLabel", background=BG, foreground=ACCENT_DK,
                        font=(base, 12, "bold"))
        style.configure("TCheckbutton", background=BG, foreground=INK, font=(base, 10))
        style.configure("Card.TCheckbutton", background=PANEL, foreground=INK, font=(base, 10))
        style.configure("TEntry", fieldbackground="white", font=(base, 10))

        style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(8, 6, 8, 0))
        style.configure("TNotebook.Tab", background="#dfe3ea", foreground="#3f4756",
                        font=(base, 11, "bold"), padding=(20, 9), borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", PANEL)],
                  foreground=[("selected", ACCENT)])

        style.configure("TButton", font=(base, 10), padding=(12, 7),
                        background="#e2e6ed", foreground=INK, borderwidth=0)
        style.map("TButton", background=[("active", "#d0d6e0")])
        style.configure("Big.TButton", font=(base, 17, "bold"), padding=(10, 16),
                        background=ACCENT, foreground="white", borderwidth=0)
        style.map("Big.TButton",
                  background=[("active", ACCENT_DK), ("disabled", "#c9ccd3")])
        style.configure("Go.TButton", font=(base, 12, "bold"), padding=(16, 10),
                        background=ACCENT, foreground="white", borderwidth=0)
        style.map("Go.TButton",
                  background=[("active", ACCENT_DK), ("disabled", "#c9ccd3")])

        # 낱개 뽑기 버튼
        style.configure("Slot.TButton", font=(base, 10, "bold"), padding=(8, 5),
                        background="#e7ebf2", foreground=ACCENT_DK, borderwidth=0)
        style.map("Slot.TButton",
                  background=[("active", "#d5dce8"), ("disabled", "#f0f1f4")],
                  foreground=[("disabled", "#b3b8c2")])
        style.configure("Extra.TButton", font=(base, 10, "bold"), padding=(8, 5),
                        background="#f5e6c8", foreground="#7a5a10", borderwidth=0)
        style.map("Extra.TButton",
                  background=[("active", "#eed9a8"), ("disabled", "#f4f4f6")],
                  foreground=[("disabled", "#b3b8c2")])

        style.configure("Cast.TButton", font=(base, 11, "bold"), padding=(14, 7),
                        background="#8e0a1f", foreground="white", borderwidth=0)
        style.map("Cast.TButton", background=[("active", "#6d0716")])

        style.configure("Treeview", font=(base, 10), rowheight=26,
                        background="white", fieldbackground="white", borderwidth=0)
        style.configure("Treeview.Heading", font=(base, 10, "bold"),
                        background="#e2e6ed", borderwidth=0)

    def _build_header(self):
        bar = tk.Frame(self, bg=ACCENT, height=64)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)
        tk.Label(bar, text="랜 덤  원 피 스  룰", bg=ACCENT, fg="white",
                 font=(self.base, 19, "bold")).pack(side="left", padx=22)
        tk.Label(bar, text="메인 컨텐츠 · 등급 · 강원랜디 뽑기", bg=ACCENT,
                 fg="#ffd9dd", font=(self.base, 10)).pack(side="left", pady=(6, 0))

        ttk.Button(bar, text="방송 창 열기", style="Cast.TButton",
                   command=self.open_cast).pack(side="right", padx=(0, 20), pady=12)

    def _build_notebook(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=14, pady=(10, 4))
        self._build_main_tab()
        self._build_grade_tab()
        self._build_gangwon_tab()
        self._build_chars_tab()
        self._build_settings_tab()
        self._build_history_tab()

    def _build_status(self):
        self.status = ttk.Label(
            self, style="Muted.TLabel",
            text="준비 완료")
        self.status.pack(side="bottom", fill="x", padx=18, pady=(0, 8))

    def _say(self, text):
        self.status.configure(text=text)

    # ------------------------------------------------------------- 방송 출력 창
    def open_cast(self):
        if self.cast is None or not self.cast.winfo_exists():
            self.cast = broadcast.BroadcastWindow(self)
        self.cast.set_chroma(bool(self.cfg.get("cast_chroma", False)))
        self.cast.show()
        self.cast.render()
        self._say("방송 창을 열었습니다. OBS 에서 이 창을 캡처하세요. (F11 전체화면)")

    def _cast_preset(self, width, height):
        self.open_cast()
        self.cast.set_preset(width, height)

    def _cast_chroma(self):
        self.cfg["cast_chroma"] = bool(self.var_chroma.get())
        if self.cast is not None and self.cast.winfo_exists():
            self.cast.set_chroma(self.cfg["cast_chroma"])

    def update_cast(self, flash=False):
        """뽑을 때마다 방송 창을 따라 갱신한다."""
        if self.cast is None or not self.cast.winfo_exists():
            return
        self.cast.render()
        if flash:
            self.cast.flash()

    def _sound_test(self):
        """소리가 안 난다고 할 때 원인을 바로 보여준다."""
        self.sound_msg.configure(text=sound.self_test(),
                                 fg=ACCENT if sound.last_error else MUTED)

    def cast_live(self, slot, text, spinning):
        """스핀 한 프레임마다 방송 창도 같이 돌린다.

        화면을 다시 그리지 않고 글자만 바꾸기 때문에 초당 수십 번 불러도 된다.
        """
        if self.cast is None or not self.cast.winfo_exists():
            return
        try:
            self.cast.live(slot, text, spinning)
        except tk.TclError:      # 방송 창을 닫는 중이면 조용히 넘어간다
            pass

    # ---------------------------------------------------------- 탭 1 메인 뽑기
    def _build_main_tab(self):
        tab = ttk.Frame(self.nb, style="Card.TFrame")
        self.nb.add(tab, text="  메인 뽑기  ")

        top = tk.Frame(tab, bg=PANEL)
        top.pack(fill="x", padx=20, pady=(14, 4))

        self.main_display = tk.Label(
            top, text="뽑기 버튼을 눌러 주세요", bg="#fbfbfd", fg=MUTED,
            font=(self.base, 25, "bold"), height=1, pady=8,
            highlightthickness=1, highlightbackground=LINE)
        self.main_display.pack(fill="x")

        row = tk.Frame(tab, bg=PANEL)
        row.pack(fill="x", padx=20, pady=10)

        self.spin_btn = ttk.Button(row, text="뽑  기  !", style="Big.TButton",
                                   command=self._spin)
        self.spin_btn.pack(side="left", fill="x", expand=True)

        opts = tk.Frame(row, bg=PANEL)
        opts.pack(side="left", padx=(16, 0))
        self.var_animate = tk.BooleanVar(value=bool(self.cfg.get("animate", True)))
        self.var_repeat = tk.BooleanVar(value=bool(self.cfg.get("avoid_repeat", True)))
        ttk.Checkbutton(opts, text="룰렛 연출", style="Card.TCheckbutton",
                        variable=self.var_animate,
                        command=self._sync_toggles).pack(anchor="w")
        ttk.Checkbutton(opts, text="같은 컨텐츠 연속 방지", style="Card.TCheckbutton",
                        variable=self.var_repeat,
                        command=self._sync_toggles).pack(anchor="w")
        self.var_sound = tk.BooleanVar(value=bool(self.cfg.get("sound", True)))
        sound_chk = ttk.Checkbutton(opts, text="효과음", style="Card.TCheckbutton",
                                    variable=self.var_sound, command=self._sync_toggles)
        sound_chk.pack(anchor="w")
        self.var_bgm = tk.BooleanVar(value=bool(self.cfg.get("bgm", True)))
        bgm_chk = ttk.Checkbutton(opts, text="긴장감 BGM", style="Card.TCheckbutton",
                                  variable=self.var_bgm, command=self._sync_toggles)
        bgm_chk.pack(anchor="w")
        if not sound.available():
            for chk in (sound_chk, bgm_chk):
                chk.configure(state="disabled")     # 윈도우가 아니면 소리 없음

        bottom = tk.Frame(tab, bg=PANEL)
        bottom.pack(side="bottom", fill="x", padx=20, pady=(6, 16))
        ttk.Button(bottom, text="결과 복사", command=self._copy_last).pack(side="left")
        ttk.Button(bottom, text="기록 보기",
                   command=lambda: self.nb.select(5)).pack(side="left", padx=8)

        # 결과 자리 : 글자만 찍는 화면과 버튼을 누르는 화면을 갈아 끼운다
        self.result_host = tk.Frame(tab, bg=PANEL)
        self.result_host.pack(fill="both", expand=True, padx=20, pady=(4, 0))

        self.text_wrap = tk.Frame(self.result_host, bg=PANEL, highlightthickness=1,
                                  highlightbackground=LINE)
        self.main_result = ResultView(self.text_wrap, self.base)
        self._attach_scroll(self.text_wrap, self.main_result)
        self.text_wrap.pack(fill="both", expand=True)

        self.panel_wrap = tk.Frame(self.result_host, bg=PANEL, highlightthickness=1,
                                   highlightbackground=LINE)
        self.panel_canvas = tk.Canvas(self.panel_wrap, bg=PANEL, highlightthickness=0)
        panel_sb = ttk.Scrollbar(self.panel_wrap, orient="vertical",
                                 command=self.panel_canvas.yview)
        self.panel_canvas.configure(yscrollcommand=panel_sb.set)
        panel_sb.pack(side="right", fill="y")
        self.panel_canvas.pack(side="left", fill="both", expand=True)
        self.panel_holder = tk.Frame(self.panel_canvas, bg=PANEL)
        self._panel_window = self.panel_canvas.create_window(
            (0, 0), window=self.panel_holder, anchor="nw")
        self.panel_holder.bind(
            "<Configure>",
            lambda e: self.panel_canvas.configure(
                scrollregion=self.panel_canvas.bbox("all")))
        self.panel_canvas.bind(
            "<Configure>",
            lambda e: self.panel_canvas.itemconfigure(self._panel_window, width=e.width))
        self.panel = None

    def _panel(self, parent, **pack_kw):
        """테두리 있는 흰 패널. 안에 들어갈 위젯은 이 프레임을 부모로 만들어야 한다."""
        wrap = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        wrap.pack(**pack_kw)
        return wrap

    @staticmethod
    def _attach_scroll(wrap, widget):
        sb = ttk.Scrollbar(wrap, orient="vertical", command=widget.yview)
        sb.pack(side="right", fill="y")
        widget.configure(yscrollcommand=sb.set)
        widget.pack(side="left", fill="both", expand=True)

    def _sync_toggles(self):
        self.cfg["animate"] = bool(self.var_animate.get())
        self.cfg["avoid_repeat"] = bool(self.var_repeat.get())
        self.cfg["sound"] = bool(self.var_sound.get())
        sound.set_enabled(self.cfg["sound"])
        self.cfg["bgm"] = bool(self.var_bgm.get())
        sound.set_bgm(self.cfg["bgm"])

    def _spin(self):
        if self._spinning:
            return
        if self.nb.index(self.nb.select()) != 0:
            return
        self._sync_toggles()
        content = self.roller.pick_main()
        if content is None:
            self._reveal(self.roller.empty_result())
            return

        if content["id"] in panels.PANELS:
            finish = lambda: self._open_panel(content)          # noqa: E731
        else:
            finish = lambda: self._reveal(self.roller.resolve(content))  # noqa: E731

        if not self.var_animate.get():
            finish()
            return

        names = [c["name"] for c in self.roller.enabled_contents()] or [content["name"]]
        self._spinning = True
        self.spin_btn.configure(state="disabled")
        self.main_result.show(None)
        # 룰렛 도는 내내 깔릴 긴장감 트랙 (틱·끝 화음까지 미리 섞여 있다)
        self._spin_track = sound.spin_start("settle", sound.SPIN_MAIN)
        self._spin_step(names, finish, 45.0, 0)

    def _spin_step(self, names, finish, delay, count):
        if delay > 270:
            self._spinning = False
            self.spin_btn.configure(state="normal")
            if not self._spin_track:
                sound.settle()
            finish()
            return
        self.main_display.configure(text=random.choice(names), fg="#9aa1ae",
                                    font=(self.base, 22, "bold"))
        if not self._spin_track and count % 2 == 0:
            sound.tick()
        self._spin_job = self.after(
            int(delay), lambda: self._spin_step(names, finish, delay * 1.16, count + 1))

    def _reveal(self, result):
        self._set_display(result.title)
        self._clear_panel()
        self.panel_wrap.pack_forget()
        self.text_wrap.pack(fill="both", expand=True)
        self.main_result.show(result)
        self._record(result)

    def _set_display(self, title):
        self.current_title = title
        size = 26 if len(title) <= 12 else 20
        self.main_display.configure(text=title, fg=ACCENT,
                                    font=(self.base, size, "bold"))

    def _clear_panel(self):
        if self.panel is not None:
            self.panel.stop()
            self.panel.destroy()
            self.panel = None

    def _open_panel(self, content):
        """버튼을 눌러가며 뽑는 화면을 띄운다."""
        self._set_display(content["name"])
        self._clear_panel()
        self.text_wrap.pack_forget()
        self.panel_wrap.pack(fill="both", expand=True)

        self.panel = panels.PANELS[content["id"]](self.panel_holder, self, content)
        self.panel.pack(fill="both", expand=True)
        self.panel_canvas.yview_moveto(0)
        self._record(self.panel.summary())
        self._say("%s — 버튼을 눌러서 뽑으세요." % content["name"])

    def refresh_panel_history(self):
        """패널에서 값이 하나 정해질 때마다 기록을 갱신한다."""
        if self.panel is None:
            return
        self.last_result = self.panel.summary()
        self._rewrite_last_history()
        self.update_cast(flash=True)

    def _record(self, result):
        self.last_result = result
        self.after_idle(self.update_cast)
        self._history_index = len(self.history)
        self.history.append(self._stamped(result))
        if hasattr(self, "history_text"):
            self._refresh_history()
        self._say("뽑기 완료 : %s" % result.title)

    @staticmethod
    def _stamped(result):
        return "[%s]\n%s" % (datetime.datetime.now().strftime("%H:%M:%S"), result.plain)

    def _rewrite_last_history(self):
        """이미 기록에 넣은 결과에 내용이 더 붙었을 때 그 줄만 갱신한다."""
        index = getattr(self, "_history_index", None)
        if index is None or not (0 <= index < len(self.history)):
            return
        self.history[index] = self._stamped(self.last_result)
        if hasattr(self, "history_text"):
            self._refresh_history()

    def _copy_last(self):
        if not self.last_result:
            messagebox.showinfo("알림", "아직 뽑은 결과가 없어요.")
            return
        self.clipboard_clear()
        self.clipboard_append(self.last_result.plain)
        self._say("결과를 클립보드에 복사했어요.")

    # ---------------------------------------------------------- 탭 2 등급 뽑기
    def _build_grade_tab(self):
        tab = ttk.Frame(self.nb, style="Card.TFrame")
        self.nb.add(tab, text="  등급 뽑기  ")

        tk.Label(tab, text="초월 · 불멸 · 영원 · 제한 · 신비 중에서 한 마리",
                 bg=PANEL, fg=MUTED, font=(self.base, 11)).pack(anchor="w", padx=20, pady=(18, 6))

        self.grade_display = tk.Label(
            tab, text="—", bg="#fbfbfd", fg=MUTED, font=(self.base, 30, "bold"),
            height=2, highlightthickness=1, highlightbackground=LINE)
        self.grade_display.pack(fill="x", padx=20)

        row = tk.Frame(tab, bg=PANEL)
        row.pack(fill="x", padx=20, pady=12)
        ttk.Button(row, text="한 마리 뽑기", style="Go.TButton",
                   command=self._grade_one).pack(side="left")
        ttk.Button(row, text="4명 각각 뽑기", style="Go.TButton",
                   command=self._grade_each).pack(side="left", padx=10)

        pool_box = tk.Frame(row, bg=PANEL)
        pool_box.pack(side="left", padx=(20, 0))
        tk.Label(pool_box, text="후보", bg=PANEL, fg=MUTED,
                 font=(self.base, 9)).pack(anchor="w")
        inner = tk.Frame(pool_box, bg=PANEL)
        inner.pack()
        self.grade_vars = {}
        current = set(self.cfg.get("grade_pool", data.GRADE_POOL))
        for name in data.GRADE_POOL:
            var = tk.BooleanVar(value=name in current)
            self.grade_vars[name] = var
            ttk.Checkbutton(inner, text=name, style="Card.TCheckbutton", variable=var,
                            command=self._sync_grade_pool).pack(side="left", padx=3)

        wrap = self._panel(tab, fill="both", expand=True, padx=20, pady=(4, 18))
        self.grade_result = ResultView(wrap, self.base)
        self._attach_scroll(wrap, self.grade_result)

    def _sync_grade_pool(self):
        pool = [n for n, v in self.grade_vars.items() if v.get()]
        if not pool:
            pool = list(data.GRADE_POOL)
            for var in self.grade_vars.values():
                var.set(True)
            messagebox.showinfo("알림", "후보를 최소 1개는 켜 두어야 해요.")
        self.cfg["grade_pool"] = pool

    def _grade_one(self):
        self._sync_grade_pool()
        result = self.roller.draw_grade_one()
        picked = result.lines[-1].text.replace("▶", "").strip()
        self.grade_display.configure(text=picked, fg=ACCENT)
        self.grade_result.show(result)
        self._record(result)

    def _grade_each(self):
        self._sync_grade_pool()
        result = self.roller.draw_grade_each()
        self.grade_display.configure(text="4명 각각", fg=GOLD)
        self.grade_result.show(result)
        self._record(result)

    # ----------------------------------------------------------- 탭 3 강원랜디
    def _build_gangwon_tab(self):
        tab = ttk.Frame(self.nb, style="Card.TFrame")
        self.nb.add(tab, text="  강원랜디  ")

        row = tk.Frame(tab, bg=PANEL)
        row.pack(fill="x", padx=20, pady=(18, 8))
        ttk.Button(row, text="강원랜디 돌리기", style="Go.TButton",
                   command=self._roll_gangwon).pack(side="left")
        self.gangwon_display = tk.Label(row, text="—", bg=PANEL, fg=MUTED,
                                        font=(self.base, 18, "bold"))
        self.gangwon_display.pack(side="left", padx=18)

        body = tk.Frame(tab, bg=PANEL)
        body.pack(fill="both", expand=True, padx=20, pady=(0, 18))

        left = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        left.pack(side="left", fill="both", expand=True)
        cols = ("name", "pct", "extra")
        self.gangwon_tree = ttk.Treeview(left, columns=cols, show="headings", height=18)
        self.gangwon_tree.heading("name", text="결과")
        self.gangwon_tree.heading("pct", text="확률")
        self.gangwon_tree.heading("extra", text="추가 숫자")
        self.gangwon_tree.column("name", width=250, anchor="w")
        self.gangwon_tree.column("pct", width=80, anchor="e")
        self.gangwon_tree.column("extra", width=90, anchor="center")
        sb = ttk.Scrollbar(left, orient="vertical", command=self.gangwon_tree.yview)
        self.gangwon_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.gangwon_tree.pack(side="left", fill="both", expand=True)

        wrap = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        wrap.pack(side="left", fill="both", expand=True, padx=(14, 0))
        self.gangwon_result = ResultView(wrap, self.base)
        self.gangwon_result.pack(fill="both", expand=True)

        self._refresh_gangwon_table()

    def _refresh_gangwon_table(self):
        tree = self.gangwon_tree
        tree.delete(*tree.get_children())
        table = self.cfg.get("gangwon", [])
        total = sum(float(r.get("weight", 0) or 0) for r in table) or 1.0
        for row in table:
            span = row.get("range")
            extra = "%d ~ %d" % (span[0], span[1]) if isinstance(span, (list, tuple)) and len(span) == 2 else ""
            tree.insert("", "end", values=(
                row.get("name", ""),
                "%.2f%%" % (float(row.get("weight", 0) or 0) / total * 100.0),
                extra,
            ))

    def _roll_gangwon(self):
        result = self.roller.roll_gangwon()
        headline = "—"
        for line in result.lines:
            if line.text.startswith("▶"):
                # 이름 자체에 괄호가 들어갈 수 있어서 뒤쪽 확률 표시만 떼어낸다
                headline = line.text.replace("▶", "").rsplit("(", 1)[0].strip()
        self.gangwon_display.configure(text=headline, fg=ACCENT)
        self.gangwon_result.show(result)
        self._record(result)

    # ------------------------------------------------------- 탭 4 캐릭터 관리
    def _build_chars_tab(self):
        tab = ttk.Frame(self.nb, style="Card.TFrame")
        self.nb.add(tab, text="  캐릭터 관리  ")

        tk.Label(tab, text="한 줄에 이름 하나씩 적어 주세요.",
                 bg=PANEL, fg=MUTED, font=(self.base, 10)).pack(anchor="w", padx=20, pady=(16, 8))

        bar = tk.Frame(tab, bg=PANEL)
        bar.pack(side="bottom", fill="x", padx=20, pady=14)
        ttk.Button(bar, text="저장", style="Go.TButton",
                   command=self._save_chars).pack(side="left")
        tk.Label(bar, text="상위는  이름 (등급)  형식으로.   예)  루피 (초월)   ·   거프 (불멸)",
                 bg=PANEL, fg=MUTED, font=(self.base, 9)).pack(side="left", padx=14)

        body = tk.Frame(tab, bg=PANEL)
        body.pack(fill="both", expand=True, padx=20)

        self.char_boxes = {}
        specs = (
            ("legend_chars", "전설", "이캐릭들필수/금지에 쓰입니다."),
            ("hidden_chars", "히든", "이캐릭들필수/금지에 쓰입니다."),
            ("upper_chars", "상위",
             "녜힁제조기 · 4인 강제전 · 지츠다이스룰.  이름 (등급) 형식."),
        )
        for key, title, hint in specs:
            col = tk.Frame(body, bg=PANEL)
            col.pack(side="left", fill="both", expand=True, padx=6)
            head = tk.Frame(col, bg=PANEL)
            head.pack(fill="x")
            tk.Label(head, text=title, bg=PANEL, fg=ACCENT_DK,
                     font=(self.base, 12, "bold")).pack(side="left")
            count = tk.Label(head, text="", bg=PANEL, fg=MUTED, font=(self.base, 9))
            count.pack(side="right")
            tk.Label(col, text=hint, bg=PANEL, fg=MUTED,
                     font=(self.base, 9)).pack(anchor="w", pady=(0, 4))

            wrap = tk.Frame(col, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
            wrap.pack(fill="both", expand=True)
            text = tk.Text(wrap, width=1, height=1, wrap="none", relief="flat", bd=0,
                           highlightthickness=0, font=(self.base, 11),
                           bg="white", fg=INK, padx=8, pady=6)
            sb = ttk.Scrollbar(wrap, orient="vertical", command=text.yview)
            text.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")
            text.pack(side="left", fill="both", expand=True)
            text.insert("1.0", "\n".join(self.cfg.get(key, [])))
            text.bind("<KeyRelease>", lambda e, k=key: self._refresh_char_counts())
            self.char_boxes[key] = (text, count)

        self._refresh_char_counts()

    def _refresh_char_counts(self):
        for key, (text, label) in self.char_boxes.items():
            n = len([x for x in text.get("1.0", "end").splitlines() if x.strip()])
            label.configure(text="%d개" % n)

    def _save_chars(self):
        for key, (text, _label) in self.char_boxes.items():
            names = config_mod.clean_names(text.get("1.0", "end").splitlines())
            self.cfg[key] = names
            # 중복·빈 줄을 정리한 결과를 화면에도 그대로 반영
            text.delete("1.0", "end")
            text.insert("1.0", "\n".join(names))
        self._refresh_char_counts()
        self._persist("캐릭터 목록을 저장했어요.")

    # ------------------------------------------------------------- 탭 5 설정
    def _build_settings_tab(self):
        tab = ttk.Frame(self.nb, style="Card.TFrame")
        self.nb.add(tab, text="  설정  ")

        canvas = tk.Canvas(tab, bg=PANEL, highlightthickness=0)
        sb = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=PANEL)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(window, width=e.width))
        def wheel(step):
            # 설정 탭을 보고 있을 때만 스크롤 (다른 탭 스크롤을 뺏지 않게)
            if self.nb.index(self.nb.select()) == self.nb.index(tab):
                canvas.yview_scroll(step, "units")

        canvas.bind_all("<MouseWheel>", lambda e: wheel(int(-e.delta / 120) or -1))
        canvas.bind_all("<Button-4>", lambda e: wheel(-1))
        canvas.bind_all("<Button-5>", lambda e: wheel(1))

        def section(title):
            tk.Label(inner, text=title, bg=PANEL, fg=ACCENT_DK,
                     font=(self.base, 12, "bold")).pack(anchor="w", padx=20, pady=(18, 2))
            tk.Frame(inner, bg=LINE, height=1).pack(fill="x", padx=20, pady=(0, 8))

        # --- 메인 컨텐츠 목록
        section("메인 컨텐츠  (체크 = 뽑기 대상 · 가중치가 클수록 자주 나옴 · 설명은 결과창 맨 위에 뜸)")
        grid = tk.Frame(inner, bg=PANEL)
        grid.pack(fill="x", padx=24)
        self.content_rows = []
        for i, item in enumerate(self.cfg["contents"]):
            var = tk.BooleanVar(value=bool(item.get("enabled", True)))
            ttk.Checkbutton(grid, style="Card.TCheckbutton", variable=var).grid(
                row=i, column=0, sticky="w", pady=1)
            name = ttk.Entry(grid, width=26, font=(self.base, 10))
            name.insert(0, item.get("name", ""))
            name.grid(row=i, column=1, sticky="w", padx=(2, 6), pady=1)
            weight = ttk.Entry(grid, width=5, font=(self.base, 10))
            weight.insert(0, str(item.get("weight", 1.0)))
            weight.grid(row=i, column=2, sticky="w", padx=(0, 6), pady=1)
            desc = ttk.Entry(grid, width=52, font=(self.base, 10))
            desc.insert(0, (item.get("desc", "") or "").replace("\n", "  "))
            desc.grid(row=i, column=3, sticky="we", pady=1)
            self.content_rows.append((item["id"], var, name, weight, desc))

        # --- 숫자 설정
        section("숫자 설정")
        nums = tk.Frame(inner, bg=PANEL)
        nums.pack(fill="x", padx=24)
        self.num_entries = {}
        specs = (
            ("altitude_min", "인생의고도 최소", 0),
            ("altitude_max", "인생의고도 최대", 1),
            ("nyehyung_count", "녜힁제조기 글자 수", 2),
            # 졸업보상 꼴찌 1명이 한 번 더 뽑는 범위. 영상 미확인이라 기본은 비어 있다.
            ("altitude2_min", "고도 추가 추첨 최소", 3),
            ("altitude2_max", "고도 추가 추첨 최대", 4),
            ("dice_min", "다이스 최소", 5),
            ("tier_min", "너의상위는 최소", 6),
            ("tier_max", "너의상위는 최대", 7),
            ("dice_max", "다이스 최대", 8),
            ("tier_zero_roll", "0상위가 되는 눈금", 9),
            ("mission_count", "개인미션 개수", 10),
            ("mission_penalty", "미션 실패 1개당 유카", 11),
            ("must_legend", "필수 전설 개수", 12),
            ("must_hidden", "필수 히든 개수", 13),
            ("ban_legend", "금지 전설 개수", 14),
            ("ban_hidden", "금지 히든 개수", 15),
        )
        for key, label, index in specs:
            row, col = divmod(index, 3)
            cell = tk.Frame(nums, bg=PANEL)
            cell.grid(row=row, column=col, sticky="w", padx=(0, 26), pady=3)
            tk.Label(cell, text=label, bg=PANEL, fg=INK,
                     font=(self.base, 10), width=18, anchor="w").pack(side="left")
            entry = ttk.Entry(cell, width=6, font=(self.base, 10))
            value = self.cfg.get(key)
            # 비워 둔 값(None)은 "None" 이 아니라 빈 칸으로 보여 준다
            entry.insert(0, "" if value is None else str(value))
            entry.pack(side="left")
            self.num_entries[key] = entry

        tk.Label(inner, text="고도 추가 추첨은 졸업보상을 가장 늦게 받은 1명만 합니다. "
                             "범위를 비워 두면 그 버튼이 잠깁니다 (영상 미확인).",
                 bg=PANEL, fg=MUTED, font=(self.base, 9)).pack(anchor="w", padx=24,
                                                               pady=(8, 0))

        # ---- 방송 출력 창
        section("방송 출력 창  (OBS 로 캡처할 별도 창)")
        cast_row = tk.Frame(inner, bg=PANEL)
        cast_row.pack(fill="x", padx=24)
        ttk.Button(cast_row, text="방송 창 열기", style="Go.TButton",
                   command=self.open_cast).pack(side="left")
        for label, w, h in broadcast.PRESETS:
            ttk.Button(cast_row, text=label,
                       command=lambda w=w, h=h: self._cast_preset(w, h)
                       ).pack(side="left", padx=(8, 0))
        self.var_chroma = tk.BooleanVar(value=bool(self.cfg.get("cast_chroma", False)))
        ttk.Checkbutton(cast_row, text="크로마키 배경(초록)", style="Card.TCheckbutton",
                        variable=self.var_chroma,
                        command=self._cast_chroma).pack(side="left", padx=(16, 0))
        tk.Label(inner, text="방송 창에서 F11 을 누르면 전체화면, Esc 로 해제됩니다. "
                             "설정·파일 경로는 방송 창에 나오지 않습니다.",
                 bg=PANEL, fg=MUTED, font=(self.base, 9)).pack(anchor="w", padx=24,
                                                               pady=(6, 0))

        # ---- 효과음
        section("효과음")
        snd_row = tk.Frame(inner, bg=PANEL)
        snd_row.pack(fill="x", padx=24)
        ttk.Button(snd_row, text="소리 테스트",
                   command=self._sound_test).pack(side="left")
        self.sound_msg = tk.Label(snd_row, text="", bg=PANEL, fg=MUTED,
                                  font=(self.base, 9), justify="left",
                                  wraplength=760, anchor="w")
        self.sound_msg.pack(side="left", padx=(12, 0))
        if not sound.available():
            self.sound_msg.configure(text="윈도우에서만 소리가 납니다.")

        strip_row = tk.Frame(inner, bg=PANEL)
        strip_row.pack(fill="x", padx=24, pady=(10, 0))
        tk.Label(strip_row, text="녜힁제조기 글자 뽑기에서 제외할 단어 (쉼표로 구분)",
                 bg=PANEL, fg=INK, font=(self.base, 10)).pack(anchor="w")
        self.strip_entry = ttk.Entry(strip_row, font=(self.base, 10))
        self.strip_entry.insert(0, ", ".join(self.cfg.get("nyehyung_strip_words", [])))
        self.strip_entry.pack(fill="x", pady=3)
        tk.Label(strip_row, text="· 상위 이름의 '초월/불멸/…' 부분에서는 글자를 안 뽑도록 하는 설정이에요.",
                 bg=PANEL, fg=MUTED, font=(self.base, 9)).pack(anchor="w")

        # --- 강원랜디 확률표
        section("강원랜디 확률표     형식 :   이름 | 가중치 | 범위(없으면 비움)")
        wrap = tk.Frame(inner, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        wrap.pack(fill="x", padx=24)
        self.gangwon_text = tk.Text(wrap, width=1, height=14, wrap="none", relief="flat", bd=0,
                                    highlightthickness=0, font=(self.base, 10),
                                    bg="white", fg=INK, padx=8, pady=6)
        sb2 = ttk.Scrollbar(wrap, orient="vertical", command=self.gangwon_text.yview)
        self.gangwon_text.configure(yscrollcommand=sb2.set)
        sb2.pack(side="right", fill="y")
        self.gangwon_text.pack(side="left", fill="both", expand=True)
        self._fill_gangwon_text()

        bar = tk.Frame(inner, bg=PANEL)
        bar.pack(fill="x", padx=24, pady=18)
        ttk.Button(bar, text="설정 저장", style="Go.TButton",
                   command=self._save_settings).pack(side="left")
        ttk.Button(bar, text="기본값으로 되돌리기",
                   command=self._reset_settings).pack(side="left", padx=10)

    def _fill_gangwon_text(self):
        lines = []
        for row in self.cfg.get("gangwon", []):
            span = row.get("range")
            span_text = "%d~%d" % (span[0], span[1]) if isinstance(span, (list, tuple)) and len(span) == 2 else ""
            lines.append("%s | %s | %s" % (row.get("name", ""), row.get("weight", 0), span_text))
        self.gangwon_text.delete("1.0", "end")
        self.gangwon_text.insert("1.0", "\n".join(lines))

    def _save_settings(self):
        contents = []
        for content_id, var, name_entry, weight_entry, desc_entry in self.content_rows:
            try:
                weight = float(weight_entry.get().strip())
            except ValueError:
                weight = 1.0
            contents.append({
                "id": content_id,
                "name": name_entry.get().strip() or content_id,
                "desc": desc_entry.get().strip(),
                "enabled": bool(var.get()),
                "weight": weight,
            })
        self.cfg["contents"] = contents

        for key, entry in self.num_entries.items():
            raw = entry.get().strip()
            if not raw:
                # 빈 칸은 0 이 아니라 "정하지 않음". 고도 추가 추첨이 여기 해당한다.
                self.cfg[key] = None
            else:
                self.cfg[key] = parse_int(raw, self.cfg.get(key) or 0)

        self.cfg["nyehyung_strip_words"] = [
            w.strip() for w in self.strip_entry.get().split(",") if w.strip()]

        table = []
        for raw in self.gangwon_text.get("1.0", "end").splitlines():
            if not raw.strip():
                continue
            parts = [p.strip() for p in raw.split("|")]
            name = parts[0]
            if not name:
                continue
            try:
                weight = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
            except ValueError:
                weight = 0.0
            span = None
            if len(parts) > 2 and parts[2]:
                match = re.match(r"^(-?\d+)\s*~\s*(-?\d+)$", parts[2])
                if match:
                    span = [int(match.group(1)), int(match.group(2))]
            table.append({"name": name, "weight": weight, "range": span})
        if table:
            self.cfg["gangwon"] = table

        self._refresh_gangwon_table()
        self._persist("설정을 저장했어요.")

    def _reset_settings(self):
        if not messagebox.askyesno("확인", "모든 설정을 기본값으로 되돌릴까요?\n(캐릭터 목록도 지워집니다)"):
            return
        self.cfg.clear()
        self.cfg.update(config_mod.default_config())
        config_mod.save_config(self.cfg)
        messagebox.showinfo("완료", "기본값으로 되돌렸어요.\n프로그램을 다시 실행해 주세요.")
        self.destroy()

    def _persist(self, message):
        try:
            path = config_mod.save_config(self.cfg)
        except Exception as exc:
            messagebox.showerror("저장 실패", "설정을 저장하지 못했어요.\n\n%s" % exc)
            return
        self._say("%s  (%s)" % (message, path))

    # ------------------------------------------------------------- 탭 6 기록
    def _build_history_tab(self):
        tab = ttk.Frame(self.nb, style="Card.TFrame")
        self.nb.add(tab, text="  기록  ")

        bar = tk.Frame(tab, bg=PANEL)
        bar.pack(fill="x", padx=20, pady=(16, 8))
        ttk.Button(bar, text="파일로 저장", command=self._save_history).pack(side="left")
        ttk.Button(bar, text="전체 복사", command=self._copy_history).pack(side="left", padx=8)
        ttk.Button(bar, text="지우기", command=self._clear_history).pack(side="left")

        wrap = tk.Frame(tab, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        wrap.pack(fill="both", expand=True, padx=20, pady=(0, 18))
        self.history_text = tk.Text(wrap, width=1, height=1, wrap="word", relief="flat", bd=0,
                                    highlightthickness=0, font=(self.base, 11),
                                    bg="white", fg=INK, padx=12, pady=10, state="disabled")
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.history_text.yview)
        self.history_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.history_text.pack(side="left", fill="both", expand=True)

    def _refresh_history(self):
        self.history_text.configure(state="normal")
        self.history_text.delete("1.0", "end")
        self.history_text.insert("1.0", "\n\n".join(reversed(self.history)))
        self.history_text.configure(state="disabled")

    def _history_blob(self):
        return "\n\n".join(self.history)

    def _copy_history(self):
        if not self.history:
            messagebox.showinfo("알림", "기록이 없어요.")
            return
        self.clipboard_clear()
        self.clipboard_append(self._history_blob())
        self._say("기록을 클립보드에 복사했어요.")

    def _save_history(self):
        if not self.history:
            messagebox.showinfo("알림", "기록이 없어요.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("텍스트 파일", "*.txt")],
            initialfile="랜덤원피스룰_기록_%s.txt" % datetime.datetime.now().strftime("%Y%m%d_%H%M"))
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(self._history_blob())
        self._say("기록을 저장했어요 : %s" % path)

    def _clear_history(self):
        if self.history and not messagebox.askyesno("확인", "기록을 모두 지울까요?"):
            return
        self.history = []
        self._history_index = None
        self._refresh_history()

    # --------------------------------------------------------------- 종료
    def _on_close(self):
        if self._spin_job is not None:
            try:
                self.after_cancel(self._spin_job)
            except Exception:
                pass
        self._sync_toggles()
        if self.cast is not None and self.cast.winfo_exists():
            self.cast.destroy()
        try:
            config_mod.save_config(self.cfg)
        except Exception:
            pass
        self.destroy()


def main():
    App().mainloop()
