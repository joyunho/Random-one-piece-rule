# -*- coding: utf-8 -*-
"""기본 데이터 정의.

여기 값들은 '처음 실행할 때의 기본값'이다.
실제로 쓰이는 값은 설정 파일(설정.json)에 저장되고, 프로그램의 [설정] 탭에서 바꿀 수 있다.
"""

APP_NAME = "랜덤원피스룰"
APP_TITLE = "랜덤 원피스 룰 뽑기"
VERSION = "1.0.0"

# 4명의 플레이어 색.
# 공개 순서는 영상에서 확인된 빨강 -> 보라 -> 파랑 -> 노랑 을 따른다.
COLORS = ["빨강", "보라", "파랑", "노랑"]
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

# 검증 상태 — 오슥균 공개 영상 확인본(비공식) 기준
#   verified   : 영상에서 규칙 문장/적용 장면까지 확인
#   partial    : 핵심은 확인, 일부 수치·예외 미확인
#   unverified : 해당 영상은 있으나 세부 룰 미확인 → 기본 꺼둠
#   custom     : 영상 근거 없이 이 프로그램에서 정한 값
STATUS_LABEL = {
    "verified": "영상 확인",
    "partial": "일부 확인",
    "unverified": "미확인",
    "custom": "커스텀",
}
STATUS_COLOR = {
    "verified": "#1f7a4d",
    "partial": "#8a6100",
    "unverified": "#8e2b26",
    "custom": "#4a5568",
}

# 세부 룰이 확인되지 않아 기본으로 꺼두는 컨텐츠
def is_off_by_default(content):
    return content.get("status") == "unverified"


