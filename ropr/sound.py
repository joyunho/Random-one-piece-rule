# -*- coding: utf-8 -*-
"""효과음.

외부 파일 없이 그때그때 WAV 를 만들어서 재생한다.
윈도우에서만 소리가 나고(winsound), 다른 OS 에서는 조용히 아무것도 안 한다.

주의 — winsound 는 '메모리에서 비동기 재생' 을 지원하지 않는다.

    winsound.PlaySound(data, SND_MEMORY | SND_ASYNC)
        -> RuntimeError("Cannot play asynchronously from memory")

CPython 이 Win32 를 부르기도 전에 막아 버리는 검사라, 예전 버전에서도 통한 적이 없다.
(PC/winsound.c : "Sidestep reference counting headache")

그래서 만든 WAV 를 임시 폴더에 파일로 한 번 써 두고,
SND_FILENAME | SND_ASYNC 로 재생한다. 이러면 화면이 멈추지 않는다.
"""

import atexit
import io
import math
import os
import shutil
import struct
import tempfile
import wave

try:
    import winsound
except ImportError:            # 윈도우가 아니면 소리 없이 동작
    winsound = None

RATE = 22050
_cache = {}
_files = {}
_tmpdir = None
_enabled = True
last_error = ""                # 소리가 안 날 때 [설정] 탭에서 이유를 보여준다


def available():
    return winsound is not None


def set_enabled(flag):
    global _enabled
    _enabled = bool(flag)


def _wav(notes, volume=0.30):
    """(주파수, 길이초) 목록을 이어붙인 WAV 바이트를 만든다.

    주파수 0 은 쉼표. 앞뒤에 짧은 페이드를 넣어 '틱' 하는 잡음을 없앤다.
    """
    frames = bytearray()
    for freq, dur in notes:
        count = max(1, int(RATE * dur))
        attack = max(1, int(RATE * 0.004))
        release = max(1, int(RATE * 0.020))
        for i in range(count):
            if freq <= 0:
                frames += struct.pack("<h", 0)
                continue
            env = min(1.0, i / attack) * min(1.0, (count - i) / release)
            value = volume * env * math.sin(2.0 * math.pi * freq * i / RATE)
            frames += struct.pack("<h", int(max(-1.0, min(1.0, value)) * 32767))

    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(bytes(frames))
    return buf.getvalue()


# ------------------------------------------------------------------ 임시 파일
def _cleanup():
    """프로그램이 끝날 때 임시 WAV 를 지운다."""
    if winsound is not None:
        try:
            # 재생 중인 파일은 윈도우가 잡고 있어서 안 지워진다. 먼저 멈춘다.
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
    if _tmpdir:
        shutil.rmtree(_tmpdir, ignore_errors=True)


def _path_for(key, data):
    """WAV 를 임시 폴더에 한 번만 써 두고 그 경로를 돌려준다.

    exe(--onefile) 의 압축 해제 폴더(sys._MEIPASS)에는 쓰지 않는다.
    거긴 종료할 때 지워지는데, 재생 중이면 안 지워져서 찌꺼기가 남는다.
    """
    global _tmpdir
    path = _files.get(key)
    if path and os.path.exists(path):
        return path
    if _tmpdir is None:
        _tmpdir = tempfile.mkdtemp(prefix="ropr_snd_")
        atexit.register(_cleanup)
    path = os.path.join(_tmpdir, key + ".wav")
    with open(path, "wb") as fp:
        fp.write(data)
    _files[key] = path
    return path


def _play(key, builder):
    global last_error
    if winsound is None or not _enabled:
        return
    try:
        data = _cache.get(key)
        if data is None:
            data = _cache[key] = builder()
        # SND_NODEFAULT : 파일을 못 찾아도 윈도우 기본 '딩' 소리를 내지 않는다
        winsound.PlaySound(
            _path_for(key, data),
            winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        last_error = ""
    except Exception as exc:        # 소리 때문에 프로그램이 죽으면 안 된다
        last_error = "%s: %s" % (type(exc).__name__, exc)


# ------------------------------------------------------------------ 효과음들
_SOUNDS = {
    # 룰렛이 돌아가는 동안의 짧은 '틱'
    "tick": lambda: _wav([(1500, 0.018)], volume=0.16),
    # 멈출 때 올라가는 '띠리리링'
    "settle": lambda: _wav(
        [(784, 0.055), (988, 0.055), (1175, 0.055), (1568, 0.130)], volume=0.30),
    # 놀리는 느낌으로 축 처지는 소리 (0상위가 떴을 때)
    "taunt": lambda: _wav(
        [(622, 0.130), (0, 0.030), (587, 0.130), (0, 0.030),
         (494, 0.150), (0, 0.040), (392, 0.300)], volume=0.30),
    # 좋은 게 떴을 때 한 번 더 올라가는 소리
    "jackpot": lambda: _wav(
        [(784, 0.060), (1047, 0.060), (1319, 0.060),
         (1568, 0.060), (2093, 0.200)], volume=0.32),
    # 꽝 / 아무것도 없을 때
    "thud": lambda: _wav([(196, 0.090), (147, 0.220)], volume=0.28),
    # 방송 화면에서 값이 하나 확정될 때 짧게 튀는 소리
    "pop": lambda: _wav([(1319, 0.035), (1976, 0.075)], volume=0.26),
}


def tick():
    _play("tick", _SOUNDS["tick"])


def settle():
    _play("settle", _SOUNDS["settle"])


def taunt():
    _play("taunt", _SOUNDS["taunt"])


def jackpot():
    _play("jackpot", _SOUNDS["jackpot"])


def thud():
    _play("thud", _SOUNDS["thud"])


def pop():
    _play("pop", _SOUNDS["pop"])


def warm_up():
    """첫 재생이 끊기지 않도록 WAV 를 미리 만들어서 파일로 깔아 둔다."""
    if winsound is None:
        return
    for key, builder in _SOUNDS.items():
        try:
            data = _cache.get(key)
            if data is None:
                data = _cache[key] = builder()
            _path_for(key, data)
        except Exception as exc:
            global last_error
            last_error = "%s: %s" % (type(exc).__name__, exc)
            return


def self_test():
    """[설정] 탭의 '소리 테스트' 버튼용. 실패하면 이유를 글자로 돌려준다."""
    if winsound is None:
        return "이 컴퓨터는 윈도우가 아니라서 소리를 낼 수 없어요."
    if not _enabled:
        return "효과음이 꺼져 있어요. [메인 뽑기] 화면의 [효과음] 을 켜 주세요."
    settle()
    if last_error:
        return "소리를 내지 못했어요 — " + last_error
    return "소리를 재생했어요. 안 들리면 윈도우 볼륨 믹서에서 이 프로그램이 " \
           "음소거되어 있는지 확인해 주세요."
