from typing import Any,  Optional
from fastmcp import Context


def _extract_header_value(headers: Any, header_name: str) -> Optional[str]:
    if headers is None:
        return None
    try:
        return (
            headers.get(header_name)
            or headers.get(header_name.lower())
            or headers.get(header_name.upper())
        )
    except AttributeError:
        return None
    

#     return pem
def normalize_pem(pem: str) -> str:
    if not pem:
        raise ValueError("Empty PEM")

    # Remove surrounding quotes only
    pem = pem.strip()
    if (pem.startswith('"') and pem.endswith('"')) or (pem.startswith("'") and pem.endswith("'")):
        pem = pem[1:-1]

    # Convert escaped newlines to real ones
    pem = pem.replace("\\n", "\n")

    # Normalize Windows line endings
    pem = pem.replace("\r\n", "\n").replace("\r", "\n")

    # Final sanity check
    if "BEGIN" not in pem or "END" not in pem:
        raise ValueError("Invalid PEM format")

    # Ensure trailing newline
    if not pem.endswith("\n"):
        pem += "\n"

    return pem



def _get_headers_from_ctx(ctx: Any) -> Any:
    """
    Returns the headers mapping from a FastMCP Context.
    Works for streamable-http where headers live on request.headers.
    """
    if ctx is None:
        return None

    rc = getattr(ctx, "request_context", None)
    if rc is None:
        return None

    # Preferred: request.headers
    req = getattr(rc, "request", None)
    if req is not None and hasattr(req, "headers") and req.headers is not None:
        return req.headers

    # Fallback: request_context.headers (sometimes populated)
    return getattr(rc, "headers", None)



def _get_bearer_token(headers):
    """
    headers: List[Tuple[bytes, bytes]] OR dict-like
    """

    # Normalize headers to dict[str, str]
    if isinstance(headers, list):
        headers_dict = {
            k.decode("latin1").lower(): v.decode("latin1")
            for k, v in headers
        }
    else:
        headers_dict = {
            str(k).lower(): str(v)
            for k, v in headers.items()
        }

    auth = headers_dict.get("authorization")
    if not auth or not auth.startswith("Bearer "):
        raise PermissionError(
            "Missing or invalid Authorization header. Expected 'Bearer <jwt>'."
        )

    return auth.split(" ", 1)[1]






def norm(pem: str) -> str:
    # normalize newlines + trim spaces on each line
    pem = pem.replace("\r\n", "\n").replace("\r", "\n").strip()
    pem = "\n".join(line.strip() for line in pem.split("\n"))
    return pem


def get_request_auth(ctx: Optional[Context]) -> tuple[str, str]:
    headers = _get_headers_from_ctx(ctx)

    access_token = _extract_header_value(headers, "XGAAccessToken")
    team_id = _extract_header_value(headers, "XGTeamID")

    if access_token and team_id:
        return access_token.strip(), team_id.strip()

    raise RuntimeError("Missing required headers: XGAAccessToken and/or XGTeamID")
