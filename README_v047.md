# v0.47 — Frontend ↔ FastAPI 연결 수정

## 변경 범위
- 아키텍처 변경 없음: Vercel Frontend → Render FastAPI → Firestore Adapter + AI Provider.
- `file://` 로컬 개발 시 브라우저 Origin=`null`을 FastAPI CORS에서 허용.
- CORS credentials를 사용하지 않는 현재 REST 호출과 일치하도록 `allow_credentials=False`.
- Frontend가 `/api/health`를 먼저 확인한 뒤 `/api/chat` 호출.
- 실패 문구를 `Backend 접근/CORS 실패`, `Backend ON · /api/chat 오류`, `Backend 응답 오류`로 분리.
- Firestore/Codyssey 연결은 이번 수정 범위가 아니며 제거하지 않음.

## 확인 순서
1. 기존 v0.46 터미널은 Ctrl+C로 종료.
2. v0.47 `START_CORE.bat` 실행.
3. `http://127.0.0.1:8000/docs`에서 version 0.47.0 확인.
4. `frontend/index.html` 실행.
5. `보빈무게 이상있는날 보여줘` 입력.
6. 답변 하단이 `Backend 연결 · memory · AI Provider NOT_FIXED`이면 연결 PASS.
