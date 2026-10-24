from fastapi import Header, HTTPException, Security, status
from jarvis.config.settings import settings


async def verify_auth_token(x_jarvis_token: str | None = Header(default=None)) -> bool:
    # If auth token is configured, enforce matching token
    if settings.AUTH_TOKEN and x_jarvis_token != settings.AUTH_TOKEN:
        # In local development mode, allow localhost bypass if token header is absent
        if not settings.DEBUG and x_jarvis_token is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid JARVIS Authentication Token"
            )
    return True
