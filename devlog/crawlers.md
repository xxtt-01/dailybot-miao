# crawlers 模块日志

## 2026-06-28: 采集时合并数据库 extra_reports
- **文件:**
  - `crawlers/modules/crawler_manager.py`
- **原因:** 桌面版手动补录入库后，采集流程需要自动读取并合并到 AI 输入
- **决策:** `collect_and_camouflage` 中增加 `fetch_db_extra_reports` 异步任务，查询当日 extra_reports 表，转换为 `[额外信息补充]` 格式混入采集结果
- **影响范围:** 采集流程会自动包含桌面版提交的补录记录

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

## 2026-06-26: 修复 _fetch_commits 异常传播使限流重试可达
- **文件:**
  - `crawlers/impl/github_crawler.py`
  - `crawlers/impl/gitee_crawler.py`
- **原因:** `_fetch_commits` 内部 try/except 捕获所有异常并返回 `[]`，导致 `collect_source` 中的 `isinstance(result, list)` 始终为 True，限流重试逻辑成为死代码。触发 API 限流时采集无重试直接返回空结果。
- **决策:** `_fetch_commits` 不再内部捕获异常，改为 `resp.raise_for_status()` 向上传播 HTTP 错误。`fetch_activities` 和 `_fetch_all_commits` 分别 catch 并返回 `[]`/跳过单仓库；`collect_source` catch `httpx.HTTPStatusError` 识别 403/429 并重试。
- **影响范围:** GitHub/Gitee 爬虫的 `_fetch_commits`、`fetch_activities`、`_fetch_all_commits`、`collect_source`

## 2026-06-26: 爬虫日志等级 DEBUG→WARNING + 非列表响应检测
- **文件:**
  - `crawlers/impl/github_crawler.py`
  - `crawlers/impl/gitee_crawler.py`
- **原因:** Gitee API 可能返回非列表响应（如错误消息字典），此前被 `_fetch_commits` 的 `isinstance` 检查静默转为 `[]`，调用方完全不知情。同时 `_fetch_all_commits` 中每个仓库的异常日志为 DEBUG 级别，默认日志不显示。
- **决策:** 将 `_fetch_all_commits` 中 per-repo 异常日志从 `logger.debug` 提升为 `logger.warning`；`_fetch_commits` 在 API 返回非列表时输出警告日志。
- **影响范围:** 运行日志可见性

## 2026-06-26: auto_discover 模式跳过 target_user 过滤
- **文件:**
  - `crawlers/modules/base_crawler.py`
- **原因:** Gitee 的 commit author 是 GitHub 用户名 `xxtt-01`，但 `target_user` 配置为 Gitee 用户名 `hey-hey-have-you-eaten-yet`。`crawl_entity` 第 219-225 行的 author 过滤将所有 Gitee commit 滤掉，导致 Gitee 始终 0 条。
- **决策:** auto_discover 模式下（`entity.path == "__auto_discover__"`）跳过 target_user 过滤，因为所有仓库归用户自己所有，无需按作者筛选。
- **影响范围:** Gitee/GitHub auto_discover 采集不再被 target_user 误过滤
- **踩坑:** 同一用户的 GitHub 和 Gitee 可能使用不同用户名/邮箱，固定字符串匹配不够灵活
