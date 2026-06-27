<script setup lang="ts">
const props = defineProps<{ showToast?: (msg: string, type: 'success' | 'error' | 'info') => void }>()
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const config = ref<any>(null)
const installedTasks = ref<string[]>([])
const loading = ref(true)
const error = ref('')
const installing = ref(false)
const uninstalling = ref(false)
const cleanupDays = ref(30)
const cleanupResult = ref<string>('')
const cleanupLoading = ref(false)

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.getScheduler()
    config.value = res.config
    installedTasks.value = res.installed_tasks || []
  } catch (e: any) {
    error.value = '获取定时任务失败: ' + (e.message || '未知错误')
  } finally {
    loading.value = false
  }
}

async function installTask() {
  const timeInput = prompt('输入执行时间 (HH:MM 格式，如 08:00):', '08:00')
  if (!timeInput) return

  // 简单格式校验
  if (!/^\d{2}:\d{2}$/.test(timeInput.trim())) {
    props.showToast?.('时间格式错误，请使用 HH:MM 格式', 'error')
    return
  }

  installing.value = true
  try {
    const res = await api.installScheduler(timeInput.trim())
    if (res.success) {
      props.showToast?.('定时任务已安装', 'success')
      await loadData()
    } else {
      props.showToast?.('安装失败', 'error')
    }
  } catch (e: any) {
    props.showToast?.('安装失败: ' + (e.message || '未知错误'), 'error')
  } finally {
    installing.value = false
  }
}

async function uninstallAll() {
  if (!confirm('确定要卸载所有定时任务吗？')) return
  uninstalling.value = true
  try {
    const res = await api.uninstallScheduler()
    if (res.success) {
      props.showToast?.('定时任务已卸载', 'success')
      await loadData()
    } else {
      props.showToast?.('卸载失败', 'error')
    }
  } catch (e: any) {
    props.showToast?.('卸载失败: ' + (e.message || '未知错误'), 'error')
  } finally {
    uninstalling.value = false
  }
}

async function runCleanup() {
  if (!confirm(`确定要清理 ${cleanupDays.value} 天前的数据吗？此操作不可恢复。`)) return
  cleanupLoading.value = true
  cleanupResult.value = ''
  try {
    const res = await api.cleanupData(cleanupDays.value)
    if (res.success) {
      const d = res.details
      cleanupResult.value = `已清理：${d.reports_deleted} 条日报、${d.logs_deleted} 条日志、${d.camouflage_deleted} 条伪装素材`
      props.showToast?.('数据清理完成', 'success')
    } else {
      props.showToast?.('清理失败', 'error')
    }
  } catch (e: any) {
    props.showToast?.('清理失败: ' + (e.message || '未知错误'), 'error')
  } finally {
    cleanupLoading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>定时任务</h2>
      <div class="header-actions">
        <button class="btn btn-primary" :disabled="installing" @click="installTask">
          {{ installing ? '安装中...' : '安装定时任务' }}
        </button>
        <button class="btn btn-danger" :disabled="uninstalling || installedTasks.length === 0" @click="uninstallAll">
          {{ uninstalling ? '卸载中...' : '卸载所有任务' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-text text-dim">加载中...</div>
    <div v-else-if="error" class="error-box glass-card">
      <span class="tag tag-danger">错误</span>
      <span>{{ error }}</span>
    </div>
    <div v-else class="scheduler-content">
      <!-- 状态卡片 -->
      <div class="cards-grid">
        <div class="glass-card status-card">
          <div class="card-label text-dim">启用状态</div>
          <div class="card-value">
            <span class="tag" :class="config?.enabled ? 'tag-success' : 'tag-warning'">
              {{ config?.enabled ? '已启用' : '未启用' }}
            </span>
          </div>
        </div>
        <div class="glass-card status-card">
          <div class="card-label text-dim">自动启动</div>
          <div class="card-value">
            <span class="tag" :class="config?.auto_start ? 'tag-success' : 'tag-warning'">
              {{ config?.auto_start ? '是' : '否' }}
            </span>
          </div>
        </div>
        <div class="glass-card status-card">
          <div class="card-label text-dim">执行时间</div>
          <div class="card-value">{{ config?.time || '--' }}</div>
          <div class="card-sub text-sm text-dim" v-if="config?.weekdays">
            {{ '每周: ' + (Array.isArray(config.weekdays) ? config.weekdays.join(', ') : config.weekdays) }}
          </div>
        </div>
      </div>

      <!-- 已安装任务 -->
      <div class="section">
        <h3 class="section-title text-dim">已安装任务</h3>
        <div v-if="installedTasks.length === 0" class="empty-state glass-card">
          <span class="text-dim">暂无已安装的定时任务</span>
        </div>
        <div v-else class="task-list">
          <div v-for="task in installedTasks" :key="task" class="glass-card task-item">
            <span class="task-icon">◷</span>
            <span class="task-name">{{ task }}</span>
          </div>
        </div>
      </div>

      <!-- 数据清理 -->
      <div class="section">
        <h3 class="section-title text-dim">数据维护</h3>
        <div class="glass-card cleanup-card">
          <div class="cleanup-row">
            <div class="cleanup-info">
              <span class="text-dim">清理历史数据</span>
              <span class="text-dim text-sm">删除指定天数前的日报和日志记录（不可恢复）</span>
            </div>
            <div class="cleanup-form">
              <label class="cleanup-label text-dim text-sm">
                保留
                <select v-model.number="cleanupDays" class="cleanup-select">
                  <option :value="7">7天</option>
                  <option :value="30">30天</option>
                  <option :value="90">90天</option>
                  <option :value="180">180天</option>
                </select>
                前的数据
              </label>
              <button class="btn btn-danger" :disabled="cleanupLoading" @click="runCleanup">
                {{ cleanupLoading ? '清理中...' : '执行清理' }}
              </button>
            </div>
          </div>
          <div v-if="cleanupResult" class="cleanup-result fade-in">
            <span class="tag tag-success">完成</span>
            <span>{{ cleanupResult }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { padding: var(--space-2); }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: var(--space-3); flex-wrap: wrap; gap: var(--space-2); }
.page-header h2 { margin: 0; }
.header-actions { display: flex; gap: var(--space-2); }
.loading-text { padding: var(--space-4); text-align: center; }
.error-box { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2); }
.cards-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-2); margin-bottom: var(--space-3); }
.status-card { padding: var(--space-2); }
.card-label { font-size: 11px; margin-bottom: 4px; }
.card-value { font-size: 16px; font-weight: 600; margin-bottom: 2px; }
.section { margin-top: var(--space-2); }
.section-title { margin-bottom: var(--space-2); }
.empty-state { padding: var(--space-3); text-align: center; }
.task-list { display: flex; flex-wrap: wrap; gap: var(--space-1); }
.task-item { display: flex; align-items: center; gap: var(--space-2); padding: 6px 14px; }
.task-icon { color: var(--accent); }
.task-name { font-size: 12px; }

.cleanup-card { padding: var(--space-2); }
.cleanup-row { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--space-2); flex-wrap: wrap; }
.cleanup-info { display: flex; flex-direction: column; gap: 2px; }
.cleanup-form { display: flex; align-items: center; gap: var(--space-2); }
.cleanup-label { display: flex; align-items: center; gap: var(--space-1); }
.cleanup-select { width: 64px; padding: 4px 6px; font-size: 11px; }
.cleanup-result { display: flex; align-items: center; gap: var(--space-2); margin-top: var(--space-2); font-size: 12px; }
</style>
