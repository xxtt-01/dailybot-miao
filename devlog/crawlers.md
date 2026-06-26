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

## 2026-06-26: 修复 GitHub/Gitee 爬虫 API 调用链路
- **文件:**
  - `crawlers/impl/github_crawler.py`
  - `crawlers/impl/gitee_crawler.py`
- **原因:** GitHub/Gitee 爬虫使用 `self.github_api(...)` 直接调用 `use_request` 返回的 `DotDict`，但 `DotDict` 未实现 `__call__`，每次调用都静默抛出 `TypeError` 并在 DEBUG 级别被吞掉，导致采集始终返回 0 条
- **决策:** 移除 `use_request`/`apis` 依赖，改为直接使用 `httpx.AsyncClient(verify=False)` 调用 commits API，与 `_fetch_all_repos` 保持一致
- **影响范围:** GitHub/Gitee 爬虫的 `fetch_activities`、`_fetch_all_commits`、`collect_source` 三个方法
- **踩坑:** `DotDict` 没有 `__call__` 方法，但 `api_method` 也只接受 `payload=None` 单参数，即使加上 `__call__` 也无法兼容关键字参数调用。`use_request` 体系与 `api_register` 的 `api_method` 设计不匹配，爬虫不该走这条链路
