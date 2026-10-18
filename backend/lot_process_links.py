"""Read-only manufacturing process relationship review; no genealogy assertions.

Grouping BA and CA on date+variant creates an assembly-set REVIEW candidate,
not an evidence-backed shared RUN or LOT consumption edge.
"""
from collections import defaultdict
from datetime import date
from lot_normalize import normalize_lot_value

QTY_METRICS = frozenset({'PRODUCTION_QTY', 'PRODUCTION_QTY_DAY', 'PRODUCTION_QTY_NIGHT'})
VARIANTS = frozenset({'IV', 'OV', 'HSV'})


def _date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def build_process_review(rows, lot_date, variant=None):
    """Return candidate assembly sets and stitching precedents; no verified edges.

    Multiple BA/CA records in the same date/variant are not collapsed into a
    single production run. Ambiguous variants are never treated as confirmed.
    """
    groups = defaultdict(lambda: {'BA': [], 'CA': []})
    stitching = []
    inserts = []
    for r in rows:
        v, process, metric = r.get('variant'), r.get('process'), r.get('metric')
        if v not in VARIANTS or (variant and v != variant):
            continue
        if process in {'BA', 'CA'} and metric in QTY_METRICS and _date(r.get('date')):
            groups[(r['date'], v)][process].append(r)
        if process == 'STITCHING' and metric in QTY_METRICS and _date(r.get('date')):
            stitching.append(r)
        if process == 'BA' and metric == 'LEAD_PIN_INSERT':
            inserts.append(r)

    assembly = []
    for (day, v), pair in sorted(groups.items()):
        if not (pair['BA'] and pair['CA']):
            continue
        assembly.append({
            'date': day, 'variant': v,
            'ba_records': [{'id': r.get('id'), 'quantity': r.get('value'), 'value_source': r.get('value_source')} for r in pair['BA']],
            'ca_records': [{'id': r.get('id'), 'quantity': r.get('value'), 'value_source': r.get('value_source')} for r in pair['CA']],
            'status': 'ASSEMBLY_SET_REVIEW',
            'reason': 'same date and variant only; same RUN not independently evidenced',
        })

    precedents = []
    for consumer in inserts:
        norm = normalize_lot_value(consumer.get('value'))
        consumed_dates = norm['normalized_dates']
        if not consumed_dates or not _date(consumer.get('date')):
            continue
        for upstream in stitching:
            if upstream['variant'] != consumer['variant']:
                continue
            if upstream['date'] not in consumed_dates:
                continue
            gap = (_date(consumer['date']) - _date(upstream['date'])).days
            if gap < 0:
                continue
            precedents.append({
                'insert_record_id': consumer.get('id'), 'insert_source_value': consumer.get('value'),
                'ba_date': consumer['date'], 'stitching_record_id': upstream.get('id'),
                'stitching_date': upstream['date'], 'variant': consumer['variant'],
                'days_before_ba': gap, 'lot_interpretation': norm['normalization_status'],
                'status': 'INSERT_DATE_STITCHING_CANDIDATE',
                'reason': 'Insert date and Stitching production date align; material genealogy unverified',
            })
    return {'assembly_sets': assembly, 'stitching_candidates': precedents, 'verified_edges': []}


def display_quantities(records):
    """Deduplicate display values only, never source records or production RUNs.

    Repeated values are not summed. Different quantities remain visible and
    require separate RUN/evidence review.
    """
    distinct = []
    for r in records:
        raw = r.get('quantity')
        key = str(raw).strip().replace(',', '')
        if key not in [k for k, _ in distinct]:
            distinct.append((key, raw))
    return ', '.join(str(raw) for _, raw in distinct) or 'BLANK'
