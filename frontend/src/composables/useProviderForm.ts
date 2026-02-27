import { ref, Ref } from 'vue'
import { useMessage } from 'naive-ui'
import { getConfig, updateConfig, testConnection, type Config } from '../api'

export interface Provider {
  type: string
  model: string
  base_url?: string
  api_key?: string
  api_key_masked?: string
  endpoint_type?: string
  high_concurrency?: boolean
  short_prompt?: boolean
  use_size_tag?: boolean
  enabled?: boolean
  _has_api_key?: boolean
}

export interface ProviderConfig {
  active_provider: string
  providers: Record<string, Provider>
}

export interface ProviderForm {
  name: string
  type: string
  api_key: string
  api_key_masked?: string
  base_url: string
  model: string
  endpoint_type?: string
  high_concurrency?: boolean
  short_prompt?: boolean
  use_size_tag?: boolean
  _has_api_key?: boolean
  enabled?: boolean
}

interface ProviderPreset {
  label: string
  base_url: string
  model: string
  endpoint?: string
  enabled?: boolean
}

type ProviderCategory = 'text' | 'image' | 'search'
type MessageApi = ReturnType<typeof useMessage>

const SEARCH_NO_KEY_REQUIRED_TYPES = new Set(['firecrawl', 'bing'])

// 文本生成服务商预设配置
export const textProviderPresets: Record<string, ProviderPreset> = {
  google_gemini: {
    label: 'Google Gemini',
    base_url: 'https://generativelanguage.googleapis.com',
    model: 'gemini-2.0-flash-exp'
  },
  deepseek: {
    label: 'DeepSeek',
    base_url: 'https://api.deepseek.com',
    model: 'deepseek-chat',
    endpoint: '/v1/chat/completions'
  },
  openai: {
    label: 'OpenAI',
    base_url: 'https://api.openai.com',
    model: 'gpt-4o',
    endpoint: '/v1/chat/completions'
  },
  moonshot: {
    label: 'Moonshot (Kimi)',
    base_url: 'https://api.moonshot.cn',
    model: 'moonshot-v1-8k',
    endpoint: '/v1/chat/completions'
  },
  zhipu: {
    label: '智谱 AI (GLM)',
    base_url: 'https://open.bigmodel.cn/api/paas',
    model: 'glm-4-flash',
    endpoint: '/v4/chat/completions'
  },
  qwen: {
    label: '通义千问 (Qwen)',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode',
    model: 'qwen-turbo',
    endpoint: '/v1/chat/completions'
  },
  siliconflow: {
    label: 'SiliconFlow',
    base_url: 'https://api.siliconflow.cn',
    model: 'deepseek-ai/DeepSeek-V3',
    endpoint: '/v1/chat/completions'
  },
  openai_compatible: {
    label: '自定义 OpenAI 兼容',
    base_url: '',
    model: '',
    endpoint: '/v1/chat/completions'
  }
}

export const textTypeOptions = Object.entries(textProviderPresets).map(([value, preset]) => ({
  value,
  label: preset.label
}))

// 图片生成服务商预设配置
export const imageProviderPresets: Record<string, ProviderPreset> = {
  google_genai: {
    label: 'Google GenAI (Imagen)',
    base_url: 'https://generativelanguage.googleapis.com',
    model: 'imagen-3.0-generate-002'
  },
  siliconflow_flux: {
    label: 'SiliconFlow (Flux)',
    base_url: 'https://api.siliconflow.cn',
    model: 'black-forest-labs/FLUX.1-schnell',
    endpoint: '/v1/images/generations'
  },
  jimeng: {
    label: '即梦 AI',
    base_url: 'https://api.jimeng.jianying.com',
    model: 'jimeng-2.0-pro',
    endpoint: '/v1/chat/completions'
  },
  dashscope: {
    label: '阿里百炼 DashScope SDK',
    base_url: 'https://dashscope.aliyuncs.com',
    model: 'qwen-image-max'
  },
  modelscope: {
    label: 'ModelScope Z-Image',
    base_url: 'https://api-inference.modelscope.cn',
    model: 'Tongyi-MAI/Z-Image-Turbo'
  },
  replicate: {
    label: 'Replicate',
    base_url: '',
    model: 'prunaai/z-image-turbo:0870559624690b3709350177b9d521d84e54d297026d725358b8f73193429e91'
  },
  image_api: {
    label: '自定义 OpenAI 兼容',
    base_url: '',
    model: '',
    endpoint: '/v1/images/generations'
  }
}

