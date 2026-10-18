"""iMEB3 LOT date lookup from supplied 'IMEB3 조견표.xlsx'.
Pure lookup: never modifies Firestore, source records or verified values.
"""
from datetime import date
import re

YEAR_CODES = dict(zip('UVWXYZABCDEF', range(2021, 2033)))
MONTH_CODES = dict(zip('ABCDEFGHIJKL', range(1, 13)))
DAY_CODES = dict(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ23456', range(1, 32)))


def lot_to_date(code: str) -> str | None:
    """Return ISO date for a complete 3-character iMEB3 LOT date code."""
    code = code.strip().upper()
    if len(code) != 3:
        return None
    y = YEAR_CODES.get(code[0]); m = MONTH_CODES.get(code[1]); d = DAY_CODES.get(code[2])
    if y is None or m is None or d is None:
        return None
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def find_lot_date(text: str) -> dict | None:
    """Detect a standalone 3-character LOT token; preserve original source text."""
    for match in re.finditer(r'(?<![A-Za-z0-9])([A-Za-z0-9]{3})(?![A-Za-z0-9])', text):
        code = match.group(1)
        converted = lot_to_date(code)
        if converted:
            return {'source_value': code, 'date': converted, 'value_source': 'DERIVED',
                    'rule': 'IMEB3 LOT NO 조견표', 'lookup_status': 'MATCHED'}
    return None
