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

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import Boolean, Column, Float, Integer, String, Uuid, select
from sqlalchemy.orm import declarative_base

from app.repositories._annotation_filter import _column_and_value, _operator_expr, apply_annotation_filters
from app.schemas.annotation_filter import AnnotationFilterItem

Base = declarative_base()

class MockAnnotation(Base):
    __tablename__ = 'mock_annotation'
    id = Column(Integer, primary_key=True)
    value_bool = Column(Boolean)
    value_int = Column(Integer)
    value_float = Column(Float)
    value_string = Column(String)
    annotation_definition_id = Column(Uuid)
    parent_id = Column(Uuid)

class MockParent(Base):
    __tablename__ = 'mock_parent'
    id = Column(Uuid, primary_key=True)

@pytest.mark.unit
def test_column_and_value_mapping():
    # Bool
    col, val = _column_and_value(MockAnnotation, "eq", True)
    assert col == MockAnnotation.value_bool
    assert val is True
    
    with pytest.raises(ValueError, match="bool annotation filters support only 'eq' operator"):
        _column_and_value(MockAnnotation, "gt", True)

    # Int
    col, val = _column_and_value(MockAnnotation, "gte", 10)
    assert col == MockAnnotation.value_int
    assert val == 10

    # Float -> Decimal
    col, val = _column_and_value(MockAnnotation, "lt", 10.5)
    assert col == MockAnnotation.value_float
    assert isinstance(val, Decimal)
    assert val == Decimal("10.5")

    # String
    col, val = _column_and_value(MockAnnotation, "eq", "test")
    assert col == MockAnnotation.value_string
    assert val == "test"
    
    col, val = _column_and_value(MockAnnotation, "neq", "other")
    assert col == MockAnnotation.value_string
    assert val == "other"

    with pytest.raises(ValueError, match="string annotation filters support only 'eq' or 'neq' operators"):
        _column_and_value(MockAnnotation, "gt", "test")

    # Unsupported
    with pytest.raises(ValueError, match="Unsupported annotation filter value type"):
        _column_and_value(MockAnnotation, "eq", None)

@pytest.mark.unit
def test_operator_expressions():
    col = MockAnnotation.value_int
    
    assert str(_operator_expr("eq", col, 10)) == "mock_annotation.value_int = :value_int_1"
    assert str(_operator_expr("neq", col, 10)) == "mock_annotation.value_int != :value_int_1"
    assert str(_operator_expr("lt", col, 10)) == "mock_annotation.value_int < :value_int_1"
    assert str(_operator_expr("lte", col, 10)) == "mock_annotation.value_int <= :value_int_1"
    assert str(_operator_expr("gt", col, 10)) == "mock_annotation.value_int > :value_int_1"
    assert str(_operator_expr("gte", col, 10)) == "mock_annotation.value_int >= :value_int_1"

    with pytest.raises(ValueError, match="Unsupported annotation filter operator: invalid"):
        _operator_expr("invalid", col, 10)

@pytest.mark.unit
def test_apply_annotation_filters_chaining_logic():
    user_id = uuid.uuid4()
    def_1 = uuid.uuid4()
    def_2 = uuid.uuid4()
    def_3 = uuid.uuid4()

    # (A OR B) AND C
    filters = [
        AnnotationFilterItem(annotation_definition_id=def_1, operator="eq", value="A", logic="and"),
        AnnotationFilterItem(annotation_definition_id=def_2, operator="eq", value="B", logic="or"),
        AnnotationFilterItem(annotation_definition_id=def_3, operator="eq", value="C", logic="and"),
    ]

    stmt = select(MockParent)
    stmt = apply_annotation_filters(
        stmt, 
        MockAnnotation, 
        MockAnnotation.parent_id, 
        MockParent.id, 
        user_id, 
        filters
    )

    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    
    # Check for OR grouping
    assert "value_string = 'A'" in sql
    assert "value_string = 'B'" in sql
    assert "value_string = 'C'" in sql
    assert "OR" in sql
    assert sql.count("EXISTS") == 3

@pytest.mark.unit
def test_apply_annotation_filters_empty():
    stmt = select(MockParent)
    result = apply_annotation_filters(stmt, MockAnnotation, MockAnnotation.parent_id, MockParent.id, uuid.uuid4(), [])
    assert result is stmt
