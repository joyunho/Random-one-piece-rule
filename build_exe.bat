@echo off
chcp 65001 > nul
REM ============================================================
REM  윈도우에서 exe 만들기
REM  1) 파이썬 3.10 이상 설치 (설치할 때 tcl/tk 옵션 체크)
REM  2) 이 파일을 더블클릭
REM  3) dist 폴더 안에 랜덤원피스룰.exe 가 생김
REM ============================================================
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1

echo [1/3] PyInstaller 설치 확인...
python -m pip install --upgrade pyinstaller || goto :fail

echo.
echo [2/3] exe 빌드 중... (몇 분 걸립니다)
python -m PyInstaller --noconfirm --onefile --windowed ^
  --name "RandomOnePieceRule" ^
  --collect-submodules ropr ^
  main.py || goto :fail

echo.
echo [3/3] 이름 바꾸는 중...
if exist "dist\랜덤원피스룰.exe" del "dist\랜덤원피스룰.exe"
move /y "dist\RandomOnePieceRule.exe" "dist\랜덤원피스룰.exe" > nul

echo.
echo ============================================
echo  완료!  dist\랜덤원피스룰.exe
echo ============================================
pause
exit /b 0

:fail
echo.
echo 빌드에 실패했습니다. 위 메시지를 확인해 주세요.
pause
exit /b 1
