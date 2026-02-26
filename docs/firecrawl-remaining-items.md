# Firecrawl 残留项清单（待改）

更新时间：2026-02-26

## 范围说明

- 本清单记录项目中仍使用 `firecrawl` / `Firecrawl` 命名、但尚未迁移为通用 `search` 命名的内容。
- 后端主链路已迁移到 `search`（`/api/search/*` + `search_providers.yaml`），并已支持 `bing`（默认）/`firecrawl`/`exa`/`tavily`/`perplexity`。
- 剩余项主要集中在前端（与当前“不改 frontend”约束一致）。

## 扫描命令

```bash
rg -n "fireclaw|firecrawl|Firecrawl" frontend --glob "!node_modules"
```

## 前端残留文件（按命中数量）

- `frontend/src/composables/useProviderForm.ts`（31 处）
- `frontend/src/views/SettingsView.vue`（25 处）
- `frontend/src/views/HomeView.vue`（8 处）
- `frontend/src/api/index.ts`（6 处）
- `frontend/src/components/home/ComposerInput.vue`（3 处）

## 主要残留类型

- 配置结构仍以 `config.firecrawl` 为中心，尚未切换为 `config.search.providers` 的多 provider 结构。
- API 调用仍访问 `/api/firecrawl/status`、`/api/firecrawl/scrape`（应改为 `/api/search/status`、`/api/search/scrape`）。
- 类型与方法命名仍为 `FirecrawlConfig` / `getFirecrawlStatus` / `saveFirecrawlConfig` 等（应统一为 `Search...`）。
- 设置页仍是单一 Firecrawl 视图，尚未支持多搜索服务配置（`bing`/`firecrawl`/`exa`/`tavily`/`perplexity`）。
- UI 文案仍为“Firecrawl 抓取配置”（应改为“搜索服务配置”或“搜索抓取配置”）。

## 迁移建议（frontend）

1. `frontend/src/api/index.ts`：统一替换为 `/api/search/*` 路径，并补齐 `bing`/`tavily`/`perplexity` 测试与状态类型。
2. `frontend/src/composables/useProviderForm.ts`：将 `firecrawlConfig` 改为 `searchProvidersConfig`，支持多 provider 表单与序列化。
3. `frontend/src/views/SettingsView.vue`：从“单一 Firecrawl 配置”改为“多搜索服务配置”，支持切换 active provider 与分别配置参数。
4. `frontend/src/views/HomeView.vue` + `frontend/src/components/home/ComposerInput.vue`：将 `firecrawlEnabled` 语义迁移为 `searchEnabled`，并展示当前 active provider（默认 `bing`）。
