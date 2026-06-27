<!-- desktop/src/components/Toast.vue — 全局玻璃提示 -->
<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'

export interface ToastItem {
  id: number
  message: string
  type: 'success' | 'error' | 'info'
}

const toasts = ref<ToastItem[]>([])
let nextId = 0

function add(message: string, type: 'success' | 'error' | 'info' = 'info', duration = 3000) {
  const id = nextId++
  toasts.value.push({ id, message, type })
  setTimeout(() => {
    const el = document.getElementById(`toast-${id}`)
    if (el) {
      el.style.opacity = '0'
      el.style.transform = 'translateX(20px)'
      setTimeout(() => {
        toasts.value = toasts.value.filter(t => t.id !== id)
      }, 300)
    }
  }, duration)
}

function remove(id: number) {
  toasts.value = toasts.value.filter(t => t.id !== id)
}

defineExpose({ add })

// 全局快捷键 debug
onBeforeUnmount(() => { toasts.value = [] })
</script>

<template>
  <div class="toast-container">
    <div v-for="t in toasts" :key="t.id" :id="`toast-${t.id}`"
      :class="['toast', `toast-${t.type}`]">
      <span class="toast-icon">
        {{ t.type === 'success' ? '✓' : t.type === 'error' ? '✗' : 'ℹ' }}
      </span>
      <span class="toast-message">{{ t.message }}</span>
      <button class="toast-close" @click="remove(t.id)">✕</button>
    </div>
  </div>
</template>

<style scoped>
.toast-container {
  position: fixed; top: 48px; right: 16px; z-index: 9999;
  display: flex; flex-direction: column; gap: 8px;
  pointer-events: none;
}

.toast {
  pointer-events: auto;
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px;
  background: rgba(24, 28, 36, 0.88);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-sm);
  box-shadow: var(--glass-shadow);
  min-width: 260px;
  max-width: 380px;
  font-size: 12px;
  transition: opacity 0.3s ease, transform 0.3s ease;
  animation: toastIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.toast-success { border-left: 3px solid var(--success); }
.toast-error   { border-left: 3px solid var(--danger); }
.toast-info    { border-left: 3px solid var(--info); }

.toast-icon {
  width: 18px; height: 18px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 700; flex-shrink: 0;
}
.toast-success .toast-icon { background: rgba(78,199,127,0.2); color: var(--success); }
.toast-error .toast-icon   { background: rgba(240,106,123,0.2); color: var(--danger); }
.toast-info .toast-icon    { background: rgba(106,176,240,0.2); color: var(--info); }

.toast-message { flex: 1; color: var(--text-primary); }

.toast-close {
  background: none; border: none; color: var(--text-dim); cursor: pointer;
  font-size: 11px; padding: 2px; transition: var(--transition-fast);
}
.toast-close:hover { color: var(--text-primary); }

@keyframes toastIn {
  from { opacity: 0; transform: translateX(20px); }
  to   { opacity: 1; transform: translateX(0); }
}
</style>
