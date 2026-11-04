from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from sqlalchemy.orm import Session as SyncSession

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


@event.listens_for(SyncSession, "before_flush")
def audit_domain_changes(session: SyncSession, _flush_context, _instances) -> None:
    actor_id = session.info.get("actor_id")
    if not actor_id:
        return
    from app.core.models import AuditLog

    existing = [obj for obj in session.new.union(session.dirty).union(session.deleted)
                if getattr(getattr(type(obj), "__table__", None), "schema", None) in {"meta", "shared", "people", "places", "events", "knowledge", "buildings"}
                or getattr(getattr(type(obj), "__table__", None), "schema", None) == "core"
                and getattr(getattr(type(obj), "__table__", None), "name", None) in {"users", "roles", "role_permissions", "settings", "entities", "modules", "features", "module_dependencies"}]
    for obj in existing:
        table = type(obj).__table__
        state = "delete" if obj in session.deleted else "create" if obj in session.new else "update"
        ident = getattr(obj, "id", None)
        if ident is None and hasattr(obj, "entity_id"):
            ident = obj.entity_id
        resource_type = f"{table.schema}.{table.name}"
        if table.name == "users" and hasattr(obj, "password_hash"):
            details = {"fields": [key for key in obj.__dict__ if not key.startswith("_") and key != "password_hash"]}
        else:
            details = {"state": state}
        session.add(AuditLog(user_id=actor_id, action=f"data.{state}", resource_type=resource_type,
                             resource_id=ident if isinstance(ident, __import__("uuid").UUID) else None,
                             details=details))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
