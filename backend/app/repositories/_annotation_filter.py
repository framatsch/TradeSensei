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

"""Shared annotation filter utilities for repository-layer SELECT queries.

Supports building EXISTS subquery conditions for both Trade and Checkin
annotation assignment tables with per-filter AND/OR logic chaining.
"""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import exists, or_, select
from sqlalchemy.sql.selectable import Select

from app.models.annotation_definition import AnnotationDefinition
from app.schemas.annotation_filter import AnnotationFilterItem


def _column_and_value(
    annotation_cls: Any,
    operator: str,
    value: int | float | bool | str,
) -> tuple[Any, Any]:
    """Map a Python filter value to the correct ORM column and typed value.

    Args:
        annotation_cls: Either TradeAnnotation or CheckinAnnotation ORM class.
        operator: Comparison operator string.
        value: Raw filter value.

    Returns:
        Tuple of (column_attribute, typed_value) for use in an operator expression.

    Raises:
        ValueError: If the value type does not match allowed operators.
    """
    if isinstance(value, bool):
        if operator != "eq":
            raise ValueError("bool annotation filters support only 'eq' operator")
        return annotation_cls.value_bool, value

    if isinstance(value, int):
        return annotation_cls.value_int, value

    if isinstance(value, float):
        return annotation_cls.value_float, Decimal(str(value))

    if isinstance(value, str):
        if operator not in ("eq", "neq"):
            raise ValueError("string annotation filters support only 'eq' or 'neq' operators")
        return annotation_cls.value_string, value

    raise ValueError("Unsupported annotation filter value type")


def _operator_expr(operator: str, column: Any, value: Any) -> Any:
    """Build a SQLAlchemy comparison expression from an operator string.

    Args:
        operator: Operator name (``eq``, ``neq``, ``lt``, ``lte``, ``gt``, ``gte``).
        column: SQLAlchemy column attribute.
        value: Typed value to compare against.

    Returns:
        SQLAlchemy binary expression.

    Raises:
        ValueError: If the operator is not recognised.
    """
    if operator == "eq":
        return column == value
    if operator == "neq":
        return column != value
    if operator == "lt":
        return column < value
    if operator == "gt":
        return column > value
    if operator == "lte":
        return column <= value
    if operator == "gte":
        return column >= value
    raise ValueError(f"Unsupported annotation filter operator: {operator}")


def build_annotation_exists(
    annotation_cls: Any,
    fk_col: Any,
    parent_id_col: Any,
    user_id: uuid.UUID,
    item: AnnotationFilterItem,
) -> Any:
    """Build a single EXISTS subquery for one annotation filter item.

    Args:
        annotation_cls: ORM class (TradeAnnotation or CheckinAnnotation).
        fk_col: FK column on annotation_cls pointing to the parent entity
            (e.g. ``CheckinAnnotation.checkin_id``).
        parent_id_col: Parent entity PK column (e.g. ``DailyCheckin.id``).
        user_id: Owning user UUID — restricts to user's annotation definitions.
        item: The filter item to evaluate.

    Returns:
        A SQLAlchemy ``exists()`` expression.
    """
    column, typed_value = _column_and_value(annotation_cls, item.operator, item.value)
    condition = _operator_expr(item.operator, column, typed_value)

    return exists(
        select(1)
        .select_from(annotation_cls)
        .join(AnnotationDefinition, annotation_cls.annotation_definition_id == AnnotationDefinition.id)
        .where(
            fk_col == parent_id_col,
            AnnotationDefinition.user_id == user_id,
            AnnotationDefinition.is_archived.is_(False),
            annotation_cls.annotation_definition_id == item.annotation_definition_id,
            condition,
        )
    )


def apply_annotation_filters(
    stmt: Select[Any],
    annotation_cls: Any,
    fk_col: Any,
    parent_id_col: Any,
    user_id: uuid.UUID,
    annotation_filters: list[AnnotationFilterItem],
) -> Select[Any]:
    """Apply annotation filters to a SELECT statement with AND/OR chaining.

    The first filter always uses AND. Subsequent filters with ``logic="or"``
    are combined into an OR group with the previous filter; ``logic="and"``
    starts a new AND group.

    Example with three filters A (and), B (or), C (and):
    ``WHERE (A OR B) AND C``

    Args:
        stmt: Base SELECT statement to augment.
        annotation_cls: Annotation ORM class (TradeAnnotation or CheckinAnnotation).
        fk_col: FK column on annotation_cls (e.g., ``CheckinAnnotation.checkin_id``).
        parent_id_col: Parent entity PK column (e.g., ``DailyCheckin.id``).
        user_id: Owning user UUID.
        annotation_filters: List of AnnotationFilterItem to apply.

    Returns:
        Augmented SELECT with annotation filter WHERE clauses applied.
    """
    if not annotation_filters:
        return stmt

    # Build OR groups: collect consecutive OR-logic filters into groups.
    # Each AND-logic filter (or the first filter) starts a new group.
    groups: list[list[Any]] = []
    current_group: list[Any] = []

    for item in annotation_filters:
        exists_expr = build_annotation_exists(annotation_cls, fk_col, parent_id_col, user_id, item)
        if item.logic == "or" and current_group:
            current_group.append(exists_expr)
        else:
            if current_group:
                groups.append(current_group)
            current_group = [exists_expr]

    if current_group:
        groups.append(current_group)

    # Each group is an OR chain; groups are ANDed together at WHERE level.
    for group in groups:
        stmt = stmt.where(group[0]) if len(group) == 1 else stmt.where(or_(*group))

    return stmt
