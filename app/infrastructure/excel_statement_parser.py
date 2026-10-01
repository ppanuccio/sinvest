"""Parser for bank statement exports (Excel) of security movements.

Reads the "RISULTATO RICERCA MOVIMENTI TITOLI" layout produced by Italian
online-banking exports (e.g. FINECO dossiers): a sheet with a header row
labelled ``Operazione / Data valuta / Descrizione / Titolo / Isin / Segno /
Quantita / Divisa / Prezzo / Cambio / Controvalore / ...`` followed by one
row per movement.

- ``Compravendita titoli`` rows become ``buy`` transactions; the amount is
  the controvalore plus any bank commissions found on the row.
- ``Stacco Cedole`` rows become ``coupon`` transactions (income).
- Sell rows (``Segno = 'V'``) are not representable in the domain yet and are
  reported back to the caller so the API can surface them.
"""

import io
import re
from datetime import datetime
from decimal import Decimal
from typing import List, Tuple

from openpyxl import load_workbook

from app.application.dto.import_dto import ImportedTransactionDTO


class StatementParseError(ValueError):
    """The workbook is not a recognizable statement of security movements."""


# Column headers we locate by name; the export pads/truncates them, so match
# on the first word pair (case-insensitive, accents/spaces ignored).
_COLUMN_MATCHERS = [
    ("date", re.compile(r"^operazione|^data\s*oper", re.I)),
    ("description", re.compile(r"^descrizione", re.I)),
    ("title", re.compile(r"^titolo", re.I)),
    ("isin", re.compile(r"^isin", re.I)),
    ("sign", re.compile(r"^segno", re.I)),
    ("quantity", re.compile(r"^quantita", re.I)),
    ("currency", re.compile(r"^divisa", re.I)),
    ("value", re.compile(r"^controvalore", re.I)),
    ("commission", re.compile(r"^commissioni", re.I)),
]

_DATE_PATTERN = re.compile(r"^(\d{2})/(\d{2})/(\d{4})")


def parse_statement_workbook(data: bytes) -> Tuple[List[ImportedTransactionDTO], int]:
    """Parse an Excel statement into import rows.

    Returns ``(rows, skipped_count)`` where skipped rows are movements the
    domain cannot represent (currently sells).
    """
    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as e:
        raise StatementParseError(f"Cannot read Excel file: {e}") from e

    rows: List[ImportedTransactionDTO] = []
    skipped = 0
    for sheet in workbook.worksheets:
        sheet_rows = list(sheet.iter_rows(values_only=True))
        columns, header_index = _find_header(sheet_rows)
        if columns is None:
            continue
        for raw in sheet_rows[header_index + 1:]:
            row = _parse_row(raw, columns)
            if row is None:
                continue
            if isinstance(row, str):  # sentinel for an unrepresentable row
                skipped += 1
            else:
                rows.append(row)
        break  # only the first recognizable sheet
    workbook.close()

    if not rows and skipped == 0:
        raise StatementParseError(
            "No security movements found. Expected a statement export with "
            "columns: Operazione, Titolo, Isin, Quantita, Divisa, Controvalore."
        )
    return rows, skipped


def _find_header(sheet_rows):
    """Locate the movement header row; returns (column_map, index) or (None, -1).

    ``column_map`` also carries a ``commissions`` entry: the list of positions
    of every commission/fee column found in the header (bank exports have
    several).
    """
    for index, raw in enumerate(sheet_rows):
        values = ["" if v is None else str(v) for v in raw]
        columns = {}
        commission_positions = []
        for position, value in enumerate(values):
            for name, pattern in _COLUMN_MATCHERS:
                if name == "commission":
                    if pattern.match(value.strip()):
                        commission_positions.append(position)
                elif name not in columns and pattern.match(value.strip()):
                    columns[name] = position
        required = ("title", "isin", "quantity", "currency", "value")
        if all(name in columns for name in required):
            columns["commissions"] = commission_positions
            return columns, index
    return None, -1


def _parse_row(raw, columns):
    """Convert one movement row, or None for blanks/headers, or 'skip' sentinel."""

    def cell(name):
        position = columns.get(name)
        return raw[position] if position is not None and position < len(raw) else None

    isin = cell("isin")
    description = cell("description") or ""
    if not isin or not str(isin).strip():
        return None

    sign = str(cell("sign") or "A").strip().upper()
    if sign == "V":  # sell: not representable yet
        return "skip"

    description_str = str(description).strip()
    if "CEDOLE" in description_str.upper():
        kind = "coupon"
    else:
        kind = "buy"

    # First cell is the operation date in the export's layout (header
    # "Operazione"); fall back to any dd/mm/yyyy-looking cell before it.
    date_value = cell("date")
    if (
        date_value is None
        or isinstance(date_value, str)
        and not _DATE_PATTERN.match(date_value.strip())
    ):
        date_value = next(
            (
                v
                for v in raw[: columns.get("description", 3)]
                if isinstance(v, str) and _DATE_PATTERN.match(v.strip())
            ),
            None,
        )
    if date_value is None:
        return None
    if isinstance(date_value, datetime):
        parsed_date = date_value
    else:
        match = _DATE_PATTERN.match(str(date_value).strip())
        if not match:
            return None
        day, month, year = match.groups()
        try:
            parsed_date = datetime(int(year), int(month), int(day))
        except ValueError:
            return None

    def decimal(name, default=None):
        value = cell(name)
        if value is None or value == "" or value == "-":
            return default
        try:
            return Decimal(str(value).replace(",", "."))
        except Exception:
            return default

    quantity = decimal("quantity")
    amount = decimal("value")
    currency = str(cell("currency") or "EUR").strip().upper()
    if quantity is None or quantity <= 0 or amount is None or amount <= 0:
        return None

    # Buys carry bank commissions on top of the controvalore.
    if kind == "buy":
        for position in columns.get("commissions", []):
            if position >= len(raw):
                continue
            fee_value = raw[position]
            if fee_value is None or fee_value == "" or fee_value == "-":
                continue
            try:
                amount += Decimal(str(fee_value).replace(",", "."))
            except Exception:
                continue

    title = str(cell("title") or isin).strip().lstrip("*")
    return ImportedTransactionDTO(
        identifier=str(isin).strip().upper(),
        title=title,
        kind=kind,
        date=parsed_date,
        quantity=quantity,
        amount=amount,
        currency=currency,
    )
