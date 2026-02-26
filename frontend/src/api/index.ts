import axios from 'axios'

const API_BASE_URL = '/api'
const ACCESS_TOKEN_KEY = 'redink_access_token'

let accessToken = localStorage.getItem(ACCESS_TOKEN_KEY) || ''

function getAuthHeaders(): Record<string, string> {
  if (!accessToken) return {}
  return { Authorization: `Bearer ${accessToken}` }
}

export function getAccessToken(): string {
  return accessToken
}

export function setAccessToken(token: string) {
  accessToken = token.trim()
  if (accessToken) {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  } else {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
  }
}

export function clearAccessToken() {
  accessToken = ''
  localStorage.removeItem(ACCESS_TOKEN_KEY)
}

axios.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers = config.headers || {}
    if (!('Authorization' in config.headers)) {
      ;(config.headers as any).Authorization = `Bearer ${accessToken}`
    }
  }
  return config
})

// ==================== 通用工具函数 ====================

/**
 * 处理 axios 错误的通用函数
 */
function handleAxiosError(error: any, defaultMessage: string, defaultReturn: any = {}): any {
  if (axios.isAxiosError(error)) {
    if (error.code === 'ECONNABORTED') {
      return { success: false, ...defaultReturn, error: '请求超时，请检查网络连接' }
    }
    if (!error.response) {
      return { success: false, ...defaultReturn, error: '网络连接失败，请检查网络设置' }
    }
    if (error.response.status === 404) {
      return { success: false, ...defaultReturn, error: '资源不存在' }
    }
    const errorMessage = error.response?.data?.error || error.message || defaultMessage
    return { success: false, ...defaultReturn, error: errorMessage }
  }
  return { success: false, ...defaultReturn, error: '未知错误，请稍后重试' }
}

function extractDownloadFilename(contentDisposition: string): string | undefined {
  if (!contentDisposition) return undefined

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match && utf8Match[1]) {
    try {
      return decodeURIComponent(utf8Match[1]).trim()
    } catch {
      return utf8Match[1].trim()
    }
  }

  const plainMatch = contentDisposition.match(/filename="?([^";]+)"?/i)
  return plainMatch && plainMatch[1] ? plainMatch[1].trim() : undefined
}

/**
 * SSE 事件处理器类型
 */
type SSEEventHandlers = Record<string, (data: any) => void>

/**
 * 通用 SSE 流处理函数
 */
async function handleSSEStream(
  url: string,
  body: any,
  handlers: SSEEventHandlers,
  onStreamError: (error: Error) => void
) {
  try {
    const isFormData = typeof FormData !== 'undefined' && body instanceof FormData
    const headers: Record<string, string> = { ...getAuthHeaders() }
    if (!isFormData) {
      headers['Content-Type'] = 'application/json'
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: isFormData ? body : JSON.stringify(body)
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('无法读取响应流')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.trim()) continue

        const [eventLine, dataLine] = line.split('\n')
        if (!eventLine || !dataLine) continue

        const eventType = eventLine.replace('event: ', '').trim()
        const eventData = dataLine.replace('data: ', '').trim()

        try {
          const data = JSON.parse(eventData)
          const handler = handlers[eventType]
          if (handler) handler(data)
        } catch (e) {
          console.error('解析 SSE 数据失败:', e)
        }
      }
    }
  } catch (error) {
    onStreamError(error as Error)
  }
}

// ==================== 类型定义 ====================

export interface Page {
  index: number
  type: 'cover' | 'content' | 'summary'
  content: string
  user_image?: string // 页面级参考图（Base64）
  image_suggestion?: string // AI 生成的配图建议
}

export interface OutlineResponse {
  success: boolean
  outline?: string
  pages?: Page[]
  error?: string
  has_images?: boolean
}

export interface OutlineStreamStartEvent {
  success: boolean
  message?: string
}

export interface OutlineStreamFinishEvent extends OutlineResponse {
  elapsed?: number
}

