@echo off
:: Register app as Windows Service (auto-start on boot)
:: Must run as Administrator!
setlocal enabledelayedexpansion

echo.
echo ====================================================
echo   Install as Windows Service  (Run As Admin!)
echo ====================================================
echo.

set ROOT=%~dp0
set VSTREAMLIT=%ROOT%.venv\Scripts\streamlit.exe
set SERVICE_NAME=MoldManagement
set NSSM=%ROOT%nssm.exe

:: ---- Check deploy done first --------------------------------
if not exist "%VSTREAMLIT%" (
    echo [ERROR] .venv not found. Run deploy_windows.bat first.
    pause
    exit /b 1
)

:: ---- Check Administrator rights ----------------------------
net session >nul
if errorlevel 1 (
    echo [ERROR] Run this script as Administrator.
    echo Right-click install_service.bat ^> Run as administrator
    pause
    exit /b 1
)

:: ---- Download NSSM if missing ------------------------------
if not exist "%NSSM%" (
    echo [Step 1] Downloading NSSM...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile '%ROOT%nssm.zip'"
    if errorlevel 1 (
        echo [ERROR] Download failed. Get nssm.exe from https://nssm.cc/download
        echo Place nssm.exe in: %ROOT%
        pause
        exit /b 1
    )
    powershell -NoProfile -Command "Expand-Archive -Path '%ROOT%nssm.zip' -DestinationPath '%ROOT%nssm_tmp' -Force"
    copy "%ROOT%nssm_tmp\nssm-2.24\win64\nssm.exe" "%NSSM%" >nul
    rd /s /q "%ROOT%nssm_tmp" >nul
    del "%ROOT%nssm.zip" >nul
    echo [OK] NSSM ready.
) else (
    echo [Step 1] NSSM found.
)
echo.

:: ---- Remove old service if exists --------------------------
"%NSSM%" stop %SERVICE_NAME% >nul
"%NSSM%" remove %SERVICE_NAME% confirm >nul

:: ---- Create logs directory ---------------------------------
if not exist "%ROOT%logs" mkdir "%ROOT%logs"

:: ---- Register service --------------------------------------
echo [Step 2] Registering service...
"%NSSM%" install %SERVICE_NAME% "%VSTREAMLIT%"
"%NSSM%" set %SERVICE_NAME% AppParameters "run app\main.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"
"%NSSM%" set %SERVICE_NAME% AppDirectory "%ROOT%"
"%NSSM%" set %SERVICE_NAME% DisplayName "Mold Management System"
"%NSSM%" set %SERVICE_NAME% Start SERVICE_AUTO_START
"%NSSM%" set %SERVICE_NAME% AppStdout "%ROOT%logs\stdout.log"
"%NSSM%" set %SERVICE_NAME% AppStderr "%ROOT%logs\stderr.log"
"%NSSM%" set %SERVICE_NAME% AppRotateFiles 1
"%NSSM%" set %SERVICE_NAME% AppRotateBytes 5242880
"%NSSM%" set %SERVICE_NAME% AppRestartDelay 3000
echo [OK] Service registered.
echo.

:: ---- Start service -----------------------------------------
echo [Step 3] Starting service...
"%NSSM%" start %SERVICE_NAME%
if errorlevel 1 (
    echo [WARN] Registered but failed to start. Check %ROOT%logs\
) else (
    echo [OK] Service started.
)

echo.
echo ====================================================
echo   Service installed!
echo.
echo   URL    : http://localhost:8501
echo   Manage : services.msc  > "Mold Management System"
echo   Logs   : %ROOT%logs\
echo ====================================================
echo.
pause
endlocal
