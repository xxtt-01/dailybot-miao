<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { api, type Report } from '../api/client'

const props = defineProps<{ showToast?: (msg: string, type: 'success' | 'error' | 'info') => void }>()

const viewMode = ref<'history' | 'drafts'>('history')
const dateFilter = ref(new Date().toISOString().slice(0, 10))
const platformFilter = ref('')
const searchQuery = ref('')
const reports = ref<Report[]>([])
const drafts = ref<Report[]>([])
const loading = ref(false)
const error = ref('')
const detailReport = ref<Report | null>(null)
const showDetail = ref(false)

// 编辑草稿
const editingReport = ref<Report | null>(null)
const editSummary = ref('')
const editSaving = ref(false)
const showEditor = ref(false)

async function loadReports() {
  loading.value = true
  error.value = ''
  try {
    if (viewMode.value === 'history') {
      const res = await api.getReports(dateFilter.value || undefined, platformFilter.value || undefined, searchQuery.value || undefined)
      reports.value = res.reports || []
    } else {
      const res = await api.getDrafts()
      drafts.value = res.drafts || []
    }
  } catch (e: any) {
    error.value = '获取数据失败: ' + (e.message || '未知错误')
    if (viewMode.value === 'history') reports.value = []
    else drafts.value = []
  } finally {
    loading.value = false
  }
}

function switchView(mode: 'history' | 'drafts') {
  viewMode.value = mode
  loadReports()
}

// ── 详情 ──

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

// ── 编辑草稿 ──

function openEditor(r: Report) {
  editingReport.value = r
  editSummary.value = r.summary || ''
  showEditor.value = true
}

function closeEditor() {
  showEditor.value = false
  editingReport.value = null
  editSummary.value = ''
}

async function saveEdit() {
  if (!editingReport.value || !editSummary.value.trim()) return
  editSaving.value = true
  try {
    const res = await api.updateReport(editingReport.value.id, editSummary.value.trim())
    if (res.success) {
      props.showToast?.('已保存', 'success')
      closeEditor()
      loadReports()
    } else {
      props.showToast?.('保存失败', 'error')
    }
  } catch (e: any) {
    props.showToast?.('保存失败: ' + (e.message || '未知错误'), 'error')
  } finally {
    editSaving.value = false
  }
}

async function pushDraft(r: Report) {
  if (!confirm(`确定要推送这条日报到 ${r.platform} 吗？`)) return
  try {
    const res = await api.pushReport(r.id)
    if (res.success) {
      props.showToast?.('推送成功', 'success')
      loadReports()
    } else {
      props.showToast?.('推送失败: ' + (res.message || '未知错误'), 'error')
    }
  } catch (e: any) {
    props.showToast?.('推送失败: ' + (e.message || '未知错误'), 'error')
  }
}

