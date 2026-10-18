from app.main import infer_graph_context

tests = [
    "2026년 9월 10일",
    "2026-09-10",
    "2026.09.10",
    "2026/09/10",
    "9/10",
    "9-10",
    "9.10",
    "0910",
    "260910",
]

for text in tests:
    result = infer_graph_context(text + " OV 생산수량", {})
    actual = result.get("date")
    status = "PASS" if actual == "2026-09-10" else "FAIL"
    print(f"{status} | {text} -> {actual}")
