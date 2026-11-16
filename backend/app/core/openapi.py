# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
