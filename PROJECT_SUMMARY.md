# ✨ 小奕 DailyBot — 项目能力地图

> AI 驱动的日报自动化工具 | v1.1.2 | 2026-06-27

---

## 一、一句话

从 Git 仓库采集提交记录 → 不足时自动补历史素材伪装 → 大模型总结润色 → 推送飞书卡片 → 桌面工具常驻系统托盘

---

## 二、架构全景

```
┌──────────────────────────────────────────────────────────────┐
│                     用户交互层                                 │
│  ┌─────────────────────┐  ┌──────────────────────────────┐   │
│  │ CLI (python run.py)  │  │ 桌面版 (Electron + Vue 3)    │   │
│  │                     │  │  ├─ 系统托盘常驻              │   │
│  │  python run.py       │  │  ├─ 无边框玻璃窗口           │   │
│  │  python run.py       │  │  ├─ 8 个功能视图             │   │
│  │   --scheduler/#47;--status  │  └─ 主题色切换(5套)       │   │
│  └─────────────────────┘  └──────────┬───────────────────┘   │
└──────────────────────────────────────┼────────────────────────┘
                                       │ REST API (localhost:8001)
                          ┌────────────▼──────────────────┐
                          │     Python FastAPI 后端        │
                          │  (serve.py / main.py)          │
                          └────┬────────────┬──────────────┘
                               │            │
                    ┌──────────▼──┐  ┌──────▼──────────┐
                    │ 数据采集层   │  │  AI 总结层       │
                    │ crawlers/   │  │  providers/      │
                    └──────────┬──┘  └──────┬──────────┘
                               │            │
                    ┌──────────▼────────────▼──────────┐
                    │        工作流 + 推送              │
                    │  workflows/feishu_workflow.py    │
                    │  └─ 飞书消息卡片                  │
                    └──────────────────────────────────┘
```

---

## 三、核心流程

```
每天 18:20（定时任务自动触发）
  │
  ├─ ① 数据采集
  │   ├─ GitHub: 自动发现仓库 → 遍历 commits API
  │   ├─ Gitee:  自动发现仓库 → 遍历 commits API
  │   └─ extra_report.md: 用户手动补充的工作记录
  │
  ├─ ② 伪装补全
  │   └─ 如果当天提交数 ≤ 4 条 → 从 14 天历史中抽取素材
  │      → 经 AI 伪装提示词将"新增"改写为"优化/重构"
  │
  ├─ ③ AI 总结（OpenAI 兼容接口）
  │   ├─ 角色"小奕"——电商系统开发工程师
  │   ├─ system prompt: 10:00-19:00 工时平摊算法
  │   ├─ camouflage prompt: 性质反转（新增→优化）
  │   └─ 输出结构化 JSON：日期/内容/成果/工时/类型/项目
  │
  ├─ ④ 飞书推送
  │   ├─ 占位卡片 → AI 总结中
  │   └─ 更新卡片 → 最终日报（交互式消息）
  │
  └─ ⑤ 持久化
      ├─ SQLite: daily_reports / run_logs / camouflage_history
      └─ 运行日志 → logs/dailybot_*.log
```

---

## 四、技术栈

### 后端（Python 3.9+）

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI + uvicorn |
| HTTP 客户端 | httpx |
| AI 接口 | OpenAI 兼容 API |
| 数据库 | SQLite（内置） |
| 任务调度 | Windows schtasks |
| 配置 | YAML + .env 环境覆盖 |
| 日志 | loguru |
| 打包 | PyInstaller |

### 桌面版（Node.js 22+）

| 组件 | 技术 |
|------|------|
| 桌面框架 | Electron 28 |
| 前端框架 | Vue 3.4 + TypeScript |
| 构建工具 | Vite + electron-vite |
| 图表 | ECharts 5 |
| UI 风格 | 深色玻璃拟态（5 套主题色） |
| 进程通信 | contextBridge + REST API |
| 打包 | electron-builder + NSIS |

---

## 五、目录结构

