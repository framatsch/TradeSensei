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

"""Pydantic schema for annotation filter items used in list query APIs."""

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class AnnotationFilterItem(BaseModel):
    """A single annotation filter condition for list queries.

    Attributes:
        annotation_definition_id: UUID of the AnnotationDefinition to filter on.
        operator: Comparison operator. Allowed values depend on annotation type:
            bool: ``eq``
            string_enum: ``eq``, ``neq``
            int/float: ``eq``, ``neq``, ``lt``, ``lte``, ``gt``, ``gte``
        value: Filter value. Must match the annotation's underlying type.
        logic: ``"and"`` (default) combines with preceding filters via AND.
               ``"or"`` merges into an OR group with the previous filter.
               The first filter always uses AND regardless of this field.
    """

    annotation_definition_id: uuid.UUID = Field(
        ..., description="UUID of the AnnotationDefinition to filter on."
    )
    operator: str = Field(
        ..., description="Comparison operator: eq, neq, lt, lte, gt, gte."
    )
    value: int | float | bool | str = Field(
        ..., description="Filter value; must match the annotation's type."
    )
    logic: Literal["and", "or"] = Field(
        default="and",
        description="Logic connector: 'and' (default) or 'or'.",
    )
