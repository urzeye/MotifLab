<template>
  <div
    v-if="providerCategory === 'search'"
    class="search-provider-list"
  >
    <div
      v-for="(provider, name) in providers"
      :key="name"
      class="search-provider-row"
      :class="{ active: activeProvider === name }"
      @click="$emit('activate', name)"
    >
      <div class="search-provider-main">
        <span
          class="provider-logo"
          :class="`provider-logo-${getProviderType(name, provider)}`"
          aria-hidden="true"
        >
          <svg
            v-if="getProviderType(name, provider) === 'perplexity'"
            viewBox="0 0 24 24"
          >
            <path
              d="M22.3977 7.0896h-2.3106V.0676l-7.5094 6.3542V.1577h-1.1554v6.1966L4.4904 0v7.0896H1.6023v10.3976h2.8882V24l6.932-6.3591v6.2005h1.1554v-6.0469l6.9318 6.1807v-6.4879h2.8882V7.0896zm-3.4657-4.531v4.531h-5.355l5.355-4.531zm-13.2862.0676 4.8691 4.4634H5.6458V2.6262zM2.7576 16.332V8.245h7.8476l-6.1149 6.1147v1.9723H2.7576zm2.8882 5.0404v-3.8852h.0001v-2.6488l5.7763-5.7764v7.0111l-5.7764 5.2993zm12.7086.0248-5.7766-5.1509V9.0618l5.7766 5.7766v6.5588zm2.8882-5.0652h-1.733v-1.9723L13.3948 8.245h7.8478v8.087z"
            />
          </svg>
          <svg
            v-else-if="getProviderType(name, provider) === 'exa'"
            viewBox="0 0 24 24"
          >
            <path d="M5 4h4l3 4 3-4h4l-5 7 5 9h-4l-3-5-3 5H5l5-9z" />
          </svg>
          <svg
            v-else-if="getProviderType(name, provider) === 'tavily'"
            viewBox="0 0 24 24"
          >
            <circle
              cx="12"
              cy="12"
              r="8.5"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            />
            <path d="m8 14 8-4-4 8-1-3-3-1z" />
          </svg>
          <svg
            v-else-if="getProviderType(name, provider) === 'firecrawl'"
            viewBox="0 0 24 24"
          >
            <path
              d="M12 2c2.8 3.1 4.1 5.1 4.1 7.2 0 1.9-1.2 3.6-3.2 4.8.3-2.2-.5-3.8-2.4-4.8-1 2.7-3.6 3.6-3.6 6.8A5 5 0 0 0 12 21a5 5 0 0 0 5-5c0-5.4-4.5-8.3-5-14Z"
            />
          </svg>
          <svg
            v-else
            viewBox="0 0 24 24"
          >
            <path d="M7 3v17l9-4.6-4.4-3 4.4-3.2L7 3Z" />
          </svg>
        </span>
        <div class="search-provider-text">
          <span class="search-provider-name">{{ getProviderDisplayName(name, provider) }}</span>
          <span
            v-if="shouldShowProviderType(name, provider)"
            class="search-provider-type"
          >
            {{ getProviderTypeLabel(name, provider) }}
          </span>
        </div>
      </div>

      <div class="search-provider-actions">
        <span
          class="search-status"
          :class="getSearchStatusMeta(name, provider).className"
        >
          {{ getSearchStatusMeta(name, provider).text }}
        </span>

        <n-tooltip trigger="hover">
          <template #trigger>
            <button
              class="search-action-btn"
              @click.stop="$emit('edit', name, provider)"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <line
                  x1="4"
                  y1="21"
                  x2="10"
                  y2="21"
                />
                <line
                  x1="4"
                  y1="14"
                  x2="14"
                  y2="14"
                />
                <line
                  x1="4"
                  y1="7"
                  x2="20"
                  y2="7"
                />
                <circle
                  cx="14"
                  cy="21"
                  r="2"
                />
                <circle
                  cx="18"
                  cy="14"
                  r="2"
                />
                <circle
                  cx="8"
                  cy="7"
                  r="2"
                />
              </svg>
            </button>
          </template>
          编辑服务
        </n-tooltip>

        <n-tooltip trigger="hover">
          <template #trigger>
            <button
              class="search-action-btn"
              @click.stop="$emit('test', name, provider)"
            >
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
            </button>
          </template>
          测试连接
        </n-tooltip>

        <n-tooltip
          v-if="canDelete"
          trigger="hover"
        >
          <template #trigger>
            <button
              class="search-action-btn danger"
              @click.stop="$emit('delete', name)"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <polyline points="3 6 5 6 21 6" />
                <path
                  d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
                />
              </svg>
            </button>
          </template>
          删除
        </n-tooltip>
      </div>
    </div>
  </div>

  <div
    v-else
    class="provider-table"
  >
    <div class="table-header">
      <div class="col-status">状态</div>
      <div class="col-name">名称</div>
      <div class="col-model">模型</div>
      <div class="col-apikey">API Key</div>
      <div class="col-actions">操作</div>
    </div>
    <div
      v-for="(provider, name) in providers"
      :key="name"
      class="table-row"
      :class="{ active: activeProvider === name }"
    >
      <div class="col-status">
        <button
          class="btn-activate"
          :class="{ active: activeProvider === name }"
          @click="$emit('activate', name)"
          :disabled="activeProvider === name"
        >
          {{ activeProvider === name ? '已激活' : '激活' }}
        </button>
      </div>
      <div class="col-name">
        <span class="table-provider-name">{{ name }}</span>
      </div>
      <div class="col-model">
        <span class="model-name">{{ provider.model }}</span>
      </div>
      <div class="col-apikey">
        <span
          class="apikey-masked"
          :class="{ empty: !provider.api_key_masked }"
        >
          {{ provider.api_key_masked || '未配置' }}
        </span>
      </div>
      <div class="col-actions">
        <n-tooltip trigger="hover">
          <template #trigger>
            <button
              class="btn-icon"
              @click="$emit('test', name, provider)"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
              </svg>
            </button>
          </template>
          测试连接
        </n-tooltip>

        <n-tooltip trigger="hover">
          <template #trigger>
            <button
              class="btn-icon"
              @click="$emit('edit', name, provider)"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"
                ></path>
                <path
                  d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"
                ></path>
              </svg>
            </button>
          </template>
          编辑
        </n-tooltip>

        <n-tooltip
          v-if="canDelete"
          trigger="hover"
        >
          <template #trigger>
            <button
              class="btn-icon danger"
              @click="$emit('delete', name)"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <polyline points="3 6 5 6 21 6"></polyline>
                <path
                  d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
                ></path>
              </svg>
            </button>
          </template>
          删除
        </n-tooltip>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NTooltip } from 'naive-ui'

