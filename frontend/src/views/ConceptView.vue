<template>
  <div class="container concept-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">概念可视化</h1>
        <p class="page-subtitle">
          {{ currentStepDescription }}
        </p>
      </div>
      <router-link to="/" class="btn btn-secondary">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
        返回首页
      </router-link>
    </div>

    <!-- Step Indicator -->
    <div class="step-indicator">
      <div
        v-for="(step, index) in steps"
        :key="step.id"
        class="step"
        :class="{
          'active': currentStep === index,
          'completed': currentStep > index,
          'error': step.error
        }"
      >
        <div class="step-number">
          <span v-if="currentStep > index && !step.error">✓</span>
          <span v-else-if="step.error">!</span>
          <span v-else>{{ index + 1 }}</span>
        </div>
        <div class="step-info">
          <span class="step-name">{{ step.name }}</span>
          <span class="step-desc">{{ step.description }}</span>
        </div>
      </div>
    </div>

    <!-- Step 0: Input -->
    <div v-if="currentStep === 0" class="card">
      <h3 class="card-title">输入文章内容</h3>
      <p class="card-desc">粘贴需要可视化的文章内容，支持中英文。</p>

      <div class="form-group">
        <label>文章内容</label>
        <textarea
          v-model="articleText"
          class="form-textarea"
          placeholder="在此粘贴文章内容..."
          rows="12"
        ></textarea>
        <span class="char-count">{{ articleText.length }} 字符</span>
      </div>

      <div class="form-group">
        <label>视觉风格</label>
        <div class="style-selector">
          <div
            v-for="style in visualStyles"
            :key="style.id"
            class="style-option"
            :class="{ selected: selectedStyle === style.id }"
            @click="selectedStyle = style.id"
          >
            <div class="style-preview" :style="{ background: style.colors?.primary || '#2F3337' }"></div>
            <span class="style-name">{{ style.name }}</span>
          </div>
        </div>
      </div>

      <div class="form-actions">
        <button
          class="btn btn-primary btn-lg"
          @click="startPipeline"
          :disabled="!articleText.trim() || isRunning"
        >
          <span v-if="isRunning" class="spinner-sm"></span>
          {{ isRunning ? '处理中...' : '开始分析' }}
        </button>
      </div>
    </div>

    <!-- Step 1: Analyze Results -->
    <div v-else-if="currentStep === 1 && analyzeResult" class="card">
      <h3 class="card-title">
        <span class="step-badge">Step 1</span>
        概念分析结果
      </h3>

      <div class="result-section">
        <h4>文章主题</h4>
        <p class="main-theme">{{ analyzeResult.main_theme }}</p>
      </div>

      <div class="result-section">
        <h4>核心概念 ({{ analyzeResult.key_concepts?.length || 0 }})</h4>
        <div class="concept-list">
          <div v-for="concept in analyzeResult.key_concepts" :key="concept.id" class="concept-card">
            <div class="concept-header">
              <span class="concept-name">{{ concept.name_cn || concept.name }}</span>
              <span class="viz-type">{{ concept.visualization_type }}</span>
            </div>
            <p class="concept-desc">{{ concept.description }}</p>
            <p class="concept-quote" v-if="concept.key_quote">
              "{{ truncate(concept.key_quote, 100) }}"
            </p>
          </div>
        </div>
      </div>

      <div v-if="isRunning" class="processing-indicator">
        <div class="spinner"></div>
        <span>正在映射理论框架...</span>
      </div>
    </div>

    <!-- Step 2: Map Results -->
    <div v-else-if="currentStep === 2 && mapResult" class="card">
      <h3 class="card-title">
        <span class="step-badge">Step 2</span>
        理论框架映射
      </h3>

      <div class="mapping-list">
        <div v-for="mapping in mapResult.mappings" :key="mapping.concept_id" class="mapping-card">
          <div class="mapping-header">
            <span class="new-title">{{ mapping.new_title }}</span>
            <span class="framework-badge">{{ mapping.framework_name }}</span>
          </div>
          <p class="mapping-insight">{{ mapping.insight }}</p>
          <div class="mapping-meta">
            <span v-if="mapping.recommended_chart" class="chart-type">
              📊 {{ mapping.recommended_chart }}
            </span>
            <span class="visual-metaphor">{{ mapping.visual_metaphor }}</span>
          </div>
        </div>
      </div>

      <div v-if="isRunning" class="processing-indicator">
        <div class="spinner"></div>
        <span>正在生成设计方案...</span>
      </div>
    </div>

    <!-- Step 3: Design Results -->
    <div v-else-if="currentStep === 3 && designResult" class="card">
      <h3 class="card-title">
        <span class="step-badge">Step 3</span>
        可视化设计
      </h3>

      <div class="design-list">
        <div v-for="design in designResult.designs" :key="design.concept_id" class="design-card">
          <div class="design-header">
            <span class="design-title">{{ design.title }}</span>
            <span class="chart-badge">{{ design.chart_type }}</span>
          </div>
          <div class="design-visual">
            <div class="visual-elements">
              <span v-for="elem in design.visual_elements?.slice(0, 4)" :key="elem" class="element-tag">
                {{ elem }}
              </span>
            </div>
          </div>
          <details class="prompt-preview">
            <summary>查看图像提示词</summary>
            <pre>{{ truncate(design.image_prompt, 300) }}</pre>
          </details>
        </div>
      </div>

      <div v-if="isRunning" class="processing-indicator">
        <div class="spinner"></div>
        <span>正在生成图像...</span>
      </div>
    </div>

    <!-- Step 4: Generate Results -->
    <div v-else-if="currentStep === 4" class="card">
      <h3 class="card-title">
        <span class="step-badge">Step 4</span>
        生成结果
      </h3>

      <div class="progress-section" v-if="generateProgress.total > 0">
        <div class="progress-info">
          <span>生成进度</span>
          <span class="progress-text">{{ generateProgress.current }} / {{ generateProgress.total }}</span>
        </div>
        <div class="progress-container">
          <div class="progress-bar" :style="{ width: progressPercent + '%' }"></div>
        </div>
      </div>

      <div class="image-grid">
        <div v-for="image in generatedImages" :key="image.index" class="image-card">
          <div v-if="image.url && image.success" class="image-preview">
            <img :src="image.url" :alt="image.title" />
          </div>
          <div v-else-if="image.status === 'generating'" class="image-placeholder">
            <div class="spinner"></div>
            <span>生成中...</span>
          </div>
          <div v-else-if="image.error" class="image-placeholder error">
            <span class="error-icon">!</span>
            <span>{{ image.error }}</span>
          </div>
          <div v-else class="image-placeholder">
            <span>等待中</span>
          </div>
          <div class="image-footer">
            <span class="image-title">{{ image.title || `图 ${image.index}` }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Completion -->
    <div v-if="isComplete && !isRunning" class="completion-section">
      <div class="completion-icon">✓</div>
      <h3>生成完成</h3>
      <p>成功生成 {{ generateProgress.success }} / {{ generateProgress.total }} 张概念图</p>
      <div class="completion-actions">
        <button class="btn btn-primary" @click="resetAndStartNew">
          生成新的概念图
        </button>
        <router-link to="/concept/history" class="btn btn-secondary">
          查看历史记录
        </router-link>
      </div>
    </div>

    <!-- Error Display -->
    <div v-if="errorMessage" class="error-card">
      <h4>出错了</h4>
      <p>{{ errorMessage }}</p>
      <button class="btn btn-secondary" @click="resetAndStartNew">重新开始</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

// State
const articleText = ref('')
const selectedStyle = ref('blueprint')
const visualStyles = ref<any[]>([])

const currentStep = ref(0)
const isRunning = ref(false)
const isComplete = ref(false)
const errorMessage = ref('')

const analyzeResult = ref<any>(null)
const mapResult = ref<any>(null)
const designResult = ref<any>(null)
const generatedImages = ref<any[]>([])
const generateProgress = ref({ current: 0, total: 0, success: 0 })

// Steps definition
const steps = ref([
  { id: 'input', name: '输入', description: '粘贴文章', error: false },
  { id: 'analyze', name: '分析', description: '提取概念', error: false },
  { id: 'map', name: '映射', description: '理论框架', error: false },
  { id: 'design', name: '设计', description: '生成方案', error: false },
  { id: 'generate', name: '生成', description: '输出图像', error: false },
])

// Computed
const currentStepDescription = computed(() => {
  if (isComplete.value) return '概念图生成完成'
  if (errorMessage.value) return '处理出错'
  if (!isRunning.value && currentStep.value === 0) return '输入文章内容开始概念可视化'
  return steps.value[currentStep.value]?.description || ''
})

const progressPercent = computed(() => {
  if (generateProgress.value.total === 0) return 0
  return (generateProgress.value.current / generateProgress.value.total) * 100
})

// Methods
const fetchVisualStyles = async () => {
  try {
    const res = await fetch('/api/knowledge/visual-styles')
    const data = await res.json()
    if (data.success) {
      visualStyles.value = data.visual_styles
    }
  } catch (e) {
    console.error('Failed to load visual styles:', e)
    // Default styles
    visualStyles.value = [
      { id: 'blueprint', name: 'Blueprint', colors: { primary: '#2F3337' } },
      { id: 'vintage', name: 'Vintage', colors: { primary: '#8B7355' } },
      { id: 'minimalist', name: 'Minimalist', colors: { primary: '#1a1a1a' } },
    ]
  }
}

const truncate = (text: string, maxLen: number) => {
  if (!text) return ''
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text
}

const startPipeline = async () => {
  if (!articleText.value.trim()) return

  isRunning.value = true
  errorMessage.value = ''
  isComplete.value = false
  currentStep.value = 1

  // Reset results
  analyzeResult.value = null
  mapResult.value = null
  designResult.value = null
  generatedImages.value = []
  generateProgress.value = { current: 0, total: 0, success: 0 }

  try {
    const response = await fetch('/api/concept/run/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        article: articleText.value,
        style: selectedStyle.value,
        config: { max_concepts: 8 }
      })
    })

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) throw new Error('Stream not available')

    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            handlePipelineEvent(data)
          } catch (e) {
            // Skip malformed JSON
          }
        }
      }
    }
  } catch (e: any) {
    console.error('Pipeline error:', e)
    errorMessage.value = e.message || '流水线执行失败'
    steps.value[currentStep.value].error = true
  } finally {
    isRunning.value = false
  }
}

