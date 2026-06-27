# DailyBot 桌面版 Phase 2 增强计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为桌面版新增 6 大功能：手动补录、通知中心、合规率看板、提交类型分类、HTML 周报月报导出、AI 对话查询

**Architecture:** 3 阶段递进：Phase A（数据库 + API 基础设施）→ Phase B（数据统计与可视化）→ Phase C（AI 交互层）。每阶段产出独立可测试。

**Tech Stack:** Python FastAPI + SQLite + Vue 3 + TypeScript + ECharts 5

**设计决策（已与用户确认）：**
- 手动补录：新建 `extra_reports` 表，API CRUD，crawler_manager 查询合并
- 通知中心：新建 `notifications` 表，engine.py 插入通知，前端面板 + 原生通知
- 合规率：基于 daily_reports 计算，新端点
- 类型分类：解析 summary JSON 中的 type/project 字段，新端点
- HTML 导出：纯前端，复用聚合 API + ECharts 交互式报告
- AI 查询：RAG 模式，后端检索 + LLM 总结

---

## 文件变更总览

### 后端 Python
| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `common/database.py` | 修改 | 新增 extra_reports 表 + 通知表 + 对应方法 |
| `web/routes.py` | 修改 | 新增 10+ API 端点 |
| `crawlers/modules/crawler_manager.py` | 修改 | collect_and_camouflage 中查询 extra_reports |
| `core/engine.py` | 修改 | 运行成功/失败时插入通知记录 |
| `providers/modules/ai_factory.py` | 修改 | 新增通用 chat 方法（AI 查询用） |

### 前端 TypeScript/Vue
| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `desktop/src/api/client.ts` | 修改 | 新增 API 方法 |
| `desktop/src/App.vue` | 修改 | 导航增加通知红点 + 通知面板入口 |
| `desktop/src/components/NotificationPanel.vue` | 新建 | 通知中心面板 |
| `desktop/src/components/AiAssistant.vue` | 新建 | AI 对话浮动面板 |
| `desktop/src/views/Dashboard.vue` | 修改 | 增加合规率卡片 + 补录入口 |
| `desktop/src/views/Reports.vue` | 修改 | 增加类型筛选 |
| `desktop/src/views/Stats.vue` | 修改 | 增加合规趋势图 + 类型分布图 + 项目分布图 + 导出按钮 |
| `desktop/src/components/ExtraReportForm.vue` | 新建 | 手动补录弹窗 |
| `desktop/src/components/ReportViewer.vue` | 新建 | HTML 周报月报展示页 |

---

### Phase A: 基础设施（数据库 + API）

#### Task A-1: 数据库新增 extra_reports 和 notifications 表

**Files:**
- Modify: `common/database.py`

**迁移策略：** 在 `_init_tables()` 中用 `CREATE TABLE IF NOT EXISTS` 幂等创建，无破坏性。

```python
# 在 _init_tables() 的 executescript 中追加
CREATE TABLE IF NOT EXISTS extra_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    content TEXT NOT NULL,
    project TEXT DEFAULT '',
    work_type TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_extra_date ON extra_reports(date);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT DEFAULT '',
    type TEXT NOT NULL,
    related_id INTEGER DEFAULT 0,
    read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_notif_read ON notifications(read);
CREATE INDEX IF NOT EXISTS idx_notif_time ON notifications(created_at);
```

新增 Database 方法：

```python
# ── extra_reports ──
def get_extra_reports(self, date: str) -> list[dict]:
    with self._get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM extra_reports WHERE date=? ORDER BY created_at", (date,)
        ).fetchall()
        return [dict(r) for r in rows]

def add_extra_report(self, date: str, content: str, project: str = "", work_type: str = "") -> int:
    with self._get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO extra_reports (date, content, project, work_type) VALUES (?, ?, ?, ?)",
            (date, content, project, work_type),
        )
        return cur.lastrowid

def update_extra_report(self, id: int, content: str, project: str = "", work_type: str = "") -> bool:
    with self._get_conn() as conn:
        cur = conn.execute(
            "UPDATE extra_reports SET content=?, project=?, work_type=?, updated_at=datetime('now') WHERE id=?",
            (content, project, work_type, id),
        )
        return cur.rowcount > 0

def delete_extra_report(self, id: int) -> bool:
    with self._get_conn() as conn:
        cur = conn.execute("DELETE FROM extra_reports WHERE id=?", (id,))
        return cur.rowcount > 0

# ── notifications ──
def add_notification(self, title: str, body: str, type: str, related_id: int = 0) -> int:
    with self._get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO notifications (title, body, type, related_id) VALUES (?, ?, ?, ?)",
            (title, body, type, related_id),
        )
        return cur.lastrowid

def get_notifications(self, limit: int = 50, unread_only: bool = False) -> list[dict]:
    with self._get_conn() as conn:
        sql = "SELECT * FROM notifications"
        params: list = []
        if unread_only:
            sql += " WHERE read=0"
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

def mark_notification_read(self, id: int) -> bool:
    with self._get_conn() as conn:
        cur = conn.execute("UPDATE notifications SET read=1 WHERE id=?", (id,))
        return cur.rowcount > 0

def mark_all_notifications_read(self) -> int:
    with self._get_conn() as conn:
        cur = conn.execute("UPDATE notifications SET read=1 WHERE read=0")
        return cur.rowcount

def get_unread_notification_count(self) -> int:
    with self._get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM notifications WHERE read=0").fetchone()
        return row["cnt"] if row else 0

def cleanup_old_notifications(self, days: int = 30):
    """清理 N 天前的通知（与 cleanup_old_records 联动）"""
    with self._get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM notifications WHERE created_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        return cur.rowcount
```

同时修改 `cleanup_old_records` 追加清理通知：
```python
# 在 cleanup_old_records 末尾追加
notif_deleted = conn.execute(
    "DELETE FROM notifications WHERE created_at < datetime('now', ?)", (f"-{days} days",)
).rowcount
result["notifications_deleted"] = notif_deleted
```

- [ ] **Step 1: 修改 `common/database.py`** — 新增建表语句 + 所有方法 + cleanup 联动
- [ ] **Step 2: 运行测试验证** — `python -c "from common.database import db; print('ok')"` 确认初始化正常
- [ ] **Step 3: 新增后端测试** — `tests/test_database.py` 追加 extra_reports 和 notifications 的 CRUD 测试

---

#### Task A-2: 后端 API 端点 — extra_reports CRUD + notifications

**Files:**
- Modify: `web/routes.py`
- Test: `tests/test_web_routes.py`

在 `web/routes.py` 末尾追加（`# ── 桌面版专用 API ──` 区域后或单独区域）：

