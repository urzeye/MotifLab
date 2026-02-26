<template>
  <div class="container outline-page-container">
    <div class="page-header outline-page-header">
      <div>
        <h1 class="page-title">编辑大纲</h1>
        <p class="page-subtitle">
          支持 Markdown 语法：`**加粗**`、`*斜体*`、`## 标题`
          <span v-if="isSaving" class="save-indicator saving">保存中...</span>
          <span v-else class="save-indicator saved">已保存</span>
        </p>
      </div>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="goBack" :disabled="revising">
          上一步
        </button>
        <button class="btn btn-primary" @click="startGeneration" :disabled="revising">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;"><path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"></path><line x1="16" y1="8" x2="2" y2="22"></line><line x1="17.5" y1="15" x2="9" y2="15"></line></svg>
          开始生成图片
        </button>
      </div>
    </div>

    <div class="outline-grid">
      <div
        v-for="(page, idx) in store.outline.pages"
        :key="page.index"
        class="card outline-card"
        :draggable="!revising && !isPageLoading(page.index)"
        @dragstart="onDragStart($event, idx)"
        @dragover.prevent="onDragOver($event, idx)"
        @drop="onDrop($event, idx)"
        :class="{ 'dragging-over': dragOverIndex === idx, 'card-loading': isPageLoading(page.index) }"
      >
        <div class="card-top-bar">
          <div class="page-info">
            <span class="page-number">P{{ idx + 1 }}</span>
            <span class="page-type" :class="page.type">{{ getPageTypeName(page.type) }}</span>
          </div>

          <div class="card-controls">
            <button
              class="icon-btn mode-btn"
              @click="togglePageMode(page.index)"
              :title="isPageInEditMode(page.index) ? '切换为预览模式' : '切换为编辑模式'"
              :disabled="isPageLoading(page.index)"
            >
              <svg v-if="isPageInEditMode(page.index)" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
              <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 20h9"></path>
                <path d="M16.5 3.5a2.1 2.1 0 1 1 3 3L7 19l-4 1 1-4Z"></path>
              </svg>
            </button>

            <button class="icon-btn" @click="triggerUpload(page.index)" title="上传参考图" :disabled="isPageLoading(page.index)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2"></rect>
                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                <polyline points="21 15 16 10 5 21"></polyline>
              </svg>
            </button>

            <div class="drag-handle" title="拖拽排序">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="2">
                <circle cx="9" cy="12" r="1"></circle>
                <circle cx="9" cy="5" r="1"></circle>
                <circle cx="9" cy="19" r="1"></circle>
                <circle cx="15" cy="12" r="1"></circle>
                <circle cx="15" cy="5" r="1"></circle>
                <circle cx="15" cy="19" r="1"></circle>
              </svg>
            </div>

            <button class="icon-btn danger" @click="deletePage(idx)" title="删除此页" :disabled="isPageLoading(page.index)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        </div>

        <input
          type="file"
          :ref="el => setFileInputRef(el, page.index)"
          style="display: none"
          accept="image/*"
          @change="handleImageUpload($event, page.index)"
        />

        <div v-if="page.user_image" class="reference-image-preview">
          <img :src="getPageImageSrc(page.user_image)" alt="参考图预览" />
          <button class="remove-btn" @click.stop="store.setPageImage(page.index, undefined)" title="移除参考图">×</button>
        </div>

        <div class="content-panel">
          <textarea
            v-if="isPageInEditMode(page.index)"
            v-model="page.content"
            class="textarea-paper"
            placeholder="在此输入文案..."
            :disabled="isPageLoading(page.index)"
            @input="store.updatePage(page.index, page.content)"
          />
          <div
            v-else
            class="markdown-preview"
            v-html="renderMarkdown(page.content)"
          ></div>
        </div>

        <div class="image-suggestion-card">
          <div class="suggestion-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2"></rect>
              <circle cx="8.5" cy="8.5" r="1.5"></circle>
              <polyline points="21 15 16 10 5 21"></polyline>
            </svg>
            配图建议
          </div>
          <div class="suggestion-content" :class="{ loading: suggestionSyncing && !page.image_suggestion }">
            {{ getImageSuggestionText(page, idx) }}
          </div>
        </div>

        <div class="word-count">{{ getContentWordCount(page.content) }} 字</div>

        <div v-if="isPageLoading(page.index)" class="page-loading-overlay">
          <div class="loading-orb"></div>
          <div class="loading-text">重生成中...</div>
        </div>
      </div>

      <div class="card add-card-dashed" @click="addPage('content')">
        <div class="add-content">
          <div class="add-icon">+</div>
          <span>添加页面</span>
        </div>
      </div>
    </div>

    <div class="revision-float-box">
      <input
        v-model="revisionRequest"
        type="text"
        class="revision-input"
        placeholder="输入修改需求，如“页数太多了，缩短到3页”"
        :disabled="revising"
        @keydown.enter.prevent="applyRevisionRequest"
      />
      <button
        class="revision-btn"
        :disabled="revising || !revisionRequest.trim()"
        @click="applyRevisionRequest"
      >
        {{ revising ? '重生成中...' : '确定修改' }}
      </button>
    </div>

    <div v-if="revisionMessage" class="revision-message">{{ revisionMessage }}</div>
    <div class="bottom-space"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGeneratorStore } from '../stores/generator'
