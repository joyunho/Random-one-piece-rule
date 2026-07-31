# -*- coding: utf-8 -*-
"""뽑기 로직 테스트.  실행 :  python -m unittest discover -s tests -v"""

import os
import random
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ropr import config as config_mod       # noqa: E402
from ropr import data                      # noqa: E402
from ropr.config import default_config     # noqa: E402
from ropr.engine import Roller, weighted_pick  # noqa: E402


def make_roller(seed=0, all_on=True, **overrides):
    cfg = default_config()
    if all_on:                      # 미확인 룰은 기본으로 꺼져 있다
        for content in cfg["contents"]:
            content["enabled"] = True
    cfg.update(overrides)
    return Roller(cfg, random.Random(seed))


class TestMain(unittest.TestCase):
    def test_기본으로는_미확인_룰이_꺼져있다(self):
        cfg = default_config()
        off = {c["id"] for c in cfg["contents"] if not c["enabled"]}
        expected = {c["id"] for c in data.CONTENTS if c["status"] == "unverified"}
        self.assertEqual(off, expected)
        self.assertTrue(off, "미확인 룰이 하나는 있어야 한다")

    def test_모든_룰에_검증_상태가_붙어있다(self):
        for content in data.CONTENTS:
            self.assertIn(content["status"], data.STATUS_LABEL, content["name"])
            if content["status"] != "unverified":
                self.assertTrue(content["desc"].strip(), content["name"])
            self.assertTrue(content.get("source"), content["name"])

    def test_모든_컨텐츠가_에러없이_뽑힌다(self):
        roller = make_roller(
            legend_chars=["전설%d" % i for i in range(12)],
            hidden_chars=["히든%d" % i for i in range(12)],
            upper_chars=["로쿠규초월", "로우초월", "규환불멸", "샹크스영원", "미호크제한"],
        )
        seen = set()
        for _ in range(6000):
            result = roller.draw_main()
            seen.add(result.title)
            self.assertTrue(result.plain)
        names = {c["name"] for c in data.CONTENTS}
        self.assertEqual(seen, names, "%d개 컨텐츠가 전부 나와야 한다" % len(names))


