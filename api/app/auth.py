"""API-key auth with three roles: viewer < engineer < admin."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from minehub_common.settings import get_settings

ROLE_RANK = {"viewer": 0, "engineer": 1, "admin": 2}
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _keys() -> dict[str, str]:
    out = {}
    for pair in get_settings().api_keys.split(","):
        role, _, key = pair.partition(":")
        if key:
            out[key.strip()] = role.strip()
    return out


def current_role(key: str | None = Security(api_key_header)) -> str:
    role = _keys().get(key or "")
    if role is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing or invalid API key")
    return role


def require(min_role: str):  # noqa: ANN201
    def dep(role: str = Depends(current_role)) -> str:
        if ROLE_RANK[role] < ROLE_RANK[min_role]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"requires {min_role} role")
        return role
    return dep