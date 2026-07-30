# -*- coding: utf-8 -*-
"""뽑기 로직 테스트.  실행 :  python -m unittest discover -s tests -v"""

import os
import random
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ropr import data                      # noqa: E402
from ropr.config import default_config     # noqa: E402
from ropr.engine import Roller, weighted_pick  # noqa: E402


def make_roller(seed=0, **overrides):
    cfg = default_config()
    cfg.update(overrides)
    return Roller(cfg, random.Random(seed))


class TestMain(unittest.TestCase):
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

    def test_4인강제전은_초불영제_중_하나(self):
        roller = make_roller(3)
        for _ in range(40):
            result = self._find(roller, "force4")
            picked = result.lines[-1].text.replace("▶", "").strip()
            self.assertIn(picked, data.GRADES)

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

    def test_인생의고도는_기본값없이_0에서15(self):
        roller = make_roller(7)
        for _ in range(30):
            result = self._find(roller, "altitude")
            values = [l for l in result.lines if l.color]
            self.assertEqual(len(values), 4)
            for line in values:
                self.assertNotIn("+", line.text, "기본 10 더하기는 없어야 한다")
                self.assertTrue(0 <= int(line.text.split(":")[1].strip()) <= 15)

    def test_한번더는_0에서5(self):
        roller = make_roller(7)
        for _ in range(30):
            result = self._find(roller, "altitude")
            before = len(result.lines)
            roller.altitude_again(result)
            added = result.lines[before:]
            self.assertEqual(added[0].kind, "head")
            self.assertIn("한 번 더", added[0].text)
            values = [l for l in added if l.color]
            self.assertEqual(len(values), 4)
            for line in values:
                self.assertTrue(0 <= int(line.text.split(":")[1].strip()) <= 5)

    def test_플레이어별_끄면_숫자_하나만(self):
        roller = make_roller(7, altitude_per_player=False)
        result = self._find(roller, "altitude")
        self.assertEqual([l for l in result.lines if l.color], [])
        picks = [l for l in result.lines if l.text.startswith("▶")]
        self.assertEqual(len(picks), 1)
        self.assertTrue(0 <= int(picks[0].text.replace("▶", "").strip()) <= 15)

    def test_너의상위는_0에서4(self):
        roller = make_roller(11)
        for _ in range(30):
            result = self._find(roller, "your_tier")
            values = [int(l.text.split(":")[1]) for l in result.lines if l.color]
            self.assertEqual(len(values), 4)
            for value in values:
                self.assertTrue(0 <= value <= 4)

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


    def test_내가제일운없어(self):
        roller = make_roller(23)
        for _ in range(40):
            result = self._find(roller, "unlucky")
            tokens = {}
            for line in result.lines:
                if line.color:
                    tokens[line.color] = int(line.text.split(":")[1].replace("개", ""))
            self.assertEqual(set(tokens), set(data.COLORS))
            for value in tokens.values():
                self.assertTrue(0 <= value <= 10)

            verdict = [l.text for l in result.lines if l.text.startswith("▶")][0]
            fewest = min(tokens.values())
            self.assertIn("토큰 %d개" % fewest, verdict)
            for color, value in tokens.items():
                self.assertEqual(color in verdict, value == fewest, (color, verdict))

    def test_행운의토큰_범위는_설정을_따른다(self):
        roller = make_roller(29, unlucky_min=2, unlucky_max=3)
        result = self._find(roller, "unlucky")
        for line in result.lines:
            if line.color:
                self.assertIn(int(line.text.split(":")[1].replace("개", "")), (2, 3))


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
