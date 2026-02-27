# RenderInk Backend Rearchitecture Execution Plan

## Scope

This document is the executable plan for backend rearchitecture and the first implementation baseline.

Goals:

1. Rebuild backend into a layered architecture with clear boundaries.
2. Keep API paths stable while replacing internals.
3. Unify configuration through one service.
4. Keep local-first runtime and support remote database backends.
5. Add extensibility for generic image generation with custom `system_prompt + user_prompt`.

Out of scope for end-to-end tests in this phase:

1. Xiaohongshu publish end-to-end flow.

## Locked Decisions

1. Refactor strategy: strangler pattern (incremental replacement).
2. API strategy: keep existing `/api/*` paths and replace implementations directly.
3. Data strategy: local-first by default, switchable to Supabase/PostgreSQL.
4. Compatibility strategy: no legacy data compatibility layer.
5. Quality gates: tests + typing + lint.
6. Publish integration: MCP as primary adapter; Playwright as optional plugin.
7. Generic image generation: internal API capability first.
8. Prompt capability: support user-defined `system_prompt + user_prompt`.
9. Execution model: async job-first for image generation.

## Target Architecture

1. `bootstrap`: application settings, logging, app assembly, dependency wiring.
2. `interfaces`: HTTP/SSE transport and schema validation.
3. `application`: use cases and orchestration.
4. `domain`: entities, value objects, ports, domain errors.
5. `infrastructure`: adapter implementations for config/db/providers/storage/publish.

Dependency direction:

1. `interfaces -> application -> domain`
2. `infrastructure -> domain`
3. `bootstrap` wires all modules together.

## Adapter Boundaries (Moderate Abstraction)

1. `ConfigStorePort`: load/save/reload config.
2. Repositories split by business domain:
   - `HistoryRepositoryPort`
   - `ConceptRepositoryPort`
   - `PublishRepositoryPort`
   - `ImageJobRepositoryPort`
3. `SearchProviderPort`: `scrape`, `test_connection`.
4. `ImageProviderPort`: `generate`, `validate`, `get_capability`.
5. `PublishGatewayPort`: `check_login`, `publish`, `publish_video`.

## API Contract Direction

