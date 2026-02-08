# Google News Trends MCP (HTTP)

An MCP server that fetches Google News articles and Google Trends data, hosted over HTTP.
testuser2@gmail.com

cd /home/abd/Downloads/google-news-trends-mcp/backend && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
## Local run

docker run -d -p 8080:8080 google-trends-mcp
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Health check

```bash
curl -i http://localhost:8000/healthz
```

## MCP usage example

```python
from mcp.client.multi import MultiServerMCPClient

client = MultiServerMCPClient(
    {
        "google-trends": {
            "url": "https://YOUR_HOST/mcp",
            "transport": "http",
            "headers": {
                "Authorization": "Bearer any-value",
            },
        }
    }
)

tools = await client.get_tools()
```

## Environment variables

Create a `.env` file (or set env vars in your deployment). Example in `.env.example`.

## Authorization

Requests to `/mcp` must include an `Authorization: Bearer <jwt>` header. The JWT is verified for:

- Signature: via `MCP_JWT_JWKS_URL` or `MCP_JWT_PUBLIC_KEY`
- Issuer: `MCP_JWT_ISSUER`
- Audience: `MCP_JWT_AUDIENCE` (defaults to `clickup-mcp` if not set)
- Required claims: `exp`, `aud`, `iss`
- Optional scope: `MCP_JWT_REQUIRED_SCOPE` must be present in `scope` or `scp`

If JWT verification is not configured (`MCP_JWT_ISSUER` missing, or no signing key source), requests return `401`.

## Tools

The following MCP tools are available:

| Tool Name                | Description                                                        |
|--------------------------|--------------------------------------------------------------------|
| **get_news_by_keyword**  | Search for news using specific keywords.                           |
| **get_news_by_location** | Retrieve news relevant to a particular location.                   |
| **get_news_by_topic**    | Get news based on a chosen topic.                                  |
| **get_top_news**         | Fetch the top news stories from Google News.                       |
| **get_trending_terms**   | Return trending keywords from Google Trends for a specified location.|

All of the news related tools have an option to summarize the text of the article using LLM Sampling (if supported) or NLP.

# For docker 
docker build -t my-fastapi-app .
docker run --rm -p 8080:8080 my-fastapi-app
>> 

## How the server works (high level)

- `main.py` creates a FastAPI app and mounts the MCP server at `/mcp`.
- `mcp_server.py` builds a `FastMCP` server and registers tools from `tools.py`.
- `AuthorizationMiddleware` validates the JWT before any MCP request is processed.
- `BrowserManager` is started in the MCP lifespan for any browser-based work in tools.

## Auth flow (step by step)

1. Client calls `POST /mcp` with JSON-RPC payload and `Authorization: Bearer <jwt>`.
2. `AuthorizationMiddleware` calls `verify_mcp_jwt(...)`.
3. `verify_mcp_jwt` extracts the bearer token, loads signing key, and validates claims.
4. If valid, the request continues to the MCP tool handler; otherwise a `401` JSON error is returned.
