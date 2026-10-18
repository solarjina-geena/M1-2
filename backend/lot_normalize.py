"""Read-only LOT evidence normalization. No Firestore writes or genealogy inference."""
import re
from datetime import date
from lot_lookup import lot_to_date

LOT_METRICS = frozenset({
    'BOBBIN_LOT', 'BOBBIN_LOT_RAW', 'BOBBIN_PRODUCTION_DATE', 'LEAD_PIN_RECEIPT_DATE', 'LEAD_PIN_LOT', 'LEAD_PIN_INSERT', 'RAW_MATERIAL_LOT',
    'RAW_LOT_DAY', 'RAW_LOT_NIGHT', 'UPPER_CASE_LOT', 'LOWER_CASE_LOT', 'WIRE_LOT', 'LOT'
})


def normalize_lot_value(value, *, reference_year=2026):
    """Return interpreted dates and uncertainty without changing original evidence.

    A standalone, complete LOT code or date is accepted. A value with a
    qualifier such as '로 판독' or '추정' is searchable but flagged UNCERTAIN.
    Multi-value and unrecognized fields are not silently interpreted.
    """
    result = {'source_value': value, 'normalized_dates': [],
              'normalization_status': 'UNRESOLVED', 'value_source': 'DERIVED'}
    if not isinstance(value, str) or not value.strip():
        return result
    s = value.strip()
    if re.search(r"\s/\s", s):
        parts = [normalize_lot_value(part, reference_year=reference_year) for part in re.split(r"\s+/\s+", s)]
        dates = list(dict.fromkeys(day for part in parts for day in part["normalized_dates"]))
        if dates:
            result["normalized_dates"] = dates
            result["normalization_status"] = "UNCERTAIN" if any(part["normalization_status"] == "UNCERTAIN" for part in parts) else "MATCHED"
        return result
    uncertain = bool(re.search(r'추정|판독|미확인|불명|예상|\?', s))
    cleaned = re.sub(r'\s*(?:로\s*판독|추정|미확인|불명|예상)\s*$', '', s).strip()
    parsed = lot_to_date(cleaned) if re.fullmatch(r'[A-Za-z0-9]{3}', cleaned) else None
    if not parsed:
        m = re.fullmatch(r'(20\d{2})[./-](\d{1,2})[./-](\d{1,2})', cleaned)
        if m:
            parts = tuple(map(int, m.groups()))
        else:
            m = re.fullmatch(r'(\d{1,2})[./-](\d{1,2})', cleaned)
            parts = (reference_year, *map(int, m.groups())) if m else None
        if parts:
            try:
                parsed = date(*parts).isoformat()
            except ValueError:
                parsed = None
    if parsed:
        result['normalized_dates'] = [parsed]
        result['normalization_status'] = 'UNCERTAIN' if uncertain else 'MATCHED'
    return result


def find_lot_evidence(rows, lot_date, variant=None):
    """Find role-specific LOT evidence by normalized date; do not alter rows."""
    matches = []
    for r in rows:
        if variant and r.get('variant') != variant:
            continue
        role = str(r.get('metric', '')).upper()
        if role not in LOT_METRICS:
            continue
        norm = normalize_lot_value(r.get('value'))
        if lot_date in norm['normalized_dates']:
            matches.append({'record': r, 'lot_role': role, 'normalization': norm})
    return matches

