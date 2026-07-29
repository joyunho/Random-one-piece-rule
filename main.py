# -*- coding: utf-8 -*-
"""랜덤 원피스 룰 뽑기 - 실행 진입점.

소스로 실행 :  python main.py
exe 로 만들기 :  build_exe.bat  (또는 GitHub Actions 의 build-exe 워크플로)
"""

import sys


def main():
    try:
        from ropr.ui import main as run
    except ImportError as exc:  # tkinter 가 없는 환경
        sys.stderr.write(
            "실행에 필요한 모듈을 찾지 못했습니다: %s\n"
            "파이썬을 설치할 때 'tcl/tk' 옵션이 함께 설치되어 있어야 합니다.\n" % exc)
        return 1
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