```python
# ── 手动补录 API ──────────────────────────

from pydantic import BaseModel

class ExtraReportCreate(BaseModel):
    date: str
    content: str
    project: str = ""
    work_type: str = ""

class ExtraReportUpdate(BaseModel):
    content: str
    project: str = ""
    work_type: str = ""

@router.get("/extra-reports")
async def get_extra_reports(date: str = Query(...)):
    """获取指定日期的补录列表"""
    items = db.get_extra_reports(date)
    return {"items": items, "count": len(items)}

@router.post("/extra-reports")
async def create_extra_report(data: ExtraReportCreate):
    """添加补录"""
    id = db.add_extra_report(data.date, data.content, data.project, data.work_type)
    return {"success": True, "id": id}

@router.put("/extra-reports/{report_id}")
async def update_extra_report(report_id: int, data: ExtraReportUpdate):
    """编辑补录"""
    ok = db.update_extra_report(report_id, data.content, data.project, data.work_type)
    if not ok:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True}

@router.delete("/extra-reports/{report_id}")
async def delete_extra_report(report_id: int):
    """删除补录"""
    ok = db.delete_extra_report(report_id)
    if not ok:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True}


# ── 通知中心 API ──────────────────────────

@router.get("/notifications")
async def get_notifications(limit: int = Query(50, ge=1, le=200), unread_only: bool = Query(False)):
    items = db.get_notifications(limit, unread_only)
    unread_count = db.get_unread_notification_count()
    return {"items": items, "count": len(items), "unread_count": unread_count}

@router.post("/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: int):
    ok = db.mark_notification_read(notif_id)
    if not ok:
        raise HTTPException(status_code=404, detail="通知不存在")
    return {"success": True}

@router.post("/notifications/read-all")
async def mark_all_read():
    count = db.mark_all_notifications_read()
    return {"success": True, "marked": count}
```

- [ ] **Step 1: 添加 Pydantic 模型 + 路由到 `web/routes.py`**
- [ ] **Step 2: 在 `tests/test_web_routes.py` 增加 API 测试**
- [ ] **Step 3: 手动验证** — 启动 serve.py 后用 curl 测试

---

#### Task A-3: engine.py 插入通知 + crawler_manager 合并 extra_reports

**Files:**
- Modify: `core/engine.py` — 运行成功/失败时插入通知
- Modify: `crawlers/modules/crawler_manager.py` — 采集时合并 extra_reports

**engine.py 改动：**

在 `finalize_workflow_async` 中，推送成功后插入通知：
```python
# 在 log.info(f"✅ [推送] 平台 {wf.WORKFLOW_NAME} 通知已发送") 之后追加
try:
    db.add_notification(
        title="日报推送成功",
        body=f"{wf.WORKFLOW_NAME} 平台日报已推送完成" if pushed else f"{wf.WORKFLOW_NAME} 平台日报已保存为草稿",
        type="push_success" if pushed else "draft_saved",
    )
except Exception:
    pass
```

在 `except` 块中（推送失败时）：
```python
# 在 await wf.on_report_failure(str(e), ctx) 之后追加
try:
    db.add_notification(
        title="日报推送失败",
        body=f"{wf.WORKFLOW_NAME} 平台: {str(e)[:100]}",
        type="push_failed",
    )
except Exception:
    pass
```

在 `run_reporting_logic` 开头 `log.info("🎬 开始执行报告生成流程...")` 后追加：
```python
try:
    db.add_notification(title="日报开始执行", body="日报生成流程已启动", type="report_started")
except Exception:
    pass
```

**crawler_manager.py 改动：**

在 `collect_and_camouflage` 中，每个平台处理 `extra_result` 的地方，追加数据库查询：

找到 `if extra_result:` 判断之前的代码，在 `extra_result = None` 之后处理，增加从数据库读取 extra_reports 的逻辑。实际上更好的方式是在 `fetch_extra_report` 中进行，或者直接在 crawler_manager 中处理。

更简单的方案：在 crawler_manager.py 的 `collect_and_camouflage` 中，在 `extra_tasks` 之后追加一个从数据库读取 extra_reports 的异步任务：

```python
# 在 extra_tasks 列表构建之后、all_results 之前追加
async def fetch_db_extra_reports():
    """从数据库查询当日的 extra_reports 并合并到 extra_result 格式"""
    try:
        from common.database import db
        today = datetime.now().strftime("%Y-%m-%d")
        items = db.get_extra_reports(today)
        if not items:
            return {}
        # 转换为与 fetch_extra_report 相同的格式
        contents = []
        for item in items:
            project_tag = f"[{item['project']}] " if item.get('project') else ""
            type_tag = f"({item['work_type']}) " if item.get('work_type') else ""
            contents.append(f"{project_tag}{type_tag}{item['content']}")
        return {"extra_report": {today: contents}}
    except Exception as e:
        logger.debug(f"[额外报告] 数据库查询失败（非关键）: {e}")
        return {}

extra_tasks.append(fetch_db_extra_reports())
```

需要添加 import：`from datetime import datetime`

- [ ] **Step 1: 修改 `core/engine.py`** — 3 处插入通知
- [ ] **Step 2: 修改 `crawlers/modules/crawler_manager.py`** — 查询 extra_reports 表
- [ ] **Step 3: 运行采集测试确认流程正常**

---

#### Task A-4: 前端 API 客户端扩展

**Files:**
- Modify: `desktop/src/api/client.ts`

追加新接口定义：

```typescript
export interface ExtraReport {
  id: number
  date: string
  content: string
  project: string
  work_type: string
  created_at: string
  updated_at: string
}

export interface Notification {
  id: number
  title: string
  body: string
  type: string
  related_id: number
  read: number
  created_at: string
}

// 在 api 对象中追加（在最后一个方法 , 前加）
getExtraReports: (date: string) =>
  request<{ items: ExtraReport[]; count: number }>(`/admin/extra-reports?date=${date}`),
addExtraReport: (data: { date: string; content: string; project?: string; work_type?: string }) =>
  request<{ success: boolean; id: number }>('/admin/extra-reports', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }),
updateExtraReport: (id: number, data: { content: string; project?: string; work_type?: string }) =>
  request<{ success: boolean }>(`/admin/extra-reports/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }),
deleteExtraReport: (id: number) =>
  request<{ success: boolean }>(`/admin/extra-reports/${id}`, { method: 'DELETE' }),

getNotifications: (limit = 50, unreadOnly = false) =>
  request<{ items: Notification[]; count: number; unread_count: number }>(
    `/admin/notifications?limit=${limit}&unread_only=${unreadOnly}`
  ),
