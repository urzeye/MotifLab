<template>
  <div class="container market-container">
    <section class="market-hero">
      <div class="hero-badge">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M20 7h-9"></path>
          <path d="M14 17H5"></path>
          <circle cx="17" cy="17" r="3"></circle>
          <circle cx="7" cy="7" r="3"></circle>
        </svg>
        热门模板持续更新
      </div>
      <h1 class="page-title">模板市集</h1>
      <p class="hero-subtitle">搜索灵感、按分类筛选，预览后可一键带入创作中心。</p>
    </section>

    <section class="toolbar-card">
      <div class="search-input-wrap">
        <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
        <input
          v-model="keyword"
          class="market-search-input"
          type="text"
          placeholder="搜索模板标题、描述或标签..."
          autocomplete="off"
        />
      </div>

      <div class="toolbar-meta">
        <span class="result-text">
          {{ loading ? '加载中...' : `共 ${total} 个模板` }}
        </span>
        <RouterLink class="btn btn-secondary jump-btn" to="/redbook">
          去创作中心
        </RouterLink>
      </div>
    </section>

    <section class="category-row">
      <button
        v-for="item in categories"
        :key="item.name"
        class="category-pill"
        :class="{ active: selectedCategory === item.name }"
        @click="selectCategory(item.name)"
      >
        <span>{{ item.name }}</span>
        <span class="count">{{ item.count }}</span>
      </button>
    </section>

    <section v-if="error" class="error-msg">{{ error }}</section>

    <section v-if="loading" class="loading-block">
      <div class="spinner"></div>
    </section>

    <section v-else-if="templates.length === 0" class="empty-card">
      <h3>没有找到匹配模板</h3>
      <p>换个关键词试试，或切换到「全部」分类。</p>
    </section>

    <section v-else class="template-grid">
      <article
        v-for="item in templates"
        :key="item.id"
        class="template-card"
      >
        <div class="cover-wrap">
          <img :src="item.coverImage" :alt="item.title" class="cover-image" loading="lazy" />
          <div class="card-badges">
            <span v-if="item.isNew" class="badge-new">NEW</span>
            <span v-if="item.isHot" class="badge-hot">HOT</span>
          </div>
        </div>

        <div class="card-content">
          <div class="card-top">
            <span class="category-mini">{{ item.category }}</span>
            <span class="usage-mini">已使用 {{ formatUsage(item.usageCount) }}</span>
          </div>

          <h3 class="card-title">{{ item.title }}</h3>
          <p class="card-desc">{{ item.description }}</p>

          <div class="tag-row">
            <span
              v-for="tag in item.tags.slice(0, 3)"
              :key="`${item.id}-${tag}`"
              class="tag-mini"
            >
              #{{ tag }}
            </span>
          </div>

          <div class="card-actions">
            <button class="btn btn-secondary action-btn" @click="openPreview(item)">
              预览模板
            </button>
            <button class="btn btn-primary action-btn" @click="useTemplate(item)">
              使用模板
            </button>
          </div>
        </div>
      </article>
    </section>

    <TemplatePreviewModal
      :visible="previewVisible"
      :template="activeTemplate"
      :applying="applying"
      @close="closePreview"
      @apply="useTemplate"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import {
  getTemplateCategories,
  getTemplates,
  type TemplateCategory,
  type TemplateItem
} from '../api'
import TemplatePreviewModal from '../components/template/TemplatePreviewModal.vue'

const router = useRouter()

const templates = ref<TemplateItem[]>([])
const categories = ref<TemplateCategory[]>([{ name: '全部', count: 0 }])
const selectedCategory = ref('全部')
const keyword = ref('')
const total = ref(0)
const loading = ref(false)
const error = ref('')

const previewVisible = ref(false)
const activeTemplate = ref<TemplateItem | null>(null)
const applying = ref(false)

const normalizedCategory = computed(() =>
  selectedCategory.value === '全部' ? '' : selectedCategory.value
)

let requestSeq = 0
let keywordDebounceTimer: number | null = null

async function loadCategories() {
  const response = await getTemplateCategories()
  if (!response.success) {
    return
  }

  const sum = response.categories.reduce((acc, item) => acc + (item.count || 0), 0)
  categories.value = [{ name: '全部', count: sum }, ...response.categories]
}

async function loadTemplates() {
  const reqId = ++requestSeq
  loading.value = true
  error.value = ''

  const response = await getTemplates({
    q: keyword.value.trim() || undefined,
    category: normalizedCategory.value || undefined
  })

  if (reqId !== requestSeq) {
    return
  }

  if (response.success) {
    templates.value = response.templates || []
    total.value = response.total || 0
  } else {
    templates.value = []
    total.value = 0
    error.value = response.error || '获取模板失败，请稍后重试'
  }

  loading.value = false
}

function selectCategory(name: string) {
  if (selectedCategory.value === name) return
  selectedCategory.value = name
}

function openPreview(template: TemplateItem) {
  activeTemplate.value = template
  previewVisible.value = true
}

function closePreview() {
  previewVisible.value = false
  activeTemplate.value = null
}

