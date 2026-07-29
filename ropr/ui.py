# -*- coding: utf-8 -*-
"""화면(tkinter GUI)."""

import datetime
import random
import re
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

from . import config as config_mod
from . import data
from .engine import Roller

BG = "#eef0f4"
PANEL = "#ffffff"
INK = "#1b1f27"
MUTED = "#6b7280"
LINE = "#d5d9e0"
ACCENT = "#c8102e"
ACCENT_DK = "#8e0a1f"
GOLD = "#b5872a"

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
        self.last_result = None
        self._history_index = None

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
        self.bind("<Return>", lambda e: self._spin())
        self.bind("<space>", lambda e: self._spin())

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
            text="설정 파일 : %s" % config_mod.config_path())
        self.status.pack(side="bottom", fill="x", padx=18, pady=(0, 8))

    def _say(self, text):
        self.status.configure(text=text)

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

        bottom = tk.Frame(tab, bg=PANEL)
        bottom.pack(side="bottom", fill="x", padx=20, pady=(6, 16))
        ttk.Button(bottom, text="결과 복사", command=self._copy_last).pack(side="left")
        ttk.Button(bottom, text="기록 보기",
                   command=lambda: self.nb.select(5)).pack(side="left", padx=8)
        # 인생의고도전이 나왔을 때만 켜지는 버튼
        self.again_btn = ttk.Button(bottom, text="한 번 더 (0~5)", style="Go.TButton",
                                    state="disabled", command=self._altitude_again)
        self.again_btn.pack(side="right")

        wrap = self._panel(tab, fill="both", expand=True, padx=20, pady=(4, 0))
        self.main_result = ResultView(wrap, self.base)
        self._attach_scroll(wrap, self.main_result)

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

    def _spin(self):
        if self._spinning:
            return
        if self.nb.index(self.nb.select()) != 0:
            return
        self._sync_toggles()
        result = self.roller.draw_main()

        if not self.var_animate.get():
            self._reveal(result)
            return

        names = [c["name"] for c in self.roller.enabled_contents()] or [result.title]
        self._spinning = True
        self.spin_btn.configure(state="disabled")
        self.main_result.show(None)
        self._spin_step(names, result, 45.0)

    def _spin_step(self, names, result, delay):
        if delay > 270:
            self._spinning = False
            self.spin_btn.configure(state="normal")
            self._reveal(result)
            return
        self.main_display.configure(text=random.choice(names), fg="#9aa1ae",
                                    font=(self.base, 22, "bold"))
        self._spin_job = self.after(
            int(delay), lambda: self._spin_step(names, result, delay * 1.16))

    def _reveal(self, result):
        size = 26 if len(result.title) <= 12 else 20
        self.main_display.configure(text=result.title, fg=ACCENT,
                                    font=(self.base, size, "bold"))
        self.main_result.show(result)
        self._record(result)

        lo = self.cfg.get("altitude2_min", 0)
        hi = self.cfg.get("altitude2_max", 5)
        is_altitude = self.roller.last_main_id == "altitude"
        self.again_btn.configure(text="한 번 더 (%s~%s)" % (lo, hi),
                                 state="normal" if is_altitude else "disabled")

    def _altitude_again(self):
        """인생의고도전에서 0~5 를 한 번 더 뽑아 결과에 이어 붙인다."""
        if self.last_result is None or self.roller.last_main_id != "altitude":
            return
        self.roller.altitude_again(self.last_result)
        self.main_result.show(self.last_result)
        self.again_btn.configure(state="disabled")
        self._rewrite_last_history()
        self._say("한 번 더 뽑았어요.")

    def _record(self, result):
        self.last_result = result
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
            ("upper_chars", "상위", "녜힁제조기에 쓰입니다.  이름 (등급) 형식."),
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
        section("메인 컨텐츠  (체크 = 뽑기 대상, 가중치가 클수록 자주 나옴)")
        grid = tk.Frame(inner, bg=PANEL)
        grid.pack(fill="x", padx=24)
        self.content_rows = []
        for i, item in enumerate(self.cfg["contents"]):
            var = tk.BooleanVar(value=bool(item.get("enabled", True)))
            ttk.Checkbutton(grid, style="Card.TCheckbutton", variable=var).grid(
                row=i, column=0, sticky="w", pady=1)
            name = ttk.Entry(grid, width=34, font=(self.base, 10))
            name.insert(0, item.get("name", ""))
            name.grid(row=i, column=1, sticky="w", padx=(2, 10), pady=1)
            weight = ttk.Entry(grid, width=6, font=(self.base, 10))
            weight.insert(0, str(item.get("weight", 1.0)))
            weight.grid(row=i, column=2, sticky="w", pady=1)
            self.content_rows.append((item["id"], var, name, weight))

        # --- 숫자 설정
        section("숫자 설정")
        nums = tk.Frame(inner, bg=PANEL)
        nums.pack(fill="x", padx=24)
        self.num_entries = {}
        specs = (
            ("dice_min", "다이스 최소", 0),
            ("dice_max", "다이스 최대", 1),
            ("nyehyung_count", "녜힁제조기 글자 수", 2),
            ("altitude_min", "인생의고도 최소", 3),
            ("altitude_max", "인생의고도 최대", 4),
            ("altitude_base", "인생의고도 기본더하기", 5),
            ("altitude2_min", "한 번 더 최소", 6),
            ("altitude2_max", "한 번 더 최대", 7),
            ("tier_min", "너의상위는 최소", 8),
            ("tier_max", "너의상위는 최대", 9),
            ("must_legend", "필수 전설 개수", 10),
            ("must_hidden", "필수 히든 개수", 11),
            ("ban_legend", "금지 전설 개수", 12),
            ("ban_hidden", "금지 히든 개수", 13),
        )
        for key, label, index in specs:
            row, col = divmod(index, 3)
            cell = tk.Frame(nums, bg=PANEL)
            cell.grid(row=row, column=col, sticky="w", padx=(0, 26), pady=3)
            tk.Label(cell, text=label, bg=PANEL, fg=INK,
                     font=(self.base, 10), width=18, anchor="w").pack(side="left")
            entry = ttk.Entry(cell, width=6, font=(self.base, 10))
            entry.insert(0, str(self.cfg.get(key, "")))
            entry.pack(side="left")
            self.num_entries[key] = entry

        self.var_per_player = tk.BooleanVar(
            value=bool(self.cfg.get("altitude_per_player", True)))
        ttk.Checkbutton(inner, style="Card.TCheckbutton",
                        text="인생의고도전을 빨/파/보/노 각각 뽑기 (끄면 다같이 쓰는 숫자 하나만)",
                        variable=self.var_per_player).pack(anchor="w", padx=24, pady=(10, 0))

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
        for content_id, var, name_entry, weight_entry in self.content_rows:
            try:
                weight = float(weight_entry.get().strip())
            except ValueError:
                weight = 1.0
            contents.append({
                "id": content_id,
                "name": name_entry.get().strip() or content_id,
                "enabled": bool(var.get()),
                "weight": weight,
            })
        self.cfg["contents"] = contents

        for key, entry in self.num_entries.items():
            self.cfg[key] = parse_int(entry.get(), self.cfg.get(key, 0))

        self.cfg["altitude_per_player"] = bool(self.var_per_player.get())
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
        try:
            config_mod.save_config(self.cfg)
        except Exception:
            pass
        self.destroy()


def main():
    App().mainloop()
