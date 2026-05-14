## 1. Database Schema & Migration

- [x] 1.1 Create Alembic migration for `taxonomies` table with all columns (including optional `icon_identifier VARCHAR`), indexes, and `UNIQUE(name, scope)` constraint
- [x] 1.2 Create Alembic migration for `annotation_definitions` table with all columns (including optional `icon_identifier VARCHAR`), `UNIQUE(name, scope)` constraint, and `scale_labels` JSONB column
- [x] 1.3 Create Alembic migration for `trade_taxonomies` assignment table with FK to trades (CASCADE) and taxonomies (RESTRICT), `UNIQUE(trade_id, taxonomy_id)`
- [x] 1.4 Create Alembic migration for `checkin_taxonomies` assignment table with FK to checkins (CASCADE) and taxonomies (RESTRICT), `UNIQUE(checkin_id, taxonomy_id)`
- [x] 1.5 Create Alembic migration for `trade_annotations` table with typed columns (`value_int`, `value_float`, `value_bool`, `value_string`), FK rules, `UNIQUE(trade_id, annotation_definition_id)`, and CHECK constraint `num_nonnulls(...) = 1`
- [x] 1.6 Create Alembic migration for `checkin_annotations` table with identical structure and constraints as `trade_annotations`
- [x] 1.7 Run and verify all migrations locally; confirm all constraints are active

## 2. SQLAlchemy ORM Models

- [x] 2.1 Create `Taxonomy` ORM model in `app/models/taxonomy.py`
- [x] 2.2 Create `AnnotationDefinition` ORM model in `app/models/annotation_definition.py`
- [x] 2.3 Create `TradeTaxonomy` ORM model in `app/models/trade_taxonomy.py`
- [x] 2.4 Create `CheckinTaxonomy` ORM model in `app/models/checkin_taxonomy.py`
- [x] 2.5 Create `TradeAnnotation` ORM model in `app/models/trade_annotation.py` with all four typed value columns
- [x] 2.6 Create `CheckinAnnotation` ORM model in `app/models/checkin_annotation.py`
- [x] 2.7 Register all new models in `app/models/__init__.py`

## 3. Pydantic Schemas

- [x] 3.1 Create `TaxonomyCreate`, `TaxonomyUpdate`, `TaxonomyResponse` schemas in `app/schemas/taxonomy.py`; include hex color regex validator in `TaxonomyCreate`/`TaxonomyUpdate`; include optional `icon_identifier: str | None` field on all three schemas
- [x] 3.2 Create `AnnotationDefinitionCreate`, `AnnotationDefinitionUpdate`, `AnnotationDefinitionResponse` schemas in `app/schemas/annotation_definition.py`; include optional `icon_identifier: str | None` field on all three schemas
- [x] 3.3 Create `TaxonomyAssignRequest` schema (just `taxonomy_id`)
- [x] 3.4 Create `AnnotationAssignRequest` schema with a single `value: Any` field (typed validation happens in service)
- [x] 3.5 Create `TradeAnnotationResponse` and `CheckinAnnotationResponse` schemas that expose a resolved `value` field (not raw typed columns)
- [x] 3.6 Extend `TradeResponse` (detail variant) to include `taxonomies: list[TaxonomyResponse]` and `annotations: list[TradeAnnotationResponse]`
- [x] 3.7 Extend `CheckinResponse` (detail variant) to include `taxonomies` and `annotations` lists

## 4. Repositories

- [x] 4.1 Create `TaxonomyRepository` in `app/repositories/taxonomy_repository.py` with: `create`, `get_by_id`, `list` (filter archived), `update`, `count_assignments`, `delete`, `archive`
- [x] 4.2 Create `AnnotationDefinitionRepository` in `app/repositories/annotation_definition_repository.py` with same interface
- [x] 4.3 Create `TradeTaxonomyRepository` in `app/repositories/trade_taxonomy_repository.py` with: `assign`, `remove`, `list_for_trade`
- [x] 4.4 Create `CheckinTaxonomyRepository` in `app/repositories/checkin_taxonomy_repository.py`
- [x] 4.5 Create `TradeAnnotationRepository` in `app/repositories/trade_annotation_repository.py` with: `assign`, `update`, `remove`, `list_for_trade`
- [x] 4.6 Create `CheckinAnnotationRepository` in `app/repositories/checkin_annotation_repository.py`

## 5. Service Layer

- [x] 5.1 Create `TaxonomyService` in `app/services/taxonomy_service.py`: CRUD with smart delete (hard vs soft), scope mutation guard, hex validation delegation
- [x] 5.2 Create `AnnotationDefinitionService` in `app/services/annotation_definition_service.py`: CRUD with smart delete, type-change block, scope mutation guard
- [x] 5.3 Create `map_value_to_column` utility function in `app/utils/annotation_mapping.py` — takes `type`, `value`, and `scale_labels`; returns the typed dict and raises `ValueError` on invalid input
- [x] 5.4 Create `TradeMetadataService` in `app/services/trade_metadata_service.py`: taxonomy assign/remove, annotation assign/update/remove with full validation (scope, archive, type mapping, range, enum)
- [x] 5.5 Create `CheckinMetadataService` in `app/services/checkin_metadata_service.py`: same structure as `TradeMetadataService`

