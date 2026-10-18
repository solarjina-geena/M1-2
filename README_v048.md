# v0.48 — Recovered/HUMAN_VERIFIED Migration

- v0.47 구조 유지
- 복구/검증된 제조 DATA를 idempotent migration batch로 추가
- HUMAN_VERIFIED > SOURCE_READ 우선순위 보호
- BLANK/UNCERTAIN 값을 임의 숫자로 변환하지 않음
- POST /api/migration/recovered-v1 : migration 실행
- GET /api/migration/status : 결과 확인
- Firestore credential이 있으면 Firestore, 없으면 memory adapter에 실행

## Batch
RECOVERED_VERIFIED_V1