interface Provider {
  type: string
  model: string
  base_url?: string
  api_key?: string
  api_key_masked?: string
  enabled?: boolean
  _has_api_key?: boolean
}

type SearchTestStatus = 'idle' | 'testing' | 'success' | 'failed'

const props = withDefaults(defineProps<{
  providers: Record<string, Provider>
  activeProvider: string
  providerCategory?: 'text' | 'image' | 'search'
  searchStatuses?: Record<string, SearchTestStatus>
}>(), {
  providerCategory: 'text',
  searchStatuses: () => ({})
})

defineEmits<{
  (e: 'activate', name: string): void
  (e: 'edit', name: string, provider: Provider): void
  (e: 'delete', name: string): void
  (e: 'test', name: string, provider: Provider): void
}>()

const canDelete = computed(() => Object.keys(props.providers).length > 1)

const SEARCH_PROVIDER_LABELS: Record<string, string> = {
  perplexity: 'Perplexity',
  exa: 'Exa',
  tavily: 'Tavily',
  firecrawl: 'Firecrawl',
  bing: 'Bing (Local)',
}

function getProviderType(name: string, provider: Provider): string {
  return String(provider.type || name).trim().toLowerCase()
}

function getProviderLabel(name: string, provider: Provider): string {
  const providerType = getProviderType(name, provider)
  return SEARCH_PROVIDER_LABELS[providerType] || name
}

function getProviderDisplayName(name: string, provider: Provider): string {
  const normalizedName = String(name || '').trim()
  const providerType = getProviderType(name, provider)
  if (normalizedName.toLowerCase() === providerType) {
    return getProviderLabel(name, provider)
  }
  return normalizedName || getProviderLabel(name, provider)
}

function getProviderTypeLabel(name: string, provider: Provider): string {
  return getProviderLabel(name, provider)
}

function shouldShowProviderType(name: string, provider: Provider): boolean {
  const normalizedName = String(name || '').trim().toLowerCase()
  return normalizedName.length > 0 && normalizedName !== getProviderType(name, provider)
}

function getSearchStatusMeta(name: string, provider: Provider): { text: string; className: string } {
  const status = props.searchStatuses[name]
  if (status === 'testing') return { text: '测试中', className: 'testing' }
  if (status === 'success') return { text: '已连接', className: 'connected' }
  if (status === 'failed') return { text: '连接失败', className: 'failed' }

  const providerType = getProviderType(name, provider)
  const hasApiKey = Boolean(provider._has_api_key || String(provider.api_key_masked || '').trim())
  const allowEmptyApiKey = providerType === 'bing' || providerType === 'firecrawl'
  const providerEnabled = provider.enabled !== false

  if (providerEnabled && (allowEmptyApiKey || hasApiKey)) {
    return { text: '已连接', className: 'connected' }
  }

  if (!hasApiKey && !allowEmptyApiKey) {
    return { text: '未配置', className: 'pending' }
  }

  return { text: '未测试', className: 'idle' }
}
</script>