markNotificationRead: (id: number) =>
  request<{ success: boolean }>(`/admin/notifications/${id}/read`, { method: 'POST' }),
markAllNotificationsRead: () =>
  request<{ success: boolean; marked: number }>('/admin/notifications/read-all', { method: 'POST' }),
```

- [ ] **Step 1: 在 `desktop/src/api/client.ts` 追加接口和类型**
- [ ] **Step 2: 确认 TypeScript 编译通过** — `cd desktop && npx tsc --noEmit`

---

#### Task A-5: 前端补录表单组件 ExtraReportForm.vue

**Files:**
- Create: `desktop/src/components/ExtraReportForm.vue`

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { api, type ExtraReport } from '../api/client'

const props = defineProps<{
  date: string
  onClose: () => void
  onSaved: () => void
  showToast?: (msg: string, type: 'success' | 'error' | 'info') => void
}>()

const content = ref('')
const project = ref('')
const workType = ref('')
const saving = ref(false)

const workTypeOptions = [
  '编码开发', '接口对接', '数据抓取/采集', '数据清洗/ETL',
  'BUG修复', '问题排查', '性能优化', '代码审查/重构',
  '测试验证', '需求分析', '系统设计', '技术调研/预研',
  '系统发布/部署', '系统维护', '自动化脚本', '文档编写',
  '会议沟通', '其它工作',
]

async function save() {
  if (!content.value.trim()) {
    props.showToast?.('请输入工作内容', 'error')
    return
  }
  saving.value = true
  try {
    await api.addExtraReport({
      date: props.date,
      content: content.value.trim(),
      project: project.value,
      work_type: workType.value,
    })
    props.showToast?.('已添加', 'success')
    props.onSaved()
    props.onClose()
  } catch (e: any) {
    props.showToast?.('保存失败: ' + (e.message || '未知错误'), 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="props.onClose">
      <div class="modal-content glass-card" style="width:520px;max-width:90vw">
        <div class="modal-header">
          <h3>补录今日工作</h3>
          <button class="btn btn-ghost" @click="props.onClose">✕</button>
        </div>
        <div class="modal-body" style="display:flex;flex-direction:column;gap:var(--space-2)">
          <div class="field">
            <label class="text-dim text-sm">工作内容 *</label>
            <textarea v-model="content" class="form-textarea" placeholder="描述你今天做了什么..." spellcheck="false" />
          </div>
          <div class="field-row">
            <div class="field" style="flex:1">
              <label class="text-dim text-sm">项目</label>
              <input v-model="project" class="form-input" placeholder="如: 对账系统" />
            </div>
            <div class="field" style="flex:1">
              <label class="text-dim text-sm">工作类型</label>
              <select v-model="workType" class="form-select">
                <option value="">不指定</option>
                <option v-for="t in workTypeOptions" :key="t" :value="t">{{ t }}</option>
              </select>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-ghost" @click="props.onClose">取消</button>
          <button class="btn btn-primary" :disabled="saving" @click="save">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2); }
.modal-body { overflow-y: auto; flex: 1; }
.modal-footer { display: flex; justify-content: flex-end; gap: var(--space-2); margin-top: var(--space-2); }
.field { display: flex; flex-direction: column; gap: 4px; }
.field-row { display: flex; gap: var(--space-2); }
.form-textarea { width: 100%; min-height: 120px; font-family: var(--font-mono); font-size: 12px; padding: var(--space-2); resize: vertical; }
.form-input { padding: 6px 10px; font-size: 12px; }
.form-select { padding: 6px 10px; font-size: 12px; }
</style>
```

- [ ] **Step 1: 创建 `ExtraReportForm.vue`**
- [ ] **Step 2: 修改 `Dashboard.vue`** — 增加"补录"按钮和弹窗调用

---

#### Task A-6: 前端通知面板组件 NotificationPanel.vue

**Files:**
- Create: `desktop/src/components/NotificationPanel.vue`

```vue
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api, type Notification } from '../api/client'

const props = defineProps<{
  show?: boolean
  onClose: () => void
  showToast?: (msg: string, type: 'success' | 'error' | 'info') => void
}>()

const items = ref<Notification[]>([])
const loading = ref(false)

const typeLabels: Record<string, string> = {
  report_started: '日报开始',
  push_success: '推送成功',
  push_failed: '推送失败',
  draft_saved: '已存草稿',
}

const typeIcons: Record<string, string> = {
  report_started: '▶',
  push_success: '✓',
  push_failed: '✗',
  draft_saved: '📝',
}

async function load() {
  loading.value = true
  try {
    const res = await api.getNotifications(50)
    items.value = res.items
  } catch { /* 静默 */ }
  loading.value = false
}

async function markRead(id: number) {
  await api.markNotificationRead(id)
  items.value = items.value.map(i => i.id === id ? { ...i, read: 1 } : i)
}

async function markAllRead() {
  await api.markAllNotificationsRead()
  items.value = items.value.map(i => ({ ...i, read: 1 }))
}

onMounted(load)
</script>

<template>
  <Teleport to="body">
    <div v-if="props.show" class="notif-overlay" @click.self="props.onClose">
      <div class="notif-panel glass-card">
        <div class="notif-header">
          <h3>通知</h3>
          <div class="notif-actions">
            <button class="btn btn-ghost btn-sm" @click="markAllRead">全部已读</button>
            <button class="btn btn-ghost btn-sm" @click="props.onClose">✕</button>
          </div>
        </div>
        <div class="notif-body">
          <div v-if="loading" class="text-dim" style="text-align:center;padding:var(--space-4)">加载中...</div>
          <div v-else-if="items.length === 0" class="text-dim" style="text-align:center;padding:var(--space-4)">暂无通知</div>
          <div v-else v-for="item in items" :key="item.id"
            class="notif-item" :class="{ unread: !item.read }"
            @click="!item.read && markRead(item.id)">
            <div class="notif-icon">{{ typeIcons[item.type] || '○' }}</div>
            <div class="notif-content">
              <div class="notif-title">{{ item.title }}</div>
              <div v-if="item.body" class="notif-body-text">{{ item.body }}</div>
              <div class="notif-time text-dim text-sm">{{ item.created_at?.slice(11, 19) || '' }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.notif-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; justify-content: flex-end; z-index: 1000; }
.notif-panel { width: 380px; height: 100vh; display: flex; flex-direction: column; border-radius: 0; padding: var(--space-3); }
.notif-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2); }
.notif-actions { display: flex; gap: var(--space-1); }
.notif-body { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
.notif-item { display: flex; gap: var(--space-2); padding: var(--space-2); border-radius: var(--radius-sm); cursor: pointer; transition: var(--transition-fast); border-left: 3px solid transparent; }
.notif-item:hover { background: rgba(255,255,255,0.03); }
.notif-item.unread { border-left-color: var(--accent); background: rgba(183,234,212,0.03); }
.notif-icon { font-size: 14px; width: 20px; text-align: center; flex-shrink: 0; margin-top: 1px; }
.notif-content { flex: 1; min-width: 0; }
.notif-title { font-size: 12px; font-weight: 500; }
.notif-body-text { font-size: 11px; color: var(--text-secondary); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.notif-time { font-size: 10px; margin-top: 2px; }
.btn-sm { padding: 3px 10px; font-size: 11px; }
</style>
```

