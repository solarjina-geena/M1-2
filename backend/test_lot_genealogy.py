from lot_genealogy import build_genealogy_candidates
from lot_trace import trace_lot
rows = [
 {'id':'s1','date':'2026-09-03','variant':'IV','process':'STITCHING','metric':'PRODUCTION_QTY','value':100},
 {'id':'s2','date':'2026-09-03','variant':'OV','process':'STITCHING','metric':'PRODUCTION_QTY','value':200},
 {'id':'b1','date':'2026-09-10','variant':'IV','process':'BA','metric':'BOBBIN_LOT','value':'9.3','value_source':'HUMAN_VERIFIED'},
 {'id':'b2','date':'2026-09-10','variant':'IV','process':'BA','metric':'LEAD_PIN_INSERT','value':'9.3'},
 {'id':'b3','date':'2026-09-10','variant':'IV','process':'BA','metric':'LEAD_PIN_LOT','value':'9.8'},
 {'id':'s3','date':'2026-09-11','variant':'IV','process':'STITCHING','metric':'PRODUCTION_QTY','value':300},
 {'id':'amb','date':'2026-09-03','variant':'HSV→OV (전환 Event)','process':'STITCHING','metric':'PRODUCTION_QTY','value':400},
]
r=build_genealogy_candidates(rows,'2026-09-03')
assert len(r['consumers']) == 2, r
assert r['verified_edges'] == [], r
assert len(r['chronology_candidates']) == 1, r
assert r['chronology_candidates'][0]['possible_upstream_record_id']=='s1', r
assert r['consumers'][0]['raw_lot']=='9.3'
assert r['consumers'][0]['provenance']=='HUMAN_VERIFIED'
assert 'LOT 필드 정규화 일치' in trace_lot(rows,'ZIC','2026-09-03')
assert '공정 연결 확정: 0건' in trace_lot(rows,'ZIC','2026-09-03')
assert build_genealogy_candidates(rows,'2026-09-03','OV')['consumers']==[]
print('PASS genealogy role separation, chronology, variants, no false edges, provenance')
