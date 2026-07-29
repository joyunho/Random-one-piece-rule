# -*- coding: utf-8 -*-
"""빌드가 끝난 exe 파일 이름을 한글로 바꾼다.

배치 파일 안에서 한글 파일명을 다루면 인코딩 때문에 깨지므로,
이 부분만 파이썬으로 뺐다. (윈도우/리눅스 모두 동작)
"""

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")

BUILT_NAME = "RandomOnePieceRule"
FINAL_NAME = "랜덤원피스룰"


def main():
    suffix = ".exe" if os.name == "nt" else ""
    src = os.path.join(DIST, BUILT_NAME + suffix)
    dst = os.path.join(DIST, FINAL_NAME + suffix)

    if not os.path.exists(src):
        sys.stderr.write("빌드 결과물을 찾지 못했습니다: %s\n" % src)
        return 1

    if os.path.exists(dst):
        os.remove(dst)
    shutil.move(src, dst)
    print(dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
