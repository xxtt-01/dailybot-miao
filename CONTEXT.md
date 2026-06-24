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
| **管理面板 (Dashboard)** | Web 可视化界面，提供概览、日报历史、配置查看、手动触发等功能 |
| **统计 (Statistics)** | 对日报运行数据的聚合分析，包括提交趋势、平台成功率等 |
| **调度器 (Scheduler)** | Windows 定时任务，控制日报自动执行的时间和频率 |
| **MCP** | Model Context Protocol，使 DailyBot 可作为工具接入 AI 客户端 |
| **OAuth Nudge** | Token 过期时自动向飞书发送授权引导卡片，点击即完成授权 |