import { updateHistory, createHistory, editOutlineStream, type Page } from '../api'

const router = useRouter()
const store = useGeneratorStore()

const dragOverIndex = ref<number | null>(null)
const draggedIndex = ref<number | null>(null)
const isSaving = ref(false)
const fileInputs = ref<Record<number, HTMLInputElement>>({})
const pageEditModeMap = ref<Record<number, boolean>>({})
const revisionRequest = ref('')
const revising = ref(false)
const revisionMessage = ref('')
const suggestionSyncing = ref(false)
const revisingPageMap = ref<Record<number, boolean>>({})

const setFileInputRef = (el: any, index: number) => {
  if (el) {
    fileInputs.value[index] = el as HTMLInputElement
  } else {
    delete fileInputs.value[index]
  }
}

const triggerUpload = (index: number) => {
  fileInputs.value[index]?.click()
}

const getPageImageSrc = (base64: string) => {
  if (base64.startsWith('data:image')) return base64
  return `data:image/png;base64,${base64}`
}

const handleImageUpload = (event: Event, index: number) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  if (file.size > 20 * 1024 * 1024) {
    alert('图片大小不能超过 20MB')
    input.value = ''
    return
  }

  const reader = new FileReader()
  reader.onload = (e) => {
    const result = e.target?.result as string
    store.setPageImage(index, result)
  }
  reader.readAsDataURL(file)
  input.value = ''
}

const getPageTypeName = (type: string) => {
  const names = { cover: '封面', content: '内容', summary: '总结' }
  return names[type as keyof typeof names] || '内容'
}

const onDragStart = (e: DragEvent, index: number) => {
  if (revising.value || isPageLoading(store.outline.pages[index]?.index ?? -1)) {
    e.preventDefault()
    return
  }
  draggedIndex.value = index
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.dropEffect = 'move'
  }
}

const onDragOver = (_e: DragEvent, index: number) => {
  if (revising.value) return
  if (draggedIndex.value === index) return
  dragOverIndex.value = index
}

const onDrop = (_e: DragEvent, index: number) => {
  if (revising.value) return
  dragOverIndex.value = null
  if (draggedIndex.value !== null && draggedIndex.value !== index) {
    store.movePage(draggedIndex.value, index)
  }
  draggedIndex.value = null
}

const deletePage = (index: number) => {
  if (confirm('确定要删除这一页吗？')) {
    store.deletePage(index)
  }
}

const addPage = (type: 'cover' | 'content' | 'summary') => {
  store.addPage(type, '')
  nextTick(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  })
}

const goBack = () => {
  router.back()
}

const startGeneration = async () => {
  if (saveTimer !== null) {
    clearTimeout(saveTimer)
    saveTimer = null
    await autoSaveOutline()
  }
  router.push('/redbook/generate')
}

const syncPageEditModeMap = () => {
  const next: Record<number, boolean> = {}
  store.outline.pages.forEach((page) => {
    next[page.index] = pageEditModeMap.value[page.index] ?? false
  })
  pageEditModeMap.value = next
}

