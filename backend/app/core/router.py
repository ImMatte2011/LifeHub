from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.auth.router import router as auth_router
from app.core.models import Module, User
from app.database import get_db

router = APIRouter(prefix="/core")
router.include_router(auth_router)


@router.get("/modules/active")
async def get_active_modules(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[dict]:
    """
    Lista dei moduli attualmente abilitati.
    Usato dal frontend per costruire menu e route dinamicamente.
    """
    result = await db.execute(
        select(Module).where(Module.is_enabled == True).order_by(Module.name)  # noqa: E712
    )
    modules = result.scalars().all()
    return [
        {
            "name": m.name,
            "display_name": m.display_name,
            "description": m.description,
            "version": m.version,
            "is_core": m.is_core,
        }
        for m in modules
    ]


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
