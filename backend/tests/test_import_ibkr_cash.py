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

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models.cash_transaction import CashTransactionType
from app.utils.parsers.ibkr_xml import IBKRXMLParser


class TestIBKRXMLCashTransactionParsing:
    """Tests for IBKR Flex XML cash transaction parsing and CASH trade filtering."""

    @pytest.mark.unit
    def test_filter_cash_trade_extracts_fee(self) -> None:
        """<Trade assetCategory="CASH"> extracts commission as FEE."""
        xml = """<FlexQueryResponse>
            <FlexStatements>
                <FlexStatement>
                    <Trades>
                        <Trade assetCategory="CASH" symbol="EUR.USD" 
                               tradeDate="20240315" dateTime="20240315;093000" 
                               quantity="-1000" tradePrice="1.08" 
                               commission="-2.50" currency="USD" />
                    </Trades>
                </FlexStatement>
            </FlexStatements>
        </FlexQueryResponse>"""

        parser = IBKRXMLParser()
        trades, cash_txs = parser.parse(xml.encode("utf-8"), "activity.xml")

        # Should not be in trades list
        assert len(trades) == 0

        # Commission should be in cash_transactions as FEE
        assert len(cash_txs) == 1
        assert cash_txs[0].type == CashTransactionType.FEE
        assert cash_txs[0].amount == Decimal("-2.50")
        assert cash_txs[0].currency == "USD"
        assert "FX Conversion" in (cash_txs[0].description or "")

    @pytest.mark.unit
    def test_filter_cash_trade_extracts_ibkr_commission(self) -> None:
        """<Trade assetCategory="CASH"> supports ibCommission attribute."""
        xml = """<FlexQueryResponse>
            <FlexStatements>
                <FlexStatement>
                    <Trades>
                        <Trade assetCategory="CASH" symbol="EUR.USD" 
                               tradeDate="20240315" dateTime="20240315;093000" 
                               quantity="-1000" tradePrice="1.08" 
                               ibCommission="-2.50" currency="USD" />
                    </Trades>
                </FlexStatement>
            </FlexStatements>
        </FlexQueryResponse>"""

        parser = IBKRXMLParser()
        trades, cash_txs = parser.parse(xml.encode("utf-8"), "activity.xml")

        assert len(trades) == 0
        assert len(cash_txs) == 1
        assert cash_txs[0].amount == Decimal("-2.50")

    @pytest.mark.unit
    def test_parse_trade_extracts_ibkr_commission(self) -> None:
        """Regular <Trade> supports ibCommission attribute."""
        xml = """<FlexQueryResponse>
            <FlexStatements>
                <FlexStatement>
                    <Trades>
                        <Trade assetCategory="STK" symbol="AAPL" 
                               tradeDate="20240315" dateTime="20240315;093000" 
                               quantity="10" tradePrice="150.00" 
                               ibCommission="-1.00" currency="USD" />
                    </Trades>
                </FlexStatement>
            </FlexStatements>
        </FlexQueryResponse>"""

        parser = IBKRXMLParser()
        trades, _ = parser.parse(xml.encode("utf-8"), "activity.xml")

        assert len(trades) == 1
        assert trades[0].commission == Decimal("1.00")

    @pytest.mark.unit
    def test_parse_cash_transaction_dividend(self) -> None:
        """<CashTransaction type="Dividends"> should be parsed correctly."""
        xml = """<FlexQueryResponse>
            <FlexStatements>
                <FlexStatement>
                    <CashTransactions>
                        <CashTransaction type="Dividends" symbol="AAPL" 
                                         reportDate="20240315" 
                                         dateTime="20240315;093000" 
                                         amount="15.50" currency="USD" 
                                         description="Dividend Payment" />
                    </CashTransactions>
                </FlexStatement>
            </FlexStatements>
        </FlexQueryResponse>"""

        parser = IBKRXMLParser()
        trades, cash_txs = parser.parse(xml.encode("utf-8"), "activity.xml")

        assert len(cash_txs) == 1
        assert cash_txs[0].type == CashTransactionType.DIVIDEND
        assert cash_txs[0].amount == Decimal("15.50")
        assert cash_txs[0].symbol == "AAPL"
        assert cash_txs[0].date == datetime(2024, 3, 15, 9, 30, 0, tzinfo=UTC)

    @pytest.mark.unit
    def test_parse_cash_transaction_withholding_tax(self) -> None:
        """<CashTransaction type="Withholding Tax"> should be parsed."""
        xml = """<FlexQueryResponse>
            <FlexStatements>
                <FlexStatement>
                    <CashTransactions>
                        <CashTransaction type="Withholding Tax" symbol="AAPL" 
                                         reportDate="20240315" 
                                         dateTime="20240315;093000" 
                                         amount="-2.30" currency="USD" />
                    </CashTransactions>
                </FlexStatement>
            </FlexStatements>
        </FlexQueryResponse>"""

        parser = IBKRXMLParser()
        trades, cash_txs = parser.parse(xml.encode("utf-8"), "activity.xml")

        assert len(cash_txs) == 1
        assert cash_txs[0].type == CashTransactionType.WITHHOLDING_TAX
        assert cash_txs[0].amount == Decimal("-2.30")

    @pytest.mark.unit
    def test_parse_cash_transaction_deposit(self) -> None:
        """<CashTransaction type="Deposits/Withdrawals"> is DEPOSIT."""
        xml = """<FlexQueryResponse>
            <FlexStatements>
                <FlexStatement>
                    <CashTransactions>
                        <CashTransaction type="Deposits/Withdrawals" 
                                         reportDate="20240315" 
                                         dateTime="20240315;093000" 
                                         amount="1000.00" currency="USD" />
                    </CashTransactions>
                </FlexStatement>
            </FlexStatements>
        </FlexQueryResponse>"""

        parser = IBKRXMLParser()
        trades, cash_txs = parser.parse(xml.encode("utf-8"), "activity.xml")

        assert len(cash_txs) == 1
        assert cash_txs[0].type == CashTransactionType.DEPOSIT
        assert cash_txs[0].amount == Decimal("1000.00")

    @pytest.mark.unit
    def test_parse_cash_transaction_withdrawal(self) -> None:
        """<CashTransaction type="Deposits/Withdrawals"> is WITHDRAWAL."""
        xml = """<FlexQueryResponse>
            <FlexStatements>
                <FlexStatement>
                    <CashTransactions>
                        <CashTransaction type="Deposits/Withdrawals" 
                                         reportDate="20240315" 
                                         dateTime="20240315;093000" 
                                         amount="-500.00" currency="USD" />
                    </CashTransactions>
                </FlexStatement>
            </FlexStatements>
        </FlexQueryResponse>"""

        parser = IBKRXMLParser()
        trades, cash_txs = parser.parse(xml.encode("utf-8"), "activity.xml")

        assert len(cash_txs) == 1
        assert cash_txs[0].type == CashTransactionType.WITHDRAWAL
        assert cash_txs[0].amount == Decimal("-500.00")
