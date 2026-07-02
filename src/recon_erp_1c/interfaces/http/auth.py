from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.client import HTTPMessage
from typing import Any


class AuthenticationError(RuntimeError):
    status = HTTPStatus.UNAUTHORIZED


@dataclass(frozen=True, slots=True)
class RequestContext:
    erp_token: str
    erp_token_hash: str
    user_email: str = ""
    user_name: str = ""
    user_id: int | None = None
    auth_source: str = "anonymous"


_PROCESS_SECRET = secrets.token_hex(32)


def create_session_token(profile: dict[str, Any], *, ttl_seconds: int = 12 * 60 * 60) -> str:
    now = int(time.time())
    payload = {
        "sub": str(profile.get("user_id") or ""),
        "email": str(profile.get("login") or ""),
        "name": str(profile.get("name") or ""),
        "iat": now,
        "exp": now + ttl_seconds,
    }
    body = _b64(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    signature = _sign(body)
    return f"{body}.{signature}"


def verify_session_token(token: str) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    body, signature = token.rsplit(".", 1)
    expected = _sign(body)
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(_unb64(body).decode("utf-8"))
    except Exception:
        return None
    if int(payload.get("exp") or 0) < int(time.time()):
        return None
    return payload


def request_context(headers: HTTPMessage, *, require_token: bool) -> RequestContext:
    session = headers.get("X-Recon-Session", "").strip()
    if session:
        payload = verify_session_token(session)
        if payload is None:
            raise AuthenticationError("Invalid reconciliation session")
        return RequestContext(
            erp_token=session,
            erp_token_hash=hashlib.sha256(session.encode("utf-8")).hexdigest(),
            user_email=str(payload.get("email") or ""),
            user_name=str(payload.get("name") or ""),
            user_id=_optional_int(payload.get("sub")),
            auth_source="recon_session",
        )

    token = _extract_token(headers)
    if require_token and not token:
        raise AuthenticationError("ERP token is required")
    return RequestContext(
        erp_token=token,
        erp_token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest() if token else "",
        user_email=headers.get("X-ERP-User-Email", "").strip(),
        user_name=headers.get("X-ERP-User-Name", "").strip(),
        auth_source="erp_token" if token else "anonymous",
    )


def _extract_token(headers: HTTPMessage) -> str:
    explicit = headers.get("X-ERP-Token", "").strip()
    if explicit:
        return explicit
    authorization = headers.get("Authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def _secret() -> bytes:
    return os.environ.get("RECON_SESSION_SECRET", _PROCESS_SECRET).encode("utf-8")


def _sign(body: str) -> str:
    return hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).hexdigest()


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _optional_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
