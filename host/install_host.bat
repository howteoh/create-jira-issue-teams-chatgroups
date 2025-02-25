@echo off
setlocal enabledelayedexpansion

echo ===== Teams Chat Creator Host Installer =====

:: 設置路徑
set "HOST_PATH=%~dp0"
set "HOST_PATH=%HOST_PATH:\=\\%"
set "LOG_FILE=%USERPROFILE%\install_host.log"

echo Installation started at %DATE% %TIME% > "%LOG_FILE%"
echo Host path: %HOST_PATH% >> "%LOG_FILE%"

:: 檢查 Python 安裝
echo Checking Python installation...
python --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH >> "%LOG_FILE%"
    echo ERROR: Python is not installed or not in PATH
    exit /b 1
)

:: 安裝必要的 Python 套件
echo Installing required Python packages...
python -m pip install --upgrade pip >> "%LOG_FILE%" 2>&1
python -m pip install requests msal >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install required packages >> "%LOG_FILE%"
    echo ERROR: Failed to install required packages
    exit /b 1
)

:: 檢查必要文件
echo Checking required files...
set "REQUIRED_FILES=teams_chat_host.py run_host.bat com.realtek.teams_chat.json"
for %%f in (%REQUIRED_FILES%) do (
    if not exist "%HOST_PATH%%%f" (
        echo ERROR: Required file %%f not found >> "%LOG_FILE%"
        echo ERROR: Required file %%f not found
        exit /b 1
    )
)

:: 設置文件權限
echo Setting file permissions...
icacls "%HOST_PATH%run_host.bat" /grant Everyone:RX >> "%LOG_FILE%" 2>&1
icacls "%HOST_PATH%teams_chat_host.py" /grant Everyone:RX >> "%LOG_FILE%" 2>&1

:: 註冊 native messaging host
echo Registering native messaging host...
reg add "HKEY_CURRENT_USER\Software\Google\Chrome\NativeMessagingHosts\com.realtek.teams_chat" /ve /t REG_SZ /d "%HOST_PATH%com.realtek.teams_chat.json" /f
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to register native messaging host >> "%LOG_FILE%"
    echo ERROR: Failed to register native messaging host
    exit /b 1
)

:: 驗證註冊表項
echo Verifying registry entry...
reg query "HKEY_CURRENT_USER\Software\Google\Chrome\NativeMessagingHosts\com.realtek.teams_chat" /ve >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Registry verification failed >> "%LOG_FILE%"
    echo ERROR: Registry verification failed
    exit /b 1
)

:: 測試 Python 腳本
echo Testing Python script...
python "%HOST_PATH%teams_chat_host.py" --test >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python script test failed >> "%LOG_FILE%"
    echo ERROR: Python script test failed
    exit /b 1
)

echo Installation completed successfully!
echo See %LOG_FILE% for details.
pause 