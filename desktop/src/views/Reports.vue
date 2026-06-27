<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { api, type Report } from '../api/client'

const props = defineProps<{ showToast?: (msg: string, type: 'success' | 'error' | 'info') => void }>()

const dateFilter = ref(new Date().toISOString().slice(0, 10))
const platformFilter = ref('')
const searchQuery = ref('')
const reports = ref<Report[]>([])
const loading = ref(false)
const error = ref('')
const detailReport = ref<Report | null>(null)
const showDetail = ref(false)

async function loadReports() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.getReports(dateFilter.value || undefined, platformFilter.value || undefined, searchQuery.value || undefined)
    reports.value = res.reports || []
  } catch (e: any) {
    error.value = '获取日报列表失败: ' + (e.message || '未知错误')
    reports.value = []
  } finally {
    loading.value = false
  }
}

async function openDetail(id: number) {
  try {
    const res = await api.getReportDetail(id)
    detailReport.value = res.report
    showDetail.value = true
  } catch (e: any) {
    props.showToast?.('获取详情失败: ' + (e.message || '未知错误'), 'error')
  }
}

function closeDetail() {
  showDetail.value = false
  detailReport.value = null
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && showDetail.value) {
    closeDetail()
  }
}

function exportCSV() {
  if (reports.value.length === 0) {
    props.showToast?.('没有可导出的数据', 'info')
    return
  }
  const headers = ['日期', '平台', '类型', '摘要', '创建时间']
  const rows = reports.value.map(r => [
    r.date,
    r.platform,
    r.is_camouflage ? '伪装' : '正常',
    `"${(r.summary || '').replace(/"/g, '""')}"`,
    r.created_at || '',
  ])
  const csv = '﻿' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `日报_${dateFilter.value || '全部'}.csv`
  a.click()
  URL.revokeObjectURL(url)
  props.showToast?.('CSV 已导出', 'success')
}

onMounted(() => {
  loadReports()
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div class="page" @keydown.escape="closeDetail">
    <div class="page-header">
      <h2>日报历史</h2>
      <div class="filters">
        <label class="filter-item">
          <span class="text-dim text-sm">日期</span>
          <input type="date" v-model="dateFilter" @change="loadReports" />
        </label>
        <label class="filter-item">
          <span class="text-dim text-sm">平台</span>
          <input type="text" v-model="platformFilter" placeholder="全部" @change="loadReports" />
        </label>
        <label class="filter-item">
          <span class="text-dim text-sm">搜索</span>
          <input type="text" v-model="searchQuery" placeholder="关键词…" @change="loadReports" />
        </label>
        <button class="btn btn-ghost" @click="loadReports" :disabled="loading">
          {{ loading ? '加载中...' : '刷新' }}
        </button>
        <button class="btn btn-ghost" @click="exportCSV" :disabled="reports.length === 0">
          导出 CSV
        </button>
      </div>
    </div>

    <div v-if="error" class="error-box glass-card">
      <span class="tag tag-danger">错误</span>
      <span>{{ error }}</span>
    </div>

    <div class="table-wrap glass-card" v-else>
      <table class="data-table" v-if="reports.length > 0">
        <thead>
          <tr>
            <th>时间</th>
            <th>平台</th>
            <th>摘要</th>
            <th>类型</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in reports" :key="r.id">
            <td class="text-dim text-sm">{{ r.created_at?.slice(11, 19) || r.date }}</td>
            <td>{{ r.platform }}</td>
            <td class="summary-cell">{{ r.summary?.slice(0, 80) }}{{ r.summary?.length > 80 ? '...' : '' }}</td>
            <td>
              <span class="tag" :class="r.is_camouflage ? 'tag-warning' : 'tag-info'">
                {{ r.is_camouflage ? '伪装' : '正常' }}
              </span>
            </td>
            <td>
              <button class="btn btn-ghost" @click="openDetail(r.id)">详情</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">
        <span class="text-dim">暂无记录</span>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <Teleport to="body">
      <div v-if="showDetail" class="modal-overlay" @click.self="closeDetail">
        <div class="modal-content glass-card">
          <div class="modal-header">
            <h3>日报详情</h3>
            <button class="btn btn-ghost" @click="closeDetail">✕</button>
          </div>
          <div class="modal-body" v-if="detailReport">
            <div class="detail-field">
              <span class="text-dim">日期</span>
              <span>{{ detailReport.date }}</span>
            </div>
            <div class="detail-field">
              <span class="text-dim">平台</span>
              <span>{{ detailReport.platform }}</span>
            </div>
            <div class="detail-field">
              <span class="text-dim">类型</span>
              <span class="tag" :class="detailReport.is_camouflage ? 'tag-warning' : 'tag-info'">
                {{ detailReport.is_camouflage ? '伪装' : '正常' }}
              </span>
            </div>
            <div class="detail-field">
              <span class="text-dim">摘要</span>
              <div class="detail-text">{{ detailReport.summary }}</div>
            </div>
            <div class="detail-field" v-if="detailReport.raw_data">
              <span class="text-dim">原始数据</span>
              <pre class="detail-raw">{{ detailReport.raw_data }}</pre>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.page { padding: var(--space-2); }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: var(--space-3); flex-wrap: wrap; gap: var(--space-2); }
.page-header h2 { margin: 0; }
.filters { display: flex; align-items: flex-end; gap: var(--space-2); flex-wrap: wrap; }
.filter-item { display: flex; flex-direction: column; gap: 2px; }
.error-box { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2); }
.table-wrap { overflow-x: auto; padding: 0; }
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th { text-align: left; padding: 10px 12px; color: var(--text-dim); font-weight: 500; border-bottom: 1px solid var(--glass-border); }
.data-table td { padding: 8px 12px; border-bottom: 1px solid var(--glass-border); }
.data-table tr:last-child td { border-bottom: none; }
.summary-cell { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty-state { padding: var(--space-4); text-align: center; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { width: 560px; max-width: 90vw; max-height: 80vh; display: flex; flex-direction: column; padding: var(--space-3); }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2); }
.modal-body { overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: var(--space-2); }
.detail-field { display: flex; flex-direction: column; gap: 4px; }
.detail-text { font-size: 12px; line-height: 1.6; white-space: pre-wrap; }
.detail-raw { background: rgba(0,0,0,0.3); padding: var(--space-2); border-radius: var(--radius-sm); font-size: 11px; max-height: 200px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }
</style>
