# -*- coding: utf-8 -*-
"""효과음 테스트.

리눅스에는 winsound 가 없어서, 윈도우의 winsound 를 흉내낸 가짜 모듈을 끼워 넣고
sound.py 가 그걸 '어떻게 부르는지' 를 검사한다.

가짜 모듈은 CPython 이 실제로 하는 검사를 그대로 재현한다 —
SND_MEMORY 와 SND_ASYNC 를 같이 주면 RuntimeError.
예전 코드가 딱 그렇게 불러서 윈도우에서 소리가 아예 안 났다.
(CPython PC/winsound.c : "Cannot play asynchronously from memory")
"""

import importlib
import os
import sys
import types
import unittest
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SND_ASYNC, SND_NODEFAULT, SND_MEMORY = 1, 2, 4
SND_PURGE, SND_FILENAME = 0x40, 0x20000


def make_fake_winsound(played):
    """윈도우 winsound 흉내내기."""

    def PlaySound(sound, flags):
        if sound is not None and (flags & SND_MEMORY) and (flags & SND_ASYNC):
            # CPython 이 Win32 를 부르기도 전에 막는 부분
            raise RuntimeError("Cannot play asynchronously from memory")
        if sound is None:
            played.append(("STOP", flags))
            return
        if flags & SND_FILENAME:
            if not os.path.exists(sound):
                raise RuntimeError("Failed to play sound")
            with wave.open(sound, "rb") as wav:      # 진짜 WAV 인지까지 확인
                frames = wav.getnframes()
                assert wav.getnchannels() == 1
                assert wav.getsampwidth() == 2
            played.append((os.path.basename(sound), flags, frames))
            return
        played.append(("MEMORY", flags))

    fake = types.ModuleType("winsound")
    fake.PlaySound = PlaySound
    fake.SND_ASYNC = SND_ASYNC
    fake.SND_NODEFAULT = SND_NODEFAULT
    fake.SND_MEMORY = SND_MEMORY
    fake.SND_PURGE = SND_PURGE
    fake.SND_FILENAME = SND_FILENAME
    return fake


