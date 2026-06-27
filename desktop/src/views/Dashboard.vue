<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type Report, type SystemStatus } from '../api/client'

defineProps<{ showToast?: (msg: string, type: 'success' | 'error' | 'info') => void }>()

const status = ref<SystemStatus | null>(null)
const versionInfo = ref<any>(null)
const reports = ref<Report[]>([])
const loading = ref(true)
const error = ref('')
const reportLoading = ref(false)
const warnings = ref<string[]>([])

async function loadAll() {
  try {
    const [st, v] = await Promise.all([
      api.getStatus().catch(() => null),
      api.getDesktopVersion().catch(() => null),
    ])
    status.value = st
    versionInfo.value = v
    if (st) {
      const today = new Date().toISOString().slice(0, 10)
      const res = await api.getReports(today).catch(() => null)
      reports.value = (res?.reports || []).slice(0, 7)
    }

    // 环境配置自检
    const cfg = await api.getConfig().catch(() => null)
    const warns: string[] = []
    if (cfg) {
      if (!cfg.crawler_sources || Object.keys(cfg.crawler_sources).length === 0) {
        warns.push('未配置采集源，请前往「采集源」添加仓库')
      }
      if (!cfg.providers || Object.keys(cfg.providers).length === 0) {
        warns.push('未配置 AI 供应商，请检查 config.yaml')
      }
      if (!cfg.workflows?.feishu?.webhook_url && !cfg.workflows?.feishu?.app_id) {
        warns.push('未配置飞书推送，日报生成后不会推送消息')
      }
    }
    if (!st) {
      warns.push('后端服务未连接，部分功能不可用')
    }
    warnings.value = warns
  } catch {
    error.value = '无法连接后端服务'
  }
  loading.value = false
}

async function triggerReport() {
  reportLoading.value = true
  try {
    await api.triggerReport()
    await loadAll()
  } catch (e: any) {
    error.value = '触发失败: ' + (e.message || '未知错误')
  } finally {
    reportLoading.value = false
  }
}

onMounted(loadAll)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>概览</h2>
      <button class="btn btn-primary" :disabled="reportLoading" @click="triggerReport">
        <span v-if="reportLoading" class="btn-spinner"></span>
        {{ reportLoading ? '执行中...' : '▶ 执行日报' }}
      </button>
    </div>

    <!-- 版本更新 -->
    <div v-if="versionInfo?.has_update" class="update-banner glass-card fade-in">
      <span>📦 新版本 {{ versionInfo.latest_version }} 可用</span>
      <a :href="versionInfo.download_url" class="btn btn-ghost" target="_blank">下载</a>
    </div>

    <!-- 环境警告 -->
    <div v-if="warnings.length > 0" class="warnings-section">
      <div v-for="(w, i) in warnings" :key="i" class="warning-item glass-card fade-in">
        <span class="tag tag-warning">注意</span>
        <span>{{ w }}</span>
      </div>
    </div>

    <!-- 骨架屏 -->
    <div v-if="loading" class="cards-grid">
      <div v-for="i in 4" :key="i" class="glass-card status-card">
        <div class="skeleton" style="width:40px;height:11px;margin-bottom:8px"></div>
        <div class="skeleton" style="width:80px;height:22px"></div>
      </div>
    </div>

    <!-- 错误 -->
    <div v-else-if="error" class="glass-card" style="display:flex;align-items:center;gap:12px;padding:16px">
      <span class="tag tag-danger">错误</span>
      <span>{{ error }}</span>
    </div>

    <!-- 状态卡片 -->
    <div v-else class="cards-grid">
      <div class="glass-card status-card">
        <div class="card-glow" style="background:var(--accent)"></div>
        <div class="card-label">版本</div>
        <div class="card-value">{{ status?.version || '--' }}</div>
      </div>
      <div class="glass-card status-card">
        <div class="card-glow" style="background:var(--info)"></div>
        <div class="card-label">工作流</div>
        <div class="card-value">{{ (status?.enabled_workflows || []).length }}</div>
        <div class="card-sub">{{ (status?.enabled_workflows || []).join(', ') || '无' }}</div>
      </div>
      <div class="glass-card status-card">
        <div class="card-glow" style="background:var(--accent)"></div>
        <div class="card-label">AI 模型</div>
        <div class="card-value">{{ status?.platforms?.length || 0 }}</div>
        <div class="card-sub">{{ status?.platforms?.map(p => p.ai_model).filter(Boolean).join(', ') || '--' }}</div>
      </div>
      <div class="glass-card status-card">
        <div class="card-glow" style="background:var(--success)"></div>
        <div class="card-label">状态</div>
        <div class="card-value"><span class="tag tag-success">运行中</span></div>
        <div class="card-sub">{{ status?.time?.slice(11, 19) || '--' }}</div>
      </div>
    </div>

    <!-- 最近日报 -->
    <div class="section">
      <h3 class="section-title">今日日报</h3>
      <div v-if="!loading && reports.length === 0" class="glass-card" style="padding:32px;text-align:center">
        <div class="text-dim">暂无今日日报记录</div>
      </div>
      <div v-else class="report-list">
        <div v-for="r in reports" :key="r.id" class="glass-card report-item">
          <div class="report-top">
            <span class="tag" :class="r.is_camouflage ? 'tag-warning' : 'tag-info'">
              {{ r.is_camouflage ? '伪装' : '正常' }}
            </span>
            <span class="text-dim text-sm">{{ r.platform }}</span>
            <span class="text-dim text-sm">{{ r.created_at?.slice(11, 19) || r.date }}</span>
          </div>
          <div class="report-summary">{{ r.summary?.slice(0, 140) }}{{ r.summary?.length > 140 ? '…' : '' }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { padding: var(--space-2); }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-3); }
.page-header h2 { font-size: 16px; font-weight: 600; margin: 0; }

.btn-spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(26,30,36,0.2); border-top-color: #1a1e24;
  border-radius: 50%; animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.update-banner { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); padding: var(--space-2); margin-bottom: var(--space-3); border-left: 3px solid var(--accent); }

.warnings-section { display: flex; flex-direction: column; gap: var(--space-1); margin-bottom: var(--space-3); }
.warning-item { display: flex; align-items: center; gap: var(--space-2); padding: 10px 14px; border-left: 3px solid var(--warning); font-size: 12px; }
.cards-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-2); margin-bottom: var(--space-3); }
@media (max-width: 900px) { .cards-grid { grid-template-columns: repeat(2, 1fr); } }

.status-card { padding: var(--space-2); position: relative; overflow: hidden; }
.card-glow {
  position: absolute; top: -60%; right: -40%;
  width: 120px; height: 120px;
  border-radius: 50%; filter: blur(40px); opacity: 0.08;
  transition: var(--transition-slow); pointer-events: none;
}
.status-card:hover .card-glow { opacity: 0.18; transform: scale(1.3); }
.card-label { font-size: 11px; color: var(--text-dim); margin-bottom: 6px; letter-spacing: 0.3px; }
.card-value { font-size: 22px; font-weight: 600; margin-bottom: 2px; }
.card-sub { font-size: 11px; color: var(--text-dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.section { margin-top: var(--space-2); }
.section-title { font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: var(--space-2); }
.report-list { display: flex; flex-direction: column; gap: var(--space-1); }
.report-item { padding: var(--space-2); }
.report-top { display: flex; align-items: center; gap: var(--space-2); margin-bottom: 6px; }
.report-summary { font-size: 12px; line-height: 1.6; color: var(--text-secondary); }
</style>