async function useTemplate(template: TemplateItem) {
  applying.value = true
  try {
    await router.push({
      path: '/redbook',
      query: { template_id: template.id }
    })
  } finally {
    applying.value = false
    closePreview()
  }
}

function formatUsage(value: number | undefined): string {
  return Number(value || 0).toLocaleString('zh-CN')
}

watch(selectedCategory, () => {
  loadTemplates()
})

watch(keyword, () => {
  if (keywordDebounceTimer !== null) {
    clearTimeout(keywordDebounceTimer)
  }
  keywordDebounceTimer = window.setTimeout(() => {
    loadTemplates()
    keywordDebounceTimer = null
  }, 280)
})

onMounted(async () => {
  await loadCategories()
  await loadTemplates()
})
</script>

<style scoped>
.market-container {
  max-width: 1320px;
  padding-top: 6px;
  padding-bottom: 24px;
}

.market-hero {
  background:
    radial-gradient(1000px 200px at 20% -20%, rgba(0, 255, 136, 0.14), transparent),
    radial-gradient(900px 250px at 90% 0, rgba(56, 189, 248, 0.1), transparent),
    var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 36px 34px 30px;
  margin-bottom: 22px;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--primary);
  background: var(--primary-light);
  border: 1px solid var(--primary);
  font-size: 12px;
  font-weight: 600;
  border-radius: 999px;
  padding: 6px 12px;
  margin-bottom: 14px;
}

.hero-subtitle {
  color: var(--text-sub);
  font-size: 16px;
  margin-top: 8px;
}

.toolbar-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.search-input-wrap {
  flex: 1;
  min-width: 220px;
  position: relative;
}

.search-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-secondary);
  pointer-events: none;
}

.market-search-input {
  width: 100%;
  height: 46px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background: var(--bg-input);
  color: var(--text-main);
  padding: 0 14px 0 42px;
  font-size: 15px;
  transition: all var(--transition-fast);
}

.market-search-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-fade);
}

.toolbar-meta {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.result-text {
  font-size: 13px;
  color: var(--text-sub);
}

.jump-btn {
  min-width: 116px;
  padding: 10px 16px;
  font-size: 14px;
}

.category-row {
  display: flex;
  align-items: center;
  gap: 10px;
  overflow-x: auto;
  padding: 3px 2px 8px;
  margin-bottom: 14px;
}

.category-pill {
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-sub);
  border-radius: 999px;
  padding: 9px 14px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.category-pill .count {
  min-width: 22px;
  padding: 0 6px;
  height: 20px;
  border-radius: 999px;
  background: var(--bg-elevated);
  color: var(--text-secondary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.category-pill:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.category-pill.active {
  border-color: var(--primary);
  background: var(--primary-light);
  color: var(--primary);
}

.category-pill.active .count {
  background: rgba(0, 255, 136, 0.16);
  color: var(--primary);
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.template-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  overflow: hidden;
  background: linear-gradient(180deg, rgba(22, 22, 26, 1), rgba(18, 18, 22, 1));
  transition: transform var(--transition-fast), border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.template-card:hover {
  transform: translateY(-4px);
  border-color: var(--primary);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.28);
}

.cover-wrap {
  position: relative;
  aspect-ratio: 3 / 4;
  background: var(--bg-elevated);
}

.cover-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.card-badges {
  position: absolute;
  left: 10px;
  top: 10px;
  display: flex;
  gap: 6px;
}

.badge-new,
.badge-hot {
  font-size: 10px;
  font-weight: 700;
  padding: 4px 7px;
  border-radius: 999px;
  line-height: 1;
}

.badge-new {
  color: #67e8f9;
  background: rgba(103, 232, 249, 0.14);
  border: 1px solid rgba(103, 232, 249, 0.5);
}

.badge-hot {
  color: #fb7185;
  background: rgba(251, 113, 133, 0.14);
  border: 1px solid rgba(251, 113, 133, 0.45);
}

.card-content {
  padding: 14px;
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.category-mini {
  font-size: 12px;
  color: var(--primary);
  background: var(--primary-light);
  border: 1px solid rgba(0, 255, 136, 0.35);
  border-radius: 999px;
  padding: 4px 8px;
}

.usage-mini {
  font-size: 12px;
  color: var(--text-secondary);
}

.card-title {
  margin: 12px 0 8px;
  font-size: 18px;
  line-height: 1.4;
}

.card-desc {
  color: var(--text-sub);
  font-size: 14px;
  line-height: 1.65;
  min-height: 45px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tag-row {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-mini {
  font-size: 11px;
  color: var(--text-sub);
  border: 1px solid var(--border-color);
  border-radius: 999px;
  padding: 4px 8px;
}

.card-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 14px;
}

.action-btn {
  font-size: 13px;
  padding: 10px 8px;
}

.loading-block,
.empty-card {
  margin-top: 8px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  min-height: 210px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 10px;
}

.empty-card h3 {
  font-size: 22px;
  margin: 0;
}

.empty-card p {
  color: var(--text-sub);
}

@media (max-width: 900px) {
  .toolbar-card {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-meta {
    justify-content: space-between;
  }

  .template-grid {
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  }
}
</style>
