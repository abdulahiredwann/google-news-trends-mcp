from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from mcp_server import mcp_http_app

app = FastAPI(lifespan=mcp_http_app.lifespan)
app.mount("/mcp", mcp_http_app)


@app.get("/healthz")
async def healthz() -> PlainTextResponse:
    return PlainTextResponse("ok")