## 6. API Routers

- [x] 6.1 Create taxonomy CRUD router at `app/api/taxonomies.py`: `POST /taxonomies`, `GET /taxonomies`, `GET /taxonomies/{id}`, `PUT /taxonomies/{id}`, `DELETE /taxonomies/{id}`
- [x] 6.2 Create annotation definition CRUD router at `app/api/annotation_definitions.py`
- [x] 6.3 Create trade metadata router at `app/api/trades/{trade_id}/metadata.py` (or inline in trades router): assign/remove taxonomy, assign/update/remove annotation
- [x] 6.4 Create checkin metadata router analogous to trade metadata router
- [x] 6.5 Register all new routers in `app/main.py`
- [x] 6.6 Update trade detail endpoint to eagerly load taxonomies and annotations (using joins/subqueries in repository)
- [x] 6.7 Update checkin detail endpoint similarly

## 7. Unit Tests

- [x] 7.1 Test `map_value_to_column` utility: correct column for each type, rejection of wrong types, range validation, enum validation
- [x] 7.2 Test taxonomy service smart delete: hard delete when no assignments, soft delete when assignments exist
- [x] 7.3 Test annotation definition service smart delete: same as above
- [x] 7.4 Test type-change block on annotation definition update
- [x] 7.5 Test scope mutation guard: scope narrowing blocked when assignments exist, allowed when none
- [x] 7.6 Test taxonomy list endpoint excludes archived; detail endpoint includes archived
- [x] 7.7 Test annotation definition list endpoint excludes archived; detail includes archived
- [x] 7.8 Test trade taxonomy assignment: success, scope mismatch 422, archived definition 422, duplicate 409
- [x] 7.9 Test trade annotation assignment: all type mappings, wrong type 422, out-of-range 422, invalid enum 422, scope mismatch 422
- [x] 7.10 Test checkin taxonomy assignment: same coverage as trade taxonomy
- [x] 7.11 Test checkin annotation assignment: same coverage as trade annotation
- [x] 7.12 Test cascade deletion: deleting trade removes all `trade_taxonomies` and `trade_annotations` rows
- [x] 7.13 Test cascade deletion: deleting checkin removes all `checkin_taxonomies` and `checkin_annotations` rows
- [x] 7.14 Test hex color regex validation: valid format accepted, short/no-hash variants rejected
- [x] 7.15 Test trade detail response includes taxonomies and annotations with resolved values
- [x] 7.16 Test archived definition still appears in trade/checkin detail when assigned

## 8. Frontend API Client Integration

- [x] 8.1 Run `openapi-sync` skill to regenerate the TypeScript client via `@hey-api/openapi-ts` — confirm `openapi-ts.config.ts` points to the live FastAPI spec (`http://localhost:8000/openapi.json`) and uses `@hey-api/client-fetch` as the client
- [x] 8.2 Verify the generated `src/client/` output includes the new taxonomy and annotation-definition service modules and their request/response types
- [x] 8.3 Add TanStack Query hooks (using the generated hey-api services) for taxonomy CRUD: `useGetTaxonomies`, `useCreateTaxonomy`, `useUpdateTaxonomy`, `useDeleteTaxonomy`
- [x] 8.4 Add TanStack Query hooks for annotation definition CRUD: `useGetAnnotationDefinitions`, `useCreateAnnotationDefinition`, `useUpdateAnnotationDefinition`, `useDeleteAnnotationDefinition`
- [x] 8.5 Add TanStack Query hooks for trade metadata: `useAssignTradeTaxonomy`, `useRemoveTradeTaxonomy`, `useAssignTradeAnnotation`, `useUpdateTradeAnnotation`, `useRemoveTradeAnnotation`
- [x] 8.6 Add TanStack Query hooks for checkin metadata: same pattern as 8.5 for checkin endpoints
- [x] 8.7 Verify the trade detail query (`useGetTrade`) response type now includes `taxonomies` and `annotations` arrays as generated by hey-api

## 9. OpenAPI Documentation

- [x] 9.1 Add FastAPI route docstrings and response_model annotations to taxonomy router
- [x] 9.2 Add FastAPI route docstrings and response_model annotations to annotation definition router
- [x] 9.3 Add FastAPI route docstrings to trade metadata and checkin metadata routers
- [x] 9.4 Add Pydantic field descriptions to all new schemas (especially `scale_labels`, `scope`, `type`)