```
D:\daily-bot\
├── run.py                    # CLI 入口
├── serve.py                  # Web 服务模式（桌面版子进程）
├── main.py                   # 异步主流程编排
├── dailybot_scheduler.py     # Windows 定时调度器
│
├── config/
│   └── config.yaml           # 主配置（模型/采集源/工作流/调度）
├── .env                      # 密钥环境变量
│
├── core/
│   └── engine.py             # 核心报告引擎（采集→AI→推送）
│
├── crawlers/                 # 采集层
│   ├── impl/
│   │   ├── github_crawler.py # GitHub commits 采集
│   │   ├── gitee_crawler.py  # Gitee commits 采集
│   │   └── gitlab_crawler.py # GitLab（已禁用/可启用）
│   └── modules/
│       ├── base_crawler.py   # 爬虫基类（模板方法）
│       ├── crawler_manager.py# 采集总控 + 伪装触发
│       └── camouflage_history.py # 伪装素材去重/冷却
│
├── providers/                # AI 供应商层
│   ├── impl/                 # 各模型适配（openai/doubao/glm 等）
│   └── modules/
│       └── ai_factory.py     # AI 工厂 + 提示词组装
│
├── prompts/                  # 提示词
│   ├── global/system.md      # 角色"小奕"主提示词
│   ├── global/camouflage.md  # 伪装专用提示词
│   ├── doubao/               # 豆包模型专用版本
│   └── __init__.py           # 自动加载 prompts/*.md
│
├── workflows/
│   └── impl/feishu_workflow.py # 飞书卡片推送
│
├── web/                      # Web 管理面板 API
│   ├── routes.py             # 15+ REST API 端点
│   └── static/dashboard.html # 玻璃拟态管理面板（原生版）
│
├── oauth/                    # OAuth 授权 / 飞书 token
│
├── common/
│   ├── config.py             # 配置加载（YAML + env 合并）
│   └── database.py           # SQLite 数据库
│
├── desktop/                  # [新增] Electron + Vue 3 桌面版
│   ├── electron/
│   │   ├── main/index.ts     # 主进程（窗口/子进程/托盘）
│   │   └── preload/index.ts  # 预加载脚本（安全桥接）
│   ├── src/
│   │   ├── App.vue           # 主布局（侧边栏 + 内容区）
│   │   ├── api/client.ts     # API 客户端
│   │   ├── styles/main.css   # 全局样式（玻璃拟态）
│   │   ├── components/
│   │   │   ├── TitleBar.vue  # 自定义标题栏
│   │   │   ├── Toast.vue     # 全局通知
│   │   │   └── ThemeSwitcher.vue # 主题色切换
│   │   └── views/
│   │       ├── Dashboard.vue    # 概览仪表盘
│   │       ├── Reports.vue      # 日报历史
│   │       ├── Logs.vue         # 运行日志
│   │       ├── Config.vue       # 配置编辑
│   │       ├── Stats.vue        # 数据统计（ECharts）
│   │       ├── Camouflage.vue   # 伪装素材管理
│   │       ├── Sources.vue      # 采集源管理
│   │       └── Scheduler.vue    # 定时任务
│   ├── package.json          # Node.js 依赖
│   └── vite.config.ts        # Vite + electron-vite 配置
│
├── docs/
│   ├── adr/0001-electron-vue-desktop.md  # 架构决策记录
│   └── superpowers/plans/               # 实施计划
│
├── dailybot.db               # SQLite 数据库
└── pyproject.toml             # Python 项目元数据
```

---

## 六、API 接口清单（16 个）

