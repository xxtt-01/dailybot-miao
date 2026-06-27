<!-- desktop/src/components/VirtualList.vue — 虚拟滚动列表 -->
<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps<{
  items: any[]
  itemHeight?: number
  overscan?: number
}>()

const itemHeight = props.itemHeight ?? 36
const overscan = props.overscan ?? 5

const containerRef = ref<HTMLElement | null>(null)
const scrollTop = ref(0)
const containerHeight = ref(400)

const totalHeight = computed(() => props.items.length * itemHeight)

const visibleRange = computed(() => {
  const start = Math.max(0, Math.floor(scrollTop.value / itemHeight) - overscan)
  const end = Math.min(props.items.length, Math.ceil((scrollTop.value + containerHeight.value) / itemHeight) + overscan)
  return { start, end }
})

const visibleItems = computed(() => {
  const { start, end } = visibleRange.value
  return props.items.slice(start, end).map((item, i) => ({
    item,
    index: start + i,
    style: { position: 'absolute', top: `${(start + i) * itemHeight}px`, left: 0, right: 0, height: `${itemHeight}px` },
  }))
})

function onScroll() {
  if (containerRef.value) {
    scrollTop.value = containerRef.value.scrollTop
  }
}

function onResize() {
  if (containerRef.value) {
    containerHeight.value = containerRef.value.clientHeight
  }
}

onMounted(() => {
  onResize()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
})
</script>

<template>
  <div ref="containerRef" class="virtual-container" @scroll="onScroll">
    <div class="virtual-spacer" :style="{ height: totalHeight + 'px', position: 'relative' }">
      <div v-for="v in visibleItems" :key="v.index" :style="v.style" class="virtual-item">
        <slot name="default" :item="v.item" :index="v.index" />
      </div>
    </div>
    <div v-if="items.length === 0" class="virtual-empty">
      <slot name="empty" />
    </div>
  </div>
</template>

<style scoped>
.virtual-container {
  overflow-y: auto;
  flex: 1;
  min-height: 0;
  contain: strict;
}
.virtual-spacer {
  width: 100%;
}
.virtual-item {
  overflow: hidden;
  will-change: transform;
}
.virtual-empty {
  padding: 32px;
  text-align: center;
}
</style>
