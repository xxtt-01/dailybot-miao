<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from './api/client'
import Dashboard from './views/Dashboard.vue'
import Reports from './views/Reports.vue'
import Logs from './views/Logs.vue'
import Config from './views/Config.vue'
import Stats from './views/Stats.vue'
import Camouflage from './views/Camouflage.vue'
import Sources from './views/Sources.vue'
import Scheduler from './views/Scheduler.vue'

const currentTab = ref('dashboard')
const statusInfo = ref<string>('')
const versionStr = ref('')
const hasUpdate = ref(false)

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
  <div class="app-layout">
    <aside class="sidebar glass-card">
      <div class="sidebar-header">
        <div class="logo">奕</div>
        <div class="version">v{{ versionStr || '--' }}</div>
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
        <span class="text-dim text-sm">{{ statusInfo || '未连接' }}</span>
      </div>
    </aside>

    <main class="main-content">
      <Dashboard v-if="currentTab === 'dashboard'" />
      <Reports v-else-if="currentTab === 'reports'" />
      <Logs v-else-if="currentTab === 'logs'" />
      <Config v-else-if="currentTab === 'config'" />
      <Stats v-else-if="currentTab === 'stats'" />
      <Camouflage v-else-if="currentTab === 'camouflage'" />
      <Sources v-else-if="currentTab === 'sources'" />
      <Scheduler v-else-if="currentTab === 'scheduler'" />
    </main>
  </div>
</template>

<style scoped>
.app-layout { display: flex; height: 100vh; overflow: hidden; }

.sidebar {
  width: 180px; margin: var(--space-1); padding: var(--space-2);
  display: flex; flex-direction: column; border-radius: var(--radius-lg); flex-shrink: 0;
}
.sidebar-header { text-align: center; padding-bottom: var(--space-2); border-bottom: 1px solid var(--glass-border); margin-bottom: var(--space-2); }
.logo { font-size: 28px; font-weight: 700; color: var(--accent); }
.version { font-size: 11px; color: var(--text-dim); margin-top: 4px; }

.sidebar-nav { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.nav-item {
  display: flex; align-items: center; gap: 10px; padding: 8px 12px;
  border: none; border-radius: var(--radius-sm); background: transparent;
  color: var(--text-secondary); cursor: pointer; font-family: var(--font-mono);
  font-size: 12px; transition: var(--transition-fast); text-align: left; width: 100%;
}
.nav-item:hover { background: rgba(255,255,255,0.05); color: var(--text-primary); }
.nav-item.active { background: rgba(183,234,212,0.1); color: var(--accent); }
.nav-icon { width: 16px; text-align: center; font-size: 13px; }
.update-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); margin-left: auto; animation: pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

.sidebar-footer {
  display: flex; align-items: center; gap: 8px; padding-top: var(--space-2);
  border-top: 1px solid var(--glass-border);
}
.status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.status-dot.online { background: var(--success); box-shadow: 0 0 6px rgba(78,199,127,0.5); }
.status-dot.offline { background: var(--danger); }

.main-content { flex: 1; overflow-y: auto; padding: var(--space-2); margin: var(--space-1) var(--space-1) var(--space-1) 0; }
</style>
