# Project Context

日报喵 (DailyBot) — AI 驱动的日报自动化工具，从 Git 仓库采集提交记录，经大模型总结后推送到 IM 平台。

## Glossary

| 术语 | 说明 |
|------|------|
| **代码源** | 从中采集提交记录的代码托管平台（GitLab、GitHub、Gitee） |
| **采集器 (Crawler)** | 负责从代码源抓取当日提交记录的插件化模块 |
| **AI 供应商 (Provider)** | 提供大模型总结能力的服务商（DeepSeek、豆包、Gemini 等） |
| **工作流 (Workflow)** | 将总结结果推送到目标 IM 平台的完整流程 |
| **RPA** | 自动化填报，通过 Playwright 操作浏览器完成日报表单填写 |
| **伪装 (Camouflage)** | 提交记录不足时，AI 使用历史素材智能生成补充内容的机制 |
| **管理面板 (Dashboard)** | 桌面版概览视图，提供系统状态、日报执行、环境警告等功能 |
| **统计 (Statistics)** | 对日报运行数据的聚合分析，包括提交趋势、平台成功率等 |
| **调度器 (Scheduler)** | Windows 定时任务，控制日报自动执行的时间和频率 |
| **MCP** | Model Context Protocol，使 DailyBot 可作为工具接入 AI 客户端 |
| **OAuth Nudge** | Token 过期时自动向飞书发送授权引导卡片，点击即完成授权 |
| **桌面版 (Desktop App)** | Electron + Vue 3 封装的桌面应用程序，替代原有的 Web 管理面板 |
| **后端服务 (Backend Service)** | Python FastAPI 进程，由 Electron 子进程管理，提供 REST API |
| **系统托盘 (System Tray)** | 桌面版最小化后常驻系统托盘，右键菜单可执行操作 |
| **实时日志 (Live Log)** | 桌面版执行日报时在界面内实时显示日志流 |
| **工作类型 (Work Type)** | AI 输出的工作分类枚举，如编码开发、BUG修复、性能优化等（21 种） |
| **项目标签 (Project Tag)** | AI 识别的工作归属项目，如得物数据、对账系统等（10 种） |
| **合规率 (Compliance Rate)** | 计算周期内实际生成日报天数占应生成天数的百分比 |
| **额外报告 (Extra Report)** | 用户手动补充的非代码工作记录，AI 总结时与 git 记录合并 |
| **AI 查询 (AI Query)** | 用户用自然语言向历史数据提问，AI 检索后返回结构化回答 |
| **通知中心 (Notification Center)** | 应用内汇总展示日报生成、推送结果等系统消息的面板 |

