from lot_trace import trace_lot
from lot_process_links import display_quantities

assert display_quantities([{'quantity':33580},{'quantity':33580}]) == '33580'
assert display_quantities([{'quantity':33580},{'quantity':33581}]) == '33580, 33581'
rows = [
 {'id':'ba1','date':'2026-09-10','variant':'IV','process':'BA','metric':'PRODUCTION_QTY','value':33580},
 {'id':'ba2','date':'2026-09-10','variant':'IV','process':'BA','metric':'PRODUCTION_QTY','value':33580},
 {'id':'ca1','date':'2026-09-10','variant':'IV','process':'CA','metric':'PRODUCTION_QTY','value':2840},
 {'id':'ca2','date':'2026-09-10','variant':'IV','process':'CA','metric':'PRODUCTION_QTY','value':2840},
 {'id':'lot','date':'2026-09-10','variant':'IV','process':'BA','metric':'BOBBIN_LOT','value':'9.3','value_source':'HUMAN_VERIFIED'},
 {'id':'b3','date':'2026-09-03','variant':'OV','process':'BA','metric':'PRODUCTION_QTY','value':18782},
 {'id':'c3','date':'2026-09-03','variant':'OV','process':'CA','metric':'PRODUCTION_QTY','value':18712},
]
s = trace_lot(rows,'ZIC','2026-09-03')
assert 'LOT 필드 정규화 일치 (소비·공급 관계 미확정): 1건' in s, s
assert 'LOT 참조 공정의 BA·CA 검토 후보: 1건' in s, s
assert 'LOT 변환일 참고 생산의 BA·CA 검토 후보: 1건' in s, s
assert 'BA 33580 / CA 2840' in s, s
assert 'BA 33580, 33580' not in s, s
assert 'DATE_CONTEXT_ONLY' in s and '공정 연결 확정: 0건' in s, s
assert '원본 2건' in s, s
print('PASS v7 display dedup, LOT-reference vs date-context, provenance and no verified edges')
