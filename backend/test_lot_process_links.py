from lot_process_links import build_process_review
from lot_trace import trace_lot
rows = [
 {'id':'bqty','date':'2026-09-10','variant':'IV','process':'BA','metric':'PRODUCTION_QTY','value':33580,'value_source':'HUMAN_VERIFIED'},
 {'id':'cqty','date':'2026-09-10','variant':'IV','process':'CA','metric':'PRODUCTION_QTY','value':2840,'value_source':'HUMAN_VERIFIED'},
 {'id':'bob','date':'2026-09-10','variant':'IV','process':'BA','metric':'BOBBIN_LOT','value':'9.3','value_source':'HUMAN_VERIFIED'},
 {'id':'ins','date':'2026-09-10','variant':'IV','process':'BA','metric':'LEAD_PIN_INSERT','value':'9.9'},
 {'id':'st','date':'2026-09-09','variant':'IV','process':'STITCHING','metric':'PRODUCTION_QTY','value':2000},
 {'id':'other','date':'2026-09-09','variant':'OV','process':'STITCHING','metric':'PRODUCTION_QTY','value':3000},
 {'id':'future','date':'2026-09-11','variant':'IV','process':'STITCHING','metric':'PRODUCTION_QTY','value':3000},
 {'id':'amb','date':'2026-09-10','variant':'HSV→OV','process':'BA','metric':'PRODUCTION_QTY','value':2000},
]
r=build_process_review(rows,'2026-09-03')
assert len(r['assembly_sets'])==1, r
assert r['assembly_sets'][0]['ba_records'][0]['quantity']==33580
assert r['assembly_sets'][0]['ca_records'][0]['quantity']==2840
assert len(r['stitching_candidates'])==1, r
assert r['stitching_candidates'][0]['stitching_record_id']=='st'
assert r['verified_edges']==[]
s=trace_lot(rows,'ZIC','2026-09-03')
assert 'LOT 필드 정규화 일치 (소비·공급 관계 미확정): 1건' in s
assert 'BA·CA 조립 세트 검토 후보: 1건' in s
assert 'Stitching→BA Insert 근거 검토 후보: 1건' in s
assert '공정 연결 확정: 0건' in s
print('PASS process review: BA/CA separate quantities, insert date candidate, variant, no confirmed edge')
