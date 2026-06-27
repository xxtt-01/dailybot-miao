<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { api } from './api/client'
import TitleBar from './components/TitleBar.vue'
import Toast from './components/Toast.vue'
import ThemeSwitcher from './components/ThemeSwitcher.vue'
import Dashboard from './views/Dashboard.vue'
import Reports from './views/Reports.vue'
import Logs from './views/Logs.vue'
import Config from './views/Config.vue'
import Stats from './views/Stats.vue'
import Camouflage from './views/Camouflage.vue'
import Sources from './views/Sources.vue'
import Scheduler from './views/Scheduler.vue'
import NotificationPanel from './components/NotificationPanel.vue'
import AiAssistant from './components/AiAssistant.vue'

const currentTab = ref('dashboard')
const statusInfo = ref('')
const versionStr = ref('')
const hasUpdate = ref(false)
const showShortcuts = ref(false)
const toastRef = ref<InstanceType<typeof Toast> | null>(null)
const showNotificationPanel = ref(false)
const showAiAssistant = ref(false)
const unreadCount = ref(0)
let notifTimer: ReturnType<typeof setInterval> | null = null

const tabs = [
  { key: 'dashboard',  label: '概览',  icon: '◉' },
  { key: 'reports',    label: '日报',  icon: '≡' },
  { key: 'logs',       label: '日志',  icon: '≫' },
  { key: 'config',     label: '配置',  icon: '⚙' },
  { key: 'stats',      label: '统计',  icon: '◈' },
  { key: 'camouflage', label: '伪装',  icon: '◎' },
  { key: 'sources',    label: '采集源', icon: '↗' },
  { key: 'scheduler',  label: '定时',  icon: '◷' },
]

function switchTab(key: string) { currentTab.value = key }

function showToast(message: string, type: 'success' | 'error' | 'info' = 'info') {
  toastRef.value?.add(message, type)
}

function navigateTo(tab: string) { switchTab(tab) }

async function checkUnread() {
  try {
    const res = await api.getNotifications(1, true)
    unreadCount.value = res.unread_count
  } catch { /* 静默 */ }
}

// 键盘快捷键
const tabKeys = ['dashboard', 'reports', 'logs', 'config', 'stats', 'camouflage', 'sources', 'scheduler']

const shortcuts = [
  { keys: '1 ~ 8', desc: '切换页面' },
  { keys: 'Ctrl + E', desc: '立即执行日报' },
  { keys: 'Ctrl + Alt + D', desc: '显示/隐藏窗口' },
  { keys: '?', desc: '打开快捷键帮助' },
  { keys: 'Esc', desc: '关闭弹窗' },
]

function onKeydown(e: KeyboardEvent) {
  // 1-8 切换页面
  if (e.key >= '1' && e.key <= '8') {
    const idx = parseInt(e.key) - 1
    if (!e.ctrlKey && !e.metaKey) {
      switchTab(tabKeys[idx])
      return
    }
  }
  // Ctrl+E 立即执行日报
  if ((e.ctrlKey || e.metaKey) && (e.key === 'e' || e.key === 'E')) {
    e.preventDefault()
    api.triggerReport()
      .then(() => showToast('日报生成任务已提交', 'success'))
      .catch(() => showToast('触发失败：后端未连接', 'error'))
  }
  // ? 显示快捷键帮助
  if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
    showShortcuts.value = !showShortcuts.value
  }
  // Escape 关闭帮助
  if (e.key === 'Escape' && showShortcuts.value) {
    showShortcuts.value = false
  }
}

onMounted(async () => {
  try {
    const st = await api.getStatus()
    versionStr.value = st.version
    statusInfo.value = `运行中 · ${(st.enabled_workflows || []).join(', ')}`
    const v = await api.getDesktopVersion()
    hasUpdate.value = v.has_update
  } catch { statusInfo.value = '后端未连接' }
  checkUnread()
  notifTimer = setInterval(checkUnread, 30000)
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  if (notifTimer) clearInterval(notifTimer)
})
</script>

