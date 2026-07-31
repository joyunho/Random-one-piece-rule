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

    def test_메모리_비동기_조합은_절대_쓰지_않는다(self):
        """이 조합은 무조건 RuntimeError 라서 소리가 안 난다."""
        for name in self.sound._SOUNDS:
            self.played.clear()
            getattr(self.sound, name)()
            self.assertEqual(self.sound.last_error, "", name)
            self.assertEqual(len(self.played), 1, (name, self.played))
            _fname, flags, _frames = self.played[0]
            self.assertFalse(flags & SND_MEMORY, name + " 가 SND_MEMORY 를 썼다")
            self.assertTrue(flags & SND_FILENAME, name)
            self.assertTrue(flags & SND_ASYNC, name + " 는 비동기여야 화면이 안 멈춘다")
            self.assertTrue(flags & SND_NODEFAULT, name + " 에 SND_NODEFAULT 필요")

    def test_모든_효과음이_실제_WAV_로_만들어진다(self):
        for name in self.sound._SOUNDS:
            self.played.clear()
            getattr(self.sound, name)()
            fname, _flags, frames = self.played[0]
            self.assertEqual(fname, name + ".wav")
            self.assertGreater(frames, 0, name + " 가 빈 소리다")

    def test_warm_up_이_전부_미리_만들어_둔다(self):
        self.sound.warm_up()
        self.assertEqual(self.sound.last_error, "")
        self.assertEqual(set(self.sound._files), set(self.sound._SOUNDS))
        for path in self.sound._files.values():
            self.assertTrue(os.path.exists(path), path)

    def test_효과음을_끄면_아무것도_재생하지_않는다(self):
        self.sound.set_enabled(False)
        self.played.clear()
        self.sound.settle()
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
            for name in sound._SOUNDS:       # 전부 불러도 예외가 없어야 한다
                getattr(sound, name)()
            sound.warm_up()
            self.assertIn("윈도우가 아니라서", sound.self_test())
        finally:
            sys.modules.pop("winsound", None)
            if saved is not None:
                sys.modules["winsound"] = saved
            importlib.reload(sound)


if __name__ == "__main__":
    unittest.main()
