# ADR-0001: 使用 Electron + Vue 3 封装桌面客户端

## 状态

已采纳 (2026-06-27)

## 背景

DailyBot 原为 CLI + Web 面板混合模式。Web 面板使用原生 HTML/CSS/JS 单页应用，通过 FastAPI 提供服务。用户需要更完整的桌面工具体验：系统托盘常驻、通知、一键操作、后台自动执行。

## 决策

将前端从原生 HTML 单页迁移至 **Electron + Vue 3 + electron-vite** 架构，Python FastAPI 后端保持不变作为 Electron 子进程运行。

## 方案细节

- **前端框架**: Vue 3 + TypeScript + Vite
- **桌面壳**: Electron，通过 `electron-vite` 集成
- **后端关系**: Electron 主进程启动时自动以子进程方式拉起 Python FastAPI 服务（PyInstaller 打包后的 exe），关闭时自动终止
- **UI 风格**: 深色玻璃拟态（glass morphism），参考 D:\token-monitor 的风格体系
- **进程模型**: Electron 主进程 → Python 子进程（FastAPI），前后端通过 REST API（localhost）通信
- **系统托盘**: 常驻系统托盘，关窗不退出，右键菜单可执行日报/查看状态
- **打包**: electron-builder + PyInstaller 联合打包为 Windows 安装包

## 动机

1. **用户体验**: 系统托盘 + 通知 + 一键操作，比开着浏览器更贴合日常使用习惯
2. **开发效率**: Vue 3 组件化开发比原生 HTML 单页更易维护和扩展
3. **零后端改动**: Python 代码（采集器、AI 总结、飞书推送）完全不需修改，API 层复用
4. **分发合理**: Electron 打包后用户双击即用，不需要配 Python 环境

## 替代方案

| 方案 | 优点 | 缺点 |
|------|------|------|
| 保留现有 Web 面板 | 零改动 | 需要开浏览器，无托盘/通知 |
| PyWebView 套壳 | 轻量 | 功能受限，不如 Electron 灵活 |
| 全部重写为 Node.js | 单一技术栈 | 所有 Python 代码需重写，成本极高 |
| Tauri | 包体小 | 需要 Rust 环境，生态不如 Electron 成熟 |

## 影响

- 新增 `electron/` 目录，包含 Electron 主进程代码
- `web/` 目录从原生 HTML 逐步替换为 Vue 3 组件
- `serve.py` 新增：支持仅启动 Web 服务（不执行日报）的模式
- 构建流程新增 npm 依赖和打包脚本
- 开发时需同时运行 Python 后端和 Vite 开发服务器

## 术语约定

- **桌面版 (Desktop App)**: Electron + Vue 3 封装的桌面应用程序
- **后端服务 (Backend Service)**: Python FastAPI 进程，提供 REST API
- **渲染进程 (Renderer)**: Vue 3 前端，运行在 Electron 浏览器窗口中
- **主进程 (Main Process)**: Electron 主进程，管理窗口生命周期和 Python 子进程

## 注意事项

- Python 子进程的生命周期管理（异常退出重启、端口冲突处理）
- 开发环境需 Python 和 Node.js 两套运行时
- 打包后体积约 150-200MB（Electron ~100MB + Python ~50MB）
