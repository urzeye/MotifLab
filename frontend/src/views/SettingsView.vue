<template>
  <div class="container">
    <div class="page-header">
      <h1 class="page-title">系统设置</h1>
      <p class="page-subtitle">配置文本、图片和搜索服务</p>
    </div>

    <div
      v-if="loading"
      class="loading-container"
    >
      <div class="spinner"></div>
      <p>加载配置中...</p>
    </div>

    <div
      v-else
      class="settings-container"
    >
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="section-title">访问安全</h2>
            <p class="section-desc">配置前端访问令牌（仅保存在当前浏览器）</p>
          </div>
          <button
            class="btn btn-small"
            @click="refreshAuthStatus"
            :disabled="authChecking"
          >
            {{ authChecking ? "检测中..." : "刷新状态" }}
          </button>
        </div>

        <div class="security-status">
          <span
            class="status-pill"
            :class="authRequired ? 'required' : 'optional'"
          >
            {{ authRequired ? "服务端已开启令牌认证" : "服务端未开启令牌认证" }}
          </span>
          <span
            v-if="rateLimit"
            class="status-pill optional"
          >
            限流：{{ rateLimit }}
          </span>
        </div>

        <label
          class="token-label"
          for="access-token-input"
          >访问令牌</label
        >
        <div class="token-row">
          <input
            id="access-token-input"
            v-model="accessTokenInput"
            class="token-input"
            :type="showToken ? 'text' : 'password'"
            placeholder="输入 MOTIFLAB_AUTH_TOKEN"
            autocomplete="off"
            spellcheck="false"
          />
          <button
            class="btn btn-small"
            @click="showToken = !showToken"
          >
            {{ showToken ? "隐藏" : "显示" }}
          </button>
        </div>
        <p class="security-hint">
          说明：这里不会修改服务端环境变量，只是设置浏览器请求头里的
          `Authorization: Bearer ...`。
        </p>

        <div class="token-actions">
          <button
            class="btn btn-primary"
            @click="saveAccessTokenSetting"
            :disabled="authChecking"
          >
            保存并验证
          </button>
          <button
            class="btn"
            @click="clearAccessTokenSetting"
            :disabled="authChecking"
          >
            清除本地令牌
          </button>
        </div>

        <p
          v-if="tokenMessage"
          class="token-message"
          :class="tokenMessageType"
        >
          {{ tokenMessage }}
        </p>
      </div>

      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="section-title">文本生成配置</h2>
            <p class="section-desc">用于生成小红书图文大纲</p>
          </div>
          <button
            class="btn btn-small"
            @click="openAddTextModal"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <line
                x1="12"
                y1="5"
                x2="12"
                y2="19"
              ></line>
              <line
                x1="5"
                y1="12"
                x2="19"
                y2="12"
              ></line>
            </svg>
            添加
          </button>
        </div>

        <!-- 服务商列表表格 -->
        <ProviderTable
          :providers="textConfig.providers"
          :activeProvider="textConfig.active_provider"
          @activate="activateTextProvider"
          @edit="openEditTextModal"
          @delete="deleteTextProvider"
          @test="testTextProviderInList"
        />
      </div>

      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="section-title">图片生成配置</h2>
            <p class="section-desc">用于生成小红书配图</p>
          </div>
          <button
            class="btn btn-small"
            @click="openAddImageModal"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <line
                x1="12"
                y1="5"
                x2="12"
                y2="19"
              ></line>
              <line
                x1="5"
                y1="12"
                x2="19"
                y2="12"
              ></line>
            </svg>
            添加
          </button>
        </div>

        <!-- 服务商列表表格 -->
        <ProviderTable
          :providers="imageConfig.providers"
          :activeProvider="imageConfig.active_provider"
          @activate="activateImageProvider"
          @edit="openEditImageModal"
          @delete="deleteImageProvider"
          @test="testImageProviderInList"
        />
      </div>

      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="section-title">搜索服务配置</h2>
            <p class="section-desc">用于抓取网页内容并注入到大纲生成上下文</p>
          </div>
          <button
            class="search-add-btn"
            @click="openAddSearchModal"
            title="添加搜索服务"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <line
                x1="12"
                y1="5"
                x2="12"
                y2="19"
              ></line>
              <line
                x1="5"
                y1="12"
                x2="19"
                y2="12"
              ></line>
            </svg>
          </button>
        </div>

        <ProviderTable
          :providers="searchConfig.providers"
          :activeProvider="searchConfig.active_provider"
          providerCategory="search"
          :searchStatuses="searchStatuses"
          @activate="activateSearchProviderWithStatus"
          @edit="openEditSearchModal"
          @delete="deleteSearchProviderWithStatus"
          @test="testSearchProviderInListWithStatus"
        />

        <div class="search-runtime-card">
          <div class="search-runtime-row">
            <div class="runtime-label">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <circle
                  cx="12"
                  cy="12"
                  r="9"
                />
                <polyline points="12 7 12 12 15 15" />
              </svg>
              <span>默认搜索服务</span>
            </div>
            <n-select
              :value="searchConfig.active_provider"
              :options="searchDefaultProviderOptions"
              size="small"
              style="width: 210px"
              :disabled="searchRuntimeSaving"
              @update:value="handleSearchDefaultProviderChange"
            />
          </div>

          <div class="search-runtime-row">
            <div class="runtime-label">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  d="M12 21s-6.7-4.6-8.8-8.1A5.6 5.6 0 0 1 12 5a5.6 5.6 0 0 1 8.8 7.9C18.7 16.4 12 21 12 21Z"
                />
                <path d="M3 12h4l2-3 3 6 2-3h7" />
              </svg>
              <span>启动时自动测试连接</span>
            </div>
            <button
              class="runtime-switch"
              :class="{ active: searchConfig.auto_test_on_startup }"
              :disabled="searchRuntimeSaving"
              @click="toggleSearchAutoTest"
            >
              <span class="runtime-switch-dot" />
            </button>
          </div>

          <div class="search-runtime-row">
            <div class="runtime-label">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <line
                  x1="8"
                  y1="6"
                  x2="21"
                  y2="6"
                />
                <line
                  x1="8"
                  y1="12"
                  x2="21"
                  y2="12"
                />
                <line
                  x1="8"
                  y1="18"
                  x2="21"
                  y2="18"
                />
                <line
                  x1="3"
                  y1="6"
                  x2="3.01"
                  y2="6"
                />
                <line
                  x1="3"
                  y1="12"
                  x2="3.01"
                  y2="12"
                />
                <line
                  x1="3"
                  y1="18"
                  x2="3.01"
                  y2="18"
                />
              </svg>
              <span>最大结果数</span>
            </div>
            <div class="runtime-stepper">
              <button
                class="stepper-btn"
                :disabled="searchRuntimeSaving || searchConfig.max_results <= 1"
                @click="changeSearchMaxResults(-1)"
              >
                -
              </button>
              <span>{{ searchConfig.max_results }}</span>
              <button
                class="stepper-btn"
                :disabled="searchRuntimeSaving || searchConfig.max_results >= 20"
                @click="changeSearchMaxResults(1)"
              >
                +
              </button>
            </div>
          </div>

          <div class="search-runtime-row">
            <div class="runtime-label">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <circle
                  cx="12"
                  cy="12"
                  r="9"
                />
                <polyline points="12 7 12 12 15 15" />
              </svg>
              <span>超时时间（秒）</span>
            </div>
            <div class="runtime-stepper">
              <button
                class="stepper-btn"
                :disabled="searchRuntimeSaving || searchConfig.timeout_seconds <= 1"
                @click="changeSearchTimeoutSeconds(-1)"
              >
                -
              </button>
              <span>{{ searchConfig.timeout_seconds }}</span>
              <button
                class="stepper-btn"
                :disabled="searchRuntimeSaving || searchConfig.timeout_seconds >= 60"
                @click="changeSearchTimeoutSeconds(1)"
              >
                +
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 文本服务商弹窗 -->
    <ProviderModal
      :visible="showTextModal"
      :isEditing="!!editingTextProvider"
      :formData="textForm"
      :testing="testingText"
      :typeOptions="textTypeOptions"
      providerCategory="text"
      @close="closeTextModal"
      @save="saveTextProvider"
      @test="testTextConnection"
      @update:formData="updateTextForm"
    />

    <!-- 图片服务商弹窗 -->
    <ImageProviderModal
      :visible="showImageModal"
      :isEditing="!!editingImageProvider"
      :formData="imageForm"
      :testing="testingImage"
      :typeOptions="imageTypeOptions"
      @close="closeImageModal"
      @save="saveImageProvider"
      @test="testImageConnection"
      @update:formData="updateImageForm"
    />

    <!-- 搜索服务商弹窗 -->
    <ProviderModal
      :visible="showSearchModal"
      :isEditing="!!editingSearchProvider"
      :formData="searchForm"
      :testing="testingSearch"
      :typeOptions="searchTypeOptions"
      providerCategory="search"
      @close="closeSearchModal"
      @save="saveSearchProviderWithStatus"
      @test="testSearchConnectionWithStatus"
      @update:formData="updateSearchForm"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { NSelect } from "naive-ui";
