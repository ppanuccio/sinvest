"""Tests for the Excel statement parser."""

from datetime import datetime
from decimal import Decimal

import pytest
from openpyxl import Workbook

from app.infrastructure.excel_statement_parser import (
    StatementParseError,
    parse_statement_workbook,
)


def build_statement_bytes(rows):
    """Build a workbook with the movement-statement header and given rows."""
    wb = Workbook()
    ws = wb.active
    ws.append(["Dossier n.: 5745921"])
    ws.append(
        [
            "Operazione",
            "Data valuta",
            "Descrizione",
            "Titolo",
            "Isin",
            "Segno",
            "Quantita",
            "Divisa",
            "Prezzo",
            "Cambio",
            "Controvalore",
            None,
            None,
            None,
            "Commissioni amministrato",
        ]
    )
    for row in rows:
        ws.append(row)
    from io import BytesIO

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


class TestParseStatementWorkbook:
    """Test parsing bank statement exports."""

    def test_parses_buys_coupons_and_fees(self):
        data = build_statement_bytes(
            [
                # Buy with a 19 EUR admin fee: amount becomes controvalore + fee.
                (
                    "22/04/2025",
                    "24/04/2025",
                    "Compravendita titoli",
                    "IBRD-17NV28 3%",
                    "XS2702860896",
                    "A",
                    5000,
                    "EUR",
                    105.2191,
                    1,
                    5260.95,
                    None,
                    None,
                    None,
                    19,
                ),
                # Buy without fees.
                (
                    "14/04/2025",
                    "16/04/2025",
                    "Compravendita titoli",
                    "XTR2 EUR OR SW 1CC",
                    "LU0290358497",
                    "A",
                    30,
                    "EUR",
                    145.9582,
                    1,
                    4378.75,
                    None,
                    None,
                    None,
                    None,
                ),
                # Coupon: kind coupon, controvalore only, no fee added.
                (
                    "18/08/2025",
                    "18/08/2025",
                    "Stacco Cedole",
                    "**IBRD-17NV28 3%",
                    "XS2702860896",
                    " ",
                    39000,
                    "EUR",
                    0,
                    1,
                    273,
                    None,
                    None,
                    None,
                    None,
                ),
                # Sell: reported as unsupported, not parsed.
                (
                    "20/08/2025",
                    "20/08/2025",
                    "Compravendita titoli",
                    "IBRD-17NV28 3%",
                    "XS2702860896",
                    "V",
                    1000,
                    "EUR",
                    106.0,
                    1,
                    1060,
                    None,
                    None,
                    None,
                    None,
                ),
            ]
        )

        rows, skipped = parse_statement_workbook(data)

        assert len(rows) == 3
        assert skipped == 1

        buy_with_fee = rows[0]
        assert buy_with_fee.identifier == "XS2702860896"
        assert buy_with_fee.kind == "buy"
        assert buy_with_fee.date == datetime(2025, 4, 22)
        assert buy_with_fee.quantity == Decimal("5000")
        assert buy_with_fee.amount == Decimal("5279.95")

        buy_plain = rows[1]
        assert buy_plain.amount == Decimal("4378.75")

        coupon = rows[2]
        assert coupon.kind == "coupon"
        assert coupon.amount == Decimal("273")
        assert coupon.title == "IBRD-17NV28 3%"  # leading ** stripped

    def test_rejects_unrecognized_workbook(self):
        wb = Workbook()
        wb.active.append(["Just", "some", "data"])
        from io import BytesIO

        buffer = BytesIO()
        wb.save(buffer)
        with pytest.raises(StatementParseError):
            parse_statement_workbook(buffer.getvalue())

    def test_rejects_non_excel_bytes(self):
        with pytest.raises(StatementParseError):
            parse_statement_workbook(b"not an excel file")
