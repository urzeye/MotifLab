import { defineStore } from 'pinia'
import type { Page } from '../api'

export interface GeneratedImage {
  index: number
  url: string
  status: 'generating' | 'done' | 'error' | 'retrying'
  error?: string
  retryable?: boolean
}

export interface GeneratorState {
  // 当前阶段
  stage: 'input' | 'outline' | 'generating' | 'result'

  // 用户输入
  topic: string

  // 大纲数据
  outline: {
    raw: string
    pages: Page[]
  }

  // 生成进度
  progress: {
    current: number
    total: number
    status: 'idle' | 'generating' | 'done' | 'error'
  }

  // 生成结果
  images: GeneratedImage[]

  // 任务ID
  taskId: string | null

  // 历史记录ID
  recordId: string | null

  // 用户上传的图片（用于图片生成参考）
  userImages: File[]
}

export const useGeneratorStore = defineStore('generator', {
  state: (): GeneratorState => ({
    stage: 'input',
    topic: '',
    outline: {
      raw: '',
      pages: []
    },
    progress: {
      current: 0,
      total: 0,
      status: 'idle'
    },
    images: [],
    taskId: null,
    recordId: null,
    userImages: []
  }),

  actions: {
    // 设置主题
    setTopic(topic: string) {
      this.topic = topic
    },

    // 设置大纲
    setOutline(raw: string, pages: Page[]) {
      this.outline.raw = raw
      this.outline.pages = pages
      this.stage = 'outline'
    },

    // 更新页面
    updatePage(index: number, content: string) {
      const page = this.outline.pages.find(p => p.index === index)
      if (page) {
        page.content = content
        // 同步更新 raw 文本
        this.syncRawFromPages()
      }
    },

    // 根据 pages 重新生成 raw 文本
    syncRawFromPages() {
      this.outline.raw = this.outline.pages
        .map(page => page.content)
        .join('\n\n<page>\n\n')
    },

    // 删除页面
    deletePage(index: number) {
      this.outline.pages = this.outline.pages.filter(p => p.index !== index)
      // 重新索引
      this.outline.pages.forEach((page, idx) => {
        page.index = idx
      })
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    // 添加页面
    addPage(type: 'cover' | 'content' | 'summary', content: string = '') {
      const newPage: Page = {
        index: this.outline.pages.length,
        type,
        content
      }
      this.outline.pages.push(newPage)
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    // 插入页面
    insertPage(afterIndex: number, type: 'cover' | 'content' | 'summary', content: string = '') {
      const newPage: Page = {
        index: afterIndex + 1,
        type,
        content
      }
      this.outline.pages.splice(afterIndex + 1, 0, newPage)
      // 重新索引
      this.outline.pages.forEach((page, idx) => {
        page.index = idx
      })
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    // 移动页面 (拖拽排序)
    movePage(fromIndex: number, toIndex: number) {
      const pages = [...this.outline.pages]
      const [movedPage] = pages.splice(fromIndex, 1)
      pages.splice(toIndex, 0, movedPage)

      // 重新索引
      pages.forEach((page, idx) => {
        page.index = idx
      })

      this.outline.pages = pages
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    // 开始生成
    startGeneration() {
      this.stage = 'generating'
      this.progress.current = 0
      this.progress.total = this.outline.pages.length
      this.progress.status = 'generating'
      this.images = this.outline.pages.map(page => ({
        index: page.index,
        url: '',
        status: 'generating'
      }))
    },

    // 更新进度
    updateProgress(index: number, status: 'generating' | 'done' | 'error', url?: string, error?: string) {
      const image = this.images.find(img => img.index === index)
      if (image) {
        image.status = status
        if (url) image.url = url
        if (error) image.error = error
      }
      if (status === 'done') {
        this.progress.current++
      }
    },

    // 完成生成
    finishGeneration(taskId: string) {
      this.taskId = taskId
      this.stage = 'result'
      this.progress.status = 'done'
    },

    // 设置单个图片为重试中状态
    setImageRetrying(index: number) {
      const image = this.images.find(img => img.index === index)
      if (image) {
        image.status = 'retrying'
      }
    },

    // 获取失败的图片列表
    getFailedImages() {
      return this.images.filter(img => img.status === 'error')
    },

    // 获取失败图片对应的页面
    getFailedPages() {
      const failedIndices = this.images
        .filter(img => img.status === 'error')
        .map(img => img.index)
      return this.outline.pages.filter(page => failedIndices.includes(page.index))
    },

    // 检查是否有失败的图片
    hasFailedImages() {
      return this.images.some(img => img.status === 'error')
    },

    // 重置
    reset() {
      this.stage = 'input'
      this.topic = ''
      this.outline = {
        raw: '',
        pages: []
      }
      this.progress = {
        current: 0,
        total: 0,
        status: 'idle'
      }
      this.images = []
      this.taskId = null
      this.recordId = null
      this.userImages = []
    }
  }
})
