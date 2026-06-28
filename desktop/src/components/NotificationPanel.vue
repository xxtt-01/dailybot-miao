<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type Notification } from '../api/client'

const props = defineProps<{
  onClose: () => void
  showToast?: (msg: string, type: 'success' | 'error' | 'info') => void
}>()

const items = ref<Notification[]>([])
const loading = ref(false)

const typeIcons: Record<string, string> = {
  report_started: '▶',
  push_success: '✓',
  push_failed: '✗',
  draft_saved: '📝',
}

async function load() {
  loading.value = true
  try {
    const res = await api.getNotifications(50)
    items.value = res.items
  } catch { /* 静默 */ }
  loading.value = false
}

async function markRead(id: number) {
  await api.markNotificationRead(id)
  items.value = items.value.map(i => i.id === id ? { ...i, read: 1 } : i)
}

async function markAllRead() {
  await api.markAllNotificationsRead()
  items.value = items.value.map(i => ({ ...i, read: 1 }))
  props.showToast?.('已全部标记已读', 'success')
}

onMounted(load)
</script>

<template>
  <Teleport to="body">
    <div class="notif-overlay" @click.self="props.onClose">
      <div class="notif-panel glass-card">
        <div class="notif-header">
          <h3>通知</h3>
          <div class="notif-actions">
            <button class="btn btn-ghost btn-sm" @click="markAllRead">全部已读</button>
            <button class="btn btn-ghost btn-sm" @click="props.onClose">✕</button>
          </div>
        </div>
        <div class="notif-body">
          <div v-if="loading" class="text-dim" style="text-align:center;padding:var(--space-4)">加载中...</div>
          <div v-else-if="items.length === 0" class="text-dim" style="text-align:center;padding:var(--space-4)">暂无通知</div>
          <div v-else v-for="item in items" :key="item.id"
            class="notif-item" :class="{ unread: !item.read }"
            @click="!item.read && markRead(item.id)">
            <div class="notif-icon">{{ typeIcons[item.type] || '○' }}</div>
            <div class="notif-content">
              <div class="notif-title">{{ item.title }}</div>
              <div v-if="item.body" class="notif-body-text">{{ item.body }}</div>
              <div class="notif-time text-dim text-sm">{{ item.created_at?.slice(11, 19) || '' }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.notif-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; justify-content: flex-end; z-index: 1000; }
.notif-panel { width: 380px; height: 100vh; display: flex; flex-direction: column; border-radius: 0; padding: var(--space-3); }
.notif-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2); }
.notif-actions { display: flex; gap: var(--space-1); }
.notif-body { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
.notif-item { display: flex; gap: var(--space-2); padding: var(--space-2); border-radius: var(--radius-sm); cursor: pointer; transition: var(--transition-fast); border-left: 3px solid transparent; }
.notif-item:hover { background: rgba(255,255,255,0.03); }
.notif-item.unread { border-left-color: var(--accent); background: rgba(183,234,212,0.03); }
.notif-icon { font-size: 14px; width: 20px; text-align: center; flex-shrink: 0; margin-top: 1px; }
.notif-content { flex: 1; min-width: 0; }
.notif-title { font-size: 12px; font-weight: 500; }
.notif-body-text { font-size: 11px; color: var(--text-secondary); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.notif-time { font-size: 10px; margin-top: 2px; }
.btn-sm { padding: 3px 10px; font-size: 11px; }
</style>