import {
  getHealth,
  getAccessToken,
  setAccessToken,
  clearAccessToken,
  verifyAccessToken,
} from "../api";
import ProviderTable from "../components/settings/ProviderTable.vue";
import ProviderModal from "../components/settings/ProviderModal.vue";
import ImageProviderModal from "../components/settings/ImageProviderModal.vue";
import {
  useProviderForm,
  textTypeOptions,
  imageTypeOptions,
  searchTypeOptions,
} from "../composables/useProviderForm";

const accessTokenInput = ref(getAccessToken());
const showToken = ref(false);
const authChecking = ref(false);
const authRequired = ref(false);
const rateLimit = ref("");
const tokenMessage = ref("");
const tokenMessageType = ref<"ok" | "error">("ok");

async function refreshAuthStatus() {
  authChecking.value = true;
  try {
    const health = await getHealth();
    authRequired.value = !!health.auth_required;
    rateLimit.value = health.rate_limit || "";
    if (!health.success) {
      tokenMessageType.value = "error";
      tokenMessage.value = `健康检查失败：${health.message || "未知错误"}`;
    } else {
      tokenMessage.value = "";
    }
  } finally {
    authChecking.value = false;
  }
}

async function saveAccessTokenSetting() {
  const token = accessTokenInput.value.trim();

  if (!token) {
    if (authRequired.value) {
      tokenMessageType.value = "error";
      tokenMessage.value = "服务端已开启令牌认证，请输入有效令牌。";
      return;
    }
    clearAccessToken();
    tokenMessageType.value = "ok";
    tokenMessage.value = "服务端未开启认证，已清除本地令牌。";
    return;
  }

  setAccessToken(token);

  if (!authRequired.value) {
    tokenMessageType.value = "ok";
    tokenMessage.value = "令牌已保存。当前服务端未开启令牌认证。";
    return;
  }

  authChecking.value = true;
  try {
    const ok = await verifyAccessToken();
    if (ok) {
      tokenMessageType.value = "ok";
      tokenMessage.value = "令牌验证通过，后续请求将自动携带该令牌。";
      return;
    }

    clearAccessToken();
    accessTokenInput.value = "";
    tokenMessageType.value = "error";
    tokenMessage.value = "令牌验证失败，已清除本地令牌。请检查后重试。";
  } finally {
    authChecking.value = false;
  }
}

