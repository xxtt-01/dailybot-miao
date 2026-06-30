@echo off
chcp 65001 >nul
echo 正在关闭 DailyBot...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
taskkill /f /im electron.exe >nul 2>&1
echo ✅ 已关闭
