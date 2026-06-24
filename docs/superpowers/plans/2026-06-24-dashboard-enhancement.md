# DailyBot 管理面板全面增强计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development to implement this plan task-by-task.

**Goal:** 为日报喵 Web 管理面板新增 6 个功能：日报详情弹窗、趋势图表（ECharts）、伪装素材管理、采集源管理、主题切换、定时任务管理

**Architecture:** 后端新增 REST API 端点（均挂载于 `/admin/` 路径），前端在现有单页 dashboard.html 上扩展。所有 API 复用现有的 `?key=xxx` 鉴权机制。ECharts 通过 CDN 加载。

**Tech Stack:** Python/FastAPI（后端）、ECharts CDN（图表）、单页 HTML/CSS/JS（前端）

---

## API 合约（前端与后端共享）

### 1. 日报详情
```
GET /admin/reports/detail?id=123
Response: { report: { id, date, platform, summary, raw_data, is_camouflage, created_at } }
```

### 2. 统计趋势
```
GET /admin/stats/trend?days=7
Response: { days: ["2026-06-18",...], counts: [3,5,...] }

GET /admin/stats/platform
Response: { platforms: [{ name: "feishu", success: 10, failed: 2, no_data: 1 }, ...] }
```

### 3. 伪装素材管理
```
GET /admin/camouflage
Response: { items: [{ id, source_name, content_preview, platform, last_used, original_date, variants_count }, ...] }

DELETE /admin/camouflage/{item_id}
Response: { success: true }
```

### 4. 采集源管理
```
GET /admin/sources
Response: { sources: [{ platform: "github", enabled: true, repo_count: 2 }, ...] }

POST /admin/sources
  Body: { platform: "github", repo_path: "user/repo", branch: "main" }
Response: { success: true, message: "..." }

DELETE /admin/sources/{platform}/{repo_index}
Response: { success: true, message: "..." }
```

### 5. 定时任务管理
```
GET /admin/scheduler
Response: { config: { enabled, auto_start, default_time }, installed_tasks: ["DailyBot-..."], running: bool }

POST /admin/scheduler/install
  Body: { time: "18:20", weekdays: [1,2,3,4,5] }
Response: { success: true, message: "..." }

POST /admin/scheduler/uninstall
Response: { success: true, message: "..." }
```

---

## 任务分解

### Task 1: 后端 API（所有新端点 + 数据层方法）

**Files:**
- Modify: `D:/daily-bot/web/routes.py` — 新增 10 个端点
- Modify: `D:/daily-bot/common/database.py` — 新增统计查询方法
- Modify: `D:/daily-bot/crawlers/modules/camouflage_history.py` — 新增 list_all/delete_item 方法
- Modify: `D:/daily-bot/dailybot_scheduler.py` — 导出函数供 API 调用

#### Step 1: Database 新增统计方法

在 `common/database.py` 末尾（`db = Database()` 之前）添加：

```python
def get_report_trend(self, days: int = 7):
    """获取近 N 天每日报告数量趋势"""
    with self._get_conn() as conn:
        rows = conn.execute(
            "SELECT date, COUNT(*) as cnt FROM daily_reports WHERE date >= date('now', ?) GROUP BY date ORDER BY date",
            (f"-{days} days",)
        ).fetchall()
        return [dict(r) for r in rows]

def get_platform_stats(self):
    """获取各平台的成功/失败/无数据统计"""
    with self._get_conn() as conn:
        rows = conn.execute(
            "SELECT platform, status, COUNT(*) as cnt FROM run_logs GROUP BY platform, status"
        ).fetchall()
        return [dict(r) for r in rows]

def get_report_by_id(self, report_id: int):
    """根据 ID 获取单条报告详情"""
    with self._get_conn() as conn:
        row = conn.execute("SELECT * FROM daily_reports WHERE id=?", (report_id,)).fetchone()
        return dict(row) if row else None
```

#### Step 2: CamouflageHistoryManager 新增方法

在 `camouflage_history.py` 的 `CamouflageHistoryManager` 类末尾添加：