HTTP envelope:

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {
    "trace_id": "..."
  }
}
```

SSE envelope:

```json
{
  "event": "start|progress|error|finish",
  "run_id": "...",
  "ts": 0.0,
  "payload": {}
}
```

## Generic Image Platform Extension Points

Future extension points reserved from phase 1:

1. Prompt composition (`system_prompt + user_prompt + variables`).
2. Provider capability registry (size, ratio, multi-image support, references).
3. Async image job lifecycle (`queued/running/success/failed/cancelled`).
4. Asset store abstraction for local/object storage backends.

## Execution Phases

### Phase 0: Docs and Architecture Baseline

1. Add this plan document.
2. Start bootstrap layer implementation.

### Phase 1: Bootstrap Refactor (Current)

1. Introduce `backend/bootstrap` modules:
   - settings
   - logging
   - tracing
   - flask_factory
2. Convert `backend/app.py` into a thin entrypoint.
3. Add request `trace_id` propagation and response header.
4. Keep existing route modules functional.

### Phase 2: Config Unification

1. Introduce unified config service and adapters.
2. Replace direct config reads in route/service modules.

### Phase 3: Persistence Unification

1. Introduce SQLAlchemy + Alembic baseline.
2. Move history/concept/publish/image jobs to repositories.

### Phase 4: Adapter Refactor

1. Move search and image providers into adapter registries.
2. Keep publish flow behind gateway abstraction.

### Phase 5: Generic Image Generation Domain

1. Add async image job APIs.
2. Reuse the same platform for redbook/concept image generation.

### Phase 6+: Route Migration and Cleanup

1. Replace old handlers with use case-driven handlers.
2. Remove duplicate legacy code paths.

## Acceptance for the Current Step

1. `backend/app.py` only acts as entrypoint.
2. Flask app creation lives in `backend/bootstrap/flask_factory.py`.
3. Logging setup is centralized in bootstrap.
4. Request `trace_id` is generated/propagated and returned via `X-Request-ID`.
5. Existing API endpoints still start and run.

## Execution Progress (2026-02-27)

Completed in this iteration:

1. Added bootstrap modules:
   - `backend/bootstrap/settings.py`
   - `backend/bootstrap/logging.py`
   - `backend/bootstrap/tracing.py`
   - `backend/bootstrap/flask_factory.py`
2. Converted `backend/app.py` to a thin entrypoint while keeping `from backend.app import create_app` compatibility.
3. Migrated app assembly responsibilities into Flask factory:
   - CORS setup (with graceful fallback when dependency is missing)
   - API auth guard with `/api/health` exemption
   - limiter initialization (best-effort)
   - route registration
   - static output serving
   - frontend static hosting and API 404 fallback
   - startup config validation
4. Added request trace propagation:
   - accepts/passthrough incoming `X-Request-ID`
   - generates one when absent
   - writes `X-Request-ID` to response headers
5. Reduced startup-time hard dependency coupling:
   - image generator factory switched to lazy loading
   - `backend/clients` text/image exports switched to lazy loading

Verification:

1. `python -c "from backend.app import create_app; app = create_app(); ..."`: passed.
2. Flask test client `GET /api/health`: status `200`, response header includes `X-Request-ID`.
3. `python -m py_compile ...`: passed for all modified files.
4. `pytest -q`: no tests discovered in current repository (`no tests ran`).

## Execution Progress (2026-02-27, Iteration 2)

Completed in this iteration:

1. Added unified config service entry:
   - `backend/config/service.py` with `ConfigService` + `get_config_service()`
   - `backend/config/__init__.py` exports service symbols
   - `backend/bootstrap/container.py` with `AppContainer` as dependency registration point
2. Started Phase 2 migration by switching core modules from direct `Config` static usage to `ConfigService`:
   - `backend/bootstrap/flask_factory.py` (startup config validation path)
   - `backend/routes/config_routes.py`
   - `backend/services/content.py`
   - `backend/services/image.py`
   - `backend/services/outline.py`
   - `backend/services/pipeline_service.py`
   - `backend/routes/search_routes.py`
   - `backend/routes/concept_routes.py`
3. Kept backward compatibility:
   - Existing `Config` class and API contracts remain available
   - Migration is incremental and non-breaking for untouched modules
4. Added moderate search adapter abstraction for extensibility:
   - `backend/services/search_service.py` now includes `SearchProviderRegistry`
   - supports dynamic provider registration via `register_search_provider(...)`
   - default registry is prewired into `AppContainer` as `search_provider_registry`
5. Started database adapter abstraction (history domain):
   - added `backend/infrastructure/history/adapters.py`
   - added `HistoryStorageAdapterProtocol` with local/supabase adapters
   - `HistoryService` now delegates CRUD/list/search/statistics to storage adapter

Verification:

1. `python -m py_compile ...` passed for all newly modified files.
2. `create_app()` initialization passed.
3. `GET /api/health` returned `200` and still includes `X-Request-ID`.
4. `search_routes` and `concept_routes` import checks passed.

## Execution Progress (2026-02-27, Iteration 3)

Completed in this iteration:

1. Finished default config lookup migration in skill layer:
   - `backend/skills/analyze.py`
   - `backend/skills/design.py`
   - `backend/skills/generate.py`
   - `backend/skills/redbook/outline.py`
   - `backend/skills/redbook/content.py`
   - `backend/skills/concept/analyze.py`
   - `backend/skills/concept/design.py`
   - `backend/skills/concept/generate.py`
   - `backend/skills/concept/map_framework.py`
2. Introduced concept-history storage adapter abstraction:
   - added `backend/infrastructure/concept_history/adapters.py`
   - added `backend/infrastructure/concept_history/__init__.py`
   - `ConceptHistoryService` now delegates to adapter interfaces (local implementation in place)
3. Connected search route to container adapter registry:
   - `backend/routes/search_routes.py` now resolves providers from `backend_container.search_provider_registry` first
   - falls back to default provider lookup to keep backward compatibility
4. Kept behavior compatibility:
   - API routes and response contracts remain unchanged
   - default storage mode remains local-first

Verification:

1. `python -m py_compile ...` passed for all newly modified skill and concept-history files.
2. `GET /api/concept/history` returned `200` and includes `X-Request-ID`.
3. `GET /api/health` / `GET /api/config` / `GET /api/search/status` still returned `200`.

## Execution Progress (2026-02-27, Iteration 4)

Completed in this iteration:

1. Added domain port layer (`backend/domain/ports`) to formalize adapter contracts:
   - `ConfigStorePort`
   - `HistoryRepositoryPort`
   - `ConceptHistoryRepositoryPort`
   - `SearchProviderPort`
   - `ImageProviderPort`
   - `PublishGatewayPort`
2. Aligned current implementations to domain ports:
   - `BaseConfigStore` now conforms to `ConfigStorePort`
   - `BaseSearchProvider` now conforms to `SearchProviderPort`
   - history/concept-history adapter protocols are bound to repository ports
3. Kept route behavior stable while improving extensibility:
   - search route uses container registry first, fallback preserved
   - all checked endpoints remain backward compatible

Verification:

1. `python -m py_compile ...` passed for domain ports and aligned implementations.
2. `GET /api/health`, `GET /api/search/status`, `GET /api/concept/history` all returned `200` with `X-Request-ID`.

## Execution Progress (2026-02-27, Iteration 5)

Completed in this iteration:

1. Added interface-layer HTTP response utility:
   - `backend/interfaces/http/response.py`
   - unified `meta.trace_id` injection without forcing response shape rewrite
2. Applied response utility to search routes:
   - `backend/routes/search_routes.py` now consistently returns `meta.trace_id`
   - existing `success/error` contract preserved
3. Kept API compatibility:
   - no endpoint path changes
   - no required request payload changes

Verification:

1. `python -m py_compile ...` passed for new interface layer files and updated routes.
2. `GET /api/search/status` returned `200`, with `success=true` and `meta.trace_id` present.

## Execution Progress (2026-02-27, Iteration 6)

Completed in this iteration:

1. Added application-layer provider config service:
   - `backend/application/services/provider_config_service.py`
   - unified text/image provider config resolving API
2. Migrated repeated provider-config resolution logic to application layer:
   - all skill modules now use `ProviderConfigService` for default provider fallback
   - `backend/services/pipeline_service.py` now uses provider bundle from application service
   - `backend/routes/concept_routes.py` now uses provider bundle from application service
3. Refined image service dependency direction:
   - `backend/services/image.py` switched to application-layer provider config service

Verification:

1. `python -m py_compile ...` passed for application service and all migrated modules.
2. `GET /api/health`, `GET /api/search/status`, `GET /api/concept/history`, `GET /api/pipeline/types` all returned `200` with `X-Request-ID`.

## Execution Progress (2026-02-27, Iteration 7)

Completed in this iteration:

1. Extended interface-layer response helper usage to pipeline routes:
   - `backend/routes/pipeline_routes.py` switched from direct `jsonify` to `json_response(...)`
   - unified error/success responses now include `meta.trace_id`
2. Preserved pipeline behavior:
   - request/response payload fields remain backward compatible
   - SSE stream endpoint behavior unchanged

Verification:

1. `python -m py_compile backend/routes/pipeline_routes.py` passed.
2. `GET /api/pipeline/types` returned `200` with `meta.trace_id`.
3. `POST /api/pipeline/cancel` (missing `run_id`) returned `400` with `meta.trace_id` and expected error contract.

## Execution Progress (2026-02-27, Iteration 8)

Completed in this iteration:

1. Extended interface-layer response helper usage to concept/config routes:
   - `backend/routes/concept_routes.py` switched from `jsonify` to `json_response(...)`
   - `backend/routes/config_routes.py` switched from `jsonify` to `json_response(...)`
   - all updated endpoints now carry `meta.trace_id` while preserving existing payload fields
2. Introduced concept-history application service:
   - added `backend/application/services/concept_history_service.py`
   - `backend/routes/concept_routes.py` history endpoints now call application service instead of direct infrastructure service lookup
3. Updated application service export surface:
   - `backend/application/services/__init__.py` now exports concept-history application service factory

Verification:

1. `python -m py_compile` passed for updated application service and route files.
2. `GET /api/config` returned `200` with `meta.trace_id`.
3. `POST /api/config/test` (without API key) returned `400` with `meta.trace_id`.
4. `GET /api/concept/history` returned `200` with `meta.trace_id`.
5. `POST /api/concept/analyze` (missing `article`) returned `400` with `meta.trace_id`.

## Execution Progress (2026-02-27, Iteration 9)

Completed in this iteration:

1. Added history application service to reduce route-layer coupling:
   - added `backend/application/services/history_application_service.py`
   - updated `backend/application/services/__init__.py` exports
   - route now depends on application service instead of direct service factory lookups
2. Unified history route JSON responses:
   - `backend/routes/history_routes.py` switched from direct `jsonify` to `json_response(...)`
   - API payload fields preserved and `meta.trace_id` is now consistently included
3. Kept download behavior unchanged:
   - `send_file` branch remains intact for ZIP download endpoints
   - only JSON error/success responses were standardized

Verification:

1. `python -m py_compile` passed for `history_application_service.py`, `application/services/__init__.py`, `history_routes.py`.
2. `POST /api/history` returned `200` with `meta.trace_id`.
3. `GET /api/history` returned `200` with `meta.trace_id`.
4. `GET /api/history/stats` returned `200` with `meta.trace_id`.
5. `GET /api/history/nonexistent-id/exists` returned `200` with `meta.trace_id`.

## Execution Progress (2026-02-27, Iteration 10)

Completed in this iteration:

1. Unified response helper usage in content and outline routes:
   - `backend/routes/content_routes.py` switched from `jsonify` to `json_response(...)`
   - `backend/routes/outline_routes.py` switched from `jsonify` to `json_response(...)`
   - error responses in SSE initializer branches now also include `meta.trace_id`
2. Aligned content route history dependency with application layer:
   - `backend/routes/content_routes.py` now uses `get_history_application_service()`
   - removed direct dependency on `backend.services.history` from route layer
3. Added safer JSON parsing in content route:
   - non-dict payloads now normalize to empty dict before reading fields

Verification:

1. `python -m py_compile` passed for `content_routes.py`, `outline_routes.py`, `application/services/__init__.py`.
2. `POST /api/content` (missing topic/outline) returned `400` with `meta.trace_id`.
3. `POST /api/outline` (missing topic) returned `400` with `meta.trace_id`.
4. `POST /api/outline/stream` (missing topic) returned `400` with `meta.trace_id`.
5. `POST /api/outline/edit/stream` (invalid mode) returned `400` with `meta.trace_id`.

## Execution Progress (2026-02-27, Iteration 11)

Completed in this iteration:

1. Unified response helper usage in knowledge/template routes:
   - `backend/routes/knowledge_routes.py` switched to `json_response(...)`
   - `backend/routes/template_routes.py` switched to `json_response(...)`
2. Preserved endpoint contracts while adding trace metadata:
   - existing business fields and status codes remain unchanged
   - all JSON responses now consistently include `meta.trace_id`
3. Applied small request parsing hardening:
   - `knowledge_routes.py` now uses `request.get_json(silent=True)` for create endpoint to avoid parse exceptions bubbling into unclear errors

Verification:

1. `python -m py_compile` passed for `knowledge_routes.py`, `template_routes.py`.
2. `GET /api/knowledge/frameworks` returned `200` with `meta.trace_id`.
3. `POST /api/knowledge/frameworks` (empty payload) returned `400` with `meta.trace_id`.
4. `GET /api/templates` returned `200` with `meta.trace_id`.
5. `GET /api/templates/categories` returned `200` with `meta.trace_id`.

## Execution Progress (2026-02-27, Iteration 12)

Completed in this iteration:

1. Unified response helper usage in image routes:
   - `backend/routes/image_routes.py` switched from `jsonify` to `json_response(...)`
   - all JSON branches now include `meta.trace_id`
2. Preserved image route behavior:
   - SSE endpoints (`/generate`, `/retry-failed`) keep stream protocol unchanged
   - file download endpoints continue returning `send_file` / redirect where applicable
3. Kept validation and status contracts intact:
   - existing 400/404/500 branch conditions are preserved
   - success/error payload fields remain backward compatible

Verification:

1. `python -m py_compile` passed for `image_routes.py`.
2. `GET /api/images/task/1.txt` returned `400` with `meta.trace_id` (unsupported extension).
3. `POST /api/retry` (missing params) returned `400` with `meta.trace_id`.
4. `POST /api/retry-failed` (missing params) returned `400` with `meta.trace_id`.
5. `POST /api/regenerate` (missing params) returned `400` with `meta.trace_id`.
6. `GET /api/task/nonexistent` returned `404` with `meta.trace_id`.
7. `GET /api/health` returned `200` with `meta.trace_id`.

## Execution Progress (2026-02-27, Iteration 13)

Completed in this iteration:

1. Unified response helper usage in publish routes:
   - `backend/routes/publish_routes.py` switched from `jsonify` to `json_response(...)`
   - all JSON responses now consistently include `meta.trace_id`
2. Reduced duplicated async loop boilerplate in route layer:
   - added `_run_async(coro)` helper in publish route module
   - centralized event-loop lifecycle management for MCP/login/publish/list/search flows
3. Applied safer JSON parsing for publish POST APIs:
   - `request.get_json(silent=True)` + dict fallback in publish endpoints
   - preserved existing validation and status-code behavior

Verification:

1. `python -m py_compile` passed for `publish_routes.py`.
2. `GET /api/publish/status` returned `200` with `meta.trace_id`.
3. `GET /api/publish/search` (missing keyword) returned `400` with `meta.trace_id`.
4. `POST /api/publish/xiaohongshu` (missing required fields) returned `400` with `meta.trace_id`.
5. `POST /api/publish/video` (missing required fields) returned `400` with `meta.trace_id`.

## Execution Progress (2026-02-27, Iteration 14)

Completed in this iteration:

1. Added forward-compatible custom prompt extension for image generation:
   - `backend/routes/image_routes.py` now accepts optional `custom_prompt` in `/generate`, `/retry`, `/regenerate`
   - `backend/services/image.py` propagates `custom_prompt` through generation/retry/regenerate workflows
2. Persisted custom prompt into task runtime context:
   - image task state now stores `custom_prompt`
   - retry/retry-failed flows can reuse the same custom prompt when caller does not resend it
3. Injected custom prompt into model prompt assembly with safeguards:
   - custom prompt appended as high-priority section
   - input length capped to prevent prompt pollution from overlong payloads

Verification:

1. `python -m py_compile` passed for `image.py`, `image_routes.py`.
2. `POST /api/retry` (missing task/page, with custom_prompt) returned `400` with `meta.trace_id`.
3. `POST /api/regenerate` (missing task/page, with custom_prompt) returned `400` with `meta.trace_id`.
4. `POST /api/generate` (missing pages, with custom_prompt) returned `400` with `meta.trace_id`.

## Execution Progress (2026-02-27, Iteration 15)

Completed in this iteration:

1. Added image generation application service:
   - new `backend/application/services/image_generation_application_service.py`
   - `backend/application/services/__init__.py` exports image generation application service factory
   - `backend/routes/image_routes.py` now depends on application service instead of direct image service factory
2. Upgraded prompt extension to dual-channel format:
   - image route now supports `user_prompt/custom_prompt` and `system_prompt` (backward compatible)
   - image service now propagates both prompt channels through generate/retry/regenerate paths
3. Persisted prompt context for retry consistency:
   - image task state now stores both `custom_prompt` and `system_prompt`
   - retry and retry-failed flows can reuse prompt context without forcing client resend
4. Fixed circular dependency during app initialization:
   - `backend/services/image.py` switched to direct module import
     `backend.application.services.provider_config_service`
   - removed runtime import loop between application-service package and image service module

Verification:

1. `python -m py_compile` passed for:
   - `backend/application/services/image_generation_application_service.py`
   - `backend/application/services/__init__.py`
   - `backend/services/image.py`
   - `backend/routes/image_routes.py`
2. `POST /api/generate` (missing pages, with `user_prompt/system_prompt`) returned `400` with `meta.trace_id`.
3. `POST /api/retry` (missing task/page, with `user_prompt/system_prompt`) returned `400` with `meta.trace_id`.
4. `POST /api/regenerate` (missing task/page, with `custom_prompt/system_prompt`) returned `400` with `meta.trace_id`.
5. `GET /api/task/nonexistent` returned `404` with `meta.trace_id`.

## Execution Progress (2026-02-27, Iteration 16)

Completed in this iteration:

1. Added publish application service to isolate async orchestration from routes:
   - new `backend/application/services/publish_application_service.py`
   - centralized event-loop execution in application layer (`_run_async`)
2. Migrated publish routes to application service dependency:
   - `backend/routes/publish_routes.py` now uses `get_publish_application_service()`
   - route layer no longer manages event-loop lifecycle directly
3. Updated application service export surface:
   - `backend/application/services/__init__.py` now exports publish application service factory

Verification:

1. `python -m py_compile` passed for:
   - `backend/application/services/publish_application_service.py`
   - `backend/application/services/__init__.py`
   - `backend/routes/publish_routes.py`
2. `GET /api/publish/status` returned `200` with `meta.trace_id`.
3. `GET /api/publish/search` (missing keyword) returned `400` with `meta.trace_id`.
4. `POST /api/publish/xiaohongshu` (missing required fields) returned `400` with `meta.trace_id`.
5. Xiaohongshu real publish end-to-end flow remains intentionally untested in this phase.

## Execution Progress (2026-02-27, Iteration 17)

Completed in this iteration:

1. Added content/outline application services:
   - new `backend/application/services/content_application_service.py`
   - new `backend/application/services/outline_application_service.py`
2. Migrated route-layer dependencies to application layer:
   - `backend/routes/content_routes.py` now uses `get_content_application_service()`
   - `backend/routes/outline_routes.py` now uses `get_outline_application_service()`
3. Moved content history writeback orchestration into application layer:
   - content generation success path now writes back `titles/copywriting/tags` via application service
   - route no longer directly orchestrates history update details
4. Updated application service export surface:
   - `backend/application/services/__init__.py` now exports content/outline application service factories

Verification:

1. `python -m py_compile` passed for:
   - `backend/application/services/content_application_service.py`
   - `backend/application/services/outline_application_service.py`
   - `backend/application/services/__init__.py`
   - `backend/routes/content_routes.py`
   - `backend/routes/outline_routes.py`
2. `POST /api/content` (missing topic/outline) returned `400` with `meta.trace_id`.
3. `POST /api/outline` (missing topic) returned `400` with `meta.trace_id`.
4. `POST /api/outline/edit/stream` (invalid mode payload) returned `400` with `meta.trace_id`.

## Execution Progress (2026-02-27, Iteration 18)

Completed in this iteration:

1. Added template/knowledge application services:
   - new `backend/application/services/template_application_service.py`
   - new `backend/application/services/knowledge_application_service.py`
2. Migrated template/knowledge routes to application layer:
   - `backend/routes/template_routes.py` now uses `get_template_application_service()`
   - `backend/routes/knowledge_routes.py` now uses `get_knowledge_application_service()`
3. Moved knowledge formatting and write orchestration from route layer:
   - framework/chart/style formatting logic moved into knowledge application service
   - framework create/reload orchestration moved into application service
4. Updated application service export surface:
   - `backend/application/services/__init__.py` now exports template/knowledge service factories

Verification:

1. `python -m py_compile` passed for:
   - `backend/application/services/template_application_service.py`
   - `backend/application/services/knowledge_application_service.py`
   - `backend/application/services/__init__.py`
   - `backend/routes/template_routes.py`
   - `backend/routes/knowledge_routes.py`
2. `GET /api/templates` returned `200` with `meta.trace_id`.
3. `GET /api/templates/categories` returned `200` with `meta.trace_id`.
4. `GET /api/knowledge/frameworks` returned `200` with `meta.trace_id`.
5. `POST /api/knowledge/frameworks` (empty payload) returned `400` with `meta.trace_id`.

## Execution Progress (2026-02-27, Iteration 19)

Completed in this iteration:

1. Added pipeline application service:
   - new `backend/application/services/pipeline_application_service.py`
   - moved base64 image input normalization into application layer
2. Migrated pipeline routes to application layer:
   - `backend/routes/pipeline_routes.py` now depends on `get_pipeline_application_service()`
   - route-level duplicated base64 decode blocks removed
3. Eliminated import-cycle risk in application services package:
   - `backend/application/services/__init__.py` rewritten to lazy-export style (`__getattr__`)
   - avoids eager import chain for services that transitively depend on pipelines/skills
4. Fixed provider-config import direction in pipeline service:
   - `backend/services/pipeline_service.py` now imports provider config service directly from module file

Verification:

1. `python -m py_compile` passed for:
   - `backend/application/services/__init__.py`
   - `backend/application/services/pipeline_application_service.py`
   - `backend/services/pipeline_service.py`
   - `backend/routes/pipeline_routes.py`
2. `GET /api/pipeline/types` returned `200` with `meta.trace_id`.
3. `POST /api/pipeline/run` returned `200` with `meta.trace_id` (default request contract).
4. `POST /api/pipeline/cancel` (missing run_id) returned `400` with `meta.trace_id`.

## Execution Progress (2026-02-27, Iteration 20)

Completed in this iteration:

1. Completed frontend contract alignment for image prompt extension:
   - `frontend/src/api/index.ts` now supports `user_prompt/system_prompt` pass-through for:
     - `generateImagesPost(...)`
     - `regenerateImage(...)`
     - `retryFailedImages(...)`
   - kept backward compatibility with existing callers (all new prompt params are optional).
2. Fixed frontend publish API mismatch:
   - `publishToXiaohongshu(...)` switched from SSE parsing to standard JSON POST.
   - callbacks are preserved (`onProgress/onComplete/onError`) so UI integration remains stable.
3. Removed legacy backend service directory by migration:
   - moved all modules from `backend/services/*` to `backend/infrastructure/services/*`
   - updated all imports in application/routes/bootstrap/pipeline layers to new module path.
4. Adjusted moved service runtime paths:
   - fixed `__file__` parent-level path calculations for prompt files/history/data roots after relocation.
5. Deleted old directory:
   - `backend/services` removed after import replacement and validation.

Verification:

1. `python -m compileall backend`: passed.
2. `python -c "from backend.app import create_app; ..."`: passed (`APP_OK True`).
3. `cd frontend && npm run build`: passed.
4. Global search check:
   - no `backend.services.*` import remains in active code.

## Execution Progress (2026-02-27, Iteration 21)

Completed in this iteration:

1. Completed persistence unification baseline with SQLAlchemy + Alembic:
   - added SQLAlchemy session/model/repository modules under `backend/infrastructure/persistence/*`
   - added Alembic baseline files:
     - `alembic.ini`
     - `backend/migrations/alembic/env.py`
     - `backend/migrations/alembic/script.py.mako`
     - `backend/migrations/alembic/versions/0001_initial_baseline.py`
2. Completed repository port coverage for business domains:
   - added/extended domain ports:
     - `HistoryRepositoryPort`
     - `ConceptRepositoryPort`
     - `PublishRepositoryPort`
     - `ImageJobRepositoryPort`
   - added SQLAlchemy repository implementations for all above domains.
3. Connected storage adapters to database mode:
   - history/concept-history adapters now support `database/sqlalchemy/db` mode
   - kept local-first behavior as default for backward compatibility.
4. Added publish-domain persistence and gateway abstraction:
   - introduced `McpPublishGateway` behind `PublishGatewayPort`
   - publish application service now writes and updates publish audit records
   - added `GET /api/publish/records` for audit querying.
5. Added generic async image job domain APIs:
   - `POST /api/image-jobs`
   - `GET /api/image-jobs`
   - `GET /api/image-jobs/<job_id>`
   - `POST /api/image-jobs/<job_id>/cancel`

Verification:

1. `python -m compileall backend tests`: passed.
2. `pytest -q`: passed (`3 passed`).

## Execution Progress (2026-02-27, Iteration 22)

Completed in this iteration:

1. Completed frontend custom prompt integration for image generation:
   - added prompt input UI in `frontend/src/views/HomeView.vue`
   - added store state persistence and action method in `frontend/src/stores/generator.ts`
   - passed prompt context through generate/retry/regenerate flows in:
     - `frontend/src/views/GenerateView.vue`
     - `frontend/src/views/ResultView.vue`
     - `frontend/src/api/index.ts`
2. Completed backend prompt pass-through consistency:
   - `retry-failed` flow now supports and persists `user_prompt/system_prompt` context.
3. Fixed async image job service consistency issue:
   - removed duplicate `finished_at` assignment
   - unified to timezone-aware UTC timestamps in image job completion/failure paths.
4. Added automated testing baseline (no longer zero-test state):
   - added `tests/test_persistence_baseline.py`
   - covers history/concept/publish repositories and image-job application service.

Verification:

1. `python -m compileall backend tests`: passed.
2. `pytest -q`: passed (`3 passed`).
3. `cd frontend && npm run build`: passed.

Remaining intentionally out-of-scope in this phase:

1. Xiaohongshu real publish end-to-end verification remains intentionally skipped.
