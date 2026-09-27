from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.deps import SessionDep
from app.api.routes import auth, tasks
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.rate_limit import setup_rate_limiting

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Async task management API: FastAPI + SQLAlchemy 2.0 async + PostgreSQL.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
setup_rate_limiting(app)
register_error_handlers(app)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health(session: SessionDep) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}
