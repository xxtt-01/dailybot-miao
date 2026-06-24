# scripts 模块日志

## 2026-06-24 15:00: 更新 PyInstaller 打包配置
- **文件:**
  - `scripts/DailyBot.spec`
- **原因:** 新增 `core`、`web` 模块及 `common.database`、`common.validator` 隐藏导入
- **决策:** added_files 添加 `core` 和 `web`，hidden_imports 添加 `core.engine`、`common.database`、`common.validator`；移除已废弃的 `playwright._impl._driver`
