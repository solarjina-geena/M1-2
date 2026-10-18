"""Read-only manufacturing genealogy candidates, never verified genealogy edges.

No database writes. Explicit LOT consumption and production chronology are different
classes of evidence. A date match alone never creates a genealogy edge.
"""
from datetime import date
from lot_normalize import find_lot_evidence

LOT_ROLE_PROCESS = {
    'BOBBIN_LOT': 'BOBBIN',
    'LEAD_PIN_LOT': 'LEAD_PIN',
    'LEAD_PIN_INSERT': 'STITCHING',
    'RAW_MATERIAL_LOT': 'RAW_MATERIAL',
    'RAW_LOT_DAY': 'RAW_MATERIAL',
    'RAW_LOT_NIGHT': 'RAW_MATERIAL',
    'UPPER_CASE_LOT': 'UPPER_CASE',
    'LOWER_CASE_LOT': 'LOWER_CASE',
}


def _known_variant(value):
    """Ambiguous labels such as 'HSV→OV' must never be silently assigned."""
    return value if value in {'IV', 'OV', 'HSV'} else None


def build_genealogy_candidates(rows, lot_date, variant=None):
    """Return role-specific consumers and *unverified* chronological candidates.

    Source record IDs are preserved, not replaced by date-derived RUN IDs.
    A source manufacturing event without explicit output LOT cannot be an edge.
    """
    consumers = []
    for item in find_lot_evidence(rows, lot_date, variant):
        r = item['record']
        consumers.append({
            'record_id': r.get('id'), 'date': r.get('date'),
            'variant': r.get('variant'), 'process': r.get('process'),
            'lot_role': item['lot_role'], 'raw_lot': r.get('value'),
            'lot_interpretation': item['normalization']['normalization_status'],
            'provenance': r.get('value_source') or r.get('provenance'),
            'source': r.get('source'), 'link_status': 'LOT_REFERENCE_ONLY',
        })
    # Only unambiguous variants and chronologically possible production events.
    # No links, not even CANDIDATE_EDGE, are generated from these alone.
    candidates = []
    seen = set()
    for consumer in consumers:
        cv = _known_variant(consumer['variant'])
        role = consumer['lot_role']
        upstream = LOT_ROLE_PROCESS.get(role)
        if not cv or not upstream or not consumer['date']:
            continue
        # STITCHING production could be relevant to INSERT, but a date alone
        # cannot prove which bobbin/lead pin it used.
        if upstream != 'STITCHING':
            continue
        for r in rows:
            if r.get('process') != 'STITCHING':
                continue
            if _known_variant(r.get('variant')) != cv:
                continue
            if r.get('metric') not in {'PRODUCTION_QTY', 'PRODUCTION_QTY_DAY', 'PRODUCTION_QTY_NIGHT'}:
                continue
            try:
                days = (date.fromisoformat(consumer['date']) - date.fromisoformat(r['date'])).days
            except (TypeError, ValueError, KeyError):
                continue
            if not (0 <= days <= 90):
                continue
            key = (consumer['record_id'], r.get('id'), r.get('date'), r.get('metric'))
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                'consumer_record_id': consumer['record_id'],
                'possible_upstream_record_id': r.get('id'),
                'possible_upstream_date': r['date'],
                'possible_upstream_process': r['process'],
                'variant': cv, 'days_before_consumption': days,
                'link_status': 'CHRONOLOGY_ONLY_UNVERIFIED',
                'reason': 'variant and chronology only; no source/consumption LOT identity',
            })
    return {'lot_date': lot_date, 'consumers': consumers,
            'chronology_candidates': candidates, 'verified_edges': []}
