# -*- coding: utf-8 -*-
"""소리를 직접 만드는 부분 (WAV 바이트를 돌려준다).

윈도우의 winsound 는 한 번에 한 소리만 낸다 — 새로 재생하면 앞의 소리가 끊긴다.
그래서 'BGM 을 깔고 그 위에 효과음' 같은 건 재생 두 번으로는 안 된다.

대신 여기서 미리 섞는다. 긴장감 트랙 + 릴 도는 틱 + 마지막 화음을 한 덩어리
WAV 로 만들어 두고, 스핀이 시작될 때 딱 한 번만 재생한다.

소리는 사인파를 그때그때 계산하지 않고 파형표(wavetable)를 미리 만들어
위상만 굴린다. 그래야 프로그램 켤 때 안 버벅인다.
"""

import array
import io
import math
import struct
import wave

RATE = 22050
TWO_PI = 2.0 * math.pi
TABLE = 2048


def _table(harmonics):
    """배음 비율을 받아서 파형표 한 주기를 만든다.

    harmonics = (1.0, 0.5, 0.25) 면 기본음 + 2배음 절반 + 3배음 1/4.
    사인파 하나만 쓰면 너무 밋밋해서 배음을 섞는다.
    """
    table = [0.0] * TABLE
    for index in range(TABLE):
        phase = TWO_PI * index / TABLE
        value = 0.0
        for n, gain in enumerate(harmonics, start=1):
            value += gain * math.sin(phase * n)
        table[index] = value
    peak = max(abs(v) for v in table) or 1.0
    return [v / peak for v in table]


# 음색 몇 가지
SOFT = _table((1.0, 0.28, 0.10))                  # 둥근 소리
BELL = _table((1.0, 0.0, 0.45, 0.0, 0.22, 0.14))  # 종 비슷한 소리
REED = _table((1.0, 0.6, 0.42, 0.28, 0.18, 0.1))  # 좀 쨍한 소리
BASS = _table((1.0, 0.5, 0.18, 0.06))             # 낮은 소리


def _seed(n):
    """재생할 때마다 소리가 달라지면 안 되니까 난수도 고정해서 쓴다."""
    state = 0x2545F491 ^ n
    while True:
        state ^= (state << 13) & 0xFFFFFFFF
        state ^= state >> 17
        state ^= (state << 5) & 0xFFFFFFFF
        yield (state & 0xFFFF) / 32767.5 - 1.0


