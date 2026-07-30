@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "LOG=%~dp0build_log.txt"
if exist "%LOG%" del "%LOG%"

echo ==============================================================
echo    Random One Piece Rule   -   Install Python + Build EXE
echo ==============================================================
echo.

REM ---------------------------------------------- [1/4] find python
echo [1/4] Looking for Python ...
call :find_python
if defined PY goto :have_python

echo       Not found. Installing Python 3 with winget ...
echo       (a Windows permission popup may appear - allow it)
echo.
where winget >nul 2>&1
if errorlevel 1 goto :no_winget

winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
echo.
call :refresh_path
call :find_python
if not defined PY goto :install_failed

:have_python
echo       Using : %PY%
%PY% -c "import sys; print('      Version :', sys.version.split()[0])"
%PY% -c "import tkinter" >nul 2>&1
if errorlevel 1 goto :no_tkinter
echo.

REM ------------------------------------------ [2/4] pyinstaller
echo [2/4] Installing PyInstaller ...   [log: build_log.txt]
%PY% -m pip install --upgrade pip >>"%LOG%" 2>&1
%PY% -m pip install --upgrade pyinstaller >>"%LOG%" 2>&1
if errorlevel 1 goto :pip_failed
echo.

REM ------------------------------------------------ [3/4] build
echo [3/4] Building the exe ...  this takes a few minutes, please wait.
%PY% -m PyInstaller --noconfirm --onefile --windowed --name RandomOnePieceRule --collect-submodules ropr main.py >>"%LOG%" 2>&1
if errorlevel 1 goto :build_failed
echo.

REM ----------------------------------------------- [4/4] rename
echo [4/4] Renaming ...
%PY% tools\finish_build.py
if errorlevel 1 goto :rename_failed

echo.
echo ==============================================================
echo    DONE.   Open the  dist  folder.
echo ==============================================================
goto :end


REM ==================================================== subroutines
:find_python
set "PY="
call :probe py -3
if not defined PY call :probe python
if not defined PY call :probe python3
goto :eof

:probe
REM Actually run it. The Microsoft Store placeholder python.exe fails here,
REM which is why "where python" alone is not enough.
%* -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if errorlevel 1 goto :eof
set "PY=%*"
goto :eof

:refresh_path
REM winget just changed PATH, but this window still has the old one.
for /f "skip=2 tokens=2,*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "MPATH=%%b"
for /f "skip=2 tokens=2,*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "UPATH=%%b"
if defined MPATH set "PATH=%MPATH%"
if defined UPATH set "PATH=%PATH%;%UPATH%"
REM common install folders, just in case
set "PATH=%PATH%;%WINDIR%"
for %%v in (313 312 311 310) do (
    set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python%%v;%LOCALAPPDATA%\Programs\Python\Python%%v\Scripts"
    set "PATH=%PATH%;%ProgramFiles%\Python%%v;%ProgramFiles%\Python%%v\Scripts"
)
goto :eof


REM ======================================================== errors
:no_winget
echo.
echo [ERROR] winget is not available on this PC, so Python cannot be
echo         installed automatically.
echo.
echo   Install Python 3 by hand :  https://www.python.org/downloads/
echo   Turn ON "Add python.exe to PATH" in the installer, then run this again.
echo.
echo   Or skip building entirely - download the ready-made exe :
echo   GitHub  -  Actions tab  -  build-exe  -  Artifacts
goto :end

:install_failed
echo.
echo [ERROR] Python was installed but this window still cannot see it.
echo         Close this window, open a NEW one, and run this file again.
goto :end

:no_tkinter
echo.
echo [ERROR] This Python has no tkinter.
echo         Reinstall Python 3 and keep "tcl/tk and IDLE" checked.
goto :end

:pip_failed
echo.
echo [ERROR] Could not install PyInstaller.  See  build_log.txt
goto :end

:build_failed
echo.
echo [ERROR] The build failed.  See  build_log.txt
goto :end

:rename_failed
echo.
echo [WARN] Rename failed, but the exe was built :
echo        dist\RandomOnePieceRule.exe
goto :end

:end
echo.
pause
endlocal
