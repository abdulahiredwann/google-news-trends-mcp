from load_var import load_var
from security.utils import _get_headers_from_ctx, _get_bearer_token
from typing import Any, Dict, Optional
import jwt

from jwt import PyJWKClient
from security.utils import normalize_pem
from jwt import InvalidTokenError

def _get_jwt_signing_key(token: str) -> str:
   
    if load_var._MCP_JWT_JWKS_URL:
        jwk_client = PyJWKClient(load_var._MCP_JWT_JWKS_URL)
        return jwk_client.get_signing_key_from_jwt(token).key
    if load_var._MCP_JWT_PUBLIC_KEY:

        return normalize_pem(load_var._MCP_JWT_PUBLIC_KEY) 

    raise PermissionError("JWT verification not configured. Set MCP_JWT_JWKS_URL or MCP_JWT_PUBLIC_KEY.")



def _get_jwt_signing_key(token: str) -> str:
   
    if load_var._MCP_JWT_JWKS_URL:
        jwk_client = PyJWKClient(load_var._MCP_JWT_JWKS_URL)
        return jwk_client.get_signing_key_from_jwt(token).key
    if load_var._MCP_JWT_PUBLIC_KEY:

        return normalize_pem(load_var._MCP_JWT_PUBLIC_KEY) 

    raise PermissionError("JWT verification not configured. Set MCP_JWT_JWKS_URL or MCP_JWT_PUBLIC_KEY.")



def verify_mcp_jwt(ctx_or_headers: Any) -> Dict[str, Any]:
    if not  load_var._MCP_JWT_ISSUER:
        raise PermissionError("JWT verification is not configured. Set MCP_JWT_ISSUER.")

    headers = _get_headers_from_ctx(ctx_or_headers) if hasattr(ctx_or_headers, "request_context") else ctx_or_headers
    token = _get_bearer_token(headers)

    try:
        claims = jwt.decode(
            token,
            _get_jwt_signing_key(token),
            algorithms=load_var._MCP_JWT_ALGORITHMS,
            audience=load_var._MCP_JWT_AUDIENCE,
            issuer=load_var._MCP_JWT_ISSUER,
            options={"require": ["exp", "aud", "iss"]},
        )
    except InvalidTokenError as exc:
        raise PermissionError("Invalid MCP JWT.") from exc

    if load_var._MCP_JWT_REQUIRED_SCOPE:
        scope_claim = claims.get("scope") or claims.get("scp") or ""
        scopes = scope_claim.split() if isinstance(scope_claim, str) else list(scope_claim)
        if load_var._MCP_JWT_REQUIRED_SCOPE not in scopes:
            raise PermissionError(f"Missing required scope: {load_var._MCP_JWT_REQUIRED_SCOPE}.")

    return claims

