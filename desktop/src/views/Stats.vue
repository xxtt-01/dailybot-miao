<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { api, type TrendData, type PlatformStat } from '../api/client'
import * as echarts from 'echarts'

const trendDays = ref(7)
const trendData = ref<TrendData | null>(null)
const platformStats = ref<PlatformStat[]>([])
const platformTrendData = ref<any>(null)
const loading = ref(true)
const error = ref('')
const hasAnyData = ref(false)
const trendChartRef = ref<HTMLDivElement>()
const pieChartRef = ref<HTMLDivElement>()
const platformChartRef = ref<HTMLDivElement>()
let trendChart: echarts.ECharts | null = null
let pieChart: echarts.ECharts | null = null
let platformChart: echarts.ECharts | null = null

// ── 新增图表 ──
const complianceData = ref<any>(null)
const workTypeData = ref<any>(null)
const complianceChartRef = ref<HTMLDivElement>()
const typeChartRef = ref<HTMLDivElement>()
const projectChartRef = ref<HTMLDivElement>()
let complianceChart: echarts.ECharts | null = null
let typeChart: echarts.ECharts | null = null
let projectChart: echarts.ECharts | null = null
const generatingReport = ref(false)

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
  } catch (e) { console.warn('[Stats] 获取报告摘要失败', e) }
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
  } catch (e) { console.warn('[Stats] 加载平台统计失败', e) }
}

async function loadPlatformTrend() {
  try {
    platformTrendData.value = await api.getPlatformTrend(trendDays.value)
    updatePlatformChart()
  } catch (e) { console.warn('[Stats] 加载平台趋势失败', e) }
}

async function loadComplianceStats() {
  try {
    complianceData.value = await api.getCompliance(30)
    updateComplianceChart()
  } catch (e) { console.warn('[Stats] 加载合规率失败', e) }
}

async function loadWorkTypes() {
  try {
    workTypeData.value = await api.getWorkTypes(30)
    updateTypeChart()
    updateProjectChart()
  } catch (e) { console.warn('[Stats] 加载工作类型失败', e) }
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

let resizeTimer: ReturnType<typeof setTimeout> | null = null
function onResize() {
  if (resizeTimer) clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    trendChart?.resize()
    pieChart?.resize()
    platformChart?.resize()
    complianceChart?.resize()
    typeChart?.resize()
    projectChart?.resize()
  }, 150)
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

// ── 合规率图表 ──
function initComplianceChart() {
  if (!complianceChartRef.value) return
  complianceChart = echarts.init(complianceChartRef.value, undefined, { renderer: 'canvas' })
  updateComplianceChart()
}

function updateComplianceChart() {
  if (!complianceChart || !complianceData.value) return
  const data = complianceData.value
  complianceChart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(24,28,36,0.9)', borderColor: 'rgba(128,138,152,0.2)', textStyle: { color: '#eef5fb', fontSize: 12 } },
    grid: { left: 40, right: 16, top: 16, bottom: 24 },
    xAxis: { type: 'category', data: data.trend.map((d: any) => d.date.slice(5)), axisLabel: { color: '#a3adbb', fontSize: 11 }, axisLine: { lineStyle: { color: 'rgba(128,138,152,0.15)' } } },
    yAxis: { type: 'value', max: 1, axisLabel: { formatter: (v: number) => v ? '有' : '无', color: '#a3adbb', fontSize: 11 }, splitLine: { lineStyle: { color: 'rgba(128,138,152,0.08)' } } },
    series: [{
      type: 'bar', data: data.trend.map((d: any) => d.reported ? 1 : 0),
      itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#4ec77f' }, { offset: 1, color: 'rgba(78,199,127,0.2)' }]), borderRadius: [2, 2, 0, 0] },
    }],
  })
}

// ── 工作类型饼图 ──
function initTypeChart() {
  if (!typeChartRef.value) return
  typeChart = echarts.init(typeChartRef.value, undefined, { renderer: 'canvas' })
  updateTypeChart()
}

function updateTypeChart() {
  if (!typeChart || !workTypeData.value) return
  const data = workTypeData.value.type_distribution.slice(0, 10)
  typeChart.setOption({
    tooltip: { trigger: 'item', backgroundColor: 'rgba(24,28,36,0.9)', borderColor: 'rgba(128,138,152,0.2)', textStyle: { color: '#eef5fb', fontSize: 12 }, formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie', radius: ['30%', '60%'],
      data: data.map((d: any, i: number) => ({
        name: d.name, value: d.count,
        itemStyle: { color: ['#b7ead4','#6ab0f0','#b794f4','#f6ad55','#f687b3','#4ec77f','#f06a7b','#e8c96a','#a3adbb','#8fdfbe'][i % 10] },
      })),
      label: { color: '#a3adbb', fontSize: 11, formatter: '{b}' },
      labelLine: { lineStyle: { color: 'rgba(128,138,152,0.3)' } },
    }],
  })
}