class TestFollowUps(unittest.TestCase):
    def _find(self, roller, content_id, tries=6000):
        name = next(c["name"] for c in data.CONTENTS if c["id"] == content_id)
        for _ in range(tries):
            result = roller.draw_main()
            if result.title == name:
                return result
        self.fail("%s 를 뽑지 못했다" % content_id)

    def test_4인강제전은_상위_한마리를_강제한다(self):
        roller = make_roller(3)
        uppers = set(roller.cfg["upper_chars"])
        for _ in range(40):
            result = self._find(roller, "force4")
            self.assertFalse([l for l in result.lines if l.kind == "warn"])
            picked = [l.text for l in result.lines if l.text.startswith("▶")]
            self.assertEqual(len(picked), 1)
            unit = picked[0].replace("▶", "").strip()
            self.assertIn(unit, uppers, "상위 목록에 있는 이름이어야 한다")
            self.assertTrue([l for l in result.lines
                             if l.kind == "note" and "4명 모두" in l.text])

    def test_4인강제전_상위목록이_비면_경고(self):
        roller = make_roller(3, upper_chars=[])
        result = self._find(roller, "force4")
        self.assertTrue(any(l.kind == "warn" for l in result.lines))
        self.assertFalse([l for l in result.lines if l.text.startswith("▶")])

    def test_지츠다이스_범위와_순서(self):
        roller = make_roller(5)
        result = self._find(roller, "jits_dice")
        rolls = {}
        for line in result.lines:
            if line.color:
                rolls[line.color] = int(line.text.split(":")[1].strip())
        self.assertEqual(set(rolls), set(data.COLORS))
        for value in rolls.values():
            self.assertTrue(1 <= value <= 100)
        self.assertEqual(len(set(rolls.values())), 4, "동점 없이 굴려야 한다")

        order_line = result.lines[-1].text
        order = re.findall(r"\d위 (\S+)", order_line)
        self.assertEqual(order, sorted(rolls, key=lambda c: rolls[c], reverse=True))

    def test_인생의고도_본추첨은_10에서20(self):
        roller = make_roller(7)
        seen = set()
        for _ in range(60):
            result = self._find(roller, "altitude")
            values = [l for l in result.lines if l.color]
            self.assertEqual(len(values), 4)
            for line in values:
                value = int(line.text.split(":")[1].strip())
                self.assertTrue(10 <= value <= 20, line.text)
                seen.add(value)
        self.assertEqual(seen, set(range(10, 21)), "10~20 이 다 나와야 한다")

    def test_추가추첨_기본범위는_0에서5(self):
        roller = make_roller(7)
        self.assertEqual(roller.altitude_extra_range(), (0, 5))
        seen = set()
        for _ in range(60):
            result = self._find(roller, "altitude")
            before = len(result.lines)
            roller.altitude_again(result)
            picked = [l for l in result.lines[before:] if l.text.startswith("▶")]
            self.assertEqual(len(picked), 1)
            seen.add(int(picked[0].text.replace("▶", "").strip()))
        self.assertEqual(seen, set(range(0, 6)), "0~5 가 다 나와야 한다")

    def test_추가추첨_범위를_비우면_뽑지_않고_경고(self):
        roller = make_roller(7, altitude2_min=None, altitude2_max=None)
        self.assertIsNone(roller.altitude_extra_range())
        result = self._find(roller, "altitude")
        before = len(result.lines)
        roller.altitude_again(result)
        added = result.lines[before:]
        self.assertTrue(added and added[0].kind == "warn", added)

    def test_추가추첨_범위를_정하면_그_안에서_뽑는다(self):
        roller = make_roller(7, altitude2_min=1, altitude2_max=3)
        self.assertEqual(roller.altitude_extra_range(), (1, 3))
        for _ in range(30):
            result = self._find(roller, "altitude")
            before = len(result.lines)
            roller.altitude_again(result)
            picked = [l for l in result.lines[before:] if l.text.startswith("▶")]
            self.assertEqual(len(picked), 1)
            self.assertIn(int(picked[0].text.replace("▶", "").strip()), (1, 2, 3))

    def test_너의상위는_1에서5_뽑고_5는_0상위(self):
        roller = make_roller(11)
        seen_raw = set()
        for _ in range(60):
            result = self._find(roller, "your_tier")
            lines = [l for l in result.lines if l.color]
            self.assertEqual(len(lines), 4)
            for line in lines:
                raw = int(re.search(r":\s*(\d+)\s*→", line.text).group(1))
                applied = int(re.search(r"상위\s*(\d+)", line.text).group(1))
                self.assertTrue(1 <= raw <= 5, line.text)
                self.assertEqual(applied, 0 if raw == 5 else raw, line.text)
                seen_raw.add(raw)
        self.assertEqual(seen_raw, {1, 2, 3, 4, 5}, "눈금 1~5 가 다 나와야 한다")

    def test_상위_눈금은_다섯가지가_고르게_나온다(self):
        roller = make_roller(0)
        counts = {}
        for _ in range(4000):
            raw = roller.rng.randint(*roller.tier_range())
            counts[raw] = counts.get(raw, 0) + 1
        for raw in range(1, 6):
            self.assertAlmostEqual(counts[raw] / 4000, 0.2, delta=0.03)

    def test_이캐필_이캐금_개수(self):
        roller = make_roller(
            13,
            legend_chars=["전설%d" % i for i in range(20)],
            hidden_chars=["히든%d" % i for i in range(20)],
        )
        for content_id, n_legend, n_hidden in (("must_char", 4, 4), ("ban_char", 7, 7)):
            result = self._find(roller, content_id)
            items = [l for l in result.lines if l.kind == "item"]
            self.assertEqual(len(items), 2)
            legend = items[0].text.split(":")[1].split(",")
            hidden = items[1].text.split(":")[1].split(",")
            self.assertEqual(len(legend), n_legend)
            self.assertEqual(len(hidden), n_hidden)
            self.assertEqual(len(set(legend)), n_legend, "중복 없이 뽑아야 한다")

    def test_캐릭터_목록이_비면_경고(self):
        roller = make_roller(17, legend_chars=[], hidden_chars=[])
        result = self._find(roller, "must_char")
        self.assertEqual(len([l for l in result.lines if l.kind == "warn"]), 2)

    def test_캐릭터가_모자라면_있는만큼만(self):
        roller = make_roller(19, legend_chars=["전설A", "전설B"], hidden_chars=["히든A"])
        result = self._find(roller, "ban_char")
        self.assertTrue(any(l.kind == "warn" for l in result.lines))
        items = [l for l in result.lines if l.kind == "item"]
        self.assertIn("전설 2개", items[0].text)
        self.assertIn("히든 1개", items[1].text)


    def test_개인미션_실패당_유카가_설정을_따른다(self):
        roller = make_roller(33)
        result = self._find(roller, "personal_mission")
        text = result.plain
        self.assertIn("실패 1개당 유카 +10", text)
        self.assertIn("3개 → +30", text)

        roller = make_roller(33, mission_penalty=15)
        result = self._find(roller, "personal_mission")
        self.assertIn("3개 → +45", result.plain)

    def test_강원랜디는_플레이어별로_뽑는다(self):
        roller = make_roller(35)
        table = {r["name"] for r in data.GANGWON_TABLE}
        for _ in range(40):
            result = self._find(roller, "gangwon")
            picks = [l for l in result.lines if l.color]
            self.assertEqual([l.color for l in picks], data.COLORS)
            for line in picks:
                name = line.text.split(":", 1)[1].rsplit("(", 1)[0].strip()
                self.assertIn(name, table, line.text)


