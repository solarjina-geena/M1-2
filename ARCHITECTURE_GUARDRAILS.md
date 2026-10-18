# v0.46 Architecture Guardrails

## 최종 구조 — 변경하지 않음
Vercel Vanilla Frontend → Render FastAPI → Firestore + AIProvider(Codyssey 우선 검토)

## Manufacturing Common Core — 외부 서비스와 독립
SOURCE_DOCUMENT → EVIDENCE → FACT → Manufacturing Timeline → Canonical RUN
→ LOT Genealogy / Quality Event → AI Candidate → Review → HUMAN_VERIFIED
→ Correction Knowledge → 재활용

## Canonical RUN
`YYYYMMDD{D|N}{sequence}` (예: `20260918D1`). 날짜만으로 생산 Event를 식별하지 않는다.
원본 LOT/source text는 별도 보존한다.

## 이번 수정의 의미
아키텍처를 단순화/삭제한 것이 아니라 **설치와 실행 단계를 분리**했다.
- Core: FastAPI/Pydantic/dotenv만으로 API/Swagger/Context 검증
- Firestore Adapter: 별도 설치/환경변수 연결
- AI Provider Adapter: Codyssey 규격 확정 후 연결

Firestore, Render/Vercel 분리, reviews/evidence, conversations, Provider 계층은 제거하지 않는다.
