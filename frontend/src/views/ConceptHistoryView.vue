<template>
  <div class="container" style="max-width: 1200px;">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">概念可视化历史</h1>
        <p class="page-subtitle">查看之前生成的概念图</p>
      </div>
      <button class="btn btn-primary" @click="router.push('/concept')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
        新建概念图
      </button>
    </div>

    <!-- Tabs -->
    <div class="tabs-container">
      <div
        class="tab-item"
        :class="{ active: currentTab === 'all' }"
        @click="switchTab('all')"
      >
        全部
      </div>
      <div
        class="tab-item"
        :class="{ active: currentTab === 'completed' }"
        @click="switchTab('completed')"
      >
        已完成
      </div>
      <div
        class="tab-item"
        :class="{ active: currentTab === 'error' }"
        @click="switchTab('error')"
      >
        失败
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
    </div>

    <!-- Empty State -->
    <div v-else-if="records.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
          <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
          <line x1="12" y1="22.08" x2="12" y2="12"></line>
        </svg>
      </div>
      <h3>暂无概念图记录</h3>
      <p>去创建一个新的概念图吧</p>
    </div>

    <!-- Record Grid -->
    <div v-else class="record-grid">
      <div
        v-for="record in records"
        :key="record.id"
        class="record-card"
        @click="viewRecord(record)"
      >
        <div class="card-thumbnail">
          <img
            v-if="record.thumbnail"
            :src="`/${record.thumbnail}`"
            :alt="record.title"
          />
          <div v-else class="no-thumbnail">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <circle cx="8.5" cy="8.5" r="1.5"></circle>
              <polyline points="21 15 16 10 5 21"></polyline>
            </svg>
          </div>
        </div>
        <div class="card-content">
          <h3 class="card-title">{{ record.title }}</h3>
          <p class="card-preview">{{ record.article_preview }}</p>
          <div class="card-meta">
            <span class="meta-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                <polyline points="21 15 16 10 5 21"></polyline>
              </svg>
              {{ record.image_count }} 张
            </span>
            <span class="meta-item">
              {{ formatDate(record.created_at) }}
            </span>
            <span :class="['status-badge', `status-${record.status}`]">
              {{ getStatusText(record.status) }}
            </span>
          </div>
        </div>
        <button class="delete-btn" @click.stop="confirmDelete(record)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="pagination">
      <button :disabled="currentPage === 1" @click="changePage(currentPage - 1)">上一页</button>
      <span>{{ currentPage }} / {{ totalPages }}</span>
      <button :disabled="currentPage === totalPages" @click="changePage(currentPage + 1)">下一页</button>
    </div>

    <!-- Detail Modal -->
    <div v-if="selectedRecord" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>{{ selectedRecord.title }}</h2>
          <button class="close-btn" @click="closeModal">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div class="modal-body">
          <!-- Images -->
          <div v-if="selectedRecord.pipeline_data?.generate?.results" class="images-section">
            <h3>生成的图片 ({{ selectedRecord.pipeline_data.generate.results.length }})</h3>
            <div class="images-grid">
              <div
                v-for="(img, idx) in selectedRecord.pipeline_data.generate.results"
                :key="idx"
                class="image-item"
                @click="openLightbox(idx)"
              >
                <img :src="`/${img.output_path}`" :alt="`概念图 ${idx + 1}`" />
                <div class="image-overlay">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    <line x1="11" y1="8" x2="11" y2="14"></line>
                    <line x1="8" y1="11" x2="14" y2="11"></line>
                  </svg>
                </div>
              </div>
            </div>
          </div>

          <!-- Analysis Results -->
          <div v-if="selectedRecord.pipeline_data?.analyze" class="analysis-section">
            <h3>分析结果</h3>
            <div class="theme-info">
              <strong>主题：</strong>{{ selectedRecord.pipeline_data.analyze.main_theme }}
            </div>
            <div v-if="selectedRecord.pipeline_data.analyze.key_concepts" class="concepts-list">
              <div
                v-for="concept in selectedRecord.pipeline_data.analyze.key_concepts"
                :key="concept.id"
                class="concept-item"
              >
                <span class="concept-name">{{ concept.name_cn || concept.name }}</span>
                <span class="concept-desc">{{ concept.description }}</span>
              </div>
            </div>
          </div>

          <!-- Original Article -->
          <div v-if="selectedRecord.article_full" class="article-section">
            <h3>原始文章</h3>
            <div class="article-content">{{ selectedRecord.article_full }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Image Lightbox -->
    <div v-if="lightboxOpen" class="lightbox-overlay" @click.self="closeLightbox">
      <button class="lightbox-close" @click="closeLightbox">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
      <button class="lightbox-nav lightbox-prev" @click="prevImage" :disabled="lightboxIndex === 0">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
      </button>
      <div class="lightbox-content">
        <img
          v-if="currentLightboxImage"
          :src="`/${currentLightboxImage.output_path}`"
          :alt="`概念图 ${lightboxIndex + 1}`"
        />
        <div class="lightbox-info">
          {{ lightboxIndex + 1 }} / {{ lightboxImages.length }}
          <span v-if="currentLightboxImage?.filename" class="lightbox-filename">
            {{ currentLightboxImage.filename }}
          </span>
        </div>
      </div>
      <button class="lightbox-nav lightbox-next" @click="nextImage" :disabled="lightboxIndex >= lightboxImages.length - 1">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getConceptHistoryList,
  getConceptHistory,
  deleteConceptHistory,
  type ConceptHistoryRecord,
  type ConceptHistoryDetail
} from '../api'