class TestRevealOrder(unittest.TestCase):
    def test_공개_순서는_빨강_보라_파랑_노랑(self):
        self.assertEqual(data.COLORS, ["빨강", "보라", "파랑", "노랑"])

    def test_색깔이_붙는_결과는_전부_그_순서를_따른다(self):
        roller = make_roller(0)
        for cid in ("altitude", "your_tier", "gangwon"):
            name = next(c["name"] for c in data.CONTENTS if c["id"] == cid)
            for _ in range(6000):
                result = roller.draw_main()
                if result.title == name:
                    break
            order = [l.color for l in result.lines if l.color]
            self.assertEqual(order, data.COLORS, cid)


class TestNyehyung(unittest.TestCase):
    UPPERS = ["로쿠규초월", "로우초월", "규환불멸", "샹크스영원", "미호크제한"]

    def test_뽑힌_글자는_항상_상위_이름에_있다(self):
        from ropr.engine import DrawResult
        for seed in range(200):
            roller = make_roller(seed, upper_chars=self.UPPERS)
            result = DrawResult("녜힁제조기")
            roller._follow_nyehyung(result)
            picked = [l for l in result.lines if l.text.startswith("뽑힌 글자")]
            self.assertEqual(len(picked), 1)
            letters = picked[0].text.split("▶")[1].replace(",", " ").split()
            self.assertEqual(len(letters), 2)
            self.assertEqual(len(set(letters)), 2, "같은 글자가 두 번 나오면 안 된다")

            text = [l.text for l in result.lines]
            start = [i for i, t in enumerate(text) if t.startswith("사용 가능한 상위")][0]
            matched = [t for t in text[start + 1:]
                       if not t.startswith("위 상위들만")]
            self.assertGreaterEqual(len(matched), 1, "최소 1마리는 나와야 한다")
            for line in matched:
                name = line.split("(")[0].strip()
                self.assertTrue(any(ch in name for ch in letters), line)

    def test_등급글자는_뽑히지_않는다(self):
        from ropr.engine import DrawResult
        for seed in range(300):
            roller = make_roller(seed, upper_chars=self.UPPERS)
            result = DrawResult("녜힁제조기")
            roller._follow_nyehyung(result)
            head = [l for l in result.lines if l.text.startswith("뽑힌 글자")][0]
            letters = head.text.split("▶")[1].replace(",", " ").split()
            for letter in letters:
                self.assertNotIn(letter, "초월불멸영원제한신비")

    def test_등급별_랜덤픽과_주사위가_없다(self):
        from ropr.engine import DrawResult
        for seed in range(120):
            roller = make_roller(seed, upper_chars=self.UPPERS)
            result = DrawResult("녜힁제조기")
            roller._follow_nyehyung(result)
            text = [l.text for l in result.lines]
            self.assertNotIn("등급별 랜덤 픽", text)
            self.assertEqual([l for l in result.lines if l.color], [])
            self.assertFalse([t for t in text if "주사위" in t or "고르는 순서" in t])

            # 걸린 상위는 전부 그대로 나열된다
            head = [t for t in text if t.startswith("사용 가능한 상위")][0]
            count = int(head.split("(")[1].split("마리")[0])
            listed = [t for t in text[text.index(head) + 1:]
                      if not t.startswith("위 상위들만")]
            self.assertEqual(len(listed), count)

    def test_걸린_상위는_2마리가_넘어도_전부_나온다(self):
        from ropr.engine import DrawResult
        uppers = ["로우초월", "로켓불멸", "로빈영원", "로저제한", "로로노아초월"]
        roller = make_roller(0, upper_chars=uppers)
        result = DrawResult("녜힁제조기")
        roller._follow_nyehyung(result)
        head = [l.text for l in result.lines if l.text.startswith("사용 가능한 상위")][0]
        # 전부 '로' 로 시작하므로 '로' 가 뽑히면 5마리가 다 나와야 한다
        letters = [l.text for l in result.lines if l.text.startswith("뽑힌 글자")][0]
        if "로" in letters.split("▶")[1]:
            self.assertIn("(5마리)", head)

    def test_상위목록이_비면_경고(self):
        from ropr.engine import DrawResult
        roller = make_roller(0, upper_chars=[])
        result = DrawResult("녜힁제조기")
        roller._follow_nyehyung(result)
        self.assertTrue(any(l.kind == "warn" for l in result.lines))

    def test_상위가_한마리뿐이어도_동작한다(self):
        from ropr.engine import DrawResult
        roller = make_roller(0, upper_chars=["로우초월"])
        result = DrawResult("녜힁제조기")
        roller._follow_nyehyung(result)
        self.assertTrue(any(l.text.startswith("뽑힌 글자") for l in result.lines))


