<template>
  <div class="container home-container">
    <!-- 图片网格轮播背景 -->
    <ShowcaseBackground />

    <!-- Hero Area -->
    <div class="hero-section">
      <div class="hero-content">
        <div class="brand-pill">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            style="margin-right: 6px"
          >
            <path
              d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"
            />
          </svg>
          AI 驱动的图文创作助手
        </div>
        <div class="platform-slogan">
          让传播不再需要门槛，让创作从未如此简单
        </div>
        <h1 class="page-title">灵感一触即发</h1>
        <p class="page-subtitle">
          输入你的创意主题，让 AI 帮你生成爆款标题、正文和封面图
        </p>
      </div>

      <div v-if="appliedTemplate" class="template-applied-banner">
        <div class="banner-left">
          <div class="banner-icon">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
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
              分类：{{ appliedTemplate.category }} ·
              将参考此模板的布局和风格，主题请自行输入
            </div>
          </div>
        </div>

        <div class="banner-actions">
          <button class="banner-btn" @click="openTemplateMarket">
            切换模板
          </button>
          <button class="banner-btn ghost" @click="clearTemplate">
            取消使用
          </button>
        </div>
      </div>

      <!-- 主题输入组合框 -->
      <ComposerInput
        ref="composerRef"
        v-model="topic"
        :loading="loading"
        :search-provider-enabled="searchProviderEnabled"
        :search-provider="searchProvider"
        :search-provider-options="searchProviderOptions"
        :page-count="pageCount"
        :enable-search="enableSearch"
        @update:pageCount="handlePageCountChange"
        @update:enableSearch="handleEnableSearchChange"
        @update:searchProvider="handleSearchProviderChange"
        @generate="handleGenerate"
        @imagesChange="handleImagesChange"
        @urlContentChange="handleUrlContentChange"
      />

      <div class="prompt-config-card" v-if="false">
        <div class="prompt-config-title">高级图片 Prompt（可选）</div>
        <div class="prompt-config-desc">
          可为当前创作设置额外提示词，后续图片生成、重试、重绘都会复用。
        </div>
        <div class="prompt-config-grid">
          <div class="prompt-field">
            <label>用户提示词（user_prompt）</label>
            <textarea
              v-model="userPrompt"
              rows="3"
              placeholder="例如：极简扁平风、柔和奶油色调、留白构图"
            />
          </div>
          <div class="prompt-field">
            <label>系统提示词（system_prompt）</label>
            <textarea
              v-model="systemPrompt"
              rows="3"
              placeholder="例如：统一 3:4 竖版、保持系列风格一致、避免复杂背景"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 版权信息 -->
    <div class="page-footer">
      <div class="footer-tip">渲染AI - 让创作更简单</div>
      <div class="footer-copyright">© 2025 渲染AI (RenderAI)</div>
      <div class="footer-license">
        Licensed under
        <a
          href="https://creativecommons.org/licenses/by-nc-sa/4.0/"
          target="_blank"
          rel="noopener noreferrer"
          >CC BY-NC-SA 4.0</a
        >
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-toast">
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useGeneratorStore } from "../stores/generator";
import {
  generateOutlineStream,
  createHistory,
  getSearchStatus,
  getConfig,
  getTemplateDetail,
  type Config,
  type OutlineStreamFinishEvent,
  type Page,
  type ScrapeResult,
  type TemplateItem,
} from "../api";

// 引入组件
import ShowcaseBackground from "../components/home/ShowcaseBackground.vue";
import ComposerInput from "../components/home/ComposerInput.vue";

const router = useRouter();
const route = useRoute();
const store = useGeneratorStore();

// 状态
const topic = ref("");
const loading = ref(false);
const error = ref("");
interface ComposerInputRef {
  clearPreviews: () => void;
  clearUrlState?: () => void;
}
const composerRef = ref<ComposerInputRef | null>(null);

// 上传的图片文件
const uploadedImageFiles = ref<File[]>([]);
// 搜索服务可用状态
const searchProviderEnabled = ref(false);
const searchProvider = ref("auto");
const searchProviderOptions = ref<Array<{ label: string; value: string }>>([
  { label: "跟随默认", value: "auto" },
]);
const urlContent = ref<ScrapeResult | null>(null);
const appliedTemplate = ref<TemplateItem | null>(null);
const pageCount = ref(5);
const enableSearch = ref(true);
const userPrompt = ref("");
const systemPrompt = ref("");

let templateRequestSeq = 0;

const SEARCH_PROVIDER_LABELS: Record<string, string> = {
  bing: "Bing (Local)",
  firecrawl: "Firecrawl",
  exa: "Exa",
  tavily: "Tavily",
  perplexity: "Perplexity",
};

function formatSearchProviderLabel(name: string, provider: any): string {
  const normalizedName = String(name || "").trim();
  const type = String(provider?.type || normalizedName)
    .trim()
    .toLowerCase();
  const typeLabel = SEARCH_PROVIDER_LABELS[type] || type || normalizedName;

  if (!normalizedName || normalizedName === type) {
    return typeLabel;
  }
  return `${normalizedName} (${typeLabel})`;
}

