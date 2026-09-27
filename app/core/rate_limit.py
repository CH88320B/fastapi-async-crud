from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()


def client_key(request: Request) -> str:
    """Rate-limit per authenticated token when present, otherwise per client IP."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return f"token:{auth[7:][-32:]}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=client_key,
    default_limits=[settings.rate_limit_default],
    enabled=settings.rate_limit_enabled,
    headers_enabled=True,
)


def setup_rate_limiting(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limited(_: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": f"Rate limit exceeded: {exc.detail}"},
            headers={"Retry-After": "60"},
        )
