class UnauthorizedError(Exception):
    pass


def check_authorization(headers) -> None:
    auth = headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise UnauthorizedError("Authorization header missing or invalid")