- [ ] **Step 1: 创建 `NotificationPanel.vue`**
- [ ] **Step 2: 修改 `App.vue`** — 导航栏增加通知图标 + 红点 + 面板入口

---

#### Task A-7: App.vue 集成通知中心入口

**Files:**
- Modify: `desktop/src/App.vue`

改动点：
1. 导入 NotificationPanel，添加 `showNotificationPanel` ref
2. 在侧边栏导航增加一个"通知"按钮（或者加在底部）
3. 定时轮询未读数（每 30 秒）
4. 收到日报完成事件时触发原生通知（已有，但联动通知中心）

简化方案：在 sidebar-footer 区域增加通知按钮 + 红色未读标记，点击弹出 NotificationPanel。

```vue
// 在 script setup 中加入
import NotificationPanel from './components/NotificationPanel.vue'

const showNotificationPanel = ref(false)
const unreadCount = ref(0)

async function checkUnread() {
  try {
    const res = await api.getNotifications(1, true)
    unreadCount.value = res.unread_count
  } catch { /* 静默 */ }
}

let notifTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  // ... 原有代码 ...
  notifTimer = setInterval(checkUnread, 30000)
  checkUnread()
})

onBeforeUnmount(() => {
  // ... 原有代码 ...
  if (notifTimer) clearInterval(notifTimer)
})
```

侧边栏底部增加：
```vue
<div class="footer-row">
  <button class="notif-btn" @click="showNotificationPanel = true">
    <span class="notif-bell-icon">🔔</span>
    <span v-if="unreadCount > 0" class="notif-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
  </button>
</div>
```

在模板末尾追加：
```vue
<NotificationPanel
  :show="showNotificationPanel"
  :show-toast="showToast"
  @close="showNotificationPanel = false"
/>
```

- [ ] **Step 1: 修改 `App.vue`** — 集成通知组件 + 轮询
- [ ] **Step 2: 确认侧边栏布局不变形**

---

#### Task A-Commit: Phase A 提交

```bash
git add common/database.py web/routes.py core/engine.py crawlers/modules/crawler_manager.py
git add desktop/src/api/client.ts desktop/src/components/ExtraReportForm.vue desktop/src/components/NotificationPanel.vue desktop/src/App.vue devlog/
git commit -m "[feat] Phase A: extra_reports + notifications 数据库/API/前端组件"
```

---

### Phase B: 数据统计与可视化

#### Task B-1: 后端统计 API — 合规率 + 工作类型分布

**Files:**
- Modify: `web/routes.py`

```python
# ── 统计 API ──

@router.get("/stats/compliance")
async def get_compliance(days: int = Query(30, ge=7, le=90)):
    """日报合规率：实际生成日报天数 / 应生成天数"""
    # 应生成天数 = 配置了工作流且在工作日的天数（简化：跳过周末）
    # 实际生成天数 = daily_reports 中不同日期的数量
    today = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    with db._get_conn() as conn:
        # 实际有日报的天数
        actual_rows = conn.execute(
            "SELECT DISTINCT date FROM daily_reports WHERE date BETWEEN ? AND ? ORDER BY date",
            (start, today),
        ).fetchall()
        actual_dates = set(r["date"] for r in actual_rows)
        
        # 每日明细
        daily = conn.execute(
            "SELECT date, COUNT(*) as cnt FROM daily_reports WHERE date BETWEEN ? AND ? GROUP BY date ORDER BY date",
            (start, today),
        ).fetchall()
    
    # 计算工作日（周一到周五）
    all_dates = []
    current = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(today, "%Y-%m-%d")
    while current <= end_dt:
        if current.weekday() < 5:  # 周一=0, 周五=4
            all_dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    reported_dates = [d["date"] for d in daily]
    compliance_rate = round(len(actual_dates) / len(all_dates) * 100, 1) if all_dates else 100
    
    # 每日趋势（有/无）
    trend = []
    for d in all_dates:
        cnt = next((r["cnt"] for r in daily if r["date"] == d), 0)
        trend.append({"date": d, "reported": d in actual_dates, "count": cnt})
    
    return {
        "days": days,
        "total_workdays": len(all_dates),
        "reported_days": len(actual_dates),
        "compliance_rate": compliance_rate,
        "trend": trend,
    }


@router.get("/stats/work-types")
async def get_work_types(days: int = Query(7, ge=1, le=90)):
    """解析日报中的 type 和 project 分布"""
    today = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    with db._get_conn() as conn:
        rows = conn.execute(
            "SELECT date, platform, summary, is_camouflage FROM daily_reports WHERE date BETWEEN ? AND ? ORDER BY date",
            (start, today),
        ).fetchall()
    
    type_count: dict[str, int] = {}
    project_count: dict[str, int] = {}
    daily_type_trend: dict[str, dict[str, int]] = {}
    
    for row in rows:
        summary = row["summary"]
        date_str = row["date"]
        if date_str not in daily_type_trend:
            daily_type_trend[date_str] = {}
        try:
            items = json.loads(summary)
            if isinstance(items, list):
                for item in items:
                    t = item.get("type", "其他")
                    p = item.get("project", "其他")
                    type_count[t] = type_count.get(t, 0) + 1
                    project_count[p] = project_count.get(p, 0) + 1
                    daily_type_trend[date_str][t] = daily_type_trend[date_str].get(t, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass
    
    # 按数量排序
    sorted_types = sorted(type_count.items(), key=lambda x: -x[1])
    sorted_projects = sorted(project_count.items(), key=lambda x: -x[1])
    
    return {
        "days": days,
        "type_distribution": [{"name": k, "count": v} for k, v in sorted_types],
        "project_distribution": [{"name": k, "count": v} for k, v in sorted_projects],
        "type_trend": daily_type_trend,
        "platforms": list(set(r["platform"] for r in rows)),
    }
```

需要追加 import：
```python
from datetime import datetime, timedelta
import json  # 如果顶端已有则不需要
```

