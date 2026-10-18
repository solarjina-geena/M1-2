"""Read-only LOT evidence lookup. Never equate production date to consumed material LOT."""
import re
from datetime import date
from lot_normalize import LOT_METRICS, find_lot_evidence
from lot_genealogy import build_genealogy_candidates
from lot_process_links import build_process_review, display_quantities
from lot_evidence_run import run_review, evidence_ref

def trace_lot(rows, lot_code, lot_date, variant=None):
    """Return only direct LOT evidence and separate production-date candidates."""
    if not lot_date or not lot_code:
        return 'LOT 코드를 해석할 수 없습니다. 조견표를 확인해 주세요.'
    relevant = [r for r in rows if not variant or r.get('variant') == variant]
    direct_matches = find_lot_evidence(relevant, lot_date)
    direct = [item['record'] for item in direct_matches]
    events = [r for r in relevant if r.get('date') == lot_date]
    lines = [f'LOT {lot_code.upper()} → {lot_date} (조견표 변환)', '※ LOT 사용 근거와 같은 날짜 생산 기록은 구분합니다.']
    lines.append(f'\n■ LOT 필드 정규화 일치 (소비·공급 관계 미확정): {len(direct)}건')
    if direct:
        for item in direct_matches[:40]:
            r = item['record']
            src = r.get('source') or {}
            where = f"{src.get('file','출처 미기재')} p{src.get('page','?')}" if isinstance(src,dict) else str(src)
            lines.append(f"- {r.get('date','날짜 미상')} / {r.get('variant','미상')} / {r.get('process','미상')} / {r.get('metric')}: {r.get('value')} / {r.get('value_source') or r.get('provenance') or '상태 미상'} / {where}")
            match = item
            if match['normalization']['normalization_status'] == 'UNCERTAIN':
                lines.append('  ↳ LOT 날짜 해석은 확인 필요(원문 판독/추정 표기)')
        if len(direct)>40: lines.append(f'- 나머지 {len(direct)-40}건은 상세 조회 필요')
    else:
        lines.append('- 현재 구조화된 LOT 필드에서 정규화 일치 기록을 찾지 못했습니다.')
    lines.append(f'\n■ {lot_date} 생산 Event (LOT 연결 미확정): {len(events)}건')
    if events:
        counts = {}
        for r in events:
            key = (r.get('variant') or '미상', r.get('process') or '미상')
            counts[key] = counts.get(key,0)+1
        for (v,p), n in sorted(counts.items()): lines.append(f'- {v} / {p}: {n}건')
    else: lines.append('- 해당 날짜 생산 Event 없음')
    genealogy = build_genealogy_candidates(relevant, lot_date)
    lines.append(f'\n■ LOT 역할별 참조: {len(genealogy["consumers"])}건 / 공정 연결 확정: 0건')
    for c in genealogy['consumers'][:20]:
        lines.append(f"- {c['lot_role']} → {c['process']} ({c['date']}, {c['variant']}) / {c['link_status']}")
    if genealogy['chronology_candidates']:
        lines.append(f'■ 시간순 선행공정 검토 후보: {len(genealogy["chronology_candidates"])}건 (연결 미확정)')
        for c in genealogy['chronology_candidates'][:10]:
            lines.append(f"- {c['possible_upstream_date']} / {c['variant']} / {c['possible_upstream_process']} → {c['days_before_consumption']}일 뒤 소비기록 (시간순 후보만)")
    review = build_process_review(relevant, lot_date, variant)
    # Direct LOT-reference assembly sets are distinct from date-only context.
    reference_keys = {(c['date'], c['variant']) for c in genealogy['consumers']}
    assembly_direct = [a for a in review['assembly_sets'] if (a['date'], a['variant']) in reference_keys]
    assembly_context = [a for a in review['assembly_sets'] if a['date'] == lot_date and (a['date'], a['variant']) not in reference_keys]
    lines.append(f'\n■ BA·CA 조립 세트 검토 후보: {len(assembly_direct) + len(assembly_context)}건 (직접 LOT 참조와 날짜 참고를 아래에서 분리)')
    lines.append(f'\n■ LOT 참조 공정의 BA·CA 검토 후보: {len(assembly_direct)}건 (LOT→CA 소비 및 동일 RUN 미확정)')
    for a in assembly_direct[:15]:
        bq, cq = display_quantities(a['ba_records']), display_quantities(a['ca_records'])
        lines.append(f"- {a['date']} / {a['variant']} / BA {bq} / CA {cq} / {a['status']}")
        lines.append(f"  ↳ 근거: 동일 날짜·Variant BA/CA 생산량; BA 원본 {len(a['ba_records'])}건, CA 원본 {len(a['ca_records'])}건. 수량 중복은 표시만 정리, 합산·원본 삭제 없음")
    lines.append(f'■ LOT 변환일 참고 생산의 BA·CA 검토 후보: {len(assembly_context)}건 (LOT 소비 연결 근거 없음)')
    for a in assembly_context[:15]:
        bq, cq = display_quantities(a['ba_records']), display_quantities(a['ca_records'])
        lines.append(f"- {a['date']} / {a['variant']} / BA {bq} / CA {cq} / {a['status']} / DATE_CONTEXT_ONLY")
    insert_candidates = [c for c in review['stitching_candidates'] if (c['ba_date'], c['variant']) in reference_keys]
    lines.append(f'■ Stitching→BA Insert 근거 검토 후보: {len(insert_candidates)}건 (연결 미확정)')
    for c in insert_candidates[:15]:
        lines.append(f"- {c['stitching_date']} Stitching → {c['ba_date']} {c['variant']} BA / Insert {c['insert_source_value']} / {c['status']}")
    if not insert_candidates:
        lines.append('- 해당 LOT 참조 BA에 대해 Insert LOT 날짜와 Variant가 일치하는 선행 Stitching 생산 기록을 확인하지 못했습니다. 원본 미기록·구조화 누락·불일치 여부는 미확정입니다.')
    # Explicitly expose the difference between a database record and a source PDF page.
    lines.append('\n■ Evidence·RUN 식별 검토 (읽기 전용)')
    for item in direct_matches[:10]:
        e = evidence_ref(item['record'])
        page = f"{e['document']} p{e['page']}" if e['document_page_verified'] else '원본 제조문서 파일·페이지 미검증'
        lines.append(f"- LOT 근거 record_id={e['record_id'] or '미기재'} / {e['provenance']} / {page}")
    selected = {(a['date'], a['variant']) for a in assembly_direct}
    for group in run_review(relevant, selected)[:10]:
        lines.append(f"- {group['date']} / {group['variant']} / RUN_UNRESOLVED / 생산수량 Evidence {group['source_record_count']}건 / 실제 문서·페이지 확인 {group['document_page_evidence_count']}건")
    if not direct_matches:
        lines.append('- LOT 근거 레코드 없음: 원본 파일·페이지 및 RUN 식별 불가')
    lines.append('- RUN ID를 날짜·Variant만으로 생성하지 않으며, PDF 페이지 미확인은 확정 근거로 사용하지 않습니다.')
    lines.append('\n■ 공정 연결 판정: LOT 필드의 날짜 일치만 확인. Stitching→BA→CA→검사→출하 관계는 별도 LOT 소비·공급 Evidence 없이는 확정하지 않습니다.')
    return '\n'.join(lines)
