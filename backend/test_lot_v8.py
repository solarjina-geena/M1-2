from lot_evidence_run import evidence_ref, run_review
from lot_trace import trace_lot

r1 = {'id':'human-1','date':'2026-09-10','variant':'IV','process':'BA','metric':'PRODUCTION_QTY','value':33580,'value_source':'HUMAN_VERIFIED','source':{'file':'IMEB3_TRACEABILITY_MASTER_PROMPT.md','page':None}}
r2 = {'id':'ca-1','date':'2026-09-10','variant':'IV','process':'CA','metric':'PRODUCTION_QTY','value':2840,'value_source':'HUMAN_VERIFIED'}
r3 = {'id':'lot-1','date':'2026-09-10','variant':'IV','process':'BA','metric':'BOBBIN_LOT','value':'9.3','value_source':'HUMAN_VERIFIED','source':{'file':'IMEB3_TRACEABILITY_MASTER_PROMPT.md','page':None}}
rows=[r1,r2,r3]
e=evidence_ref(r3)
assert e['record_id']=='lot-1' and e['source_value']=='9.3' and e['provenance']=='HUMAN_VERIFIED'
assert e['document_page_verified'] is False
assert evidence_ref({'source':{'file':'scan.pdf','page':0}})['document_page_verified'] is True
reviews=run_review(rows,{('2026-09-10','IV')})
assert len(reviews)==1 and reviews[0]['run_id'] is None and reviews[0]['source_record_count']==2
assert len(rows)==3 and r1['value']==33580 and r2['value']==2840
out=trace_lot(rows,'ZIC','2026-09-03')
assert 'LOT 필드 정규화 일치 (소비·공급 관계 미확정): 1건' in out
assert 'Evidence·RUN 식별 검토' in out and 'RUN_UNRESOLVED' in out
assert '원본 제조문서 파일·페이지 미검증' in out
assert '공정 연결 확정: 0건' in out
print('PASS v8 evidence refs, unverified page, unresolved RUN, no writes, v7 output')
