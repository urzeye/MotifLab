# Firecrawl 残留项清单（待改）

更新时间：2026-02-26

## 范围说明

- 本清单用于记录项目中仍使用 `firecrawl` / `Firecrawl` 命名、但尚未迁移为通用 `search` 命名的内容。
- 当前后端主链路已迁移到 `search`（`/api/search/*` + `search_providers.yaml`）。
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

- 配置结构仍使用 `config.firecrawl`（应改为 `config.search`）。
- API 调用仍访问 `/api/firecrawl/status`、`/api/firecrawl/scrape`（应改为 `/api/search/status`、`/api/search/scrape`）。
- 类型与方法命名仍为 `FirecrawlConfig` / `getFirecrawlStatus` / `saveFirecrawlConfig` 等（应统一为 `Search...`）。
- UI 文案仍为“Firecrawl 抓取配置”（应改为“搜索服务配置”或“搜索抓取配置”）。

## 迁移建议（frontend）

1. `frontend/src/api/index.ts`：先替换 API 路径与响应类型，保留最小兼容映射。
2. `frontend/src/composables/useProviderForm.ts`：把 `firecrawlConfig` 改为 `searchConfig`，对齐后端 `search` payload。
3. `frontend/src/views/SettingsView.vue`：替换绑定字段与文案，支持多 provider（`firecrawl`/`exa`）。
4. `frontend/src/views/HomeView.vue` + `frontend/src/components/home/ComposerInput.vue`：将 `firecrawlEnabled` 重命名为 `searchEnabled` 并更新判断逻辑。