function clearAccessTokenSetting() {
  clearAccessToken();
  accessTokenInput.value = "";
  tokenMessageType.value = "ok";
  tokenMessage.value = "本地令牌已清除。";
}

/**
 * 系统设置页面
 *
 * 功能：
 * - 管理文本生成服务商配置
 * - 管理图片生成服务商配置
 * - 测试 API 连接
 */

// 使用 composable 管理表单状态和逻辑
const {
  // 状态
  loading,
  testingText,
  testingImage,
  testingSearch,

  // 配置数据
  textConfig,
  imageConfig,
  searchConfig,

  // 文本服务商弹窗
  showTextModal,
  editingTextProvider,
  textForm,

  // 图片服务商弹窗
  showImageModal,
  editingImageProvider,
  imageForm,
  showSearchModal,
  editingSearchProvider,
  searchForm,

  // 方法
  loadConfig,

  // 文本服务商方法
  activateTextProvider,
  openAddTextModal,
  openEditTextModal,
  closeTextModal,
  saveTextProvider,
  deleteTextProvider,
  testTextConnection,
  testTextProviderInList,
  updateTextForm,

  // 图片服务商方法
  activateImageProvider,
  openAddImageModal,
  openEditImageModal,
  closeImageModal,
  saveImageProvider,
  deleteImageProvider,
  testImageConnection,
  testImageProviderInList,
  updateImageForm,
  activateSearchProvider,
  openAddSearchModal,
  openEditSearchModal,
  closeSearchModal,
  saveSearchProvider,
  deleteSearchProvider,
  testSearchConnection,
  testSearchProviderInList,
  saveSearchConfig,
  updateSearchForm,
} = useProviderForm();

