@echo off
title SadTalker Flask WebUI

REM Check if virtual environment exists
IF NOT EXIST venv310 (
    echo [SETUP] Creating virtual environment...
    python -m venv venv310
) ELSE (
    echo [SETUP] Virtual environment already exists
)

echo [SETUP] Activating virtual environment...
call .\venv310\Scripts\activate.bat

set PYTHON=venv310\Scripts\python.exe
echo [SETUP] Using Python: %PYTHON%

REM Skip dependency check for now - Launcher.py handles it
echo [SETUP] Starting SadTalker server...

REM Start SadTalker Flask App in background
echo.
echo ================================================
echo  SadTalker is starting up...
echo  Please wait while the server initializes...
echo ================================================
echo.
start "" /B %PYTHON% Launcher.py

REM Wait until port 7860 is LISTENING with faster polling
:WAIT
netstat -an | find ":7860" | find "LISTENING" > nul
if errorlevel 1 (
    timeout /t 1 > nul
    goto WAIT
)

REM Additional wait to ensure Flask app is fully initialized
timeout /t 2 > nul

echo.
echo [READY] Server is running on http://127.0.0.1:7860
echo.

REM Open Chrome after server is confirmed ready
echo [SETUP] Opening browser...
start chrome http://127.0.0.1:7860

pause
