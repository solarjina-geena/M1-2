import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "get_manufacturing_records",
                arguments={
                    "date": "2026-09-10",
                    "variant": "OV",
                },
            )

            if result.isError:
                print("MCP 호출 오류:", result.content)
                return

            for item in result.content:
                if item.type == "text":
                    data = json.loads(item.text)

                    print("조회 날짜:", data.get("date"))
                    print("Variant:", data.get("variant"))
                    print("전체 기록:", data.get("count"))
                    print("중복 의심 그룹:", data.get("duplicate_candidate_count"))

                    processes = sorted({
                        str(r.get("process", "UNKNOWN"))
                        for r in data.get("records", [])
                    })
                    print("포함된 공정:", processes)

asyncio.run(main())