const router = useRouter()

const records = ref<ConceptHistoryRecord[]>([])
const loading = ref(false)
const currentTab = ref('all')
const currentPage = ref(1)
const totalPages = ref(1)
const selectedRecord = ref<ConceptHistoryDetail | null>(null)

// Lightbox state
const lightboxOpen = ref(false)
const lightboxIndex = ref(0)

const lightboxImages = computed(() => {
  return selectedRecord.value?.pipeline_data?.generate?.results || []
})

const currentLightboxImage = computed(() => {
  return lightboxImages.value[lightboxIndex.value] || null
})

function openLightbox(index: number) {
  lightboxIndex.value = index
  lightboxOpen.value = true
}

function closeLightbox() {
  lightboxOpen.value = false
}

function prevImage() {
  if (lightboxIndex.value > 0) {
    lightboxIndex.value--
  }
}

function nextImage() {
  if (lightboxIndex.value < lightboxImages.value.length - 1) {
    lightboxIndex.value++
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (!lightboxOpen.value) return
  if (e.key === 'Escape') closeLightbox()
  if (e.key === 'ArrowLeft') prevImage()
  if (e.key === 'ArrowRight') nextImage()
}

async function loadData() {
  loading.value = true
  try {
    const statusFilter = currentTab.value === 'all' ? undefined : currentTab.value
    const res = await getConceptHistoryList(currentPage.value, 12, statusFilter)
    if (res.success && res.data) {
      records.value = res.data.records
      totalPages.value = res.data.total_pages
    }
  } catch (e) {
    console.error('加载历史失败:', e)
  } finally {
    loading.value = false
  }
}

function switchTab(tab: string) {
  currentTab.value = tab
  currentPage.value = 1
  loadData()
}

function changePage(page: number) {
  currentPage.value = page
  loadData()
}

async function viewRecord(record: ConceptHistoryRecord) {
  const res = await getConceptHistory(record.id)
  if (res.success && res.data) {
    selectedRecord.value = res.data
  }
}

function closeModal() {
  selectedRecord.value = null
}

async function confirmDelete(record: ConceptHistoryRecord) {
  if (confirm('确定删除这条记录吗？相关图片也会被删除。')) {
    const res = await deleteConceptHistory(record.id)
    if (res.success) {
      loadData()
    } else {
      alert('删除失败: ' + (res.error || '未知错误'))
    }
  }
}

function formatDate(dateStr: string) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getStatusText(status: string) {
  const statusMap: Record<string, string> = {
    'draft': '草稿',
    'in_progress': '进行中',
    'completed': '已完成',
    'error': '失败'
  }
  return statusMap[status] || status
}

onMounted(() => {
  loadData()
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}

.page-subtitle {
  color: var(--text-sub);
  margin: 4px 0 0;
}

.tabs-container {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0;
}

.tab-item {
  padding: 10px 20px;
  cursor: pointer;
  color: var(--text-sub);
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab-item:hover {
  color: var(--text-main);
}

.tab-item.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
  font-weight: 500;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 60px;
}

.empty-state {
  text-align: center;
  padding: 80px 0;
  color: var(--text-sub);
}

.empty-icon {
  opacity: 0.5;
  margin-bottom: 16px;
}

.empty-state h3 {
  margin: 0 0 8px;
  color: var(--text-main);
}

.record-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.record-card {
  background: white;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.record-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  transform: translateY(-2px);
}

.card-thumbnail {
  height: 160px;
  background: #f5f5f5;
  overflow: hidden;
}

.card-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-thumbnail {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ccc;
}

.card-content {
  padding: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-preview {
  font-size: 13px;
  color: var(--text-sub);
  margin: 0 0 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-meta {
  display: flex;
  gap: 12px;
  align-items: center;
  font-size: 12px;
  color: var(--text-sub);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
}

.status-completed {
  background: #e8f5e9;
  color: #2e7d32;
}

.status-in_progress {
  background: #e3f2fd;
  color: #1565c0;
}

.status-error {
  background: #ffebee;
  color: #c62828;
}

.status-draft {
  background: #f5f5f5;
  color: #757575;
}

.delete-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(255,255,255,0.9);
  border: none;
  border-radius: 6px;
  padding: 6px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}

.record-card:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: #fee;
  color: #c00;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 40px;
}

.pagination button {
  padding: 8px 16px;
  border: 1px solid var(--border-color);
  background: white;
  border-radius: 6px;
  cursor: pointer;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 16px;
  max-width: 900px;
  max-height: 90vh;
  width: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1a1a1a;
}

.close-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  color: var(--text-sub);
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
}

.images-section,
.analysis-section,
.article-section {
  margin-bottom: 32px;
}

.images-section h3,
.analysis-section h3,
.article-section h3 {
  font-size: 16px;
  margin: 0 0 16px;
  color: #1a1a1a;
}

.images-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.image-item {
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  position: relative;
}

.image-item img {
  width: 100%;
  display: block;
  transition: transform 0.3s;
}

.image-item:hover img {
  transform: scale(1.05);
}

.image-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
  color: white;
}