export interface OutlineStreamParams {
  topic: string
  images?: File[]
  sourceContent?: string
  templateRef?: TemplateReferencePayload
  enableSearch?: boolean
}

export interface OutlineEditStreamParams {
  topic: string
  current_outline?: string
  current_pages?: Page[]
  revision_request?: string
  mode?: 'suggest_only' | 'revise'
  template_ref?: TemplateReferencePayload
}

export interface OutlineEditStreamPageEvent {
  success: boolean
  mode: 'suggest_only' | 'revise'
  page: Page
}

export interface OutlineEditStreamFinishEvent {
  success: boolean
  mode: 'suggest_only' | 'revise'
  outline: string
  pages: Page[]
}

export interface ProgressEvent {
  index: number
  status: 'generating' | 'done' | 'error'
  current?: number
  total?: number
  image_url?: string
  message?: string
}

export interface FinishEvent {
  success: boolean
  task_id: string
  images: string[]
}

export interface HistoryRecord {
  id: string
  title: string
  created_at: string
  updated_at: string
  status: string
  thumbnail: string | null
  page_count: number
  task_id: string | null
}

export interface HistoryDetail {
  id: string
  title: string
  created_at: string
  updated_at: string
  outline: { raw: string; pages: Page[] }
  images: { task_id: string | null; generated: string[] }
  content?: { titles: string[]; copywriting: string; tags: string[] }
  status: string
  thumbnail: string | null
}

export interface UpdateHistoryParams {
  outline?: { raw: string; pages: Page[] }
  images?: { task_id: string | null; generated: string[] }
  status?: string
  thumbnail?: string
  content?: { titles: string[]; copywriting: string; tags: string[] }
}

export interface VibeSurfStatus {
  running: boolean
  message: string
  version?: string
}

export interface LoginStatus {
  logged_in: boolean
  username?: string
  message: string
}

export interface PublishProgressEvent {
  step: string
  message: string
  progress?: number
  success?: boolean
  error?: string
  post_url?: string
}

export interface PublishData {
  images: string[]
  title: string
  content: string
  tags: string[]
}

export interface ContentResponse {
  success: boolean
  titles?: string[]
  copywriting?: string
  tags?: string[]
  error?: string
}

export interface HealthResponse {
  success: boolean
  message?: string
  auth_required?: boolean
  rate_limit?: string
}

export interface FirecrawlStatusResponse {
  success: boolean
  enabled?: boolean
  configured?: boolean
  error?: string
}

export interface ScrapeResultData {
  title: string
  content: string
  word_count: number
  url: string
}

export interface ScrapeResult {
  success: boolean
  data?: ScrapeResultData
  error?: string
}

export interface TemplateReferencePayload {
  id: string
  title: string
  category?: string
  description?: string
  prompt?: string
  stylePrompt?: string
  tags?: string[]
}

export interface TemplateItem {
  id: string
  title: string
  description: string
  category: string
  coverImage: string
  fullImage: string
  tags: string[]
  prompt: string
  usageCount: number
  isHot: boolean
  isNew: boolean
  createdAt?: string
  stylePrompt?: string
}

export interface TemplateCategory {
  name: string
  count: number
}

export interface TemplatesResponse {
  success: boolean
  templates: TemplateItem[]
  total: number
  q?: string
  category?: string
  error?: string
}

export interface TemplateCategoriesResponse {
  success: boolean
  categories: TemplateCategory[]
  error?: string
}

export interface TemplateDetailResponse {
  success: boolean
  template?: TemplateItem
  error?: string
}

export async function getHealth(): Promise<HealthResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      headers: { ...getAuthHeaders() }
    })
    if (!response.ok) {
      return { success: false, message: `HTTP ${response.status}` }
    }
    return await response.json()
  } catch (error: any) {
    return { success: false, message: error?.message || 'health check failed' }
  }
}

export async function verifyAccessToken(): Promise<boolean> {
  try {
    const response = await axios.get(`${API_BASE_URL}/config`, { timeout: 5000 })
    return response.data?.success === true
  } catch {
    return false
  }
}

