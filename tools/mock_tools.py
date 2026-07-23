import asyncio
import atexit
import json
import os
import sys
import threading
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _MCPClient:
    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._session = None
        self._tool_names = set()
        self._stack = None
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _submit(self, coro, timeout=30):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout=timeout)

    async def _connect(self):
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.server"],
            cwd=_REPO_ROOT,
        )
        stack = AsyncExitStack()
        devnull = open(os.devnull, "w")
        read, write = await stack.enter_async_context(stdio_client(params, errlog=devnull))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        tools = await session.list_tools()

        self._stack = stack
        self._session = session
        self._tool_names = {t.name for t in tools.tools}

    def _ensure_connected(self):
        with self._lock:
            if self._session is None:
                self._submit(self._connect())

    async def _call(self, name, arguments):
        result = await self._session.call_tool(name, arguments)
        if result.isError:
            message = result.content[0].text if result.content else "unknown MCP error"
            return {"error": message}
        if result.structuredContent is not None:
            return result.structuredContent
        text = result.content[0].text if result.content else "{}"
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return {"error": f"could not parse tool result: {text}"}

    def call_tool(self, name: str, **kwargs) -> dict:
        self._ensure_connected()
        if name not in self._tool_names:
            return {"error": f"unknown tool '{name}'"}
        try:
            return self._submit(self._call(name, kwargs))
        except Exception as exc:
            return {"error": f"MCP call to '{name}' failed: {exc}"}

    def close(self):
        if self._session is None:
            return
        try:
            self._submit(self._stack.aclose(), timeout=10)
        except Exception:
            pass
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)


_client = _MCPClient()
atexit.register(_client.close)


def call_tool(name: str, **kwargs) -> dict:
    return _client.call_tool(name, **kwargs)