const isPageInEditMode = (index: number) => !!pageEditModeMap.value[index]

const togglePageMode = (index: number) => {
  if (isPageLoading(index)) return
  pageEditModeMap.value[index] = !pageEditModeMap.value[index]
}

const isPageLoading = (index: number) => !!revisingPageMap.value[index]

const initRevisingPageLoading = (pages: Page[]) => {
  const next: Record<number, boolean> = {}
  pages.forEach((page, idx) => {
    const key = typeof page?.index === 'number' ? page.index : idx
    next[key] = true
  })
  revisingPageMap.value = next
}

const markPageLoaded = (index: number) => {
  revisingPageMap.value = {
    ...revisingPageMap.value,
    [index]: false
  }
}

const clearRevisingPageLoading = () => {
  revisingPageMap.value = {}
}

const upsertPageFromStream = (incoming: Page) => {
  const target = store.outline.pages.find((p) => p.index === incoming.index)
  if (target) {
    target.type = incoming.type
    target.content = incoming.content
    target.image_suggestion = incoming.image_suggestion
    return
  }

  store.outline.pages.push({ ...incoming })
  store.outline.pages.sort((a, b) => a.index - b.index)
}

const escapeHtml = (value: string) => value
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;')

const renderInlineMarkdown = (text: string) => {
  let html = escapeHtml(text)
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  html = html.replace(/~~([^~]+)~~/g, '<del>$1</del>')
  return html
}

