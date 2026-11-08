from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import current_user
from app.db.session import get_session
from app.errors import DomainError
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut
from app.services.auth import hash_password, issue_token, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class KredensialSalah(DomainError):
    status = 401


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
async def register(
    body: RegisterIn, session: AsyncSession = Depends(get_session)
) -> User:
    sudah_ada = await session.scalar(
        select(User).where(User.email == body.email.lower())
    )
    if sudah_ada:
        raise DomainError("email_terpakai", "Email ini sudah terdaftar.")
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
        role=body.role,
    )
    session.add(user)
    await session.flush()
    return user


@router.post("/login", response_model=TokenOut)
async def login(
    body: LoginIn, session: AsyncSession = Depends(get_session)
) -> TokenOut:
    user = await session.scalar(select(User).where(User.email == body.email.lower()))
    # Pesan yang sama untuk email tak dikenal maupun password salah, supaya tidak
    # membocorkan email mana yang terdaftar.
    if user is None or not verify_password(body.password, user.password_hash):
        raise KredensialSalah("kredensial_salah", "Email atau password salah.")
    return TokenOut(access_token=issue_token(user.id, user.role))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)) -> User:
    return user