const handlePipelineEvent = (event: any) => {
  console.log('Pipeline event:', event)

  switch (event.event) {
    case 'start':
      // Pipeline started
      break

    case 'step_start':
      if (event.skill === 'concept_analyze') currentStep.value = 1
      else if (event.skill === 'concept_map') currentStep.value = 2
      else if (event.skill === 'concept_design') currentStep.value = 3
      else if (event.skill === 'concept_generate') currentStep.value = 4
      break

    case 'step_complete':
      if (event.skill === 'concept_analyze') {
        // Fetch full analyze result
        analyzeResult.value = event.result?.main_theme ? event.result : null
      } else if (event.skill === 'concept_map') {
        // mapResult set via accumulated data
      } else if (event.skill === 'concept_design') {
        // designResult set via accumulated data
      }
      break

    case 'generate_start':
      generateProgress.value.total = event.result?.total || 0
      generatedImages.value = Array.from({ length: generateProgress.value.total }, (_, i) => ({
        index: i + 1,
        status: 'pending',
        url: null,
        error: null
      }))
      break

    case 'generate_progress':
      if (event.result?.index) {
        const idx = event.result.index - 1
        if (generatedImages.value[idx]) {
          generatedImages.value[idx].status = 'generating'
          generatedImages.value[idx].title = event.result.title
        }
      }
      break

    case 'generate_result':
      if (event.result?.index) {
        const idx = event.result.index - 1
        generateProgress.value.current = event.result.index
        if (generatedImages.value[idx]) {
          generatedImages.value[idx] = {
            ...generatedImages.value[idx],
            ...event.result,
            status: event.result.success ? 'done' : 'error',
            url: event.result.output_path ? `/${event.result.output_path}` : event.result.url
          }
          if (event.result.success) {
            generateProgress.value.success++
          }
        }
      }
      break

    case 'generate_complete':
      generateProgress.value.current = event.result?.total || generateProgress.value.total
      generateProgress.value.success = event.result?.success_count || 0
      break

    case 'complete':
      isComplete.value = true
      // Update results from final output
      if (event.result) {
        analyzeResult.value = {
          main_theme: event.result.main_theme,
          key_concepts: event.result.concepts
        }
        mapResult.value = { mappings: event.result.mappings }
        designResult.value = { designs: event.result.designs }
      }
      break

    case 'error':
    case 'step_error':
      errorMessage.value = event.error || '处理失败'
      steps.value[currentStep.value].error = true
      break
  }
}

