# -*- coding: utf-8 -*-
"""효과음.

외부 파일 없이 그때그때 WAV 를 만들어서 메모리에서 바로 재생한다.
윈도우에서만 소리가 나고(winsound), 다른 OS 에서는 조용히 아무것도 안 한다.
"""

import io
import math
import struct
import wave

try:
    import winsound
except ImportError:            # 윈도우가 아니면 소리 없이 동작
    winsound = None

RATE = 22050
_cache = {}
_enabled = True


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


def _play(key, builder):
    if winsound is None or not _enabled:
        return
    data = _cache.get(key)
    if data is None:
        data = _cache[key] = builder()
    try:
        winsound.PlaySound(data, winsound.SND_MEMORY | winsound.SND_ASYNC)
    except Exception:
        pass


# ------------------------------------------------------------------ 효과음들
def tick():
    """룰렛이 돌아가는 동안의 짧은 '틱'."""
    _play("tick", lambda: _wav([(1500, 0.018)], volume=0.16))


def settle():
    """멈출 때 올라가는 '띠리리링'."""
    _play("settle", lambda: _wav(
        [(784, 0.055), (988, 0.055), (1175, 0.055), (1568, 0.130)], volume=0.30))


def taunt():
    """놀리는 느낌으로 축 처지는 소리 (너의상위는 4 가 떴을 때)."""
    _play("taunt", lambda: _wav(
        [(622, 0.130), (0, 0.030), (587, 0.130), (0, 0.030),
         (494, 0.150), (0, 0.040), (392, 0.300)], volume=0.30))


def jackpot():
    """좋은 게 떴을 때 한 번 더 올라가는 소리."""
    _play("jackpot", lambda: _wav(
        [(784, 0.060), (1047, 0.060), (1319, 0.060),
         (1568, 0.060), (2093, 0.200)], volume=0.32))


def thud():
    """꽝 / 아무것도 없을 때."""
    _play("thud", lambda: _wav([(196, 0.090), (147, 0.220)], volume=0.28))


def warm_up():
    """첫 재생이 끊기지 않도록 WAV 를 미리 만들어 둔다."""
    if winsound is None:
        return
    for key, builder in (("tick", lambda: _wav([(1500, 0.018)], volume=0.16)),):
        _cache.setdefault(key, builder())
