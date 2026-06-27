<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api/client'

const props = defineProps<{
  showToast?: (msg: string, type: 'success' | 'error' | 'info') => void
}>()

const emit = defineEmits<{ close: [] }>()

const question = ref('')
const answer = ref('')
const loading = ref(false)
const searched = ref(false)

const suggestions = [
  '上周做了什么工作？',
  '最近修复了哪些 Bug？',
  '哪个平台推送最多？',
  '伪装日报占比多少？',
  '我最近在哪个项目上投入最多？',
]

async function ask(q?: string) {
  const text = q || question.value
  if (!text.trim()) return
  loading.value = true
  answer.value = ''
  searched.value = false
  try {
    const res = await api.aiQuery(text.trim())
    answer.value = res.answer
    searched.value = true
  } catch (e: any) {
    answer.value = '查询失败: ' + (e.message || '未知错误')
  } finally {
    loading.value = false
  }
}

function selectSuggestion(s: string) {
  question.value = s
  ask(s)
}
</script>

<template>
  <div class="ai-assistant glass-card">
    <div class="ai-header">
      <span class="ai-title">AI 助手</span>
      <button class="btn btn-ghost btn-sm" @click="emit('close')">✕</button>
    </div>
    <div class="ai-body">
      <div v-if="!searched && !loading" class="ai-suggestions">
        <div class="text-dim text-sm" style="margin-bottom:8px">试试这些问题：</div>
        <div v-for="s in suggestions" :key="s" class="suggestion-chip" @click="selectSuggestion(s)">
          {{ s }}
        </div>
      </div>
      <div v-if="loading" class="ai-loading">
        <span class="text-dim text-sm">思考中...</span>
      </div>
      <div v-if="answer" class="ai-answer">{{ answer }}</div>
    </div>
    <div class="ai-footer">
      <input v-model="question" class="ai-input" placeholder="问问你的日报数据..." spellcheck="false"
        @keydown.enter="ask()" :disabled="loading" />
      <button class="btn btn-primary btn-sm" :disabled="loading || !question.trim()" @click="ask()">
        提问
      </button>
    </div>
  </div>
</template>

<style scoped>
.ai-assistant {
  position: fixed; bottom: 16px; right: 16px;
  width: 380px; max-height: 500px;
  display: flex; flex-direction: column;
  z-index: 999; padding: var(--space-2);
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
.ai-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2); }
.ai-title { font-size: 13px; font-weight: 600; }
.ai-body { flex: 1; overflow-y: auto; min-height: 80px; max-height: 320px; margin-bottom: var(--space-2); }
.ai-suggestions { display: flex; flex-direction: column; gap: 4px; }
.suggestion-chip {
  padding: 6px 10px; font-size: 11px; border-radius: var(--radius-sm);
  background: rgba(255,255,255,0.03); cursor: pointer; transition: var(--transition-fast);
  color: var(--text-secondary);
}
.suggestion-chip:hover { background: rgba(255,255,255,0.06); color: var(--text-primary); }
.ai-loading { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2); }
.ai-answer { font-size: 12px; line-height: 1.7; white-space: pre-wrap; padding: var(--space-1); color: var(--text-secondary); }
.ai-footer { display: flex; gap: var(--space-1); }
.ai-input { flex: 1; padding: 6px 10px; font-size: 12px; }
.btn-sm { padding: 3px 10px; font-size: 11px; }
</style>