const resetAndStartNew = () => {
  currentStep.value = 0
  isComplete.value = false
  errorMessage.value = ''
  analyzeResult.value = null
  mapResult.value = null
  designResult.value = null
  generatedImages.value = []
  generateProgress.value = { current: 0, total: 0, success: 0 }
  steps.value.forEach(s => s.error = false)
}

onMounted(() => {
  fetchVisualStyles()
})
</script>

<style scoped>
.concept-container {
  max-width: 900px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 4px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-sub);
}

/* Step Indicator */
.step-indicator {
  display: flex;
  justify-content: space-between;
  margin-bottom: 32px;
  padding: 16px 24px;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
}

.step {
  display: flex;
  align-items: center;
  gap: 12px;
  opacity: 0.5;
  transition: all 0.3s;
}

.step.active, .step.completed {
  opacity: 1;
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--bg-secondary);
  border: 2px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-sub);
  transition: all 0.3s;
}

.step.active .step-number {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
}

.step.completed .step-number {
  background: #10b981;
  border-color: #10b981;
  color: white;
}

.step.error .step-number {
  background: #ef4444;
  border-color: #ef4444;
  color: white;
}

.step-info {
  display: flex;
  flex-direction: column;
}

.step-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}

.step-desc {
  font-size: 12px;
  color: var(--text-sub);
}

/* Card styles */
.card {
  padding: 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 20px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 8px;
}