function isSearchProviderReady(name: string, provider: any): boolean {
  if (!provider || !provider.enabled) {
    return false;
  }
  const type = String(provider.type || name)
    .trim()
    .toLowerCase();
  if (["exa", "tavily", "perplexity"].includes(type)) {
    return !!(provider._has_api_key || provider.api_key_masked);
  }
  return true;
}

function updateSearchProviderOptions(
  searchConfig: Config["search"] | undefined,
) {
  const providers = searchConfig?.providers || {};
  const activeProvider = String(searchConfig?.active_provider || "").trim();

  const available = Object.entries(providers)
    .filter(([name, provider]) => isSearchProviderReady(name, provider))
    .map(([name, provider]) => ({
      value: name,
      label: formatSearchProviderLabel(name, provider),
    }));

  const activeLabel = available.find(
    (item) => item.value === activeProvider,
  )?.label;
  searchProviderOptions.value = [
    {
      value: "auto",
      label: activeLabel ? `跟随默认（${activeLabel}）` : "跟随默认",
    },
    ...available,
  ];

  if (
    searchProvider.value !== "auto" &&
    !available.some((item) => item.value === searchProvider.value)
  ) {
    searchProvider.value = "auto";
  }
}

async function checkSearchStatus() {
  const [result, configResult] = await Promise.all([
    getSearchStatus(),
    getConfig(),
  ]);
  searchProviderEnabled.value =
    result.success && !!result.enabled && !!result.configured;

  if (configResult.success && configResult.config?.search) {
    updateSearchProviderOptions(configResult.config.search);
    return;
  }

  searchProviderOptions.value = [{ label: "跟随默认", value: "auto" }];
  searchProvider.value = "auto";
}

async function applyTemplateById(templateId: string) {
  const reqId = ++templateRequestSeq;
  const result = await getTemplateDetail(templateId);
  if (reqId !== templateRequestSeq) return;

  if (result.success && result.template) {
    appliedTemplate.value = result.template;
    error.value = "";
  } else {
    appliedTemplate.value = null;
    error.value = result.error || "模板加载失败，请重试";
  }
}

function openTemplateMarket() {
  router.push("/templates");
}

function clearTemplate() {
  appliedTemplate.value = null;
  const query = { ...route.query };
  delete query.template_id;
  router.replace({ path: "/redbook", query });
}

/**
 * 处理图片变化
 */
function handleImagesChange(images: File[]) {
  uploadedImageFiles.value = images;
}

function handleUrlContentChange(content: ScrapeResult | null) {
  urlContent.value = content;
}

function handlePageCountChange(value: number) {
  if (!Number.isFinite(value)) {
    pageCount.value = 5;
    return;
  }
  pageCount.value = Math.max(1, Math.min(15, Math.trunc(value)));
}

function handleEnableSearchChange(value: boolean) {
  enableSearch.value = !!value;
}

function handleSearchProviderChange(value: string) {
  searchProvider.value = value || "auto";
}

function buildTopicWithPageCount(rawTopic: string, totalPages: number): string {
  const normalizedPages = Math.max(1, Math.min(15, Math.trunc(totalPages)));
  return (
    `${rawTopic}\n\n` +
    `【页数要求】必须严格生成 ${normalizedPages} 页（包括封面和总结页），总计 ${normalizedPages} 页，不得多也不得少。`
  );
}

/**
 * 兜底解析大纲文本，避免后端偶发缺失 pages 时阻断流程。
 */
function parsePagesFromRawOutline(rawOutline: string): Page[] {
  const raw = String(rawOutline || "")
    .replace(/\r\n/g, "\n")
    .trim();
  if (!raw) return [];

  const chunks = raw
    .split(/\n?\s*<page>\s*\n?/gi)
    .map((item) => item.trim())
    .filter(Boolean);

  if (chunks.length === 0) return [];

  return chunks.map((content, index) => {
    let type: "cover" | "content" | "summary" = "content";
    if (index === 0) type = "cover";
    else if (index === chunks.length - 1) type = "summary";

    return {
      index,
      type,
      content,
    };
  });
}

/**
 * 异步落库大纲快照，不阻塞页面跳转。
 */
async function persistOutlineHistory(
  title: string,
  raw: string,
  pages: Page[],
): Promise<void> {
  try {
    const historyResult = await createHistory(title, {
      raw,
      pages,
    });

    if (historyResult.success && historyResult.record_id) {
      store.setRecordId(historyResult.record_id);
      return;
    }

    console.error("创建历史记录失败:", historyResult.error || "未知错误");
    store.setRecordId(null);
  } catch (err: any) {
    console.error("创建历史记录异常:", err?.message || err);
    store.setRecordId(null);
  }
}

/**
 * 生成大纲
 */
