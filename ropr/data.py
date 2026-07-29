# -*- coding: utf-8 -*-
"""기본 데이터 정의.

여기 값들은 '처음 실행할 때의 기본값'이다.
실제로 쓰이는 값은 설정 파일(설정.json)에 저장되고, 프로그램의 [설정] 탭에서 바꿀 수 있다.
"""

APP_NAME = "랜덤원피스룰"
APP_TITLE = "랜덤 원피스 룰 뽑기"
VERSION = "1.0.0"

# 4명의 플레이어 색 (워크 기준 빨/파/보/노)
COLORS = ["빨강", "파랑", "보라", "노랑"]
COLOR_HEX = {
    "빨강": "#d64545",
    "파랑": "#3a7bd5",
    "보라": "#8e5bd0",
    "노랑": "#c08a00",
}

# 초 / 불 / 영 / 제
GRADES = ["초월", "불멸", "영원", "제한"]

# [등급 뽑기] 탭에서 한 마리 뽑을 때 쓰는 후보 (초월/불멸/영원/제한/신비)
GRADE_POOL = ["초월", "불멸", "영원", "제한", "신비"]

# 메인 컨텐츠.
#   id     : 내부 식별자 (추가 뽑기 분기용, 바꾸지 말 것)
#   name   : 화면에 보이는 이름 (설정에서 수정 가능)
#   follow : 뽑힌 뒤에 이어지는 추가 뽑기 종류
CONTENTS = [
    {"id": "story_bomber",     "name": "스토리 폭격기전",              "follow": None},
    {"id": "adcarry",          "name": "원딜전(물1마1)",               "follow": None},
    {"id": "force4",           "name": "4인 강제전",                   "follow": "force4"},
    {"id": "jits_dice",        "name": "지츠'다이스'룰",               "follow": "jits_dice"},
    {"id": "nightmare",        "name": "변질된 악몽",                  "follow": None},
    {"id": "nyehyung",         "name": "녜힁제조기",                   "follow": "nyehyung"},
    {"id": "altitude",         "name": "인생의고도전(기본10 + ?)",     "follow": "altitude"},
    {"id": "mystic_world",     "name": "신비한이세계전",               "follow": None},
    {"id": "your_tier",        "name": "너의상위는(0~4)",              "follow": "your_tier"},
    {"id": "must_char",        "name": "이캐릭들필수에요(4전설+4히든)", "follow": "must_char"},
    {"id": "ban_char",         "name": "이캐릭들금지에요(7전설+7히든)", "follow": "ban_char"},
    {"id": "gangwon",          "name": "강원랜디",                     "follow": "gangwon"},
    {"id": "personal_mission", "name": "개인미션전",                   "follow": None},
    {"id": "random_nav",       "name": "랜덤항법전",                   "follow": None},
]

# 강원랜디 확률표.
#   range 가 있으면 그 결과를 뽑은 뒤 범위 안에서 숫자를 한 번 더 뽑는다.
#   가중치 합계 = 0.55 + 5.85 * 17 = 100.00
GANGWON_TABLE = [
    {"name": "꽝(1불1초1영1제)",        "weight": 0.55, "range": None},
    {"name": "강제상위",                "weight": 5.85, "range": None},
    {"name": "강제신비함",              "weight": 5.85, "range": None},
    {"name": "강제전설+히든",           "weight": 5.85, "range": None},
    {"name": "고유생 상위",             "weight": 5.85, "range": None},
    {"name": "개인미션 클리어",         "weight": 5.85, "range": None},
    {"name": "노불노초",                "weight": 5.85, "range": None},
    {"name": "랜덤항법",                "weight": 5.85, "range": None},
    {"name": "아이템사용상위",          "weight": 5.85, "range": None},
    {"name": "올중도",                  "weight": 5.85, "range": None},
    {"name": "전설위습먹기",            "weight": 5.85, "range": None},
    {"name": "체젠,마나젠,암브,방무",   "weight": 5.85, "range": None},
    {"name": "토큰 희귀함 먹기",        "weight": 5.85, "range": None},
    {"name": "포네그리프 해석",         "weight": 5.85, "range": None},
    {"name": "변이횟수 0~3",            "weight": 5.85, "range": [0, 3]},
    {"name": "상위고정 1~4",            "weight": 5.85, "range": [1, 4]},
    {"name": "해적선 사용 0~5",         "weight": 5.85, "range": [0, 5]},
    {"name": "인생의고도 10~20",        "weight": 5.85, "range": [10, 20]},
]
