# -*- coding: utf-8 -*-
"""뽑기 로직 (화면과 완전히 분리되어 있어서 따로 테스트 가능)."""

import random
from dataclasses import dataclass, field
from typing import List, Optional

HANGUL_START = "가"  # 가
HANGUL_END = "힣"    # 힣


@dataclass
class Line:
    """결과창에 찍히는 한 줄."""
    text: str
    kind: str = "item"            # head / item / note / warn
    color: Optional[str] = None   # 빨강 / 파랑 / 보라 / 노랑 이면 그 색으로 표시


@dataclass
class DrawResult:
    title: str
    lines: List[Line] = field(default_factory=list)

    def head(self, text):
        self.lines.append(Line(text, "head"))

    def item(self, text, color=None):
        self.lines.append(Line(text, "item", color))

    def note(self, text):
        self.lines.append(Line(text, "note"))

    def warn(self, text):
        self.lines.append(Line(text, "warn"))

    @property
    def plain(self):
        prefix = {"head": "  ▷ ", "item": "      ", "note": "  · ", "warn": "  ! "}
        out = ["■ %s" % self.title]
        for line in self.lines:
            out.append(prefix.get(line.kind, "  ") + line.text)
        return "\n".join(out)


def weighted_pick(rng, items, weights):
    """가중치대로 하나 고르기."""
    total = sum(w for w in weights if w > 0)
    if total <= 0:
        return rng.choice(items)
    point = rng.random() * total
    upto = 0.0
    for item, weight in zip(items, weights):
        if weight <= 0:
            continue
        upto += weight
        if point < upto:
            return item
    return items[-1]


def syllables_of(text):
    """문자열에서 한글 글자만 뽑아낸다."""
    return [ch for ch in text if HANGUL_START <= ch <= HANGUL_END]


