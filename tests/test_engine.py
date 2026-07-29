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
        cfg = default_config()
        cfg.update(
            legend_chars=["전설%d" % i for i in range(12)],
            hidden_chars=["히든%d" % i for i in range(12)],
            upper_chars=["로쿠규초월", "로우초월", "규환불멸", "샹크스영원", "미호크제한"],
        )
        for content in cfg["contents"]:      # 창작 룰까지 전부 켜고 확인
            content["enabled"] = True
        roller = Roller(cfg, random.Random(0))

        seen = set()
        for _ in range(6000):
            result = roller.draw_main()
            seen.add(result.title)
            self.assertTrue(result.plain)
        names = {c["name"] for c in data.CONTENTS}
        self.assertEqual(seen, names, "%d개 컨텐츠가 전부 나와야 한다" % len(names))

    def test_창작룰은_기본으로_꺼져있다(self):
        cfg = default_config()
        off = {c["id"] for c in cfg["contents"] if not c["enabled"]}
        self.assertEqual(off, data.OFF_BY_DEFAULT)

        roller = Roller(cfg, random.Random(0))
        titles = {roller.draw_main().title for _ in range(4000)}
        for content in data.CONTENTS:
            if content["id"] in data.OFF_BY_DEFAULT:
                self.assertNotIn(content["name"], titles)

    def test_연속방지(self):
        roller = make_roller(avoid_repeat=True)
        previous = None
        for _ in range(500):
            title = roller.draw_main().title
            self.assertNotEqual(title, previous)
            previous = title

    def test_꺼진_컨텐츠는_안나온다(self):
        cfg = default_config()
        for content in cfg["contents"]:
            content["enabled"] = content["id"] in ("force4", "adcarry")
        roller = Roller(cfg, random.Random(1))
        titles = {roller.draw_main().title for _ in range(200)}
        self.assertEqual(titles, {"4인 강제전", "원딜전(물1마1)"})

    def test_컨텐츠가_전부_꺼지면_안내(self):
        cfg = default_config()
        for content in cfg["contents"]:
            content["enabled"] = False
        result = Roller(cfg, random.Random(0)).draw_main()
        self.assertEqual([l.kind for l in result.lines], ["warn"])


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
        roller = make_roller(17)
        result = self._find(roller, "must_char")
        self.assertEqual(len([l for l in result.lines if l.kind == "warn"]), 2)

    def test_캐릭터가_모자라면_있는만큼만(self):
        roller = make_roller(19, legend_chars=["전설A", "전설B"], hidden_chars=["히든A"])
        result = self._find(roller, "ban_char")
        self.assertTrue(any(l.kind == "warn" for l in result.lines))
        items = [l for l in result.lines if l.kind == "item"]
        self.assertIn("전설 2개", items[0].text)
        self.assertIn("히든 1개", items[1].text)


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
            matched = text[start + 1:text.index("등급별 랜덤 픽")]
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

    def test_등급별로_한마리씩_뽑고_다이스로_순서를_정한다(self):
        from ropr.engine import DrawResult
        for seed in range(120):
            roller = make_roller(seed, upper_chars=self.UPPERS)
            result = DrawResult("녜힁제조기")
            roller._follow_nyehyung(result)
            text = [l.text for l in result.lines]

            start = text.index("등급별 랜덤 픽")
            picks = text[start + 1:start + 1 + len(data.GRADES)]
            self.assertEqual(len(picks), 4)

            matched_head = [t for t in text if t.startswith("사용 가능한 상위")][0]
            count = int(matched_head.split("(")[1].split("마리")[0])
            matched = [t.split("(")[0].strip() for t in text[text.index(matched_head) + 1:start]]
            self.assertEqual(len(matched), count)

            for grade, line in zip(data.GRADES, picks):
                self.assertTrue(line.startswith(grade), line)
                name = line.split(":")[1].strip()
                if name == "(해당하는 상위 없음)":
                    self.assertFalse([m for m in matched if grade in m], grade)
                else:
                    self.assertIn(name, matched, "뽑힌 상위는 사용 가능 목록 안에 있어야 한다")
                    self.assertIn(grade, name)

            # 다이스로 고르는 순서까지 나와야 한다
            rolls = {l.color: int(l.text.split(":")[1]) for l in result.lines if l.color}
            self.assertEqual(set(rolls), set(data.COLORS))
            order = re.findall(r"\d위 (\S+)", text[-2])
            self.assertEqual(order, sorted(rolls, key=lambda c: rolls[c], reverse=True))

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


