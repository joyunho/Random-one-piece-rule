# -*- coding: utf-8 -*-
"""효과음 재생.

소리를 만드는 건 synth.py 가 하고, 여기서는 '언제 무엇을 트는지' 만 다룬다.
윈도우에서만 소리가 나고(winsound), 다른 OS 에서는 조용히 아무것도 안 한다.

주의 1 — winsound 는 '메모리에서 비동기 재생' 을 지원하지 않는다.

    winsound.PlaySound(data, SND_MEMORY | SND_ASYNC)
        -> RuntimeError("Cannot play asynchronously from memory")

CPython 이 Win32 를 부르기도 전에 막아 버리는 검사다.
(PC/winsound.c : "Sidestep reference counting headache")
그래서 만든 WAV 를 임시 폴더에 파일로 써 두고 SND_FILENAME | SND_ASYNC 로 튼다.

주의 2 — winsound 는 한 번에 한 소리만 낸다.
새로 재생하면 앞의 소리가 그 자리에서 끊긴다. 그래서 'BGM 을 깔고 그 위에 효과음'
같은 건 재생 두 번으로는 안 된다. 대신 synth.py 에서 미리 섞은
'긴장감 트랙 + 릴 틱 + 마지막 화음' 한 덩어리를 스핀 시작할 때 한 번만 튼다.
"""

import atexit
import os
import shutil
import tempfile
import time

from . import synth

try:
    import winsound
except ImportError:            # 윈도우가 아니면 소리 없이 동작
    winsound = None

_cache = {}
_files = {}
_tmpdir = None
_enabled = True
_bgm = True                    # 스핀 중 긴장감 트랙
_busy_until = 0.0              # 지금 틀어 둔 트랙이 끝나는 시각
last_error = ""                # 소리가 안 날 때 [설정] 탭에서 이유를 보여준다


# 이름 -> (만드는 함수, 길이초). 길이는 트랙이 겹치지 않게 하려고 들고 있다.
_SOUNDS = {
    "tick": (synth.tick_wav, 0.05),
    "settle": (synth.settle_wav, 1.00),
    "taunt": (synth.taunt_wav, 1.35),
    "jackpot": (synth.jackpot_wav, 1.45),
    "thud": (synth.thud_wav, 0.75),
    "pop": (synth.pop_wav, 0.22),
}

# 스핀 트랙 : 패널(38ms/1.14/235)과 메인 룰렛(45ms/1.16/270) 은 길이가 다르다
SPIN_PANEL = (38, 1.14, 235)
SPIN_MAIN = (45, 1.16, 270)


def _spin_key(kind, timing):
    return "spin_%s_%d" % (kind, int(timing[0]))


def _register_spins():
    """스핀 트랙을 등록한다.

    끝소리 종류마다 트랙을 따로 만들 수도 있지만, 실제로 쓰는 건 'settle' 뿐이다.
    (놀리는 소리·꽝은 스핀이 끝난 뒤에 따로 나온다)
    안 쓰는 걸 미리 만들면 프로그램 켤 때 1초 넘게 멈춰 있어서 만들지 않는다.
    """
    for timing in (SPIN_PANEL, SPIN_MAIN):
        _ticks, span = synth.spin_schedule(*timing)
        _SOUNDS[_spin_key("settle", timing)] = (
            (lambda t=timing: synth.spin_wav("settle", *t)), span + 1.15)


_register_spins()


def available():
    return winsound is not None


def set_enabled(flag):
    global _enabled
    _enabled = bool(flag)


def set_bgm(flag):
    global _bgm
    _bgm = bool(flag)


def bgm_enabled():
    return _bgm


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