class TestGangwon(unittest.TestCase):
    def test_18개_전부_나오고_확률이_대략_맞는다(self):
        roller = make_roller(29)
        counts = {}
        trials = 200000
        for _ in range(trials):
            result = roller.roll_gangwon()
            name = [l for l in result.lines if l.text.startswith("▶")][0]
            name = name.text.split("▶")[1].rsplit("(", 1)[0].strip()
            counts[name] = counts.get(name, 0) + 1

        table = {row["name"]: row["weight"] for row in data.GANGWON_TABLE}
        self.assertEqual(set(counts), set(table), "18개 결과가 전부 나와야 한다")
        for name, weight in table.items():
            observed = counts[name] / trials * 100.0
            self.assertAlmostEqual(observed, weight, delta=max(0.35, weight * 0.08),
                                   msg="%s 확률이 어긋남" % name)

    def test_가중치_합계는_100(self):
        self.assertAlmostEqual(sum(r["weight"] for r in data.GANGWON_TABLE), 100.0, places=6)

    def test_범위가_있는_결과는_숫자도_뽑는다(self):
        ranges = {r["name"]: r["range"] for r in data.GANGWON_TABLE if r["range"]}
        roller = make_roller(31)
        found = set()
        for _ in range(20000):
            result = roller.roll_gangwon()
            name = [l for l in result.lines if l.text.startswith("▶")][0]
            name = name.text.split("▶")[1].rsplit("(", 1)[0].strip()
            extra = [l.text for l in result.lines if l.text.startswith("└")]
            if name in ranges:
                self.assertEqual(len(extra), 1)
                value = int(extra[0].split(":")[1].strip())
                low, high = ranges[name]
                self.assertTrue(low <= value <= high, "%s : %d" % (name, value))
                found.add(name)
            else:
                self.assertEqual(extra, [])
        self.assertEqual(found, set(ranges))


class TestGrade(unittest.TestCase):
    def test_한마리_뽑기(self):
        roller = make_roller(37)
        seen = {roller.draw_grade_one().lines[-1].text.replace("▶", "").strip()
                for _ in range(400)}
        self.assertEqual(seen, set(data.GRADE_POOL))

    def test_4명_각각(self):
        roller = make_roller(41)
        result = roller.draw_grade_each()
        picks = [l for l in result.lines if l.color]
        self.assertEqual([l.color for l in picks], data.COLORS)
        for line in picks:
            self.assertIn(line.text.split(":")[1].strip(), data.GRADE_POOL)

    def test_후보를_줄이면_그중에서만(self):
        roller = make_roller(43, grade_pool=["신비"])
        for _ in range(50):
            self.assertIn("신비", roller.draw_grade_one().lines[-1].text)


