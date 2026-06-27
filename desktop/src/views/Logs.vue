<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { api, type RunLog } from '../api/client'
import VirtualList from '../components/VirtualList.vue'

const logs = ref<RunLog[]>([])
const MAX_LIVE_LINES = 1000
const liveLines = ref<{ id: number; time: string; level: string; msg: string }[]>([])
const loading = ref(true)
const error = ref('')
const refreshing = ref(false)
const searchQuery = ref('')
const liveMode = ref(false)
const listRef = ref<HTMLElement | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null
let abortController: AbortController | null = null
let lineIdCounter = 0

// ── 历史日志 ──

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

// ── 实时日志 SSE ──

async function startLiveLogs() {
  liveLines.value = []
  abortController = new AbortController()
  try {
    const response = await fetch('http://127.0.0.1:8001/admin/live-logs', {
      headers: { 'X-Desktop-Client': 'true' },
      signal: abortController.signal,
    })
    if (!response.ok) { stopLiveLogs(); return }
    const reader = response.body?.getReader()
    if (!reader) { stopLiveLogs(); return }
    const decoder = new TextDecoder()
    let buffer = ''

    const readLoop = async () => {
      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const parsed = JSON.parse(line.slice(6))
              const text = parsed.text || ''
              const parts = text.split(' | ')
              const time = parts[0] || ''
              const level = parts[1] || 'INFO'
              const msg = parts.slice(2).join(' | ') || text
              const id = lineIdCounter++
              liveLines.value.push({ id, time, level, msg })
              // 上限控制：超出 1000 行时丢弃最旧的 25%
              if (liveLines.value.length > MAX_LIVE_LINES) {
                liveLines.value.splice(0, Math.floor(MAX_LIVE_LINES / 4))
              }
            }
          }
          // 自动滚动到底部
          await nextTick()
          if (listRef.value) {
            listRef.value.scrollTop = listRef.value.scrollHeight
          }
        }
      } catch { /* 流中断 */ }
      stopLiveLogs()
    }
    readLoop()
  } catch { stopLiveLogs() }
}

function stopLiveLogs() {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
}

function toggleLiveMode() {
  liveMode.value = !liveMode.value
  if (liveMode.value) {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
    startLiveLogs()
  } else {
    stopLiveLogs()
    pollTimer = setInterval(loadLogs, 10000)
    loadLogs()
  }
}

// ── 格式化 ──

function timeStr(t: string) { return (t || '').replace('T', ' ').slice(0, 19) }
function statusTag(s: string): string {
  switch (s) { case 'success': return 'tag-success'; case 'failed': return 'tag-danger'; case 'no_data': return 'tag-warning'; default: return 'tag-info' }
}
function statusLabel(s: string): string {
  switch (s) { case 'success': return '成功'; case 'failed': return '失败'; case 'no_data': return '无数据'; default: return s }
}
function levelTag(s: string): string {
  const lower = s.toLowerCase()
  if (lower.includes('error') || lower.includes('fail')) return 'tag-danger'
  if (lower.includes('warn')) return 'tag-warning'
  if (lower.includes('success') || lower.includes('完成')) return 'tag-success'
  return 'tag-info'
}

// ── 生命周期 ──

onMounted(() => {
  loadLogs()
  pollTimer = setInterval(loadLogs, 10000)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
  stopLiveLogs()
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>运行日志</h2>
      <div class="header-right">
        <button class="btn" :class="liveMode ? 'btn-primary' : 'btn-ghost'" @click="toggleLiveMode">
          <span class="live-dot" :class="{ active: liveMode }"></span>
          {{ liveMode ? '实时' : '历史' }}
        </button>
        <label v-if="!liveMode" class="search-box">
          <input type="text" v-model="searchQuery" placeholder="搜索日志…" @change="loadLogs" class="search-input" />
        </label>
        <span v-if="!liveMode" class="auto-refresh-hint" :class="{ active: !loading }">
          <span class="refresh-dot"></span>
          自动刷新
        </span>
        <button v-if="!liveMode" class="btn btn-ghost" :disabled="refreshing" @click="loadLogs">
          {{ refreshing ? '刷新中...' : '刷新' }}
        </button>
      </div>
    </div>

    <!-- 加载态：历史模式 -->
    <div v-if="!liveMode && loading" class="loading-state">
      <div v-for="i in 5" :key="i" class="skeleton" :style="{ height: '32px', marginBottom: '6px' }"></div>
    </div>

    <!-- 错误 -->
    <div v-else-if="!liveMode && error" class="glass-card" style="display:flex;align-items:center;gap:12px;padding:16px">
      <span class="tag tag-danger">错误</span>
      <span>{{ error }}</span>
    </div>

    <!-- 历史日志列表（虚拟滚动） -->
    <VirtualList v-else-if="!liveMode" :items="logs" :item-height="36" :overscan="8">
      <template #default="{ item: log }">
        <div class="glass-card log-item">
          <span class="log-time">{{ timeStr(log.created_at) }}</span>
          <span class="tag" :class="statusTag(log.status)">{{ statusLabel(log.status) }}</span>
          <span class="log-msg">
            <span v-if="log.platform" class="log-platform">{{ '[' + log.platform + ']' }}</span>
            {{ log.message }}
          </span>
        </div>
      </template>
      <template #empty>
        <div class="text-dim">暂无日志记录</div>
      </template>
    </VirtualList>

    <!-- 实时日志列表 -->
    <div v-else ref="listRef" class="log-scroll live-scroll">
      <div class="live-indicator glass-card">
        <span class="live-dot active"></span>
        <span>实时日志流 — 执行日报后自动显示</span>
      </div>
      <TransitionGroup name="log-fade" tag="div" class="log-list">
        <div v-for="line in liveLines" :key="line.id" class="glass-card log-item">
          <span class="log-time">{{ line.time }}</span>
          <span class="tag" :class="levelTag(line.level)">{{ line.level }}</span>
          <span class="log-msg">{{ line.msg }}</span>
        </div>
      </TransitionGroup>
      <div v-if="liveLines.length === 0" class="glass-card" style="padding:32px;text-align:center">
        <div class="text-dim">等待日志… 点击「执行日报」查看实时输出</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { padding: var(--space-2); height: 100%; display: flex; flex-direction: column; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2); flex-shrink: 0; }
.page-header h2 { font-size: 16px; font-weight: 600; margin: 0; }
.header-right { display: flex; align-items: center; gap: var(--space-2); }

.live-dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--text-dim);
  display: inline-block; margin-right: 2px;
}
.live-dot.active { background: var(--success); animation: pulse 1.5s infinite; }

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

.log-list { display: flex; flex-direction: column; gap: 3px; }

.log-item {
  display: flex; align-items: center; gap: var(--space-2);
  padding: 7px 12px; font-size: 12px;
}
.log-time { white-space: nowrap; flex-shrink: 0; min-width: 150px; color: var(--text-dim); font-size: 11px; }
.log-msg { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.log-platform { color: var(--text-dim); margin-right: 4px; }

.live-scroll { background: rgba(0,0,0,0.15); border-radius: var(--radius-sm); padding: var(--space-1); }
.live-indicator { display: flex; align-items: center; gap: var(--space-2); padding: 6px 12px; margin-bottom: var(--space-1); font-size: 11px; }

/* TransitionGroup 动画 */
.log-fade-enter-active { transition: all var(--transition-normal); }
.log-fade-enter-from { opacity: 0; transform: translateX(-10px); }
.log-fade-move { transition: transform var(--transition-normal); }

@keyframes pulse { 0%,100%{opacity:0.5} 50%{opacity:0.2} }
</style>
