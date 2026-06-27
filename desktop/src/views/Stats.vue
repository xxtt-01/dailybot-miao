<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import { api, type TrendData, type PlatformStat } from '../api/client'
import * as echarts from 'echarts'

const trendDays = ref(7)
const trendData = ref<TrendData | null>(null)
const platformStats = ref<PlatformStat[]>([])
const platformTrendData = ref<any>(null)
const loading = ref(true)
const error = ref('')
const trendChartRef = ref<HTMLDivElement>()
const pieChartRef = ref<HTMLDivElement>()
const platformChartRef = ref<HTMLDivElement>()
let trendChart: echarts.ECharts | null = null
let pieChart: echarts.ECharts | null = null
let platformChart: echarts.ECharts | null = null

// 周报/月报
const summaryTab = ref<'daily' | 'weekly' | 'monthly'>('daily')
const summaryData = ref<any>(null)
const summaryLoading = ref(false)

function getDateRange(mode: 'weekly' | 'monthly'): { start: string; end: string } {
  const now = new Date()
  const end = now.toISOString().slice(0, 10)
  if (mode === 'weekly') {
    const start = new Date(now)
    start.setDate(start.getDate() - 6)
    return { start: start.toISOString().slice(0, 10), end }
  }
  const start = new Date(now.getFullYear(), now.getMonth(), 1)
  return { start: start.toISOString().slice(0, 10), end }
}

async function loadSummary() {
  if (summaryTab.value === 'daily') return
  summaryLoading.value = true
  try {
    const { start, end } = getDateRange(summaryTab.value)
    summaryData.value = await api.getReportSummary(start, end)
  } catch { /* 静默 */ }
  summaryLoading.value = false
}

function switchSummary(mode: 'daily' | 'weekly' | 'monthly') {
  summaryTab.value = mode
  if (mode !== 'daily') loadSummary()
}

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

async function loadPlatformTrend() {
  try {
    platformTrendData.value = await api.getPlatformTrend(trendDays.value)
    updatePlatformChart()
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
  platformChart?.resize()
}

function switchDays(d: number) {
  trendDays.value = d
  loadTrend()
  loadPlatformTrend()
}

function initPlatformChart() {
  if (!platformChartRef.value) return
  platformChart = echarts.init(platformChartRef.value, undefined, { renderer: 'canvas' })
  updatePlatformChart()
}

function updatePlatformChart() {
  if (!platformChart || !platformTrendData.value) return
  const platforms = platformTrendData.value.platforms
  const days = platformTrendData.value.days
  const colors = ['#b7ead4', '#6ab0f0', '#b794f4', '#f6ad55', '#f687b3', '#4ec77f']
  const series = Object.keys(platforms).map((name, i) => ({
    name,
    type: 'bar' as const,
    stack: 'total',
    data: platforms[name],
    itemStyle: { color: colors[i % colors.length], borderRadius: [0, 0, 0, 0] },
    emphasis: { focus: 'series' as const },
  }))
  platformChart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(24,28,36,0.9)', borderColor: 'rgba(128,138,152,0.2)', textStyle: { color: '#eef5fb', fontSize: 12 } },
    legend: { data: Object.keys(platforms), textStyle: { color: '#a3adbb', fontSize: 11 }, bottom: 0 },
    grid: { left: 40, right: 16, top: 16, bottom: 40 },
    xAxis: {
      type: 'category', data: days,
      axisLabel: { color: '#a3adbb', fontSize: 11 },
      axisLine: { lineStyle: { color: 'rgba(128,138,152,0.15)' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value', minInterval: 1,
      axisLabel: { color: '#a3adbb', fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(128,138,152,0.08)' } },
    },
    series,
  })
}

onMounted(async () => {
  await nextTick()
  initTrendChart()
  initPieChart()
  initPlatformChart()
  await Promise.all([loadTrend(), loadPlatformStats(), loadPlatformTrend()])
  loading.value = false
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  trendChart?.dispose()
  pieChart?.dispose()
  platformChart?.dispose()
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

      <!-- 多平台对比 -->
      <div class="glass-card chart-card">
        <div class="chart-header">
          <span class="text-dim">多平台工作量对比</span>
        </div>
        <div ref="platformChartRef" class="chart-container"></div>
      </div>

      <!-- 周报/月报聚合 -->
      <div class="glass-card chart-card summary-card">
        <div class="chart-header">
          <span class="text-dim">汇总统计</span>
          <div class="btn-group">
            <button class="btn" :class="summaryTab === 'daily' ? 'btn-primary' : 'btn-ghost'" @click="switchSummary('daily')">日报</button>
            <button class="btn" :class="summaryTab === 'weekly' ? 'btn-primary' : 'btn-ghost'" @click="switchSummary('weekly')">周报</button>
            <button class="btn" :class="summaryTab === 'monthly' ? 'btn-primary' : 'btn-ghost'" @click="switchSummary('monthly')">月报</button>
          </div>
        </div>
        <div v-if="summaryTab === 'daily'" class="summary-placeholder text-dim">
          切换周报/月报查看聚合统计
        </div>
        <div v-else-if="summaryLoading" class="summary-placeholder text-dim">
          加载中...
        </div>
        <div v-else-if="summaryData" class="summary-body">
          <div class="summary-row">
            <div class="summary-stat">
              <span class="summary-num">{{ summaryData.total }}</span>
              <span class="summary-label text-dim">总报告数</span>
            </div>
            <div class="summary-stat">
              <span class="summary-num">{{ summaryData.by_type?.normal || 0 }}</span>
              <span class="summary-label text-dim">正常</span>
            </div>
            <div class="summary-stat">
              <span class="summary-num">{{ summaryData.by_type?.camouflage || 0 }}</span>
              <span class="summary-label text-dim">伪装</span>
            </div>
            <div class="summary-stat">
              <span class="summary-num">{{ Object.keys(summaryData.by_platform || {}).length }}</span>
              <span class="summary-label text-dim">平台数</span>
            </div>
          </div>
          <div v-if="summaryData.by_platform" class="summary-platforms">
            <div v-for="(v, k) in summaryData.by_platform" :key="k" class="summary-platform-item">
              <span class="tag tag-info">{{ k }}</span>
              <span>{{ v.count }} 篇报告</span>
            </div>
          </div>
        </div>
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
.summary-card { grid-column: 1 / -1; }
.summary-placeholder { text-align: center; padding: var(--space-4); font-size: 12px; }
.summary-body { display: flex; flex-direction: column; gap: var(--space-2); }
.summary-row { display: flex; gap: var(--space-3); }
.summary-stat { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px; }
.summary-num { font-size: 28px; font-weight: 700; color: var(--accent); }
.summary-label { font-size: 11px; }
.summary-platforms { display: flex; flex-wrap: wrap; gap: var(--space-1); padding-top: var(--space-2); border-top: 1px solid var(--glass-border); }
.summary-platform-item { display: flex; align-items: center; gap: var(--space-2); font-size: 12px; }
</style>
