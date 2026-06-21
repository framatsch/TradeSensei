## 1. Taxonomy Pydantic Params Models

- [x] 1.1 Add `CreateTaxonomyParams` model in `mcp.py` with fields: `name` (str), `scope` (str), `color_hex` (str), `description` (str | None), `icon_identifier` (str | None)
- [x] 1.2 Add `UpdateTaxonomyParams` model in `mcp.py` with fields: `taxonomy_id` (UUID), `name` (str | None), `scope` (str | None), `color_hex` (str | None), `description` (str | None), `icon_identifier` (str | None), `is_archived` (bool | None)
- [x] 1.3 Add `DeleteTaxonomyParams` model in `mcp.py` with fields: `taxonomy_id` (UUID) — no `force` parameter

## 2. Taxonomy Tool Handlers

- [x] 2.1 Implement `_handle_create_taxonomy` — validate params, call `TaxonomyService.create`, emit `taxonomy.created` audit event, return `{ "taxonomy_id", "name" }`
- [x] 2.2 Implement `_handle_update_taxonomy` — validate params, call `TaxonomyService.update`, emit `taxonomy.updated` audit event, return `{ "taxonomy_id", "name", "is_archived" }`
- [x] 2.3 Implement `_handle_delete_taxonomy` — validate params, call `TaxonomyService.archive` (not `delete`), emit `taxonomy.deleted` audit event, return `{ "archived": true }`. If taxonomy has active assignments, return error: "has active assignments — remove assignments before deleting"

## 3. Taxonomy Tool Registry Entries

- [x] 3.1 Register `create_taxonomy` in `_TOOL_REGISTRY` with JSON Schema input, handler, `mutating: True`
- [x] 3.2 Register `update_taxonomy` in `_TOOL_REGISTRY` with JSON Schema input, handler, `mutating: True`
- [x] 3.3 Register `delete_taxonomy` in `_TOOL_REGISTRY` with JSON Schema input, handler, `mutating: True`

## 4. Annotation Definition Pydantic Params Models

- [x] 4.1 Add `CreateAnnotationDefinitionParams` model in `mcp.py` with fields: `name` (str), `type` (Literal["int","float","bool","string_enum"]), `scope` (str), `description` (str | None), `icon_identifier` (str | None), `scale_labels` (dict | None)
- [x] 4.2 Add `UpdateAnnotationDefinitionParams` model in `mcp.py` with fields: `annotation_definition_id` (UUID), `name` (str | None), `type` (Literal | None), `scope` (str | None), `description` (str | None), `icon_identifier` (str | None), `scale_labels` (dict | None), `is_archived` (bool | None)
- [x] 4.3 Add `DeleteAnnotationDefinitionParams` model in `mcp.py` with fields: `annotation_definition_id` (UUID) — no `force` parameter

## 5. Annotation Definition Tool Handlers

- [x] 5.1 Implement `_handle_create_annotation_definition` — validate params, call `AnnotationDefinitionService.create`, emit `annotation_definition.created` audit event, return `{ "annotation_definition_id", "name", "type" }`
- [x] 5.2 Implement `_handle_update_annotation_definition` — validate params, call `AnnotationDefinitionService.update`, emit `annotation_definition.updated` audit event, return `{ "annotation_definition_id", "name", "is_archived" }`
- [x] 5.3 Implement `_handle_delete_annotation_definition` — validate params, call `AnnotationDefinitionService.archive` (not `delete`), emit `annotation_definition.deleted` audit event, return `{ "archived": true }`. If definition has active assignments, return error: "has active assignments — remove assignments before deleting"

## 6. Annotation Definition Tool Registry Entries

- [x] 6.1 Register `create_annotation_definition` in `_TOOL_REGISTRY` with JSON Schema input, handler, `mutating: True`
- [x] 6.2 Register `update_annotation_definition` in `_TOOL_REGISTRY` with JSON Schema input, handler, `mutating: True`
- [x] 6.3 Register `delete_annotation_definition` in `_TOOL_REGISTRY` with JSON Schema input, handler, `mutating: True`

## 7. Verification

- [ ] 7.1 Run `mypy --strict backend/app/api/mcp.py` — zero errors
- [x] 7.2 Run `ruff check backend/app/api/mcp.py` — no violations
- [x] 7.3 Verify that `TaxonomyService` and `AnnotationDefinitionService` have `update` and `delete` methods with the expected signatures (or note if adapter code is needed)