def _play(key, force=False):
    """소리 하나 재생. force 가 아니면 트랙이 도는 중엔 건드리지 않는다."""
    global last_error, _busy_until
    if winsound is None or not _enabled:
        return False
    builder, seconds = _SOUNDS[key]
    # 긴장감 트랙이 도는 중에 딴 걸 틀면 트랙이 끊긴다. 그냥 넘어간다.
    if not force and time.monotonic() < _busy_until:
        return False
    try:
        data = _cache.get(key)
        if data is None:
            data = _cache[key] = builder()
        # SND_NODEFAULT : 파일을 못 찾아도 윈도우 기본 '딩' 소리를 내지 않는다
        winsound.PlaySound(
            _path_for(key, data),
            winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        _busy_until = time.monotonic() + seconds
        last_error = ""
        return True
    except Exception as exc:        # 소리 때문에 프로그램이 죽으면 안 된다
        last_error = "%s: %s" % (type(exc).__name__, exc)
        return False


# ------------------------------------------------------------------ 효과음들
def tick():
    """긴장감 트랙을 끈 경우에만 쓰는 낱개 '틱'."""
    _play("tick")


def settle():
    _play("settle")


def taunt():
    # 놀리는 소리는 스핀 트랙을 끊어서라도 들려줘야 한다 (그게 하이라이트)
    _play("taunt", force=True)


def jackpot():
    _play("jackpot", force=True)


def thud():
    _play("thud", force=True)


def pop():
    _play("pop")


def spin_start(kind="settle", timing=SPIN_PANEL):
    """스핀이 시작될 때 긴장감 트랙을 한 번 튼다.

    돌려주는 값이 True 면 마지막 화음까지 트랙에 들어 있으니,
    부르는 쪽에서 틱이나 끝소리를 따로 낼 필요가 없다.
    """
    if winsound is None or not _enabled or not _bgm:
        return False
    if time.monotonic() < _busy_until:     # 이미 돌고 있으면 그게 계속 깔린다
        return True
    return _play(_spin_key(kind, timing), force=True)


def stop():
    """지금 나는 소리를 멈춘다."""
    global _busy_until
    _busy_until = 0.0
    if winsound is None:
        return
    try:
        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception:
        pass


def warm_next():
    """미리 만들어 둘 소리를 하나만 만든다. 남은 게 있으면 True.

    전부 한 번에 만들면 0.5초쯤 멈춰 있어서, 창을 띄운 뒤 한 개씩 나눠 만든다.
    긴 트랙(스핀)을 먼저 만들어야 첫 뽑기에서 안 버벅인다.
    """
    global last_error
    if winsound is None:
        return False
    todo = [k for k in _SOUNDS if k not in _files]
    if not todo:
        return False
    todo.sort(key=lambda k: -_SOUNDS[k][1])      # 긴 것부터
    key = todo[0]
    try:
        data = _cache.get(key)
        if data is None:
            data = _cache[key] = _SOUNDS[key][0]()
        _path_for(key, data)
    except Exception as exc:
        last_error = "%s: %s" % (type(exc).__name__, exc)
        _files[key] = ""                          # 계속 다시 시도하지 않게
    return len(todo) > 1


def warm_up():
    """미리 만들기를 끝까지 (테스트·스크립트용)."""
    while warm_next():
        pass


def self_test():
    """[설정] 탭의 '소리 테스트' 버튼용. 실패하면 이유를 글자로 돌려준다."""
    if winsound is None:
        return "이 컴퓨터는 윈도우가 아니라서 소리를 낼 수 없어요."
    if not _enabled:
        return "효과음이 꺼져 있어요. [메인 뽑기] 화면의 [효과음] 을 켜 주세요."
    stop()
    if _bgm:
        _play(_spin_key("settle", SPIN_PANEL), force=True)
        what = "긴장감 트랙 + 마지막 화음"
    else:
        _play("settle", force=True)
        what = "마지막 화음"
    if last_error:
        return "소리를 내지 못했어요 — " + last_error
    return "%s 를 재생했어요. 안 들리면 윈도우 볼륨 믹서에서 이 프로그램이 " \
           "음소거되어 있는지 확인해 주세요." % what