async function handleGenerate() {
  const rawTopic = topic.value.trim();
  if (!rawTopic) return;

  loading.value = true;
  error.value = "";

  try {
    store.setImagePrompt({
      userPrompt: userPrompt.value,
      systemPrompt: systemPrompt.value,
    });

    const imageFiles = uploadedImageFiles.value;
    const sourceContent = urlContent.value?.success
      ? urlContent.value.data?.content
      : undefined;
    const topicForOutline = buildTopicWithPageCount(rawTopic, pageCount.value);
    const templateRef = appliedTemplate.value
      ? {
          id: appliedTemplate.value.id,
          title: appliedTemplate.value.title,
          category: appliedTemplate.value.category,
          description: appliedTemplate.value.description,
          prompt: appliedTemplate.value.prompt,
          stylePrompt: appliedTemplate.value.stylePrompt,
          tags: appliedTemplate.value.tags,
        }
      : undefined;

    const result = await new Promise<OutlineStreamFinishEvent>(
      (resolve, reject) => {
        void generateOutlineStream(
          {
            topic: topicForOutline,
            images: imageFiles.length > 0 ? imageFiles : undefined,
            sourceContent,
            templateRef,
            enableSearch: enableSearch.value,
            searchProvider:
              enableSearch.value && searchProvider.value !== "auto"
                ? searchProvider.value
                : undefined,
          },
          () => {},
          (event) => resolve(event),
          (event) =>
            resolve({ success: false, error: event.error || "生成大纲失败" }),
          (streamError) => reject(streamError),
        );
      },
    );

    const resolvedOutline = result.outline || "";
    const resolvedPages =
      Array.isArray(result.pages) && result.pages.length > 0
        ? result.pages
        : parsePagesFromRawOutline(resolvedOutline);

    if (
      result.success &&
      (resolvedPages.length > 0 || !!resolvedOutline.trim())
    ) {
      // 新主题成功生成大纲后，先清空旧任务上下文，避免复用历史图片/任务ID。
      store.resetGenerationContext();

      // 设置主题和大纲到 store
      store.setTopic(rawTopic);
      store.setOutline(resolvedOutline, resolvedPages);

      // 保存用户上传的图片到 store
      if (imageFiles.length > 0) {
        store.userImages = imageFiles;
      } else {
        store.userImages = [];
      }

      // 清理 ComposerInput 的预览
      composerRef.value?.clearPreviews();
      composerRef.value?.clearUrlState?.();
      uploadedImageFiles.value = [];
      urlContent.value = null;

      // 先进入大纲页，历史记录异步写入，避免被网络/数据库慢请求卡住跳转。
      void router.push("/redbook/outline");
      void persistOutlineHistory(rawTopic, resolvedOutline, resolvedPages);
    } else {
      error.value = result.error || "生成大纲失败";
    }
  } catch (err: any) {
    error.value = err.message || "网络错误，请重试";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  checkSearchStatus();
  userPrompt.value = store.imagePrompt.userPrompt || "";
  systemPrompt.value = store.imagePrompt.systemPrompt || "";
});

watch(
  [userPrompt, systemPrompt],
  ([nextUserPrompt, nextSystemPrompt]) => {
    store.setImagePrompt({
      userPrompt: nextUserPrompt,
      systemPrompt: nextSystemPrompt,
    });
  },
  { immediate: true },
);

watch(
  () => route.query.template_id,
  (value) => {
    const templateId = Array.isArray(value) ? value[0] : value;
    if (templateId && typeof templateId === "string") {
      applyTemplateById(templateId);
    } else {
      appliedTemplate.value = null;
    }
  },
  { immediate: true },
);
</script>

<style scoped>
.home-container {
  max-width: 1100px;
  width: 100%;
  flex: 1;
  display: flex;
  flex-direction: column;
  margin: 0 auto;
  position: relative;
  z-index: 1;
}

/* Hero Section - 深色模式优化 */
.hero-section {
  text-align: center;
  margin: auto 0; /* 垂直居中核心窗体 */
  padding: 56px 64px;
  animation: fadeIn 0.6s ease-out;
  background: var(--bg-card);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-color);
}

.hero-content {
  margin-bottom: 40px;
}

.prompt-config-card {
  margin-top: 20px;
  padding: 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--bg-elevated);
  text-align: left;
}

.prompt-config-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}

.prompt-config-desc {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-sub);
}

.prompt-config-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.prompt-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.prompt-field label {
  font-size: 12px;
  color: var(--text-sub);
}

.prompt-field textarea {
  width: 100%;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-main);
  padding: 10px 12px;
  resize: vertical;
  font-size: 13px;
  line-height: 1.45;
}

.prompt-field textarea:focus {
  outline: none;
  border-color: var(--primary);
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
  background: linear-gradient(
    90deg,
    var(--primary-light),
    rgba(56, 189, 248, 0.08)
  );
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
  padding: 0 0 16px;
  margin-top: 0;
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
  margin-bottom: 8px;
  color: var(--text-sub);
}

/* Animations */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 900px) {
  .template-applied-banner {
    flex-direction: column;
    align-items: flex-start;
  }

  .prompt-config-grid {
    grid-template-columns: 1fr;
  }
}
</style>
