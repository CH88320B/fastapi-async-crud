from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError
from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas.user import UserCreate, UserUpdate


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email.strip().lower()))


async def create(session: AsyncSession, data: UserCreate) -> User:
    user = User(email=data.email, full_name=data.full_name, hashed_password=hash_password(data.password))
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Email already registered") from exc
    await session.refresh(user)
    return user


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    user = await get_by_email(session, email)
    if not verify_password(password, user.hashed_password if user else None):
        return None
    if user is None or not user.is_active:
        return None
    return user


async def update(session: AsyncSession, user: User, data: UserUpdate) -> User:
    if data.full_name is not None:
        user.full_name = data.full_name.strip()
    if data.password is not None:
        user.hashed_password = hash_password(data.password)
    await session.commit()
    await session.refresh(user)
    return user