.image-item:hover .image-overlay {
  opacity: 1;
}

.theme-info {
  margin-bottom: 16px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  color: #1a1a1a;
}

.concepts-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.concept-item {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  color: #1a1a1a;
}

.concept-name {
  font-weight: 600;
  display: block;
  margin-bottom: 4px;
  color: #1a1a1a;
}

.concept-desc {
  font-size: 13px;
  color: #666;
}

.article-content {
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  max-height: 60vh;
  overflow-y: auto;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.6;
  color: #333;
}

/* Lightbox */
.lightbox-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.95);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.lightbox-close {
  position: absolute;
  top: 20px;
  right: 20px;
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  padding: 8px;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.lightbox-close:hover {
  opacity: 1;
}

.lightbox-nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: white;
  cursor: pointer;
  padding: 16px;
  border-radius: 8px;
  opacity: 0.7;
  transition: opacity 0.2s, background 0.2s;
}

.lightbox-nav:hover:not(:disabled) {
  opacity: 1;
  background: rgba(255, 255, 255, 0.2);
}

.lightbox-nav:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.lightbox-prev {
  left: 20px;
}

.lightbox-next {
  right: 20px;
}

.lightbox-content {
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.lightbox-content img {
  max-width: 100%;
  max-height: 80vh;
  object-fit: contain;
  border-radius: 8px;
}

.lightbox-info {
  margin-top: 16px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
  text-align: center;
}

.lightbox-filename {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  opacity: 0.6;
}
</style>
