<template>
  <div class="container home-container">
    <!-- 图片网格轮播背景 -->
    <ShowcaseBackground />

    <!-- Hero Area -->
    <div class="hero-section">
      <div class="hero-content">
        <div class="brand-pill">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>
          AI 驱动的图文创作助手
        </div>
        <div class="platform-slogan">
          让传播不再需要门槛，让创作从未如此简单
        </div>
        <h1 class="page-title">灵感一触即发</h1>
        <p class="page-subtitle">输入你的创意主题，让 AI 帮你生成爆款标题、正文和封面图</p>
      </div>

      <div v-if="appliedTemplate" class="template-applied-banner">
        <div class="banner-left">
          <div class="banner-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 7h-9"></path>
              <path d="M14 17H5"></path>
              <circle cx="17" cy="17" r="3"></circle>
              <circle cx="7" cy="7" r="3"></circle>
            </svg>
          </div>
          <div class="banner-text">
            <div class="banner-title">
              已应用模板：{{ appliedTemplate.title }}
            </div>
            <div class="banner-sub">
              分类：{{ appliedTemplate.category }} · 将参考此模板的布局和风格，主题请自行输入
            </div>
          </div>
        </div>

        <div class="banner-actions">
          <button class="banner-btn" @click="openTemplateMarket">切换模板</button>
          <button class="banner-btn ghost" @click="clearTemplate">取消使用</button>
        </div>
      </div>

      <!-- 主题输入组合框 -->
      <ComposerInput
        ref="composerRef"
        v-model="topic"
        :loading="loading"
        :firecrawl-enabled="firecrawlEnabled"
        :page-count="pageCount"
        :enable-search="enableSearch"
        @update:pageCount="handlePageCountChange"
        @update:enableSearch="handleEnableSearchChange"
        @generate="handleGenerate"
        @imagesChange="handleImagesChange"
        @urlContentChange="handleUrlContentChange"
      />
    </div>

    <!-- 版权信息 -->
    <div class="page-footer">
      <div class="footer-tip">
        渲染AI - 让创作更简单
      </div>
      <div class="footer-copyright">
        © 2025 渲染AI (RenderAI)
      </div>
      <div class="footer-license">
        Licensed under <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/" target="_blank" rel="noopener noreferrer">CC BY-NC-SA 4.0</a>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-toast">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useGeneratorStore } from '../stores/generator'
import {
  generateOutlineStream,
  createHistory,
  getFirecrawlStatus,
  getTemplateDetail,
  type OutlineStreamFinishEvent,
  type ScrapeResult,
  type TemplateItem
} from '../api'

// 引入组件
import ShowcaseBackground from '../components/home/ShowcaseBackground.vue'
import ComposerInput from '../components/home/ComposerInput.vue'

const router = useRouter()
const route = useRoute()
const store = useGeneratorStore()

// 状态
const topic = ref('')
const loading = ref(false)
const error = ref('')
const composerRef = ref<InstanceType<typeof ComposerInput> | null>(null)

// 上传的图片文件
const uploadedImageFiles = ref<File[]>([])
// Firecrawl 状态
const firecrawlEnabled = ref(false)
const urlContent = ref<ScrapeResult | null>(null)
const appliedTemplate = ref<TemplateItem | null>(null)
const pageCount = ref(5)
const enableSearch = ref(false)

let templateRequestSeq = 0

async function checkFirecrawlStatus() {
  const result = await getFirecrawlStatus()
  firecrawlEnabled.value = result.success && !!result.enabled && !!result.configured
}

async function applyTemplateById(templateId: string) {
  const reqId = ++templateRequestSeq
  const result = await getTemplateDetail(templateId)
  if (reqId !== templateRequestSeq) return

  if (result.success && result.template) {
    appliedTemplate.value = result.template
    error.value = ''
  } else {
    appliedTemplate.value = null
    error.value = result.error || '模板加载失败，请重试'
  }
}

function openTemplateMarket() {
  router.push('/templates')
}

function clearTemplate() {
  appliedTemplate.value = null
  const query = { ...route.query }
  delete query.template_id
  router.replace({ path: '/redbook', query })
}

/**
 * 处理图片变化
 */
function handleImagesChange(images: File[]) {
  uploadedImageFiles.value = images
}

function handleUrlContentChange(content: ScrapeResult | null) {
  urlContent.value = content
}

function handlePageCountChange(value: number) {
  if (!Number.isFinite(value)) {
    pageCount.value = 5
    return
  }
  pageCount.value = Math.max(1, Math.min(15, Math.trunc(value)))
}

function handleEnableSearchChange(value: boolean) {
  enableSearch.value = !!value
}

function buildTopicWithPageCount(rawTopic: string, totalPages: number): string {
  const normalizedPages = Math.max(1, Math.min(15, Math.trunc(totalPages)))
  return (
    `${rawTopic}\n\n` +
    `【页数要求】必须严格生成 ${normalizedPages} 页（包括封面和总结页），总计 ${normalizedPages} 页，不得多也不得少。`
  )
}

/**
 * 生成大纲
 */
