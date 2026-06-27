<!-- desktop/src/components/ThemeSwitcher.vue — 主题色选择器 -->
<script setup lang="ts">
import { ref } from 'vue'

const THEME_KEY = 'dailybot-theme'

const themes = [
  { id: 'mint',     label: '薄荷', color: '#b7ead4' },
  { id: 'ocean',    label: '海洋', color: '#6ab0f0' },
  { id: 'lavender', label: '薰衣草', color: '#b794f4' },
  { id: 'sunset',   label: '落日', color: '#f6ad55' },
  { id: 'rose',     label: '玫瑰', color: '#f687b3' },
]

const currentTheme = ref(localStorage.getItem(THEME_KEY) || 'mint')
const open = ref(false)

function applyTheme(id: string) {
  currentTheme.value = id
  document.documentElement.setAttribute('data-theme', id)
  localStorage.setItem(THEME_KEY, id)
}

function selectTheme(id: string) {
  applyTheme(id)
  open.value = false
}

// 初始化
applyTheme(currentTheme.value)
</script>

<template>
  <div class="theme-area">
    <button class="theme-toggle btn-icon" title="切换主题" @click="open = !open">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <circle cx="7" cy="7" r="5" stroke="currentColor" stroke-width="1.2"/>
        <path d="M7 2v1M7 11v1M2 7h1M11 7h1M3.5 3.5l.7.7M9.8 9.8l.7.7M3.5 10.5l.7-.7M9.8 4.2l.7-.7" stroke="currentColor" stroke-width="1" stroke-linecap="round"/>
      </svg>
    </button>

    <Transition name="theme-pop">
      <div v-if="open" class="theme-panel glass-card" @click.stop>
        <div class="theme-panel-title">主题色</div>
        <div class="theme-swatches">
          <button v-for="t in themes" :key="t.id"
            :class="['theme-swatch', { active: currentTheme === t.id }]"
            :style="{ '--swatch': t.color }"
            :title="t.label"
            @click="selectTheme(t.id)">
            <span class="swatch-dot"></span>
            <span class="swatch-label">{{ t.label }}</span>
            <span v-if="currentTheme === t.id" class="swatch-check">✓</span>
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.theme-area { position: relative; }
.theme-toggle { width: 28px; height: 28px; }

.theme-panel {
  position: absolute;
  bottom: 100%;
  left: 0;
  margin-bottom: 8px;
  padding: 10px 12px;
  min-width: 160px;
  z-index: 100;
}
.theme-panel-title {
  font-size: 11px; color: var(--text-dim);
  margin-bottom: 8px; letter-spacing: 0.3px;
}
.theme-swatches { display: flex; flex-direction: column; gap: 4px; }

.theme-swatch {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 8px; border: none; border-radius: var(--radius-sm);
  background: transparent; color: var(--text-secondary);
  cursor: pointer; font-family: var(--font-mono); font-size: 12px;
  transition: var(--transition-fast); text-align: left;
}
.theme-swatch:hover { background: rgba(255,255,255,0.04); color: var(--text-primary); }
.theme-swatch.active { background: rgba(255,255,255,0.06); color: var(--text-primary); }

.swatch-dot {
  width: 16px; height: 16px; border-radius: 50%;
  background: var(--swatch); flex-shrink: 0;
  box-shadow: 0 0 8px var(--swatch);
}
.swatch-label { flex: 1; }
.swatch-check { color: var(--accent); font-size: 11px; }

.theme-pop-enter-active, .theme-pop-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.theme-pop-enter-from, .theme-pop-leave-to {
  opacity: 0; transform: translateY(6px);
}
</style>
