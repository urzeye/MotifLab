<template>
  <div class="container knowledge-container">
    <div class="page-header">
      <h1 class="page-title">知识库管理</h1>
      <p class="page-subtitle">管理理论框架、图表类型和视觉风格</p>
    </div>

    <!-- 选项卡 -->
    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="tab-btn"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        <component :is="tab.icon" />
        {{ tab.label }}
      </button>
    </div>

    <!-- 内容区 -->
    <div class="tab-content">
      <!-- 理论框架 -->
      <div v-if="activeTab === 'frameworks'" class="content-section">
        <div class="section-header">
          <h2>理论框架</h2>
          <p>用于概念分析和映射的理论框架库</p>
        </div>
        <div v-if="loading" class="loading">加载中...</div>
        <div v-else class="card-grid">
          <div v-for="framework in frameworks" :key="framework.id" class="knowledge-card">
            <h3>{{ framework.name }}</h3>
            <p class="card-desc">{{ framework.description }}</p>
            <div class="card-tags">
              <span v-for="domain in framework.domains" :key="domain" class="tag">{{ domain }}</span>
            </div>
            <div class="card-meta">
              <span>{{ framework.components?.length || 0 }} 个组件</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 图表类型 -->
      <div v-if="activeTab === 'charts'" class="content-section">
        <div class="section-header">
          <h2>图表类型</h2>
          <p>可视化输出的图表类型库</p>
        </div>
        <div v-if="loading" class="loading">加载中...</div>
        <div v-else class="card-grid">
          <div v-for="chart in chartTypes" :key="chart.id" class="knowledge-card">
            <h3>{{ chart.name }}</h3>
            <p class="card-desc">{{ chart.description }}</p>
            <div class="card-tags">
              <span v-for="use in chart.best_for" :key="use" class="tag">{{ use }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 视觉风格 -->
      <div v-if="activeTab === 'styles'" class="content-section">
        <div class="section-header">
          <h2>视觉风格</h2>
          <p>概念图的视觉风格预设</p>
        </div>
        <div v-if="loading" class="loading">加载中...</div>
        <div v-else class="style-grid">
          <div v-for="style in visualStyles" :key="style.id" class="style-card">
            <div class="style-preview" :style="getStylePreview(style)">
              <div class="preview-dot primary"></div>
              <div class="preview-dot secondary"></div>
              <div class="preview-line"></div>
            </div>
            <div class="style-info">
              <h3>{{ style.name }}</h3>
              <p>{{ style.description }}</p>
              <div class="color-swatches">
                <span
                  v-for="(color, key) in style.colors"
                  :key="key"
                  class="swatch"
                  :style="{ background: color }"
                  :title="key + ': ' + color"
                ></span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface Framework {
  id: string
  name: string
  description: string
  domains: string[]
  components?: string[]
}

interface ChartType {
  id: string
  name: string
  description: string
  best_for: string[]
}

interface VisualStyle {
  id: string
  name: string
  description: string
  colors: {
    primary: string
    secondary: string
    background: string
  }
}

const tabs = [
  { id: 'frameworks', label: '理论框架', icon: 'span' },
  { id: 'charts', label: '图表类型', icon: 'span' },
  { id: 'styles', label: '视觉风格', icon: 'span' },
]

const activeTab = ref('frameworks')
const loading = ref(true)
const frameworks = ref<Framework[]>([])
const chartTypes = ref<ChartType[]>([])
const visualStyles = ref<VisualStyle[]>([])

async function fetchKnowledge() {
  loading.value = true
  try {
    const [frameworksRes, chartsRes, stylesRes] = await Promise.all([
      fetch('/api/knowledge/frameworks').then(r => r.json()),
      fetch('/api/knowledge/chart-types').then(r => r.json()),
      fetch('/api/knowledge/visual-styles').then(r => r.json()),
    ])

    if (frameworksRes.success) {
      frameworks.value = frameworksRes.frameworks
    }
    if (chartsRes.success) {
      chartTypes.value = chartsRes.chart_types
    }
    if (stylesRes.success) {
      visualStyles.value = stylesRes.visual_styles
    }
  } catch (err) {
    console.error('Failed to fetch knowledge:', err)
  } finally {
    loading.value = false
  }
}

function getStylePreview(style: VisualStyle) {
  return {
    background: style.colors.background,
    '--primary': style.colors.primary,
    '--secondary': style.colors.secondary,
  }
}

onMounted(() => {
  fetchKnowledge()
})
</script>

<style scoped>
.knowledge-container {
  max-width: 1000px;
  padding-top: 24px;
}

.page-header {
  margin-bottom: 32px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 8px;
}

.page-subtitle {
  font-size: 15px;
  color: var(--text-sub);
}

/* Tabs */
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-sub);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.tab-btn.active {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
}

/* Content Section */
.section-header {
  margin-bottom: 24px;
}

.section-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 4px;
}

.section-header p {
  font-size: 14px;
  color: var(--text-sub);
}

.loading {
  text-align: center;
  padding: 48px;
  color: var(--text-sub);
}

/* Card Grid */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.knowledge-card {
  padding: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  transition: all 0.2s;
}

.knowledge-card:hover {
  border-color: var(--primary-light);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.knowledge-card h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 8px;
}

.card-desc {
  font-size: 13px;
  color: var(--text-sub);
  line-height: 1.5;
  margin-bottom: 12px;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.tag {
  font-size: 11px;
  padding: 3px 8px;
  background: var(--primary-fade);
  color: var(--primary);
  border-radius: var(--radius-xs);
}

.card-meta {
  font-size: 12px;
  color: var(--text-secondary);
}

/* Style Grid */
.style-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.style-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: all 0.2s;
}

.style-card:hover {
  border-color: var(--primary-light);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.style-preview {
  height: 100px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  position: absolute;
}

.preview-dot.primary {
  background: var(--primary);
  left: 30%;
}

.preview-dot.secondary {
  background: var(--secondary);
  right: 30%;
}

.preview-line {
  position: absolute;
  width: 40%;
  height: 2px;
  background: var(--primary);
  opacity: 0.5;
}

.style-info {
  padding: 16px;
}

.style-info h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 4px;
}

.style-info p {
  font-size: 12px;
  color: var(--text-sub);
  margin-bottom: 12px;
}

.color-swatches {
  display: flex;
  gap: 6px;
}

.swatch {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
}
</style>
