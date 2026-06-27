<script setup lang="ts">
import { ref, computed, onMounted, h, defineComponent, type PropType } from 'vue'
import { api } from '../api/client'

const props = defineProps<{ showToast?: (msg: string, type: 'success' | 'error' | 'info') => void }>()

const configData = ref<any>(null)
const loading = ref(true)
const error = ref('')
const editMode = ref(false)
const editText = ref('')
const saving = ref(false)
const toggling = ref<string | null>(null)

// 提取已启用的平台列表（含 auto_push 状态）
const platforms = computed(() => {
  const raw = configData.value?.platforms
  if (!raw || typeof raw !== 'object') return []
  return Object.entries(raw)
    .filter(([_, v]: [string, any]) => v && typeof v === 'object' && v.ai_model)
    .map(([name, cfg]: [string, any]) => ({
      name,
      autoPush: cfg.auto_push !== false,
    }))
})

async function toggleAutoPush(name: string, enabled: boolean) {
  toggling.value = name
  try {
    const res = await api.updateConfig({
      platforms: { [name]: { auto_push: enabled } },
    })
    if (res.success) {
      // 更新本地数据
      if (configData.value?.platforms?.[name]) {
        configData.value.platforms[name].auto_push = enabled
      }
      props.showToast?.(`${name} 自动推送已${enabled ? '开启' : '关闭'}`, 'success')
    } else {
      props.showToast?.('保存失败', 'error')
    }
  } catch (e: any) {
    props.showToast?.('保存失败: ' + (e.message || '未知错误'), 'error')
  } finally {
    toggling.value = null
  }
}

async function loadConfig() {
  loading.value = true
  error.value = ''
  try {
    configData.value = await api.getConfig()
  } catch (e: any) {
    error.value = '获取配置失败: ' + (e.message || '未知错误')
  } finally {
    loading.value = false
  }
}

function enterEdit() {
  editText.value = JSON.stringify(configData.value, null, 2)
  editMode.value = true
}

function cancelEdit() {
  editMode.value = false
  editText.value = ''
}

async function saveConfig() {
  saving.value = true
  try {
    const parsed = JSON.parse(editText.value)
    const res = await api.updateConfig(parsed)
    if (res.success) {
      configData.value = parsed
      editMode.value = false
      props.showToast?.('配置已保存', 'success')
    } else {
      props.showToast?.('保存失败: ' + (res.message || '未知错误'), 'error')
    }
  } catch (e: any) {
    props.showToast?.('保存失败: ' + (e.message || 'JSON 格式错误'), 'error')
  } finally {
    saving.value = false
  }
}

function isSensitive(key: string): boolean {
  const sensitiveKeys = ['key', 'secret', 'password', 'token', 'auth', 'credential']
  return sensitiveKeys.some(s => key.toLowerCase().includes(s))
}

// 展开状态管理
const expanded = ref<Set<string>>(new Set(['root']))

function togglePath(path: string) {
  if (expanded.value.has(path)) {
    expanded.value.delete(path)
  } else {
    expanded.value.add(path)
  }
}

// 递归树节点组件
interface NodeData {
  key: string
  val: any
  path: string
  depth: number
}

const TreeNode = defineComponent({
  name: 'TreeNode',
  props: {
    data: { type: Object as PropType<NodeData>, required: true },
  },
  setup(props) {
    return () => {
      const { key, val, path, depth } = props.data
      const nodePath = path + '/' + key
      const isObj = val !== null && typeof val === 'object'
      const paddingLeft = depth * 16

      if (isObj) {
        const isArr = Array.isArray(val)
        const keys = val ? Object.keys(val) : []
        const isExp = expanded.value.has(nodePath)

        return h('div', { style: { lineHeight: '1.8' } }, [
          h('div', { style: { paddingLeft: paddingLeft + 'px' } }, [
            h('span', {
              style: { cursor: 'pointer', userSelect: 'none', marginRight: '4px', color: 'var(--text-secondary)' },
              onClick: () => togglePath(nodePath),
            }, isExp ? '▾' : '▸'),
            h('span', { style: { color: '#6ab0f0', marginRight: '4px' } }, key + ':'),
            h('span', {
              class: 'text-dim',
              style: { fontSize: '11px', marginLeft: '4px' },
            }, isArr ? '[' + val.length + ']' : '{' + keys.length + '}'),
          ]),
          isExp ? h('div',
            keys.map((k: string) => h(TreeNode, {
              data: { key: k, val: val[k], path: nodePath, depth: depth + 1 },
            }))
          ) : null,
        ])
      }

      // 叶子节点
      const displayVal = val === null ? 'null'
        : typeof val === 'string'
          ? '"' + (isSensitive(key) ? '****' : val) + '"'
          : String(val)

      const valColor = val === null ? 'var(--text-dim)'
        : typeof val === 'string' ? '#e8c96a'
        : typeof val === 'number' ? '#6ae89a'
        : typeof val === 'boolean' ? '#c97ae8'
        : 'var(--text-primary)'

      return h('div', { style: { paddingLeft: paddingLeft + 'px', lineHeight: '1.8' } }, [
        h('span', { style: { color: '#6ab0f0', marginRight: '4px' } }, key + ':'),
        h('span', {
          style: val === null ? { color: valColor, fontStyle: 'italic' } : { color: valColor },
        }, displayVal),
      ])
    }
  },
})