class Mix:
    """소리 여러 겹을 시간 축에 얹는 도화지."""

    def __init__(self, seconds):
        self.n = max(1, int(RATE * seconds))
        self.buf = [0.0] * self.n

    # ---------------------------------------------------------------- 재료
    def tone(self, at, dur, freq, gain=0.5, table=SOFT,
             attack=0.006, release=None, glide=None, vibrato=0.0):
        """음 하나. glide 를 주면 그 주파수까지 미끄러진다."""
        start = int(RATE * at)
        count = int(RATE * dur)
        if count <= 0 or start >= self.n:
            return
        release = dur * 0.7 if release is None else release
        a = max(1, int(RATE * attack))
        r = max(1, int(RATE * release))
        phase = 0.0
        end_freq = freq if glide is None else glide
        for i in range(count):
            pos = start + i
            if pos >= self.n:
                break
            t = i / count
            f = freq + (end_freq - freq) * t
            if vibrato:
                f *= 1.0 + vibrato * math.sin(TWO_PI * 5.5 * i / RATE)
            phase += f * TABLE / RATE
            # 앞은 부드럽게 올리고 뒤는 서서히 줄인다 (딱 끊으면 '틱' 소리가 난다)
            env = min(1.0, i / a) * min(1.0, (count - i) / r)
            self.buf[pos] += gain * env * table[int(phase) % TABLE]

    def hit(self, at, dur, freq, gain=0.5, noise=0.5, seed=1):
        """타악기. 잡음 + 뚝 떨어지는 저음."""
        start = int(RATE * at)
        count = int(RATE * dur)
        if count <= 0 or start >= self.n:
            return
        rnd = _seed(seed)
        phase = 0.0
        for i in range(count):
            pos = start + i
            if pos >= self.n:
                break
            env = (1.0 - i / count) ** 2.4
            f = freq * (1.0 - 0.55 * (i / count))     # 칠 때 음이 뚝 떨어진다
            phase += f * TABLE / RATE
            body = BASS[int(phase) % TABLE]
            self.buf[pos] += gain * env * (body * (1.0 - noise) + next(rnd) * noise)

    def roll(self, at, dur, gain=0.22, seed=7):
        """드럼 롤처럼 자글자글 깔리는 잡음."""
        start = int(RATE * at)
        count = int(RATE * dur)
        rnd = _seed(seed)
        prev = 0.0
        for i in range(count):
            pos = start + i
            if pos >= self.n:
                break
            # 저역 통과 : 그냥 잡음은 '치익' 해서 거슬린다
            prev = prev * 0.72 + next(rnd) * 0.28
            swell = 0.35 + 0.65 * (i / count)          # 뒤로 갈수록 커진다
            tremolo = 0.75 + 0.25 * math.sin(TWO_PI * 11.0 * i / RATE)
            self.buf[pos] += gain * swell * tremolo * prev

    def chord(self, at, freqs, dur, gain=0.34, table=BELL, spread=0.045):
        """화음. 조금씩 늦게 들어가야 딱딱하지 않다."""
        for k, freq in enumerate(freqs):
            self.tone(at + k * spread, dur - k * spread, freq,
                      gain=gain, table=table, attack=0.008)

    # ---------------------------------------------------------------- 출력
    def wav(self, peak=0.86):
        """-1~1 로 눌러 담고 16bit WAV 로."""
        top = max((abs(v) for v in self.buf), default=0.0)
        scale = (peak / top) if top > peak else 1.0
        pcm = array.array("h", bytes(2 * self.n))
        for i, value in enumerate(self.buf):
            v = value * scale
            # 살짝 부드럽게 눌러서 찌그러지는 소리를 막는다
            if v > 1.0 or v < -1.0:
                v = math.tanh(v)
            pcm[i] = int(v * 32767)
        # 맨 앞뒤 5ms 페이드 (재생 시작·끝의 '툭' 제거)
        fade = int(RATE * 0.005)
        for i in range(min(fade, self.n)):
            k = i / fade
            pcm[i] = int(pcm[i] * k)
            pcm[self.n - 1 - i] = int(pcm[self.n - 1 - i] * k)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(RATE)
            out.writeframes(pcm.tobytes())
        return buf.getvalue()


# ------------------------------------------------------------------ 음이름
def hz(semitones_from_a4):
    return 440.0 * (2.0 ** (semitones_from_a4 / 12.0))


A2, E3, A3 = hz(-24), hz(-17), hz(-12)
C4, D4, E4, G4, A4 = hz(3), hz(5), hz(7), hz(10), hz(12)
C5, D5, E5, G5, A5 = hz(15), hz(17), hz(19), hz(22), hz(24)
E6, A6 = hz(31), hz(36)


def spin_schedule(start_ms, growth, limit_ms):
    """패널/룰렛이 실제로 화면을 바꾸는 시각(초)들.

    거기에 맞춰 틱을 찍어야 화면과 소리가 어긋나지 않는다.
    """
    times, t, delay = [], 0.0, float(start_ms)
    while delay <= limit_ms:
        times.append(t / 1000.0)
        t += delay
        delay *= growth
    return times, t / 1000.0


def tension_bed(mix, span, seed=3):
    """스핀 내내 깔리는 긴장감 트랙.

    - 낮게 밀고 올라오는 드론
    - 점점 커지는 드럼 롤
    - 심장박동처럼 규칙적으로 치는 저음
    """
    mix.tone(0.0, span, A2, gain=0.30, table=BASS,
             glide=A2 * 1.5, attack=0.12, release=0.25)
    mix.tone(0.0, span, E3, gain=0.13, table=REED,
             glide=E3 * 1.5, attack=0.30, release=0.30, vibrato=0.006)
    mix.roll(0.0, span, gain=0.20, seed=seed)

    beat, when = 0, 0.0
    while when < span - 0.05:
        # 뒤로 갈수록 심장박동이 빨라진다
        gap = 0.30 - 0.16 * (when / span)
        mix.hit(when, min(0.20, span - when), A2 * 0.5,
                gain=0.34 + 0.20 * (when / span), noise=0.18, seed=seed + beat)
        when += gap
        beat += 1


