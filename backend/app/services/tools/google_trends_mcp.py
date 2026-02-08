"""
google_trends_mcp.py — Google Trends MCP Client Configuration
=============================================================

Configures the connection to the Google Trends MCP (Model Context Protocol) server.

What is MCP?
    MCP (Model Context Protocol) is a standard for AI tools. An MCP server
    exposes tools (functions) that an LLM agent can call. In our case, the
    Google Trends MCP server provides tools like:
    - get_news_by_keyword    → Search Google News by keyword
    - get_news_by_location   → Get news for a specific country/region
    - get_news_by_topic      → Get news by topic category
    - get_top_news           → Get today's top headlines
    - get_trending_terms     → Get currently trending search terms

How MCP integration works:
    1. The MCP server runs in a Docker container on port 8080.
    2. We use `langchain-mcp-adapters` (MultiServerMCPClient) to connect.
    3. The adapter converts MCP tools into LangChain-compatible tools.
    4. These tools are then passed to the ReAct agent alongside Tavily.
    5. The agent decides which tool to call based on the user's query.

Authentication:
    The MCP server requires a Supabase JWT in the Authorization header.
    We pass the user's access_token so the MCP server can verify the request.

Configuration:
    MCP_SERVER_URL in .env:
    - Docker Compose: http://google-trends-mcp:8080/mcp/  (service name)
    - Local dev:      http://localhost:8080/mcp/
"""

from langchain_mcp_adapters.client import MultiServerMCPClient
from app.core.config import settings


def get_mcp_client_config(access_token: str = "") -> dict:
    """
    Build the MCP client configuration dictionary.

    This config is passed to MultiServerMCPClient to tell it how to
    connect to the Google Trends MCP server.

    Args:
        access_token (str): The user's Supabase JWT token. Passed as an
            Authorization header so the MCP server can authenticate the request.

    Returns:
        dict: Configuration for MultiServerMCPClient with the format:
            {
                "google-trends": {
                    "url": "http://...:8080/mcp/",
                    "transport": "streamable_http",
                    "headers": {"Authorization": "Bearer <token>"}  # if token provided
                }
            }

    Usage:
        config = get_mcp_client_config(access_token=user_token)
        client = MultiServerMCPClient(config)
        tools  = await client.get_tools()   # Returns LangChain-compatible tools

    Transport types:
        - "streamable_http": HTTP-based transport (used here) — simple and reliable.
        - "stdio": Subprocess-based transport (used when MCP server is a local process).
        - "sse": Server-Sent Events transport (another HTTP option).
        We use streamable_http because our MCP server is a separate Docker container.
    """
    config = {
        "google-trends": {
            "url": settings.MCP_SERVER_URL,
            "transport": "streamable_http",
        }
    }
    # Add JWT auth header if token is available
    if access_token:
        config["google-trends"]["headers"] = {
            "Authorization": f"Bearer {access_token}",
        }
    return config