// ── 项目投入分布 ──
function initProjectChart() {
  if (!projectChartRef.value) return
  projectChart = echarts.init(projectChartRef.value, undefined, { renderer: 'canvas' })
  updateProjectChart()
}

function updateProjectChart() {
  if (!projectChart || !workTypeData.value) return
  const data = workTypeData.value.project_distribution
  projectChart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(24,28,36,0.9)', borderColor: 'rgba(128,138,152,0.2)', textStyle: { color: '#eef5fb', fontSize: 12 } },
    grid: { left: 80, right: 16, top: 16, bottom: 24 },
    xAxis: { type: 'value', axisLabel: { color: '#a3adbb', fontSize: 11 }, splitLine: { lineStyle: { color: 'rgba(128,138,152,0.08)' } } },
    yAxis: { type: 'category', data: data.map((d: any) => d.name).reverse(), axisLabel: { color: '#a3adbb', fontSize: 11 }, axisLine: { lineStyle: { color: 'rgba(128,138,152,0.15)' } } },
    series: [{
      type: 'bar', data: data.map((d: any) => d.count).reverse(),
      itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: 'rgba(106,176,240,0.2)' }, { offset: 1, color: '#6ab0f0' }]), borderRadius: [0, 4, 4, 0] },
    }],
  })
}

// ── 生成周报/月报 HTML ──
async function generateReport(mode: 'weekly' | 'monthly') {
  generatingReport.value = true
  try {
    const now = new Date()
    const end = now.toISOString().slice(0, 10)
    let start: string
    if (mode === 'weekly') {
      const s = new Date(now); s.setDate(s.getDate() - 6)
      start = s.toISOString().slice(0, 10)
    } else {
      start = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10)
    }

    const [summary, compliance, workTypes] = await Promise.all([
      api.getReportSummary(start, end),
      api.getCompliance(30),
      api.getWorkTypes(30),
    ])

    const win = window.open('', '_blank')
    if (!win) { throw new Error('浏览器阻止了新窗口打开') }

    const title = mode === 'weekly' ? `周报 ${start} ~ ${end}` : `月报 ${start.slice(0, 7)}`

    const dailyRows = (summary.reports || []).slice(0, 100).map((r: any) => {
      let firstType = '--'
      try { const items = JSON.parse(r.summary); if (Array.isArray(items) && items[0]) firstType = items[0].type || '--' } catch {}
      return `<tr><td>${r.date}</td><td>${r.platform}</td><td><span class="tag">${firstType}</span></td><td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${(r.summary || '').slice(0, 100)}</td></tr>`
    }).join('')

    win.document.write(`
      <!DOCTYPE html>
      <html><head>
        <meta charset="utf-8">
        <title>${title}</title>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"><\/script>
        <style>
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body { font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #0f1219; color: #eef5fb; padding: 40px; }
          .container { max-width: 900px; margin: 0 auto; }
          h1 { font-size: 24px; margin-bottom: 4px; }
          .meta { color: #a3adbb; font-size: 13px; margin-bottom: 24px; }
          .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
          .stat-card { background: rgba(255,255,255,0.04); border: 1px solid rgba(128,138,152,0.15); border-radius: 8px; padding: 16px; text-align: center; }
          .stat-value { font-size: 28px; font-weight: 700; color: #b7ead4; }
          .stat-label { font-size: 11px; color: #a3adbb; margin-top: 4px; }
          .section { margin-bottom: 24px; }
          .section-title { font-size: 14px; font-weight: 600; color: #a3adbb; margin-bottom: 12px; letter-spacing: 0.5px; }
          .chart-box { height: 280px; margin-bottom: 24px; background: rgba(255,255,255,0.02); border-radius: 8px; padding: 8px; }
          table { width: 100%; border-collapse: collapse; font-size: 12px; }
          th { text-align: left; padding: 8px 10px; color: #a3adbb; font-weight: 500; border-bottom: 1px solid rgba(128,138,152,0.15); }
          td { padding: 6px 10px; border-bottom: 1px solid rgba(128,138,152,0.08); }
          .tag { display: inline-block; font-size: 10px; padding: 1px 6px; border-radius: 4px; background: rgba(106,176,240,0.15); color: #6ab0f0; }
          @media print { body { background: white; color: #333; } .stat-card { background: #f5f5f5; border-color: #ddd; } }
        </style>
      </head><body>
        <div class="container">
          <h1>${title}</h1>
          <div class="meta">${summary.total} 篇日报 · ${compliance.compliance_rate}% 合规率 · ${Object.keys(summary.by_platform || {}).length} 个平台</div>

          <div class="stats-row">
            <div class="stat-card"><div class="stat-value">${summary.total}</div><div class="stat-label">总日报数</div></div>
            <div class="stat-card"><div class="stat-value">${summary.by_type?.normal || 0}</div><div class="stat-label">正常</div></div>
            <div class="stat-card"><div class="stat-value">${summary.by_type?.camouflage || 0}</div><div class="stat-label">伪装</div></div>
            <div class="stat-card"><div class="stat-value">${compliance.compliance_rate}%</div><div class="stat-label">合规率</div></div>
          </div>

          <div class="section">
            <div class="section-title">日报类型分布</div>
            <div id="typeChart" class="chart-box"></div>
          </div>

          <div class="section">
            <div class="section-title">每日明细</div>
            <table>
              <thead><tr><th>日期</th><th>平台</th><th>类型</th><th>摘要</th></tr></thead>
              <tbody>${dailyRows}</tbody>
            </table>
          </div>

          <button onclick="window.print()" style="position:fixed;bottom:24px;right:24px;padding:10px 20px;background:#b7ead4;color:#0f1219;border:none;border-radius:8px;cursor:pointer;font-size:13px">🖨 打印 / 保存 PDF</button>
        </div>
        <script>
          const typeData = ${JSON.stringify(workTypes.type_distribution.slice(0, 8))};
          const chart = echarts.init(document.getElementById('typeChart'));
          chart.setOption({
            tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
            series: [{ type: 'pie', radius: ['30%', '60%'], data: typeData.map(function(d) { return { name: d.name, value: d.count }; }), label: { formatter: '{b}' } }],
          });
        <\/script>
      </body></html>
    `)
    win.document.close()
  } catch (e: any) {
    // silently fail
  } finally {
    generatingReport.value = false
  }
}