async function handleGenerate() {
  const rawTopic = topic.value.trim()
  if (!rawTopic) return

  loading.value = true
  error.value = ''

  try {
    const imageFiles = uploadedImageFiles.value
    const sourceContent = urlContent.value?.success ? urlContent.value.data?.content : undefined
    const topicForOutline = buildTopicWithPageCount(rawTopic, pageCount.value)
    const templateRef = appliedTemplate.value
      ? {
          id: appliedTemplate.value.id,
          title: appliedTemplate.value.title,
          category: appliedTemplate.value.category,
          description: appliedTemplate.value.description,
          prompt: appliedTemplate.value.prompt,
          stylePrompt: appliedTemplate.value.stylePrompt,
          tags: appliedTemplate.value.tags
        }
      : undefined

    const result = await new Promise<OutlineStreamFinishEvent>((resolve, reject) => {
      void generateOutlineStream(
        {
          topic: topicForOutline,
          images: imageFiles.length > 0 ? imageFiles : undefined,
          sourceContent,
          templateRef,
          enableSearch: enableSearch.value
        },
        () => {},
        (event) => resolve(event),
        (event) => resolve({ success: false, error: event.error || '生成大纲失败' }),
        (streamError) => reject(streamError)
      )
    })

    if (result.success && result.pages) {
      // 设置主题和大纲到 store
      store.setTopic(rawTopic)
      store.setOutline(result.outline || '', result.pages)

      // 大纲生成成功后，立即创建历史记录
      // 这样即使用户刷新页面或关闭浏览器，大纲也不会丢失
      try {
        const historyResult = await createHistory(
          rawTopic,
          {
            raw: result.outline || '',
            pages: result.pages
          }
        )

        // 保存历史记录 ID 到 store，后续生成正文和图片时会使用
        if (historyResult.success && historyResult.record_id) {
          store.setRecordId(historyResult.record_id)
        } else {
          // 创建历史记录失败，记录错误但不阻断流程
          console.error('创建历史记录失败:', historyResult.error || '未知错误')
          store.setRecordId(null)
        }
      } catch (err: any) {
        // 创建历史记录异常，记录错误但不阻断流程
        console.error('创建历史记录异常:', err.message || err)
        store.setRecordId(null)
      }

      // 保存用户上传的图片到 store
      if (imageFiles.length > 0) {
        store.userImages = imageFiles
      } else {
        store.userImages = []
      }

      // 清理 ComposerInput 的预览
      composerRef.value?.clearPreviews()
      composerRef.value?.clearUrlState?.()
      uploadedImageFiles.value = []
      urlContent.value = null

      router.push('/redbook/outline')
    } else {
      error.value = result.error || '生成大纲失败'
    }
  } catch (err: any) {
    error.value = err.message || '网络错误，请重试'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  checkFirecrawlStatus()
})

watch(
  () => route.query.template_id,
  (value) => {
    const templateId = Array.isArray(value) ? value[0] : value
    if (templateId && typeof templateId === 'string') {
      applyTemplateById(templateId)
    } else {
      appliedTemplate.value = null
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.home-container {
  max-width: 1100px;
  padding-top: 16px;
  position: relative;
  z-index: 1;
}

/* Hero Section - 深色模式优化 */
.hero-section {
  text-align: center;
  margin-bottom: 48px;
  padding: 56px 64px;
  animation: fadeIn 0.6s ease-out;
  background: var(--bg-card);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-color);
}

.hero-content {
  margin-bottom: 40px;
}

.template-applied-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
  padding: 14px 16px;
  border: 1px solid var(--primary);
  border-radius: var(--radius-md);
  background: linear-gradient(90deg, var(--primary-light), rgba(56, 189, 248, 0.08));
}

.banner-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.banner-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--primary);
  color: var(--primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 255, 136, 0.08);
}

.banner-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}

.banner-sub {
  font-size: 12px;
  color: var(--text-sub);
  margin-top: 2px;
}

.banner-actions {
  display: flex;
  gap: 8px;
}

.banner-btn {
  border: 1px solid var(--primary);
  background: var(--primary);
  color: var(--text-inverse);
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.banner-btn:hover {
  opacity: 0.92;
}

.banner-btn.ghost {
  background: transparent;
  color: var(--primary);
}

.brand-pill {
  display: inline-flex;
  align-items: center;
  padding: 8px 20px;
  background: var(--primary-fade);
  color: var(--primary);
  border-radius: var(--radius-sm);
  font-size: var(--small-size);
  font-weight: 600;
  margin-bottom: 24px;
  border: 1px solid var(--primary-light);
}

.platform-slogan {
  font-size: var(--h3-size);
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 28px;
  line-height: 1.4;
  letter-spacing: -0.01em;
}

.page-subtitle {
  font-size: var(--body-size);
  color: var(--text-sub);
  margin-top: 12px;
  line-height: var(--body-line-height);
}

/* Page Footer */
.page-footer {
  text-align: center;
  padding: 32px 0 20px;
  margin-top: 32px;
}

.footer-copyright {
  font-size: var(--small-size);
  color: var(--text-main);
  font-weight: 500;
  margin-bottom: 8px;
}

.footer-copyright a {
  color: var(--primary);
  text-decoration: none;
  font-weight: 600;
}

.footer-copyright a:hover {
  color: var(--primary-hover);
}

.footer-license {
  font-size: var(--caption-size);
  color: var(--text-secondary);
}

.footer-license a {
  color: var(--text-sub);
  text-decoration: none;
}

.footer-license a:hover {
  color: var(--primary);
}

.footer-tip {
  font-size: var(--small-size);
  color: var(--text-sub);
  margin-bottom: 12px;
}

/* Error Toast */
.error-toast {
  position: fixed;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  background: #EF4444;
  color: white;
  padding: 14px 28px;
  border-radius: var(--radius-sm);
  box-shadow: 0 8px 24px rgba(239, 68, 68, 0.4);
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 1000;
  animation: slideUp 0.3s ease-out;
}

/* Animations */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 900px) {
  .template-applied-banner {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
