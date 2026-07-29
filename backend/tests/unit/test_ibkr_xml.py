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

from decimal import Decimal

import pytest

from app.core.exceptions import ImportParseError
from app.utils.parsers.ibkr_xml import (
    IBKRXMLParser,
    _extract_occ_underlying,
    _parse_execution_datetime,
    _safe_decimal,
)


def test_extract_occ_underlying():
    assert _extract_occ_underlying("AAPL") == "AAPL"
    assert _extract_occ_underlying("AAPL  230120C00150000") == "AAPL"
    # Not digit strike
    assert _extract_occ_underlying("AAPL  230120CX0150000") == "AAPL  230120CX0150000"

def test_parse_execution_datetime_value_error():
    with pytest.raises(ValueError):
        _parse_execution_datetime("bad", "")

def test_safe_decimal_invalid():
    assert _safe_decimal("bad", Decimal("-1")) == Decimal("-1")

def test_parser_xml_decode_error():
    parser = IBKRXMLParser()
    with pytest.raises(ImportParseError, match="not valid UTF-8"):
        parser._parse_xml(b"\xff\xff")
    with pytest.raises(ImportParseError, match="Invalid IBKR Flex XML"):
        parser._parse_xml(b"<bad")

def test_parse_raw_corporate_actions():
    xml = b"""
    <FlexQueryResponse>
        <CorporateAction actionID="1" type="RS" quantity="-10" conid="123" />
        <CorporateAction actionID="1" type="RS" quantity="1" conid="456" symbol="AAPL" dateTime="20230101" />
        <CorporateAction actionID="2" type="RS" quantity="-10" conid="123" />
        <CorporateAction actionID="3" type="FS" quantity="-10" conid="123" />
        <CorporateAction actionID="3" type="FS" quantity="bad" conid="456" />
        <CorporateAction actionID="4" type="RS" quantity="10" conid="123" symbol="AAPL" dateTime="20230101;100000" />
        <CorporateAction actionID="4" type="RS" quantity="-1" conid="456" />
        <CorporateAction actionID="5" type="RS" quantity="10" conid="123" symbol="AAPL" dateTime="bad" />
        <CorporateAction actionID="5" type="RS" quantity="-1" conid="456" />
    </FlexQueryResponse>
    """
    parser = IBKRXMLParser()
    raw, ca = parser.parse_raw(xml, "test.xml")
    assert len(ca) == 2
    assert ca[0].ratio == Decimal("0.1")
    assert ca[1].ratio == Decimal("10")

def test_parse_trade_element_raw_skipped():
    xml = b"""
    <FlexQueryResponse>
        <Trade assetCategory="STK" />
        <Trade assetCategory="STK" symbol="AAPL" />
        <Trade assetCategory="STK" symbol="AAPL" tradeDate="20230101" quantity="0" />
        <Trade assetCategory="STK" symbol="AAPL" tradeDate="20230101" quantity="10" tradePrice="-1" />
        <Trade assetCategory="STK" symbol="AAPL" tradeDate="20230101" quantity="10" tradePrice="0" transactionType="Trade" tradeMoney="-100" />
        <Trade assetCategory="STK" symbol="AAPL" tradeDate="20230101" quantity="10" tradePrice="0" transactionType="Trade" cost="-100" />
        <Trade assetCategory="STK" symbol="AAPL" tradeDate="bad" quantity="10" tradePrice="1" />
        <Trade assetCategory="OPT" symbol="AAPL  230120C00150000" tradeDate="20230101" quantity="10" tradePrice="1" />
    </FlexQueryResponse>
    """
    parser = IBKRXMLParser()
    raw, _ = parser.parse_raw(xml, "test.xml")
    assert len(parser.warnings) > 0

def test_parse_execution_element_raw_skipped():
    xml = b"""
    <FlexQueryResponse>
        <Execution assetCategory="STK" />
        <Execution assetCategory="STK" symbol="AAPL" />
        <Execution assetCategory="STK" symbol="AAPL" execDate="20230101" quantity="0" />
        <Execution assetCategory="STK" symbol="AAPL" execDate="20230101" quantity="10" price="-1" />
        <Execution assetCategory="STK" symbol="AAPL" execDate="bad" quantity="10" price="1" />
        <Execution assetCategory="OPT" symbol="AAPL  230120C00150000" execDate="20230101" quantity="10" price="1" />
    </FlexQueryResponse>
    """
    parser = IBKRXMLParser()
    raw, _ = parser.parse_raw(xml, "test.xml")
    assert len(parser.warnings) > 0

def test_parse_trade_element_legacy():
    xml = b"""
    <FlexQueryResponse>
        <Trade assetCategory="STK" />
        <Trade assetCategory="STK" symbol="AAPL" />
        <Trade assetCategory="STK" symbol="AAPL" tradeDate="20230101" quantity="0" />
        <Trade assetCategory="STK" symbol="AAPL" tradeDate="20230101" quantity="10" tradePrice="-1" />
        <Trade assetCategory="STK" symbol="AAPL" tradeDate="bad" quantity="10" tradePrice="1" />
        <Trade assetCategory="STK" symbol="AAPL" tradeDate="20230101" quantity="10" tradePrice="0" transactionType="Trade" tradeMoney="-100" />
        <Trade assetCategory="STK" symbol="AAPL" tradeDate="20230101" quantity="10" tradePrice="0" transactionType="Trade" cost="-100" />
        <Trade assetCategory="OPT" symbol="AAPL  230120C00150000" tradeDate="20230101" quantity="10" tradePrice="1" />
    </FlexQueryResponse>
    """
    parser = IBKRXMLParser()
    trades, _ = parser.parse(xml, "test.xml")
    assert len(trades) > 0

def test_parse_execution_element_legacy():
    xml = b"""
    <FlexQueryResponse>
        <Execution assetCategory="STK" />
        <Execution assetCategory="STK" symbol="AAPL" />
        <Execution assetCategory="STK" symbol="AAPL" execDate="20230101" quantity="0" />
        <Execution assetCategory="STK" symbol="AAPL" execDate="20230101" quantity="10" price="-1" />
        <Execution assetCategory="STK" symbol="AAPL" execDate="bad" quantity="10" price="1" />
        <Execution assetCategory="OPT" symbol="AAPL  230120C00150000" execDate="20230101" quantity="10" price="1" />
    </FlexQueryResponse>
    """
    parser = IBKRXMLParser()
    trades, _ = parser.parse(xml, "test.xml")
    assert len(trades) > 0


