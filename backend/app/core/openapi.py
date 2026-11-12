"""Register public file contracts separately from their schema response DTO."""

from typing import Any

from fastapi import FastAPI

from app.schemas.generic_import import GenericExecutionDocumentV1


def register_execution_format_components(application: FastAPI) -> None:
    """Extend generated OpenAPI with the document and nested execution models."""
    original = application.openapi

    def with_execution_format() -> dict[str, Any]:  # Any: FastAPI's OpenAPI document is recursively heterogeneous JSON.
        document = original()
        schema = GenericExecutionDocumentV1.model_json_schema(ref_template="#/components/schemas/{model}")
        definitions = schema.pop("$defs", {})
        components = document.setdefault("components", {}).setdefault("schemas", {})
        components.update(definitions)
        components[GenericExecutionDocumentV1.__name__] = schema
        return document

    application.openapi = with_execution_format  # type: ignore[method-assign]  # FastAPI documents instance-level OpenAPI overrides.
