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

Verification:

1. `python -m py_compile ...` passed for all newly modified files.
2. `create_app()` initialization passed.
3. `GET /api/health` returned `200` and still includes `X-Request-ID`.
4. `search_routes` and `concept_routes` import checks passed.
