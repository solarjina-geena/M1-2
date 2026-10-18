"""Read-only provenance/RUN review. IDs are references, not inferred manufacturing RUNs."""
from collections import defaultdict

VALID_VARIANTS = {'IV', 'OV', 'HSV'}
QTY = {'PRODUCTION_QTY', 'PRODUCTION_QTY_DAY', 'PRODUCTION_QTY_NIGHT'}

def evidence_ref(row):
    source = row.get('source')
    source = source if isinstance(source, dict) else {}
    return {
        'record_id': row.get('id'),
        'document': source.get('file') or None,
        'page': source.get('page') if source.get('page') is not None else None,
        'metric': row.get('metric'),
        'source_value': row.get('value'),
        'provenance': row.get('value_source') or row.get('provenance') or 'UNCERTAIN',
        'document_page_verified': bool(source.get('file') and source.get('page') is not None and str(source.get('file')).lower().endswith(('.pdf', '.png', '.jpg', '.jpeg'))),
    }

def run_review(rows, dates_variants):
    """Return record-level evidence grouped by day/variant, never synthesize a RUN ID."""
    wanted = set(dates_variants)
    groups = defaultdict(lambda: {'BA': [], 'CA': [], 'STITCHING': []})
    for r in rows:
        key = (r.get('date'), r.get('variant'))
        if key not in wanted or r.get('variant') not in VALID_VARIANTS:
            continue
        if r.get('process') in groups[key] and r.get('metric') in QTY:
            groups[key][r['process']].append(evidence_ref(r))
    result = []
    for (day, variant), by_process in sorted(groups.items()):
        evidence = [e for records in by_process.values() for e in records]
        result.append({
            'date': day, 'variant': variant, 'run_id': None,
            'status': 'RUN_UNRESOLVED',
            'by_process': by_process,
            'source_record_count': len(evidence),
            'document_page_evidence_count': sum(e['document_page_verified'] for e in evidence),
            'reason': 'Date and variant do not establish a unique manufacturing RUN; original document/page and equipment/time evidence required',
        })
    return result
