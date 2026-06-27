<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type CamouflageItem } from '../api/client'

const items = ref<CamouflageItem[]>([])
const loading = ref(true)
const error = ref('')

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.getCamouflage()
    items.value = res.items || []
  } catch (e: any) {
    error.value = '获取伪装素材失败: ' + (e.message || '未知错误')
  } finally {
    loading.value = false
  }
}

async function deleteItem(id: string, source: string) {
  if (!confirm(`确定要删除 "${source}" 的伪装素材吗？`)) return
  try {
    const res = await api.deleteCamouflage(id)
    if (res.success) {
      items.value = items.value.filter(i => i.id !== id)
    } else {
      alert('删除失败')
    }
  } catch (e: any) {
    alert('删除失败: ' + (e.message || '未知错误'))
  }
}

function truncate(text: string, max = 80): string {
  if (!text) return ''
  return text.length > max ? text.slice(0, max) + '...' : text
}

onMounted(loadData)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>伪装素材</h2>
      <button class="btn btn-ghost" @click="loadData" :disabled="loading">
        {{ loading ? '加载中...' : '刷新' }}
      </button>
    </div>

    <div v-if="loading" class="loading-text text-dim">加载中...</div>
    <div v-else-if="error" class="error-box glass-card">
      <span class="tag tag-danger">错误</span>
      <span>{{ error }}</span>
    </div>
    <div v-else class="table-wrap glass-card">
      <table class="data-table" v-if="items.length > 0">
        <thead>
          <tr>
            <th>ID</th>
            <th>来源项目</th>
            <th>内容预览</th>
            <th>平台</th>
            <th>最后使用</th>
            <th>变体数</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td class="text-dim text-sm">{{ item.id }}</td>
            <td>{{ item.source_name }}</td>
            <td class="preview-cell" :title="item.content_preview">{{ truncate(item.content_preview, 80) }}</td>
            <td>{{ item.platform }}</td>
            <td class="text-dim text-sm">{{ item.last_used || '--' }}</td>
            <td>{{ item.variants_count }}</td>
            <td>
              <button class="btn btn-danger btn-sm" @click="deleteItem(item.id, item.source_name)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">
        <span class="text-dim">暂无记录</span>
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
.table-wrap { overflow-x: auto; padding: 0; }
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th { text-align: left; padding: 10px 12px; color: var(--text-dim); font-weight: 500; border-bottom: 1px solid var(--glass-border); }
.data-table td { padding: 8px 12px; border-bottom: 1px solid var(--glass-border); }
.data-table tr:last-child td { border-bottom: none; }
.preview-cell { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.btn-sm { padding: 3px 10px; font-size: 11px; }
.empty-state { padding: var(--space-4); text-align: center; }
</style>
