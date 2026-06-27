<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { api, type RunLog } from '../api/client'

const logs = ref<RunLog[]>([])
const loading = ref(true)
const error = ref('')
const refreshing = ref(false)
const searchQuery = ref('')
const listRef = ref<HTMLElement | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

async function loadLogs() {
  if (!loading.value) refreshing.value = true
  try {
    const res = await api.getLogs(100, searchQuery.value || undefined)
    logs.value = res.logs || []
    error.value = ''
  } catch (e: any) {
    error.value = '获取日志失败: ' + (e.message || '未知错误')
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

function statusTag(s: string): string {
  switch (s) { case 'success': return 'tag-success'; case 'failed': return 'tag-danger'; case 'no_data': return 'tag-warning'; default: return 'tag-info' }
}
function statusLabel(s: string): string {
  switch (s) { case 'success': return '成功'; case 'failed': return '失败'; case 'no_data': return '无数据'; default: return s }
}
function timeStr(t: string) { return (t || '').replace('T', ' ').slice(0, 19) }

onMounted(() => {
  loadLogs()
  pollTimer = setInterval(loadLogs, 10000)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>运行日志</h2>
      <div class="header-right">
        <label class="search-box">
          <input type="text" v-model="searchQuery" placeholder="搜索日志…" @change="loadLogs" class="search-input" />
        </label>
        <span class="auto-refresh-hint" :class="{ active: !loading }">
          <span class="refresh-dot"></span>
          自动刷新
        </span>
        <button class="btn btn-ghost" :disabled="refreshing" @click="loadLogs">
          {{ refreshing ? '刷新中...' : '刷新' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div v-for="i in 5" :key="i" class="skeleton" :style="{ height: '32px', marginBottom: '6px' }"></div>
    </div>

    <div v-else-if="error" class="glass-card" style="display:flex;align-items:center;gap:12px;padding:16px">
      <span class="tag tag-danger">错误</span>
      <span>{{ error }}</span>
    </div>

    <div v-else ref="listRef" class="log-scroll">
      <TransitionGroup name="log-fade" tag="div" class="log-list">
        <div v-for="log in logs" :key="log.id" class="glass-card log-item">
          <span class="log-time">{{ timeStr(log.created_at) }}</span>
          <span class="tag" :class="statusTag(log.status)">{{ statusLabel(log.status) }}</span>
          <span class="log-msg">
            <span v-if="log.platform" class="log-platform">{{ '[' + log.platform + ']' }}</span>
            {{ log.message }}
          </span>
        </div>
      </TransitionGroup>
      <div v-if="logs.length === 0" class="glass-card" style="padding:32px;text-align:center">
        <div class="text-dim">暂无日志记录</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { padding: var(--space-2); height: 100%; display: flex; flex-direction: column; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2); flex-shrink: 0; }
.page-header h2 { font-size: 16px; font-weight: 600; margin: 0; }
.header-right { display: flex; align-items: center; gap: var(--space-2); }

.auto-refresh-hint {
  display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-dim);
}
.refresh-dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--success);
  opacity: 0.4; transition: var(--transition-fast);
}
.auto-refresh-hint.active .refresh-dot { opacity: 1; animation: pulse 2s infinite; }
.search-box { display: flex; }
.search-input { width: 140px; font-size: 11px; padding: 4px 8px; }

.loading-state { padding: var(--space-2); }

.log-scroll { flex: 1; overflow-y: auto; }
.log-list { display: flex; flex-direction: column; gap: 3px; }

.log-item {
  display: flex; align-items: center; gap: var(--space-2);
  padding: 7px 12px; font-size: 12px;
}
.log-time { white-space: nowrap; flex-shrink: 0; min-width: 150px; color: var(--text-dim); font-size: 11px; }
.log-msg { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.log-platform { color: var(--text-dim); margin-right: 4px; }

/* TransitionGroup 动画 */
.log-fade-enter-active { transition: all var(--transition-normal); }
.log-fade-enter-from { opacity: 0; transform: translateX(-10px); }
.log-fade-move { transition: transform var(--transition-normal); }
</style>
