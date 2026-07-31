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
    {
        "id": "story_bomber", "name": "스토리 폭격기전", "follow": None,
        "desc": "",
    },
    {
        "id": "adcarry", "name": "원딜전(물1마1)", "follow": None,
        "desc": "물1 마1 구성으로 진행합니다.",
    },
    {
        "id": "force4", "name": "4인 강제전", "follow": "force4",
        "desc": "상위 중에서 한 마리를 뽑습니다. 4명 모두 그 상위로 강제로 갑니다.",
    },
    {
        "id": "jits_dice", "name": "지츠'다이스'룰", "follow": "jits_dice",
        "desc": "등급마다 상위를 한 마리씩 뽑아 놓고, 빨/파/보/노가 주사위를 굴려 "
                "높게 뜬 사람부터 그중 하나를 골라 갑니다.",
    },
    {
        "id": "nightmare", "name": "변질된 악몽", "follow": None,
        "desc": "",
    },
    {
        "id": "nyehyung", "name": "녜힁제조기", "follow": "nyehyung",
        "desc": "상위 이름에 들어있는 글자를 2개 뽑고, 그 글자가 이름에 포함된 "
                "상위만 사용해서 클리어합니다.",
    },
    {
        "id": "altitude", "name": "인생의고도전(0~15)", "follow": "altitude",
        "desc": "색깔별로 0~15 를 뽑습니다. [추가 고도] 를 누르면 0~5 가 나와서 "
                "기존 고도에 자동으로 더해집니다.",
    },
    {
        "id": "mystic_world", "name": "신비한이세계전", "follow": None,
        "desc": "",
    },
    {
        "id": "your_tier", "name": "너의상위는(0~4)", "follow": "your_tier",
        "desc": "빨/파/보/노가 각각 0~4 를 뽑아, 그 개수만큼 상위를 씁니다.",
    },
    {
        "id": "must_char", "name": "이캐릭들필수에요(4전설+4히든)", "follow": "must_char",
        "desc": "전설 4명 · 히든 4명을 뽑습니다. 뽑힌 캐릭터는 반드시 써야 합니다.",
    },
    {
        "id": "ban_char", "name": "이캐릭들금지에요(7전설+7히든)", "follow": "ban_char",
        "desc": "전설 7명 · 히든 7명을 뽑습니다. 뽑힌 캐릭터는 쓸 수 없습니다.",
    },
    {
        "id": "gangwon", "name": "강원랜디", "follow": "gangwon",
        "desc": "확률표에서 결과를 하나 뽑습니다. 숫자 범위가 붙은 결과는 숫자까지 뽑습니다.",
    },
    {
        "id": "personal_mission", "name": "개인미션전", "follow": None,
        "desc": "",
    },
    {
        "id": "random_nav", "name": "랜덤항법전", "follow": None,
        "desc": "",
    },
    {
        "id": "unlucky", "name": "내가 제일 운 없어", "follow": "unlucky",
        "desc": "색깔별로 행운의 토큰을 뽑습니다. 토큰을 쓰지 않고 클리어하면 "
                "가진 토큰 숫자만큼 유카를 줄일 수 있습니다.\n"
                "제일 적게 받은 사람은 스토리를 과반 이상 먹으면 토큰을 한 번 더 뽑을 수 있습니다.",
    },
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
