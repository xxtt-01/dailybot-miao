# DailyBot 小奕 - PowerShell 启动脚本
# 用法: 右键 → 使用 PowerShell 运行

# 设置终端为 UTF-8
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

Write-Host "================================"
Write-Host "  DailyBot 小奕 - 快捷启动" -ForegroundColor Cyan
Write-Host "================================"

# 杀死残留进程
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process electron -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

Write-Host "[1/2] 启动后端服务..." -ForegroundColor Yellow
$python = Start-Process -FilePath "python" -ArgumentList "serve.py" -WorkingDirectory (Join-Path $PSScriptRoot ".") -NoNewWindow -PassThru

Start-Sleep -Seconds 8

Write-Host "[2/2] 启动桌面端..." -ForegroundColor Yellow
Set-Location (Join-Path $PSScriptRoot "desktop")
Start-Process -FilePath "npm" -ArgumentList "run dev" -NoNewWindow

Set-Location $PSScriptRoot
Write-Host ""
Write-Host "✅ 启动完成！桌面窗口会自动弹出" -ForegroundColor Green
Write-Host "   - 后端: http://127.0.0.1:8001" -ForegroundColor Gray
Write-Host "   - 前端: http://localhost:5173" -ForegroundColor Gray
