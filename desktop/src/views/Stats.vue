<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { api, type TrendData, type PlatformStat } from '../api/client'
import * as echarts from 'echarts'

const trendDays = ref(7)
const trendData = ref<TrendData | null>(null)
const platformStats = ref<PlatformStat[]>([])
const loading = ref(true)
const error = ref('')
const trendChartRef = ref<HTMLDivElement>()
const pieChartRef = ref<HTMLDivElement>()
let trendChart: echarts.ECharts | null = null
let pieChart: echarts.ECharts | null = null

async function loadTrend() {
  try {
    trendData.value = await api.getTrend(trendDays.value)
    updateTrendChart()
  } catch (e: any) {
    error.value = '获取趋势数据失败: ' + (e.message || '未知错误')
  }
}

async function loadPlatformStats() {
  try {
    const res = await api.getPlatformStats()
    platformStats.value = res.platforms || []
    updatePieChart()
  } catch { /* 静默 */ }
}

function initTrendChart() {
  if (!trendChartRef.value) return
  trendChart = echarts.init(trendChartRef.value, undefined, { renderer: 'canvas' })
  updateTrendChart()
}

function updateTrendChart() {
  if (!trendChart || !trendData.value) return
  trendChart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(24,28,36,0.9)', borderColor: 'rgba(128,138,152,0.2)', textStyle: { color: '#eef5fb', fontSize: 12 } },
    grid: { left: 40, right: 16, top: 16, bottom: 24 },
    xAxis: {
      type: 'category', data: trendData.value.days,
      axisLabel: { color: '#a3adbb', fontSize: 11 },
      axisLine: { lineStyle: { color: 'rgba(128,138,152,0.15)' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value', minInterval: 1,
      axisLabel: { color: '#a3adbb', fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(128,138,152,0.08)' } },
    },
    series: [{
      type: 'bar', data: trendData.value.counts,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#b7ead4' },
          { offset: 1, color: 'rgba(183,234,212,0.2)' },
        ]),
        borderRadius: [4, 4, 0, 0],
      },
      emphasis: { itemStyle: { color: '#8fdfbe' } },
    }],
  })
}

function initPieChart() {
  if (!pieChartRef.value) return
  pieChart = echarts.init(pieChartRef.value, undefined, { renderer: 'canvas' })
  updatePieChart()
}

function updatePieChart() {
  if (!pieChart) return
  const data: { name: string; value: number; itemStyle: any }[] = []
  const colorMap: Record<string, string> = {
    success: '#4ec77f', failed: '#f06a7b', no_data: '#f0a06a',
  }
  const labelMap: Record<string, string> = {
    success: '成功', failed: '失败', no_data: '无数据',
  }

  for (const p of platformStats.value) {
    if (p.success > 0) data.push({ name: p.name + ' - 成功', value: p.success, itemStyle: { color: '#4ec77f' } })
    if (p.failed > 0) data.push({ name: p.name + ' - 失败', value: p.failed, itemStyle: { color: '#f06a7b' } })
    if (p.no_data > 0) data.push({ name: p.name + ' - 无数据', value: p.no_data, itemStyle: { color: '#f0a06a' } })
  }

  if (data.length === 0) {
    data.push({ name: '暂无数据', value: 1, itemStyle: { color: 'rgba(128,138,152,0.2)' } })
  }

  pieChart.setOption({
    tooltip: { trigger: 'item', backgroundColor: 'rgba(24,28,36,0.9)', borderColor: 'rgba(128,138,152,0.2)', textStyle: { color: '#eef5fb', fontSize: 12 }, formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie', radius: ['30%', '60%'], center: ['50%', '50%'],
      data,
      label: { color: '#a3adbb', fontSize: 11, formatter: '{b}' },
      labelLine: { lineStyle: { color: 'rgba(128,138,152,0.3)' } },
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' } },
    }],
  })
}

function onResize() {
  trendChart?.resize()
  pieChart?.resize()
}

function switchDays(d: number) {
  trendDays.value = d
  loadTrend()
}

onMounted(async () => {
  await nextTick()
  initTrendChart()
  initPieChart()
  await Promise.all([loadTrend(), loadPlatformStats()])
  loading.value = false
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  trendChart?.dispose()
  pieChart?.dispose()
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>数据统计</h2>
    </div>

    <div v-if="loading" class="loading-text text-dim">加载中...</div>
    <div v-else-if="error" class="error-box glass-card">
      <span class="tag tag-danger">错误</span>
      <span>{{ error }}</span>
    </div>
    <div v-else class="stats-grid">
      <!-- 趋势图 -->
      <div class="glass-card chart-card">
        <div class="chart-header">
          <span class="text-dim">日报趋势</span>
          <div class="btn-group">
            <button class="btn" :class="trendDays === 7 ? 'btn-primary' : 'btn-ghost'" @click="switchDays(7)">7日</button>
            <button class="btn" :class="trendDays === 30 ? 'btn-primary' : 'btn-ghost'" @click="switchDays(30)">30日</button>
          </div>
        </div>
        <div ref="trendChartRef" class="chart-container"></div>
      </div>

      <!-- 平台饼图 -->
      <div class="glass-card chart-card">
        <div class="chart-header">
          <span class="text-dim">平台运行状态</span>
        </div>
        <div ref="pieChartRef" class="chart-container"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { padding: var(--space-2); }
.page-header { margin-bottom: var(--space-2); }
.page-header h2 { margin: 0; }
.loading-text { padding: var(--space-4); text-align: center; }
.error-box { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2); }
.stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-2); }
.chart-card { padding: var(--space-2); }
.chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2); }
.btn-group { display: flex; gap: 4px; }
.chart-container { width: 100%; height: 300px; }
</style>
