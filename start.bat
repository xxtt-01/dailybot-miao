@echo off
chcp 65001 >nul
cd /d %~dp0

title DailyBot

echo ================================
echo   DailyBot - 快速启动
echo ================================
echo.

python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [错误] 未找到 Python
    pause
    exit /b 1
)

echo [1] 启动后端...
start /B cmd /c "python serve.py" >nul 2>&1
timeout /t 8 /nobreak >nul

echo [2] 启动桌面...
cd desktop
start "DailyBot" cmd /c "npm run dev"
cd ..

echo.
echo 启动完成! 关闭此窗口不影响运行
echo.
pause