class TestRoster(unittest.TestCase):
    """기본으로 들어있는 캐릭터 명단."""

    def test_기본_명단이_비어있지_않다(self):
        cfg = default_config()
        self.assertGreaterEqual(len(cfg["legend_chars"]), 7, "이캐금에 전설 7개가 필요하다")
        self.assertGreaterEqual(len(cfg["hidden_chars"]), 7, "이캐금에 히든 7개가 필요하다")
        self.assertGreaterEqual(len(cfg["upper_chars"]), 4)

    def test_명단에_중복이_없다(self):
        cfg = default_config()
        for key in ("legend_chars", "hidden_chars", "upper_chars"):
            names = cfg[key]
            self.assertEqual(len(names), len(set(names)), key)

    def test_상위는_전부_등급이_붙어있다(self):
        known = set(data.GRADE_POOL)
        for name in default_config()["upper_chars"]:
            self.assertTrue(any(g in name for g in known),
                            "등급을 못 알아보는 상위: %s" % name)

    def test_네_등급이_모두_들어있다(self):
        uppers = default_config()["upper_chars"]
        for grade in data.GRADES:
            self.assertTrue([u for u in uppers if grade in u], "%s 상위가 없다" % grade)

    def test_빈_목록으로_저장돼_있어도_기본명단이_채워진다(self):
        from ropr.config import _merge
        merged = _merge({"legend_chars": [], "hidden_chars": [], "upper_chars": []})
        self.assertTrue(merged["legend_chars"])
        self.assertTrue(merged["upper_chars"])

    def test_중복과_빈줄은_정리된다(self):
        from ropr.config import clean_names
        self.assertEqual(
            clean_names(["샹크스", " 카이도 ", "", "샹크스", "   ", "빅맘"]),
            ["샹크스", "카이도", "빅맘"])

    def test_중복이_있어도_같은_캐릭이_두번_안뽑힌다(self):
        roller = make_roller(0, legend_chars=["A", "A", "A", "A", "B", "C", "D"],
                             hidden_chars=["X", "Y", "Z", "W"])
        name = next(c["name"] for c in data.CONTENTS if c["id"] == "must_char")
        for _ in range(6000):
            result = roller.draw_main()
            if result.title == name:
                break
        picked = [x.strip() for x in
                  [l for l in result.lines if l.kind == "item"][0].text.split(":")[1].split(",")]
        self.assertEqual(len(picked), len(set(picked)), picked)

    def test_사용자가_넣은_명단이_우선한다(self):
        from ropr.config import _merge
        merged = _merge({"legend_chars": ["내캐릭"], "hidden_chars": [], "upper_chars": []})
        self.assertEqual(merged["legend_chars"], ["내캐릭"])

    def test_기본_명단으로_이캐필_이캐금이_경고없이_돈다(self):
        roller = Roller(default_config(), random.Random(0))
        for content_id in ("must_char", "ban_char"):
            name = next(c["name"] for c in data.CONTENTS if c["id"] == content_id)
            for _ in range(6000):
                result = roller.draw_main()
                if result.title == name:
                    break
            self.assertFalse([l for l in result.lines if l.kind == "warn"],
                             [l.text for l in result.lines if l.kind == "warn"])


class TestAtomicPick(unittest.TestCase):
    """일괄 추첨은 결과를 먼저 중복 없이 확정해야 한다 (방송 사고 방지)."""

    def test_한번에_여러명_뽑아도_중복이_없다(self):
        roller = make_roller(0)
        for _ in range(2000):
            picked = roller.pick_chars("legend_chars", 7)
            self.assertEqual(len(picked), 7)
            self.assertEqual(len(set(picked)), 7, picked)

    def test_이미_뽑힌_이름은_제외된다(self):
        roller = make_roller(1)
        first = roller.pick_chars("hidden_chars", 5)
        second = roller.pick_chars("hidden_chars", 5, exclude=first)
        self.assertFalse(set(first) & set(second))

    def test_명단보다_많이_요청하면_있는만큼만(self):
        roller = make_roller(2, legend_chars=["A", "B"])
        self.assertEqual(sorted(roller.pick_chars("legend_chars", 7)), ["A", "B"])