export const imageTypeOptions = Object.entries(imageProviderPresets).map(([value, preset]) => ({
  value,
  label: preset.label
}))

// 搜索服务商预设配置
export const searchProviderPresets: Record<string, ProviderPreset> = {
  bing: {
    label: 'Bing（默认，无需 Key）',
    base_url: 'https://www.bing.com',
    model: '',
    enabled: true
  },
  firecrawl: {
    label: 'Firecrawl',
    base_url: 'https://api.firecrawl.dev',
    model: '',
    enabled: false
  },
  exa: {
    label: 'Exa',
    base_url: 'https://api.exa.ai',
    model: '',
    enabled: false
  },
  tavily: {
    label: 'Tavily',
    base_url: 'https://api.tavily.com',
    model: '',
    enabled: false
  },
  perplexity: {
    label: 'Perplexity',
    base_url: 'https://api.perplexity.ai',
    model: 'sonar',
    enabled: false
  }
}

export const searchTypeOptions = Object.entries(searchProviderPresets).map(([value, preset]) => ({
  value,
  label: preset.label
}))

function createEmptyForm(category: ProviderCategory): ProviderForm {
  const isImage = category === 'image'
  const isSearch = category === 'search'

  return {
    name: '',
    type: isImage ? 'image_api' : isSearch ? 'bing' : 'openai_compatible',
    api_key: '',
    api_key_masked: '',
    base_url: '',
    model: '',
    endpoint_type: isImage ? '/v1/images/generations' : '/v1/chat/completions',
    high_concurrency: false,
    short_prompt: false,
    use_size_tag: isImage ? true : undefined,
    _has_api_key: false,
    enabled: isSearch ? false : undefined
  }
}