onMounted(async () => {
  // 先加载所有数据
  await Promise.all([loadTrend(), loadPlatformStats(), loadPlatformTrend(), loadComplianceStats(), loadWorkTypes()])

  // 渲染图表容器
  loading.value = false

  // 等待 DOM 渲染完成再初始化图表
  await nextTick()
  initTrendChart()
  initPieChart()
  initPlatformChart()
  initComplianceChart()
  initTypeChart()
  initProjectChart()

  // 重新更新图表（加载时图表未初始化，update 被跳过）
  updateTrendChart()
  updatePieChart()
  updatePlatformChart()
  updateComplianceChart()
  updateTypeChart()
  updateProjectChart()

  hasAnyData.value = !!(trendData.value || platformStats.value.length > 0 || platformTrendData.value || complianceData.value || workTypeData.value)
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  if (resizeTimer) clearTimeout(resizeTimer)
  window.removeEventListener('resize', onResize)
  trendChart?.dispose()
  pieChart?.dispose()
  platformChart?.dispose()
  complianceChart?.dispose()
  typeChart?.dispose()
  projectChart?.dispose()
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
      <!-- 无数据提示 -->
      <div v-if="!hasAnyData" class="glass-card" style="padding:32px;text-align:center;grid-column:1/-1">
        <div class="text-dim">暂无统计数据，生成日报后会自动累积</div>
      </div>

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

      <!-- 合规率趋势 -->
      <div class="glass-card chart-card">
        <div class="chart-header">
          <span class="text-dim">合规率趋势(30天)</span>
        </div>
        <div ref="complianceChartRef" class="chart-container"></div>
      </div>

      <!-- 工作类型分布 -->
      <div class="glass-card chart-card">
        <div class="chart-header">
          <span class="text-dim">工作类型分布</span>
        </div>
        <div ref="typeChartRef" class="chart-container"></div>
      </div>

      <!-- 项目分布 -->
      <div class="glass-card chart-card">
        <div class="chart-header">
          <span class="text-dim">项目投入分布</span>
        </div>
        <div ref="projectChartRef" class="chart-container"></div>
      </div>

      <!-- 周报/月报聚合 -->
      <div class="glass-card chart-card summary-card">
        <div class="chart-header">
          <span class="text-dim">汇总统计</span>
          <div class="btn-group">
            <button class="btn" :class="summaryTab === 'daily' ? 'btn-primary' : 'btn-ghost'" @click="switchSummary('daily')">日报</button>
            <button class="btn" :class="summaryTab === 'weekly' ? 'btn-primary' : 'btn-ghost'" @click="switchSummary('weekly')">周报</button>
            <button class="btn" :class="summaryTab === 'monthly' ? 'btn-primary' : 'btn-ghost'" @click="switchSummary('monthly')">月报</button>
            <button class="btn btn-ghost" :disabled="generatingReport" @click="generateReport('weekly')">生成周报</button>
            <button class="btn btn-ghost" :disabled="generatingReport" @click="generateReport('monthly')">生成月报</button>
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