# 메인 컨텐츠.
#   id     : 내부 식별자 (추가 뽑기 분기용, 바꾸지 말 것)
#   name   : 화면에 보이는 이름 (설정에서 수정 가능)
#   follow : 뽑힌 뒤에 이어지는 추가 뽑기 종류
CONTENTS = [
    {
        "id": "story_bomber", "name": "스토리 폭격기전", "follow": None,
        "status": "unverified", "desc": "",
        "source": "https://www.youtube.com/watch?v=Mf9DV3X10Oc",
    },
    {
        "id": "adcarry", "name": "원딜전(물1마1)", "follow": None,
        "status": "unverified", "desc": "물1 마1 구성으로 진행합니다. (세부 예외 미확인)",
        "source": "https://www.youtube.com/watch?v=010qUh_lXBo",
    },
    {
        "id": "force4", "name": "4인 강제전", "follow": "force4",
        "status": "unverified",
        "desc": "상위 중에서 한 마리를 뽑습니다. 4명 모두 그 상위로 강제로 갑니다.\n"
                "(등급 공유인지 각자 한 유닛인지 영상 미확인)",
        "source": "https://www.youtube.com/watch?v=2k_AaxJJMqw",
    },
    {
        "id": "jits_dice", "name": "지츠'다이스'룰", "follow": "jits_dice",
        "status": "unverified",
        "desc": "등급마다 상위를 한 마리씩 뽑아 놓고, 주사위를 굴려 높게 뜬 사람부터 "
                "그중 하나를 골라 갑니다.\n(주사위 범위·동점 처리 영상 미확인)",
        "source": "https://www.youtube.com/watch?v=l7LVRLnjyaU",
    },
    {
        "id": "nightmare", "name": "변질된 악몽", "follow": None,
        "status": "unverified", "desc": "",
        "source": "https://www.youtube.com/watch?v=PVVyh30Tv1k",
    },
    {
        "id": "nyehyung", "name": "녜힁제조기", "follow": "nyehyung",
        "status": "partial",
        "desc": "상위 이름에 들어있는 글자를 2개 뽑고, 그 글자가 이름에 포함된 "
                "상위만 사용해서 클리어합니다.\n"
                "팀 안에서 같은 상위를 중복해서 쓰는 것은 금지입니다.",
        "source": "https://www.youtube.com/watch?v=doSjz1rHGsM",
    },
    {
        "id": "altitude", "name": "인생의고도전", "follow": "altitude",
        "status": "partial",
        "desc": "플레이어마다 10~20 중 하나를 뽑고, 그 숫자만큼 고도를 갑니다.\n"
                "졸업보상을 가장 늦게 받은 1명만 추가 추첨을 한 번 더 합니다.",
        "source": "https://www.youtube.com/watch?v=j4shAeicaX0",
    },
    {
        "id": "mystic_world", "name": "신비한이세계전", "follow": None,
        "status": "unverified", "desc": "",
        "source": "https://www.youtube.com/watch?v=Ul0TK0hTvlE",
    },
    {
        "id": "your_tier", "name": "너의상위는", "follow": "your_tier",
        "status": "verified",
        "desc": "플레이어마다 1~5 를 뽑습니다. 1~4 는 나온 숫자만큼 상위를 올리고, "
                "5 가 나오면 상위 없음(0상위)입니다.",
        "source": "https://www.youtube.com/watch?v=c9wDUtDjb-U",
    },
    {
        "id": "must_char", "name": "이캐릭들필수에요", "follow": "must_char",
        "status": "verified",
        "desc": "팀 공통으로 전설 4명 · 히든 4명을 뽑습니다. 팀이 이 목록을 전부 "
                "한 번 이상 완성하면 됩니다.\n"
                "한 사람이 여러 개를 몰아서 만들어도 되고, 만든 뒤 상위 재료로 "
                "소비해도 완성으로 인정합니다.",
        "source": "https://www.youtube.com/watch?v=5pAILNk8aME",
    },
    {
        "id": "ban_char", "name": "이캐릭들금지에요", "follow": "ban_char",
        "status": "verified",
        "desc": "팀 공통으로 전설 7명 · 히든 7명을 뽑습니다. 이 캐릭터는 갈 수 없습니다.\n"
                "일단 만든 뒤 상위 조합 재료로 소비하는 우회도 금지입니다.",
        "source": "https://www.youtube.com/watch?v=XdV6tw9Vpuk",
    },
    {
        "id": "required_random_unit", "name": "필수!랜덤유닛획득",
        "follow": "required_random_unit", "status": "verified",
        "desc": "플레이어마다 랜덤/콜라보 유닛을 하나씩 배정받고, 그 유닛을 반드시 "
                "만들어야 합니다.\n"
                "이후 상위 재료로 소비해도 인정되고, 그 외 상위 선택은 자유입니다.",
        "source": "https://www.youtube.com/watch?v=or3EkIQFIag",
    },
    {
        "id": "gangwon", "name": "강원랜디", "follow": "gangwon",
        "status": "partial",
        "desc": "플레이어마다 미션을 하나씩 뽑습니다. 숫자가 붙은 결과는 숫자까지 뽑습니다.\n"
                "확률표는 영상 근거를 확인하지 못해 커스텀 값입니다.",
        "source": "https://www.youtube.com/watch?v=k1gCBQjWItg",
    },
    {
        "id": "personal_mission", "name": "개인미션전", "follow": "personal_mission",
        "status": "verified",
        "desc": "플레이어마다 비밀 미션 3개를 수행합니다. 실패 1개당 유카가 늘어납니다.\n"
                "이름은 개인미션전이지만 경기는 팀전이고, 종료 후 각자 미션을 공개해 "
                "대조합니다.",
        "source": "https://www.youtube.com/watch?v=nbU6T6J_ZV8",
    },
    {
        "id": "random_nav", "name": "랜덤항법전", "follow": None,
        "status": "unverified", "desc": "",
        "source": "https://www.youtube.com/watch?v=WotOqueqLqA",
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


# id -> 검증 상태 (설정에서 이름/설명을 바꿔도 상태는 원본을 따른다)
CONTENT_STATUS = {c["id"]: c["status"] for c in CONTENTS}
CONTENT_SOURCE = {c["id"]: c.get("source", "") for c in CONTENTS}