.card-desc {
  font-size: 14px;
  color: var(--text-sub);
  margin-bottom: 20px;
}

.step-badge {
  font-size: 11px;
  padding: 4px 8px;
  background: var(--primary);
  color: white;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
}

/* Form styles */
.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 8px;
}

.form-textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  background: var(--bg-secondary);
  color: var(--text-main);
}

.form-textarea:focus {
  outline: none;
  border-color: var(--primary);
}

.char-count {
  display: block;
  text-align: right;
  font-size: 12px;
  color: var(--text-sub);
  margin-top: 4px;
}

/* Style selector */
.style-selector {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.style-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--bg-secondary);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
}

.style-option:hover {
  border-color: var(--primary);
}

.style-option.selected {
  border-color: var(--primary);
  background: rgba(59, 130, 246, 0.1);
}

.style-preview {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-sm);
}

.style-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-main);
}

/* Form actions */
.form-actions {
  display: flex;
  justify-content: center;
  padding-top: 16px;
}

/* Result sections */
.result-section {
  margin-bottom: 24px;
}

.result-section h4 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-sub);
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.main-theme {
  font-size: 18px;
  color: var(--text-main);
  line-height: 1.5;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

/* Concept cards */
.concept-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.concept-card {
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.concept-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.concept-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-main);
}

.viz-type {
  font-size: 11px;
  padding: 3px 8px;
  background: rgba(59, 130, 246, 0.1);
  color: var(--primary);
  border-radius: var(--radius-sm);
}

.concept-desc {
  font-size: 13px;
  color: var(--text-sub);
  line-height: 1.5;
  margin-bottom: 8px;
}

.concept-quote {
  font-size: 12px;
  color: var(--text-sub);
  font-style: italic;
  opacity: 0.8;
}

/* Mapping cards */
.mapping-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mapping-card {
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--primary);
}

.mapping-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.new-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-main);
  text-transform: uppercase;
}

.framework-badge {
  font-size: 11px;
  padding: 3px 8px;
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border-radius: var(--radius-sm);
}

.mapping-insight {
  font-size: 13px;
  color: var(--text-sub);
  line-height: 1.5;
  margin-bottom: 12px;
}

.mapping-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-sub);
}

/* Design cards */
.design-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.design-card {
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.design-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.design-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}

.chart-badge {
  font-size: 11px;
  padding: 3px 8px;
  background: rgba(139, 92, 246, 0.1);
  color: #8b5cf6;
  border-radius: var(--radius-sm);
}

.visual-elements {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.element-tag {
  font-size: 11px;
  padding: 3px 8px;
  background: var(--bg-card);
  border-radius: var(--radius-sm);
  color: var(--text-sub);
}

.prompt-preview {
  cursor: pointer;
}

.prompt-preview summary {
  font-size: 12px;
  color: var(--primary);
}

.prompt-preview pre {
  margin-top: 8px;
  padding: 12px;
  background: var(--bg-card);
  border-radius: var(--radius-sm);
  font-size: 11px;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-x: auto;
}

/* Image grid */
.progress-section {
  margin-bottom: 24px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}

.progress-text {
  font-weight: 600;
  color: var(--primary);
}

.progress-container {
  height: 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--primary);
  transition: width 0.3s;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.image-card {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.image-preview {
  aspect-ratio: 1;
  overflow: hidden;
}

.image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-placeholder {
  aspect-ratio: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--text-sub);
  font-size: 13px;
}

.image-placeholder.error {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.error-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #ef4444;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}

.image-footer {
  padding: 12px;
  border-top: 1px solid var(--border-color);
}

.image-title {
  font-size: 12px;
  color: var(--text-main);
}

/* Processing indicator */
.processing-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(59, 130, 246, 0.1);
  border-radius: var(--radius-md);
  margin-top: 20px;
  color: var(--primary);
  font-size: 14px;
}

/* Completion section */
.completion-section {
  text-align: center;
  padding: 48px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

.completion-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  background: #10b981;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
}

.completion-section h3 {
  font-size: 20px;
  color: var(--text-main);
  margin-bottom: 8px;
}

.completion-section p {
  color: var(--text-sub);
  margin-bottom: 24px;
}

.completion-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}

/* Error card */
.error-card {
  padding: 24px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid #ef4444;
  border-radius: var(--radius-lg);
  text-align: center;
}

.error-card h4 {
  color: #ef4444;
  margin-bottom: 8px;
}

.error-card p {
  color: var(--text-sub);
  margin-bottom: 16px;
}

/* Spinner */
.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner-sm {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
  margin-right: 8px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .step-indicator {
    flex-wrap: wrap;
    gap: 16px;
  }

  .step-info {
    display: none;
  }

  .concept-list,
  .design-list {
    grid-template-columns: 1fr;
  }

  .image-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
