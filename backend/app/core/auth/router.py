from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user, _extract_token
from app.core.auth.schemas import LoginRequest, LoginResponse, MeResponse, UserResponse
from app.core.auth.service import (
    authenticate_user,
    create_session,
    delete_session,
    is_multi_user_enabled,
    write_audit,
)
from app.core.models import User
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    Login con username e password.

    Controlli nell'ordine:
    1. Credenziali valide
    2. Account attivo (is_active)
    3. Se multi_user_enabled=False, solo admin può accedere
    """
    user = await authenticate_user(db, body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    multi_user = await is_multi_user_enabled(db)
    if not multi_user and not user.is_system_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Multi-user access is disabled on this instance",
        )

    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    session = await create_session(db, user, ip_address=ip, user_agent=user_agent)

    await write_audit(
        db,
        action="auth.login",
        user_id=user.id,
        ip_address=ip,
        details={"username": user.username},
    )

    return LoginResponse(
        token=session.issued_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    token = _extract_token(request) or ""

    await write_audit(
        db,
        action="auth.logout",
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )

    await delete_session(db, token)


@router.get("/me", response_model=MeResponse)
async def me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MeResponse:
    """Restituisce l'utente corrente e lo stato multi_user dell'istanza."""
    multi_user = await is_multi_user_enabled(db)
    return MeResponse(
        user=UserResponse.model_validate(current_user),
        multi_user_enabled=multi_user,
    )
