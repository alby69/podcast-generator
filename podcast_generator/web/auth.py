from __future__ import annotations

import hmac
from typing import Optional

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse

from podcast_generator.config import Settings

security = HTTPBearer(auto_error=False)


def _get_config() -> Settings:
    return Settings()


def verify_web_password(request: Request) -> Optional[str]:
    cfg = _get_config()
    if not cfg.web_password:
        return "ok"
    token = request.cookies.get("auth_token")
    if token and hmac.compare_digest(token, cfg.web_password):
        return "ok"
    raise HTTPException(status_code=302, detail="Redirecting to login")


async def verify_api_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> bool:
    cfg = _get_config()
    if not cfg.api_token:
        return True
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header. Use: Authorization: Bearer <token>",
        )
    if not hmac.compare_digest(credentials.credentials, cfg.api_token):
        raise HTTPException(status_code=401, detail="Invalid API token")
    return True
