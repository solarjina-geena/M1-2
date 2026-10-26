import csv
import hashlib
import json
import os
import re
import uuid
import time
import threading
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from fastapi import (FastAPI, HTTPException, Query, Response)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv
load_dotenv()
app = FastAPI(title='iMEB3 Manufacturing Intelligence API', version='0.50.0')
configured_origins = [x.strip() for x in os.getenv('ALLOWED_ORIGINS', 'http://localhost:5500,http://127.0.0.1:5500,null').split(',') if x.strip()]
local_dev_origins = ['http://localhost:5500', 'http://127.0.0.1:5500']
origins = list(dict.fromkeys([*configured_origins, *local_dev_origins]))
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=['*'], allow_headers=['*'], expose_headers=['X-Data-Source', 'X-Data-Source-Info', 'X-Data-Source-Notice'])
DB_MODE = 'memory'
firestore_db = None
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    raw = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON', '').strip()
    key_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', '').strip()
    if raw or key_path:
        info = json.loads(raw) if raw else key_path
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(info))
        firestore_db = firestore.client()
        DB_MODE = 'firestore'
except Exception as e:
    print('Firestore init skipped:', e)
MEM = {'data': {}, 'conversations': {}, 'reviews': {}}
FIRESTORE_EXPORT_DIR = Path(__file__).resolve().parents[2] / 'firestore_import'
FIRESTORE_EXPORT_CSV = '20260801-20260930_firestore_unified.csv'
ACTIVE_DATA_SOURCE = 'firestore' if DB_MODE == 'firestore' else 'memory'
_CSV_FALLBACK_CACHE = None
_CSV_FALLBACK_INFO = {'record_count': 0, 'skipped_enrich_without_base': 0, 'corrections_applied': 0, 'corrections_already_present': 0}
_READ_CACHE_TTL_SECONDS = 60
_READ_CACHE = {}
_READ_CACHE_LOCK = threading.Lock()
_FIRESTORE_READ_BACKOFF_UNTIL = 0.0
_DAILY_BACKUP_RETENTION_DAYS = max(2, int(os.getenv('DAILY_BACKUP_RETENTION_DAYS', '7')))
_DAILY_BACKUP_LOCK = threading.Lock()
_DAILY_BACKUP_DATE = None
_DAILY_BACKUP_STATUS = 'not_run'
SEED = [{'id': 'DEMO-RUN-1', 'date': '2026-01-01', 'run_id': '20260101D01', 'shift': 'D', 'run_sequence': 1, 'product': 'iMEB3-DEMO', 'variant': 'DEMO', 'process': 'ASSEMBLY', 'metric': 'PRODUCTION_QTY', 'value': 11137, 'unit': 'EA', 'value_source': 'DERIVED', 'verification_status': 'DEMO_DATA'}, {'id': 'DEMO-RUN-2', 'date': '2026-01-02', 'run_id': '20260102D01', 'shift': 'D', 'run_sequence': 1, 'product': 'iMEB3-DEMO', 'variant': 'DEMO', 'process': 'ASSEMBLY', 'metric': 'PRODUCTION_QTY', 'value': 11274, 'unit': 'EA', 'value_source': 'DERIVED', 'verification_status': 'DEMO_DATA'}, {'id': 'DEMO-RUN-3', 'date': '2026-01-03', 'run_id': '20260103D01', 'shift': 'D', 'run_sequence': 1, 'product': 'iMEB3-DEMO', 'variant': 'DEMO', 'process': 'ASSEMBLY', 'metric': 'PRODUCTION_QTY', 'value': 11411, 'unit': 'EA', 'value_source': 'DERIVED', 'verification_status': 'DEMO_DATA'}, {'id': 'DEMO-RUN-4', 'date': '2026-01-04', 'run_id': '20260104D01', 'shift': 'D', 'run_sequence': 1, 'product': 'iMEB3-DEMO', 'variant': 'DEMO', 'process': 'ASSEMBLY', 'metric': 'PRODUCTION_QTY', 'value': 11548, 'unit': 'EA', 'value_source': 'DERIVED', 'verification_status': 'DEMO_DATA'}, {'id': 'DEMO-RUN-5', 'date': '2026-01-05', 'run_id': '20260105D01', 'shift': 'D', 'run_sequence': 1, 'product': 'iMEB3-DEMO', 'variant': 'DEMO', 'process': 'ASSEMBLY', 'metric': 'PRODUCTION_QTY', 'value': 11685, 'unit': 'EA', 'value_source': 'DERIVED', 'verification_status': 'DEMO_DATA'}, {'id': 'DEMO-RUN-6', 'date': '2026-01-06', 'run_id': '20260106D01', 'shift': 'D', 'run_sequence': 1, 'product': 'iMEB3-DEMO', 'variant': 'DEMO', 'process': 'ASSEMBLY', 'metric': 'PRODUCTION_QTY', 'value': 11822, 'unit': 'EA', 'value_source': 'DERIVED', 'verification_status': 'DEMO_DATA'}, {'id': 'DEMO-RUN-7', 'date': '2026-01-07', 'run_id': '20260107D01', 'shift': 'D', 'run_sequence': 1, 'product': 'iMEB3-DEMO', 'variant': 'DEMO', 'process': 'ASSEMBLY', 'metric': 'PRODUCTION_QTY', 'value': 11959, 'unit': 'EA', 'value_source': 'DERIVED', 'verification_status': 'DEMO_DATA'}, {'id': 'DEMO-RUN-8', 'date': '2026-01-08', 'run_id': '20260108D01', 'shift': 'D', 'run_sequence': 1, 'product': 'iMEB3-DEMO', 'variant': 'DEMO', 'process': 'ASSEMBLY', 'metric': 'PRODUCTION_QTY', 'value': 12096, 'unit': 'EA', 'value_source': 'DERIVED', 'verification_status': 'DEMO_DATA'}, {'id': 'DEMO-RUN-9', 'date': '2026-01-09', 'run_id': '20260109D01', 'shift': 'D', 'run_sequence': 1, 'product': 'iMEB3-DEMO', 'variant': 'DEMO', 'process': 'ASSEMBLY', 'metric': 'PRODUCTION_QTY', 'value': 12233, 'unit': 'EA', 'value_source': 'DERIVED', 'verification_status': 'DEMO_DATA'}]
if DB_MODE == 'memory':
    for _r in SEED:
        MEM['data'][_r['id']] = _r

def now():
    return datetime.now(timezone.utc).isoformat()

def put(col, id, obj):
    if DB_MODE == 'firestore':
        if ACTIVE_DATA_SOURCE == 'csv_fallback':
            if col == 'data':
                raise HTTPException(status_code=503, detail='CSV 임시조회는 읽기 전용입니다. Firestore가 복구된 뒤 다시 저장해 주세요.')
            MEM.setdefault(col, {})[id] = obj
            return obj
        firestore_db.collection(col).document(id).set(obj)
    else:
        MEM[col][id] = obj
    if DB_MODE == 'firestore':
        with _READ_CACHE_LOCK:
            _READ_CACHE.pop(col, None)
        return obj
    return obj

def get(col, id):
    if DB_MODE == 'firestore':
        if ACTIVE_DATA_SOURCE == 'csv_fallback':
            return MEM.setdefault(col, {}).get(id)
        s = firestore_db.collection(col).document(id).get()
        if s.exists:
            return s.to_dict()
        return
    return MEM[col].get(id)

