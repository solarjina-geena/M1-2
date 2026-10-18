from app.main import all_docs

rows = all_docs("data")
lot_rows = [
    r for r in rows
    if "LOT" in str(r.get("metric", "")).upper()
    or "INSERT" in str(r.get("metric", "")).upper()
]

print("LOT 관련 기록:", len(lot_rows))

for r in lot_rows[:40]:
    print(
        r.get("date"),
        r.get("variant"),
        r.get("process"),
        r.get("metric"),
        repr(r.get("value"))
    )
