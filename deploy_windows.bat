@echo off
setlocal enabledelayedexpansion

echo.
echo ====================================================
echo   Mold Management System - Windows Deployment
echo ====================================================
echo.

:: ---- Step 1: Find Python ------------------------------------
set PYTHON=

py --version >nul
if not errorlevel 1 (
    set PYTHON=py
    goto :found
)

python --version >nul
if not errorlevel 1 (
    set PYTHON=python
    goto :found
)

if exist "D:\python\python.exe"                  set PYTHON=D:\python\python.exe
if exist "C:\Python313\python.exe"               set PYTHON=C:\Python313\python.exe
if exist "C:\Python312\python.exe"               set PYTHON=C:\Python312\python.exe
if exist "C:\Python311\python.exe"               set PYTHON=C:\Python311\python.exe
if exist "C:\Python310\python.exe"               set PYTHON=C:\Python310\python.exe

if "!PYTHON!"=="" (
    echo [ERROR] Python not found.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    echo Check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

:found
"!PYTHON!" --version
echo.

:: ---- Step 2: Create virtual environment ---------------------
set ROOT=%~dp0
set VENV=%ROOT%.venv
set VPYTHON=%VENV%\Scripts\python.exe
set VSTREAMLIT=%VENV%\Scripts\streamlit.exe

if exist "%VPYTHON%" (
    echo [Step 1] Virtual environment already exists.
) else (
    echo [Step 1] Creating virtual environment...
    "!PYTHON!" -m venv "%VENV%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
)
echo.

:: ---- Step 3: Upgrade pip ------------------------------------
echo [Step 2] Upgrading pip...
"%VPYTHON%" -m pip install --upgrade pip --quiet -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
echo [OK] pip ready.
echo.

:: ---- Step 4: Install packages (use domestic mirror) ---------
echo [Step 3] Installing packages via Tsinghua mirror...
"%VPYTHON%" -m pip install -r "%ROOT%requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
if errorlevel 1 (
    echo.
    echo [WARN] Tsinghua mirror failed, trying Aliyun mirror...
    "%VPYTHON%" -m pip install -r "%ROOT%requirements.txt" -i https://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
    if errorlevel 1 (
        echo.
        echo [ERROR] Package install failed on all mirrors.
        echo Check network, then run manually:
        echo   cd /d "%ROOT%"
        echo   .venv\Scripts\pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
        pause
        exit /b 1
    )
)
echo.
echo [OK] All packages installed.
echo.

:: ---- Step 5: Create data directory --------------------------
if not exist "%ROOT%data" mkdir "%ROOT%data"
echo [Step 4] Data directory ready.
echo.

:: ---- Step 6: Write start_app.bat ----------------------------
echo [Step 5] Writing start_app.bat...

set STARTBAT=%ROOT%start_app.bat
echo @echo off                                                    > "%STARTBAT%"
echo cd /d "%ROOT%"                                              >> "%STARTBAT%"
echo echo.                                                       >> "%STARTBAT%"
echo echo ==========================================             >> "%STARTBAT%"
echo echo   Starting Mold Management System                      >> "%STARTBAT%"
echo echo   URL: http://localhost:8501                           >> "%STARTBAT%"
echo echo ==========================================             >> "%STARTBAT%"
echo echo.                                                       >> "%STARTBAT%"
echo "%VSTREAMLIT%" run app\main.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false >> "%STARTBAT%"
echo pause                                                       >> "%STARTBAT%"

echo [OK] start_app.bat created.

:: ---- Step 7: Write stop_app.bat -----------------------------
set STOPBAT=%ROOT%stop_app.bat
echo @echo off                                     > "%STOPBAT%"
echo echo Stopping Mold Management System...       >> "%STOPBAT%"
echo taskkill /F /IM streamlit.exe                >> "%STOPBAT%"
echo echo Done.                                   >> "%STOPBAT%"
echo pause                                        >> "%STOPBAT%"

echo [OK] stop_app.bat created.
echo.

:: ---- Done ---------------------------------------------------
echo ====================================================
echo   Deployment complete!
echo.
echo   Start : double-click start_app.bat
echo   Stop  : double-click stop_app.bat
echo   URL   : http://localhost:8501
echo   Login : admin / Admin@123
echo ====================================================
echo.
pause
endlocal