export async function getFirecrawlStatus(): Promise<FirecrawlStatusResponse> {
  try {
    const response = await axios.get(`${API_BASE_URL}/firecrawl/status`, { timeout: 8000 })
    return response.data
  } catch (error) {
    return handleAxiosError(error, '获取 Firecrawl 状态失败', {
      enabled: false,
      configured: false
    })
  }
}

export async function scrapeUrl(url: string): Promise<ScrapeResult> {
  try {
    const response = await axios.post(`${API_BASE_URL}/firecrawl/scrape`, { url }, { timeout: 90000 })
    return response.data
  } catch (error) {
    return handleAxiosError(error, '抓取网页失败')
  }
}

export async function getTemplates(params?: {
  q?: string
  category?: string
  limit?: number
}): Promise<TemplatesResponse> {
  try {
    const response = await axios.get(`${API_BASE_URL}/templates`, { params, timeout: 10000 })
    return response.data
  } catch (error) {
    return handleAxiosError(error, '获取模板列表失败', { templates: [], total: 0 })
  }
}

export async function getTemplateCategories(): Promise<TemplateCategoriesResponse> {
  try {
    const response = await axios.get(`${API_BASE_URL}/templates/categories`, { timeout: 10000 })
    return response.data
  } catch (error) {
    return handleAxiosError(error, '获取模板分类失败', { categories: [] })
  }
}

export async function getTemplateDetail(templateId: string): Promise<TemplateDetailResponse> {
  try {
    const response = await axios.get(`${API_BASE_URL}/templates/${templateId}`, { timeout: 10000 })
    return response.data
  } catch (error) {
    return handleAxiosError(error, '获取模板详情失败')
  }
}

// ==================== 大纲生成 API ====================