- [ ] **Step 1: 在 `web/routes.py` `stats` 区域追加两个端点**
- [ ] **Step 2: 手动验证** — `curl http://127.0.0.1:8001/admin/stats/compliance` 和 `curl http://127.0.0.1:8001/admin/stats/work-types`

---

#### Task B-2: 前端 API 追加统计端点

**Files:**
- Modify: `desktop/src/api/client.ts`

```typescript
// 在 api 对象中追加
getCompliance: (days = 30) =>
  request<{
    days: number; total_workdays: number; reported_days: number
    compliance_rate: number; trend: { date: string; reported: boolean; count: number }[]
  }>(`/admin/stats/compliance?days=${days}`),

getWorkTypes: (days = 7) =>
  request<{
    days: number
    type_distribution: { name: string; count: number }[]
    project_distribution: { name: string; count: number }[]
    type_trend: Record<string, Record<string, number>>
    platforms: string[]
  }>(`/admin/stats/work-types?days=${days}`),
```

- [ ] **Step 1: 追加 API 方法**

---

#### Task B-3: Dashboard 合规率卡片 + 补录入口

**Files:**
- Modify: `desktop/src/views/Dashboard.vue`

改动点：
1. 在状态卡片区域增加"合规率"卡片
2. 在"执行日报"按钮旁增加"补录"按钮
3. 点击补录 → 弹出 ExtraReportForm

```vue
// script setup 追加
import ExtraReportForm from '../components/ExtraReportForm.vue'

const complianceRate = ref<number | null>(null)
const showExtraForm = ref(false)
const todayStr = new Date().toISOString().slice(0, 10)

async function loadCompliance() {
  try {
    const res = await api.getCompliance(30)
    complianceRate.value = res.compliance_rate
  } catch { /* 静默 */ }
}

// loadAll 中调用 loadCompliance 和 loadExtraReports
```

在模板中，状态卡片 grid 增加第 5 张卡片（或替换某个卡片）：
```vue
<div class="glass-card status-card">
  <div class="card-glow" style="background:var(--accent)"></div>
  <div class="card-label">合规率(30天)</div>
  <div class="card-value" :style="{ color: complianceRate !== null && complianceRate >= 80 ? 'var(--success)' : complianceRate !== null && complianceRate >= 50 ? 'var(--warning)' : 'var(--danger)' }">
    {{ complianceRate !== null ? complianceRate + '%' : '--' }}
  </div>
  <div class="card-sub text-dim" v-if="complianceRate !== null">
    {{ complianceRate >= 80 ? '优秀' : complianceRate >= 50 ? '一般' : '需关注' }}
  </div>
</div>
```

page-header 区域增加补录按钮：
```vue
<button class="btn btn-ghost" @click="showExtraForm = true">+ 补录</button>
```

模板末尾追加：
```vue
<ExtraReportForm
  v-if="showExtraForm"
  :date="todayStr"
  :show-toast="props.showToast"
  @close="showExtraForm = false"
  @saved="loadAll"
/>
```

- [ ] **Step 1: 修改 `Dashboard.vue`** — 合规率卡片 + 补录入口
- [ ] **Step 2: 确认布局** — 卡片 grid 在 4 列下正常

---

#### Task B-4: Reports 增加类型筛选

**Files:**
- Modify: `desktop/src/views/Reports.vue`

在筛选项区域增加类型过滤：
```vue
<label class="filter-item">
  <span class="text-dim text-sm">类型</span>
  <select v-model="typeFilter" @change="loadReports">
    <option value="">全部</option>
    <option value="编码开发">编码开发</option>
    <option value="BUG修复">BUG修复</option>
    <option value="性能优化">性能优化</option>
    <!-- 等等 -->
  </select>
</label>
```

但更好的做法是：从服务端获取类型列表（通过 work-types API 的 type_distribution），而非硬编码。简化版本可以先硬编码 5 个常用项。

或者更简洁：不要下拉框，改为在 table 的"类型"列显示每个报告的 type 标签（从 summary JSON 中解析第一条）。

更实用的方案——加点小改动：
1. Reports.vue 的 table 中"类型"列改为显示解析出的第一个工作类型
2. 点击类型标签可以筛选

```typescript
// 工具函数：从 summary JSON 提取第一个 type
function extractFirstType(summary: string): string {
  try {
    const items = JSON.parse(summary)
    if (Array.isArray(items) && items.length > 0) return items[0].type || '--'
  } catch { /* */ }
  return '--'
}
```

在 table 的`<td>`类型列：
```vue
<td><span class="tag tag-info text-sm">{{ extractFirstType(r.summary) }}</span></td>
```

- [ ] **Step 1: 修改 Reports.vue** — 类型列 + extractFirstType 函数

---

#### Task B-5: Stats 增加合规趋势图 + 类型/项目分布图表

**Files:**
- Modify: `desktop/src/views/Stats.vue`

在原有图表基础上增加：
1. 合规率趋势折线图（新卡片）
2. 工作类型分布饼图（替换/补充现有饼图）
3. 项目分布柱状图（新卡片）