<style scoped>
.search-provider-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.search-provider-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.search-provider-row:hover {
  border-color: var(--border-hover);
  background: var(--bg-hover);
}

.search-provider-row.active {
  border-color: var(--color-success-border);
  background: color-mix(in srgb, var(--color-success-bg) 35%, var(--bg-card));
}

.search-provider-main {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.search-provider-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.search-provider-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
}

.search-provider-type {
  font-size: 12px;
  color: var(--text-sub);
  line-height: 1.2;
}

.provider-logo {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.provider-logo svg {
  width: 17px;
  height: 17px;
  fill: currentColor;
}

.provider-logo-tavily svg {
  fill: none;
}

.provider-logo-perplexity {
  color: #27b8c8;
  background: rgba(39, 184, 200, 0.12);
}

.provider-logo-exa {
  color: #3b73ff;
  background: rgba(59, 115, 255, 0.12);
}

.provider-logo-tavily {
  color: #5f95f9;
  background: rgba(95, 149, 249, 0.12);
}

.provider-logo-firecrawl {
  color: #ef5f43;
  background: rgba(239, 95, 67, 0.14);
}

.provider-logo-bing {
  color: #2ebfcf;
  background: rgba(46, 191, 207, 0.14);
}

.search-provider-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.search-status {
  height: 24px;
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.search-status.connected {
  color: var(--color-success);
  background: var(--color-success-bg);
}

.search-status.testing {
  color: var(--color-warning);
  background: var(--color-warning-bg);
}

.search-status.failed {
  color: var(--color-error);
  background: var(--color-error-bg);
}

.search-status.idle,
.search-status.pending {
  color: var(--text-sub);
  background: var(--bg-hover);
}

.search-action-btn {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-sub);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.search-action-btn svg {
  width: 17px;
  height: 17px;
}

.search-action-btn:hover {
  background: var(--bg-elevated);
  border-color: var(--border-color);
  color: var(--text-main);
}

.search-action-btn.danger:hover {
  color: var(--color-error);
  border-color: var(--color-error-border);
  background: var(--color-error-bg);
}

.provider-table {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--bg-card);
}

.table-header {
  display: grid;
  grid-template-columns: 96px minmax(130px, 0.85fr) minmax(170px, 1fr) minmax(240px, 1.75fr) 108px;
  gap: 12px;
  padding: 14px 16px;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-color);
  font-size: var(--caption-size);
  font-weight: 600;
  color: var(--text-sub);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.table-row {
  display: grid;
  grid-template-columns: 96px minmax(130px, 0.85fr) minmax(170px, 1fr) minmax(240px, 1.75fr) 108px;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
  align-items: center;
  transition: background-color var(--transition-fast);
}

.table-header > div,
.table-row > div {
  min-width: 0;
  white-space: nowrap;
}

.table-row:last-child {
  border-bottom: none;
}

.table-row:hover {
  background: var(--bg-elevated);
}

.table-row.active {
  background: var(--primary-fade);
  border-left: 3px solid var(--primary);
}

.btn-activate {
  padding: 6px 12px;
  border-radius: var(--radius-xs);
  font-size: var(--caption-size);
  font-weight: 500;
  border: 1px solid var(--border-color);
  background: var(--bg-elevated);
  color: var(--text-sub);
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.btn-activate:hover:not(:disabled) {
  border-color: var(--primary);
  color: var(--primary);
  background: var(--primary-fade);
}

.btn-activate.active {
  background: var(--primary-light);
  border-color: var(--primary);
  color: var(--primary);
  cursor: default;
}

.table-provider-name {
  display: block;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-name {
  display: inline-block;
  max-width: 100%;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: var(--caption-size);
  color: var(--text-sub);
  background: var(--bg-input);
  padding: 4px 8px;
  border-radius: var(--radius-xs);
  border: 1px solid var(--border-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: middle;
}

.apikey-masked {
  display: block;
  font-size: var(--caption-size);
  font-family: 'Monaco', 'Menlo', monospace;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: normal;
}

.apikey-masked.empty {
  color: #f59e0b;
}

.col-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.btn-icon {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background: var(--bg-elevated);
  color: var(--text-sub);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.btn-icon:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: var(--primary-fade);
}

.btn-icon.danger:hover {
  border-color: var(--color-error);
  color: var(--color-error);
  background: var(--color-error-bg);
}

.status-badge.warning {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

@media (max-width: 768px) {
  .search-provider-row {
    align-items: flex-start;
    gap: 10px;
    flex-direction: column;
  }

  .search-provider-actions {
    width: 100%;
    justify-content: space-between;
  }

  .search-provider-name {
    font-size: 16px;
  }

  .table-header,
  .table-row {
    grid-template-columns: 70px 1fr 100px;
  }

  .col-model,
  .col-apikey {
    display: none;
  }
}
</style>
