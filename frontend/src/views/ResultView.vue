<template>
  <div class="container">
    <div class="page-header">
      <div>
        <h1 class="page-title">创作完成</h1>
        <p class="page-subtitle">恭喜！你的小红书图文已生成完毕，共 {{ store.images.length }} 张</p>
      </div>
      <div style="display: flex; gap: 12px;">
        <button class="btn" @click="startOver" style="background: white; border: 1px solid var(--border-color);">
          再来一篇
        </button>
        <button class="btn" @click="downloadAll" style="background: white; border: 1px solid var(--border-color);">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
          一键下载
        </button>
        <button class="btn btn-primary" @click="goToPublish">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2L11 13"></path><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
          发布到小红书
        </button>
      </div>
    </div>

    <div class="card">
      <div class="grid-cols-4">
        <div v-for="image in store.images" :key="image.index" class="image-card group">
          <!-- Image Area -->
          <div
            v-if="image.url"
            class="result-image-wrap"
            @click="viewImage(image.url)"
          >
            <img
              :src="image.url"
              :alt="`第 ${image.index + 1} 页`"
              class="result-image"
            />
            <!-- Regenerating Overlay -->
            <div v-if="regeneratingIndex === image.index" class="result-image-overlay regenerating-overlay">
               <div class="spinner" style="width: 24px; height: 24px; border-width: 2px; border-color: var(--primary); border-top-color: transparent;"></div>
               <span style="font-size: 12px; color: var(--primary); margin-top: 8px; font-weight: 600;">重绘中...</span>
            </div>

            <!-- Hover Overlay -->
            <div v-else class="result-image-overlay hover-overlay">
              预览大图
            </div>
          </div>

          <!-- Action Bar -->
          <div class="result-image-footer">
            <span style="font-size: 12px; color: var(--text-sub);">Page {{ image.index + 1 }}</span>
            <div style="display: flex; gap: 8px;">
              <button
                class="image-action-btn"
                title="重新生成此图"
                @click="handleRegenerate(image)"
                :disabled="regeneratingIndex === image.index"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6"></path><path d="M1 20v-6h6"></path><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
              </button>
              <button
                class="image-action-btn download-btn"
                @click="downloadOne(image)"
              >
                下载
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 标题、文案、标签生成区域 -->
    <ContentDisplay />
  </div>
</template>

<style scoped>
/* 确保图片预览区域正确填充 */
.image-card > div:first-child {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.result-image-wrap {
  position: relative;
  aspect-ratio: 3 / 4;
  overflow: hidden;
  cursor: pointer;
  line-height: 0;
  background: var(--bg-elevated);
}

.result-image {
  width: 100%;
  height: 100%;
  display: block;
  vertical-align: top;
  object-fit: cover;
  transition: transform 0.3s;
}

.result-image-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 600;
  transition: opacity 0.2s;
}

.regenerating-overlay {
  flex-direction: column;
  background: rgba(10, 12, 18, 0.62);
  backdrop-filter: blur(2px);
  z-index: 10;
}

.hover-overlay {
  background: rgba(0, 0, 0, 0.38);
  opacity: 0;
}

.result-image-footer {
  padding: 12px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.image-action-btn {
  border: none;
  background: none;
  color: var(--text-sub);
  cursor: pointer;
  display: flex;
  align-items: center;
}

.image-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.download-btn {
  color: var(--primary);
  font-size: 12px;
}

.image-card:hover .hover-overlay {
  opacity: 1;
}
.image-card:hover img {
  transform: scale(1.05);
}
</style>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGeneratorStore } from '../stores/generator'
import { downloadHistoryZip, getHistory, regenerateImage, updateHistory } from '../api'
import ContentDisplay from '../components/result/ContentDisplay.vue'

const router = useRouter()
const route = useRoute()
const store = useGeneratorStore()
const regeneratingIndex = ref<number | null>(null)

const viewImage = (url: string) => {
  const baseUrl = url.split('?')[0]
  window.open(baseUrl + '?thumbnail=false', '_blank')
}

const startOver = () => {
  store.reset()
  router.push('/')
}

const goToPublish = () => {
  router.push('/redbook/publish')
}

const downloadOne = (image: any) => {
  if (image.url) {
    const link = document.createElement('a')
    const baseUrl = image.url.split('?')[0]
    link.href = baseUrl + '?thumbnail=false'
    link.download = `rednote_page_${image.index + 1}.png`
    link.click()
  }
}