def load_csv_fallback():
    '''Rebuild a read-only data snapshot from the one explicitly approved export file.'''

    global _CSV_FALLBACK_INFO, _CSV_FALLBACK_CACHE
    path = FIRESTORE_EXPORT_DIR / FIRESTORE_EXPORT_CSV
    try:
        stat = path.stat()
    except OSError as exc:
        raise HTTPException(status_code=503, detail='Firestore 조회가 제한됐고 지정된 CSV 임시자료를 찾을 수 없습니다.') from exc
    csv_path = FIRESTORE_EXPORT_DIR / FIRESTORE_EXPORT_CSV
    try:
        csv_stat = csv_path.stat()
    except OSError:
        csv_stat = None
    signature = (stat.st_mtime_ns, stat.st_size,
                 csv_stat.st_mtime_ns if csv_stat else None,
                 csv_stat.st_size if csv_stat else None)
    if _CSV_FALLBACK_CACHE and _CSV_FALLBACK_CACHE[0] == signature:
        return [dict(row) for row in _CSV_FALLBACK_CACHE[1]]
    docs = {}
    skipped_enrich = set()
    corrections_applied = 0
    corrections_already_present = 0
    try:
        with path.open('r', encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            required = {'action', 'collection', 'document_id', 'payload_json', 'expected_document_json'}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise ValueError('CSV 열 구성이 예상한 Firestore 변경자료와 다릅니다.')
            for line, row in enumerate(reader, start=2):
                if row.get('collection') != 'data':
                    continue
                action = (row.get('action') or '').strip().upper()
                doc_id = (row.get('document_id') or '').strip()
                if not doc_id:
                    raise ValueError(f'{line}행에 document_id가 없습니다.')
                payload = json.loads(row.get('payload_json') or '{}')
                if not isinstance(payload, dict):
                    raise ValueError(f'{line}행 payload_json이 객체가 아닙니다.')
                if action == 'ADD':
                    if str(payload.get('id') or doc_id) != doc_id:
                        raise ValueError(f'{line}행 document_id와 payload id가 다릅니다.')
                    payload.setdefault('id', doc_id)
                    docs[doc_id] = payload
                    continue
                if action == 'ENRICH':
                    if doc_id not in docs:
                        skipped_enrich.add(doc_id)
                        continue
                    docs[doc_id].update(payload)
                    continue
                if action == 'CORRECT':
                    expected = json.loads(row.get('expected_document_json') or 'null')
                    current = docs.get(doc_id)
                    if current is not None:
                        if current == expected:
                            docs[doc_id] = payload
                            corrections_applied += 1
                            continue
                    if current is not None:
                        if current == payload:
                            corrections_already_present += 1
                            continue
                    raise ValueError(f'{line}행 correction의 기대값이 현재 자료와 일치하지 않습니다.')
                raise ValueError(f'{line}행에서 지원하지 않는 action을 발견했습니다.')
    except HTTPException:
        raise
    except Exception as exc:
        print('CSV fallback load failed:', type(exc).__name__, str(exc)[:300])
        raise HTTPException(status_code=503, detail='지정된 CSV 임시자료를 안전하게 재구성하지 못했습니다.') from exc
    rows = list(docs.values())
    _CSV_FALLBACK_INFO = {'record_count': len(rows), 'skipped_enrich_without_base': len(skipped_enrich), 'corrections_applied': corrections_applied, 'corrections_already_present': corrections_already_present}
    _CSV_FALLBACK_CACHE = signature, rows
    return [dict(row) for row in rows]

def all_docs(col):
    global ACTIVE_DATA_SOURCE, _FIRESTORE_READ_BACKOFF_UNTIL
    if DB_MODE == 'firestore':
        if ACTIVE_DATA_SOURCE == 'csv_fallback' and col != 'data':
            return list(MEM.setdefault(col, {}).values())
        now_mono = time.monotonic()
        with _READ_CACHE_LOCK:
            if col == 'data' and now_mono < _FIRESTORE_READ_BACKOFF_UNTIL:
                ACTIVE_DATA_SOURCE = 'csv_fallback'
                return load_csv_fallback()
            cached = _READ_CACHE.get(col)
            if cached and cached[0] > now_mono:
                if col == 'data':
                    ACTIVE_DATA_SOURCE = 'firestore'
                return [dict(row) for row in cached[1]]
        try:
            rows = [d.to_dict() for d in firestore_db.collection(col).stream(timeout=10, retry=None)]
        except Exception as exc:
            try:
                from google.api_core.exceptions import (DeadlineExceeded, ResourceExhausted, ServiceUnavailable)
                if isinstance(exc, (ResourceExhausted, ServiceUnavailable, DeadlineExceeded)):
                    if col == 'data':
                        rows = load_csv_fallback()
                        ACTIVE_DATA_SOURCE = 'csv_fallback'
                        _FIRESTORE_READ_BACKOFF_UNTIL = time.monotonic() + _READ_CACHE_TTL_SECONDS
                    else:
                        raise
                else:
                    raise
            except ImportError:
                raise
        if col == 'data' and ACTIVE_DATA_SOURCE == 'csv_fallback':
            _READ_CACHE[col] = time.monotonic() + _READ_CACHE_TTL_SECONDS, rows
            return [dict(row) for row in rows]
        if col == 'data':
            ACTIVE_DATA_SOURCE = 'firestore'
            _FIRESTORE_READ_BACKOFF_UNTIL = 0.0
        _READ_CACHE[col] = time.monotonic() + _READ_CACHE_TTL_SECONDS, rows
        return [dict(row) for row in rows]
    return list(MEM[col].values())

def maybe_create_daily_backup(rows):
    '''Persist one idempotent daily copy of Firestore data in Firestore itself.'''
    global _DAILY_BACKUP_DATE, _DAILY_BACKUP_STATUS
    if DB_MODE != 'firestore' or ACTIVE_DATA_SOURCE != 'firestore':
        return
    backup_day = datetime.now(timezone.utc).date().isoformat()
    if _DAILY_BACKUP_DATE == backup_day:
        return
    if not _DAILY_BACKUP_LOCK.acquire(blocking=False):
        return
    try:
        if _DAILY_BACKUP_DATE == backup_day:
            return
        backup_root = firestore_db.collection('daily_backups')
        day_ref = backup_root.document(backup_day)
        prior = day_ref.get()
        prior_data = (prior.to_dict() or {}) if prior.exists else {}
        if prior.exists and prior_data.get('status') == 'complete':
            _DAILY_BACKUP_DATE = backup_day
            _DAILY_BACKUP_STATUS = 'complete'
            return

        if prior.exists:
            # Remove an incomplete prior attempt so stale partial rows cannot
            # leak into the retried snapshot for the same date.
            partial_docs = day_ref.collection('data').stream(timeout=15, retry=None)
            cleanup_batch = firestore_db.batch()
            cleanup_count = 0
            for partial_doc in partial_docs:
                cleanup_batch.delete(partial_doc.reference)
                cleanup_count += 1
                if cleanup_count == 400:
                    cleanup_batch.commit()
                    cleanup_batch = firestore_db.batch()
                    cleanup_count = 0
            if cleanup_count:
                cleanup_batch.commit()

        _DAILY_BACKUP_STATUS = 'writing'
        day_ref.set({'backup_date': backup_day, 'status': 'writing', 'started_at': now()}, merge=True)
        batch = firestore_db.batch()
        pending = 0
        for row in rows:
            source_id = str(row.get('id') or json.dumps(row, sort_keys=True, default=str))
            backup_id = hashlib.sha256(source_id.encode('utf-8')).hexdigest()
            backup_ref = day_ref.collection('data').document(backup_id)
            batch.set(backup_ref, {'source_id': source_id, 'snapshot_date': backup_day, 'record': row})
            pending += 1
            if pending == 400:
                batch.commit()
                batch = firestore_db.batch()
                pending = 0
        if pending:
            batch.commit()
        day_ref.set({'backup_date': backup_day, 'status': 'complete',
                     'record_count': len(rows), 'completed_at': now()}, merge=True)
        _DAILY_BACKUP_DATE = backup_day
        _DAILY_BACKUP_STATUS = 'complete'
        print('Firestore daily data backup complete:', backup_day, 'records:', len(rows))

        # Keep a rolling week of snapshots to bound storage. A cleanup failure
        # does not invalidate today's already completed backup.
        try:
            from datetime import date, timedelta
            cutoff = (date.fromisoformat(backup_day) - timedelta(days=_DAILY_BACKUP_RETENTION_DAYS - 1)).isoformat()
            expired = backup_root.where('backup_date', '<', cutoff).stream(timeout=15, retry=None)
            for old_day in expired:
                old_data = old_day.reference.collection('data').stream(timeout=15, retry=None)
                delete_batch = firestore_db.batch()
                deleted = 0
                for old_doc in old_data:
                    delete_batch.delete(old_doc.reference)
                    deleted += 1
                    if deleted == 400:
                        delete_batch.commit()
                        delete_batch = firestore_db.batch()
                        deleted = 0
                if deleted:
                    delete_batch.commit()
                old_day.reference.delete()
        except Exception as exc:
            print('Firestore daily backup retention cleanup failed:', type(exc).__name__)
    except Exception as exc:
        _DAILY_BACKUP_STATUS = 'failed'
        print('Firestore daily data backup failed:', type(exc).__name__)
    finally:
        _DAILY_BACKUP_LOCK.release()

def delete(col, id):
    if DB_MODE == 'firestore':
        if ACTIVE_DATA_SOURCE == 'csv_fallback':
            if col == 'data':
                raise HTTPException(status_code=503, detail='CSV 임시조회는 읽기 전용입니다. Firestore가 복구된 뒤 다시 삭제해 주세요.')
            MEM.setdefault(col, {}).pop(id, None)
            return
        firestore_db.collection(col).document(id).delete()
    else:
        MEM[col].pop(id, None)
    if DB_MODE == 'firestore':
        with _READ_CACHE_LOCK:
            _READ_CACHE.pop(col, None)

def canonical_run_id(date: str, shift: str, sequence: int) -> str:
    digits = re.sub('\\D', '', date)
    if len(digits) != 8:
        raise ValueError('date는 YYYY-MM-DD 또는 YYYYMMDD로 정규화 가능해야 합니다.')
    return f'{digits}{shift}{sequence}'

class DataIn(BaseModel):
    date: str
    value: float | None = Field(None, allow_inf_nan=False)
    memo: str = ''
    shift: Literal['D', 'N'] = 'D'
    run_sequence: int = Field(1, ge=1)
    product: str = 'iMEB3'
    variant: Literal['IV', 'OV', 'HSV'] = 'IV'
    process: str = 'INJECTION'
    metric: str = 'BOBBIN_WEIGHT'
    unit: str = ''
    source_lot: str | None = None
    value_source: Literal['SOURCE_READ', 'HUMAN_VERIFIED', 'DERIVED', 'UNCERTAIN', 'BLANK'] = 'SOURCE_READ'

    @field_validator('date')
    @classmethod
    def validate_date(cls, value: str) -> str:
        for fmt in ('%Y-%m-%d', '%Y%m%d'):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                continue
        raise ValueError('date는 실제 날짜인 YYYY-MM-DD 또는 YYYYMMDD 형식이어야 합니다.')

class DataUpdate(BaseModel):
    value: float | None = Field(None, allow_inf_nan=False)
    memo: str | None = None
    value_source: str | None = None

class Message(BaseModel):
    role: Literal['user', 'assistant']
    content: str

class ConversationIn(BaseModel):
    title: str = '새 대화'
    messages: list[Message] = []
    context: dict[str, Any] = {}

class ChatIn(BaseModel):
    message: str
    conversation_id: str | None = None
    context: dict[str, Any] = {}
    attachments: list[dict[str, Any]] = []

class ReviewIn(BaseModel):
    type: str = 'DATA_CONFIRMATION'
    status: Literal['NEEDS_REVIEW', 'CONFIRMED', 'CORRECTED', 'HOLD'] = 'NEEDS_REVIEW'
    evidence_id: str | None = None
    run_id: str | None = None
    lot_id: str | None = None
    conversation_id: str | None = None
    source_value: Any = None
    verified_value: Any = None
    note: str = ''

_WORKBOOK_EVIDENCE_CACHE = None

def load_workbook_evidence():
    '''Read only confirmed graph evidence from the one designated workbook.'''

    global _WORKBOOK_EVIDENCE_CACHE
    path = FIRESTORE_EXPORT_DIR / 'M3-1_원본판독_9월_완성본.xlsx'
    csv_path = FIRESTORE_EXPORT_DIR / FIRESTORE_EXPORT_CSV
    try:
        stat = path.stat()
    except OSError:
        return {'available': False, 'production': [], 'inspection_lots': []}
    try:
        csv_stat = csv_path.stat()
        csv_signature = (csv_stat.st_mtime_ns, csv_stat.st_size)
    except OSError:
        csv_signature = None
    signature = stat.st_mtime_ns, stat.st_size, csv_signature
    if _WORKBOOK_EVIDENCE_CACHE and _WORKBOOK_EVIDENCE_CACHE[0] == signature:
        return _WORKBOOK_EVIDENCE_CACHE[1]
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(path) as book:
        shared = []
        if 'xl/sharedStrings.xml' in book.namelist():
            root = ET.fromstring(book.read('xl/sharedStrings.xml'))
            shared = [''.join(t.text or '' for t in si.findall('.//m:t', ns)) for si in root.findall('m:si', ns)]
        def rows(sheet):
            root = ET.fromstring(book.read(f'xl/worksheets/{sheet}'))
            result = []
            for row in root.findall('.//m:sheetData/m:row', ns):
                values = {}
                for cell in row.findall('m:c', ns):
                    col = re.match('[A-Z]+', cell.get('r', '')).group(0) if cell.get('r') else ''
                    v = cell.find('m:v', ns)
                    if cell.get('t') == 'inlineStr':
                        value = ''.join(t.text or '' for t in cell.findall('.//m:t', ns))
                    elif v is None:
                        value = ''
                    elif cell.get('t') == 's':
                        value = shared[int(v.text)]
                    else:
                        value = v.text or ''
                    values[col] = value
                result.append(values)
                continue
            return result

        summary = rows('sheet4.xml')
        records = rows('sheet5.xml')
    source_by_key = {r.get('A', ''): {'ids': r.get('R', ''), 'operator': r.get('N', '')}
                     for r in summary if r.get('A') and r.get('R')}
    qty_by_key = {}
    for r in records:
        if r.get('B') == '수량' and r.get('C') == 'Lot별 BOX 수' and r.get('E', '').isdigit() and r.get('J') == '확인':
            qty_by_key[r.get('A'), r.get('H')] = int(r['E'])
    inspection_metadata = {}
    if csv_path.exists():
        with csv_path.open('r', encoding='utf-8-sig', newline='') as handle:
            for source_row in csv.DictReader(handle):
                if source_row.get('collection') != 'data' or source_row.get('action') not in ('ADD', 'ENRICH'):
                    continue
                try:
                    payload = json.loads(source_row.get('payload_json') or '{}')
                except (TypeError, ValueError):
                    continue
                if str(payload.get('process', '')).upper() not in ('FINAL_INSPECTION', 'INSPECTION'):
                    continue
                detail = payload.get('details') or {}
                source_id = payload.get('id') or source_row.get('document_id')
                metadata = inspection_metadata.setdefault(source_id, {})
                metadata['inspection_class'] = metadata.get('inspection_class') or detail.get('inspection_class_raw', '')
                metadata['operator'] = metadata.get('operator') or detail.get('inspector_raw') or detail.get('operator_raw', '')
    production = []
    inspection_lots = []
    for r in records:
        key = r.get('A', '')
        day = r.get('R', '')
        variant = r.get('T', '')
        if r.get('B') == '수량' and r.get('C') in ('BA 총생산', 'CA 총생산') and r.get('J') == '확인' and r.get('E', '').isdigit() and re.fullmatch('2026-\\d{2}-\\d{2}', day) and variant in ('IV', 'OV', 'HSV'):
            process = 'BA' if r['C'] == 'BA 총생산' else 'CA'
            production.append({'id': f'workbook-{key}-{variant}-{process}', 'date': day, 'variant': variant, 'process': process, 'metric': 'PRODUCTION_QTY', 'value': int(r['E']), 'shift': r.get('I', ''), 'value_source': 'HUMAN_VERIFIED', 'source_record_id': key, 'source': {'file': 'M3-1_원본판독_9월_완성본.xlsx', 'sheet': '02_기록값', 'row_evidence': 'confirmed'}})
        if not r.get('B') == '공정LOT':
            continue
        if not r.get('C') == 'Lot No':
            continue
        if not r.get('S') == '최종검사':
            continue
        if not r.get('U') == 'LOT':
            continue
        if not r.get('J') == '확인':
            continue
        if not variant in ('IV', 'OV', 'HSV'):
            continue
        if not re.fullmatch('2026-\\d{2}-\\d{2}', day):
            continue
        raw = r.get('E', '')
        code_match = re.search('[A-Z][A-Z0-9]{2}', raw.upper())
        lot_code = code_match.group(0) if code_match else ''
        date_code = r.get('N', '')
        lot_date = f'20{date_code[:2]}-{date_code[2:4]}-{date_code[4:6]}' if re.fullmatch('\\d{6}', date_code) else ''
        if not lot_code:
            continue
        if not lot_date:
            continue
        source_info = source_by_key.get(key, {'ids': '', 'operator': ''})
        sources = [x.strip() for x in source_info['ids'].split(',') if x.strip()]
        col_match = re.match('(\\d+)', r.get('H', ''))
        col = int(col_match.group(1)) if col_match else 0
        if len(sources) > 1:
            source_id = next((x for x in sources if re.search(f'-C{col}(?:$|-)', x)), '') if col else ''
        else:
            source_id = sources[0] if sources else ''
        boxes = qty_by_key.get((key, r.get('H')))
        metadata = inspection_metadata.get(source_id, {})
        inspection_class = metadata.get('inspection_class', '')
        operator = metadata.get('operator') or source_info['operator']
        training = operator.strip() in ('남설매', '김태연') and bool(re.search(r'1차\s*검사', inspection_class))
        inspection_lots.append({'id': f'workbook-lot-{key}-{variant}-{col or 1}-{lot_code}', 'date': lot_date, 'inspection_date': day, 'variant': variant, 'process': 'CA', 'metric': 'INSPECTION_PRODUCT_LOT', 'lot_code': lot_code, 'raw_lot': raw, 'trace_lot_id': date_code + 'D1', 'boxes': boxes, 'box_size_ea': 480, 'source_record_id': source_id, 'source_key': key, 'operator': operator, 'inspection_class': inspection_class, 'training_inspection': training, 'value_source': 'HUMAN_VERIFIED', 'source': {'file': 'M3-1_원본판독_9월_완성본.xlsx', 'sheet': '02_기록값', 'row_evidence': 'confirmed'}})
        continue
    result = {'available': True, 'source': 'designated_workbook', 'production': production, 'inspection_lots': inspection_lots}
    _WORKBOOK_EVIDENCE_CACHE = signature, result
    return result

@app.get('/api/workbook-evidence')
def workbook_evidence():
    return load_workbook_evidence()

@app.get('/api/health')
def health():
    return {'ok': True, 'storage': ACTIVE_DATA_SOURCE, 'configured_storage': DB_MODE,
            'csv_fallback': ACTIVE_DATA_SOURCE == 'csv_fallback',
            'csv_fallback_info': _CSV_FALLBACK_INFO if ACTIVE_DATA_SOURCE == 'csv_fallback' else None,
            'daily_backup': {'enabled': DB_MODE == 'firestore', 'status': _DAILY_BACKUP_STATUS,
                             'date': _DAILY_BACKUP_DATE, 'retention_days': _DAILY_BACKUP_RETENTION_DAYS}}

@app.post('/api/data')
def create_data(body: DataIn):
    if DB_MODE == 'firestore' and ACTIVE_DATA_SOURCE == 'csv_fallback':
        raise HTTPException(status_code=503, detail='CSV 임시조회는 읽기 전용입니다. Firestore가 복구된 뒤 다시 등록해 주세요.')
    id = str(uuid.uuid4())
    obj = body.model_dump()
    obj.update(id=id, run_id=canonical_run_id(body.date, body.shift, body.run_sequence), created_at=now(), updated_at=now())
    return put('data', id, obj)

@app.get('/api/data')
def list_data(response: Response, limit: int = Query(2000, ge=1, le=2000)):
    rows = all_docs('data')
    response.headers['X-Data-Source'] = ACTIVE_DATA_SOURCE
    if ACTIVE_DATA_SOURCE == 'csv_fallback':
        response.headers['X-Data-Source-Notice'] = 'Read-only temporary Firestore export; incomplete enrichment rows are skipped'
        response.headers['X-Data-Source-Info'] = json.dumps(_CSV_FALLBACK_INFO, separators=(',', ':'))
        response.headers['X-Data-Source-Info'] = json.dumps(_CSV_FALLBACK_INFO, separators=(',', ':'))
    maybe_create_daily_backup(rows)
    ordered = sorted(rows, key=lambda x: (str(x.get('date') or ''), str(x.get('run_id') or ''), str(x.get('id') or '')))
    return ordered[:limit]

@app.put('/api/data/{id}')
def update_data(id: str, body: DataUpdate):
    if DB_MODE == 'firestore' and ACTIVE_DATA_SOURCE == 'csv_fallback':
        raise HTTPException(status_code=503, detail='CSV 임시조회는 읽기 전용입니다. Firestore가 복구된 뒤 다시 수정해 주세요.')
    obj = get('data', id)
    if not obj:
        raise HTTPException(404, '데이터가 없습니다.')
    for k, v in body.model_dump(exclude_unset=True).items():
        obj[k] = v
    obj['updated_at'] = now()
    return put('data', id, obj)

@app.delete('/api/data/{id}')
def delete_data(id: str):
    if DB_MODE == 'firestore' and ACTIVE_DATA_SOURCE == 'csv_fallback':
        raise HTTPException(status_code=503, detail='CSV 임시조회는 읽기 전용입니다. Firestore가 복구된 뒤 다시 삭제해 주세요.')
    if not get('data', id):
        raise HTTPException(404, '데이터가 없습니다.')
    delete('data', id)
    return {'deleted': id}

def build_summary(rows=None):
    rows = all_docs('data') if rows is None else rows
    production = [r for r in rows if str(r.get('metric', '')).upper() in {'PRODUCTION_QTY', 'PRODUCTION_QUANTITY'} and isinstance(r.get('value'), (int, float))]
    numeric = production or [r for r in rows if isinstance(r.get('value'), (int, float))]
    vals = [r['value'] for r in numeric]
    dates = sorted([r.get('date') for r in numeric if r.get('date')])
    ordered = sorted(numeric, key=lambda r: (str(r.get('date') or ''), str(r.get('run_id') or '')))
    trend = '데이터 부족'
    change_pct = None
    if len(ordered) >= 6:
        n = max(3, min(10, len(ordered) // 3))
        a = sum((x['value'] for x in ordered[-2 * n:-n])) / n
        b = sum((x['value'] for x in ordered[-n:])) / n
        if a:
            change_pct = (b - a) / abs(a) * 100
            trend = ('증가' if change_pct > 2 else '감소' if change_pct < -2 else '유지') + f' ({change_pct:+.1f}%)'
    return {'period': f'{dates[0]} ~ {dates[-1]}' if dates else '데이터 없음', 'count': len(numeric), 'total_records': len(rows), 'primary_metric': 'PRODUCTION_QTY' if production else 'ALL_NUMERIC', 'metrics': {'total': sum(vals) if vals else None, 'average': sum(vals) / len(vals) if vals else None, 'max': max(vals) if vals else None, 'min': min(vals) if vals else None}, 'trend': trend, 'change_pct': change_pct, 'rule': 'BLANK≠0; date alone is not unique; canonical RUN=YYYYMMDD{D|N}{sequence}'}

@app.get('/api/data/summary')
def summary(response: Response):
    rows = all_docs('data')
    response.headers['X-Data-Source'] = ACTIVE_DATA_SOURCE
    maybe_create_daily_backup(rows)
    if ACTIVE_DATA_SOURCE == 'csv_fallback':
        response.headers['X-Data-Source-Info'] = json.dumps(_CSV_FALLBACK_INFO, separators=(',', ':'))
    return build_summary(rows)

@app.post('/api/data/seed-demo')
def seed_demo():
    '''평가용 비식별 시계열 120건. 실제 회사 생산실적이 아님.'''

    inserted = 0
    from datetime import date, timedelta
    variants = ['IV', 'OV', 'HSV']
    start = date(2026, 1, 1)
    for i in range(120):
        d = start + timedelta(days=i)
        variant = variants[i % 3]
        rid = f'demo-{i + 1:03d}'
        if get('data', rid):
            continue
        value = round(11000 + i * 18 + (i % 7 - 3) * 75 + (300 if variant == 'OV' else 600 if variant == 'HSV' else 0), 2)
        obj = {'id': rid, 'date': d.isoformat(), 'value': value, 'memo': f'평가용 비식별 {variant} 생산량 시계열', 'shift': 'D', 'run_sequence': 1, 'run_id': f'{d.strftime('%Y%m%d')}D1', 'product': 'iMEB3-DEMO', 'variant': variant, 'process': 'INJECTION', 'metric': 'PRODUCTION_QTY', 'unit': 'EA', 'source_lot': None, 'value_source': 'DERIVED', 'verification_status': 'DEMO_DATA', 'created_at': now(), 'updated_at': now()}
        put('data', rid, obj)
        inserted += 1
        continue
    return {'inserted': inserted, 'total': len(all_docs('data')), 'notice': '평가용 비식별 DEMO DATA이며 실제 회사 생산실적이 아닙니다.'}

@app.post('/api/migration/recovered-v1')
def migrate_recovered_v1():
    from migration.migrate_recovered import migrate
    return {**migrate(put, get, now), 'storage': DB_MODE}

@app.get('/api/migration/status')
def migration_status():
    rows = [r for r in all_docs('data') if r.get('migration_batch') == 'RECOVERED_VERIFIED_V1']
    hv = sum((1 for r in rows if r.get('value_source') == 'HUMAN_VERIFIED'))
    sr = sum((1 for r in rows if r.get('value_source') == 'SOURCE_READ'))
    return {'batch': 'RECOVERED_VERIFIED_V1', 'migrated': len(rows), 'human_verified': hv, 'source_read': sr, 'storage': DB_MODE}

@app.post('/api/conversations')
def create_conv(body: ConversationIn):
    id = str(uuid.uuid4())
    obj = {'id': id, **body.model_dump(), 'created_at': now(), 'updated_at': now()}
    return put('conversations', id, obj)

@app.get('/api/conversations')
def list_conv():
    return sorted(all_docs('conversations'), key=(lambda x: x.get('updated_at', '')), reverse=True)

@app.get('/api/conversations/{id}')
def get_conv(id: str):
    obj = get('conversations', id)
    if not obj:
        raise HTTPException(404, '대화가 없습니다.')
    return obj

@app.delete('/api/conversations/{id}')
def del_conv(id: str):
    delete('conversations', id)
    return {'deleted': id}

@app.post('/api/reviews')
def create_review(body: ReviewIn):
    id = str(uuid.uuid4())
    obj = {'id': id, **body.model_dump(), 'created_at': now(), 'updated_at': now()}
    return put('reviews', id, obj)

@app.get('/api/reviews')
def list_reviews(status: str | None=None):
    rows = all_docs('reviews')
    return [r for r in rows if status is None or r.get('status') == status]

SYSTEM = '당신은 iMEB3 제조 품질·Traceability AI Agent다.\n원본 Evidence와 사람의 판단을 엄격히 분리한다.\nProvenance 우선순위는 HUMAN_VERIFIED > SOURCE_READ > DERIVED이다.\nBLANK를 0으로 만들지 말고, 없는 값을 만들지 말라.\nMES와 작업일보를 임의로 혼합하지 말라.\n생산 RUN 식별자는 YYYYMMDD{D|N}{sequence}이며 날짜만으로 생산 Event를 확정하지 말라.\n\n중요한 Provenance 규칙:\n- verification_status가 DEMO_DATA인 레코드는 평가용 비식별 샘플 데이터다.\n- DEMO_DATA를 HUMAN_VERIFIED 또는 SOURCE_READ라고 표현하지 말라.\n- DEMO_DATA에서 계산한 합계, 평균, 최대, 최소, 추세는 DEMO_DATA 기반 DERIVED 통계라고 명시하라.\n- DEMO_DATA는 실제 회사 생산실적이나 원본 제조 Evidence라고 표현하지 말라.\n- provenance/value_source와 verification_status가 충돌하면 실제 상태를 임의로 승격하지 말라.\n\n답변은 짧고 현장 사용자가 이해하기 쉬운 한국어로 한다.'
SYSTEM += '\n이전 대화에서 사용자가 직접 정한 별칭·선호·설정은 대화 문맥으로 답하라. 이를 Firestore에서 검증된 제조 사실처럼 표현하지 말라. 후속 질문은 이전 사용자·AI 메시지를 참고해 이어서 답하라.'

def infer_graph_context(text: str, current: dict[str, Any]):
    c = dict(current or {})
    u = text.upper()
    c['product'] = 'iMEB3'
    c.pop('process', None)
    c.pop('date', None)
    c.pop('date_query', None)
    c.pop('lot_query', None)
    c.pop('lot_date', None)
    for v in ('HSV', 'OV', 'IV'):
        if not re.search(f'(?<![A-Z]){v}(?![A-Z])', u):
            continue
        c['variant'] = v
        break
    else:
        c.pop('variant', None)
    has_ba = bool(re.search('(?<![A-Z])BA(?![A-Z])|WINDING|권선|보빈아세이', u))
    has_ca = bool(re.search('(?<![A-Z])CA(?![A-Z])|압입|코일아세이', u))
    if has_ba and has_ca:
        c.pop('process', None)
    elif has_ba:
        c['process'] = 'BA'
    elif has_ca:
        c['process'] = 'CA'
    elif re.search('\\bBS\\b|STITCHING|스티칭', u):
        c['process'] = 'STITCHING'
    elif '사출' in text:
        c['process'] = 'INJECTION'
    metric = 'OVERVIEW'
    overview_words = ['현황', '분석', '비교', '불량', '공정별']
    if not any((word in text for word in overview_words)):
        for keys, m in (['보압'], 'HOLDING_PRESSURE'), (['쿠션', '전환위치'], 'CUSHION'), (['중량', '무게'], 'BOBBIN_WEIGHT'), (['생산량', '수량'], 'PRODUCTION_QTY'), (['냉각'], 'COOLING_TIME'), (['압력1', '압력 1', '1차 압력', '사출압력 1'], 'INJECTION_PRESSURE_1'):
            if not any((k in text for k in keys)):
                continue
            metric = m
            break
    c['metric'] = metric
    from datetime import date
    date_patterns = [('(?<!\\d)(20\\d{2})\\s*년\\s*(\\d{1,2})\\s*월\\s*(\\d{1,2})\\s*일?', 'ymd'), ('(?<!\\d)(20\\d{2})[./-](\\d{1,2})[./-](\\d{1,2})(?!\\d)', 'ymd'), ('(?<!\\d)(\\d{2})(\\d{2})(\\d{2})(?!\\d)', 'yymmdd'), ('(?<!\\d)(\\d{1,2})[./-](\\d{1,2})(?!\\d)', 'md'), ('(?<!\\d)(\\d{2})(\\d{2})(?!\\d)', 'mmdd')]
    for pattern, date_format in date_patterns:
        dm = re.search(pattern, text)
        if not dm:
            continue
        try:
            if date_format == 'ymd':
                year, month, day = map(int, dm.groups())
            elif date_format == 'yymmdd':
                yy, month, day = map(int, dm.groups())
                year = 2000 + yy
            elif date_format == 'md':
                month, day = map(int, dm.groups())
                year = 2026
            else:
                month, day = map(int, dm.groups())
                year = 2026
            c['date'] = date(year, month, day).isoformat()
            c['date_query'] = dm.group(0)
            break
        except ValueError:
            pass
    from lot_lookup import find_lot_date
    lot_match = find_lot_date(text)
    if lot_match:
        c['lot_query'] = lot_match['source_value']
        c['lot_date'] = lot_match['date']
    return c

def process_summary_answer(rows: list[dict], ctx: dict[str, Any]) -> str:
    process_names = {'INJECTION': '사출', 'STITCHING': 'BS / 스티칭', 'BA': 'BA / 보빈아세이', 'CA': 'CA / 코일아세이', 'BA_CA': 'BA·CA 복합 기록', 'PATROL': '공정검사'}
    metric_names = {'PRODUCTION_QTY': '생산수량', 'BOBBIN_LOT': '보빈 LOT', 'SET_UP_NG': '셋업 불량수량', 'DEPTH_NG': '깊이 불량수량', 'RESISTANCE_NG': '저항 불량수량', 'WORK_HOURS': '작업시간', 'TIMELINE_EVENT': '작업·설비 이력', 'BOBBIN_WEIGHT': '보빈 중량', 'HOLDING_PRESSURE': '보압', 'CUSHION': '쿠션', 'WELD_NG': '용접불량', 'VISION1_NG': '비전 1차 불량', 'VISION2_NG': '비전 2차 불량', 'VISION3_NG': '비전 3차 불량', 'LOWER_CASE_MIX_NG': '로어케이스 혼입불량', 'WITHSTAND_VOLTAGE_NG': '내전압불량', 'FALSE_REJECT': '가성불량', 'CONFIRMED_NG': '진성불량', 'LEAD_PIN_LOT': '리드핀 LOT', 'LEAD_PIN_INSERT': '리드핀 삽입 LOT', 'PROGRAM': '프로그램', 'TURN': '권선 턴수', 'EVENT': '작업·설비 이력', 'PRODUCTION_QTY_DAY': '주간 생산수량', 'PRODUCTION_QTY_NIGHT': '야간 생산수량', 'WORK_HOURS_DAY': '주간 작업시간', 'WORK_HOURS_NIGHT': '야간 작업시간'}
    title = f'{ctx.get('date', '조회 기간 전체')} · iMEB3 {ctx.get('variant', '전체 모델')}'
    lines = [title, '공정별 기록']
    event_metrics = {'EVENT', 'TIMELINE_EVENT'}
    for process, name in process_names.items():
        records = [r for r in rows if r.get('process') == process]
        if not records:
            continue
        lines.append(f'\n■ {name}')
        seen = set()
        normal_lines = []
        event_lines = []
        for r in records:
            key = r.get('date'), r.get('variant'), r.get('metric'), str(r.get('value')), r.get('unit')
            if key in seen:
                continue
            seen.add(key)
            metric_code = str(r.get('metric') or '').upper()
            metric = metric_names.get(metric_code, metric_code or '기록 항목')
            value = r.get('value')
            if isinstance(value, (int, float)):
                value = f'{value:,}'
            status = ' ✓' if r.get('value_source') == 'HUMAN_VERIFIED' else ''
            if metric_code in event_metrics:
                event_lines.append(f'- {value} {r.get('unit', '')}{status}')
                continue
            normal_lines.append(f'- {metric}: {value} {r.get('unit', '')}{status}')
            continue
        if normal_lines:
            lines.append('생산·품질 기록')
            lines.extend(normal_lines)
        if not event_lines:
            continue
        lines.append('작업·설비 이력')
        lines.extend(event_lines)
        continue
    if len(lines) == 2:
        return '해당 조건에서 확인된 공정 기록이 없습니다.'
    return '\n'.join(lines)

def fallback_answer(message: str, rows: list[dict], ctx: dict[str, Any]) -> str:
    if ctx.get('metric') in ('OVERVIEW', 'PRODUCTION_QTY'):
        if (ctx.get('metric') == 'OVERVIEW' and not ctx.get('variant')
                and not ctx.get('process') and not ctx.get('date')):
            summary = build_summary(rows)
            metrics = summary['metrics']
            fmt = lambda value: f'{value:,.1f}' if isinstance(value, (int, float)) else '자료 없음'
            return '\n'.join([
                'Firestore 제조 데이터 요약',
                f"전체 기록 {summary['total_records']:,}건 · 생산량 수치 기록 {summary['count']:,}건",
                f"기간 {summary['period']}",
                f"생산량 평균 {fmt(metrics['average'])} EA · 최소 {fmt(metrics['min'])} EA · 최대 {fmt(metrics['max'])} EA",
                f"최근 추세 {summary['trend']}",
                '※ 제조 공정별 생산량은 중복 합산하지 않았습니다.'
            ])
        return process_summary_answer(rows, ctx)
    vr = ctx.get('variant')
    metric = ctx.get('metric')
    if metric == 'BOBBIN_WEIGHT':
        if any((k in message for k in ('이상', '이탈', '불량'))):
            spec = {'IV': (11.0, 11.6), 'OV': (12.0, 12.6), 'HSV': (12.1, 12.7)}
            bad = [r for r in rows if r.get('variant') in spec and isinstance(r.get('value'), (int, float)) and not spec[r['variant']][0] <= r['value'] <= spec[r['variant']][1]]
            if bad:
                return 'Bobbin 중량 SPEC 이탈이 확인됩니다. ' + '; '.join((f'{r.get('run_id')} {r.get('variant')} {r.get('value'):.3f}g' for r in bad))
            return '현재 구조화된 Bobbin 중량 DATA에서는 SPEC 이탈 RUN이 확인되지 않습니다.'
    if rows:
        sample = '; '.join((f'{r.get('date')} {r.get('variant')} {r.get('metric')}={r.get('value')} {r.get('unit', '')}' for r in rows[:12]))
        return f'현재 구조화된 제조 DATA에서 {len(rows)}건을 조회했습니다. {sample}'
    return '현재 구조화된 제조 DATA에서 질문과 직접 일치하는 Evidence를 찾지 못했습니다. 없는 값은 생성하지 않습니다.'

def conversation_history_messages(history: list[dict] | None) -> list[dict[str, str]]:
    messages = []
    for item in (history or [])[-8:]:
        role = item.get('role') if isinstance(item, dict) else None
        content = item.get('content') if isinstance(item, dict) else None
        if role not in ('user', 'assistant') or not isinstance(content, str) or not content.strip():
            continue
        messages.append({'role': role, 'content': content.strip()[:1500]})
    return messages

def openai_answer(message: str, rows: list[dict], ctx: dict[str, Any], history: list[dict] | None = None) -> tuple[str, str]:
    local_answer = fallback_answer(message, rows, ctx)
    if not rows and not history:
        return local_answer, 'LOCAL_ONLY'
    analysis_keywords = ('분석', '비교', '추세', '원인', '상관', '왜', '평가', '개선', '예측', '차이')
    if not history and not any((keyword in message for keyword in analysis_keywords)):
        return local_answer, 'LOCAL_ONLY'
    ai_answer, provider = codysay_answer(message, rows, ctx, history)
    if provider not in ('ANTHROPIC_MESSAGES', 'OPENAI_RESPONSES', 'CODYSAY_CHAT_COMPLETIONS', 'CODYSAY_FUNCTION_CALLING') or not ai_answer.strip():
        return local_answer, provider
    return local_answer + '\n\n■ AI 추가 분석\n' + ai_answer.strip(), provider

MANUFACTURING_TOOLS = [{'type': 'function', 'function': {'name': 'get_manufacturing_records', 'description': 'iMEB3 제조 데이터에서 날짜, 제품 모델, 공정에 해당하는 생산수량과 불량 및 작업 기록을 조회한다.', 'parameters': {'type': 'object', 'properties': {'date': {'type': 'string', 'description': '생산일자 YYYY-MM-DD'}, 'variant': {'type': 'string', 'enum': ['IV', 'OV', 'HSV', 'ALL'], 'description': '제품 모델'}, 'process': {'type': 'string', 'enum': ['BA', 'CA', 'INJECTION', 'STITCHING', 'PATROL', 'ALL'], 'description': '조회할 제조 공정'}}, 'required': ['date', 'variant', 'process']}}}]

def codysay_answer(message: str, rows: list[dict], ctx: dict[str, Any], history: list[dict] | None = None) -> tuple[str, str]:
    history_messages = conversation_history_messages(history)
    history_text = '\n'.join(f"{item['role']}: {item['content']}" for item in history_messages)
    anthropic_key = os.getenv('ANTHROPIC_API_KEY', '').strip()
    if anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            model = os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-6')
            max_tokens = int(os.getenv('ANTHROPIC_MAX_OUTPUT_TOKENS', os.getenv('OPENAI_MAX_OUTPUT_TOKENS', '2000')))
            summary = build_summary(rows)
            evidence = [{'date': r.get('date'), 'variant': r.get('variant'), 'process': r.get('process'), 'metric': r.get('metric'), 'value': r.get('value'), 'unit': r.get('unit'), 'verification_status': r.get('verification_status')} for r in rows[:20]]
            instructions = SYSTEM + '\n\n[사용자 데이터 요약]\n' + json.dumps(summary, ensure_ascii=False) + '\n\n[질문 관련 DATA]\n' + json.dumps(evidence, ensure_ascii=False) + '\nHUMAN_VERIFIED, SOURCE_READ, DERIVED 등 내부 상태명은 출력하지 마라. 사람 확인값은 ✓, 계산값은 ≈로 표시하고, 기존 조회 수치는 반복하지 마라. 기존 제조 데이터 조회 결과를 반복하지 말고 추가 분석만 작성하라. 분석은 최대 3문장, 250자 이내로 작성하라. 내부 레코드 ID, run_id, 영문 필드명은 출력하지 마라. 근거 없는 원인이나 불량률은 추정하지 마라. BA와 CA는 연속 공정이므로 생산수량을 합산하여 총생산량이라고 표현하지 마라.'
            response = client.messages.create(model=model, max_tokens=max_tokens, system=instructions, messages=history_messages + [{'role': 'user', 'content': message}])
            answer = ''.join(block.text for block in response.content if getattr(block, 'type', '') == 'text').strip()
            if answer:
                print('Anthropic Messages API response length:', len(answer))
                return answer, 'ANTHROPIC_MESSAGES'
            return fallback_answer(message, rows, ctx), 'FALLBACK_EMPTY_ANSWER'
        except Exception as e:
            import traceback
            print('Anthropic API error type:', type(e).__name__)
            print('Anthropic API error detail:', str(e)[:1000])
            for frame in traceback.extract_tb(e.__traceback__):
                if frame.filename.endswith('main.py'):
                    print('  line:', frame.lineno, '| function:', frame.name)
            return fallback_answer(message, rows, ctx), 'FALLBACK_AI_ERROR'
    key = os.getenv('OPENAI_API_KEY', '').strip()
    if not key:
        return fallback_answer(message, rows, ctx), 'FALLBACK_NO_KEY'
    try:
        from openai import OpenAI
        base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1').strip()
        client = OpenAI(api_key=key, base_url=base_url) if base_url else OpenAI(api_key=key)
        model = os.getenv('OPENAI_MODEL', 'gpt-5-mini')
        max_completion_tokens = int(os.getenv('OPENAI_MAX_OUTPUT_TOKENS', '2000'))
        summary = build_summary(rows)
    except Exception as e:
        import traceback
        print('AI API setup error type:', type(e).__name__)
        print('AI API setup error detail:', str(e)[:1000])
        print('AI API setup error location:')
        for frame in traceback.extract_tb(e.__traceback__):
            if frame.filename.endswith('main.py'):
                print('  line:', frame.lineno, '| function:', frame.name)
        return fallback_answer(message, rows, ctx), 'FALLBACK_AI_ERROR'
    try:
        evidence = [{'date': r.get('date'), 'variant': r.get('variant'), 'process': r.get('process'), 'metric': r.get('metric'), 'value': r.get('value'), 'unit': r.get('unit'), 'verification_status': r.get('verification_status')} for r in rows[:20]]
        instructions = SYSTEM + '\n\n[사용자 데이터 요약]\n' + json.dumps(summary, ensure_ascii=False) + '\n\n[질문 관련 DATA]\n' + json.dumps(evidence, ensure_ascii=False) + '\nHUMAN_VERIFIED, SOURCE_READ, DERIVED 등 내부 상태명은 출력하지 마라. 사람 확인값은 ✓, 계산값은 ≈로 표시하고, 기존 조회 수치는 반복하지 마라.' + '\n기존 제조 데이터 조회 결과를 반복하지 말고 추가 분석만 작성하라.' + '\n분석은 최대 3문장, 250자 이내로 작성하라.' + '\n내부 레코드 ID, run_id, 영문 필드명은 출력하지 마라.' + '\n원본 수치와 계산값을 구분하고, 근거 없는 원인이나 불량률은 추정하지 마라.' + '\nBA와 CA는 연속 공정이므로 생산수량을 합산하여 총생산량이라고 표현하지 마라.' + '\n서로 다른 공정의 불량수량을 합산하여 전체 불량률을 계산하지 마라. 공정별 수량 차이는 재공품 및 공정 흐름 확인 없이 손실로 단정하지 마라.'
        if 'codyssey.kr' not in base_url.lower():
            prompt = (f'[이전 대화 문맥]\n{history_text}\n\n' if history_text else '') + f'[현재 질문]\n{message}'
            resp = client.responses.create(model=model, instructions=instructions, input=prompt, max_output_tokens=max_completion_tokens)
            answer = (resp.output_text or '').strip()
            if not answer:
                return fallback_answer(message, rows, ctx), 'FALLBACK_EMPTY_ANSWER'
            print('OpenAI Responses API response length:', len(answer))
            return answer, 'OPENAI_RESPONSES'
        ai_start = time.perf_counter()
        chat_messages = [{'role': 'system', 'content': instructions}, *history_messages, {'role': 'user', 'content': message}]
        resp = client.chat.completions.create(model=model, messages=chat_messages, max_completion_tokens=max_completion_tokens)
        print('Codyssey API elapsed seconds:', round(time.perf_counter() - ai_start, 2))
        tool_calls = resp.choices[0].message.tool_calls or []
        if tool_calls:
            print('GPT tool calls:', len(tool_calls))
            for call in tool_calls:
                if call.function.name != 'get_manufacturing_records':
                    return ('', 'FALLBACK_UNKNOWN_TOOL')
                args = json.loads(call.function.arguments)
                date = args.get('date', '')
                variant = args.get('variant', 'ALL')
                process = args.get('process', 'ALL')
                if variant not in ('IV', 'OV', 'HSV', 'ALL'):
                    return ('', 'FALLBACK_INVALID_TOOL')
                if process not in ('BA', 'CA', 'INJECTION', 'STITCHING', 'PATROL', 'ALL'):
                    return ('', 'FALLBACK_INVALID_TOOL')
                result = get_manufacturing_records(date=date, variant=variant, process=process)
                print('GPT tool name:', call.function.name)
                print('GPT tool result count:', len(result))
            tool_messages = [{'role': 'system', 'content': instructions}, *history_messages, {'role': 'user', 'content': message}, resp.choices[0].message.model_dump(exclude_none=True)]
            for call in tool_calls:
                args = json.loads(call.function.arguments)
                result = get_manufacturing_records(date=args.get('date', ''), variant=args.get('variant', 'ALL'), process=args.get('process', 'ALL'))
                safe_result = [{'date': r.get('date'), 'variant': r.get('variant'), 'process': r.get('process'), 'metric': r.get('metric'), 'value': r.get('value'), 'unit': r.get('unit'), 'value_source': r.get('value_source')} for r in result[:40]]
                tool_messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': json.dumps(safe_result, ensure_ascii=False, default=str)})
                continue
            final_resp = client.chat.completions.create(model=model, messages=tool_messages, max_completion_tokens=max_completion_tokens)
            final_answer = (final_resp.choices[0].message.content or '').strip()
            if not final_answer:
                return ('', 'FALLBACK_EMPTY_TOOL_ANSWER')
            return final_answer, 'CODYSAY_FUNCTION_CALLING'
    except Exception as e:
        import traceback
        print('Codyssey API error type:', type(e).__name__)
        print('Codyssey API error detail:', str(e)[:1000])
        print('Codyssey API error location:')
        for frame in traceback.extract_tb(e.__traceback__):
            if frame.filename.endswith('main.py'):
                print('  line:', frame.lineno, '| function:', frame.name)
        return fallback_answer(message, rows, ctx), 'FALLBACK_AI_ERROR'
    answer = resp.choices[0].message.content or ''
    print('Codyssey API response length:', len(answer))
    print('Codyssey API finish reason:', resp.choices[0].finish_reason)
    if not answer.strip():
        print('Codyssey API returned empty text; using evidence-based fallback')
        return fallback_answer(message, rows, ctx), 'FALLBACK_EMPTY_ANSWER'
    return answer, 'CODYSAY_CHAT_COMPLETIONS'

def get_manufacturing_records(date: str, variant: str, process: str) -> list[dict]:
    rows = all_docs('data')
    if date:
        rows = [r for r in rows if r.get('date') == date]
    if variant in ('IV', 'OV', 'HSV'):
        rows = [r for r in rows if r.get('variant') == variant]
    if process != 'ALL':
        rows = [r for r in rows if r.get('process') == process]
    return rows

@app.post('/api/chat')
def chat(body: ChatIn):
    ctx = infer_graph_context(body.message, body.context)
    all_rows = all_docs('data')
    maybe_create_daily_backup(all_rows)
    workbook = load_workbook_evidence()
    if workbook.get('available'):
        all_rows = all_rows + workbook.get('production', []) + workbook.get('inspection_lots', [])
    rows = all_rows
    vr = ctx.get('variant')
    if vr in ('IV', 'OV', 'HSV'):
        rows = [r for r in rows if r.get('variant') == vr]
    metric = ctx.get('metric')
    if not ctx.get('variant') and not ctx.get('process'):
        vr = None
    if metric != 'OVERVIEW':
        rows = [r for r in rows if str(r.get('metric') or '').upper() == str(metric).upper()]
    process = ctx.get('process')
    if process:
        rows = [r for r in rows if r.get('process') == process]
    date = ctx.get('date')
    if date:
        rows = [r for r in rows if r.get('date') == date]
    if ctx.get('date') and ctx.get('variant') in ('IV', 'OV', 'HSV') and DB_MODE == 'firestore' and ACTIVE_DATA_SOURCE == 'firestore':
        try:
            from mcp_bridge import fetch_manufacturing_via_mcp
            mcp_result = fetch_manufacturing_via_mcp(date=ctx['date'], variant=ctx['variant'], process=ctx.get('process') or '')
            if 'error' not in mcp_result:
                mcp_rows = mcp_result.get('records', [])
                if ctx.get('metric') != 'OVERVIEW':
                    mcp_rows = [r for r in mcp_rows if str(r.get('metric') or '').upper() == str(ctx.get('metric')).upper()]
                rows = mcp_rows
        except Exception as e:
            print('MCP 조회 실패, 기존 조회 사용:', type(e).__name__)
    conv = get('conversations', body.conversation_id) if body.conversation_id else None
    if not conv:
        cid = str(uuid.uuid4())
        conv = {'id': cid, 'title': body.message[:28] or '새 대화', 'messages': [], 'context': ctx, 'created_at': now(), 'updated_at': now()}
    history = conv.get('messages', [])
    is_lot_trace = bool(ctx.get('lot_query') and ctx.get('lot_date'))
    graph_date = ctx.get('lot_date') or ctx.get('date')
    lot_graph = None
    lot_rows = all_rows
    explicit_variant = next((v for v in ('HSV', 'OV', 'IV') if re.search(f'(?<![A-Z]){v}(?![A-Z])', body.message.upper())), None)
    if is_lot_trace:
        from lot_trace import trace_lot
        answer = trace_lot(lot_rows, ctx['lot_query'], ctx['lot_date'], explicit_variant)
        provider = 'LOCAL_LOT_EVIDENCE'
    else:
        answer, provider = openai_answer(body.message, rows, ctx, history)
    if DB_MODE in ('firestore', 'memory'):
        from lot_normalize import find_lot_evidence
        graph_variant = explicit_variant or ctx.get('variant')
        matches = find_lot_evidence(lot_rows, graph_date, graph_variant) if graph_date else []
        graph_nodes, graph_edges = [], []
        role_lane = {'RAW_MATERIAL_LOT': 'RAW_MATERIAL', 'RAW_LOT_DAY': 'RAW_MATERIAL', 'RAW_LOT_NIGHT': 'RAW_MATERIAL', 'BOBBIN_LOT': 'BOBBIN', 'BOBBIN_LOT_RAW': 'BOBBIN', 'BOBBIN_PRODUCTION_DATE': 'BOBBIN', 'LEAD_PIN_RECEIPT_DATE': 'LEAD_PIN', 'LEAD_PIN_LOT': 'LEAD_PIN', 'LEAD_PIN_INSERT': 'STITCHING', 'UPPER_CASE_LOT': 'CA', 'LOWER_CASE_LOT': 'CA', 'WIRE_LOT': 'WIRE', 'LOT': 'FINAL_INSPECTION'}
        process_lane = {'INJECTION': 'BOBBIN', 'STITCHING': 'STITCHING', 'BA': 'BA', 'BA_WINDING': 'BA', 'CA': 'CA', 'CA_PRESS_FIT': 'CA', 'FINAL_INSPECTION': 'FINAL_INSPECTION', 'INSPECTION': 'FINAL_INSPECTION'}
        process_aliases = {'BA_WINDING': 'BA', 'CA_PRESS_FIT': 'CA'}
        canonical_process = lambda value: process_aliases.get(str(value or '').upper(), str(value or '').upper())
        qty_metrics = {'PRODUCTION_QTY', 'PRODUCTION_QTY_DAY', 'PRODUCTION_QTY_NIGHT'}
        event_by_key = {}
        for ix, item in enumerate(matches):
            record = item['record']
            source_role = role_lane.get(item['lot_role'], process_lane.get(record.get('process'), 'BA'))
            source_id = f'lot-{ix}'
            graph_nodes.append({'id': source_id, 'kind': 'lot', 'role': source_role, 'date': (item['normalization'].get('normalized_dates') or [record.get('date')])[0], 'event_date': record.get('date'), 'variant': record.get('variant'), 'run_id': record.get('run_id'), 'metric': item['lot_role'], 'source_record_id': record.get('id'), 'label': str(record.get('value') or item['lot_role']), 'quantity': None, 'status': item['normalization'].get('normalization_status')})
            event_key = record.get('date'), record.get('variant'), canonical_process(record.get('process'))
            if event_key not in event_by_key:
                event_id = f'event-{len(event_by_key)}'
                event_by_key[event_key] = event_id
                qtys = [r.get('value') for r in lot_rows if r.get('date') == record.get('date') and r.get('variant') == record.get('variant') and canonical_process(r.get('process')) == canonical_process(record.get('process')) and str(r.get('metric', '_')).upper() in qty_metrics and str(r.get('value', '_')).replace(',', '').strip() not in {'0', '0.0'}]
                quantity = qtys[0] if len(set(map(str, qtys))) == 1 and qtys else None
                graph_nodes.append({'id': event_id, 'kind': 'event', 'role': process_lane.get(canonical_process(record.get('process')), source_role), 'date': record.get('date'), 'variant': record.get('variant'), 'label': record.get('process') or '공정 기록', 'quantity': quantity, 'status': 'SOURCE_READ'})
            graph_edges.append({'from': source_id, 'to': event_by_key[event_key], 'status': 'LOT_REFERENCE_ONLY', 'priority': 3})
            continue
        producer_by_role = {'BOBBIN': 'INJECTION', 'STITCHING': 'STITCHING', 'FINAL_INSPECTION': 'CA'}
        for lot_node in graph_nodes:
            if lot_node.get('kind') != 'lot':
                continue
            source = next((r for r in lot_rows if r.get('id') == lot_node.get('source_record_id')), None)
            if source:
                for event in graph_nodes:
                    if event.get('kind') == 'event' and event.get('date') == source.get('date') and event.get('variant') == source.get('variant') and event.get('role') == process_lane.get(canonical_process(source.get('process'))):
                        graph_edges.append({'from': lot_node['id'], 'to': event['id'], 'status': 'LOT_REFERENCE_ONLY'})
            producer = producer_by_role.get(lot_node.get('role'))
            if not producer:
                continue
            lot_day = lot_node.get('date')
            producer_rows = [r for r in lot_rows if r.get('date') == lot_day and r.get('variant') == lot_node.get('variant') and canonical_process(r.get('process')) == producer and str(r.get('metric', '_')).upper() in qty_metrics and str(r.get('value', '_')).replace(',', '').strip() not in {'0', '0.0'}]
            for src in producer_rows:
                event = next((n for n in graph_nodes if n.get('kind') == 'event' and n.get('date') == lot_day and n.get('variant') == src.get('variant') and n.get('role') == process_lane.get(producer)), None)
                if not event:
                    continue
                if any(e.get('from') == event['id'] and e.get('to') == lot_node['id'] for e in graph_edges):
                    continue
                graph_edges.append({'from': event['id'], 'to': lot_node['id'], 'status': 'LOT_DATE_CANDIDATE_UNVERIFIED', 'priority': 2})
        for record in lot_rows:
            if record.get('process') == 'FINAL_INSPECTION' or record.get('metric') == 'INSPECTION_PRODUCT_LOT':
                if record.get('date') != graph_date and record.get('inspection_date') != graph_date:
                    continue
                if graph_variant in ('IV', 'OV', 'HSV') and record.get('variant') != graph_variant:
                    continue
                inspection_day = record.get('inspection_date') or record.get('date')
                role = 'FINAL_INSPECTION'
                event_key = inspection_day, record.get('variant'), role
                if event_key not in event_by_key:
                    event_id = f'inspection-{len(event_by_key)}'
                    event_by_key[event_key] = event_id
                    graph_nodes.append({'id': event_id, 'kind': 'event', 'role': role, 'date': inspection_day, 'variant': record.get('variant'), 'label': '최종검사 · 날짜 기록', 'quantity': record.get('value') or (record.get('boxes') * record.get('box_size_ea') if isinstance(record.get('boxes'), int) else None), 'status': 'DATE_CONTEXT_ONLY'})
                lot_code = record.get('lot_code') or record.get('value')
                graph_nodes.append({'id': f'inspection-lot-{len(graph_nodes)}', 'kind': 'lot', 'role': role, 'date': record.get('date'), 'event_date': inspection_day, 'variant': record.get('variant'), 'metric': record.get('metric'), 'source_record_id': record.get('id'), 'label': str(lot_code), 'quantity': None if record.get('training_inspection') else (record.get('boxes') * record.get('box_size_ea') if isinstance(record.get('boxes'), int) else None), 'status': 'TRAINING_EXCLUDED' if record.get('training_inspection') else 'LOT_REFERENCE_ONLY'})
                continue
            if record.get('date') != graph_date:
                continue
            if graph_variant in ('IV', 'OV', 'HSV') and record.get('variant') != graph_variant:
                continue
            if str(record.get('metric', '_')).upper() not in qty_metrics:
                continue
            if str(record.get('metric', '_')).upper().startswith('PRODUCTION_QTY') and str(record.get('value', '_')).replace(',', '').strip() in {'0', '0.0'}:
                continue
            event_key = record.get('date'), record.get('variant'), canonical_process(record.get('process'))
            if event_key in event_by_key:
                continue
            event_id = f'date-context-{len(event_by_key)}'
            event_by_key[event_key] = event_id
            graph_nodes.append({'id': event_id, 'kind': 'event', 'role': process_lane.get(canonical_process(record.get('process')), 'BA'), 'date': record.get('date'), 'variant': record.get('variant'), 'label': (record.get('process') or '공정') + ' · 날짜 기록', 'quantity': record.get('value'), 'status': 'DATE_CONTEXT_ONLY'})
        assembly_by_day = {}
        for record in lot_rows:
            if canonical_process(record.get('process')) in {'BA', 'CA'}:
                if str(record.get('metric', '_')).upper() not in qty_metrics or str(record.get('value', '_')).replace(',', '').strip() in {'0', '0.0'}:
                    continue
                key = record.get('date'), record.get('variant')
                group = assembly_by_day.setdefault(key, {'BA': 0, 'CA': 0})
                group[canonical_process(record.get('process'))] += 1
        for (day, v), counts in assembly_by_day.items():
            if counts['BA'] and counts['CA']:
                ba_id = event_by_key.get((day, v, 'BA'))
                ca_id = event_by_key.get((day, v, 'CA'))
                if ba_id and ca_id:
                    graph_edges.append({'from': ba_id, 'to': ca_id, 'status': 'ASSEMBLY_SET_REVIEW', 'priority': 1})
        lot_graph = {'storage': ACTIVE_DATA_SOURCE, 'read_only': True, 'lot_code': ctx.get('lot_query') or ctx.get('date_query'), 'lot_date': graph_date, 'anchor_date': ctx.get('date') or graph_date, 'variant': graph_variant, 'nodes': graph_nodes, 'edges': graph_edges}
    conv['messages'].append({'role': 'user', 'content': body.message, 'attachments': body.attachments})
    conv['messages'].append({'role': 'assistant', 'content': answer})
    conv['context'] = ctx
    conv['updated_at'] = now()
    put('conversations', conv['id'], conv)
    response = {'conversation_id': conv['id'], 'answer': answer, 'graph_context': ctx, 'storage': ACTIVE_DATA_SOURCE, 'ai_provider': provider}
    if lot_graph is not None:
        response['lot_graph'] = lot_graph
    return response

# WARNING: Decompyle incomplete
