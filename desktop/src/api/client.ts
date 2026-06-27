// desktop/src/api/client.ts — 封装所有后端 API 调用
const BASE = 'http://127.0.0.1:8001'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = BASE + path
  const res = await fetch(url, {
    headers: {
      Accept: 'application/json',
      'X-Desktop-Client': 'true',  // 桌面版本地请求，跳过 key 鉴权
      ...options?.headers,
    },
    ...options,
  })
  if (res.status === 401) {
    throw new Error('API Key 不匹配，请检查 config.yaml 中的 admin.api_key 配置')
  }
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`请求失败 ${res.status}: ${text.slice(0, 200)}`)
  }
  return res.json()
}

export interface SystemStatus {
  version: string
  enabled_workflows: string[]
  platforms: { name: string; ai_model: string; rpa_enabled: boolean }[]
  time: string
}

export interface Report {
  id: number
  date: string
  platform: string
  summary: string
  raw_data: string
  is_camouflage: number
  created_at: string
}

export interface RunLog {
  id: number
  date: string
  platform: string
  status: string
  message: string
  created_at: string
}

export interface TrendData {
  days: string[]
  counts: number[]
}

export interface PlatformStat {
  name: string
  success: number
  failed: number
  no_data: number
}

export interface CamouflageItem {
  id: string
  source_name: string
  content_preview: string
  platform: string
  last_used: string
  variants_count: number
}

export interface SourceInfo {
  platform: string
  enabled: boolean
  repo_count: number
  repos: { path: string; branch: string }[]
}

export interface VersionInfo {
  current_version: string
  latest_version: string
  has_update: boolean
  download_url: string
}

export interface ExtraReport {
  id: number
  date: string
  content: string
  project: string
  work_type: string
  created_at: string
  updated_at: string
}

export interface Notification {
  id: number
  title: string
  body: string
  type: string
  related_id: number
  read: number
  created_at: string
}

export interface ComplianceData {
  days: number
  total_workdays: number
  reported_days: number
  compliance_rate: number
  trend: { date: string; reported: boolean; count: number }[]
}

export interface WorkTypeData {
  days: number
  type_distribution: { name: string; count: number }[]
  project_distribution: { name: string; count: number }[]
  type_trend: Record<string, Record<string, number>>
  platforms: string[]
}

export interface AiQueryResult {
  answer: string
  source_count: number
}

export const api = {
  getStatus: () => request<SystemStatus>('/admin/status'),
  getConfig: () => request<any>('/admin/config?masked=true'),
  updateConfig: (data: any, replace = false) => {
    let path = '/admin/config'
    if (replace) path += '?replace=true'
    return request<{ success: boolean; message: string }>(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
  },
  getReports: (date?: string, platform?: string, search?: string) => {
    let path = '/admin/reports?limit=50'
    if (date) path += `&date=${date}`
    if (platform) path += `&platform=${platform}`
    if (search) path += `&search=${encodeURIComponent(search)}`
    return request<{ date: string; reports: Report[]; count: number }>(path)
  },
  getReportDetail: (id: number) =>
    request<{ report: Report }>(`/admin/reports/detail?id=${id}`),
  getLogs: (limit = 100, search?: string) => {
    let path = `/admin/logs?limit=${limit}`
    if (search) path += `&search=${encodeURIComponent(search)}`
    return request<{ logs: RunLog[]; count: number }>(path)
  },
  triggerReport: () =>
    request<{ message: string; status: string }>('/admin/trigger', { method: 'POST' }),
  getTrend: (days = 7) => request<TrendData>(`/admin/stats/trend?days=${days}`),
  getPlatformStats: () => request<{ platforms: PlatformStat[] }>('/admin/stats/platform'),
  getPlatformTrend: (days = 7) => request<{ days: string[]; platforms: Record<string, number[]> }>(`/admin/stats/platform-trend?days=${days}`),
  getReportSummary: (start: string, end: string) =>
    request<{ start: string; end: string; total: number; by_platform: Record<string, { count: number }>; by_type: { normal: number; camouflage: number }; reports: any[] }>(`/admin/reports/summary?start=${start}&end=${end}`),
  getCamouflage: () => request<{ items: CamouflageItem[] }>('/admin/camouflage'),
  deleteCamouflage: (id: string) =>
    request<{ success: boolean }>(`/admin/camouflage/${id}`, { method: 'DELETE' }),
  getSources: () => request<{ sources: SourceInfo[] }>('/admin/sources'),
  addSource: (platform: string, repoPath: string, branch: string) =>
    request<{ success: boolean }>('/admin/sources', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform, repo_path: repoPath, branch }),
    }),
  deleteSource: (platform: string, index: number) =>
    request<{ success: boolean }>(`/admin/sources/${platform}/${index}`, { method: 'DELETE' }),
  getScheduler: () =>
    request<{ config: any; installed_tasks: string[] }>('/admin/scheduler'),
  installScheduler: (time: string, weekdays?: number[]) =>
    request<{ success: boolean }>('/admin/scheduler/install', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ time, weekdays }),
    }),
  uninstallScheduler: () =>
    request<{ success: boolean }>('/admin/scheduler/uninstall', { method: 'POST' }),
  getDesktopVersion: () => request<VersionInfo>('/admin/desktop-version'),
  cleanupData: (days = 30) =>
    request<{ success: boolean; message: string; details: any }>(`/admin/maintenance/cleanup?days=${days}`, { method: 'POST' }),
  autoMaintenance: () =>
    request<{ success: boolean; message: string }>('/admin/maintenance/auto', { method: 'POST' }),
  getDrafts: () => request<{ drafts: Report[]; count: number }>('/admin/reports/drafts'),
  updateReport: (id: number, summary: string) =>
    request<{ success: boolean; message: string }>(`/admin/reports/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ summary }),
    }),
  pushReport: (id: number) =>
    request<{ success: boolean; message: string }>(`/admin/reports/${id}/push`, { method: 'POST' }),

  // ── Extra Reports ──
  getExtraReports: (date: string) =>
    request<{ items: ExtraReport[]; count: number }>(`/admin/extra-reports?date=${date}`),
  addExtraReport: (data: { date: string; content: string; project?: string; work_type?: string }) =>
    request<{ success: boolean; id: number }>('/admin/extra-reports', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  updateExtraReport: (id: number, data: { content: string; project?: string; work_type?: string }) =>
    request<{ success: boolean }>(`/admin/extra-reports/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  deleteExtraReport: (id: number) =>
    request<{ success: boolean }>(`/admin/extra-reports/${id}`, { method: 'DELETE' }),

  // ── Notifications ──
  getNotifications: (limit = 50, unreadOnly = false) =>
    request<{ items: Notification[]; count: number; unread_count: number }>(
      `/admin/notifications?limit=${limit}&unread_only=${unreadOnly}`
    ),
  markNotificationRead: (id: number) =>
    request<{ success: boolean }>(`/admin/notifications/${id}/read`, { method: 'POST' }),
  markAllNotificationsRead: () =>
    request<{ success: boolean; marked: number }>('/admin/notifications/read-all', { method: 'POST' }),

  // ── Stats ──
  getCompliance: (days = 30) =>
    request<ComplianceData>(`/admin/stats/compliance?days=${days}`),
  getWorkTypes: (days = 30) =>
    request<WorkTypeData>(`/admin/stats/work-types?days=${days}`),

  // ── AI Query ──
  aiQuery: (question: string, days = 30) =>
    request<AiQueryResult>('/admin/ai-query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, days }),
    }),
}
