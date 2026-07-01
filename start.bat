@echo off
chcp 65001 >nul
cd /d %~dp0

title DailyBot 小奕 - 启动中...

echo ================================
echo   DailyBot 小奕 - 快捷启动
echo ================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [错误] 未找到 Python，请确认已安装
    echo 下载: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查 Node.js
node --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [错误] 未找到 Node.js，请确认已安装
    echo 下载: https://nodejs.org/
    pause
    exit /b 1
)

echo [1/2] 清理残留进程...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
taskkill /f /im electron.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/2] 启动后端服务...
start /B cmd /c "python serve.py" >nul 2>&1

echo   等待后端就绪...
timeout /t 8 /nobreak >nul

:: 检查后端
powershell -NoProfile -Command "& {try {$r=Invoke-WebRequest -Uri 'http://127.0.0.1:8001/health' -UseBasicParsing -TimeoutSec 3; if($r.StatusCode -eq 200){exit 0}else{exit 1}}catch{exit 1}}" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo   [OK] 后端已就绪
) else (
    echo   [!] 后端未响应，请检查 serve.py 是否有错误
)

:: 启动桌面端（另开新窗口）
cd desktop
start "DailyBot" cmd /c "npm run dev"
cd ..

echo.
echo ================================
echo   DailyBot 启动完成
echo   后端: http://127.0.0.1:8001
echo   桌面窗口将自动弹出
echo ================================
echo.
echo 此窗口可安全关闭，不影响运行
echo 如需完全停止，请运行 stop.bat
echo.
pause
