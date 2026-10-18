from mcp.server.fastmcp import FastMCP

mcp = FastMCP("iMEB3 Manufacturing Traceability")


@mcp.tool()
def server_status() -> str:
    """제조 데이터 MCP 서버의 연결 상태를 확인합니다."""
    return "iMEB3 제조 데이터 MCP 서버 정상 연결"


@mcp.tool()
def manufacturing_db_status() -> dict:
    """제조 데이터베이스 연결 상태와 기록 수를 확인합니다. 읽기 전용입니다."""
    from app.main import DB_MODE, all_docs

    if DB_MODE != "firestore":
        return {
            "connected": False,
            "storage": DB_MODE,
            "message": "Firestore 미연결. DEMO 데이터를 실제 제조 데이터로 사용하지 않습니다.",
        }

    records = all_docs("data")

    return {
        "connected": True,
        "storage": "firestore",
        "record_count": len(records),
        "message": "Firestore 제조 데이터 조회 성공",
    }

@mcp.tool()
def get_manufacturing_records(
    date: str,
    variant: str,
    process: str = "",
) -> dict:
    """날짜, 제품 Variant, 공정으로 제조 기록을 조회합니다. 읽기 전용입니다."""
    from app.main import DB_MODE, all_docs

    if DB_MODE != "firestore":
        return {
            "error": "Firestore 미연결",
            "records": [],
        }

    variant = variant.strip().upper()
    process = process.strip().upper()

    if variant not in {"IV", "OV", "HSV"}:
        return {
            "error": "variant는 IV, OV, HSV 중 하나여야 합니다.",
            "records": [],
        }

    records = [
        record
        for record in all_docs("data")
        if record.get("date") == date
        and str(record.get("variant", "")).upper() == variant
        and (
            not process
            or str(record.get("process", "")).upper() == process
        )
    ]

    duplicate_candidates = []
    groups = {}

    for record in records:
        key = (
            record.get("date"),
            record.get("variant"),
            record.get("process"),
            record.get("metric"),
            str(record.get("value")),
        )
        groups.setdefault(key, []).append(record)

    for key, group in groups.items():
        if len(group) > 1:
            duplicate_candidates.append({
                "date": key[0],
                "variant": key[1],
                "process": key[2],
                "metric": key[3],
                "value": key[4],
                "record_ids": [r.get("id") for r in group],
                "status": "NEEDS_REVIEW",
            })

    return {
        "date": date,
        "variant": variant,
        "process": process or "ALL",
        "count": len(records),
        "records": records,
        "duplicate_candidates": duplicate_candidates,
        "duplicate_candidate_count": len(duplicate_candidates),
    }

if __name__ == "__main__":
    mcp.run()