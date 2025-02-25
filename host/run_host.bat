@echo off
set PYTHONIOENCODING=utf-8
set LOG_FILE="%USERPROFILE%\host_output.log"

echo ===== Starting host script at %DATE% %TIME% ===== > %LOG_FILE%
echo Working directory: %~dp0 >> %LOG_FILE%
echo Python path: %PATH% >> %LOG_FILE%

cd /d "%~dp0"

echo Testing Python installation... >> %LOG_FILE%
"C:\Program Files\Python310\python.exe" --version >> %LOG_FILE% 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python test failed with error code %ERRORLEVEL% >> %LOG_FILE%
    exit /b %ERRORLEVEL%
)

echo Starting native messaging host... >> %LOG_FILE%
"C:\Program Files\Python310\python.exe" -u teams_chat_host.py >> %LOG_FILE% 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo Host script failed with error code %ERRORLEVEL% >> %LOG_FILE%
    exit /b %ERRORLEVEL%
) 