class Roller:
    def __init__(self, cfg, rng=None):
        self.cfg = cfg
        self.rng = rng if rng is not None else random.Random()
        self.last_main_id = None

    # ------------------------------------------------------------------ 공통
    def _colors(self):
        return list(self.cfg.get("colors") or ["빨강", "파랑", "보라", "노랑"])

    def _grades(self):
        return list(self.cfg.get("grades") or ["초월", "불멸", "영원", "제한"])

    def _int(self, key, fallback):
        try:
            return int(self.cfg.get(key, fallback))
        except (TypeError, ValueError):
            return fallback

    def _range(self, min_key, max_key, min_default, max_default):
        lo = self._int(min_key, min_default)
        hi = self._int(max_key, max_default)
        if lo > hi:
            lo, hi = hi, lo
        return lo, hi

    def enabled_contents(self):
        out = []
        for c in self.cfg.get("contents", []):
            if not c.get("enabled", True):
                continue
            try:
                weight = float(c.get("weight", 1.0))
            except (TypeError, ValueError):
                weight = 1.0
            if weight <= 0:
                continue
            out.append(c)
        return out

    # -------------------------------------------------------- 메인 컨텐츠 뽑기
    def pick_main(self):
        pool = self.enabled_contents()
        if not pool:
            return None
        if self.cfg.get("avoid_repeat", True) and self.last_main_id and len(pool) > 1:
            filtered = [c for c in pool if c["id"] != self.last_main_id]
            if filtered:
                pool = filtered
        picked = weighted_pick(self.rng, pool, [float(c.get("weight", 1.0)) for c in pool])
        self.last_main_id = picked["id"]
        return picked

    def draw_main(self):
        picked = self.pick_main()
        if picked is None:
            res = DrawResult("뽑을 컨텐츠가 없어요")
            res.warn("[설정] 탭에서 메인 컨텐츠를 최소 1개는 켜 주세요.")
            return res

        res = DrawResult(picked["name"])
        follow = {
            "force4": self._follow_force4,
            "jits_dice": self._follow_jits_dice,
            "nyehyung": self._follow_nyehyung,
            "altitude": self._follow_altitude,
            "your_tier": self._follow_your_tier,
            "must_char": self._follow_must_char,
            "ban_char": self._follow_ban_char,
            "gangwon": self._follow_gangwon,
        }.get(self._follow_kind(picked["id"]))
        if follow:
            follow(res)
        return res

    @staticmethod
    def _follow_kind(content_id):
        from . import data
        for c in data.CONTENTS:
            if c["id"] == content_id:
                return c["follow"]
        return None

    # ------------------------------------------------------------ 추가 뽑기들
    def _follow_force4(self, res):
        """4인 강제전 → 초 / 불 / 영 / 제 중 하나."""
        grades = self._grades()
        res.head("초 · 불 · 영 · 제 중에서 하나 뽑기")
        res.item("▶  %s" % self.rng.choice(grades))

    def _follow_jits_dice(self, res):
        """지츠 '다이스' 룰 → 초불영제 4개 + 색깔별 주사위, 높은 사람부터 고르기."""
        grades = self._grades()
        colors = self._colors()
        lo, hi = self._range("dice_min", "dice_max", 1, 100)

        candidates = list(grades)
        self.rng.shuffle(candidates)
        res.head("이번 판 후보")
        res.item("   ".join(candidates))

        rolls = self._distinct_rolls(colors, lo, hi)
        res.head("주사위 (%d ~ %d)" % (lo, hi))
        for color in colors:
            res.item("%s  :  %d" % (color, rolls[color]), color=color)

        order = sorted(colors, key=lambda c: rolls[c], reverse=True)
        res.head("고르는 순서 (높은 사람부터)")
        res.item("   →   ".join("%d위 %s" % (i + 1, c) for i, c in enumerate(order)))

    def _distinct_rolls(self, colors, lo, hi):
        """되도록 동점이 안 나오게 굴린다 (범위가 좁으면 동점 허용)."""
        for _ in range(200):
            rolls = {c: self.rng.randint(lo, hi) for c in colors}
            if len(set(rolls.values())) == len(colors):
                return rolls
        return {c: self.rng.randint(lo, hi) for c in colors}

    def _follow_altitude(self, res):
        """인생의고도전 → 플레이어별로 기본값 + (0~15)."""
        base = self._int("altitude_base", 10)
        lo, hi = self._range("altitude_min", "altitude_max", 0, 15)
        res.head("인생의 고도  ( 기본 %d  +  %d~%d )" % (base, lo, hi))
        for color in self._colors():
            add = self.rng.randint(lo, hi)
            res.item("%s  :  %d + %d  =  %d" % (color, base, add, base + add), color=color)

    def _follow_your_tier(self, res):
        """너의상위는 → 빨/파/보/노 개별로 0~4."""
        lo, hi = self._range("tier_min", "tier_max", 0, 4)
        res.head("너의 상위는  ( %d ~ %d )" % (lo, hi))
        for color in self._colors():
            res.item("%s  :  %d" % (color, self.rng.randint(lo, hi)), color=color)

    def _follow_must_char(self, res):
        self._pick_characters(
            res,
            self._int("must_legend", 4),
            self._int("must_hidden", 4),
            "필수로 써야 하는 캐릭터",
        )

    def _follow_ban_char(self, res):
        self._pick_characters(
            res,
            self._int("ban_legend", 7),
            self._int("ban_hidden", 7),
            "금지된 캐릭터",
        )

    def _pick_characters(self, res, n_legend, n_hidden, label):
        res.head(label)
        for title, key, count in (("전설", "legend_chars", n_legend), ("히든", "hidden_chars", n_hidden)):
            pool = [str(x) for x in self.cfg.get(key, []) if str(x).strip()]
            if not pool:
                res.warn("%s 목록이 비어 있어요 → [캐릭터 관리] 탭에서 등록해 주세요." % title)
                continue
            take = min(count, len(pool))
            if take < count:
                res.warn("%s 은(는) %d개가 필요한데 %d개만 등록되어 있어요." % (title, count, len(pool)))
            picked = self.rng.sample(pool, take)
            res.item("%s %d개  :  %s" % (title, take, ",  ".join(picked)))

    def _follow_nyehyung(self, res):
        """녜힁제조기.

        상위 이름에 들어있는 글자 중에서 2글자를 뽑고,
        그 글자가 이름에 포함된 상위만 써서 클리어한다.
        (최소 1마리는 나와야 하므로 실제 상위 이름에 있는 글자만 후보로 쓴다)
        """
        count = max(1, self._int("nyehyung_count", 2))
        names = [str(x).strip() for x in self.cfg.get("upper_chars", []) if str(x).strip()]

        res.head("상위 이름에서 %d글자 뽑기" % count)
        if not names:
            res.warn("상위 목록이 비어 있어요 → [캐릭터 관리] 탭의 '상위 목록'에 이름을 등록해 주세요.")
            res.note("등록해 두면 그 이름들에 실제로 들어있는 글자만 뽑아서, 최소 1마리는 반드시 나오게 됩니다.")
            return

        pool = {}   # 글자 -> [해당 글자가 이름에 들어있는 상위들]
        cores = {}  # 원래 이름 -> 등급 글자를 뺀 이름
        strip_words = self.cfg.get("nyehyung_strip_words") or []
        for name in names:
            core = name
            for word in strip_words:
                core = core.replace(word, "")
            cores[name] = core
            for ch in set(syllables_of(core)):
                pool.setdefault(ch, []).append(name)

        if not pool:
            res.warn("상위 이름에서 뽑을 수 있는 글자가 없어요. (등급 글자만 남은 이름들)")
            return

        keys = sorted(pool.keys())
        take = min(count, len(keys))
        if take < count:
            res.warn("%d글자를 뽑아야 하는데 후보 글자가 %d개뿐이에요." % (count, len(keys)))
        picked = self.rng.sample(keys, take)

        res.item("뽑힌 글자  ▶   %s" % " ,  ".join(picked))

        matched = [n for n in names if any(ch in cores[n] for ch in picked)]
        res.head("사용 가능한 상위 (%d마리)" % len(matched))
        for name in matched:
            hit = [ch for ch in picked if ch in cores[name]]
            res.item("%s   (%s)" % (name, "·".join(hit)))
        res.note("위 상위들만 써서 클리어하면 됩니다.")

    def _follow_gangwon(self, res):
        self.roll_gangwon(res)

    # -------------------------------------------------------------- 강원랜디
    def roll_gangwon(self, res=None):
        if res is None:
            res = DrawResult("강원랜디")
        table = [r for r in self.cfg.get("gangwon", []) if str(r.get("name", "")).strip()]
        if not table:
            res.warn("강원랜디 확률표가 비어 있어요 → [설정] 탭에서 등록해 주세요.")
            return res

        weights = []
        for row in table:
            try:
                weights.append(float(row.get("weight", 0)))
            except (TypeError, ValueError):
                weights.append(0.0)
        total = sum(w for w in weights if w > 0) or 1.0

        picked = weighted_pick(self.rng, table, weights)
        try:
            pct = float(picked.get("weight", 0)) / total * 100.0
        except (TypeError, ValueError):
            pct = 0.0

        res.head("확률표에서 하나 뽑기")
        res.item("▶  %s      ( %.2f%% )" % (picked["name"], pct))

        span = picked.get("range")
        if isinstance(span, (list, tuple)) and len(span) == 2:
            lo, hi = int(span[0]), int(span[1])
            if lo > hi:
                lo, hi = hi, lo
            res.item("└  뽑은 숫자  :  %d" % self.rng.randint(lo, hi))
        return res

    # -------------------------------------------------------------- 등급 뽑기
    def grade_pool(self):
        pool = [str(g) for g in (self.cfg.get("grade_pool") or []) if str(g).strip()]
        return pool or ["초월", "불멸", "영원", "제한", "신비"]

    def draw_grade_one(self):
        res = DrawResult("등급 뽑기")
        pool = self.grade_pool()
        res.head("초월 · 불멸 · 영원 · 제한 · 신비 중 한 마리")
        res.item("▶  %s" % self.rng.choice(pool))
        return res

    def draw_grade_each(self):
        res = DrawResult("등급 뽑기 (4명 각각)")
        pool = self.grade_pool()
        res.head("플레이어별로 한 마리씩")
        for color in self._colors():
            res.item("%s  :  %s" % (color, self.rng.choice(pool)), color=color)
        return res