onMounted(loadConfig)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>配置</h2>
      <button v-if="!editMode" class="btn btn-ghost" @click="enterEdit">编辑配置</button>
    </div>

    <div v-if="loading" class="loading-text text-dim">加载中...</div>
    <div v-else-if="error" class="error-box glass-card">
      <span class="tag tag-danger">错误</span>
      <span>{{ error }}</span>
    </div>

    <!-- 只读树形模式 -->
    <div v-else-if="!editMode">
      <!-- 快捷设置：auto_push 开关 -->
      <div v-if="platforms.length > 0" class="quick-settings glass-card">
        <div class="quick-title text-dim text-sm">快捷设置</div>
        <div v-for="p in platforms" :key="p.name" class="quick-row">
          <div class="quick-info">
            <span class="quick-label">{{ p.name }}</span>
            <span class="quick-desc text-dim text-sm">自动推送日报到{{ p.name === 'feishu' ? '飞书' : p.name }}</span>
          </div>
          <label class="toggle-switch" :class="{ disabled: toggling === p.name }">
            <input type="checkbox" :checked="p.autoPush" :disabled="toggling === p.name"
              @change="toggleAutoPush(p.name, ($event.target as HTMLInputElement).checked)" />
            <span class="toggle-slider"></span>
          </label>
        </div>
      </div>
      <div class="config-tree glass-card">
        <div class="tree-root">
          <TreeNode
            v-for="key in Object.keys(configData || {})" :key="key"
            :data="{ key, val: configData[key], path: 'root', depth: 0 }"
          />
        </div>
      </div>
    </div>

    <!-- 编辑模式 -->
    <div v-else class="edit-area glass-card">
      <textarea v-model="editText" class="config-textarea" spellcheck="false"></textarea>
      <div class="edit-actions">
        <button class="btn btn-ghost" @click="cancelEdit">取消</button>
        <button class="btn btn-primary" :disabled="saving" @click="saveConfig">
          {{ saving ? '保存中...' : '保存' }}
        </button>
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
.config-tree { padding: var(--space-2); max-height: calc(100vh - 150px); overflow-y: auto; }
.tree-root { font-size: 12px; }

/* 快捷设置 */
.quick-settings { padding: var(--space-2); margin-bottom: var(--space-2); }
.quick-title { margin-bottom: var(--space-2); letter-spacing: 0.3px; }
.quick-row { display: flex; align-items: center; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--glass-border); }
.quick-row:last-child { border-bottom: none; }
.quick-info { display: flex; flex-direction: column; gap: 1px; }
.quick-label { font-size: 12px; font-weight: 500; }
.quick-desc { font-size: 10px; }

/* Toggle 开关 */
.toggle-switch { position: relative; display: inline-block; width: 36px; height: 20px; flex-shrink: 0; }
.toggle-switch input { opacity: 0; width: 0; height: 0; }
.toggle-slider {
  position: absolute; cursor: pointer; inset: 0;
  background: rgba(128,138,152,0.2);
  border-radius: 20px; transition: var(--transition-fast);
}
.toggle-slider::before {
  content: ''; position: absolute; width: 16px; height: 16px;
  left: 2px; bottom: 2px; background: var(--text-dim);
  border-radius: 50%; transition: var(--transition-fast);
}
.toggle-switch input:checked + .toggle-slider { background: var(--accent-glow); }
.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(16px); background: var(--accent);
}
.toggle-switch.disabled { opacity: 0.4; pointer-events: none; }
.edit-area { padding: var(--space-2); }
.config-textarea { width: 100%; min-height: 400px; font-family: var(--font-mono); font-size: 12px; padding: var(--space-2); resize: vertical; }
.edit-actions { display: flex; gap: var(--space-2); justify-content: flex-end; margin-top: var(--space-2); }
</style>
