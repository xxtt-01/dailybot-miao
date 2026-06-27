<script setup lang="ts">
const props = defineProps<{ showToast?: (msg: string, type: 'success' | 'error' | 'info') => void }>()
import { ref, onMounted } from 'vue'
import { api, type SourceInfo } from '../api/client'

const sources = ref<SourceInfo[]>([])
const loading = ref(true)
const error = ref('')
const formPlatform = ref('github')
const formPath = ref('')
const formBranch = ref('main')
const adding = ref(false)

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.getSources()
    sources.value = res.sources || []
  } catch (e: any) {
    error.value = '获取采集源失败: ' + (e.message || '未知错误')
  } finally {
    loading.value = false
  }
}

async function addSource() {
  if (!formPath.value.trim()) {
    props.showToast?.('请输入仓库路径', 'error')
    return
  }
  adding.value = true
  try {
    const res = await api.addSource(formPlatform.value, formPath.value.trim(), formBranch.value.trim())
    if (res.success) {
      formPath.value = ''
      formBranch.value = 'main'
      await loadData()
    } else {
      props.showToast?.('添加失败', 'error')
    }
  } catch (e: any) {
    props.showToast?.('添加失败: ' + (e.message || '未知错误'), 'error')
  } finally {
    adding.value = false
  }
}

async function deleteSource(platform: string, index: number) {
  if (!confirm(`确定要删除 ${platform} 的仓库 #${index + 1} 吗？`)) return
  try {
    const res = await api.deleteSource(platform, index)
    if (res.success) {
      await loadData()
    } else {
      props.showToast?.('删除失败', 'error')
    }
  } catch (e: any) {
    props.showToast?.('删除失败: ' + (e.message || '未知错误'), 'error')
  }
}

const platforms = ['github', 'gitee']

onMounted(loadData)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>采集源</h2>
      <button class="btn btn-ghost" @click="loadData" :disabled="loading">
        {{ loading ? '加载中...' : '刷新' }}
      </button>
    </div>

    <div v-if="loading" class="loading-text text-dim">加载中...</div>
    <div v-else-if="error" class="error-box glass-card">
      <span class="tag tag-danger">错误</span>
      <span>{{ error }}</span>
    </div>
    <div v-else class="sources-grid">
      <div v-for="src in sources" :key="src.platform" class="glass-card source-card">
        <div class="source-header">
          <span class="source-platform">{{ src.platform }}</span>
          <span class="tag" :class="src.enabled ? 'tag-success' : 'tag-warning'">
            {{ src.enabled ? '已启用' : '未启用' }}
          </span>
        </div>
        <div class="source-repos" v-if="src.repos && src.repos.length > 0">
          <div v-for="(repo, idx) in src.repos" :key="idx" class="repo-item">
            <div class="repo-info">
              <span class="repo-path">{{ repo.path }}</span>
              <span class="repo-branch tag tag-accent text-sm">{{ repo.branch }}</span>
            </div>
            <button class="btn btn-danger btn-sm" @click="deleteSource(src.platform, idx)">删除</button>
          </div>
        </div>
        <div v-else class="text-dim text-sm" style="padding: var(--space-1) 0;">暂无仓库</div>
        <div class="source-count text-dim text-sm">共 {{ src.repo_count }} 个仓库</div>
      </div>

      <!-- 添加表单 -->
      <div class="glass-card add-card">
        <div class="source-header">
          <span class="text-dim">添加仓库</span>
        </div>
        <div class="add-form">
          <div class="form-row">
            <label class="form-label text-dim text-sm">平台</label>
            <select v-model="formPlatform">
              <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
            </select>
          </div>
          <div class="form-row">
            <label class="form-label text-dim text-sm">仓库路径</label>
            <input type="text" v-model="formPath" placeholder="owner/repo" />
          </div>
          <div class="form-row">
            <label class="form-label text-dim text-sm">分支</label>
            <input type="text" v-model="formBranch" placeholder="main" />
          </div>
          <button class="btn btn-primary" :disabled="adding" @click="addSource">
            {{ adding ? '添加中...' : '添加' }}
          </button>
        </div>
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
.sources-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: var(--space-2); }
.source-card, .add-card { padding: var(--space-2); }
.source-header { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); }
.source-platform { font-size: 14px; font-weight: 600; }
.source-repos { display: flex; flex-direction: column; gap: 4px; margin-bottom: var(--space-1); }
.repo-item { display: flex; align-items: center; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid var(--glass-border); }
.repo-item:last-child { border-bottom: none; }
.repo-info { display: flex; align-items: center; gap: var(--space-2); }
.repo-path { font-size: 12px; }
.repo-branch { font-size: 10px; padding: 1px 6px; }
.btn-sm { padding: 3px 10px; font-size: 11px; }
.add-form { display: flex; flex-direction: column; gap: var(--space-1); }
.form-row { display: flex; align-items: center; gap: var(--space-2); }
.form-label { min-width: 64px; flex-shrink: 0; }
.add-form input, .add-form select { flex: 1; }
</style>