```python
def list_all_items(self) -> List[dict]:
    """展平所有日期分组，返回素材列表（按 last_used 降序）"""
    items = []
    for date_str, entries in self.history.items():
        for item_id, history in entries.items():
            items.append({
                "id": item_id,
                "source_name": history.source_name,
                "content_preview": (history.content or "")[:100],
                "platform": history.platform,
                "last_used": history.last_used,
                "original_date": history.original_date,
                "variants_count": len(history.variants),
            })
    items.sort(key=lambda x: x["last_used"] or "", reverse=True)
    return items

def delete_item(self, item_id: str) -> bool:
    """从所有日期分组中删除指定素材"""
    found = False
    for date_str in list(self.history.keys()):
        if item_id in self.history[date_str]:
            del self.history[date_str][item_id]
            if not self.history[date_str]:
                del self.history[date_str]
            found = True
    if found:
        self.save()
    return found
```

#### Step 3: 新增路由端点

在 `web/routes.py` 末尾添加以下端点（均在 `verify_admin_key` 保护下）：

```python
@router.get("/reports/detail")
async def get_report_detail(id: int = Query(...)):
    report = db.get_report_by_id(id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return {"report": report}

@router.get("/stats/trend")
async def get_stats_trend(days: int = Query(7, ge=1, le=90)):
    data = db.get_report_trend(days)
    return {"days": [d["date"] for d in data], "counts": [d["cnt"] for d in data]}

@router.get("/stats/platform")
async def get_platform_stats():
    data = db.get_platform_stats()
    platforms = {}
    for row in data:
        p = row["platform"]
        if p not in platforms:
            platforms[p] = {"name": p, "success": 0, "failed": 0, "no_data": 0}
        status = row["status"]
        if status in platforms[p]:
            platforms[p][status] = row["cnt"]
    return {"platforms": list(platforms.values())}

@router.get("/camouflage")
async def get_camouflage_list():
    from crawlers.modules.camouflage_history import camouflage_history_manager
    items = camouflage_history_manager.list_all_items()
    return {"items": items}

@router.delete("/camouflage/{item_id}")
async def delete_camouflage_item(item_id: str):
    from crawlers.modules.camouflage_history import camouflage_history_manager
    ok = camouflage_history_manager.delete_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="素材不存在")
    return {"success": True, "message": "已删除"}

@router.get("/sources")
async def get_sources():
    sources_cfg = config.get("crawler_sources", {})
    result = []
    for platform_name, cfg in sources_cfg.items():
        if isinstance(cfg, dict):
            repos = cfg.get("repos", [])
            result.append({
                "platform": platform_name,
                "enabled": cfg.get("enabled", False),
                "repo_count": len(repos),
                "repos": [{"path": r.get("path", ""), "branch": r.get("branch", "main")} for r in repos],
            })
    return {"sources": result}

@router.post("/sources")
async def add_source(data: dict):
    platform = data.get("platform", "")
    repo_path = data.get("repo_path", "")
    branch = data.get("branch", "main")
    if not platform or not repo_path:
        raise HTTPException(status_code=400, detail="platform 和 repo_path 必填")
    sources_cfg = config.get("crawler_sources", {})
    if platform not in sources_cfg:
        sources_cfg[platform] = {"enabled": True, "repos": [], "token": ""}
    sources_cfg[platform].setdefault("repos", [])
    sources_cfg[platform]["repos"].append({"path": repo_path, "branch": branch})
    # 写回 YAML
    _write_config_yaml({"crawler_sources": sources_cfg})
    config.reload()
    return {"success": True, "message": f"已添加仓库 {repo_path}"}

@router.delete("/sources/{platform}/{repo_index:int}")
async def delete_source(platform: str, repo_index: int):
    sources_cfg = config.get("crawler_sources", {})
    if platform not in sources_cfg:
        raise HTTPException(status_code=404, detail="平台不存在")
    repos = sources_cfg[platform].get("repos", [])
    if repo_index < 0 or repo_index >= len(repos):
        raise HTTPException(status_code=404, detail="仓库索引超出范围")
    removed = repos.pop(repo_index)
    _write_config_yaml({"crawler_sources": sources_cfg})
    config.reload()
    return {"success": True, "message": f"已删除仓库 {removed.get('path', '')}"}

@router.get("/scheduler")
async def get_scheduler_status():
    from dailybot_scheduler import get_registered_task_names
    sc = config.get("scheduler", {})
    tasks = get_registered_task_names()
    return {"config": {"enabled": sc.get("enabled", False), "auto_start": sc.get("auto_start", False), "default_time": sc.get("default_time", "18:20")}, "installed_tasks": tasks}

@router.post("/scheduler/install")
async def install_scheduler(data: dict = {"time": "18:20", "weekdays": [1, 2, 3, 4, 5]}):
    from dailybot_scheduler import register_schtask, get_exe_path, TASK_NAME_PREFIX
    import sys
    task_name = f"{TASK_NAME_PREFIX}Dashboard"
    time_str = data.get("time", "18:20")
    weekdays = data.get("weekdays")
    exe_path = get_exe_path()
    import logging
    dummy_log = logging.getLogger("scheduler_api")
    ok = register_schtask(task_name, time_str, exe_path, dummy_log, weekdays)
    return {"success": ok, "message": "定时任务已安装" if ok else "安装失败"}

@router.post("/scheduler/uninstall")
async def uninstall_scheduler():
    from dailybot_scheduler import remove_all_tasks
    import logging
    dummy_log = logging.getLogger("scheduler_api")
    remove_all_tasks(dummy_log)
    return {"success": True, "message": "已卸载所有定时任务"}
```

