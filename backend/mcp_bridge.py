import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def _fetch(date: str, variant: str, process: str = "") -> dict:
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).with_name("mcp_server.py"))],
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "get_manufacturing_records",
                arguments={
                    "date": date,
                    "variant": variant,
                    "process": process,
                },
            )

            if result.isError:
                raise RuntimeError("MCP 제조 데이터 조회 실패")

            for item in result.content:
                if item.type == "text":
                    return json.loads(item.text)

            raise RuntimeError("MCP 조회 결과가 비어 있습니다.")


def fetch_manufacturing_via_mcp(
    date: str,
    variant: str,
    process: str = "",
) -> dict:
    """MCP 서버를 통해 제조 데이터를 읽기 전용으로 조회합니다."""
    return asyncio.run(_fetch(date, variant, process))