def spin_wav(kind="settle", start_ms=38, growth=1.14, limit_ms=235):
    """긴장감 트랙 + 릴 틱 + 마지막 화음을 한 덩어리로 섞는다."""
    ticks, span = spin_schedule(start_ms, growth, limit_ms)
    tail = 1.15 if kind in ("settle", "jackpot") else 1.0
    mix = Mix(span + tail)

    tension_bed(mix, span)

    # 릴이 한 칸 넘어갈 때마다 '틱'. 뒤로 갈수록 음이 올라가서 조여드는 느낌.
    for i, at in enumerate(ticks):
        ratio = i / max(1, len(ticks) - 1)
        mix.tone(at, 0.045, 900.0 + 700.0 * ratio,
                 gain=0.20 + 0.10 * ratio, table=BELL, attack=0.001, release=0.04)
        mix.hit(at, 0.05, 380.0, gain=0.13, noise=0.65, seed=40 + i)

    # 멈추는 순간
    if kind == "taunt":                 # 놀리는 소리 : 축 처진다
        for k, freq in enumerate((E5, D5, C5, A3 * 2)):
            mix.tone(span + k * 0.16, 0.30 if k < 3 else 0.66, freq,
                     gain=0.42, table=REED, attack=0.01, vibrato=0.02 if k == 3 else 0.0)
        mix.hit(span + 0.48, 0.45, A2 * 0.75, gain=0.40, noise=0.25, seed=99)
    elif kind == "thud":                # 꽝
        mix.hit(span, 0.55, A2 * 0.7, gain=0.62, noise=0.30, seed=51)
        mix.tone(span + 0.02, 0.50, A2, gain=0.30, table=BASS,
                 glide=A2 * 0.6, attack=0.004)
    elif kind == "jackpot":             # 대박
        mix.hit(span, 0.30, A3, gain=0.45, noise=0.40, seed=61)
        for k, freq in enumerate((A4, C5 * 1.0595, E5, A5)):
            mix.tone(span + k * 0.075, 0.34, freq, gain=0.40,
                     table=BELL, attack=0.004)
        mix.chord(span + 0.30, (A5, E6, A6), 0.95, gain=0.30)
    else:                               # 기본 : 시원하게 올라가는 화음
        mix.hit(span, 0.26, A3, gain=0.40, noise=0.35, seed=71)
        mix.chord(span, (A4, E5, A5), 0.85, gain=0.34)
        mix.tone(span + 0.04, 0.70, A5 * 2, gain=0.14, table=BELL, attack=0.01)
    return mix.wav()


# ------------------------------------------------------- 짧은 소리 (단발용)
def tick_wav():
    mix = Mix(0.05)
    mix.tone(0.0, 0.04, 1500.0, gain=0.45, table=BELL, attack=0.001, release=0.035)
    return mix.wav(peak=0.55)


def settle_wav():
    mix = Mix(1.0)
    mix.hit(0.0, 0.22, A3, gain=0.40, noise=0.35, seed=71)
    mix.chord(0.0, (A4, E5, A5), 0.85, gain=0.36)
    return mix.wav()


def taunt_wav():
    mix = Mix(1.35)
    for k, freq in enumerate((E5, D5, C5, A3 * 2)):
        mix.tone(k * 0.16, 0.30 if k < 3 else 0.66, freq, gain=0.44,
                 table=REED, attack=0.01, vibrato=0.02 if k == 3 else 0.0)
    mix.hit(0.48, 0.45, A2 * 0.75, gain=0.40, noise=0.25, seed=99)
    return mix.wav()


def jackpot_wav():
    mix = Mix(1.45)
    mix.hit(0.0, 0.30, A3, gain=0.45, noise=0.40, seed=61)
    for k, freq in enumerate((A4, C5 * 1.0595, E5, A5)):
        mix.tone(k * 0.075, 0.34, freq, gain=0.42, table=BELL, attack=0.004)
    mix.chord(0.30, (A5, E6, A6), 0.95, gain=0.32)
    return mix.wav()


def thud_wav():
    mix = Mix(0.75)
    mix.hit(0.0, 0.55, A2 * 0.7, gain=0.62, noise=0.30, seed=51)
    mix.tone(0.02, 0.50, A2, gain=0.32, table=BASS, glide=A2 * 0.6, attack=0.004)
    return mix.wav()


def pop_wav():
    mix = Mix(0.22)
    mix.tone(0.0, 0.05, E5, gain=0.40, table=BELL, attack=0.002, release=0.04)
    mix.tone(0.04, 0.14, A5, gain=0.34, table=BELL, attack=0.002)
    return mix.wav(peak=0.7)