<template>
  <div class="app-window">
    <Toast ref="toastRef" />
    <TitleBar />
    <div class="app-body">
      <!-- 侧边栏 -->
      <aside class="sidebar glass-card">
        <div class="sidebar-brand">
          <div class="brand-icon">奕</div>
          <div class="brand-meta">
            <div class="brand-name">DailyBot</div>
            <div class="brand-version">v{{ versionStr || '--' }}</div>
          </div>
        </div>

        <nav class="sidebar-nav">
          <button v-for="tab in tabs" :key="tab.key"
            :class="['nav-item', { active: currentTab === tab.key }]"
            @click="switchTab(tab.key)">
            <span class="nav-icon">{{ tab.icon }}</span>
            <span class="nav-label">{{ tab.label }}</span>
            <span v-if="tab.key === 'config' && hasUpdate" class="update-dot"></span>
          </button>
        </nav>

        <div class="sidebar-footer">
          <div class="footer-row">
            <div class="status-dot" :class="statusInfo ? 'online' : 'offline'"></div>
            <span class="footer-status text-dim text-sm truncate">{{ statusInfo || '未连接' }}</span>
          </div>
          <div class="footer-row footer-actions">
            <ThemeSwitcher />
            <button class="notif-bell-btn" @click="showNotificationPanel = !showNotificationPanel" title="通知">
              <span class="bell-icon">🔔</span>
              <span v-if="unreadCount > 0" class="notif-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
            </button>
            <button class="btn btn-ghost btn-sm" style="font-size:11px;padding:2px 6px" @click="showAiAssistant = !showAiAssistant" title="AI 助手">AI</button>
          </div>
          <div class="footer-row shortcut-hint text-dim text-sm">
            <span>1-8 切换 · Ctrl+E 执行 · ? 帮助</span>
          </div>
        </div>
      </aside>

      <!-- 内容区 -->
      <main class="main-content">
        <Transition name="page" mode="out-in">
          <Dashboard v-if="currentTab === 'dashboard'" key="dashboard" :show-toast="showToast" :on-navigate="navigateTo" />
          <Reports v-else-if="currentTab === 'reports'" key="reports" :show-toast="showToast" />
          <Logs v-else-if="currentTab === 'logs'" key="logs" />
          <Config v-else-if="currentTab === 'config'" key="config" :show-toast="showToast" />
          <Stats v-else-if="currentTab === 'stats'" key="stats" />
          <Camouflage v-else-if="currentTab === 'camouflage'" key="camouflage" :show-toast="showToast" />
          <Sources v-else-if="currentTab === 'sources'" key="sources" :show-toast="showToast" />
          <Scheduler v-else-if="currentTab === 'scheduler'" key="scheduler" :show-toast="showToast" />
        </Transition>
      </main>
    </div>

    <!-- 快捷键帮助弹窗 -->
    <Teleport to="body">
      <div v-if="showShortcuts" class="modal-overlay" @click.self="showShortcuts = false">
        <div class="modal-box shortcuts-panel">
          <div class="modal-header">
            <h3>⌨ 快捷键</h3>
            <button class="btn btn-ghost" @click="showShortcuts = false">✕</button>
          </div>
          <div class="shortcuts-grid">
            <div v-for="s in shortcuts" :key="s.keys" class="shortcut-row">
              <span class="shortcut-keys">{{ s.keys }}</span>
              <span class="shortcut-desc text-dim">{{ s.desc }}</span>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <NotificationPanel v-if="showNotificationPanel" :show-toast="showToast" @close="showNotificationPanel = false" />
    <AiAssistant v-if="showAiAssistant" :show-toast="showToast" @close="showAiAssistant = false" />
  </div>
</template>

<style scoped>
.app-window {
  display: flex; flex-direction: column;
  height: 100vh; overflow: hidden;
}

.app-body {
  display: flex; flex: 1; overflow: hidden;
}

