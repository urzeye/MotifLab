import { ref, Ref } from 'vue'
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
}

export interface ProviderConfig {
  active_provider: string
  providers: Record<string, Provider>
}

export interface ProviderForm {
  name: string
  type: string
  api_key: string
  api_key_masked: string
  base_url: string
  model: string
  endpoint_type: string
  high_concurrency?: boolean
  short_prompt?: boolean
  _has_api_key: boolean
}

export const textTypeOptions = [
  { value: 'google_gemini', label: 'Google Gemini' },
  { value: 'openai_compatible', label: 'OpenAI 兼容接口' }
]

export const imageTypeOptions = [
  { value: 'google_genai', label: 'Google GenAI' },
  { value: 'image_api', label: 'OpenAI 兼容接口' }
]

function createEmptyForm(isImage: boolean): ProviderForm {
  return {
    name: '',
    type: isImage ? 'image_api' : 'openai_compatible',
    api_key: '',
    api_key_masked: '',
    base_url: '',
    model: '',
    endpoint_type: isImage ? '/v1/images/generations' : '/v1/chat/completions',
    high_concurrency: false,
    short_prompt: false,
    _has_api_key: false
  }
}

function createProviderHandler(
  config: Ref<ProviderConfig>,
  form: Ref<ProviderForm>,
  showModal: Ref<boolean>,
  editing: Ref<string | null>,
  testing: Ref<boolean>,
  isImage: boolean,
  autoSave: () => Promise<void>
) {
  const activate = async (name: string) => {
    config.value.active_provider = name
    await autoSave()
  }

  const openAdd = () => {
    editing.value = null
    form.value = createEmptyForm(isImage)
    showModal.value = true
  }

  const openEdit = (name: string, provider: Provider) => {
    editing.value = name
    form.value = {
      name,
      type: provider.type || (isImage ? 'image_api' : 'openai_compatible'),
      api_key: '',
      api_key_masked: provider.api_key_masked || '',
      base_url: provider.base_url || '',
      model: provider.model || '',
      endpoint_type: provider.endpoint_type || (isImage ? '/v1/images/generations' : '/v1/chat/completions'),
      high_concurrency: provider.high_concurrency || false,
      short_prompt: provider.short_prompt || false,
      _has_api_key: !!provider.api_key_masked
    }
    showModal.value = true
  }

  const close = () => {
    showModal.value = false
    editing.value = null
  }

  const save = async () => {
    const name = editing.value || form.value.name
    if (!name) return alert('请填写服务商名称')
    if (!form.value.type) return alert('请选择服务商类型')
    if (!editing.value && !form.value.api_key) return alert('请填写 API Key')

    const existing = config.value.providers[name] || {}
    const data: any = { type: form.value.type, model: form.value.model }

    if (form.value.api_key) data.api_key = form.value.api_key
    else if (existing.api_key) data.api_key = existing.api_key
    if (form.value.base_url) data.base_url = form.value.base_url

    if (isImage) {
      data.high_concurrency = form.value.high_concurrency
      data.short_prompt = form.value.short_prompt
      if (form.value.type === 'image_api') data.endpoint_type = form.value.endpoint_type
    } else {
      if (form.value.type === 'openai_compatible') data.endpoint_type = form.value.endpoint_type
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
      const result = await testConnection({
        type: form.value.type,
        provider_name: editing.value || undefined,
        api_key: form.value.api_key || undefined,
        base_url: form.value.base_url,
        model: form.value.model
      })
      if (result.success) alert('✅ ' + result.message)
    } catch (e: any) {
      alert('❌ 连接失败：' + (e.response?.data?.error || e.message))
    } finally {
      testing.value = false
    }
  }

  const testInList = async (name: string, provider: Provider) => {
    try {
      const result = await testConnection({
        type: provider.type,
        provider_name: name,
        base_url: provider.base_url,
        model: provider.model
      })
      if (result.success) alert('✅ ' + result.message)
    } catch (e: any) {
      alert('❌ 连接失败：' + (e.response?.data?.error || e.message))
    }
  }

  return { activate, openAdd, openEdit, close, save, remove, test, testInList }
}

export function useProviderForm() {
  const loading = ref(true)
  const saving = ref(false)
  const testingText = ref(false)
  const testingImage = ref(false)

  const textConfig = ref<ProviderConfig>({ active_provider: '', providers: {} })
  const imageConfig = ref<ProviderConfig>({ active_provider: '', providers: {} })

  const showTextModal = ref(false)
  const editingTextProvider = ref<string | null>(null)
  const textForm = ref<ProviderForm>(createEmptyForm(false))

  const showImageModal = ref(false)
  const editingImageProvider = ref<string | null>(null)
  const imageForm = ref<ProviderForm>(createEmptyForm(true))

  async function loadConfig() {
    loading.value = true
    try {
      const result = await getConfig()
      if (result.success && result.config) {
        textConfig.value = {
          active_provider: result.config.text_generation.active_provider,
          providers: result.config.text_generation.providers
        }
        imageConfig.value = result.config.image_generation
      } else {
        alert('加载配置失败: ' + (result.error || '未知错误'))
      }
    } catch (e) {
      alert('加载配置失败: ' + String(e))
    } finally {
      loading.value = false
    }
  }

  async function autoSaveConfig() {
    try {
      const config: Partial<Config> = {
        text_generation: { active_provider: textConfig.value.active_provider, providers: textConfig.value.providers },
        image_generation: imageConfig.value
      }
      const result = await updateConfig(config)
      if (result.success) await loadConfig()
    } catch (e) {
      console.error('自动保存失败:', e)
    }
  }

  const textHandler = createProviderHandler(textConfig, textForm, showTextModal, editingTextProvider, testingText, false, autoSaveConfig)
  const imageHandler = createProviderHandler(imageConfig, imageForm, showImageModal, editingImageProvider, testingImage, true, autoSaveConfig)

  return {
    loading, saving, testingText, testingImage,
    textConfig, imageConfig,
    showTextModal, editingTextProvider, textForm,
    showImageModal, editingImageProvider, imageForm,
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
    updateTextForm: (data: ProviderForm) => { textForm.value = data },
    // Image provider methods
    activateImageProvider: imageHandler.activate,
    openAddImageModal: imageHandler.openAdd,
    openEditImageModal: imageHandler.openEdit,
    closeImageModal: imageHandler.close,
    saveImageProvider: imageHandler.save,
    deleteImageProvider: imageHandler.remove,
    testImageConnection: imageHandler.test,
    testImageProviderInList: imageHandler.testInList,
    updateImageForm: (data: ProviderForm) => { imageForm.value = data }
  }
}

// Type aliases for backward compatibility
export type TextProviderForm = ProviderForm
export type ImageProviderForm = ProviderForm