同时需要在 `web/routes.py` 中添加辅助函数 `_write_config_yaml`：

```python
def _write_config_yaml(updates: dict):
    """将配置更新写回 YAML 文件（保留已有字段）"""
    import yaml
    target_path = None
    for p in ["config.yaml", "config/config.yaml"]:
        if os.path.exists(p):
            target_path = p
            break
    if not target_path:
        return
    with open(target_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    for k, v in updates.items():
        if isinstance(v, dict) and k in raw and isinstance(raw[k], dict):
            raw[k].update(v)
        else:
            raw[k] = v
    with open(target_path, "w", encoding="utf-8") as f:
        yaml.dump(raw, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
```

#### Step 4: 运行测试验证

```bash
cd D:/daily-bot && python -m pytest tests/ -v --tb=short
```
预期：全部通过（新端点暂无测试，但旧测试不应破坏）

### Task 2: 前端仪表盘增强

**Files:**
- Modify: `D:/daily-bot/web/static/dashboard.html` — 完整重写（保留已有功能，新增 5 个功能）

#### 实现要点

**1. 日报详情弹窗**
- 日报表格每行末尾加"详情"按钮
- 点击后弹 Modal，展示该条报告的完整 summary + raw_data
- Modal 中格式化展示 JSON 内容

**2. 趋势图表（ECharts）**
- 在 HTML head 中加载 `<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js">`
- 新增 Tab："📊 数据统计"
- Tab 内容：7日/30日切换按钮 + ECharts 柱状图 + 平台成功率饼图

**3. 伪装素材管理**
- 新增 Tab："🎭 伪装素材"
- 表格展示：素材ID、来源项目、内容预览、平台、最后使用日期、操作（删除）
- 删除操作需要二次确认

**4. 采集源管理**
- 新增 Tab："📡 采集源"
- 列表展示各平台及其仓库
- 底部添加表单：选择平台 + 输入仓库路径 + 分支

**5. 定时任务管理**
- 新增 Tab："⏰ 定时任务"
- 展示当前配置（启用状态、执行时间）
- 安装/卸载按钮
- 显示当前已注册的 Windows 任务列表

**6. 主题切换**
- 右上角添加主题切换按钮（🌙/☀️）
- 定义 :root 亮色 CSS 变量
- localStorage 保存偏好

#### 注意事项
- 所有 API 调用复用现有的 `api()` 函数和 `escHtml()` 函数
- 新增 Tab 遵循现有的 `.tab-btn` + `.tab-content` 切换模式
- ECharts 图表在 Tab 切换到"数据统计"时初始化（用 `ResizeObserver` 监听），避免 hidden 元素渲染问题

---

## 执行顺序

1. **Task 1（后端 API）** → 先完成，因为 Task 2 依赖 API 合约
2. **Task 2（前端仪表盘）** → 在 Task 1 完成后启动

注意：两个 Task 可以**并行**执行，因为 API 合约已在上方定义，前端可以直接按合约调用。并行时后端需先完成路由注册，前端可先写 HTML/CSS 结构再联调。
