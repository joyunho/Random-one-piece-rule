@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "LOG=%~dp0build_log.txt"
if exist "%LOG%" del "%LOG%"

echo ================================================
echo    Random One Piece Rule  -  EXE Builder
echo ================================================
echo.

REM ---- find a working python -------------------------------------------
set "PY="
where py >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY goto :have_python
where python >nul 2>&1
if not errorlevel 1 set "PY=python"
:have_python
if not defined PY goto :no_python

echo [1/4] Checking Python ...
%PY% --version
if errorlevel 1 goto :no_python

%PY% -c "import tkinter" >nul 2>&1
if errorlevel 1 goto :no_tkinter
echo.

echo [2/4] Installing PyInstaller ...   [log: build_log.txt]
%PY% -m pip install --upgrade pyinstaller >>"%LOG%" 2>&1
if errorlevel 1 goto :pip_failed
echo.

echo [3/4] Building the exe ...  this takes a few minutes, please wait.
%PY% -m PyInstaller --noconfirm --onefile --windowed --name RandomOnePieceRule --collect-submodules ropr main.py >>"%LOG%" 2>&1
if errorlevel 1 goto :build_failed
echo.

echo [4/4] Renaming ...
%PY% tools\finish_build.py
if errorlevel 1 goto :rename_failed

echo.
echo ================================================
echo    DONE.  Open the  dist  folder.
echo ================================================
goto :end


:no_python
echo.
echo [ERROR] Python was not found on this PC.
echo.
echo   1. Install Python 3 from  https://www.python.org/downloads/
echo   2. Turn ON "Add python.exe to PATH" in the installer
echo   3. Run this file again
echo.
echo   Or skip building: download the ready-made exe from GitHub
echo   Actions tab  -  build-exe  -  Artifacts
goto :end

:no_tkinter
echo.
echo [ERROR] tkinter is missing from this Python.
echo   Reinstall Python 3 and keep the "tcl/tk and IDLE" option checked.
goto :end

:pip_failed
echo.
echo [ERROR] Could not install PyInstaller.
echo   Open  build_log.txt  in this folder to see why.
goto :end

:build_failed
echo.
echo [ERROR] The build failed.
echo   Open  build_log.txt  in this folder to see why.
goto :end

:rename_failed
echo.
echo [WARN] Rename step failed, but the exe was built:
echo   dist\RandomOnePieceRule.exe
goto :end

:end
echo.
pause
endlocal
