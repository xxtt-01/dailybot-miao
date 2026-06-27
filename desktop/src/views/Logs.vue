<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { api, type RunLog } from '../api/client'

const logs = ref<RunLog[]>([])
const loading = ref(true)
const error = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

async function loadLogs() {
  try {
    const res = await api.getLogs(100)
    logs.value = res.logs || []
    error.value = ''
  } catch (e: any) {
    error.value = '获取日志失败: ' + (e.message || '未知错误')
  } finally {
    loading.value = false
  }
}

function statusTag(status: string): string {
  switch (status) {
    case 'success': return 'tag-success'
    case 'failed': return 'tag-danger'
    case 'no_data': return 'tag-warning'
    default: return 'tag-info'
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'success': return '成功'
    case 'failed': return '失败'
    case 'no_data': return '无数据'
    default: return status
  }
}

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
      <span class="text-dim text-sm">每10秒自动刷新</span>
    </div>

    <div v-if="loading" class="loading-text text-dim">加载中...</div>
    <div v-else-if="error" class="error-box glass-card">
      <span class="tag tag-danger">错误</span>
      <span>{{ error }}</span>
    </div>
    <div v-else class="log-list">
      <div v-if="logs.length === 0" class="empty-state text-dim">暂无日志记录</div>
      <div v-for="log in logs" :key="log.id" class="glass-card log-item">
        <span class="log-time text-dim text-sm">{{ log.created_at || log.date }}</span>
        <span class="tag" :class="statusTag(log.status)">{{ statusLabel(log.status) }}</span>
        <span class="log-platform text-dim">{{ log.platform ? '[' + log.platform + ']' : '' }}</span>
        <span class="log-message">{{ log.message }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { padding: var(--space-2); }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2); }
.page-header h2 { margin: 0; }
.loading-text { padding: var(--space-4); text-align: center; }
.error-box { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2); }
.log-list { display: flex; flex-direction: column; gap: 4px; }
.log-item {
  display: flex; align-items: center; gap: var(--space-2);
  padding: 6px 12px; font-size: 12px;
}
.log-time { white-space: nowrap; flex-shrink: 0; min-width: 140px; }
.log-platform { white-space: nowrap; flex-shrink: 0; }
.log-message { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.empty-state { padding: var(--space-4); text-align: center; }
</style>
