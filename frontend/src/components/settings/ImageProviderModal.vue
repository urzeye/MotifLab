<template>
  <!-- 图片服务商编辑/添加弹窗 -->
  <div v-if="visible" class="modal-overlay" @click="$emit('close')">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h3>{{ isEditing ? '编辑服务商' : '添加服务商' }}</h3>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body">
        <!-- 服务商名称（仅添加时显示） -->
        <div class="form-group" v-if="!isEditing">
          <label>服务商名称</label>
          <input
            type="text"
            class="form-input"
            :value="formData.name"
            @input="updateField('name', ($event.target as HTMLInputElement).value)"
            placeholder="例如: google_genai"
          />
          <span class="form-hint">唯一标识，用于区分不同服务商</span>
        </div>

        <!-- 类型选择 -->
        <div class="form-group">
          <label>类型</label>
          <select
            class="form-select"
            :value="formData.type"
            @change="handleTypeChange(($event.target as HTMLSelectElement).value)"
          >
            <option v-for="opt in typeOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
          <span class="form-hint" v-if="currentPreset && !isEditing">
            选择后将自动填充默认配置，可自行修改
          </span>
        </div>

        <!-- API Key -->
        <div class="form-group">
          <label>API Key</label>
          <input
            type="text"
            class="form-input"
            :value="formData.api_key"
            @input="updateField('api_key', ($event.target as HTMLInputElement).value)"
            :placeholder="isEditing && formData._has_api_key ? formData.api_key_masked : '输入 API Key'"
          />
          <span class="form-hint" v-if="isEditing && formData._has_api_key">
            已配置 API Key，留空表示不修改
          </span>
        </div>

        <!-- Base URL -->
        <div class="form-group" v-if="showBaseUrl">
          <label>Base URL</label>
          <input
            type="text"
            class="form-input"
            :value="formData.base_url"
            @input="updateField('base_url', ($event.target as HTMLInputElement).value)"
            placeholder="例如: https://generativelanguage.googleapis.com"
          />
          <span class="form-hint" v-if="previewUrl">
            预览: {{ previewUrl }}
          </span>
        </div>

        <!-- 模型 -->
        <div class="form-group">
          <label>模型</label>
          <input
            type="text"
            class="form-input"
            :value="formData.model"
            @input="updateField('model', ($event.target as HTMLInputElement).value)"
            :placeholder="modelPlaceholder"
          />
        </div>

        <!-- 端点路径（仅 OpenAI 兼容接口） -->
        <div class="form-group" v-if="showEndpointType">
          <label>API 端点路径</label>
          <input
            type="text"
            class="form-input"
            :value="formData.endpoint_type"
            @input="updateField('endpoint_type', ($event.target as HTMLInputElement).value)"
            placeholder="例如: /v1/images/generations 或 /v1/chat/completions"
          />
          <span class="form-hint">
            常用端点：/v1/images/generations（标准图片生成）、/v1/chat/completions（即梦等返回链接的 API）
          </span>
        </div>

        <!-- 高并发模式 -->
        <div class="form-group">
          <label class="toggle-label">
            <span>高并发模式</span>
            <div
              class="toggle-switch"
              :class="{ active: formData.high_concurrency }"
              @click="updateField('high_concurrency', !formData.high_concurrency)"
            >
              <div class="toggle-slider"></div>
            </div>
          </label>
          <span class="form-hint">
            启用后将并行生成图片，速度更快但对 API 质量要求较高。GCP 300$ 试用账号不建议启用。
          </span>
        </div>

        <!-- 短 Prompt 模式 -->
        <div class="form-group">
          <label class="toggle-label">
            <span>短 Prompt 模式</span>
            <div
              class="toggle-switch"
              :class="{ active: formData.short_prompt }"
              @click="updateField('short_prompt', !formData.short_prompt)"
            >
              <div class="toggle-slider"></div>
            </div>
          </label>
          <span class="form-hint">
            启用后使用精简版提示词，适合有字符限制的 API（如即梦 1600 字符限制）。
          </span>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn" @click="$emit('close')">取消</button>
        <button
          class="btn btn-secondary"
          @click="$emit('test')"
          :disabled="testing || (!formData.api_key && !isEditing)"
        >
          <span v-if="testing" class="spinner-small"></span>
          {{ testing ? '测试中...' : '测试连接' }}
        </button>
        <button class="btn btn-primary" @click="$emit('save')">
          {{ isEditing ? '保存' : '添加' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { imageProviderPresets } from '../../composables/useProviderForm'

/**
 * 图片服务商编辑/添加弹窗组件
 *
 * 功能：
 * - 添加新服务商
 * - 编辑现有服务商
 * - 测试连接
 * - 预设配置自动填充
 * - 支持高并发模式和短 Prompt 模式开关
 */

// 定义表单数据类型
interface FormData {
  name: string
  type: string
  api_key: string
  api_key_masked?: string
  _has_api_key?: boolean
  base_url: string
  model: string
  endpoint_type?: string
  high_concurrency?: boolean
  short_prompt?: boolean
}

// 定义类型选项
interface TypeOption {
  value: string
  label: string
}

// 定义 Props
const props = defineProps<{
  visible: boolean
  isEditing: boolean
  formData: FormData
  testing: boolean
  typeOptions: TypeOption[]
}>()

// 定义 Emits
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'save'): void
  (e: 'test'): void
  (e: 'update:formData', data: FormData): void
}>()