export async function generateOutline(
  topic: string,
  images?: File[],
  sourceContent?: string,
  templateRef?: TemplateReferencePayload
): Promise<OutlineResponse> {
  if (images && images.length > 0) {
    const formData = new FormData()
    formData.append('topic', topic)
    if (sourceContent) {
      formData.append('source_content', sourceContent)
    }
    if (templateRef) {
      formData.append('template_ref', JSON.stringify(templateRef))
    }
    images.forEach(file => formData.append('images', file))
    const response = await axios.post<OutlineResponse>(`${API_BASE_URL}/outline`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  }
  const response = await axios.post<OutlineResponse>(`${API_BASE_URL}/outline`, {
    topic,
    source_content: sourceContent || undefined,
    template_ref: templateRef || undefined
  })
  return response.data
}

export async function generateOutlineStream(
  params: OutlineStreamParams,
  onStart: (event: OutlineStreamStartEvent) => void,
  onFinish: (event: OutlineStreamFinishEvent) => void,
  onError: (event: { success: boolean; error?: string }) => void,
  onStreamError: (error: Error) => void
) {
  const { topic, images, sourceContent, templateRef, enableSearch } = params
  let body: FormData | Record<string, any>

  if (images && images.length > 0) {
    const formData = new FormData()
    formData.append('topic', topic)
    formData.append('enable_search', String(!!enableSearch))
    if (sourceContent) {
      formData.append('source_content', sourceContent)
    }
    if (templateRef) {
      formData.append('template_ref', JSON.stringify(templateRef))
    }
    images.forEach(file => formData.append('images', file))
    body = formData
  } else {
    body = {
      topic,
      enable_search: !!enableSearch,
      source_content: sourceContent || undefined,
      template_ref: templateRef || undefined
    }
  }

  await handleSSEStream(
    `${API_BASE_URL}/outline/stream`,
    body,
    {
      start: onStart,
      finish: onFinish,
      error: onError
    },
    onStreamError
  )
}

export async function editOutlineStream(
  params: OutlineEditStreamParams,
  onStart: (event: { success: boolean; mode: 'suggest_only' | 'revise'; message?: string }) => void,
  onPage: (event: OutlineEditStreamPageEvent) => void,
  onFinish: (event: OutlineEditStreamFinishEvent) => void,
  onError: (event: { success: boolean; mode: 'suggest_only' | 'revise'; error?: string }) => void,
  onStreamError: (error: Error) => void
) {
  await handleSSEStream(
    `${API_BASE_URL}/outline/edit/stream`,
    params,
    {
      start: onStart,
      page: onPage,
      finish: onFinish,
      error: onError
    },
    onStreamError
  )
}

// ==================== 图片生成 API ====================

export function getImageUrl(taskId: string, filename: string, thumbnail = true): string {
  return `${API_BASE_URL}/images/${taskId}/${filename}?thumbnail=${thumbnail}`
}

export async function regenerateImage(
  taskId: string,
  page: Page,
  useReference = true,
  context?: { fullOutline?: string; userTopic?: string }
): Promise<{ success: boolean; index: number; image_url?: string; error?: string }> {
  const response = await axios.post(`${API_BASE_URL}/regenerate`, {
    task_id: taskId,
    page,
    use_reference: useReference,
    full_outline: context?.fullOutline,
    user_topic: context?.userTopic
  })
  return response.data
}

export async function retryFailedImages(
  taskId: string,
  pages: Page[],
  onProgress: (event: ProgressEvent) => void,
  onComplete: (event: ProgressEvent) => void,
  onError: (event: ProgressEvent) => void,
  onFinish: (event: { success: boolean; total: number; completed: number; failed: number }) => void,
  onStreamError: (error: Error) => void
) {
  await handleSSEStream(
    `${API_BASE_URL}/retry-failed`,
    { task_id: taskId, pages },
    {
      retry_start: (data) => onProgress({ index: -1, status: 'generating', message: data.message }),
      complete: onComplete,
      error: onError,
      retry_finish: onFinish
    },
    onStreamError
  )
}

export async function generateImagesPost(
  pages: Page[],
  taskId: string | null,
  fullOutline: string,
  onProgress: (event: ProgressEvent) => void,
  onComplete: (event: ProgressEvent) => void,
  onError: (event: ProgressEvent) => void,
  onFinish: (event: FinishEvent) => void,
  onStreamError: (error: Error) => void,
  userImages?: File[],
  userTopic?: string
) {
  let userImagesBase64: string[] = []
  if (userImages && userImages.length > 0) {
    userImagesBase64 = await Promise.all(
      userImages.map(file => new Promise<string>((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve(reader.result as string)
        reader.onerror = reject
        reader.readAsDataURL(file)
      }))
    )
  }

  await handleSSEStream(
    `${API_BASE_URL}/generate`,
    {
      pages,
      task_id: taskId,
      full_outline: fullOutline,
      user_images: userImagesBase64.length > 0 ? userImagesBase64 : undefined,
      user_topic: userTopic || ''
    },
    { progress: onProgress, complete: onComplete, error: onError, finish: onFinish },
    onStreamError
  )
}

// ==================== 历史记录 API ====================

export async function createHistory(
  topic: string,
  outline: { raw: string; pages: Page[] },
  taskId?: string,
  content?: { titles: string[]; copywriting: string; tags: string[] }
): Promise<{ success: boolean; record_id?: string; error?: string }> {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/history`,
      { topic, outline, task_id: taskId, content },
      { timeout: 10000 }
    )
    return response.data
  } catch (error) {
    return handleAxiosError(error, '创建历史记录失败')
  }
}

export async function getHistoryList(
  page = 1,
  pageSize = 20,
  status?: string
): Promise<{
  success: boolean
  records: HistoryRecord[]
  total: number
  page: number
  page_size: number
  total_pages: number
  error?: string
}> {
  const defaultReturn = { records: [], total: 0, page: 1, page_size: pageSize, total_pages: 0 }
  try {
    const params: any = { page, page_size: pageSize }
    if (status) params.status = status
    const response = await axios.get(`${API_BASE_URL}/history`, { params, timeout: 10000 })
    return response.data
  } catch (error) {
    return handleAxiosError(error, '获取历史记录列表失败', defaultReturn)
  }
}

export async function getHistory(recordId: string): Promise<{
  success: boolean
  record?: HistoryDetail
  error?: string
}> {
  try {
    const response = await axios.get(`${API_BASE_URL}/history/${recordId}`, { timeout: 10000 })
    return response.data
  } catch (error) {
    return handleAxiosError(error, '获取历史记录详情失败')
  }
}

export async function updateHistory(
  recordId: string,
  data: UpdateHistoryParams
): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await axios.put(`${API_BASE_URL}/history/${recordId}`, data, { timeout: 10000 })
    return response.data
  } catch (error) {
    return handleAxiosError(error, '更新历史记录失败')
  }
}

export async function checkHistoryExists(recordId: string): Promise<boolean> {
  try {
    const response = await axios.get(`${API_BASE_URL}/history/${recordId}/exists`, { timeout: 5000 })
    return response.data.exists === true
  } catch {
    return false
  }
}

export async function deleteHistory(recordId: string): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await axios.delete(`${API_BASE_URL}/history/${recordId}`, { timeout: 10000 })
    return response.data
  } catch (error) {
    return handleAxiosError(error, '删除历史记录失败')
  }
}

export async function searchHistory(keyword: string): Promise<{
  success: boolean
  records: HistoryRecord[]
  error?: string
}> {
  try {
    const response = await axios.get(`${API_BASE_URL}/history/search`, { params: { keyword }, timeout: 10000 })
    return response.data
  } catch (error) {
    return handleAxiosError(error, '搜索历史记录失败', { records: [] })
  }
}

export async function getHistoryStats(): Promise<{
  success: boolean
  total: number
  by_status: Record<string, number>
  error?: string
}> {
  try {
    const response = await axios.get(`${API_BASE_URL}/history/stats`, { timeout: 10000 })
    return response.data
  } catch (error) {
    return handleAxiosError(error, '获取统计信息失败', { total: 0, by_status: {} })
  }
}

export async function scanAllTasks(): Promise<{
  success: boolean
  total_tasks?: number
  synced?: number
  failed?: number
  orphan_tasks?: string[]
  results?: any[]
  error?: string
}> {
  const response = await axios.post(`${API_BASE_URL}/history/scan-all`)
  return response.data
}

// ==================== 配置管理 API ====================

export interface Config {
  text_generation: { active_provider: string; providers: Record<string, any> }
  image_generation: { active_provider: string; providers: Record<string, any> }
  firecrawl?: {
    enabled: boolean
    api_key_masked?: string
    base_url?: string
    _has_api_key?: boolean
  }
}

export async function downloadHistoryZip(
  recordId: string,
  content?: { titles: string[]; copywriting: string; tags: string[] }
): Promise<{ blob: Blob; filename: string }> {
  const hasContent = Boolean(
    content && (
      (Array.isArray(content.titles) && content.titles.some(t => String(t || '').trim())) ||
      String(content.copywriting || '').trim() ||
      (Array.isArray(content.tags) && content.tags.some(t => String(t || '').trim()))
    )
  )

  const requestConfig = {
    responseType: 'blob' as const,
    timeout: 60000,
    params: { _: Date.now() }
  }

  const response = hasContent
    ? await axios.post(`${API_BASE_URL}/history/${recordId}/download`, { content }, requestConfig)
    : await axios.get(`${API_BASE_URL}/history/${recordId}/download`, requestConfig)

  const contentDisposition = String(response.headers['content-disposition'] || '')
  const filename = extractDownloadFilename(contentDisposition) || 'images.zip'

  return {
    blob: response.data,
    filename
  }
}

export async function getConfig(): Promise<{ success: boolean; config?: Config; error?: string }> {
  const response = await axios.get(`${API_BASE_URL}/config`)
  return response.data
}

export async function updateConfig(config: Partial<Config>): Promise<{ success: boolean; message?: string; error?: string }> {
  const response = await axios.post(`${API_BASE_URL}/config`, config)
  return response.data
}

export async function testConnection(config: {
  type: string
  provider_name?: string
  api_key?: string
  base_url?: string
  model?: string
  endpoint_type?: string
}): Promise<{ success: boolean; message?: string; error?: string }> {
  const response = await axios.post(`${API_BASE_URL}/config/test`, config)
  return response.data
}

// ==================== 内容生成 API ====================

export async function generateContent(
  topic: string,
  outline: string,
  recordId?: string
): Promise<ContentResponse> {
  const response = await axios.post<ContentResponse>(`${API_BASE_URL}/content`, {
    topic,
    outline,
    record_id: recordId
  })
  return response.data
}

// ==================== 发布 API (VibeSurf) ====================

export async function checkVibeSurfStatus(): Promise<{ success: boolean; status?: VibeSurfStatus; error?: string }> {
  try {
    const response = await axios.get(`${API_BASE_URL}/publish/status`, { timeout: 5000 })
    return response.data
  } catch (error) {
    return handleAxiosError(error, '检查状态失败')
  }
}

export async function checkXiaohongshuLogin(): Promise<{ success: boolean; status?: LoginStatus; error?: string }> {
  try {
    const response = await axios.get(`${API_BASE_URL}/publish/login-check`, { timeout: 10000 })
    return response.data
  } catch (error) {
    return handleAxiosError(error, '检查登录状态失败')
  }
}

export async function openXiaohongshuLogin(): Promise<{ success: boolean; message?: string; error?: string }> {
  try {
    const response = await axios.post(`${API_BASE_URL}/publish/login`, {}, { timeout: 30000 })
    return response.data
  } catch (error) {
    return handleAxiosError(error, '打开登录页面失败')
  }
}

export async function publishToXiaohongshu(
  data: PublishData,
  onProgress: (event: PublishProgressEvent) => void,
  onComplete: (event: PublishProgressEvent) => void,
  onError: (event: PublishProgressEvent) => void,
  onStreamError: (error: Error) => void
) {
  await handleSSEStream(
    `${API_BASE_URL}/publish/xiaohongshu`,
    data,
    { progress: onProgress, complete: onComplete, error: onError },
    onStreamError
  )
}

// ==================== 概念可视化历史 API ====================

export interface ConceptHistoryRecord {
  id: string
  title: string
  created_at: string
  updated_at: string
  status: string
  task_id: string
  style: string | null
  article_preview: string
  thumbnail: string | null
  image_count: number
}

export interface ConceptHistoryDetail extends ConceptHistoryRecord {
  article_full: string
  pipeline_data: {
    analyze: any
    map: any
    design: any
    generate: any
  }
}

export async function getConceptHistoryList(
  page = 1,
  pageSize = 20,
  status?: string
): Promise<{
  success: boolean
  data?: {
    records: ConceptHistoryRecord[]
    total: number
    page: number
    page_size: number
    total_pages: number
  }
  error?: string
}> {
  try {
    const params: any = { page, page_size: pageSize }
    if (status) params.status = status
    const response = await axios.get(`${API_BASE_URL}/concept/history`, { params, timeout: 10000 })
    return response.data
  } catch (error) {
    return handleAxiosError(error, '获取概念历史列表失败', { data: { records: [], total: 0, page: 1, page_size: pageSize, total_pages: 0 } })
  }
}

export async function getConceptHistory(recordId: string): Promise<{
  success: boolean
  data?: ConceptHistoryDetail
  error?: string
}> {
  try {
    const response = await axios.get(`${API_BASE_URL}/concept/history/${recordId}`, { timeout: 10000 })
    return response.data
  } catch (error) {
    return handleAxiosError(error, '获取概念历史详情失败')
  }
}

export async function deleteConceptHistory(recordId: string): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await axios.delete(`${API_BASE_URL}/concept/history/${recordId}`, { timeout: 10000 })
    return response.data
  } catch (error) {
    return handleAxiosError(error, '删除概念历史记录失败')
  }
}
