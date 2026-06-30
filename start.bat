@echo off
chcp 65001 >nul
cd /d %~dp0

echo ================================
echo   DailyBot 小奕 - 快捷启动
echo ================================

:: 先杀死残留进程
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im electron.exe >nul 2>&1

echo [1/2] 启动后端服务...
start "DailyBot-Backend" /B python serve.py

:: 等后端就绪
timeout /t 8 /nobreak >nul

echo [2/2] 启动桌面端...
cd desktop
start "DailyBot-Desktop" /B npm run dev

cd ..
echo.
echo ✅ 启动完成！桌面窗口会自动弹出
echo    - 后端: http://127.0.0.1:8001
echo    - 前端: http://localhost:5173
echo.
echo 💡 如需关闭，运行 stop.bat
echo.
