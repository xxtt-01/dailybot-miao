<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api/client'

const props = defineProps<{
  date: string
  onClose: () => void
  onSaved: () => void
  showToast?: (msg: string, type: 'success' | 'error' | 'info') => void
}>()

const content = ref('')
const project = ref('')
const workType = ref('')
const saving = ref(false)

const workTypeOptions = [
  '编码开发', '接口对接', '数据抓取/采集', '数据清洗/ETL',
  'BUG修复', '问题排查', '性能优化', '代码审查/重构',
  '测试验证', '需求分析', '系统设计', '技术调研/预研',
  '系统发布/部署', '系统维护', '自动化脚本', '文档编写',
  '会议沟通', '其它工作',
]

async function save() {
  if (!content.value.trim()) {
    props.showToast?.('请输入工作内容', 'error')
    return
  }
  saving.value = true
  try {
    await api.addExtraReport({
      date: props.date,
      content: content.value.trim(),
      project: project.value,
      work_type: workType.value,
    })
    props.showToast?.('已添加', 'success')
    props.onSaved()
    props.onClose()
  } catch (e: any) {
    props.showToast?.('保存失败: ' + (e.message || '未知错误'), 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="props.onClose">
      <div class="modal-content glass-card" style="width:520px;max-width:90vw">
        <div class="modal-header">
          <h3>补录今日工作</h3>
          <button class="btn btn-ghost" @click="props.onClose">✕</button>
        </div>
        <div class="modal-body" style="display:flex;flex-direction:column;gap:var(--space-2)">
          <div class="field">
            <label class="text-dim text-sm">工作内容 *</label>
            <textarea v-model="content" class="form-textarea" placeholder="描述你今天做了什么..." spellcheck="false" />
          </div>
          <div class="field-row">
            <div class="field" style="flex:1">
              <label class="text-dim text-sm">项目</label>
              <input v-model="project" class="form-input" placeholder="如: 对账系统" />
            </div>
            <div class="field" style="flex:1">
              <label class="text-dim text-sm">工作类型</label>
              <select v-model="workType" class="form-select">
                <option value="">不指定</option>
                <option v-for="t in workTypeOptions" :key="t" :value="t">{{ t }}</option>
              </select>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-ghost" @click="props.onClose">取消</button>
          <button class="btn btn-primary" :disabled="saving" @click="save">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2); }
.modal-body { overflow-y: auto; flex: 1; }
.modal-footer { display: flex; justify-content: flex-end; gap: var(--space-2); margin-top: var(--space-2); }
.field { display: flex; flex-direction: column; gap: 4px; }
.field-row { display: flex; gap: var(--space-2); }
.form-textarea { width: 100%; min-height: 120px; font-family: var(--font-mono); font-size: 12px; padding: var(--space-2); resize: vertical; }
.form-input { padding: 6px 10px; font-size: 12px; width:100%; }
.form-select { padding: 6px 10px; font-size: 12px; width:100%; }
</style>
