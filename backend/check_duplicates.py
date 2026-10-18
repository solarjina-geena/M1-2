from app.main import DB_MODE, all_docs

if DB_MODE != "firestore":
    print("Firestore 미연결: 조회 중단")
else:
    records = all_docs("data")

    for process in ["BA", "CA"]:
        print(f"\n===== {process} 생산수량 기록 =====")

        for r in records:
            if (
                r.get("date") == "2026-09-10"
                and str(r.get("variant", "")).upper() == "OV"
                and str(r.get("process", "")).upper() == process
                and r.get("metric") == "PRODUCTION_QTY"
            ):
                print({
                    "id": r.get("id"),
                    "run_id": r.get("run_id"),
                    "lot_id": r.get("lot_id"),
                    "value": r.get("value"),
                    "value_source": r.get("value_source"),
                    "evidence_id": r.get("evidence_id"),
                })
