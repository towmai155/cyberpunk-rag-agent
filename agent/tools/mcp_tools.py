import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from utils.config_handler import agent_conf
from utils.logger_handler import logger


def _run_coroutine_sync(coroutine):
    """Run an async MCP operation from the current synchronous agent flow."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coroutine)
        return future.result()


def _normalize_mcp_config() -> dict[str, dict[str, Any]]:
    """Read enabled MCP server definitions from config/agent.yaml."""
    servers = agent_conf.get("mcp_servers") or {}
    if not isinstance(servers, dict):
        logger.warning("mcp_servers 配置不是字典，已跳过 MCP 工具加载。")
        return {}

    enabled_servers = {}
    for name, server_config in servers.items():
        if not isinstance(server_config, dict):
            logger.warning(f"MCP server {name} 配置不是字典，已跳过。")
            continue
        if server_config.get("enabled", True) is False:
            continue

        normalized = dict(server_config)
        normalized.pop("enabled", None)
        enabled_servers[name] = normalized

    return enabled_servers


def _sync_mcp_tool_call(mcp_tool: BaseTool, **kwargs):
    return _run_coroutine_sync(mcp_tool.ainvoke(kwargs))


def _as_sync_tool(mcp_tool: BaseTool) -> BaseTool:
    """Wrap async MCP tools so the current synchronous stream API can call them."""
    return StructuredTool.from_function(
        func=lambda **kwargs: _sync_mcp_tool_call(mcp_tool, **kwargs),
        name=mcp_tool.name,
        description=mcp_tool.description or f"MCP tool: {mcp_tool.name}",
        args_schema=getattr(mcp_tool, "args_schema", None),
    )


async def _load_mcp_tools_async() -> list[BaseTool]:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    servers = _normalize_mcp_config()
    if not servers:
        return []

    client = MultiServerMCPClient(servers)
    tools = await client.get_tools()
    logger.info(f"已加载 MCP 工具 {len(tools)} 个。")
    return [_as_sync_tool(mcp_tool) for mcp_tool in tools]


def load_mcp_tools() -> list[BaseTool]:
    """Load MCP tools declared in config/agent.yaml.

    Loading failures are logged and isolated so local tools remain usable.
    """
    try:
        return _run_coroutine_sync(_load_mcp_tools_async())
    except ImportError:
        logger.warning("未安装 langchain-mcp-adapters，已跳过 MCP 工具加载。")
    except Exception as e:
        logger.error(f"MCP 工具加载失败: {str(e)}", exc_info=True)
    return []