type SearchConnectionState = "idle" | "testing" | "success" | "failed";

const searchStatuses = ref<Record<string, SearchConnectionState>>({});
const searchRuntimeSaving = ref(false);
const SEARCH_PROVIDER_LABELS: Record<string, string> = {
  bing: "Bing (Local)",
  firecrawl: "Firecrawl",
  exa: "Exa",
  tavily: "Tavily",
  perplexity: "Perplexity",
};

function getSearchProviderLabel(name: string, provider: any): string {
  const normalizedName = String(name || "").trim();
  const type = String(provider?.type || normalizedName).trim().toLowerCase();
  const typeLabel = SEARCH_PROVIDER_LABELS[type] || type || normalizedName;
  if (!normalizedName || normalizedName === type) return typeLabel;
  return `${normalizedName} (${typeLabel})`;
}

const searchDefaultProviderOptions = computed(() => {
  const providers = searchConfig.value.providers || {};
  return Object.entries(providers).map(([name, provider]) => ({
    value: name,
    label: getSearchProviderLabel(name, provider),
  }));
});

function syncSearchStatuses() {
  const providers = searchConfig.value.providers || {};
  const next: Record<string, SearchConnectionState> = {};

  for (const name of Object.keys(providers)) {
    const current = searchStatuses.value[name];
    if (current) {
      next[name] = current;
      continue;
    }
    next[name] = searchConfig.value.active_provider === name ? "success" : "idle";
  }

  searchStatuses.value = next;
}

watch(
  () => ({
    active: searchConfig.value.active_provider,
    providers: searchConfig.value.providers,
  }),
  () => {
    syncSearchStatuses();
  },
  { deep: true, immediate: true }
);

async function activateSearchProviderWithStatus(name: string) {
  await activateSearchProvider(name);
  searchStatuses.value[name] = "success";
}

async function handleSearchDefaultProviderChange(name: string) {
  const target = String(name || "").trim();
  if (!target || target === searchConfig.value.active_provider) {
    return;
  }
  await activateSearchProviderWithStatus(target);
}

async function deleteSearchProviderWithStatus(name: string) {
  await deleteSearchProvider(name);
  if (!searchConfig.value.providers[name]) {
    const next = { ...searchStatuses.value };
    delete next[name];
    searchStatuses.value = next;
  }
}

async function enableSearchProviderAfterTest(name: string) {
  const provider = searchConfig.value.providers[name];
  if (!provider || provider.enabled !== false) return;
  provider.enabled = true;
  await saveSearchConfig();
}

async function testSearchProviderInListWithStatus(name: string, provider: any) {
  searchStatuses.value[name] = "testing";
  const ok = await testSearchProviderInList(name, provider);
  searchStatuses.value[name] = ok ? "success" : "failed";
  if (ok) {
    await enableSearchProviderAfterTest(name);
  }
}

async function testSearchConnectionWithStatus() {
  const target = editingSearchProvider.value || searchForm.value.name;
  if (target) {
    searchStatuses.value[target] = "testing";
  }
  const ok = await testSearchConnection();
  if (target) {
    searchStatuses.value[target] = ok ? "success" : "failed";
    if (ok) {
      await enableSearchProviderAfterTest(target);
    }
  }
}

async function saveSearchProviderWithStatus() {
  const target = editingSearchProvider.value || searchForm.value.name;
  await saveSearchProvider();
  if (target && searchConfig.value.providers[target]) {
    if (!searchStatuses.value[target]) {
      searchStatuses.value[target] = "idle";
    }
    if (searchConfig.value.active_provider === target) {
      searchStatuses.value[target] = "success";
    }
  }
}