function createProviderHandler(
  config: Ref<ProviderConfig>,
  form: Ref<ProviderForm>,
  showModal: Ref<boolean>,
  editing: Ref<string | null>,
  testing: Ref<boolean>,
  category: ProviderCategory,
  message: MessageApi,
  autoSave: () => Promise<void>
) {
  const isImage = category === 'image'
  const isSearch = category === 'search'

  const activate = async (name: string) => {
    config.value.active_provider = name
    if (isSearch && config.value.providers[name]) {
      config.value.providers[name].enabled = true
    }
    await autoSave()
  }

  const openAdd = () => {
    editing.value = null
    form.value = createEmptyForm(category)
    showModal.value = true
  }

  const openEdit = (name: string, provider: Provider) => {
    editing.value = name
    form.value = {
      name,
      type: provider.type || (isImage ? 'image_api' : isSearch ? 'bing' : 'openai_compatible'),
      api_key: '',
      api_key_masked: provider.api_key_masked || '',
      base_url: provider.base_url || '',
      model: provider.model || '',
      endpoint_type: provider.endpoint_type || (isImage ? '/v1/images/generations' : '/v1/chat/completions'),
      high_concurrency: provider.high_concurrency || false,
      short_prompt: provider.short_prompt || false,
      use_size_tag: isImage ? (provider.use_size_tag ?? true) : undefined,
      _has_api_key: !!provider._has_api_key || !!provider.api_key_masked,
      enabled: isSearch ? !!provider.enabled : undefined
    }
    showModal.value = true
  }

  const close = () => {
    showModal.value = false
    editing.value = null
  }

  const save = async () => {
    const name = editing.value || form.value.name
    if (!name) {
      message.warning('请填写服务商名称')
      return
    }
    if (!form.value.type) {
      message.warning('请选择服务商类型')
      return
    }

    const apiKey = form.value.api_key.trim()
    const needApiKey = !isSearch || !SEARCH_NO_KEY_REQUIRED_TYPES.has(form.value.type)
    if (!editing.value && !apiKey && needApiKey) {
      message.warning('请填写 API Key')
      return
    }

    const existing = config.value.providers[name] || {}
    const data: any = { type: form.value.type }

    const model = form.value.model.trim()
    if (!isSearch || model || form.value.type === 'perplexity') {
      data.model = model
    }

    if (apiKey) data.api_key = apiKey
    else if (existing.api_key) data.api_key = existing.api_key

    const baseUrl = form.value.base_url.trim()
    if (isSearch || baseUrl) {
      data.base_url = baseUrl
    }

    if (isSearch) {
      data.enabled = !!form.value.enabled
    }

    if (isImage) {
      data.high_concurrency = form.value.high_concurrency
      data.short_prompt = form.value.short_prompt
      if (form.value.type === 'image_api') {
        data.endpoint_type = form.value.endpoint_type || '/v1/images/generations'
        data.use_size_tag = form.value.use_size_tag ?? true
      }
    } else if (!isSearch) {
      if (form.value.type === 'openai_compatible') {
        data.endpoint_type = form.value.endpoint_type
      }
    }

    config.value.providers[name] = data
    close()
    await autoSave()
  }

  const remove = async (name: string) => {
    if (!confirm(`确定要删除服务商 "${name}" 吗？`)) return
    delete config.value.providers[name]
    if (config.value.active_provider === name) config.value.active_provider = ''
    await autoSave()
  }

  const test = async () => {
    testing.value = true
    try {
      const payload: any = {
        type: form.value.type,
        provider_name: editing.value || undefined,
        api_key: form.value.api_key.trim() || undefined,
        base_url: form.value.base_url.trim() || undefined,
        model: form.value.model.trim() || undefined
      }
      if (isImage) {
        payload.endpoint_type = form.value.endpoint_type || '/v1/images/generations'
      } else if (!isSearch) {
        payload.endpoint_type = form.value.endpoint_type || '/v1/chat/completions'
      }

      const result = await testConnection(payload)
      if (result.success) {
        message.success(result.message || '连接成功')
      } else {
        message.error('连接失败：' + (result.error || result.message || '未知错误'))
      }
    } catch (e: any) {
      message.error('连接失败：' + (e.response?.data?.error || e.message))
    } finally {
      testing.value = false
    }
  }

  const testInList = async (name: string, provider: Provider) => {
    try {
      const payload: any = {
        type: provider.type,
        provider_name: name,
        base_url: provider.base_url,
        model: provider.model
      }
      if (isImage) {
        payload.endpoint_type = provider.endpoint_type || '/v1/images/generations'
      } else if (!isSearch) {
        payload.endpoint_type = provider.endpoint_type || '/v1/chat/completions'
      }

      const result = await testConnection(payload)
      if (result.success) {
        message.success(result.message || '连接成功')
      } else {
        message.error('连接失败：' + (result.error || result.message || '未知错误'))
      }
    } catch (e: any) {
      message.error('连接失败：' + (e.response?.data?.error || e.message))
    }
  }

  return { activate, openAdd, openEdit, close, save, remove, test, testInList }
}

function normalizeProviderConfig(data: any, fallbackActive = ''): ProviderConfig {
  if (!data || typeof data !== 'object') {
    return { active_provider: fallbackActive, providers: {} }
  }
  return {
    active_provider: data.active_provider || fallbackActive,
    providers: data.providers || {}
  }
}

