"""
tavily.py — Tavily Web Search Tool
====================================

Wraps the Tavily Search API as a LangChain tool for the ReAct agent.

What is Tavily?
    Tavily is a search API optimized for AI agents. It returns clean,
    summarised search results (not raw HTML). This makes it ideal for
    LLM-based agents that need to search the web.

How it's used:
    1. The ReAct agent sees the tool description and decides when to use it.
    2. When the user asks something like "Search the web for LangChain agents",
       the agent calls this tool with the query.
    3. Tavily returns up to 5 search results with titles, URLs, and snippets.
    4. The agent reads the results and summarises them in its response.

Configuration:
    Requires TAVILY_API_KEY in the .env file. If the key is not set,
    get_tavily_tool() returns None and the agent simply won't have
    web search capability (but still works with other tools / its own knowledge).
"""

from langchain_community.tools.tavily_search import TavilySearchResults
from app.core.config import settings
import os


def get_tavily_tool():
    """
    Create and return a Tavily search tool for the ReAct agent.

    Returns:
        TavilySearchResults | None:
            - A configured LangChain tool if TAVILY_API_KEY is set.
            - None if the API key is missing (agent continues without web search).

    How it works:
        1. Checks if TAVILY_API_KEY is set in the environment/settings.
        2. Sets the env var so the Tavily SDK can read it.
        3. Creates a TavilySearchResults tool with:
           - max_results=5: Return up to 5 search results
           - name="tavily_search": The name the agent sees
           - description: Tells the agent WHEN to use this tool

    The description is crucial — it's what the LLM reads to decide whether
    to use Tavily or another tool for a given query.
    """
    if not settings.TAVILY_API_KEY:
        return None

    # The Tavily SDK reads TAVILY_API_KEY from the environment
    os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY

    tool = TavilySearchResults(
        max_results=5,
        name="tavily_search",
        description=(
            "Search the web for current information. "
            "Use this tool when the user asks about recent events, "
            "wants to find information online, or asks you to search the web. "
            "Input should be a search query string."
        ),
    )
    return tool
