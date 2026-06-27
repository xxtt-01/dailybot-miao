<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const config = ref<any>(null)
const installedTasks = ref<string[]>([])
const loading = ref(true)
const error = ref('')
const installing = ref(false)
const uninstalling = ref(false)

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
    alert('时间格式错误，请使用 HH:MM 格式 (如 08:00)')
    return
  }

  installing.value = true
  try {
    const res = await api.installScheduler(timeInput.trim())
    if (res.success) {
      alert('定时任务已安装')
      await loadData()
    } else {
      alert('安装失败')
    }
  } catch (e: any) {
    alert('安装失败: ' + (e.message || '未知错误'))
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
      alert('定时任务已卸载')
      await loadData()
    } else {
      alert('卸载失败')
    }
  } catch (e: any) {
    alert('卸载失败: ' + (e.message || '未知错误'))
  } finally {
    uninstalling.value = false
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
</style>