export function useProviderForm() {
  const message = useMessage()
  const loading = ref(true)
  const saving = ref(false)
  const testingText = ref(false)
  const testingImage = ref(false)
  const testingSearch = ref(false)

  const textConfig = ref<ProviderConfig>({ active_provider: '', providers: {} })
  const imageConfig = ref<ProviderConfig>({ active_provider: '', providers: {} })
  const searchConfig = ref<ProviderConfig>({ active_provider: 'bing', providers: {} })

  const showTextModal = ref(false)
  const editingTextProvider = ref<string | null>(null)
  const textForm = ref<ProviderForm>(createEmptyForm('text'))

  const showImageModal = ref(false)
  const editingImageProvider = ref<string | null>(null)
  const imageForm = ref<ProviderForm>(createEmptyForm('image'))

  const showSearchModal = ref(false)
  const editingSearchProvider = ref<string | null>(null)
  const searchForm = ref<ProviderForm>(createEmptyForm('search'))

  async function loadConfig() {
    loading.value = true
    try {
      const result = await getConfig()
      if (result.success && result.config) {
        textConfig.value = normalizeProviderConfig(result.config.text_generation)
        imageConfig.value = normalizeProviderConfig(result.config.image_generation)
        searchConfig.value = normalizeProviderConfig(result.config.search, 'bing')
      } else {
        message.error('加载配置失败: ' + (result.error || '未知错误'))
      }
    } catch (e) {
      message.error('加载配置失败: ' + String(e))
    } finally {
      loading.value = false
    }
  }

  async function autoSaveConfig() {
    try {
      const config: Partial<Config> = {
        text_generation: {
          active_provider: textConfig.value.active_provider,
          providers: textConfig.value.providers
        },
        image_generation: imageConfig.value,
        search: searchConfig.value
      }
      const result = await updateConfig(config)
      if (result.success) await loadConfig()
    } catch (e) {
      console.error('自动保存失败:', e)
    }
  }

  const textHandler = createProviderHandler(
    textConfig,
    textForm,
    showTextModal,
    editingTextProvider,
    testingText,
    'text',
    message,
    autoSaveConfig
  )
  const imageHandler = createProviderHandler(
    imageConfig,
    imageForm,
    showImageModal,
    editingImageProvider,
    testingImage,
    'image',
    message,
    autoSaveConfig
  )
  const searchHandler = createProviderHandler(
    searchConfig,
    searchForm,
    showSearchModal,
    editingSearchProvider,
    testingSearch,
    'search',
    message,
    autoSaveConfig
  )

  return {
    loading,
    saving,
    testingText,
    testingImage,
    testingSearch,
    textConfig,
    imageConfig,
    searchConfig,
    showTextModal,
    editingTextProvider,
    textForm,
    showImageModal,
    editingImageProvider,
    imageForm,
    showSearchModal,
    editingSearchProvider,
    searchForm,
    loadConfig,
    // Text provider methods
    activateTextProvider: textHandler.activate,
    openAddTextModal: textHandler.openAdd,
    openEditTextModal: textHandler.openEdit,
    closeTextModal: textHandler.close,
    saveTextProvider: textHandler.save,
    deleteTextProvider: textHandler.remove,
    testTextConnection: textHandler.test,
    testTextProviderInList: textHandler.testInList,
    updateTextForm: (data: ProviderForm) => {
      textForm.value = data
    },
    // Image provider methods
    activateImageProvider: imageHandler.activate,
    openAddImageModal: imageHandler.openAdd,
    openEditImageModal: imageHandler.openEdit,
    closeImageModal: imageHandler.close,
    saveImageProvider: imageHandler.save,
    deleteImageProvider: imageHandler.remove,
    testImageConnection: imageHandler.test,
    testImageProviderInList: imageHandler.testInList,
    updateImageForm: (data: ProviderForm) => {
      imageForm.value = data
    },
    // Search provider methods
    activateSearchProvider: searchHandler.activate,
    openAddSearchModal: searchHandler.openAdd,
    openEditSearchModal: searchHandler.openEdit,
    closeSearchModal: searchHandler.close,
    saveSearchProvider: searchHandler.save,
    deleteSearchProvider: searchHandler.remove,
    testSearchConnection: searchHandler.test,
    testSearchProviderInList: searchHandler.testInList,
    updateSearchForm: (data: ProviderForm) => {
      searchForm.value = data
    }
  }
}

// Type aliases for backward compatibility
export type TextProviderForm = ProviderForm
export type ImageProviderForm = ProviderForm
export type SearchProviderForm = ProviderForm
