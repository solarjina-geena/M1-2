from lot_normalize import normalize_lot_value, find_lot_evidence
from lot_trace import trace_lot

cases = {
    'ZID': ('2026-09-04', 'MATCHED'),
    '9.3': ('2026-09-03', 'MATCHED'),
    '9/7': ('2026-09-07', 'MATCHED'),
    '8/24로 판독': ('2026-08-24', 'UNCERTAIN'),
    '2026-08-13 추정': ('2026-08-13', 'UNCERTAIN'),
    'ZI6': (None, 'UNRESOLVED'),
    '9/31': (None, 'UNRESOLVED'),
}
for value, (expected, status) in cases.items():
    actual = normalize_lot_value(value)
    assert actual['normalized_dates'] == ([expected] if expected else []), (value, actual)
    assert actual['normalization_status'] == status, (value, actual)
    assert actual['source_value'] == value
    print('PASS', repr(value), actual['normalized_dates'], status)
rows = [
    {'date':'2026-09-10','variant':'IV','process':'BA','metric':'BOBBIN_LOT','value':'9.3','value_source':'HUMAN_VERIFIED'},
    {'date':'2026-09-10','variant':'IV','process':'BA','metric':'LEAD_PIN_LOT','value':'9.8'},
    {'date':'2026-09-03','variant':'IV','process':'BA','metric':'PRODUCTION_QTY','value':123},
    {'date':'2026-09-10','variant':'OV','process':'BA','metric':'BOBBIN_LOT','value':'9.3'},
]
assert len(find_lot_evidence(rows,'2026-09-03','IV')) == 1
assert len(find_lot_evidence(rows,'2026-09-03')) == 2
assert 'LOT 필드 정규화 일치 (소비·공급 관계 미확정): 1건' in trace_lot(rows,'ZIC','2026-09-03','IV')
assert rows[0]['value'] == '9.3' and rows[0]['value_source'] == 'HUMAN_VERIFIED'
print('PASS role, variant, no date-based false linkage, source preservation')