async function persistSearchRuntimeSettings() {
  if (searchRuntimeSaving.value) return;
  searchRuntimeSaving.value = true;
  try {
    await saveSearchConfig();
  } finally {
    searchRuntimeSaving.value = false;
  }
}

async function toggleSearchAutoTest() {
  searchConfig.value.auto_test_on_startup = !searchConfig.value.auto_test_on_startup;
  await persistSearchRuntimeSettings();
}

async function changeSearchMaxResults(delta: number) {
  const next = Math.min(20, Math.max(1, searchConfig.value.max_results + delta));
  if (next === searchConfig.value.max_results) return;
  searchConfig.value.max_results = next;
  await persistSearchRuntimeSettings();
}

async function changeSearchTimeoutSeconds(delta: number) {
  const next = Math.min(60, Math.max(1, searchConfig.value.timeout_seconds + delta));
  if (next === searchConfig.value.timeout_seconds) return;
  searchConfig.value.timeout_seconds = next;
  await persistSearchRuntimeSettings();
}

onMounted(async () => {
  await Promise.all([loadConfig(), refreshAuthStatus()]);
  accessTokenInput.value = getAccessToken();
});
</script>

<style scoped>
/* 覆盖掉冲突的局部样式 */
.security-status {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  border-radius: 999px;
  padding: 4px 10px;
  border: 1px solid transparent;
}

.status-pill.required {
  color: var(--color-error);
  background: var(--color-error-bg);
  border-color: var(--color-error-border);
}

.status-pill.optional {
  color: var(--text-secondary);
  background: var(--bg-hover);
  border-color: var(--border-color);
}

.token-label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-sub);
}

.token-row {
  display: flex;
  gap: 12px;
}

.token-input {
  flex: 1;
  height: 48px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 0 16px;
  font-size: 15px;
  background: var(--bg-body);
  color: var(--text-main);
  transition: all var(--transition-fast);
}

.token-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 2px var(--primary-light);
  background: var(--bg-elevated);
}

.security-hint {
  margin: 10px 0 0;
  font-size: 13px;
  color: var(--text-sub);
}

.token-actions {
  margin-top: 16px;
  display: flex;
  gap: 12px;
}

.token-message {
  margin: 12px 0 0;
  font-size: 13px;
}

.token-message.ok {
  color: var(--color-success);
}

.token-message.error {
  color: var(--color-error);
}

/* 按钮样式 (重新统一) */
.btn-small {
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-body);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-small:hover {
  background: var(--bg-hover);
  border-color: var(--text-sub);
}

.btn-small svg {
  stroke-width: 2.5;
}

.search-add-btn {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-sub);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.search-add-btn:hover {
  border-color: var(--border-color);
  background: var(--bg-hover);
  color: var(--text-main);
}

.search-runtime-card {
  margin-top: 20px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--bg-elevated);
}

.search-runtime-row {
  min-height: 56px;
  padding: 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.search-runtime-row + .search-runtime-row {
  border-top: 1px solid var(--border-color);
}

.runtime-label {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  color: var(--text-main);
}

.runtime-label svg {
  width: 18px;
  height: 18px;
  color: var(--text-sub);
  flex-shrink: 0;
}

.runtime-switch {
  width: 46px;
  height: 28px;
  border-radius: 999px;
  border: 1px solid #d1d5db;
  background: #e5e7eb;
  padding: 2px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.runtime-switch.active {
  border-color: #10b981;
  background: #10b981;
  box-shadow: 0 0 0 1px rgba(16, 185, 129, 0.15);
}

.runtime-switch:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.runtime-switch-dot {
  display: block;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
  transition: transform var(--transition-fast);
}

.runtime-switch.active .runtime-switch-dot {
  transform: translateX(18px);
}

.runtime-stepper {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.stepper-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-sub);
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.stepper-btn:hover:not(:disabled) {
  background: var(--bg-hover);
  color: var(--text-main);
}

.stepper-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.runtime-stepper span {
  min-width: 26px;
  text-align: center;
  color: var(--text-main);
}

@media (max-width: 768px) {
  .search-runtime-row {
    min-height: 52px;
    padding: 0 10px;
  }

  .runtime-label {
    font-size: 14px;
  }
}

/* 加载状态 */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: var(--text-sub);
}
</style>