```vue
// script setup 追加
import { api } from '../api/client'

const complianceData = ref<any>(null)
const workTypeData = ref<any>(null)
const complianceChartRef = ref<HTMLDivElement>()
const typeChartRef = ref<HTMLDivElement>()
const projectChartRef = ref<HTMLDivElement>()
let complianceChart: echarts.ECharts | null = null
let typeChart: echarts.ECharts | null = null
let projectChart: echarts.ECharts | null = null

async function loadComplianceStats() {
  try {
    complianceData.value = await api.getCompliance(30)
    updateComplianceChart()
  } catch { /* */ }
}

async function loadWorkTypes() {
  try {
    workTypeData.value = await api.getWorkTypes(30)
    updateTypeChart()
    updateProjectChart()
  } catch { /* */ }
}

function initComplianceChart() {
  if (!complianceChartRef.value) return
  complianceChart = echarts.init(complianceChartRef.value)
  updateComplianceChart()
}

function updateComplianceChart() {
  if (!complianceChart || !complianceData.value) return
  const data = complianceData.value
  complianceChart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(24,28,36,0.9)', borderColor: 'rgba(128,138,152,0.2)', textStyle: { color: '#eef5fb', fontSize: 12 } },
    grid: { left: 40, right: 16, top: 16, bottom: 24 },
    xAxis: { type: 'category', data: data.trend.map((d: any) => d.date.slice(5)), axisLabel: { color: '#a3adbb', fontSize: 11 }, axisLine: { lineStyle: { color: 'rgba(128,138,152,0.15)' } } },
    yAxis: { type: 'value', max: 1, axisLabel: { formatter: (v: number) => v ? '有' : '无', color: '#a3adbb', fontSize: 11 }, splitLine: { lineStyle: { color: 'rgba(128,138,152,0.08)' } } },
    series: [{
      type: 'bar', data: data.trend.map((d: any) => d.reported ? 1 : 0),
      itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#4ec77f' }, { offset: 1, color: 'rgba(78,199,127,0.2)' }]), borderRadius: [2, 2, 0, 0] },
    }],
  })
}

function updateTypeChart() {
  if (!typeChart || !workTypeData.value) return
  const data = workTypeData.value.type_distribution.slice(0, 10)
  typeChart.setOption({
    tooltip: { trigger: 'item', backgroundColor: 'rgba(24,28,36,0.9)', borderColor: 'rgba(128,138,152,0.2)', textStyle: { color: '#eef5fb', fontSize: 12 }, formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie', radius: ['30%', '60%'],
      data: data.map((d: any, i: number) => ({
        name: d.name, value: d.count,
        itemStyle: { color: ['#b7ead4','#6ab0f0','#b794f4','#f6ad55','#f687b3','#4ec77f','#f06a7b','#e8c96a','#a3adbb','#8fdfbe'][i % 10] },
      })),
      label: { color: '#a3adbb', fontSize: 11, formatter: '{b}' },
      labelLine: { lineStyle: { color: 'rgba(128,138,152,0.3)' } },
    }],
  })
}

function updateProjectChart() {
  if (!projectChart || !workTypeData.value) return
  const data = workTypeData.value.project_distribution
  projectChart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(24,28,36,0.9)', borderColor: 'rgba(128,138,152,0.2)', textStyle: { color: '#eef5fb', fontSize: 12 } },
    grid: { left: 80, right: 16, top: 16, bottom: 24 },
    xAxis: { type: 'value', axisLabel: { color: '#a3adbb', fontSize: 11 }, splitLine: { lineStyle: { color: 'rgba(128,138,152,0.08)' } } },
    yAxis: { type: 'category', data: data.map((d: any) => d.name).reverse(), axisLabel: { color: '#a3adbb', fontSize: 11 }, axisLine: { lineStyle: { color: 'rgba(128,138,152,0.15)' } } },
    series: [{
      type: 'bar', data: data.map((d: any) => d.count).reverse(),
      itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: 'rgba(106,176,240,0.2)' }, { offset: 1, color: '#6ab0f0' }]), borderRadius: [0, 4, 4, 0] },
    }],
  })
}

// 在 onMounted 中追加初始化
initComplianceChart()
initTypeChart()
initProjectChart()

// 在 onResize 中追加
complianceChart?.resize()
typeChart?.resize()
projectChart?.resize()

// 在 onBeforeUnmount 中追加 dispose
complianceChart?.dispose()
typeChart?.dispose()
projectChart?.dispose()

// 在 loadTrend 等调用时一并加载
// 修改 onMounted 的 load 部分
```

Stats 模板中追加 3 张新卡片。

- [ ] **Step 1: 修改 `Stats.vue`** — 追加 3 个图表 + 加载逻辑 + resize/dispose

---

#### Task B-6: HTML 周报/月报交互式导出

**Files:**
- Modify: `desktop/src/views/Stats.vue` — 追加导出按钮和报告生成逻辑

在 Stats.vue 的汇总统计卡片区域，增加"生成周报/月报"按钮：

