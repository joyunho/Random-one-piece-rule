# -*- coding: utf-8 -*-
"""설정 파일 저장/불러오기.

설정은 JSON 파일 하나에 전부 들어간다.
- exe 로 만들어 실행하면  : exe 가 있는 폴더의 `데이터/설정.json`
- 그 폴더에 못 쓰면       : %APPDATA%\\랜덤원피스룰\\설정.json
- 소스로 실행하면         : 프로젝트 폴더의 `데이터/설정.json`
"""

import copy
import json
import os
import sys
from pathlib import Path

from . import data, roster

CONFIG_FILENAME = "설정.json"
_config_path = None


def _candidate_dirs():
    """설정을 저장할 후보 폴더들 (앞에서부터 쓸 수 있는 곳을 고른다)."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent.parent
    yield base / "데이터"

    appdata = os.environ.get("APPDATA")
    if appdata:
        yield Path(appdata) / data.APP_NAME

    yield Path.home() / ("." + data.APP_NAME)


def config_path():
    """실제로 사용할 설정 파일 경로. 쓰기 가능한 첫 번째 후보를 고른다."""
    global _config_path
    if _config_path is not None:
        return _config_path

    for folder in _candidate_dirs():
        try:
            folder.mkdir(parents=True, exist_ok=True)
            probe = folder / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except Exception:
            continue
        _config_path = folder / CONFIG_FILENAME
        return _config_path

    # 어디에도 못 쓰면 홈 폴더에 직접
    _config_path = Path.home() / ("%s_%s" % (data.APP_NAME, CONFIG_FILENAME))
    return _config_path


def clean_names(names):
    """앞뒤 공백 정리 + 빈 줄 제거 + 중복 제거 (순서는 유지).

    중복이 남아 있으면 '전설 4개' 를 뽑을 때 같은 캐릭터가 두 번 나올 수 있다.
    """
    seen, out = set(), []
    for raw in names or []:
        name = str(raw).strip()
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def default_config():
    return {
        "version": 1,
        "colors": list(data.COLORS),
        "grades": list(data.GRADES),
        "grade_pool": list(data.GRADE_POOL),

        # 지츠 다이스 룰에서 굴리는 숫자 범위
        "dice_min": 1,
        "dice_max": 100,

        # 인생의고도전 (2026-07-16 확인본) : 플레이어별 10~20
        "altitude_min": 10,
        "altitude_max": 20,
        # 추가 추첨 범위는 영상에서 확인되지 않았다.
        # None 이면 임의로 채우지 않고 "범위 지정 필요" 로 막는다.
        "altitude2_min": None,
        "altitude2_max": None,

        # 너의상위는 : 1~5 를 뽑고 5 는 0상위
        "tier_min": 1,
        "tier_max": 5,
        "tier_zero_roll": 5,      # 이 눈금이 나오면 상위 0

        # 개인미션전 : 미션 개수와 실패 1개당 유카 (2026-07-23 확인본 = 10)
        "mission_count": 3,
        "mission_penalty": 10,

        # 이캐릭들필수에요 / 이캐릭들금지에요
        "must_legend": 4,
        "must_hidden": 4,
        "ban_legend": 7,
        "ban_hidden": 7,

        # 직전에 나온 메인 컨텐츠가 연속으로 또 나오지 않게
        "avoid_repeat": True,
        # 룰렛 연출 사용
        "animate": True,
        # 효과음 (윈도우에서만 소리가 난다)
        "sound": True,
        # 방송 출력 창 배경을 크로마키 초록으로
        "cast_chroma": False,

        "contents": [
            {"id": c["id"], "name": c["name"], "desc": c.get("desc", ""),
             "enabled": not data.is_off_by_default(c), "weight": 1.0}
            for c in data.CONTENTS
        ],
        "gangwon": copy.deepcopy(data.GANGWON_TABLE),

        # 녜힁제조기 : 상위 이름에 들어있는 글자 중 2글자를 뽑는다.
        #   - 등급을 뜻하는 글자(초월/불멸/…)는 뽑기 후보에서 빼야 의미가 있다.
        "nyehyung_count": 2,
        "nyehyung_strip_words": ["초월", "불멸", "영원", "제한", "신비"],

        "random_unit_chars": list(roster.DEFAULT_RANDOM_UNITS),

        "legend_chars": list(roster.DEFAULT_LEGEND),
        "hidden_chars": list(roster.DEFAULT_HIDDEN),
        "upper_chars": list(roster.DEFAULT_UPPER),
    }


def _merge(loaded):
    """저장된 설정에 빠진 항목을 기본값으로 채운다 (버전 올라가도 안 깨지게)."""
    cfg = default_config()

    for key, value in loaded.items():
        if key in ("contents", "gangwon"):
            continue
        cfg[key] = value

    # 메인 컨텐츠 : 사용자가 바꾼 이름/사용여부/가중치는 유지, 새로 생긴 항목은 추가
    saved = {c.get("id"): c for c in loaded.get("contents", []) if isinstance(c, dict)}
    merged = []
    for base in cfg["contents"]:
        item = dict(base)
        old = saved.get(base["id"])
        if old:
            item["name"] = old.get("name", item["name"])
            item["desc"] = old.get("desc", item["desc"])
            item["enabled"] = bool(old.get("enabled", True))
            try:
                item["weight"] = float(old.get("weight", 1.0))
            except (TypeError, ValueError):
                item["weight"] = 1.0
        merged.append(item)
    cfg["contents"] = merged

    # 강원랜디 확률표는 통째로 사용자가 편집하는 값이라 있으면 그대로 사용
    table = loaded.get("gangwon")
    if isinstance(table, list) and table:
        cleaned = []
        for row in table:
            if not isinstance(row, dict) or not str(row.get("name", "")).strip():
                continue
            try:
                weight = float(row.get("weight", 0))
            except (TypeError, ValueError):
                weight = 0.0
            rng = row.get("range")
            if isinstance(rng, (list, tuple)) and len(rng) == 2:
                try:
                    rng = [int(rng[0]), int(rng[1])]
                except (TypeError, ValueError):
                    rng = None
            else:
                rng = None
            cleaned.append({"name": str(row["name"]).strip(), "weight": weight, "range": rng})
        if cleaned:
            cfg["gangwon"] = cleaned

    # 목록이 비어 있으면 기본 명단을 채워준다.
    # (기본값이 생기기 전에 만들어진 설정 파일도 그대로 쓸 수 있도록)
    defaults = {
        "legend_chars": roster.DEFAULT_LEGEND,
        "hidden_chars": roster.DEFAULT_HIDDEN,
        "upper_chars": roster.DEFAULT_UPPER,
        "random_unit_chars": roster.DEFAULT_RANDOM_UNITS,
    }
    for key, fallback in defaults.items():
        cfg[key] = clean_names(cfg.get(key)) or list(fallback)
    return cfg


def load_config():
    path = config_path()
    if not path.exists():
        return default_config()
    try:
        with open(path, "r", encoding="utf-8") as fp:
            loaded = json.load(fp)
        if not isinstance(loaded, dict):
            raise ValueError("설정 파일 형식이 올바르지 않습니다.")
        return _merge(loaded)
    except Exception:
        # 설정이 깨졌으면 백업만 남기고 기본값으로 시작
        try:
            path.replace(path.with_suffix(".json.bak"))
        except Exception:
            pass
        return default_config()


def save_config(cfg):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as fp:
        json.dump(cfg, fp, ensure_ascii=False, indent=2)
    tmp.replace(path)
    return path