| # | 端点 | 方法 | 用途 | 桌面版用 |
|---|------|------|------|---------|
| 1 | `/admin/status` | GET | 系统状态 | ✅ |
| 2 | `/admin/config` | GET | 查看配置（脱敏） | ✅ |
| 3 | `/admin/config` | POST | 编辑配置保存 | ✅ |
| 4 | `/admin/reports` | GET | 日报列表 | ✅ |
| 5 | `/admin/reports/detail` | GET | 日报详情 | ✅ |
| 6 | `/admin/logs` | GET | 运行日志 | ✅ |
| 7 | `/admin/trigger` | POST | 手动触发日报 | ✅ |
| 8 | `/admin/stats/trend` | GET | 日报趋势数据 | ✅ |
| 9 | `/admin/stats/platform` | GET | 平台运行统计 | ✅ |
| 10 | `/admin/camouflage` | GET | 伪装素材列表 | ✅ |
| 11 | `/admin/camouflage/{id}` | DELETE | 删除素材 | ✅ |
| 12 | `/admin/sources` | GET | 采集源列表 | ✅ |
| 13 | `/admin/sources` | POST | 添加采集源 | ✅ |
| 14 | `/admin/sources/{p}/{i}` | DELETE | 删除采集源 | ✅ |
| 15 | `/admin/scheduler` | GET | 定时任务状态 | ✅ |
| 16 | `/admin/scheduler/install` | POST | 安装定时任务 | ✅ |
| 17 | `/admin/scheduler/uninstall` | POST | 卸载定时任务 | ✅ |
| 18 | `/admin/live-logs` | GET | SSE 实时日志流 | ✅ |
| 19 | `/admin/desktop-version` | GET | 版本更新检查 | ✅ |
| 20 | `/admin/exit` | POST | 关闭后端服务 | ✅ |
| 21 | `/health` | GET | 健康检查 | ✅ |
| 22 | `/` | GET | 管理面板 HTML | |

---

## 七、运行方式

### 自动定时执行

```bash
python run.py --scheduler   # 注册 Windows 定时任务（默认 18:20）
python run.py --status      # 查看任务状态
```

### 手动执行一次

```bash
python run.py               # 完整采集→AI→推送流程
```

### 桌面版（开发模式）

```bash
# 终端 1: 启动 Python 后端
python serve.py

# 终端 2: 启动 Electron 开发模式（热更新）
cd desktop && npm run dev
```

### 桌面版（打包）

```bash
cd desktop
npm run build   # 输出 release/ 目录
```

---

## 八、桌面版特性

| 特性 | 说明 |
|------|------|
| 系统托盘 | 常驻右下角，右键菜单：打开/执行日报/退出 |
| 无边框窗口 | acrylic 毛玻璃背景，圆角 |
| 自定义标题栏 | 拖拽区域 + SVG 控制按钮（最小化/最大化/关闭） |
| 玻璃拟态 UI | backdrop-filter 毛玻璃 + 环境光晕浮动球体 |
| 主题色切换 | 5 套配色（薄荷/海洋/薰衣草/落日/玫瑰） |
| 页面过渡 | Vue Transition 淡入 + 上移动画 |
| Toast 通知 | 全局玻璃风格通知，替代 alert |
| 骨架屏 | shimmer 动画加载占位 |
| 实时日志 | 日志列表 TransitionGroup 渐入动画 |
| 开机自启 | Electron 原生 API，IPC 暴露给前端开关 |
| 版本更新 | 启动时检查 GitHub release |
| 后端管理 | Electron 自动拉起 Python 子进程 + 健康检查 |

---

## 九、数据流

```
GitHub API ──┐
Gitee API  ──┤
             ├──→ CrawlerManager.collect_and_camouflage()
GitLab API ──┤                │
(disabled)    │                ▼
             │         原始提交文本
extra_report.md ──→    + 伪装素材
             │         + 额外报告
             ▼                │
         AIFactory.summarize()│
         (deepseek-v4-flash)  │
             │                ▼
             ▼         JSON 日报数组
        飞书消息卡片    [{date, content, result,
        交互式更新      start_time, end_time,
                      priority, type, project}]
             │
             ▼
      SQLite 持久化
      (daily_reports + run_logs)
```

---

## 十、关键设计决策

| 决策 | 方案 | 原因 |
|------|------|------|
| 桌面架构 | Electron 子进程调用 Python | 零改动后端代码 |
| 通信方式 | REST API (localhost) | 简单可靠，调试方便 |
| 安全模型 | 信任本机用户 | 桌面工具无需复杂鉴权 |
| 前端框架 | Vue 3 + TypeScript | 上手简单，中文文档好 |
| UI 风格 | 深色玻璃拟态 | 用户偏好，适合长时间使用 |
| 数据存储 | SQLite | 单机够用，零运维 |
| 定时调度 | Windows schtasks | 系统原生，无需额外服务 |
| AI 伪装 | 历史素材 + 性质反转 | 无新功能时维持日报完整 |