```typescript
const generatingReport = ref(false)

async function generateReport(mode: 'weekly' | 'monthly') {
  generatingReport.value = true
  try {
    const now = new Date()
    const end = now.toISOString().slice(0, 10)
    let start: string
    if (mode === 'weekly') {
      const s = new Date(now); s.setDate(s.getDate() - 6)
      start = s.toISOString().slice(0, 10)
    } else {
      start = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10)
    }
    
    const [summary, compliance, workTypes] = await Promise.all([
      api.getReportSummary(start, end),
      api.getCompliance(30),
      api.getWorkTypes(30),
    ])
    
    // 在新窗口打开报告
    const win = window.open('', '_blank')
    if (!win) { throw new Error('浏览器阻止了新窗口打开') }
    
    const title = mode === 'weekly' ? `周报 ${start} ~ ${end}` : `月报 ${start.slice(0, 7)}`
    
    win.document.write(`
      <!DOCTYPE html>
      <html><head>
        <meta charset="utf-8">
        <title>${title}</title>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"><\/script>
        <style>
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body { font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #0f1219; color: #eef5fb; padding: 40px; }
          .container { max-width: 900px; margin: 0 auto; }
          h1 { font-size: 24px; margin-bottom: 4px; }
          .meta { color: #a3adbb; font-size: 13px; margin-bottom: 24px; }
          .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
          .stat-card { background: rgba(255,255,255,0.04); border: 1px solid rgba(128,138,152,0.15); border-radius: 8px; padding: 16px; text-align: center; }
          .stat-value { font-size: 28px; font-weight: 700; color: #b7ead4; }
          .stat-label { font-size: 11px; color: #a3adbb; margin-top: 4px; }
          .section { margin-bottom: 24px; }
          .section-title { font-size: 14px; font-weight: 600; color: #a3adbb; margin-bottom: 12px; letter-spacing: 0.5px; }
          .chart-box { height: 280px; margin-bottom: 24px; background: rgba(255,255,255,0.02); border-radius: 8px; padding: 8px; }
          table { width: 100%; border-collapse: collapse; font-size: 12px; }
          th { text-align: left; padding: 8px 10px; color: #a3adbb; font-weight: 500; border-bottom: 1px solid rgba(128,138,152,0.15); }
          td { padding: 6px 10px; border-bottom: 1px solid rgba(128,138,152,0.08); }
          .tag { display: inline-block; font-size: 10px; padding: 1px 6px; border-radius: 4px; background: rgba(106,176,240,0.15); color: #6ab0f0; }
          .tag-success { background: rgba(78,199,127,0.15); color: #4ec77f; }
          .tag-warning { background: rgba(240,160,106,0.15); color: #f0a06a; }
          .print-btn { position: fixed; bottom: 24px; right: 24px; padding: 10px 20px; background: #b7ead4; color: #0f1219; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; }
          @media print { .print-btn { display: none; } body { background: white; color: #333; padding: 20px; } .stat-card { background: #f5f5f5; border-color: #ddd; } }
        </style>
      </head><body>
        <div class="container">
          <h1>${title}</h1>
          <div class="meta">${summary.total} 篇日报 · ${compliance.compliance_rate}% 合规率 · ${Object.keys(summary.by_platform).length} 个平台</div>
          
          <div class="stats-row">
            <div class="stat-card"><div class="stat-value">${summary.total}</div><div class="stat-label">总日报数</div></div>
            <div class="stat-card"><div class="stat-value">${summary.by_type.normal}</div><div class="stat-label">正常</div></div>
            <div class="stat-card"><div class="stat-value">${summary.by_type.camouflage}</div><div class="stat-label">伪装</div></div>
            <div class="stat-card"><div class="stat-value">${compliance.compliance_rate}%</div><div class="stat-label">合规率</div></div>
          </div>
          
          <div class="section">
            <div class="section-title">日报类型分布</div>
            <div id="typeChart" class="chart-box"></div>
          </div>
          
          <div class="section">
            <div class="section-title">每日明细</div>
            <table>
              <thead><tr><th>日期</th><th>平台</th><th>类型</th><th>摘要</th></tr></thead>
              <tbody>
                ${summary.reports.slice(0, 100).map((r: any) => {
                  let firstType = '--'
                  try { const items = JSON.parse(r.summary); if (Array.isArray(items) && items[0]) firstType = items[0].type || '--' } catch {}
                  return `<tr><td>${r.date}</td><td>${r.platform}</td><td><span class="tag">${firstType}</span></td><td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${(r.summary || '').slice(0, 100)}</td></tr>`
                }).join('')}
              </tbody>
            </table>
          </div>
          
          <button class="print-btn" onclick="window.print()">🖨 打印 / 保存 PDF</button>
        </div>
        <script>
          const typeData = ${JSON.stringify(workTypes.type_distribution.slice(0, 8))};
          if (document.getElementById('typeChart')) {
            const chart = echarts.init(document.getElementById('typeChart'));
            chart.setOption({
              tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
              series: [{ type: 'pie', radius: ['30%', '60%'], data: typeData.map(d => ({ name: d.name, value: d.count })), label: { formatter: '{b}' } }],
            });
          }
        <\/script>
      </body></html>
    `)
    win.document.close()
  } catch (e: any) {
    props.showToast?.('生成失败: ' + (e.message || ''), 'error')
  } finally {
    generatingReport.value = false
  }
}
```

Stats 模板的汇总统计卡片中增加按钮：
```vue
<div class="btn-group">
  <button class="btn btn-ghost" :disabled="generatingReport" @click="generateReport('weekly')">
    生成周报
  </button>
  <button class="btn btn-ghost" :disabled="generatingReport" @click="generateReport('monthly')">
    生成月报
  </button>
</div>
```

- [ ] **Step 1: 修改 `Stats.vue`** — 追加 generateReport + 按钮 + 新窗口 HTML 模板

---

#### Task B-Commit: Phase B 提交

```bash
git add web/routes.py desktop/src/api/client.ts desktop/src/views/Dashboard.vue desktop/src/views/Reports.vue desktop/src/views/Stats.vue devlog/
git commit -m "[feat] Phase B: 合规率/类型分类统计 API + 前端图表 + HTML 报告导出"
```

---

### Phase C: AI 交互层

#### Task C-1: AIFactory 新增 chat 方法 + 后端 AI 查询端点

**Files:**
- Modify: `providers/modules/ai_factory.py` — 新增通用 chat 方法
- Modify: `web/routes.py` — 新增 POST /admin/ai-query

**Step 1: AIFactory 新增 chat 方法**

在 `ai_factory.py` 的 `summarize` 方法后追加：

```python
async def chat(self, question: str, system_prompt: str = "你是一个有用的AI助手。") -> str:
    """通用对话接口（非日报总结），供 AI 查询等场景使用"""
    chat_req = self.api_reqs.get("chat_completions")
    if not chat_req:
        raise ValueError(f"[{self.AI_PROVIDER_NAME}] 未找到聊天接口")

    cfg = self.model_cfg if self.model_cfg else config.get_model(self.AI_PROVIDER_NAME)
    if not cfg:
        raise ValueError(f"[{self.AI_PROVIDER_NAME}] 未找到模型配置")

    model_id = getattr(self, "model_id", None)
    if not model_id or model_id == self.AI_PROVIDER_NAME:
        model_id = cfg.get("model")
        if not model_id and cfg.get("models") and isinstance(cfg.get("models"), list):
            model_id = cfg.get("models")[0]
    if not model_id:
        raise ValueError(f"[{self.AI_PROVIDER_NAME}] 缺少模型 ID")

    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    }

    custom_params = cfg.get("params", {})
    if custom_params:
        timeout = custom_params.get("timeout", 0)
        if timeout:
            custom_params["timeout"] = timeout * 60
        payload.update(custom_params)

    res_data = await chat_req.fetch(payload)
    return self._parse_response(res_data)
```

**Step 2: routes.py 新增 AI 查询端点**

```python
from pydantic import BaseModel

class AiQueryRequest(BaseModel):
    question: str
    days: int = 30

@router.post("/ai-query")
async def ai_query(data: AiQueryRequest):
    """AI 对话查询：用自然语言查询历史日报数据"""
    from providers.modules.ai_factory import AIFactory

    today = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=data.days)).strftime("%Y-%m-%d")

    # 1. 检索数据
    with db._get_conn() as conn:
        rows = conn.execute(
            "SELECT date, platform, summary, is_camouflage, pushed FROM daily_reports WHERE date BETWEEN ? AND ? ORDER BY date DESC LIMIT 50",
            (start, today),
        ).fetchall()

    reports_data = [dict(r) for r in rows]
    if not reports_data:
        return {"answer": "查询时间范围内没有日报数据。", "source_count": 0}

    # 2. 拼接上下文
    context_lines = [f"在 {start} 到 {today} 之间有 {len(reports_data)} 条日报记录："]
    for r in reports_data[:30]:
        summary_preview = (r["summary"] or "")[:200]
        context_lines.append(f"- {r['date']} [{r['platform']}]: {summary_preview}")
    context = "\n".join(context_lines)

    # 3. 调用 AI
    prompt = f"""你是一个日报数据助手，根据用户的问题和提供的日报数据，给出简洁准确的回答。

用户问题: {data.question}

日报数据:
{context}

请基于以上数据回答用户的问题。如果数据不足以回答，请如实说明。回答要求：
- 简洁、准确、有条理
- 可以引用具体数据
- 不要编造数据中没有的信息"""

    try:
        enabled_workflows = getattr(config, "ENABLED_WORKFLOWS", [])
        if not enabled_workflows:
            return {"answer": "没有配置工作流，无法调用 AI。", "source_count": len(reports_data)}

        first_platform = enabled_workflows[0]
        platform_config = config.get_platform(first_platform)
        model_key = platform_config.get("ai_model", "")

        if not model_key:
            return {"answer": "未找到 AI 模型配置。", "source_count": len(reports_data)}

        ai = AIFactory.get_ai(model_key)
        if not ai:
            return {"answer": "AI 模型不可用。", "source_count": len(reports_data)}

        answer = await ai.chat(prompt, system_prompt="你是一个日报数据助手，基于日报数据回答问题。回答简洁准确。")
        return {"answer": answer, "source_count": len(reports_data)}
    except Exception as e:
        logger.error(f"AI 查询失败: {e}")
        return {"answer": f"AI 查询时出错: {str(e)[:100]}", "source_count": len(reports_data)}
```

注意：检查 `AIFactory` 是否有 `chat` 或类似方法。如果 AI 调用方式不同，需要适配。

- [ ] **Step 1: 检查 `AIFactory` 的调用接口** — 确认是 `chat()` 还是 `summarize()` 还是其他
- [ ] **Step 2: 在 `web/routes.py` 新增端点**
- [ ] **Step 3: 手动测试** — `curl -X POST http://127.0.0.1:8001/admin/ai-query -H "Content-Type: application/json" -d '{"question":"上周做了什么","days":7}' -H "X-Desktop-Client: true"`

---

#### Task C-2: 前端 AI 对话组件 AiAssistant.vue

**Files:**
- Create: `desktop/src/components/AiAssistant.vue`

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api/client'

const props = defineProps<{
  showToast?: (msg: string, type: 'success' | 'error' | 'info') => void
}>()

const emit = defineEmits<{ close: [] }>()

const question = ref('')
const answer = ref('')
const loading = ref(false)
const searched = ref(false)

const suggestions = [
  '上周做了什么工作？',
  '最近修复了哪些 Bug？',
  '哪个平台推送最多？',
  '伪装日报占比多少？',
  '我最近在哪个项目上投入最多？',
]

async function ask(q?: string) {
  const text = q || question.value
  if (!text.trim()) return
  loading.value = true
  answer.value = ''
  searched.value = false
  try {
    const res = await api.aiQuery(text.trim())
    answer.value = res.answer
    searched.value = true
  } catch (e: any) {
    answer.value = '查询失败: ' + (e.message || '未知错误')
  } finally {
    loading.value = false
  }
}

function selectSuggestion(s: string) {
  question.value = s
  ask(s)
}
</script>

<template>
  <div class="ai-assistant glass-card">
    <div class="ai-header">
      <span class="ai-title">AI 助手</span>
      <button class="btn btn-ghost btn-sm" @click="emit('close')">✕</button>
    </div>
    <div class="ai-body">
      <div v-if="!searched && !loading" class="ai-suggestions">
        <div class="text-dim text-sm" style="margin-bottom:8px">试试这些问题：</div>
        <div v-for="s in suggestions" :key="s" class="suggestion-chip" @click="selectSuggestion(s)">
          {{ s }}
        </div>
      </div>
      <div v-if="loading" class="ai-loading">
        <span class="thinking-dots"></span>
        <span class="text-dim text-sm">思考中...</span>
      </div>
      <div v-if="answer" class="ai-answer">{{ answer }}</div>
    </div>
    <div class="ai-footer">
      <input v-model="question" class="ai-input" placeholder="问问你的日报数据..." spellcheck="false"
        @keydown.enter="ask()" :disabled="loading" />
      <button class="btn btn-primary btn-sm" :disabled="loading || !question.trim()" @click="ask()">
        提问
      </button>
    </div>
  </div>
</template>

<style scoped>
.ai-assistant {
  position: fixed; bottom: 16px; right: 16px;
  width: 380px; max-height: 500px;
  display: flex; flex-direction: column;
  z-index: 999; padding: var(--space-2);
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
.ai-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2); }
.ai-title { font-size: 13px; font-weight: 600; }
.ai-body { flex: 1; overflow-y: auto; min-height: 80px; max-height: 320px; margin-bottom: var(--space-2); }
.ai-suggestions { display: flex; flex-direction: column; gap: 4px; }
.suggestion-chip {
  padding: 6px 10px; font-size: 11px; border-radius: var(--radius-sm);
  background: rgba(255,255,255,0.03); cursor: pointer; transition: var(--transition-fast);
  color: var(--text-secondary);
}
.suggestion-chip:hover { background: rgba(255,255,255,0.06); color: var(--text-primary); }
.ai-loading { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2); }
.thinking-dots::after { content: '...'; animation: dots 1.5s steps(4, end) infinite; }
@keyframes dots { 0% { content: '.'; } 25% { content: '..'; } 50% { content: '...'; } 75% { content: ''; } }
.ai-answer { font-size: 12px; line-height: 1.7; white-space: pre-wrap; padding: var(--space-1); color: var(--text-secondary); }
.ai-footer { display: flex; gap: var(--space-1); }
.ai-input { flex: 1; padding: 6px 10px; font-size: 12px; }
.btn-sm { padding: 3px 10px; font-size: 11px; }
</style>
```

- [ ] **Step 1: 创建 `AiAssistant.vue`**
- [ ] **Step 2: 在 `App.vue` 增加 AI 助手开关** — 底部增加"AI 助手"按钮
- [ ] **Step 3: 在 `App.vue` 模板末尾插入组件**

---

#### Task C-3: App.vue 集成 AI 助手

**Files:**
- Modify: `desktop/src/App.vue`

在 sidebar-footer 增加：
```vue
<div class="footer-row">
  <button class="btn btn-ghost btn-sm" style="width:100%" @click="showAiAssistant = !showAiAssistant">
    <span>🤖 AI 助手</span>
  </button>
</div>
```

在模板末尾追加：
```vue
<AiAssistant v-if="showAiAssistant" :show-toast="showToast" @close="showAiAssistant = false" />
```

- [ ] **Step 1: 修改 `App.vue`** — 集成 AI 助手按钮 + 组件

---

#### Task C-Commit: Phase C 提交

```bash
git add web/routes.py desktop/src/api/client.ts desktop/src/components/AiAssistant.vue desktop/src/App.vue devlog/
git commit -m "[feat] Phase C: AI 对话查询 + 浮动助手面板"
```

---

## 最终集成校验

- [ ] **启动后端** — `python serve.py` 确认无 import 错误
- [ ] **启动桌面** — `cd desktop && npm run dev` 确认编译无报错
- [ ] **手动遍历 8 个视图** — 确认无空白/崩溃
- [ ] **测试补录流程** — 添加补录 → 重新执行日报 → 确认合并到 AI 输入
- [ ] **测试通知流程** — 执行日报 → 通知面板出现条目
- [ ] **测试 AI 查询** — 提问 → 获得回答
- [ ] **测试报告导出** — 点击生成周报 → 新窗口打开 → 打印预览
- [ ] **git 提交全部 3 个 phase**