function exportCSV() {
  if (reports.value.length === 0) {
    props.showToast?.('没有可导出的数据', 'info')
    return
  }
  const headers = ['日期', '平台', '类型', '状态', '摘要', '创建时间']
  const rows = reports.value.map(r => [
    r.date,
    r.platform,
    r.is_camouflage ? '伪装' : '正常',
    r.pushed ? '已推送' : '待推送',
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

// ── 键盘 ──

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    if (showEditor.value) { closeEditor(); return }
    if (showDetail.value) { closeDetail(); return }
  }
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
  <div class="page">
    <div class="page-header">
      <h2>日报历史</h2>
      <div class="header-actions">
        <div class="btn-group">
          <button class="btn" :class="viewMode === 'history' ? 'btn-primary' : 'btn-ghost'" @click="switchView('history')">历史</button>
          <button class="btn" :class="viewMode === 'drafts' ? 'btn-primary' : 'btn-ghost'" @click="switchView('drafts')">
            待推送
            <span v-if="drafts.length > 0" class="draft-badge">{{ drafts.length }}</span>
          </button>
        </div>
        <button class="btn btn-ghost" @click="loadReports" :disabled="loading">
          {{ loading ? '加载中...' : '刷新' }}
        </button>
        <button v-if="viewMode === 'history'" class="btn btn-ghost" @click="exportCSV" :disabled="reports.length === 0">
          导出 CSV
        </button>
      </div>
    </div>

    <!-- 筛选：历史模式 -->
    <div v-if="viewMode === 'history'" class="filters">
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
    </div>

    <div v-if="error" class="error-box glass-card">
      <span class="tag tag-danger">错误</span>
      <span>{{ error }}</span>
    </div>

    <!-- 历史列表 -->
    <div v-else-if="viewMode === 'history'" class="table-wrap glass-card">
      <table class="data-table" v-if="reports.length > 0">
        <thead>
          <tr>
            <th>时间</th>
            <th>平台</th>
            <th>摘要</th>
            <th>类型</th>
            <th>状态</th>
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
              <span v-if="r.pushed === 0" class="tag tag-warning">待推送</span>
              <span v-else class="tag tag-success">已推送</span>
            </td>
            <td class="actions-cell">
              <button class="btn btn-ghost" @click="openDetail(r.id)">详情</button>
              <button v-if="r.pushed === 0" class="btn btn-ghost" @click="openEditor(r)">编辑</button>
              <button v-if="r.pushed === 0" class="btn btn-success" @click="pushDraft(r)">推送</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">
        <span class="text-dim">暂无记录</span>
      </div>
    </div>

    <!-- 草稿列表 -->
    <div v-else class="drafts-section">
      <div v-if="drafts.length === 0" class="glass-card" style="padding:32px;text-align:center">
        <div class="text-dim">没有待推送的草稿</div>
      </div>
      <div v-else class="draft-list">
        <div v-for="r in drafts" :key="r.id" class="glass-card draft-item">
          <div class="draft-header">
            <span class="tag tag-warning">待推送</span>
            <span class="text-dim text-sm">{{ r.platform }}</span>
            <span class="text-dim text-sm">{{ r.date }}</span>
          </div>
          <div class="draft-summary">{{ r.summary?.slice(0, 200) }}{{ r.summary?.length > 200 ? '…' : '' }}</div>
          <div class="draft-actions">
            <button class="btn btn-ghost" @click="openEditor(r)">✏ 编辑</button>
            <button class="btn btn-success" @click="pushDraft(r)">▶ 推送</button>
          </div>
        </div>
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
              <span class="text-dim">状态</span>
              <span v-if="detailReport.pushed === 0" class="tag tag-warning">待推送</span>
              <span v-else class="tag tag-success">已推送</span>
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

    <!-- 编辑器弹窗 -->
    <Teleport to="body">
      <div v-if="showEditor" class="modal-overlay" @click.self="closeEditor">
        <div class="modal-content glass-card editor-modal">
          <div class="modal-header">
            <h3>编辑日报</h3>
            <button class="btn btn-ghost" @click="closeEditor">✕</button>
          </div>
          <div class="modal-body" v-if="editingReport">
            <div class="detail-field">
              <span class="text-dim">平台</span>
              <span>{{ editingReport.platform }}</span>
            </div>
            <div class="detail-field">
              <span class="text-dim">日期</span>
              <span>{{ editingReport.date }}</span>
            </div>
            <div class="detail-field">
              <span class="text-dim">摘要内容</span>
              <textarea v-model="editSummary" class="edit-textarea" spellcheck="false"></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-ghost" @click="closeEditor">取消</button>
            <button class="btn btn-primary" :disabled="editSaving || !editSummary.trim()" @click="saveEdit">
              {{ editSaving ? '保存中...' : '保存' }}
            </button>
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

/* 头部操作区 */
.header-actions { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.btn-group { display: flex; gap: 4px; }
.draft-badge {
  background: var(--warning); color: #1a1e24; font-size: 10px; font-weight: 700;
  padding: 0 5px; border-radius: 8px; line-height: 16px; min-width: 16px; text-align: center;
}

/* 操作列 */
.actions-cell { display: flex; gap: 4px; }

/* 草稿卡片 */
.draft-list { display: flex; flex-direction: column; gap: var(--space-1); }
.draft-item { padding: var(--space-2); }
.draft-header { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-1); }
.draft-summary { font-size: 12px; line-height: 1.6; color: var(--text-secondary); margin-bottom: var(--space-2); white-space: pre-wrap; }
.draft-actions { display: flex; gap: var(--space-1); }

/* 编辑器 */
.editor-modal { width: 640px; max-width: 90vw; }
.edit-textarea { width: 100%; min-height: 200px; font-family: var(--font-mono); font-size: 12px; padding: var(--space-2); resize: vertical; }
.modal-footer { display: flex; justify-content: flex-end; gap: var(--space-2); margin-top: var(--space-2); }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { width: 560px; max-width: 90vw; max-height: 80vh; display: flex; flex-direction: column; padding: var(--space-3); }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2); }
.modal-body { overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: var(--space-2); }
.detail-field { display: flex; flex-direction: column; gap: 4px; }
.detail-text { font-size: 12px; line-height: 1.6; white-space: pre-wrap; }
.detail-raw { background: rgba(0,0,0,0.3); padding: var(--space-2); border-radius: var(--radius-sm); font-size: 11px; max-height: 200px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }
</style>
