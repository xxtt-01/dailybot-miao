<!-- desktop/src/components/TitleBar.vue — 自定义窗口标题栏 -->
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
  } catch {
    // Electron 外运行（如浏览器开发模式）忽略
  }
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
    </div>
    <div class="titlebar-controls">
      <button class="control-btn" @click="minimize" title="最小化">─</button>
      <button class="control-btn" @click="maximize" title="最大化">
        {{ isMaximized ? '❐' : '□' }}
      </button>
      <button class="control-btn control-close" @click="closeWin" title="关闭">✕</button>
    </div>
  </div>
</template>

<style scoped>
.titlebar {
  display: flex;
  align-items: center;
  height: 32px;
  flex-shrink: 0;
  user-select: none;
}
.titlebar-drag {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 12px;
  height: 100%;
  -webkit-app-region: drag;
}
.titlebar-icon {
  font-size: 16px;
  font-weight: 700;
  color: var(--accent);
}
.titlebar-text {
  font-size: 12px;
  color: var(--text-secondary);
}
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
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-fast);
  font-family: var(--font-mono);
}
.control-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-primary);
}
.control-close:hover {
  background: rgba(240, 106, 123, 0.2);
  color: var(--danger);
}
</style>