/* ── 侧边栏 ── */
.sidebar {
  width: 184px; flex-shrink: 0;
  margin: 0 var(--space-1) var(--space-1) var(--space-1);
  padding: var(--space-2) var(--space-2) var(--space-2);
  display: flex; flex-direction: column;
  border-radius: var(--radius-lg);
}

.sidebar-brand {
  display: flex; align-items: center; gap: var(--space-2);
  padding-bottom: var(--space-2);
  margin-bottom: var(--space-2);
  border-bottom: 1px solid var(--glass-border);
}
.brand-icon {
  width: 32px; height: 32px; border-radius: var(--radius-sm);
  background: var(--accent-glow);
  color: var(--accent);
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 700; flex-shrink: 0;
}
.brand-meta { flex: 1; min-width: 0; }
.brand-name { font-size: 12px; font-weight: 600; color: var(--text-primary); }
.brand-version { font-size: 10px; color: var(--text-dim); margin-top: 1px; }

.sidebar-nav { flex: 1; display: flex; flex-direction: column; gap: 1px; }

.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 7px 10px;
  border: none; border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary); cursor: pointer;
  font-family: var(--font-mono); font-size: 12px;
  transition: var(--transition-fast);
  text-align: left; width: 100%; position: relative;
}
.nav-item:hover { background: rgba(255,255,255,0.03); color: var(--text-primary); }
.nav-item.active {
  background: var(--accent-glow);
  color: var(--accent);
  box-shadow: inset 2px 0 0 var(--accent);
}

.nav-icon { width: 14px; text-align: center; font-size: 12px; opacity: 0.7; }
.nav-item.active .nav-icon { opacity: 1; }
.nav-label { flex: 1; }

.update-dot {
  width: 5px; height: 5px; border-radius: 50%;
  background: var(--accent); margin-left: auto;
  box-shadow: 0 0 4px rgba(183,234,212,0.6);
}

/* ── 底部 ── */
.sidebar-footer {
  display: flex; flex-direction: column; gap: var(--space-1);
  padding-top: var(--space-2);
  border-top: 1px solid var(--glass-border);
  margin-top: var(--space-1);
}
.footer-row { display: flex; align-items: center; gap: 8px; }
.footer-actions { justify-content: flex-end; }
.footer-status { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.shortcut-hint { opacity: 0.45; font-size: 10px; line-height: 1.4; text-align: center; justify-content: center; }

/* ── 通知铃铛 ── */
.notif-bell-btn {
  position: relative; background: none; border: none; cursor: pointer;
  padding: 4px; font-size: 14px; line-height: 1; border-radius: var(--radius-sm);
  color: var(--text-dim); transition: var(--transition-fast);
}
.notif-bell-btn:hover { color: var(--text-primary); background: rgba(255,255,255,0.05); }
.notif-badge {
  position: absolute; top: -2px; right: -4px;
  background: var(--danger, #e06c75); color: #fff;
  font-size: 9px; font-weight: 700; line-height: 1;
  padding: 2px 4px; border-radius: 8px; min-width: 14px; text-align: center;
  box-shadow: 0 0 4px rgba(224,108,117,0.5); pointer-events: none;
}

/* ── 快捷键帮助 ── */
.shortcuts-panel { max-width: 400px; }
.shortcuts-grid { display: flex; flex-direction: column; gap: var(--space-1); }
.shortcut-row { display: flex; align-items: center; gap: var(--space-2); padding: 6px 0; border-bottom: 1px solid var(--glass-border); font-size: 12px; }
.shortcut-row:last-child { border-bottom: none; }
.shortcut-keys {
  font-family: var(--font-mono); font-size: 11px; font-weight: 600;
  background: rgba(255,255,255,0.06); padding: 2px 8px; border-radius: 4px;
  min-width: 100px; text-align: center; color: var(--accent);
}
.shortcut-desc { flex: 1; }

/* ── 内容区 ── */
.main-content {
  flex: 1; overflow-y: auto;
  padding: var(--space-3);
  margin: 0 var(--space-1) var(--space-1) 0;
}
</style>
