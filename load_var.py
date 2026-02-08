
import os
from dotenv import load_dotenv

load_dotenv()

class LoadVar:
    def __init__(self):
        self._MCP_JWT_AUDIENCE = os.getenv("MCP_JWT_AUDIENCE", "clickup-mcp")
        self._MCP_JWT_ISSUER = os.getenv("MCP_JWT_ISSUER", "")
        self._MCP_JWT_JWKS_URL = os.getenv("MCP_JWT_JWKS_URL", "")
        self._MCP_JWT_PUBLIC_KEY = os.getenv("MCP_JWT_PUBLIC_KEY","")
        self._MCP_JWT_REQUIRED_SCOPE = os.getenv("MCP_JWT_REQUIRED_SCOPE")
        self._MCP_JWT_ALGORITHMS = (os.getenv("MCP_JWT_ALGORITHMS", "RS256").split(","))


load_var = LoadVar()