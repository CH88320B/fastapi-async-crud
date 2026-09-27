from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, SessionDep
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import create_access_token
from app.schemas.user import Token, UserCreate, UserRead, UserUpdate
from app.services import users

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_auth)
async def register(request: Request, data: UserCreate, session: SessionDep) -> UserRead:
    user = await users.create(session, data)
    return UserRead.model_validate(user)


@router.post("/token", response_model=Token)
@limiter.limit(settings.rate_limit_auth)
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
) -> Token:
    """OAuth2 password flow. Send `username` (the email) and `password` as form fields."""
    user = await users.authenticate(session, form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(
        access_token=create_access_token(user.id, {"email": user.email}),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/me", response_model=UserRead)
async def update_me(data: UserUpdate, user: CurrentUser, session: SessionDep) -> UserRead:
    return UserRead.model_validate(await users.update(session, user, data))
