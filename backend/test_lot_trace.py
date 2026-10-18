from lot_trace import trace_lot
from app.main import infer_graph_context

ctx = infer_graph_context('ZID LOT의 제조 공정 기록을 추적해줘.', {})
assert ctx['lot_query'] == 'ZID' and ctx['lot_date'] == '2026-09-04' and 'date' not in ctx
rows = [
 {'date':'2026-09-04','variant':'OV','process':'INJECTION','metric':'PRODUCTION_QTY','value':100},
 {'date':'2026-09-08','variant':'IV','process':'BA','metric':'BOBBIN_LOT','value':'9/4','value_source':'HUMAN_VERIFIED'},
 {'date':'2026-09-10','variant':'OV','process':'BA','metric':'BOBBIN_LOT','value':'8/26'},
]
out = trace_lot(rows,'ZID','2026-09-04')
assert '직접 일치: 1건' in out
assert '생산 Event (LOT 연결 미확정): 1건' in out
assert '9/4' in out and '8/26' not in out
assert '100' not in out
print('PASS: LOT direct evidence isolated from same-date production and unrelated records')
