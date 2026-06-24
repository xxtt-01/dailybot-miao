# crawlers 模块日志

## 2026-06-24: 新增伪装素材列表与删除方法
- **文件:**
  - `crawlers/modules/camouflage_history.py`
- **原因:** 后端 API 增强需要 CamouflageHistoryManager 提供列表查询和删除功能
- **决策:**
  - `list_all_items()` — 遍历所有历史分组返回平铺素材列表，按最后使用时间倒序
  - `delete_item(item_id)` — 从所有日期分组中删除指定素材并保存
- **影响范围:** CamouflageHistoryManager 新增 2 个方法
## 2026-06-24: 修复采集任务异常处理漏洞
- **文件:**
  - `crawlers/modules/crawler_manager.py`
- **原因:** `asyncio.gather(return_exceptions=True)` 的结果未做 Exception 类型检查，采集任务失败时会尝试对 Exception 对象调用 `.items()` 导致 AttributeError
- **决策:** 在 `activities_map` 和 `extra_result` 使用前添加 `isinstance` 检查，异常时跳过该平台
- **影响范围:** 多平台采集场景下，单个平台失败不再阻塞其他平台