class TestSoundOnWindows(unittest.TestCase):
    def setUp(self):
        self.played = []
        self._saved = sys.modules.get("winsound")
        sys.modules["winsound"] = make_fake_winsound(self.played)
        # reload 로 모듈 본문을 다시 실행해야 가짜 winsound 를 집어간다.
        # (sys.modules 에서 지우기만 하면 ropr 패키지가 들고 있는 옛 모듈이 온다)
        from ropr import sound
        importlib.reload(sound)
        self.sound = sound
        sound.set_enabled(True)

    def tearDown(self):
        try:
            self.sound._cleanup()
        except Exception:
            pass
        if self._saved is None:
            sys.modules.pop("winsound", None)
        else:
            sys.modules["winsound"] = self._saved
        importlib.reload(self.sound)      # 원래 상태로 되돌린다

    def test_윈도우면_소리를_낼_수_있다고_한다(self):
        self.assertTrue(self.sound.available())

    # 밖에서 부르는 효과음 함수들
    EFFECTS = ("tick", "settle", "taunt", "jackpot", "thud", "pop")

    def test_메모리_비동기_조합은_절대_쓰지_않는다(self):
        """이 조합은 무조건 RuntimeError 라서 소리가 안 난다."""
        for name in self.EFFECTS:
            self.sound.stop()            # 앞 소리가 끝났다고 치고
            self.played.clear()
            getattr(self.sound, name)()
            self.assertEqual(self.sound.last_error, "", name)
            self.assertEqual(len(self.played), 1, (name, self.played))
            _fname, flags, _frames = self.played[0]
            self.assertFalse(flags & SND_MEMORY, name + " 가 SND_MEMORY 를 썼다")
            self.assertTrue(flags & SND_FILENAME, name)
            self.assertTrue(flags & SND_ASYNC, name + " 는 비동기여야 화면이 안 멈춘다")
            self.assertTrue(flags & SND_NODEFAULT, name + " 에 SND_NODEFAULT 필요")

    def test_모든_소리가_실제_WAV_로_만들어진다(self):
        for name in self.sound._SOUNDS:
            builder, seconds = self.sound._SOUNDS[name]
            self.sound.stop()
            self.played.clear()
            self.sound._play(name, force=True)
            fname, _flags, frames = self.played[0]
            self.assertEqual(fname, name + ".wav")
            self.assertGreater(frames, 0, name + " 가 빈 소리다")
            # 등록해 둔 길이와 실제 길이가 맞아야 겹침 방지가 제대로 된다
            self.assertAlmostEqual(frames / 22050.0, seconds, delta=0.30, msg=name)

    def test_스핀_트랙은_한_번만_깔린다(self):
        """winsound 는 한 번에 한 소리라, 도는 중에 딴 걸 틀면 트랙이 끊긴다."""
        self.sound.stop()
        self.played.clear()
        self.assertTrue(self.sound.spin_start("settle", self.sound.SPIN_PANEL))
        self.assertEqual(len(self.played), 1)

        # 트랙이 도는 동안 두 번째 스핀이 시작돼도 새로 틀지 않는다
        self.assertTrue(self.sound.spin_start("settle", self.sound.SPIN_PANEL))
        self.assertEqual(len(self.played), 1, self.played)
        # 낱개 틱/끝소리도 트랙을 안 끊는다
        self.sound.tick()
        self.sound.settle()
        self.sound.pop()
        self.assertEqual(len(self.played), 1, self.played)

        # 놀리는 소리는 하이라이트라서 끊고 들어간다
        self.sound.taunt()
        self.assertEqual(len(self.played), 2, self.played)
        self.assertEqual(self.played[1][0], "taunt.wav")

    def test_BGM_을_끄면_트랙_대신_틱만(self):
        self.sound.set_bgm(False)
        self.sound.stop()
        self.played.clear()
        self.assertFalse(self.sound.spin_start("settle", self.sound.SPIN_PANEL))
        self.assertEqual(self.played, [])
        self.sound.tick()
        self.assertEqual(len(self.played), 1)
        self.sound.set_bgm(True)

    def test_스핀_트랙이_화면이_도는_시간을_덮는다(self):
        """트랙이 화면보다 짧으면 중간에 소리가 끊겨 버린다."""
        from ropr import synth
        for timing in (self.sound.SPIN_PANEL, self.sound.SPIN_MAIN):
            _ticks, span = synth.spin_schedule(*timing)
            key = self.sound._spin_key("settle", timing)
            self.sound.stop()
            self.played.clear()
            self.sound._play(key, force=True)
            _fname, _flags, frames = self.played[0]
            self.assertGreater(frames / 22050.0, span, key + " 트랙이 너무 짧다")

    def test_틱이_화면_바뀌는_시각에_찍힌다(self):
        from ropr import synth
        times, span = synth.spin_schedule(*self.sound.SPIN_PANEL)
        self.assertEqual(len(times), 14)
        self.assertAlmostEqual(span, 1.428, delta=0.01)
        self.assertAlmostEqual(times[0], 0.0)
        for earlier, later in zip(times, times[1:]):
            self.assertLess(earlier, later)

    def test_warm_up_이_전부_미리_만들어_둔다(self):
        self.sound.warm_up()
        self.assertEqual(self.sound.last_error, "")
        self.assertEqual(set(self.sound._files), set(self.sound._SOUNDS))
        for path in self.sound._files.values():
            self.assertTrue(os.path.exists(path), path)

    def test_효과음을_끄면_아무것도_재생하지_않는다(self):
        self.sound.set_enabled(False)
        self.sound.stop()
        self.played.clear()
        self.sound.settle()
        self.sound.taunt()
        self.assertFalse(self.sound.spin_start("settle", self.sound.SPIN_PANEL))
        self.assertEqual(self.played, [])
        self.sound.set_enabled(True)

    def test_끝날_때_임시파일을_지운다(self):
        self.sound.warm_up()
        tmpdir = self.sound._tmpdir
        self.assertTrue(os.path.isdir(tmpdir))
        self.sound._cleanup()
        # 재생 중인 파일을 잡고 있으면 못 지우니까 먼저 멈춰야 한다
        self.assertIn(("STOP", SND_PURGE), self.played)
        self.assertFalse(os.path.exists(tmpdir))

    def test_소리테스트_버튼이_이유를_알려준다(self):
        self.assertIn("재생했어요", self.sound.self_test())
        self.sound.set_enabled(False)
        self.assertIn("꺼져 있어요", self.sound.self_test())
        self.sound.set_enabled(True)


class TestSoundElsewhere(unittest.TestCase):
    """윈도우가 아니면 조용히 아무것도 안 해야 한다 (죽으면 안 된다)."""

    def test_윈도우가_아니면_조용히_넘어간다(self):
        saved = sys.modules.pop("winsound", None)
        sys.modules["winsound"] = None       # import 하면 ImportError
        from ropr import sound
        try:
            importlib.reload(sound)
            self.assertFalse(sound.available())
            for name in ("tick", "settle", "taunt", "jackpot", "thud", "pop"):
                getattr(sound, name)()   # 전부 불러도 예외가 없어야 한다
            sound.spin_start()
            sound.stop()
            sound.warm_up()
            self.assertIn("윈도우가 아니라서", sound.self_test())
        finally:
            sys.modules.pop("winsound", None)
            if saved is not None:
                sys.modules["winsound"] = saved
            importlib.reload(sound)


if __name__ == "__main__":
    unittest.main()