class TestConfigMigration(unittest.TestCase):
    """예전 버전에서 저장한 설정.json 을 열어도 깨지지 않아야 한다."""

    def test_없어진_룰이_남긴_설정은_지워진다(self):
        old = {"unlucky_min": 0, "unlucky_max": 10,
               "altitude_base": 10, "altitude_per_player": False,
               "tier_min": 1}
        cfg = config_mod._merge(old)
        for key in config_mod.DEAD_KEYS:
            self.assertNotIn(key, cfg, key)
        self.assertEqual(cfg["tier_min"], 1)      # 살아있는 값은 그대로

    def test_고도_추가추첨_기본값은_0에서5(self):
        cfg = config_mod._merge({})
        self.assertEqual((cfg["altitude2_min"], cfg["altitude2_max"]), (0, 5))
        self.assertEqual(Roller(cfg).altitude_extra_range(), (0, 5))

    def test_고도_추가추첨_범위를_비우면_None_그대로(self):
        cfg = config_mod._merge({"altitude2_min": None, "altitude2_max": None})
        self.assertIsNone(cfg["altitude2_min"])
        self.assertIsNone(Roller(cfg).altitude_extra_range())

    def test_범위를_채우면_추가추첨이_열린다(self):
        cfg = config_mod._merge({"altitude2_min": 0, "altitude2_max": 5})
        self.assertEqual(Roller(cfg).altitude_extra_range(), (0, 5))

    def test_숫자를_비워도_기본값으로_돌아간다(self):
        """설정 화면에서 칸을 비우면 None 이 저장된다. 그래도 죽으면 안 된다."""
        cfg = config_mod._merge({"tier_min": None, "tier_max": None,
                                 "altitude_min": None, "altitude_max": None,
                                 "mission_count": None, "mission_penalty": None,
                                 "tier_zero_roll": None})
        roller = Roller(cfg)
        self.assertEqual(roller.tier_range(), (1, 5))
        self.assertEqual(roller.altitude_range(), (10, 20))
        self.assertEqual(roller.tier_zero_roll(), 5)
        self.assertEqual(roller.mission_count(), 3)
        self.assertEqual(roller.mission_penalty(), 10)

    def test_설정_화면에_있는_숫자칸은_전부_실제로_쓰이는_값이다(self):
        """죽은 설정이 화면에 남아 있으면 안 된다."""
        import ast
        with open(os.path.join(ROOT, "ropr", "ui.py"), encoding="utf-8") as fp:
            src = fp.read()
        tree = ast.parse(src)
        keys = set()
        for node in ast.walk(tree):
            # ("altitude_min", "인생의고도 최소", 0) 모양의 튜플만 모은다
            if (isinstance(node, ast.Tuple) and len(node.elts) == 3
                    and all(isinstance(e, ast.Constant) for e in node.elts)
                    and isinstance(node.elts[0].value, str)
                    and isinstance(node.elts[2].value, int)):
                keys.add(node.elts[0].value)
        self.assertIn("altitude_min", keys, "숫자 설정 목록을 못 찾았다")
        base = default_config()
        for key in keys:
            self.assertIn(key, base, "설정 화면에 죽은 항목이 있다: " + key)


class TestNoShadowedDefs(unittest.TestCase):
    """같은 이름을 두 번 정의하면 나중 것이 이겨서 조용히 옛 동작으로 돌아간다.

    실제로 tier_range() 가 두 번 정의돼 1~5 가 0~4 로 되돌아간 적이 있다.
    """

    def test_같은_이름을_두번_정의한_곳이_없다(self):
        import ast
        import collections
        import glob

        problems = []
        for path in sorted(glob.glob(os.path.join(ROOT, "ropr", "*.py"))):
            with open(path, encoding="utf-8") as fp:
                tree = ast.parse(fp.read())
            for node in ast.walk(tree):
                if not isinstance(node, (ast.ClassDef, ast.Module)):
                    continue
                seen = collections.Counter(
                    child.name for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)))
                for name, count in seen.items():
                    if count > 1:
                        problems.append("%s: %s.%s x%d" % (
                            os.path.basename(path),
                            getattr(node, "name", "<module>"), name, count))
        self.assertEqual(problems, [], "중복 정의: " + ", ".join(problems))


class TestWeightedPick(unittest.TestCase):
    def test_가중치_0은_안뽑힌다(self):
        rng = random.Random(0)
        items = ["a", "b", "c"]
        picks = {weighted_pick(rng, items, [1, 0, 1]) for _ in range(500)}
        self.assertEqual(picks, {"a", "c"})

    def test_비율이_맞는다(self):
        rng = random.Random(0)
        items = ["a", "b"]
        picks = [weighted_pick(rng, items, [9, 1]) for _ in range(20000)]
        self.assertAlmostEqual(picks.count("a") / 20000, 0.9, delta=0.02)


if __name__ == "__main__":
    unittest.main()