const renderMarkdown = (markdown: string) => {
  if (!markdown || !markdown.trim()) {
    return '<p class="md-empty">点击右上角编辑按钮开始填写文案</p>'
  }

  const lines = markdown.replace(/\r\n/g, '\n').split('\n')
  let html = ''
  let inUl = false
  let inOl = false

  const closeLists = () => {
    if (inUl) {
      html += '</ul>'
      inUl = false
    }
    if (inOl) {
      html += '</ol>'
      inOl = false
    }
  }

  lines.forEach((rawLine) => {
    const line = rawLine.trim()

    if (!line) {
      closeLists()
      return
    }

    const h3Match = line.match(/^###\s+(.+)$/)
    if (h3Match) {
      closeLists()
      html += `<h3>${renderInlineMarkdown(h3Match[1])}</h3>`
      return
    }

    const h2Match = line.match(/^##\s+(.+)$/)
    if (h2Match) {
      closeLists()
      html += `<h2>${renderInlineMarkdown(h2Match[1])}</h2>`
      return
    }

    const h1Match = line.match(/^#\s+(.+)$/)
    if (h1Match) {
      closeLists()
      html += `<h1>${renderInlineMarkdown(h1Match[1])}</h1>`
      return
    }

    const ulMatch = line.match(/^[-*+]\s+(.+)$/)
    if (ulMatch) {
      if (inOl) {
        html += '</ol>'
        inOl = false
      }
      if (!inUl) {
        html += '<ul>'
        inUl = true
      }
      html += `<li>${renderInlineMarkdown(ulMatch[1])}</li>`
      return
    }

    const olMatch = line.match(/^\d+\.\s+(.+)$/)
    if (olMatch) {
      if (inUl) {
        html += '</ul>'
        inUl = false
      }
      if (!inOl) {
        html += '<ol>'
        inOl = true
      }
      html += `<li>${renderInlineMarkdown(olMatch[1])}</li>`
      return
    }

    closeLists()
    html += `<p>${renderInlineMarkdown(line)}</p>`
  })

  closeLists()
  return html
}

const extractPlainText = (markdown: string) => markdown
  .replace(/```[\s\S]*?```/g, ' ')
  .replace(/`[^`]+`/g, ' ')
  .replace(/!\[[^\]]*\]\([^)]+\)/g, ' ')
  .replace(/\[[^\]]*\]\([^)]+\)/g, ' ')
  .replace(/^#{1,6}\s+/gm, '')
  .replace(/^[-*+]\s+/gm, '')
  .replace(/^\d+\.\s+/gm, '')
  .replace(/\*\*([^*]+)\*\*/g, '$1')
  .replace(/\*([^*]+)\*/g, '$1')
  .replace(/~~([^~]+)~~/g, '$1')
  .replace(/\s+/g, ' ')
  .trim()

const getContentWordCount = (content: string) => {
  const plain = extractPlainText(content || '').replace(/\s+/g, '')
  return plain.length
}

const getImageSuggestionText = (page: Page, idx: number) => {
  const aiText = (page.image_suggestion || '').trim()
  if (aiText) return aiText
  if (suggestionSyncing.value) return '正在生成配图建议...'
  return `第 ${idx + 1} 页暂未生成配图建议，可点击底部“确定修改”或稍后重试。`
}

let saveTimer: number | null = null
let revisionMessageTimer: number | null = null

const clearRevisionMessage = () => {
  if (revisionMessageTimer !== null) {
    clearTimeout(revisionMessageTimer)
    revisionMessageTimer = null
  }
  revisionMessage.value = ''
}

const showRevisionMessage = (message: string, duration = 2600) => {
  clearRevisionMessage()
  revisionMessage.value = message
  if (duration > 0) {
    revisionMessageTimer = window.setTimeout(() => {
      revisionMessage.value = ''
      revisionMessageTimer = null
    }, duration)
  }
}

const autoSaveOutline = async () => {
  if (!store.recordId) {
    console.warn('未找到历史记录ID，无法自动保存')
    return
  }
  if (!store.outline.pages || store.outline.pages.length === 0) return

  try {
    isSaving.value = true
    const result = await updateHistory(store.recordId, {
      outline: { raw: store.outline.raw, pages: store.outline.pages }
    })
    if (!result.success) {
      console.error('自动保存失败:', result.error)
    }
  } catch (error) {
    console.error('自动保存出错:', error)
  } finally {
    isSaving.value = false
  }
}

const debouncedSave = () => {
  if (saveTimer !== null) clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => {
    autoSaveOutline()
    saveTimer = null
  }, 300)
}

const checkAndCreateHistory = async () => {
  if (store.recordId) return
  if (!store.outline.pages || store.outline.pages.length === 0) return

  try {
    const result = await createHistory(
      store.topic || '未命名主题',
      { raw: store.outline.raw, pages: store.outline.pages },
      store.taskId || undefined
    )
    if (result.success && result.record_id) {
      store.setRecordId(result.record_id)
    }
  } catch (error) {
    console.error('创建历史记录出错:', error)
  }
}

const normalizeStreamPage = (page: any, fallbackIndex: number): Page => {
  const type = String(page?.type || 'content')
  const safeType: 'cover' | 'content' | 'summary' =
    type === 'cover' || type === 'summary' ? type : 'content'
  return {
    index: typeof page?.index === 'number' ? page.index : fallbackIndex,
    type: safeType,
    content: String(page?.content || ''),
    image_suggestion: String(page?.image_suggestion || '').trim() || undefined
  }
}

const mergeSuggestionsIntoCurrentPages = (pages: Page[]) => {
  const suggestionMap = new Map<number, string>()
  pages.forEach((page, idx) => {
    const targetIndex = typeof page.index === 'number' ? page.index : idx
    const text = (page.image_suggestion || '').trim()
    if (text) suggestionMap.set(targetIndex, text)
  })

  store.outline.pages.forEach((page, idx) => {
    const text = suggestionMap.get(idx) || suggestionMap.get(page.index)
    if (text) {
      page.image_suggestion = text
    }
  })
}

const runOutlineEditStream = async (
  mode: 'suggest_only' | 'revise',
  revisionText: string,
  onPageEvent?: (page: Page) => void
): Promise<{ outline: string; pages: Page[] }> => {
  const streamedPages: Page[] = []

  return new Promise((resolve, reject) => {
    editOutlineStream(
      {
        topic: store.topic || '未命名主题',
        current_outline: store.outline.raw,
        current_pages: store.outline.pages,
        revision_request: revisionText,
        mode
      },
      () => {},
      (event) => {
        const normalized = normalizeStreamPage(event.page, streamedPages.length)
        streamedPages[normalized.index] = normalized
        onPageEvent?.(normalized)

        if (mode === 'suggest_only') {
          const target = store.outline.pages.find(p => p.index === normalized.index)
          if (target && normalized.image_suggestion) {
            target.image_suggestion = normalized.image_suggestion
          }
        }
      },
      (event) => {
        const pages = Array.isArray(event.pages) && event.pages.length > 0
          ? event.pages.map((page, idx) => normalizeStreamPage(page, idx))
          : streamedPages.filter(Boolean)
        resolve({
          outline: event.outline || store.outline.raw,
          pages
        })
      },
      (event) => {
        reject(new Error(event.error || '流式编辑失败'))
      },
      (error) => {
        reject(error)
      }
    )
  })
}

const syncSuggestionsWithAI = async () => {
  if (!store.outline.pages.length) return
  const missing = store.outline.pages.some(page => !(page.image_suggestion || '').trim())
  if (!missing) return

  suggestionSyncing.value = true
  clearRevisionMessage()
  try {
    const result = await runOutlineEditStream('suggest_only', '')
    mergeSuggestionsIntoCurrentPages(result.pages)
    if (store.recordId) {
      await updateHistory(store.recordId, {
        outline: { raw: store.outline.raw, pages: store.outline.pages }
      })
    }
    showRevisionMessage('已生成配图建议')
  } catch (error: any) {
    showRevisionMessage(error?.message || '生成配图建议失败', 4200)
  } finally {
    suggestionSyncing.value = false
  }
}

const applyRevisionRequest = async () => {
  if (!revisionRequest.value.trim() || revising.value) return
  if (!store.topic.trim()) {
    showRevisionMessage('缺少主题，无法重生成，请先返回首页输入主题。', 4200)
    return
  }

  if (saveTimer !== null) {
    clearTimeout(saveTimer)
    saveTimer = null
    await autoSaveOutline()
  }

  revising.value = true
  suggestionSyncing.value = true
  clearRevisionMessage()
  initRevisingPageLoading(store.outline.pages)

  try {
    const oldImages = store.outline.pages.map(page => page.user_image)
    const requestText = revisionRequest.value.trim()
    const result = await runOutlineEditStream('revise', requestText, (streamedPage) => {
      upsertPageFromStream(streamedPage)
      markPageLoaded(streamedPage.index)
    })

    if (!result.pages.length) {
      throw new Error('未返回有效页面数据')
    }

    const nextPages: Page[] = result.pages.map((page, idx) => ({
      ...page,
      index: idx,
      user_image: oldImages[idx]
    }))

    const nextRaw = result.outline || nextPages.map(page => page.content).join('\n\n<page>\n\n')
    store.setOutline(nextRaw, nextPages)
    syncPageEditModeMap()
    revisionRequest.value = ''

    if (store.recordId) {
      await updateHistory(store.recordId, {
        outline: { raw: store.outline.raw, pages: store.outline.pages }
      })
    }

    showRevisionMessage('已根据修改需求重新生成大纲')
  } catch (error: any) {
    showRevisionMessage(error?.message || '重新生成失败，请稍后重试', 4200)
  } finally {
    revising.value = false
    suggestionSyncing.value = false
    clearRevisingPageLoading()
  }
}

onMounted(() => {
  checkAndCreateHistory()
  syncPageEditModeMap()
  syncSuggestionsWithAI()
})

onUnmounted(() => {
  if (saveTimer !== null) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  clearRevisionMessage()
})

watch(
  () => store.outline.pages,
  () => {
    syncPageEditModeMap()
    if (!revising.value) {
      debouncedSave()
    }
  },
  { deep: true }
)
</script>

<style scoped>
.outline-page-container {
  max-width: 100%;
}

.outline-page-header {
  max-width: 1240px;
  margin: 0 auto 28px auto;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.save-indicator {
  margin-left: 12px;
  font-size: 12px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
  transition: all 0.3s ease;
}

.save-indicator.saving {
  color: #1890ff;
  background: #e6f7ff;
  border: 1px solid #91d5ff;
}

.save-indicator.saved {
  color: #52c41a;
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  opacity: 0.78;
}

.outline-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 24px;
  max-width: 1520px;
  margin: 0 auto;
  padding: 0 20px;
}

.outline-card {
  display: flex;
  flex-direction: column;
  padding: 18px;
  transition: all 0.2s ease;
  border: 1px solid var(--border-color);
  border-radius: 20px;
  background: var(--bg-card);
  box-shadow: var(--shadow-sm);
  min-height: 620px;
  position: relative;
}

.outline-card.card-loading .content-panel,
.outline-card.card-loading .image-suggestion-card,
.outline-card.card-loading .word-count {
  filter: grayscale(0.16);
  opacity: 0.66;
}

.outline-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
  border-color: var(--border-hover);
  z-index: 10;
}

.outline-card.dragging-over {
  border: 2px dashed var(--primary);
  opacity: 0.82;
}

.card-top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-color);
}

.page-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-number {
  min-width: 44px;
  height: 32px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.03em;
  color: #fff;
  background: linear-gradient(135deg, #ff5f6d, #ff3f5c);
  box-shadow: 0 6px 14px rgba(255, 79, 106, 0.3);
}

.page-type {
  font-size: 12px;
  padding: 5px 10px;
  border-radius: 8px;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.page-type.cover {
  color: #ff5f6d;
  background: rgba(255, 95, 109, 0.14);
}

.page-type.content {
  color: var(--text-sub);
  background: var(--bg-elevated);
}

.page-type.summary {
  color: #52c41a;
  background: rgba(82, 196, 26, 0.12);
}

.card-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  opacity: 0.45;
  transition: opacity 0.2s;
}

.outline-card:hover .card-controls {
  opacity: 1;
}

.drag-handle {
  cursor: grab;
  padding: 2px;
  color: var(--text-placeholder);
}

.drag-handle:active {
  cursor: grabbing;
}

.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-sub);
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
}

.icon-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  color: var(--text-placeholder);
}

.icon-btn:disabled:hover {
  color: var(--text-placeholder);
}

.icon-btn:hover {
  color: var(--primary);
}

.icon-btn.mode-btn:hover {
  color: #ff5f6d;
}

.icon-btn.danger:hover {
  color: #ef4444;
}

.reference-image-preview {
  margin-bottom: 12px;
  position: relative;
  width: 84px;
  height: 112px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border-color);
  background: var(--bg-elevated);
}

.reference-image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 18px;
  height: 18px;
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: rgba(0, 0, 0, 0.58);
  color: #fff;
  line-height: 1;
}

.remove-btn:hover {
  background: rgba(239, 68, 68, 0.92);
}

.content-panel {
  flex: 1;
  min-height: 250px;
  display: flex;
  flex-direction: column;
}

.textarea-paper {
  width: 100%;
  flex: 1;
  min-height: 300px;
  height: 100%;
  border: 1px solid var(--border-color);
  background: transparent;
  padding: 12px;
  font-size: 16px;
  line-height: 1.72;
  color: var(--text-main);
  resize: none;
  overflow-y: auto;
  font-family: inherit;
  border-radius: 10px;
}

.textarea-paper::placeholder {
  color: var(--text-placeholder);
}

.textarea-paper:focus {
  outline: none;
  border-color: #ff5f6d;
  box-shadow: 0 0 0 2px rgba(255, 95, 109, 0.14);
}

.markdown-preview {
  flex: 1;
  min-height: 300px;
  border: 1px solid rgba(255, 95, 109, 0.2);
  border-radius: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  line-height: 1.75;
  font-size: 16px;
  color: var(--text-main);
  overflow: auto;
}

.markdown-preview :deep(h1) {
  font-size: 34px;
  margin: 6px 0 12px;
}

.markdown-preview :deep(h2) {
  font-size: 26px;
  margin: 6px 0 10px;
}

.markdown-preview :deep(h3) {
  font-size: 20px;
  margin: 6px 0 8px;
}

.markdown-preview :deep(p) {
  margin: 0 0 10px;
  color: var(--text-main);
}

.markdown-preview :deep(ul),
.markdown-preview :deep(ol) {
  padding-left: 24px;
  margin: 0 0 10px;
}

.markdown-preview :deep(li) {
  margin: 3px 0;
}

.markdown-preview :deep(code) {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 6px;
  background: rgba(255, 95, 109, 0.12);
  color: #ff8a9b;
  font-size: 14px;
}

.markdown-preview :deep(.md-empty) {
  color: var(--text-placeholder);
}

.image-suggestion-card {
  margin-top: 14px;
  border: 1px solid rgba(255, 95, 109, 0.22);
  border-radius: 14px;
  background: rgba(255, 95, 109, 0.04);
  padding: 10px 10px 12px;
}

.suggestion-title {
  font-size: 14px;
  color: #ff6478;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.suggestion-content {
  max-height: 96px;
  overflow: auto;
  font-size: 15px;
  line-height: 1.7;
  color: var(--text-sub);
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(255, 95, 109, 0.18);
  background: rgba(255, 255, 255, 0.02);
}

.suggestion-content.loading {
  color: var(--text-secondary);
  font-style: italic;
}

.word-count {
  text-align: right;
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 8px;
}

.page-loading-overlay {
  position: absolute;
  inset: 12px;
  border-radius: 16px;
  border: 1px solid rgba(255, 95, 109, 0.28);
  background: linear-gradient(145deg, rgba(19, 20, 30, 0.78), rgba(28, 22, 30, 0.78));
  backdrop-filter: blur(4px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  z-index: 30;
  pointer-events: auto;
  overflow: hidden;
}

.page-loading-overlay::after {
  content: '';
  position: absolute;
  inset: -40% -10%;
  background: linear-gradient(
    110deg,
    transparent 38%,
    rgba(255, 255, 255, 0.08) 50%,
    transparent 62%
  );
  transform: translateX(-120%);
  animation: pageSheen 1.8s ease-in-out infinite;
}

.loading-orb {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 2px solid rgba(255, 95, 109, 0.24);
  border-top-color: #ff6e7f;
  box-shadow: 0 0 20px rgba(255, 95, 109, 0.3);
  animation: pageSpin 0.9s linear infinite;
}

.loading-text {
  font-size: 13px;
  color: #ffd6dc;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.add-card-dashed {
  border: 2px dashed var(--border-color);
  background: transparent;
  box-shadow: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  min-height: 620px;
  color: var(--text-placeholder);
  transition: all 0.2s;
}

.add-card-dashed:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: var(--primary-fade);
}

.add-content {
  text-align: center;
}

.add-icon {
  font-size: 34px;
  font-weight: 300;
  margin-bottom: 8px;
}

.revision-float-box {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 22px;
  width: min(760px, calc(100vw - 42px));
  background: rgba(25, 25, 28, 0.96);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 95, 109, 0.22);
  border-radius: 18px;
  padding: 10px;
  display: flex;
  gap: 10px;
  z-index: 90;
  box-shadow: 0 18px 36px rgba(0, 0, 0, 0.28);
}

.revision-input {
  flex: 1;
  height: 44px;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  background: var(--bg-elevated);
  color: var(--text-main);
  font-size: 14px;
  padding: 0 16px;
}

.revision-input:focus {
  outline: none;
  border-color: #ff5f6d;
  box-shadow: 0 0 0 2px rgba(255, 95, 109, 0.16);
}

.revision-btn {
  height: 44px;
  min-width: 126px;
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, #ff5f6d, #ff3f5c);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.revision-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.revision-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.revision-message {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 86px;
  color: #ffd8de;
  background: rgba(255, 95, 109, 0.18);
  border: 1px solid rgba(255, 95, 109, 0.35);
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 12px;
  z-index: 91;
  pointer-events: none;
}

.bottom-space {
  height: 150px;
}

@media (max-width: 980px) {
  .outline-grid {
    grid-template-columns: 1fr;
    padding: 0;
  }

  .outline-card,
  .add-card-dashed {
    min-height: 520px;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .revision-float-box {
    width: calc(100vw - 28px);
    bottom: 14px;
  }

  .revision-btn {
    min-width: 102px;
  }
}

@keyframes pageSpin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes pageSheen {
  0% {
    transform: translateX(-120%);
  }
  60% {
    transform: translateX(120%);
  }
  100% {
    transform: translateX(120%);
  }
}
</style>