class TestExtraRules(unittest.TestCase):
    """만들어 본 추가 룰 3개."""

    def _run(self, follow_name, **overrides):
        from ropr.engine import DrawResult
        results = []
        for seed in range(120):
            roller = make_roller(seed, **overrides)
            result = DrawResult("t")
            getattr(roller, follow_name)(result)
            results.append(result)
        return results

    def test_현상금_최고최저가_갈린다(self):
        legend = ["전설%d" % i for i in range(8)]
        for result in self._run("_follow_bounty", legend_chars=legend):
            rolls = {}
            for line in result.lines:
                if line.color and "억" in line.text:
                    rolls[line.color] = int(line.text.split(":")[1].replace("억", "").strip())
            self.assertEqual(set(rolls), set(data.COLORS))
            for value in rolls.values():
                self.assertTrue(1 <= value <= 100)

            text = [l.text for l in result.lines]
            top = [t for t in text if t.startswith("해군 집중 표적")][0].split("▶")[1]
            bottom = [t for t in text if t.startswith("무명의 해적")][0].split("▶")[1]
            self.assertIn(max(rolls, key=lambda c: rolls[c]), top)
            self.assertIn(min(rolls, key=lambda c: rolls[c]), bottom)

            banned = [t for t in text if "금지 전설" in t][0].split(":")[1].strip()
            self.assertIn(banned, legend)

    def test_현상금_전설목록이_비면_경고(self):
        for result in self._run("_follow_bounty")[:5]:
            self.assertTrue(any(l.kind == "warn" for l in result.lines))

    def test_각성과_봉인은_서로_다른_등급(self):
        for result in self._run("_follow_fruit_wake"):
            picks = [l for l in result.lines if l.color]
            self.assertEqual([l.color for l in picks], data.COLORS)
            for line in picks:
                wake = line.text.split("각성")[1].split("/")[0].strip()
                seal = line.text.split("봉인")[1].strip()
                self.assertIn(wake, data.GRADE_POOL)
                self.assertIn(seal, data.GRADE_POOL)
                self.assertNotEqual(wake, seal, "각성과 봉인이 같으면 안 된다")

    def test_각성_후보가_하나뿐이면_경고(self):
        for result in self._run("_follow_fruit_wake", grade_pool=["신비"])[:3]:
            self.assertTrue(any(l.kind == "warn" for l in result.lines))

    def test_포네그리프_합계로_결과가_갈린다(self):
        outcomes = set()
        for result in self._run("_follow_poneglyph"):
            values = [int(l.text.split(":")[1]) for l in result.lines if l.color]
            self.assertEqual(len(values), 4)
            for value in values:
                self.assertTrue(0 <= value <= 4)

            head = [l.text for l in result.lines if l.text.startswith("해독 결과")][0]
            total = int(head.split("합계")[1].replace(")", "").strip())
            self.assertEqual(total, sum(values))

            verdict = [l.text for l in result.lines if l.text.startswith("▶")][0]
            outcomes.add(verdict)
            if total >= 12:
                self.assertIn("라프텔", verdict)
            elif total <= 4:
                self.assertIn("공백", verdict)
            else:
                self.assertIn("항해 계속", verdict)
        self.assertGreaterEqual(len(outcomes), 2, "결과가 한 종류만 나오면 안 된다")


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
