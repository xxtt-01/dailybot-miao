<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type Report, type SystemStatus, type VersionInfo } from '../api/client'

const status = ref<SystemStatus | null>(null)
const versionInfo = ref<VersionInfo | null>(null)
const reports = ref<Report[]>([])
const loading = ref(true)
const error = ref('')
const reportLoading = ref(false)
const reportDone = ref(false)

async function loadStatus() {
  try {
    status.value = await api.getStatus()
  } catch (e: any) {
    error.value = '获取状态失败: ' + (e.message || '未知错误')
  }
}

async function loadVersion() {
  try {
    versionInfo.value = await api.getDesktopVersion()
  } catch { /* 静默忽略 */ }
}

async function loadReports() {
  try {
    const today = new Date().toISOString().slice(0, 10)
    const res = await api.getReports(today)
    reports.value = (res.reports || []).slice(0, 7)
  } catch { /* 静默忽略 */ }
}

async function triggerReport() {
  reportLoading.value = true
  reportDone.value = false
  try {
    await api.triggerReport()
    reportDone.value = true
    alert('日报已触发执行，请稍后查看结果')
    await loadReports()
  } catch (e: any) {
    alert('触发失败: ' + (e.message || '未知错误'))
  } finally {
    reportLoading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadStatus(), loadVersion(), loadReports()])
  loading.value = false
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>概览</h2>
      <button class="btn btn-primary" :disabled="reportLoading" @click="triggerReport">
        {{ reportLoading ? '执行中...' : '▶ 执行日报' }}
      </button>
    </div>

    <!-- 版本更新横幅 -->
    <div v-if="versionInfo?.has_update" class="update-banner glass-card">
      <span>📦 新版本 {{ versionInfo.latest_version }} 可用 (当前: {{ versionInfo.current_version }})</span>
      <a :href="versionInfo.download_url" class="btn btn-ghost" target="_blank">前往下载</a>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-text text-dim">加载中...</div>

    <!-- 错误提示 -->
    <div v-else-if="error" class="error-box glass-card">
      <span class="tag tag-danger">错误</span>
      <span>{{ error }}</span>
    </div>

    <!-- 状态卡片 -->
    <div v-else class="cards-grid">
      <div class="glass-card status-card">
        <div class="card-label text-dim">版本</div>
        <div class="card-value">{{ status?.version || '--' }}</div>
      </div>
      <div class="glass-card status-card">
        <div class="card-label text-dim">工作流</div>
        <div class="card-value">{{ (status?.enabled_workflows || []).length }}</div>
        <div class="card-sub text-sm text-dim">{{ (status?.enabled_workflows || []).join(', ') || '无' }}</div>
      </div>
      <div class="glass-card status-card">
        <div class="card-label text-dim">AI 模型</div>
        <div class="card-value">{{ status?.platforms?.length || 0 }} 个</div>
        <div class="card-sub text-sm text-dim">
          {{ status?.platforms?.map(p => p.ai_model).filter(Boolean).join(', ') || '--' }}
        </div>
      </div>
      <div class="glass-card status-card">
        <div class="card-label text-dim">运行状态</div>
        <div class="card-value tag tag-success">运行中</div>
        <div class="card-sub text-sm text-dim">更新时间: {{ status?.time || '--' }}</div>
      </div>
    </div>

    <!-- 最近日报 -->
    <div class="section">
      <h3 class="section-title">今日日报摘要</h3>
      <div v-if="reports.length === 0" class="empty-state text-dim">暂无今日日报记录</div>
      <div v-else class="report-list">
        <div v-for="r in reports" :key="r.id" class="glass-card report-item">
          <div class="report-meta">
            <span class="tag" :class="r.is_camouflage ? 'tag-warning' : 'tag-info'">
              {{ r.is_camouflage ? '伪装' : '正常' }}
            </span>
            <span class="text-dim text-sm">{{ r.platform }}</span>
            <span class="text-dim text-sm">{{ r.created_at?.slice(11, 19) || r.date }}</span>
          </div>
          <div class="report-summary">{{ r.summary?.slice(0, 120) }}{{ r.summary?.length > 120 ? '...' : '' }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { padding: var(--space-2); }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-3); }
.page-header h2 { margin: 0; }
.loading-text { padding: var(--space-4); text-align: center; }
.error-box { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2); margin-bottom: var(--space-3); }
.update-banner { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); padding: var(--space-2); margin-bottom: var(--space-3); border-color: rgba(183, 234, 212, 0.3); }
.cards-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-2); margin-bottom: var(--space-3); }
.status-card { padding: var(--space-2); }
.card-label { font-size: 11px; margin-bottom: 4px; }
.card-value { font-size: 20px; font-weight: 600; margin-bottom: 2px; }
.section { margin-top: var(--space-2); }
.section-title { margin-bottom: var(--space-2); color: var(--text-secondary); }
.empty-state { padding: var(--space-4); text-align: center; }
.report-list { display: flex; flex-direction: column; gap: var(--space-1); }
.report-item { padding: var(--space-2); }
.report-meta { display: flex; align-items: center; gap: var(--space-2); margin-bottom: 4px; }
.report-summary { font-size: 12px; color: var(--text-primary); line-height: 1.5; }
</style>
