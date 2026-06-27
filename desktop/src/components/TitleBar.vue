<!-- desktop/src/components/TitleBar.vue — 自定义窗口标题栏（玻璃质感） -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'

const isMaximized = ref(false)

declare const windowControls: {
  minimize: () => void
  maximize: () => void
  close: () => void
  isMaximized: () => Promise<boolean>
  onMaximizeChange: (cb: (m: boolean) => void) => void
}

onMounted(async () => {
  try {
    isMaximized.value = await windowControls.isMaximized()
    windowControls.onMaximizeChange((m) => { isMaximized.value = m })
  } catch { /* Electron 外运行忽略 */ }
})

function minimize() { windowControls.minimize() }
function maximize() { windowControls.maximize() }
function closeWin() { windowControls.close() }
</script>

<template>
  <div class="titlebar">
    <div class="titlebar-drag">
      <span class="titlebar-icon">奕</span>
      <span class="titlebar-text">DailyBot 小奕</span>
      <span v-if="isMaximized" class="maximized-hint">· 最大化</span>
    </div>
    <div class="titlebar-controls">
      <button class="control-btn" @click="minimize" title="最小化">
        <svg width="12" height="12" viewBox="0 0 12 12"><rect x="1" y="5.5" width="10" height="1" fill="currentColor" rx="0.5"/></svg>
      </button>
      <button class="control-btn" @click="maximize" title="最大化">
        <svg v-if="!isMaximized" width="12" height="12" viewBox="0 0 12 12">
          <rect x="1.5" y="1.5" width="9" height="9" fill="none" stroke="currentColor" stroke-width="1.2" rx="1"/>
        </svg>
        <svg v-else width="12" height="12" viewBox="0 0 12 12">
          <rect x="3" y="0.5" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.2" rx="1"/>
          <rect x="0.5" y="3" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.2" rx="1" style="background:var(--bg-base)"/>
        </svg>
      </button>
      <button class="control-btn control-close" @click="closeWin" title="关闭">
        <svg width="12" height="12" viewBox="0 0 12 12">
          <path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.titlebar {
  display: flex;
  align-items: center;
  height: 34px;
  flex-shrink: 0;
  user-select: none;
  background: rgba(24, 28, 36, 0.3);
  border-bottom: 1px solid rgba(128, 138, 152, 0.06);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}
.titlebar-drag {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 14px;
  height: 100%;
  -webkit-app-region: drag;
}
.titlebar-icon {
  font-size: 15px;
  font-weight: 700;
  color: var(--accent);
  opacity: 0.9;
}
.titlebar-text {
  font-size: 12px;
  color: var(--text-secondary);
  letter-spacing: 0.2px;
}
.maximized-hint { font-size: 11px; color: var(--text-dim); }
.titlebar-controls {
  display: flex;
  height: 100%;
  -webkit-app-region: no-drag;
}
.control-btn {
  width: 46px;
  height: 100%;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-fast);
}
.control-btn:hover {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-primary);
}
.control-close:hover {
  background: rgba(240, 106, 123, 0.15);
  color: var(--danger);
}
.control-btn:active { background: rgba(255, 255, 255, 0.1); }
.control-close:active { background: rgba(240, 106, 123, 0.25); }
</style>
