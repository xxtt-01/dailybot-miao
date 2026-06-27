<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from './api/client'
import TitleBar from './components/TitleBar.vue'
import Toast from './components/Toast.vue'
import Dashboard from './views/Dashboard.vue'
import Reports from './views/Reports.vue'
import Logs from './views/Logs.vue'
import Config from './views/Config.vue'
import Stats from './views/Stats.vue'
import Camouflage from './views/Camouflage.vue'
import Sources from './views/Sources.vue'
import Scheduler from './views/Scheduler.vue'

const currentTab = ref('dashboard')
const statusInfo = ref('')
const versionStr = ref('')
const hasUpdate = ref(false)
const toastRef = ref<InstanceType<typeof Toast> | null>(null)

const tabs = [
  { key: 'dashboard', label: '概览', icon: '◉' },
  { key: 'reports', label: '日报', icon: '≡' },
  { key: 'logs', label: '日志', icon: '≫' },
  { key: 'config', label: '配置', icon: '⚙' },
  { key: 'stats', label: '统计', icon: '◈' },
  { key: 'camouflage', label: '伪装', icon: '◎' },
  { key: 'sources', label: '采集源', icon: '↗' },
  { key: 'scheduler', label: '定时', icon: '◷' },
]

function switchTab(key: string) { currentTab.value = key }

// 暴露 toast 给子组件使用
function showToast(message: string, type: 'success' | 'error' | 'info' = 'info') {
  toastRef.value?.add(message, type)
}

onMounted(async () => {
  try {
    const st = await api.getStatus()
    versionStr.value = st.version
    statusInfo.value = `运行中 · ${(st.enabled_workflows || []).join(', ')}`
    const v = await api.getDesktopVersion()
    hasUpdate.value = v.has_update
  } catch {
    statusInfo.value = '后端未连接'
  }
})
</script>

<template>
  <div class="app-frame">
    <Toast ref="toastRef" />
    <TitleBar />
    <div class="app-body">
      <aside class="sidebar glass-card">
        <div class="sidebar-header">
          <div class="version-text">v{{ versionStr || '--' }}</div>
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
          <div class="status-dot" :class="statusInfo ? 'online' : 'offline'"></div>
          <span class="text-dim text-sm truncate">{{ statusInfo || '未连接' }}</span>
        </div>
      </aside>

      <main class="main-content">
        <Transition name="page" mode="out-in">
          <Dashboard v-if="currentTab === 'dashboard'" key="dashboard"
            :show-toast="showToast" />
          <Reports v-else-if="currentTab === 'reports'" key="reports"
            :show-toast="showToast" />
          <Logs v-else-if="currentTab === 'logs'" key="logs" />
          <Config v-else-if="currentTab === 'config'" key="config"
            :show-toast="showToast" />
          <Stats v-else-if="currentTab === 'stats'" key="stats" />
          <Camouflage v-else-if="currentTab === 'camouflage'" key="camouflage"
            :show-toast="showToast" />
          <Sources v-else-if="currentTab === 'sources'" key="sources"
            :show-toast="showToast" />
          <Scheduler v-else-if="currentTab === 'scheduler'" key="scheduler"
            :show-toast="showToast" />
        </Transition>
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-frame { display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
.app-body { display: flex; flex: 1; overflow: hidden; }

.sidebar {
  width: 180px; margin: 0 var(--space-1) var(--space-1) var(--space-1);
  padding: var(--space-2) var(--space-2) var(--space-2);
  display: flex; flex-direction: column;
  border-radius: var(--radius-lg); flex-shrink: 0;
}
.sidebar-header {
  text-align: center; padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--glass-border); margin-bottom: var(--space-2);
}
.version-text { font-size: 11px; color: var(--text-dim); }

.sidebar-nav { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px;
  border: none; border-radius: var(--radius-sm); background: transparent;
  color: var(--text-secondary); cursor: pointer; font-family: var(--font-mono);
  font-size: 12px; transition: var(--transition-fast);
  text-align: left; width: 100%; position: relative;
}
.nav-item:hover { background: rgba(255,255,255,0.04); color: var(--text-primary); }
.nav-item.active {
  background: rgba(183,234,212,0.08); color: var(--accent);
  box-shadow: inset 3px 0 0 var(--accent);
}

.nav-icon { width: 16px; text-align: center; font-size: 13px; }

.update-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent); margin-left: auto;
  box-shadow: 0 0 6px rgba(183,234,212,0.6);
}

.sidebar-footer {
  display: flex; align-items: center; gap: 8px;
  padding-top: var(--space-2); border-top: 1px solid var(--glass-border);
}
.truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.main-content {
  flex: 1; overflow-y: auto;
  padding: var(--space-2);
  margin: 0 var(--space-1) var(--space-1) 0;
}
</style>