// 当前选中的预设
const currentPreset = computed(() => {
  return imageProviderPresets[props.formData.type]
})

// 更新表单字段
function updateField(field: keyof FormData, value: string | boolean) {
  emit('update:formData', {
    ...props.formData,
    [field]: value
  })
}

// 处理类型变更（自动填充预设配置）
function handleTypeChange(newType: string) {
  const preset = imageProviderPresets[newType]

  // 如果是编辑模式，只更新类型
  if (props.isEditing) {
    updateField('type', newType)
    return
  }

  // 添加模式：自动填充预设配置
  if (preset) {
    emit('update:formData', {
      ...props.formData,
      type: newType,
      base_url: preset.base_url || props.formData.base_url,
      model: preset.model || props.formData.model,
      endpoint_type: preset.endpoint || props.formData.endpoint_type
    })
  } else {
    updateField('type', newType)
  }
}

// 是否显示 Base URL（所有类型都显示，方便自定义）
const showBaseUrl = computed(() => {
  // google_genai 使用原生 SDK，不需要 base_url
  return props.formData.type !== 'google_genai'
})

// 是否显示端点类型（仅自定义 OpenAI 兼容接口）
const showEndpointType = computed(() => {
  return props.formData.type === 'image_api'
})

// 模型占位符
const modelPlaceholder = computed(() => {
  const preset = currentPreset.value
  if (preset?.model) {
    return `推荐: ${preset.model}`
  }
  return '输入模型名称'
})

// 预览 URL
const previewUrl = computed(() => {
  if (!props.formData.base_url) return ''

  const baseUrl = props.formData.base_url.replace(/\/$/, '').replace(/\/v1$/, '')

  if (props.formData.type === 'google_genai') {
    return `${baseUrl}/v1beta/models/${props.formData.model || '{model}'}:generateImages`
  }

  const endpoint = props.formData.endpoint_type || '/v1/images/generations'
  return `${baseUrl}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`
})
</script>

<style scoped>
/* 模态框遮罩 - 深色主题适配 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

/* 模态框内容 - 使用设计系统变量 */
.modal-content {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--border-color);
}

/* 头部 */
.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: var(--h4-size);
  font-weight: var(--h4-weight);
  color: var(--text-main);
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--text-sub);
  padding: 0;
  line-height: 1;
  transition: color var(--transition-fast);
}

.close-btn:hover {
  color: var(--text-main);
}

/* 主体 */
.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

/* 表单组 */
.form-group {
  margin-bottom: 20px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  font-size: var(--small-size);
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 8px;
}

/* 输入框 - 深色主题 WCAG AA 对比度 */
.form-input {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: var(--small-size);
  background: var(--bg-input);
  color: var(--text-main);
  transition: all var(--transition-fast);
}

.form-input::placeholder {
  color: var(--text-placeholder);
}

.form-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-fade);
  background: var(--bg-elevated);
}

/* 下拉选择框 - 深色主题 */
.form-select {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: var(--small-size);
  background: var(--bg-input);
  color: var(--text-main);
  cursor: pointer;
  transition: all var(--transition-fast);
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23A1A1AA' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
}

.form-select:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-fade);
}

.form-select option {
  background: var(--bg-card);
  color: var(--text-main);
}

.form-hint {
  display: block;
  font-size: var(--caption-size);
  color: var(--text-sub);
  margin-top: 6px;
  line-height: 1.5;
}

/* Toggle 开关样式 - 深色主题 */
.toggle-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
}

.toggle-switch {
  width: 44px;
  height: 24px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  position: relative;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.toggle-switch.active {
  background: var(--primary);
  border-color: var(--primary);
}

.toggle-slider {
  width: 18px;
  height: 18px;
  background: var(--text-sub);
  border-radius: 50%;
  position: absolute;
  top: 2px;
  left: 2px;
  transition: all var(--transition-fast);
}

.toggle-switch.active .toggle-slider {
  transform: translateX(20px);
  background: var(--text-inverse);
}

/* 底部 */
.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 按钮样式 - 深色主题 */
.btn {
  padding: 10px 18px;
  border-radius: var(--radius-sm);
  font-size: var(--small-size);
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border-color);
  background: var(--bg-elevated);
  color: var(--text-main);
  transition: all var(--transition-fast);
}

.btn:hover {
  background: var(--bg-card);
  border-color: var(--border-hover);
}

.btn-primary {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--text-inverse);
  box-shadow: var(--primary-glow);
}

.btn-primary:hover {
  background: var(--primary-hover);
  transform: translateY(-1px);
}

.btn-secondary {
  background: var(--bg-elevated);
  border-color: var(--border-color);
  color: var(--text-sub);
}

.btn-secondary:hover {
  background: var(--bg-card);
  color: var(--text-main);
  border-color: var(--border-hover);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

/* 加载动画 */
.spinner-small {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-right: 6px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
