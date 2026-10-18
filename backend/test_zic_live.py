from app.main import all_docs
from lot_trace import trace_lot

rows = all_docs("data")

print("전체 기록:", len(rows))
print("9월 3일 생산 기록:", len([
    r for r in rows
    if r.get("date") == "2026-09-03"
]))

print("9/10 IV BA Bobbin LOT:")
for r in rows:
    if (
        r.get("date") == "2026-09-10"
        and r.get("variant") == "IV"
        and r.get("process") == "BA"
        and r.get("metric") == "BOBBIN_LOT"
    ):
        print(repr(r.get("value")))

print("LOT 정규화 모듈의 실제 함수:")
import lot_normalize
print([name for name in dir(lot_normalize) if not name.startswith("_")])

print("ZIC 추적 결과:")
print(trace_lot(rows, "ZIC", "2026-09-03"))