function hasPersistableContent() {
  const hasTitles = Array.isArray(store.content.titles) && store.content.titles.some(t => String(t || '').trim())
  const hasCopywriting = Boolean(String(store.content.copywriting || '').trim())
  const hasTags = Array.isArray(store.content.tags) && store.content.tags.some(t => String(t || '').trim())
  return hasTitles || hasCopywriting || hasTags
}

async function syncContentToHistory() {
  if (!store.recordId || !hasPersistableContent()) return

  try {
    await updateHistory(store.recordId, {
      content: {
        titles: [...(store.content.titles || [])],
        copywriting: String(store.content.copywriting || ''),
        tags: [...(store.content.tags || [])]
      }
    })
  } catch (error) {
    console.error('下载前同步文案到历史记录失败:', error)
  }
}

const downloadAll = async () => {
  if (store.recordId) {
    await syncContentToHistory()

    const fallbackLink = document.createElement('a')
    fallbackLink.href = `/api/history/${store.recordId}/download?_=${Date.now()}`

    try {
      const contentPayload = hasPersistableContent()
        ? {
            titles: [...(store.content.titles || [])],
            copywriting: String(store.content.copywriting || ''),
            tags: [...(store.content.tags || [])]
          }
        : undefined

      const { blob, filename } = await downloadHistoryZip(store.recordId, contentPayload)
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('打包下载失败，回退到直链下载:', error)
      fallbackLink.click()
    }

    return
  }

  store.images.forEach((image, index) => {
    if (image.url) {
      setTimeout(() => {
        const link = document.createElement('a')
        const baseUrl = image.url.split('?')[0]
        link.href = baseUrl + '?thumbnail=false'
        link.download = `rednote_page_${image.index + 1}.png`
        link.click()
      }, index * 300)
    }
  })
}

const handleRegenerate = async (image: any) => {
  if (!store.taskId || regeneratingIndex.value !== null) return

  regeneratingIndex.value = image.index
  try {
    // Find the page content from outline
    const pageContent = store.outline.pages.find(p => p.index === image.index)
    if (!pageContent) {
       alert('无法找到对应页面的内容')
       return
    }

    // 构建上下文信息
    const context = {
      fullOutline: store.outline.raw || '',
      userTopic: store.topic || ''
    }

    const result = await regenerateImage(store.taskId, pageContent, true, context)
    if (result.success && result.image_url) {
       const newUrl = result.image_url
       store.updateImage(image.index, newUrl)

       // 将重绘结果同步到历史记录，避免刷新后展示旧图
       if (store.recordId) {
         try {
           const generated = store.outline.pages.map(p => {
             const img = store.images.find(i => i.index === p.index)
             if (img && img.status === 'done' && img.url) {
               return img.url.split('/').pop()?.split('?')[0] || ''
             }
             return ''
           })

           await updateHistory(store.recordId, {
             images: {
               task_id: store.taskId,
               generated
             }
           })
         } catch (e) {
           console.error('同步历史记录失败:', e)
         }
       }
    } else {
       alert('重绘失败: ' + (result.error || '未知错误'))
    }
  } catch (e: any) {
    alert('重绘失败: ' + e.message)
  } finally {
    regeneratingIndex.value = null
  }
}

function resolveRouteRecordId() {
  const queryId = typeof route.query.recordId === 'string' ? route.query.recordId.trim() : ''
  if (queryId) return queryId

  const paramId = typeof route.params.recordId === 'string' ? route.params.recordId.trim() : ''
  return paramId
}

async function hydrateFromHistoryRecord(recordId: string) {
  const res = await getHistory(recordId)
  if (!res.success || !res.record) {
    alert('无法加载结果页：历史记录不存在或已被删除')
    router.push('/history')
    return
  }

  const record = res.record
  store.setTopic(record.title)
  store.setOutline(record.outline.raw, record.outline.pages)
  store.setRecordId(record.id)

  if (record.content) {
    store.setContent(
      record.content.titles || [],
      record.content.copywriting || '',
      record.content.tags || []
    )
  } else {
    store.clearContent()
  }

  const taskId = record.images?.task_id || null
  const generated = Array.isArray(record.images?.generated) ? record.images.generated : []
  store.taskId = taskId

  if (taskId) {
    store.images = record.outline.pages.map((_, idx) => {
      const filename = generated[idx]
      return {
        index: idx,
        url: filename ? `/api/images/${taskId}/${filename}` : '',
        status: filename ? 'done' : 'error',
        retryable: !filename
      }
    })
    store.finishGeneration(taskId)
  } else {
    store.images = []
    store.stage = 'result'
  }
}

onMounted(async () => {
  const recordId = resolveRouteRecordId()
  if (!recordId) return
  await hydrateFromHistoryRecord(recordId)
})
</script>
