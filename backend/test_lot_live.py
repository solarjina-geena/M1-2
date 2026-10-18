from app.main import all_docs
from lot_trace import trace_lot

rows = all_docs("data")
date_rows = [r for r in rows if r.get("date") == "2026-09-04"]

print("Firestore 전체:", len(rows))
print("9월 4일 기록:", len(date_rows))
print("LOT 추적 함수 직접 실행:")
print(trace_lot(rows, "ZID", "2026-09-04"))
